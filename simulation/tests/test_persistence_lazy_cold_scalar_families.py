import pytest

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.warfare import Conflict
from ate_sim.society_accountability import Inquiry
from ate_sim.threat_ecology import MagicalThreat
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.record_index import indexed

RULES = 'cold-scalar-family-gates'
FAMILIES = ('warfare.conflicts', 'society_accountability.inquiries', 'threat_ecology.threats')


def table(world, family):
    root, field = family.split('.')
    return getattr(getattr(world, root), field)


def record(family, key, active=True):
    if family == FAMILIES[0]:
        return Conflict(key, 1, 2, 0, 'probe', status='war' if active else 'peace')
    if family == FAMILIES[1]:
        return Inquiry(key, 1, 0, 'probe', 1, .2, status='open' if active else 'closed')
    return MagicalThreat(key, 'probe', 1, 1, 0, .1, status='active' if active else 'resolved')


def converted(tmp_path, history=5, alias=False):
    world = World(843000)
    for family in FAMILIES:
        records = table(world, family)
        for key in range(1, history + 9):
            records[key] = record(family, key, key > history)
    if alias:
        world.currency.wallets[11] = {'conflict': world.warfare.conflicts[history + 1]}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_closed_history_does_not_load_on_open_or_active_queries(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        for family in FAMILIES:
            records = table(session.world, family)
            assert records.diagnostics()['payload_loads'] == 0
            assert records.diagnostics()['resident_records'] == 0
        before = session.store.diagnostics()
        assert [r.id for r in session.world.warfare.active()] == list(range(history + 1, history + 9))
        assert [r.id for r in indexed(session.world.society_accountability, 'inquiries').select(('status', 'branch'), 'open', 1)] == list(range(history + 1, history + 9))
        assert [r.id for r in session.world.threat_ecology.active(1)] == list(range(history + 1, history + 9))
        assert session.store.diagnostics().query_rows - before.query_rows == 24
        for family in FAMILIES:
            assert table(session.world, family).diagnostics()['payload_loads'] == 8


def test_direct_edits_memberships_and_single_family_save(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        historical_pin = session.store.capture_pin()
        before = session.store.db.execute('SELECT namespace,COUNT(*) FROM lazy_record_versions GROUP BY namespace').fetchall()
        q = session.world.society_accountability.inquiries[6]
        q.status = 'closed'
        assert [r.id for r in indexed(session.world.society_accountability, 'inquiries').select(('status', 'branch'), 'open', 1)] == list(range(7, 14))
        session.save()
        after = dict(session.store.db.execute('SELECT namespace,COUNT(*) FROM lazy_record_versions GROUP BY namespace').fetchall())
        deltas = {ns: after.get(ns, 0) - count for ns, count in before}
        assert {ns: n for ns, n in deltas.items() if n} == {'world.society_accountability.inquiries': 1}
        session.store.release_pin(historical_pin)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.society_accountability.inquiries[6].status == 'closed'
        assert len(indexed(session.world.society_accountability, 'inquiries').select(('status', 'branch'), 'open', 1)) == 7


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_scalar_save_failure_resolves_with_frozen_evidence(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.threat_ecology.threats[6].status = 'resolved'
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.threat_ecology.threats[6].status == 'resolved'
        assert len(session.world.threat_ecology.active(1)) == 7


def test_shared_wallet_mutation_reopen_and_portable_detach(tmp_path):
    path = converted(tmp_path, alias=True)
    session = open_lazy_world_session(path, rules_id=RULES)
    shared = session.wallets[11]['conflict']
    assert shared is session.world.warfare.conflicts[6]
    shared.status = 'peace'
    session.save()
    session.close()
    session = open_lazy_world_session(path, rules_id=RULES)
    assert session.wallets[11]['conflict'] is session.world.warfare.conflicts[6]
    assert len(session.world.warfare.active()) == 7
    detached = session.detach(materialize_history=True)
    assert detached.currency.wallets[11]['conflict'] is detached.warfare.conflicts[6]
    assert checkpoint.loads(checkpoint.dumps(detached)).digest() == detached.digest()


def test_delete_reinsert_preserves_native_order_and_layout(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        records = session.world.warfare.conflicts
        del records[1]
        records[1] = record(FAMILIES[0], 1)
        records[20] = record(FAMILIES[0], 20)
        assert tuple(records) == (*range(2, 14), 1, 20)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert tuple(session.world.warfare.conflicts) == (*range(2, 14), 1, 20)
        assert len(session.world.warfare.conflicts) == 14
        assert session.save() == session.pin.captured_head


def test_scalar_predicate_preserves_native_numeric_equality(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        q = session.world.society_accountability.inquiries[6]
        q.branch = 1.0
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        queries = indexed(session.world.society_accountability, 'inquiries')
        assert queries.ids(('status', 'branch'), 'open', 1) == tuple(range(6, 14))
        assert queries.ids(('status', 'branch'), 'open', True) == tuple(range(6, 14))
        assert type(queries[6].branch) is float


def test_scalar_residency_sidecars_remain_bounded_and_retained_object_mutates(tmp_path):
    path = converted(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        records = session.world.warfare.conflicts
        retained = records[1]
        for key in range(2, 1001):
            records[key]
        assert records.diagnostics()['resident_records'] <= 256
        assert len(records._baseline_payload) <= 256
        assert len(records._baseline_ordinal) <= 256
        retained.status = 'war'
        assert records[1] is retained
        assert 1 in records.ids('status', 'war')
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.warfare.conflicts[1].status == 'war'


def legacy_scalar_authority(path):
    from ate_sim.incremental_store import _record_checksum
    from ate_sim.persistence_adapters import WorldCodec, SCHEMA, META
    from ate_sim.persistence_lazy_store import LazyRecordStore
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA, expected_rules_id=RULES) as store:
        for family in (*FAMILIES, 'threat_ecology.resolutions'):
            namespace = 'world.' + family
            rows = store.db.execute('SELECT typed_key,payload,valid_from FROM lazy_record_versions WHERE namespace=? AND valid_to IS NULL', (namespace,)).fetchall()
            for key, payload, generation in rows:
                ordinal = store.db.execute('SELECT ordinal FROM lazy_order_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL', (namespace, key)).fetchone()[0]
                envelope = store.codec.encode((ordinal, store.codec.decode(payload)))
                checksum = _record_checksum(namespace, key, 1, store.codec.version, generation, envelope)
                store.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)', (namespace, key, envelope, checksum, store.codec.version, 1, generation))
            for sql_table in ('lazy_record_versions', 'lazy_order_versions', 'lazy_query_versions', 'lazy_namespace_state'):
                store.db.execute('DELETE FROM ' + sql_table + ' WHERE namespace=?', (namespace,))
        for key, value, schema in store.read_records(META, expected_record_schema=1):
            layout = value if key == 'collections/v1' else value['collections']
            for family in (*FAMILIES, 'threat_ecology.resolutions'):
                namespace = 'world.' + family
                old = layout[namespace]
                layout[namespace] = (old[0].removesuffix('-scalar/v1'), old[1], old[2])
            typed_key, payload = store.codec.encode(key), store.codec.encode(value)
            generation = store.db.execute('SELECT last_changed_generation FROM records WHERE namespace=? AND typed_key=?', (META, typed_key)).fetchone()[0]
            checksum = _record_checksum(META, typed_key, schema, store.codec.version, generation, payload)
            store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?', (payload, checksum, META, typed_key))
        store.db.commit()
        store.verify_all()


def test_legacy_scalar_fields_remain_eager_and_open_preserves_bytes(tmp_path):
    import sqlite3
    path = converted(tmp_path)
    legacy_scalar_authority(path)
    with sqlite3.connect(path) as db:
        before = db.execute('SELECT namespace,typed_key,payload,payload_checksum FROM records ORDER BY namespace,typed_key').fetchall()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert not {'world.' + family for family in (*FAMILIES, 'threat_ecology.resolutions')} & session._scalar_tables.keys()
        assert len(session.world.warfare.active()) == 8
        assert len(session.world.threat_ecology.active(1)) == 8
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT namespace,typed_key,payload,payload_checksum FROM records ORDER BY namespace,typed_key').fetchall() == before


def test_marked_empty_scalar_family_requires_checked_namespace_authority(tmp_path):
    import sqlite3
    from ate_sim.incremental_store import StoreIntegrityError
    world = World(843000)
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM lazy_namespace_state WHERE namespace='world.warfare.conflicts'")
    with pytest.raises(StoreIntegrityError, match='scalar namespace authority'):
        open_lazy_world_session(path, rules_id=RULES)


def test_failed_detach_retains_scalar_mutation_authority(tmp_path, monkeypatch):
    from ate_sim import persistence_lifecycle as lifecycle
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        retained = session.world.warfare.conflicts[6]
        def fail(phase, _session):
            if phase == 'before_publish':
                raise OSError('detach staging')
        monkeypatch.setattr(lifecycle, '_lifecycle_phase', fail)
        with pytest.raises(OSError, match='detach staging'):
            session.detach(materialize_history=True)
        retained.status = 'peace'
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.warfare.conflicts[6].status == 'peace'
