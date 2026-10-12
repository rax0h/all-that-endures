"""An Event-ID graph edge references the one existing World authority."""
import importlib
import importlib.util
import pytest
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.incremental_store import CodecError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import stored_value, ENTRY_NAMESPACE, HistoryReference
from ate_sim.persistence_record_headers import stored_record_field, record_header, record_reference_placements
from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from ate_sim.persistence_frozen_snapshots import immutable_snapshot_value
from ate_sim.agency import ActionRecord


def reference_module():
    name = 'ate_sim.persistence_event_id_reference'
    assert importlib.util.find_spec(name) is not None, 'typed Event-ID graph reference is missing'
    return importlib.import_module(name)


def test_event_id_reference_is_a_closed_codec_value_and_physical_child_edge():
    module = reference_module()
    ref = module.EventIdReference(7)
    codec = WorldCodec(identity_links_recorded=True)
    assert codec.decode(codec.encode(ref)) == ref
    assert stored_value(ref) and stored_record_field(ref)
    assert not immutable_snapshot_value(ref)
    value = (0, 'ids', (ref, HistoryReference('list', 8)))
    from ate_sim.incremental_store import Membership
    source = VersionChange(ENTRY_NAMESPACE, (3, 'ids'), value,
        memberships=(Membership('incarnation', 3, 0),))
    adapter = AUXILIARY_OWNER_FAMILIES[ENTRY_NAMESPACE]
    adapter.validate_source(source, 'lazy', codec)
    assert adapter.reference_placements(value) == (((('index', 2), ('index', 0)), 7),
                                                  ((('index', 2), ('index', 1)), 8))
    record = ActionRecord(1, 2, 'work', 'wealth', .5)
    header = record_header(record, values=(1, 2, 'work', 'wealth', .5, ref))
    assert record_reference_placements(header) == (((('field', 'event_id'),), 7),)


@pytest.mark.parametrize('bad', [True, False, 0, -1, 1.0, '1', None])
def test_event_id_reference_rejects_nonpositive_or_noninteger_incarnation(bad):
    with pytest.raises(ValueError): reference_module().EventIdReference(bad)


@pytest.mark.parametrize('node', [['typed-event-id-authority/v1'],
    ['typed-event-id-authority/v1', True], ['typed-event-id-authority/v1', 0],
    ['typed-event-id-authority/v1', 1, 2]])
def test_event_id_reference_codec_rejects_malformed_tag(node):
    import json
    reference_module()
    with pytest.raises(CodecError): WorldCodec().decode(json.dumps(node).encode())


def test_explicit_event_graph_copy_keeps_one_event_id_authority_and_literal_marker(tmp_path):
    from ate_sim.core import Event, Layer
    from ate_sim.persistence_event_ids import AUTHORITY_REFERENCE
    from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, sha, RULES
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    def configure(world):
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY,
            data={'ids': world.event_ids, 'literal': AUTHORITY_REFERENCE}))
        world.event_ids.add(1); world.next_event = 2
    source = legacy_lazy(tmp_path, configure=configure)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        ids = session.world.event_ids
        assert session.world.events[0].data['ids'] is ids
        assert session.world.events[0].data['literal'] == AUTHORITY_REFERENCE
        ids.add(2)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['ids'] is session.world.event_ids
        assert 2 in session.world.events[0].data['ids']


def test_native_recursive_admission_borrows_same_facade_without_copying_members(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        ids = session.world.event_ids
        ids.add(1)
        record = ActionRecord(1, 2, 'work', 'wealth', .5, event_id=ids)
        session.skills[1, 'craft'].provenance = [ids, {'ids': ids}, record]
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1]['ids'] is root[2].event_id is ids
        ids.remove(1); ids.add(99)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1]['ids'] is root[2].event_id is session.world.event_ids
        assert 99 in root[0] and 1 not in root[0]


def test_graph_copy_keeps_existing_soul_authority_marker_compatibility(tmp_path):
    from ate_sim.core import Event, Layer
    from ate_sim.metaphysics import SoulState
    from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, RULES
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    def configure(world):
        world.metaphysics.souls[1] = SoulState(1, authorities=world.event_ids)
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'ids': world.event_ids}))
        world.event_ids.add(1); world.next_event = 2
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.souls[1].authorities is session.world.event_ids
        assert session.world.events[0].data['ids'] is session.souls[1].authorities
        session.world.event_ids.add(2)
        session.save()


def test_event_id_graph_detach_uses_one_portable_native_set(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        ids = session.world.event_ids
        ids.update((1, 2))
        session.skills[1, 'craft'].provenance = [ids, {'ids': ids}]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        plain = session.detach(materialize_history=True)
    root = plain.skills.skills[1, 'craft'].provenance
    assert type(root[0]) is set and root[0] == {1, 2}
    assert root[0] is root[1]['ids'] is plain.event_ids


def test_native_event_id_copy_rejects_foreign_publisher_before_member_visits(tmp_path):
    from ate_sim.incremental_store import StoreError
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES
    paths = []
    for name in ('left', 'right'):
        directory = tmp_path / name; directory.mkdir()
        paths.append(converted_catalog(directory))
    with open_bridge(paths[0], rules_id=RULES) as left, open_bridge(paths[1], rules_id=RULES) as right:
        activate(left); activate(right)
        ids = right.world.event_ids
        ids.update(range(1, 1001))
        before = ids.diagnostics()['member_visits']
        with pytest.raises(StoreError): left._recursive_histories.copy_input(ids)
        assert ids.diagnostics()['member_visits'] == before


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_event_id_graph_alias_and_exception_backings_resolve_one_save(tmp_path, phase):
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES
    def configure(world, _history): world.event_ids = set(range(1, 1001))
    target = converted_catalog(tmp_path, configure_world=configure)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        ids = session.world.event_ids
        session.skills[1, 'craft'].provenance = [{'ids': ids}]
        session.save()
        ids.remove(2); ids.add(2000)
        def fail(at):
            if at == phase: raise OSError('Event-ID graph publication fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='Event-ID graph publication fault'): session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save(); session.save()
        assert session.skills[1, 'craft'].provenance[0]['ids'] is ids
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        ids = session.skills[1, 'craft'].provenance[0]['ids']
        assert ids is session.world.event_ids and 2 not in ids and 2000 in ids


def test_checked_current_copy_keeps_physical_event_id_reference(tmp_path):
    from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, RULES
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    source = legacy_lazy(tmp_path)
    normalized = tmp_path / 'normalized.sqlite'
    module()._copy_with_checked_catalog(source, normalized, rules_id=RULES, normalize_events=True)
    with open_bridge(normalized, rules_id=RULES) as session:
        activate(session)
        session.world.event_ids.add(1)
        session.skills[1, 'craft'].provenance = [session.world.event_ids]
        session.save()
    copied = tmp_path / 'copied.sqlite'
    module()._copy_current_checked_catalog(normalized, copied, rules_id=RULES)
    with open_bridge(copied, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[0] is session.world.event_ids
        assert 1 in session.skills[1, 'craft'].provenance[0]


def test_event_id_reference_point_publish_has_fixed_history_work(tmp_path, record_property):
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size); directory.mkdir()
        def configure(world, _history): world.event_ids = set(range(1, size + 1))
        target = converted_catalog(directory, size=size, configure_world=configure)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            ids = session.world.event_ids
            session.skills[1, 'craft'].provenance = [ids, {'ids': ids}]
            session.save()
            session._registry.live_bindings = lambda: pytest.fail('Event-ID graph publish inventoried registry')
            session._eager_tracker._contains_identity = lambda *_: pytest.fail('Event-ID graph publish searched owners')
            session.store.reset_diagnostics()
            ids.remove(2); ids.add(size + 99)
            session.save()
            now = session.store.diagnostics()
            metric = now.payload_reads, now.payload_writes, now.metadata_rows
            metrics.append(metric)
            for label, count in zip(('payload_reads', 'payload_writes', 'metadata_rows'), metric):
                record_property(f'H{size}_{label}', count)
            assert ids.diagnostics()['member_visits'] == 0
    assert metrics[0] == metrics[1]


@pytest.mark.parametrize('root_ids,backings', [({8}, ()), ({7}, ('map',))])
def test_copy_reference_scrub_rejects_wrong_or_competing_event_id_authority(root_ids, backings):
    from ate_sim.persistence_catalog_copy import _check_reference_targets
    from ate_sim.persistence_history_dependencies import NAMESPACE, dependency_value
    from ate_sim.incremental_store import StoreIntegrityError
    ref = reference_module().EventIdReference(7)
    rows = tuple(VersionChange(NAMESPACE, 7, dependency_value(kind)) for kind in backings)
    with pytest.raises(StoreIntegrityError):
        _check_reference_targets((ref,), rows, event_id_incarnations=root_ids)


def test_reference_scrub_preserves_unused_legacy_facade_snapshot_without_typed_edge():
    from ate_sim.persistence_catalog_copy import _check_reference_targets
    from ate_sim.persistence_history_dependencies import NAMESPACE, dependency_value
    rows = (VersionChange(NAMESPACE, 7, dependency_value('set')),)
    _check_reference_targets((('event-ids-range/v1', 10),), rows, event_id_incarnations={7})


def test_event_id_alias_copy_rejects_invalid_compact_root_before_publish(tmp_path):
    from ate_sim.core import Event, Layer
    from ate_sim.incremental_store import RecordChange, StoreError
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, opened, module, sha, RULES
    def configure(world):
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'ids': world.event_ids}))
        world.event_ids.add(1); world.next_event = 2
    source = legacy_lazy(tmp_path, configure=configure)
    with opened(source) as store:
        pin = store.capture_pin(); token = 'f' * 32
        result = store.commit(pin, commit_token=token, changes=(
            RecordChange('world.event_ids', 0, (0, ('event-ids-range/v1', True))),
            RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token))),
            version_changes=(), new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    before = sha(source)
    target = tmp_path / 'normalized.sqlite'
    with pytest.raises(StoreError):
        module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_events=True)
    assert sha(source) == before and not target.exists()


def test_checked_current_copy_rejects_invalid_facade_with_valid_catalog_witness(tmp_path):
    from dataclasses import replace
    from ate_sim.incremental_store import RecordChange, StoreError
    from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
    from ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta
    from ate_sim.persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, opened, module, sha, RULES
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    source = legacy_lazy(tmp_path)
    checked = tmp_path / 'checked.sqlite'
    mod = module()
    mod._copy_with_checked_catalog(source, checked, rules_id=RULES, normalize_events=True)
    with open_bridge(checked, rules_id=RULES) as session:
        activate(session)
        session.world.event_ids.add(1)
        session.skills[1, 'craft'].provenance = [session.world.event_ids]
        session.save()
    with opened(checked) as store:
        pin = store.capture_pin()
        versions, ordinary = mod._owner_sources(store, pin)
        changed = next(c for c in ordinary if (c.namespace, c.key) == ('world.event_ids', 0))
        changed = replace(changed, value=(changed.value[0], ('event-ids-range/v1', True)))
        ordinary = tuple(changed if (c.namespace, c.key) == ('world.event_ids', 0) else c for c in ordinary)
        placements = tuple(IdentityOccurrenceChange(ns, store.codec.decode(key), store.codec.decode(path), inc)
            for ns, key, path, inc in store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
                'FROM lazy_identity_occurrence_versions WHERE valid_to IS NULL'))
        delta = initial_catalog_delta(store.codec, versions, placements, ordinary_changes=ordinary,
            next_incarnation_id=store.read_identity_state(pin), generation=pin.captured_head + 1)
        token = 'd' * 32
        result = store.commit(pin, commit_token=token, changes=ordinary + (
            RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token)),),
            version_changes=tuple(versions) + delta.decode(store.codec)[0], new_segments=(), metadata=store.head_metadata())
        store.release_pin(result.pin)
    before = sha(checked)
    destination = tmp_path / 'copied.sqlite'
    with pytest.raises(StoreError, match='Event-ID.*authority'):
        mod._copy_current_checked_catalog(checked, destination, rules_id=RULES)
    assert sha(checked) == before and not destination.exists()
