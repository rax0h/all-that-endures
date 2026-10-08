import pytest

from ate_sim.core import World
from ate_sim.institutions import SocietyApplication, Branch
from ate_sim.society_accountability import Inquiry, _close
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'bounded-application-threshold'


def application(key, *, branch=1, passed=False):
    return SocietyApplication(key, 'probe', key, branch, 0, True, passed=passed)


def converted(tmp_path, history):
    world = World(843000, year=2)
    world.institutions.branches[1] = Branch(1, 1, 1, 0, None)
    for key in range(1, history + 1):
        world.institutions.applications[key] = application(key)
    world.society_accountability.inquiries[1] = Inquiry(1, 1, 0, 'probe', 1, .2)
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_inquiry_close_uses_five_checked_candidates_no_application_payloads(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        applications = session.institution_applications
        before = session.store.diagnostics()
        _close(session.world, session.world.society_accountability.inquiries[1])
        after = session.store.diagnostics()
        assert session.world.society_accountability.inquiries[1].findings == ('training_or_selection_failure',)
        assert applications.diagnostics()['payload_loads'] == 0
        assert after.query_rows - before.query_rows <= 5
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.society_accountability.inquiries[1].status == 'closed'


def test_threshold_uses_current_overlays_and_excludes_changed_baseline_keys(tmp_path):
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        applications = session.institution_applications
        assert applications.at_least(('branch', 'passed'), 1, False, count=5)
        applications[1].passed = True
        assert not applications.at_least(('branch', 'passed'), 1, False, count=5)
        applications[6] = application(6)
        assert applications.at_least(('branch', 'passed'), 1, False, count=5)
        del applications[2]
        assert not applications.at_least(('branch', 'passed'), 1, False, count=5)
        applications[1].passed = False
        assert applications.at_least(('branch', 'passed'), 1, False, count=5)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.institution_applications.at_least(('branch', 'passed'), 1, False, count=5)


@pytest.mark.parametrize('failed', [4, 5, 6])
def test_eager_and_lazy_inquiry_findings_match_at_threshold(tmp_path, failed):
    path = converted(tmp_path, failed)
    eager = World(843000, year=2)
    eager.institutions.branches[1] = Branch(1, 1, 1, 0, None)
    for key in range(1, failed + 1):
        eager.institutions.applications[key] = application(key)
    query = Inquiry(1, 1, 0, 'probe', 1, .2)
    eager.society_accountability.inquiries[1] = query
    _close(eager, query)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        _close(session.world, session.world.society_accountability.inquiries[1])
        assert session.world.digest() == eager.digest()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_threshold_membership_save_failure_resolves_current_predicate(tmp_path, phase):
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        applications = session.institution_applications
        applications[1].branch = 2
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        assert not applications.at_least(('branch', 'passed'), 1, False, count=5)
        if phase == 'before_commit':
            session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert not session.institution_applications.at_least(('branch', 'passed'), 1, False, count=5)


def make_legacy_application_authority(path):
    from ate_sim.incremental_store import _record_checksum
    from ate_sim.persistence_adapters import WorldCodec, SCHEMA, META, COLLECTION_LAYOUT
    from ate_sim.persistence_lazy import INSTITUTION_APPLICATION_NAMESPACE
    from ate_sim.persistence_lazy_store import LazyRecordStore, _version_checksum
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        for key, value, schema in store.read_records(META, expected_record_schema=1):
            layout = value if key == COLLECTION_LAYOUT else value['collections']
            old = layout[INSTITUTION_APPLICATION_NAMESPACE]
            layout[INSTITUTION_APPLICATION_NAMESPACE] = ('RecordTable', old[1], old[2])
            typed_key, payload = store.codec.encode(key), store.codec.encode(value)
            generation = store.db.execute('SELECT last_changed_generation FROM records WHERE namespace=? AND typed_key=?', (META, typed_key)).fetchone()[0]
            checksum = _record_checksum(META, typed_key, schema, store.codec.version, generation, payload)
            store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?', (payload, checksum, META, typed_key))
        rows = store.db.execute('SELECT typed_key,record_schema,codec_version,valid_from,valid_to,memberships,payload FROM lazy_record_versions WHERE namespace=?', (INSTITUTION_APPLICATION_NAMESPACE,)).fetchall()
        for key, schema, codec, start, end, memberships, payload in rows:
            memberships = store.codec.encode(tuple(member for member in store.codec.decode(memberships) if member[0] != 'branch_passed'))
            checksum = _version_checksum(INSTITUTION_APPLICATION_NAMESPACE, key, schema, codec, start, end, memberships, payload)
            store.db.execute('UPDATE lazy_record_versions SET memberships=?,row_checksum=? WHERE namespace=? AND typed_key=? AND valid_from=?', (memberships, checksum, INSTITUTION_APPLICATION_NAMESPACE, key, start))
        store.db.execute("DELETE FROM lazy_query_versions WHERE namespace=? AND index_name='branch_passed'", (INSTITUTION_APPLICATION_NAMESPACE,))
        store.db.commit()
        store.verify_all()


def test_legacy_index_absence_uses_checked_fallback_without_open_upgrade(tmp_path):
    path = converted(tmp_path, 5)
    make_legacy_application_authority(path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        authority = session.store.db.execute("SELECT typed_key,payload,memberships,row_checksum FROM lazy_record_versions WHERE namespace='world.institutions.applications' ORDER BY typed_key,valid_from").fetchall()
        applications = session.institution_applications
        assert not applications._branch_query_authority
        assert applications.diagnostics()['payload_loads'] == 0
        assert session.store.db.execute("SELECT COUNT(*) FROM lazy_query_versions WHERE index_name='branch_passed'").fetchone()[0] == 0
        assert applications.at_least(('branch', 'passed'), 1, False, count=5)
        assert applications.diagnostics()['payload_loads'] == 5
        applications[1].branch = 2
        assert not applications.at_least(('branch', 'passed'), 1, False, count=5)
    import sqlite3
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT typed_key,payload,memberships,row_checksum FROM lazy_record_versions WHERE namespace='world.institutions.applications' ORDER BY typed_key,valid_from").fetchall() == authority
        assert db.execute("SELECT COUNT(*) FROM lazy_query_versions WHERE index_name='branch_passed'").fetchone()[0] == 0


@pytest.mark.parametrize('count', [-1, True, 5.0, '5'])
def test_threshold_requires_exact_nonnegative_count(tmp_path, count):
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        with pytest.raises(ValueError):
            session.institution_applications.at_least(('branch', 'passed'), 1, False, count=count)


def test_passed_query_preserves_native_bool_numeric_equality_on_reopen(tmp_path):
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.institution_applications[1].passed = 0
        assert session.institution_applications.at_least(('branch', 'passed'), 1, False, count=5)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert type(session.institution_applications[1].passed) is int
        assert session.institution_applications.at_least(('branch', 'passed'), 1, False, count=5)
        assert session.institution_applications.at_least(('branch', 'passed'), 1, 0.0, count=5)


def test_query_capability_kind_preserves_cross_owner_application_paths(tmp_path):
    world = World(843000)
    for key in range(1, 6):
        world.institutions.applications[key] = application(key)
    world.currency.wallets[11] = {'application': world.institutions.applications[1]}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        shared = session.wallets[11]['application']
        assert shared is session.institution_applications[1]
        shared.passed = True
        assert not session.institution_applications.at_least(('branch', 'passed'), 1, False, count=5)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.wallets[11]['application'] is session.institution_applications[1]
        assert not session.institution_applications.at_least(('branch', 'passed'), 1, False, count=5)
