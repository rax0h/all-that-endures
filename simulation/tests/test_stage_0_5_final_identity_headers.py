"""Identity copy checks encode compact headers, never history payloads."""
from dataclasses import replace

import pytest

from simulation.ate_sim.core import Settlement
from simulation.ate_sim.incremental_store import StoreConflictError
from simulation.ate_sim.persistence_lazy_families import FAMILIES
from simulation.ate_sim.persistence_lazy_nested_history import HistoryReference
from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence
from simulation.tests.test_stage_0_5_final_sequence_compat import store_at, native
from simulation.tests.test_persistence_lazy_store import metadata


@pytest.mark.parametrize('history', [1000, 10000])
def test_identity_header_comparison_never_reads_sequence_history(tmp_path, history):
    with store_at(tmp_path / 'headers.sqlite') as store:
        seq = native(store, range(history))
        header = Settlement(1, 0, 0, households=seq)
        expected = replace(header, households=HistoryReference('sequence', 1))
        seq._nread = lambda *args: pytest.fail('identity comparison traversed history')
        before = store.diagnostics().payload_reads
        actual = FAMILIES['world.settlements'].identity_payload_bytes(store, seq._pin, header)
        assert actual == store.codec.encode(expected)
        assert store.diagnostics().payload_reads == before
        assert len(actual) < 4096


def test_identity_header_rejects_a_foreign_history_lease(tmp_path):
    with store_at(tmp_path / 'left.sqlite') as left, store_at(tmp_path / 'right.sqlite') as right:
        seq = native(left, [1, 2, 3])
        header = Settlement(1, 0, 0, households=seq)
        with pytest.raises(StoreConflictError, match='history.*lease'):
            FAMILIES['world.settlements'].identity_payload_bytes(right, right.capture_pin(), header)


def test_identity_header_rejects_a_different_generation_lease(tmp_path):
    with store_at(tmp_path / 'generations.sqlite') as store:
        older = store.capture_pin()
        seq = native(store, [1, 2, 3])
        header = Settlement(1, 0, 0, households=seq)
        with pytest.raises(StoreConflictError, match='history.*lease'):
            FAMILIES['world.settlements'].identity_payload_bytes(store, older, header)


def test_compact_header_preserves_equal_distinct_sequence_incarnations(tmp_path):
    with store_at(tmp_path / 'distinct.sqlite') as store:
        first = native(store, [True, 1., 2])
        second = LazyOrderedSequence(store, first._pin, 2,
                                     initial_values=[True, 1., 2], value_mode='native')
        adapter = FAMILIES['world.settlements']
        assert adapter.identity_payload_bytes(store, first._pin, first) != adapter.identity_payload_bytes(store, first._pin, second)
        assert adapter.identity_payload_bytes(store, first._pin, first) == store.codec.encode(first.storage_reference())


@pytest.mark.parametrize('bad_peer', [False, True])
def test_coordinator_compares_compact_history_placements_before_installing(tmp_path, bad_peer):
    from simulation.ate_sim.incremental_store import StoreIntegrityError
    from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId, Occurrence
    from simulation.ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta
    from simulation.ate_sim.persistence_lazy_identity_coordinator import IdentityCoordinator
    from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
    namespace, path = 'world.settlements', (('field', 'households'),)
    with store_at(tmp_path / 'coordinator.sqlite') as store:
        pin = store.capture_pin()
        seq = LazyOrderedSequence(store, pin, 1, initial_values=range(1000), value_mode='native')
        prepared = seq.prepare_delta()
        versions = tuple(VersionChange(namespace, key, Settlement(key, 0, 0,
            households=HistoryReference('sequence', 2 if bad_peer and key == 2 else 1)))
            for key in (1, 2))
        placements = tuple(IdentityOccurrenceChange(namespace, key, path, 1) for key in (1, 2))
        catalog = initial_catalog_delta(store.codec, versions, placements,
                                        next_incarnation_id=2, generation=1)
        pin = store.commit(pin, commit_token='initial',
            version_changes=versions + prepared.decode(store.codec)[0] + catalog.decode(store.codec)[0],
            identity_changes=placements, next_incarnation_id=2, changes=(), new_segments=(),
            metadata=metadata(1, (namespace, 'world_identity_links'))).pin
        seq.accept_delta(prepared, pin)
        registry = LazyIdentityRegistry(store.store_identity, next_incarnation=2)
        registry.bind(seq, Occurrence(namespace, 1, path),
                      incarnation=IncarnationId(store.store_identity, 1))
        owners, dirty, installed = {}, set(), []
        def load(owner):
            if owner not in owners:
                owners[owner] = store.read_version(pin, *owner, expected_record_schema=1).value
            return owners[owner]
        def install(owner, relative, value):
            installed.append(owner)
            object.__setattr__(owners[owner], relative[0][1], value)
        coord = IdentityCoordinator(store, pin, registry, load_owner=load,
            resolve_path=lambda owner, relative: getattr(owner, relative[0][1]),
            install_path=install, mark_dirty=dirty.add, preflight=lambda: None,
            encode_placement=lambda owner, relative, value:
                FAMILIES[owner[0]].identity_payload_bytes(store, pin, value))
        seq._nread = lambda *args: pytest.fail('coordinator traversed history')
        if bad_peer:
            with pytest.raises(StoreIntegrityError, match='copies disagree'):
                coord.routes_for_mutation(seq)
            assert not installed and not dirty
        else:
            assert set(coord.routes_for_mutation(seq)) == {(namespace, 1), (namespace, 2)}
            assert owners[namespace, 1].households is seq
            assert owners[namespace, 2].households is seq
            assert dirty == {(namespace, 1), (namespace, 2)}
