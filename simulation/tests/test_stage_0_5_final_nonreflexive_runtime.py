"""One registry preserves native atom sharing, input D and publisher recovery."""
import gc
import pytest

from ate_sim.incremental_store import StoreError
from ate_sim.persistence_nonreflexive_keys import NAMESPACE as ATOMS
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    RULES, activate, converted_catalog, open_bridge,
)


def test_one_nan_is_shared_by_map_key_value_ref_and_frozenset_after_reopen(tmp_path):
    target = converted_catalog(tmp_path)
    from ate_sim.core import Ref
    nan = float('nan')
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{nan: nan}, Ref('key', nan), frozenset((nan,))]
        s.save()
        assert s.store.namespace_size(s.pin, ATOMS) == 1
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        values = s.skills[1, 'craft'].provenance
        key = next(iter(values[0]))
        assert values[0][key] is key is values[1].id is next(iter(values[2]))
        values[0]._clear_cache()
        assert values[0][key] is key


@pytest.mark.parametrize('kind', ['map', 'set'])
def test_unpublished_nan_insert_remove_preserves_native_semantics(tmp_path, kind):
    target = converted_catalog(tmp_path)
    key = float('nan')
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{} if kind == 'map' else set()]
        history = s.skills[1, 'craft'].provenance[0]
        s.save()
        if kind == 'map':
            history[key] = key
            assert history.pop(key) is key
        else:
            history.add(key)
            history.remove(key)
        assert len(history) == 0 and key not in history
        s.save()
        assert len(history) == 0


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_nan_input_and_sharing_survive_frozen_save_recovery(tmp_path, phase):
    target = converted_catalog(tmp_path)
    key = float('nan')
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{key: key}]
        generation = s.store.generation
        def fail(at):
            if at == phase:
                raise OSError('nan-fault')
        s.store._phase_hook = fail
        with pytest.raises(OSError, match='nan-fault'):
            s.save()
        s.store._phase_hook = lambda _: None
        s.resolve_save()
        if phase == 'before_commit':
            s.save()
        assert s.store.generation == generation + 1
        history = s.skills[1, 'craft'].provenance[0]
        assert next(iter(history)) is history[key] is key
        assert s.save() == generation + 1
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        history = s.skills[1, 'craft'].provenance[0]
        restored = next(iter(history))
        assert history[restored] is restored


def test_invalid_map_value_rejects_before_nan_allocation_or_entry_mutation(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{}]
        s.save()
        history = s.skills[1, 'craft'].provenance[0]
        before = s._registry.next_incarnation
        with pytest.raises(TypeError):
            history[float('nan')] = object()
        assert len(history) == 0 and s._registry.next_incarnation == before


def test_unheld_nan_sources_release_roots_after_acknowledgement(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{float('nan'): 3}]
        s.save()
        gc.collect()
        s._recursive_histories.collect_source_memos()
        assert s._registry.diagnostics()['strong_object_roots'] == 0
        history = s.skills[1, 'craft'].provenance[0]
        held = next(iter(history))
        s._recursive_histories.collect_source_memos()
        assert held in history
        history._clear_cache()
        del held
        gc.collect()
        s._recursive_histories.collect_source_memos()
        assert s._registry.diagnostics()['strong_object_roots'] == 0


def test_held_nan_lookup_rejects_closed_session(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{float('nan'): 3}]
        s.save()
        history = s.skills[1, 'craft'].provenance[0]
        held = next(iter(history))
    with pytest.raises(StoreError):
        history[held]


def test_nan_atom_cannot_resolve_to_a_live_container_incarnation(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        history = s.skills[1, 'craft'].provenance
        with pytest.raises(StoreIntegrityError, match='NaN.*canonical'):
            s._recursive_histories.load_nan(NonreflexiveKeyReference(history._incarnation))


def test_frozen_nan_snapshot_certification_survives_reopen(tmp_path):
    from ate_sim.core import Event, Layer
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        snapshot = Event(17, 0, 'snapshot', Layer.SOCIETY, data={'value': float('nan')})
        snapshot.seal()
        s.skills[1, 'craft'].provenance = [snapshot]
        stored = s.skills[1, 'craft'].provenance[0]
        assert stored.data._deep_immutable
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert s.skills[1, 'craft'].provenance[0].data._deep_immutable


def test_nan_local_edit_cost_is_independent_of_unrelated_history(tmp_path, record_property):
    from simulation.tests.test_stage_0_5_final_nonreflexive_copy import source_with_atoms, RULES as COPY_RULES
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = source_with_atoms(directory, size=size)
        with open_bridge(target, rules_id=COPY_RULES) as s:
            activate(s)
            root = s.skills[1, 'craft'].provenance
            child = root[0]
            held_keys = tuple(child)
            held_set = root[1]
            previous = s.skills[2, 'craft'].provenance
            key = held_keys[0]
            assert child[key] is key is next(iter(held_set))
            child._clear_cache()
            s.store.reset_diagnostics()
            child[key] = 9
            s.save()
            measured = s.store.diagnostics()
            metrics.append(measured)
            record_property(f'H{size}_nan_edit', repr(measured))
            s.store.reset_diagnostics()
            read_versions = s.store.read_version
            read_records = s.store.read_records
            def forbidden_version(*_args, **_kwargs):
                pytest.fail('no-op save read a historical backing payload')
            def metadata_only(namespace, **kwargs):
                assert namespace == 'world_event_storage'
                return read_records(namespace, **kwargs)
            s.store.read_version = forbidden_version
            s.store.read_records = metadata_only
            assert s.save() == s.pin.captured_head
            noop = s.store.diagnostics()
            assert noop.payload_writes == 0
            assert noop.payload_reads == 3  # Existing fixed event-storage metadata.
            record_property(f'H{size}_nan_noop', repr(noop))
            s.store.read_version = read_versions
            s.store.read_records = read_records
    assert metrics[0].payload_reads == metrics[1].payload_reads
    assert metrics[0].payload_writes == metrics[1].payload_writes
    assert metrics[0].metadata_rows == metrics[1].metadata_rows
    assert abs(metrics[0].payload_read_bytes - metrics[1].payload_read_bytes) < 128
    assert abs(metrics[0].payload_write_bytes - metrics[1].payload_write_bytes) < 128


def test_cancelled_unheld_nan_input_does_not_leak_conditional_roots(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.skills[1, 'craft'].provenance = [{}]
        s.save()
        history = s.skills[1, 'craft'].provenance[0]
        key = float('nan')
        history[key] = 3
        del history[key]
        del key
        s.save()
        gc.collect()
        s._recursive_histories.collect_source_memos()
        assert s._registry.diagnostics()['strong_object_roots'] == 0


def test_cancelled_held_nan_can_be_reattached_after_an_unrelated_save(tmp_path):
    from simulation.tests.test_stage_0_5_final_nonreflexive_copy import source_with_atoms, RULES as COPY_RULES
    from ate_sim.persistence_catalog_copy import _copy_current_checked_catalog
    source = source_with_atoms(tmp_path)
    with open_bridge(source, rules_id=COPY_RULES) as s:
        activate(s)
        history = s.skills[1, 'craft'].provenance[0]
        key = float('nan')
        history[key] = 3
        del history[key]
        s.skills[1, 'craft'].level += .1
        s.save()
        # No dependency may claim a body that was never published.
        _copy_current_checked_catalog(source, tmp_path / 'cancelled.sqlite', rules_id=COPY_RULES)
        history[key] = key
        s.save()
        assert history[key] is key
    _copy_current_checked_catalog(source, tmp_path / 'reattached.sqlite', rules_id=COPY_RULES)


def test_direct_soul_map_and_set_admission_share_native_nan_identity(tmp_path):
    from ate_sim.metaphysics import SoulState
    def configure(world, _history):
        world.metaphysics.souls[1] = SoulState(1)
    target = converted_catalog(tmp_path, configure_world=configure)
    a, b = float('nan'), float('nan')
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        soul = s.souls[1]
        soul.marks = {a, b}
        soul.cosmic_links = {a: a, b: b}
        assert len(soul.marks) == len(soul.cosmic_links) == 2
        assert soul.cosmic_links[a] is a
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        soul = s.souls[1]
        keys = list(soul.cosmic_links)
        assert len(keys) == len(soul.marks) == 2
        assert all(key in soul.marks and soul.cosmic_links[key] is key for key in keys)


def test_nan_value_replacement_then_reversion_restores_checked_sharing(tmp_path):
    from simulation.tests.test_stage_0_5_final_nonreflexive_copy import source_with_atoms, RULES as COPY_RULES
    from ate_sim.persistence_catalog_copy import _copy_current_checked_catalog
    source = source_with_atoms(tmp_path)
    with open_bridge(source, rules_id=COPY_RULES) as s:
        activate(s)
        history = s.skills[1, 'craft'].provenance[0]
        keys = tuple(history)
        key = keys[0]
        history[key] = 9
        history[key] = key
        s.save()
        assert history[key] is key
    _copy_current_checked_catalog(source, tmp_path / 'reverted.sqlite', rules_id=COPY_RULES)
    with open_bridge(source, rules_id=COPY_RULES) as s:
        activate(s)
        history = s.skills[1, 'craft'].provenance[0]
        key = next(iter(history))
        assert history[key] is key
