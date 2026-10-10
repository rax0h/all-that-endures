"""Actual World routing/publication against an explicitly staged catalog.

This fixture does not advertise capability6: ordinary format activation remains
the complete-copy converter's responsibility, not an implicit open migration.
"""
import pytest
from contextlib import contextmanager
from unittest.mock import patch
from dataclasses import replace

from ate_sim.core import World
from ate_sim.skills import SkillHistory
from ate_sim.incremental_store import RecordChange, Membership, StoreIntegrityError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange, IdentityOccurrenceChange
from ate_sim.persistence_lazy_families import FAMILIES
from ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta
from ate_sim.persistence_session import write_cold_snapshot, EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
from ate_sim.persistence_adapters import WorldCodec, SCHEMA

RULES = 'final-world-catalog-bridge'
NS = 'world.skills.skills'
PATH = (('field', 'provenance'),)


def converted_catalog(tmp_path, size=32, owners=2, *, configure_world=None, counted_households=False,
                      packed_actions=False):
    world = World(843000)
    history = list(range(size))
    for key in range(1, owners + 1):
        world.skills.skills[key, 'craft'] = SkillHistory(key, 'craft', provenance=history if key < 3 else [])
    if configure_world is not None:
        configure_world(world, history)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True,
                         counted_households=counted_households)
    with LazyRecordStore.open(target, codec=WorldCodec(identity_links_recorded=True), expected_simulation_schema=SCHEMA,
                              expected_rules_id=RULES) as store:
        pin = store.capture_pin()
        removals = tuple(RecordChange('world_identity_links', key, delete=True)
                        for key, _, _ in store.read_records('world_identity_links'))
        if packed_actions:
            from ate_sim.persistence_adapters import (PACKED_LIST_KEY, PACKED_LIST_KIND,
                PACKED_LIST_PAYLOAD, META)
            namespace = 'world.agency.actions'
            rows = tuple(store.read_records(namespace))
            assert all(type(key) is int for key, _, _ in rows)
            values = tuple(value for _ordinal, value in sorted(envelope for _key, envelope, _schema in rows))
            manifest = dict(store.read_record(META, 'manifest'))
            layout = dict(manifest['collections'])
            layout[namespace] = (PACKED_LIST_KIND, len(values), 0)
            manifest['collections'] = layout
            removals += tuple(RecordChange(namespace, key, delete=True) for key, _, _ in rows)
            removals += (RecordChange(namespace, PACKED_LIST_KEY, (0, (PACKED_LIST_PAYLOAD, values))),
                         RecordChange(META, 'manifest', manifest))
        # Only test setup uses two commits. The eventual copy converter must
        # stage this authority replacement atomically before publishing a file.
        pin = store.commit(pin, commit_token='a' * 32, changes=removals +
            (RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, 'a' * 32)),),
            version_changes=(), new_segments=(), metadata=store.head_metadata()).pin
        versions, ordinary = [], []
        for namespace, adapter in FAMILIES.items():
            if store._namespace_state_at(namespace, pin.captured_head) is not None:
                for key in store.iter_keys(pin, namespace):
                    row = store._visible_record_row(pin.captured_head, namespace, store.codec.encode(key))
                    value, schema, _, _, members = store._check_record_row(namespace, store.codec.encode(key), row, decode=True)
                    versions.append(VersionChange(namespace, key, value, record_schema=schema,
                        memberships=tuple(Membership(*member) for member in members)))
            else:
                ordinary.extend(RecordChange(namespace, key, value, record_schema=schema)
                    for key, value, schema in store.read_records(namespace))
        placements = tuple(IdentityOccurrenceChange(namespace, store.codec.decode(key), store.codec.decode(path), inc)
            for namespace, key, path, inc in store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
                'FROM lazy_identity_occurrence_versions WHERE valid_to IS NULL'))
        remapped = ()
        if packed_actions:
            old = tuple(p for p in placements if p.owner_namespace == 'world.agency.actions')
            new = tuple(IdentityOccurrenceChange(p.owner_namespace, PACKED_LIST_KEY,
                (('index', p.owner_key),) + p.occurrence_path, p.incarnation_id) for p in old)
            placements = tuple(p for p in placements if p.owner_namespace != 'world.agency.actions') + new
            remapped = tuple(IdentityOccurrenceChange(p.owner_namespace, p.owner_key, p.occurrence_path,
                delete=True) for p in old) + new
        allocator = store.read_identity_state(pin)
        delta = initial_catalog_delta(store.codec, versions, placements, ordinary_changes=ordinary,
            next_incarnation_id=allocator, generation=pin.captured_head + 1)
        from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
        from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as NESTED
        from ate_sim.persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCES
        dependencies = tuple(VersionChange(DEPENDENCIES, key, dependency_value(
            'sequence' if namespace == SEQUENCES else store.read_version(pin, namespace, key, expected_record_schema=1).value[0]))
            for namespace in (NESTED, SEQUENCES) for key in store.iter_keys(pin, namespace))
        result = store.commit(pin, commit_token='b' * 32, changes=tuple(ordinary) +
            (RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, 'b' * 32)),),
            version_changes=tuple(versions) + delta.decode(store.codec)[0] + dependencies, identity_changes=remapped,
            next_incarnation_id=allocator, new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    return target


@contextmanager
def open_bridge(target, *, rules_id):
    # Bypass just the legacy bootstrap reader: this file intentionally has no
    # ordinary P2C links. Do not pretend these tests verify capability6 open.
    from ate_sim.persistence_session import _validate_head_inventory
    def legacy_inventory(head, manifest, links, events):
        counts = dict(head.namespace_counts)
        counts['world_identity_links'] = (0, 0)
        _validate_head_inventory(replace(head, namespace_counts=counts), manifest, links, events)
    with patch('ate_sim.persistence_lazy._read_current_identity_links', return_value=()), \
         patch('ate_sim.persistence_lazy._validate_head_inventory', side_effect=legacy_inventory):
        session = open_lazy_world_session(target, rules_id=rules_id)
    with session:
        yield session


def activate(session):
    session._activate_checked_identity_catalog()
    return session._identity_coordinator


def _route_save_metrics(tmp_path, size):
    target = converted_catalog(tmp_path, size, owners=24)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        assert not dict.__contains__(session.skills, (2, 'craft'))
        session.store.reset_diagnostics()
        child.append(size)
        assert session.skills[2, 'craft'].provenance is child
        assert dict.__len__(session.skills) == 2
        assert coord.dirty_owners == {(NS, (1, 'craft')), (NS, (2, 'craft'))}
        read = session.store.read_version
        def checked_read(pin, namespace, key, **kwargs):
            if namespace == NS:
                assert key in {(1, 'craft'), (2, 'craft')}, 'unrelated owner archive was read'
            return read(pin, namespace, key, **kwargs)
        session.store.read_version = checked_read
        session._registry.live_bindings = lambda: pytest.fail('save inventoried the live registry')
        child._read_page = lambda *_: pytest.fail('compact save read historical member pages')
        commit = session.store.commit
        def checked_commit(pin, **arguments):
            assert session._pending_save.publication.coordinator_participant is not None
            headers = [c for c in arguments['version_changes'] if c.namespace == NS]
            assert {c.key for c in headers} == {(1, 'craft'), (2, 'craft')}
            assert all(c.value.provenance == child.storage_reference() for c in headers)
            assert not any(c.namespace == 'world_identity_links' for c in arguments['changes'])
            return commit(pin, **arguments)
        session.store.commit = checked_commit
        successor = session.save()
        assert coord.pin == session.pin and not coord.dirty_owners
        assert session.save() == successor
        assert session.store.diagnostics().payload_read_bytes < 32768
        metrics = session.store.diagnostics()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[-1] == size
        assert session.skills[1, 'craft'].provenance is session.skills[2, 'craft'].provenance
    return metrics


def test_actual_world_routes_cold_peer_and_forces_both_headers_at_paired_scales(tmp_path, record_property):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        result = _route_save_metrics(directory, size)
        metrics.append(result)
        record_property(f'H{size}_payload_reads', result.payload_reads)
        record_property(f'H{size}_payload_read_bytes', result.payload_read_bytes)
        record_property(f'H{size}_metadata_rows', result.metadata_rows)
    # The same affected closure does the same checked work. Compact witness
    # reads are counted as payload by diagnostics; an invented per-save ceiling
    # is not a substitute for proving archive-size independence.
    assert metrics[0].payload_reads == metrics[1].payload_reads
    assert metrics[0].metadata_rows == metrics[1].metadata_rows
    assert metrics[0].payload_writes == metrics[1].payload_writes


def test_actual_world_missing_cold_group_occurrence_rejects_before_edit(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',
            (NS, session.store.codec.encode((2, 'craft')), session.store.codec.encode(PATH)))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            child.append(99)
        assert len(child) == 32 and not child.pending_changes()


def test_actual_world_deleted_cold_owner_is_not_resurrected_by_retained_alias(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        del session.skills[2, 'craft']
        child.append(99)
        assert (2, 'craft') not in session.skills
        assert (NS, (2, 'craft')) not in coord.routes_for_mutation(child)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert (2, 'craft') not in session.skills
        assert session.skills[1, 'craft'].provenance[-1] == 99


def test_actual_world_replaced_child_routes_old_alias_only_to_remaining_peer(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        first = session.skills[1, 'craft']
        old = first.provenance
        first.provenance = [777]
        old.append(99)
        assert first.provenance == [777]
        assert session.skills[2, 'craft'].provenance is old
        assert coord.routes_for_mutation(old) == ((NS, (2, 'craft')),)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance == [777]
        assert session.skills[2, 'craft'].provenance[-1] == 99


def test_actual_world_owner_inventory_is_checked_before_binding(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',
            (NS, session.store.codec.encode((1, 'craft')), session.store.codec.encode(PATH)))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError, match='(identity|occurrence|incomplete)'):
            session.skills[1, 'craft']
        assert not session._registry.occurrences_for_owner(NS, (1, 'craft'))


def test_catalog_activation_rejects_existing_unsaved_family_edits(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        session.skills[1, 'craft'].level = .5
        from ate_sim.incremental_store import StoreConflictError
        with pytest.raises(StoreConflictError, match='clean'):
            activate(session)
        assert session._identity_coordinator is None


def test_world_preparation_failure_thaws_new_catalog_freeze_only(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        prepare, encode = coord.prepare_delta, session.store.codec.encode
        def fail_counts(value):
            if type(value) is dict and 'world_snapshot' in value and 'world_identity_links' in value:
                raise OSError('count capture failed')
            return encode(value)
        def freeze_then_fail(*args, **kwargs):
            delta = prepare(*args, **kwargs)
            session.store.codec.encode = fail_counts
            return delta
        coord.prepare_delta = freeze_then_fail
        with pytest.raises(OSError, match='count capture failed'):
            session._prepare_hybrid_save()
        session.store.codec.encode = encode
        coord.prepare_delta = prepare
        assert coord._prepared is None and coord.dirty_owners
        assert child[-1] == 99 and child.pending_changes()
        session.save()


def test_catalog_noop_save_has_no_archive_or_identity_work(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        session.save()
        assert not session.skills._dirty
        assert not coord.dirty_owners
        coord.catalog.read_owner_identity = lambda *_: pytest.fail('noop read owner identity')
        coord.catalog.read_identity_group = lambda *_: pytest.fail('noop read identity group')
        child._read_page = lambda *_: pytest.fail('noop read history')
        session.store.reset_diagnostics()
        generation = session.pin.captured_head
        assert session.save() == generation
        diagnostics = session.store.diagnostics()
        assert diagnostics.payload_writes == 0 and diagnostics.payload_reads == 3


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_actual_world_catalog_rollback_and_lost_ack_recover_exactly(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        def fail(at):
            if at == phase:
                raise OSError('catalog bridge fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='catalog bridge fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            assert coord._prepared is None
            child.append(100)
            session.save()
        assert not coord.dirty_owners and coord.pin == session.pin
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[-1] == (100 if phase == 'before_commit' else 99)
