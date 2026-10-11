"""Private checked-catalog bootstrap copies are not complete format6 upgrades."""
import hashlib
import importlib
import importlib.util
import pytest

from ate_sim.core import World
from ate_sim.skills import SkillHistory
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, OWNER_NAMESPACE, CATALOG_NAMESPACE
from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE, PAGE_NAMESPACE
from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
from ate_sim.incremental_store import RecordChange, StoreIntegrityError, StoreFormatError
from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY

RULES = 'private-catalog-copy'
NS = 'world.skills.skills'


def module():
    name = 'ate_sim.persistence_catalog_copy'
    assert importlib.util.find_spec(name) is not None, 'private checked-catalog copy helper is missing'
    return importlib.import_module(name)


def opened(path):
    return LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA, expected_rules_id=RULES)


def legacy_lazy(tmp_path, size=32, *, configure=None):
    world = World(843000)
    shared = list(range(size))
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=shared)
    world.skills.skills[2, 'craft'] = SkillHistory(2, 'craft', provenance=shared)
    if configure is not None: configure(world)
    cold, source = tmp_path / 'cold.sqlite', tmp_path / 'legacy-lazy.sqlite'
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, source, rules_id=RULES, native_graph_buckets=True)
    return source


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(values):
    if hasattr(values, 'close'): values.close()


def test_catalog_copy_preserves_source_and_checks_all_physical_owner_witnesses(tmp_path):
    source = legacy_lazy(tmp_path, size=256)
    before = sha(source)
    with opened(source) as store:
        generation, identity = store.generation, store.store_identity
    target = tmp_path / 'copy.sqlite'
    result = module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert sha(source) == before
    assert result['source_generation'] == generation and result['generation'] == generation + 1
    assert result['complete_format'] is False
    with opened(target) as store:
        assert store.store_identity != identity
        assert int(store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0]) == 5
        pin = store.capture_pin()
        try:
            catalog = IdentityCatalog(store)
            a = catalog.read_owner_identity(pin, (NS, (1, 'craft')))
            b = catalog.read_owner_identity(pin, (NS, (2, 'craft')))
            try:
                inc = dict(a.occurrences)[(('field', 'provenance'),)]
                assert dict(b.occurrences)[(('field', 'provenance'),)] == inc
            finally:
                close(a.occurrences); close(b.occurrences)
            group = catalog.read_identity_group(pin, inc)
            try:
                assert (NS, (1, 'craft'), (('field', 'provenance'),)) in group.occurrences
                assert (NS, (2, 'craft'), (('field', 'provenance'),)) in group.occurrences
            finally:
                close(group.occurrences); close(group.links)
            for key in store.iter_keys(pin, PAGE_NAMESPACE):
                owner = catalog.read_owner_identity(pin, (PAGE_NAMESPACE, key))
                close(owner.occurrences)
            for backing in store.iter_keys(pin, DESCRIPTOR_NAMESPACE):
                kind = store.read_version(pin, DESCRIPTOR_NAMESPACE, backing, expected_record_schema=1).value[0]
                assert store.read_version(pin, DEPENDENCIES, backing, expected_record_schema=1).value == dependency_value(kind)
        finally:
            store.release_pin(pin)


@pytest.mark.parametrize('phase', ['after_private_copy', 'before_catalog_commit', 'after_catalog_commit', 'after_catalog_validation'])
def test_private_copy_fault_leaves_source_and_final_destination_untouched(tmp_path, monkeypatch, phase):
    source = legacy_lazy(tmp_path)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    mod = module()
    def fail(at, _path):
        if at == phase: raise OSError('private catalog copy fault')
    monkeypatch.setattr(mod, '_copy_phase', fail)
    with pytest.raises(OSError, match='catalog copy fault'):
        mod._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before
    assert not tuple(tmp_path.glob('.ate-catalog-copy-*'))


def test_competing_destination_is_not_overwritten(tmp_path, monkeypatch):
    source = legacy_lazy(tmp_path)
    target = tmp_path / 'copy.sqlite'
    mod = module()
    def race(at, _path):
        if at == 'before_publish': target.write_bytes(b'competing destination')
    monkeypatch.setattr(mod, '_copy_phase', race)
    with pytest.raises(FileExistsError):
        mod._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert target.read_bytes() == b'competing destination'


def test_same_source_and_destination_rejects_without_change(tmp_path):
    source = legacy_lazy(tmp_path)
    before = sha(source)
    with pytest.raises(ValueError, match='different paths'):
        module()._copy_with_checked_catalog(source, source, rules_id=RULES)
    assert sha(source) == before


def test_copied_aliases_continue_independently_and_reject_foreign_source_alias(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    from ate_sim.incremental_store import StoreError
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    source = legacy_lazy(tmp_path)
    target = tmp_path / 'copy.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    with open_lazy_world_session(source, rules_id=RULES) as original, open_bridge(target, rules_id=RULES) as copied:
        activate(copied)
        source_alias = original.skills[1, 'craft'].provenance
        alias = copied.skills[1, 'craft'].provenance
        assert alias is copied.skills[2, 'craft'].provenance and alias is not source_alias
        with pytest.raises(StoreError): copied.skills[1, 'craft'].provenance = source_alias
        alias.append(99)
        copied.save()
        assert list(source_alias) == list(range(32))
    with open_bridge(target, rules_id=RULES) as copied:
        activate(copied)
        assert copied.skills[1, 'craft'].provenance[-1] == 99
        assert copied.skills[1, 'craft'].provenance is copied.skills[2, 'craft'].provenance


def test_copy_keeps_original_collection_ordinals_and_high_water(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    source = legacy_lazy(tmp_path)
    with open_lazy_world_session(source, rules_id=RULES) as s:
        del s.skills[1, 'craft']
        s.save()
    with opened(source) as store:
        pin = store.capture_pin()
        try:
            expected = tuple(store.db.execute('SELECT typed_key,ordinal FROM lazy_order_versions '
                'WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                (NS, pin.captured_head, pin.captured_head)))
            state = store._namespace_state_at(NS, pin.captured_head)[:2]
            assert expected[0][1] > 0
        finally: store.release_pin(pin)
    target = tmp_path / 'copy.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    with opened(target) as store:
        pin = store.capture_pin()
        try:
            assert tuple(store.db.execute('SELECT typed_key,ordinal FROM lazy_order_versions '
                'WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                (NS, pin.captured_head, pin.captured_head))) == expected
            assert store._namespace_state_at(NS, pin.captured_head)[:2] == state
        finally: store.release_pin(pin)


def test_source_advance_after_capture_cannot_mix_copy_generations(tmp_path, monkeypatch):
    source = legacy_lazy(tmp_path)
    with opened(source) as store: captured = store.generation
    def advance(phase, _path):
        if phase == 'after_private_copy':
            with opened(source) as writer:
                pin = writer.capture_pin()
                token = 'c' * 32
                result = writer.commit(pin, commit_token=token,
                    changes=(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token)),),
                    version_changes=(), new_segments=(), metadata=writer.head_metadata())
                writer.release_pin(result.pin)
    monkeypatch.setattr(module(), '_copy_phase', advance)
    result = module()._copy_with_checked_catalog(source, tmp_path / 'copy.sqlite', rules_id=RULES)
    assert result['source_generation'] == captured
    assert result['generation'] == captured + 1
    with opened(source) as store: assert store.generation == captured + 1


def test_corrupt_source_fails_before_destination_publication(tmp_path):
    import sqlite3
    source = legacy_lazy(tmp_path)
    with sqlite3.connect(source) as db:
        db.execute('UPDATE lazy_record_versions SET payload_checksum=? WHERE namespace=?', ('0' * 64, PAGE_NAMESPACE))
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_catalog_bootstrap_cannot_relabel_an_already_staged_catalog(tmp_path):
    source = legacy_lazy(tmp_path)
    target = tmp_path / 'copy.sqlite'
    mod = module()
    mod._copy_with_checked_catalog(source, target, rules_id=RULES)
    before = sha(target)
    another = tmp_path / 'another.sqlite'
    with pytest.raises(StoreFormatError, match='genuine legacy'):
        mod._copy_with_checked_catalog(target, another, rules_id=RULES)
    assert not another.exists() and sha(target) == before


def test_counted_leaf_owners_are_checked_without_claiming_branch_ownership(tmp_path):
    from ate_sim.core import Household
    from ate_sim.persistence_lazy_sequence import NODE_NAMESPACE, DESCRIPTOR_NAMESPACE as COUNTED
    def configure(world): world.households[1] = Household(1, 1, members=list(range(1, 257)))
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'copy.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    with opened(target) as store:
        pin = store.capture_pin()
        try:
            catalog = IdentityCatalog(store)
            branches = leaves = 0
            for key in store.iter_keys(pin, NODE_NAMESPACE):
                value = store.read_version(pin, NODE_NAMESPACE, key, expected_record_schema=1).value
                if value[0] == 'leaf':
                    leaves += 1
                    close(catalog.read_owner_identity(pin, (NODE_NAMESPACE, key)).occurrences)
                else:
                    branches += 1
                    assert not store.contains_lazy_key(pin, OWNER_NAMESPACE, (NODE_NAMESPACE, key))
            assert branches and leaves
            for inc in store.iter_keys(pin, COUNTED):
                assert store.read_version(pin, DEPENDENCIES, inc, expected_record_schema=1).value == dependency_value('sequence')
        finally: store.release_pin(pin)


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_real_commit_fault_discards_only_private_copy_and_retry_succeeds(tmp_path, monkeypatch, phase):
    source = legacy_lazy(tmp_path)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    original = LazyRecordStore.commit
    def injected(store, *args, **kwargs):
        if store.path.name == 'destination.sqlite':
            def fail(at):
                if at == phase: raise OSError('catalog transaction fault')
            store._phase_hook = fail
        return original(store, *args, **kwargs)
    monkeypatch.setattr(LazyRecordStore, 'commit', injected)
    with pytest.raises(OSError, match='transaction fault'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before
    monkeypatch.setattr(LazyRecordStore, 'commit', original)
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert target.exists() and sha(source) == before


def test_copy_keeps_checked_immutable_event_segments(tmp_path):
    from ate_sim.core import Event, Layer
    from ate_sim.persistence_events import CHUNK_SIZE
    from ate_sim.event_log import EventLog
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    def configure(world):
        world.events = EventLog()
        for ident in range(1, CHUNK_SIZE + 1):
            world.events.append(Event(ident, 0, 'memory', Layer.SOCIETY, data={'value':ident}))
        world.event_ids.update(range(1, CHUNK_SIZE + 1))
        world.next_event = CHUNK_SIZE + 1
        world.events.seal_before(1)
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'copy.sqlite'
    with opened(source) as store: expected = tuple(store.db.execute('SELECT * FROM segments'))
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    with opened(target) as store: assert tuple(store.db.execute('SELECT * FROM segments')) == expected
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert s.world.events._disk_count == CHUNK_SIZE
        assert s.world.events[0].data['value'] == 1
        assert s.world.events[-1].data['value'] == CHUNK_SIZE


def test_private_catalog_copy_requires_an_explicit_bounded_authority_source(tmp_path):
    import sqlite3
    source = legacy_lazy(tmp_path)
    with sqlite3.connect(source) as db:
        db.execute("UPDATE store_metadata SET value='4' WHERE key='format_version'")
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreFormatError, match='bounded-authority'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_copy_rejects_dangling_root_history_reference_before_publication(tmp_path):
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.persistence_history_types import NAMESPACE as TYPES
    source = legacy_lazy(tmp_path)
    with opened(source) as store:
        pin = store.capture_pin()
        inc = store.read_version(pin, NS, (1, 'craft'), expected_record_schema=1).value.provenance.incarnation
        token = 'd' * 32
        result = store.commit(pin, commit_token=token,
            changes=(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token)),),
            version_changes=(VersionChange(DESCRIPTOR_NAMESPACE, inc, delete=True), VersionChange(TYPES, inc, delete=True)),
            new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    before = sha(source)
    target = tmp_path / 'copy.sqlite'
    with pytest.raises(StoreIntegrityError, match='reference'):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    assert not target.exists() and sha(source) == before


def test_copy_preserves_already_held_source_alias_and_excludes_unsaved_overlay(tmp_path):
    from ate_sim.persistence_lazy import open_lazy_world_session
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    source = legacy_lazy(tmp_path)
    target = tmp_path / 'copy.sqlite'
    with open_lazy_world_session(source, rules_id=RULES) as original:
        alias = original.skills[1, 'craft'].provenance
        alias.append(77)
        generation = original.pin.captured_head
        before = sha(source)
        module()._copy_with_checked_catalog(source, target, rules_id=RULES)
        assert sha(source) == before and original.pin.captured_head == generation
        assert original.skills[1, 'craft'].provenance is original.skills[2, 'craft'].provenance is alias
        assert alias[-1] == 77
        with open_bridge(target, rules_id=RULES) as copied:
            activate(copied)
            assert list(copied.skills[1, 'craft'].provenance) == list(range(32))


def test_copy_preserves_ordinary_query_memberships(tmp_path):
    from ate_sim.core import TradeRoute
    from ate_sim.incremental_store import Membership
    def configure(world): world.trade_routes[1, 2] = TradeRoute(1, 2)
    source = legacy_lazy(tmp_path, configure=configure)
    with opened(source) as store:
        pin = store.capture_pin()
        value = store.read_record('world.trade_routes', (1, 2))
        token = 'e' * 32
        result = store.commit(pin, commit_token=token,
            changes=(RecordChange('world.trade_routes', (1, 2), value, memberships=(Membership('endpoint', 1, 7),)),
                     RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token))),
            version_changes=(), new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
        expected = tuple(store.db.execute('SELECT namespace,index_name,index_value,record_key,ordinal FROM query_membership'))
        assert expected
    target = tmp_path / 'copy.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES)
    with opened(target) as store:
        assert tuple(store.db.execute('SELECT namespace,index_name,index_value,record_key,ordinal FROM query_membership')) == expected
