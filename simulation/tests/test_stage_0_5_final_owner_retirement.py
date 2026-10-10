"""Owner retirement uses checked metadata, never detached child payloads."""
import pytest

from simulation.ate_sim.incremental_store import StoreConflictError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId, Occurrence
from simulation.ate_sim.persistence_lazy_identity_catalog import IdentityCatalog, initial_catalog_delta
from simulation.ate_sim.persistence_lazy_identity_coordinator import IdentityCoordinator
from simulation.ate_sim.persistence_lazy_spill import CheckedSpool
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata

from dataclasses import dataclass


@dataclass
class Box:
    value: int


NS = 'world.households'
PATH = (('field', 'members'),)


def fixture(store, count=2):
    store.codec.register_record('RetirementBox', Box)
    versions = tuple(VersionChange(NS, k, {'members': Box(7)}) for k in range(1, count + 1))
    placements = tuple(IdentityOccurrenceChange(NS, k, PATH, 1) for k in range(1, count + 1))
    delta = initial_catalog_delta(store.codec, versions, placements,
                                  next_incarnation_id=2, generation=1)
    return store.commit(store.capture_pin(), commit_token='initial',
        version_changes=versions + delta.decode(store.codec)[0], changes=(),
        new_segments=(), identity_changes=placements, next_incarnation_id=2,
        metadata=metadata(1, (NS, 'world_identity_links'))).pin


def coordinator(store, pin):
    registry = LazyIdentityRegistry(store.store_identity, next_incarnation=2)
    dirty, owners = set(), {}
    def load(owner):
        if owner not in owners:
            owners[owner] = store.read_version(instance.pin, *owner, expected_record_schema=1).value
        return owners[owner]
    instance = IdentityCoordinator(store, pin, registry, load_owner=load,
        resolve_path=lambda value, path: value['members'],
        install_path=lambda owner, path, value: owners[owner].__setitem__('members', value),
        mark_dirty=dirty.add, preflight=lambda: None)
    return instance, registry, dirty, owners, load


def test_owner_retirement_overlays_replacement_and_never_loads_a_retired_owner(tmp_path):
    with make_store(tmp_path / 'retire.sqlite') as store:
        pin = fixture(store)
        old = store.capture_pin()
        coord, registry, dirty, owners, load = coordinator(store, pin)
        original = load((NS, 1))['members']
        registry.bind(original, Occurrence(NS, 1, PATH),
                      incarnation=IncarnationId(store.store_identity, 1))
        replacement = Box(8)
        coord.replace_placement((NS, 1), PATH, replacement)
        coord.load_owner = lambda owner: pytest.fail('retired owner payload loaded')
        coord.retire_owner((NS, 1))
        coord.retire_owner((NS, 2))
        assert coord.routes_for_mutation(original) == ()
        assert coord.routes_for_mutation(replacement) == ()
        assert registry.incarnation_for_occurrence(Occurrence(NS, 1, PATH)) is None
        assert dirty == {(NS, 1), (NS, 2)}
        payloads = tuple(VersionChange(NS, key, delete=True) for key in (1, 2))
        prepared = coord.prepare_delta(payloads)
        versions, ordinary, placements = prepared.decode(store.codec)
        successor = store.commit(pin, commit_token='retire',
            version_changes=payloads + versions, changes=ordinary, new_segments=(),
            identity_changes=placements, next_incarnation_id=registry.next_incarnation,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        coord.accept_delta(prepared, successor)
        assert store.read_identity_group(successor, 1).occurrences == ()
        assert len(store.read_identity_group(old, 1).occurrences) == 2
        assert not coord.dirty_owners and not coord.placement_overlay


def test_corrupt_owner_inventory_fails_before_any_retirement_overlay(tmp_path):
    with make_store(tmp_path / 'corrupt.sqlite') as store:
        pin = fixture(store)
        coord, registry, dirty, owners, load = coordinator(store, pin)
        store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_key=?',
                         (store.codec.encode(1),))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            coord.retire_owner((NS, 1))
        assert not dirty and not coord.placement_overlay


def test_frozen_retirement_is_rejected_before_metadata_reads(tmp_path):
    with make_store(tmp_path / 'frozen.sqlite') as store:
        pin = fixture(store)
        coord, registry, dirty, owners, load = coordinator(store, pin)
        coord.prepare_delta((VersionChange(NS, 1, {'members': Box(7)}),))
        before = store.diagnostics()
        with pytest.raises(StoreConflictError, match='frozen'):
            coord.retire_owner((NS, 1))
        assert store.diagnostics() == before
        assert not dirty and not coord.placement_overlay


def test_long_owner_inventory_spills_without_materializing_compatibility_api(tmp_path):
    with make_store(tmp_path / 'long-owner.sqlite') as store:
        store.codec.register_record('RetirementBox', Box)
        paths = tuple((('key', key),) for key in range(100))
        versions = (VersionChange(NS, 1, {'members': Box(7)}),)
        placements = tuple(IdentityOccurrenceChange(NS, 1, path, 1) for path in paths)
        delta = initial_catalog_delta(store.codec, versions, placements,
                                     next_incarnation_id=2, generation=1)
        pin = store.commit(store.capture_pin(), commit_token='initial',
            version_changes=versions + delta.decode(store.codec)[0], changes=(), new_segments=(),
            identity_changes=placements, next_incarnation_id=2,
            metadata=metadata(1, (NS, 'world_identity_links'))).pin
        store.identity_occurrences_for_owner = lambda *args: pytest.fail('materialized owner inventory')
        catalog = IdentityCatalog(store, occurrence_limit=8, byte_limit=4096)
        checked = catalog.read_owner_identity(pin, (NS, 1))
        assert isinstance(checked.occurrences, CheckedSpool)
        assert len(checked.occurrences) == 100
        assert set(checked.occurrences) == {(path, 1) for path in paths}
        path = checked.occurrences.path
        checked.occurrences.close()
        from pathlib import Path
        assert not Path(path).exists()


def test_later_corrupt_group_does_not_detach_an_earlier_live_placement(tmp_path):
    from simulation.ate_sim.persistence_lazy_identity_catalog import GROUP_NAMESPACE
    with make_store(tmp_path / 'later-group.sqlite') as store:
        store.codec.register_record('RetirementBox', Box)
        paths = ((('key', 'a'),), (('key', 'b'),))
        versions = (VersionChange(NS, 1, {'a': Box(1), 'b': Box(2)}),)
        placements = tuple(IdentityOccurrenceChange(NS, 1, path, inc)
                           for inc, path in enumerate(paths, 1))
        delta = initial_catalog_delta(store.codec, versions, placements,
                                     next_incarnation_id=3, generation=1)
        pin = store.commit(store.capture_pin(), commit_token='initial',
            version_changes=versions + delta.decode(store.codec)[0], changes=(),
            new_segments=(), identity_changes=placements, next_incarnation_id=3,
            metadata=metadata(1, (NS, 'world_identity_links'))).pin
        coord, registry, dirty, owners, load = coordinator(store, pin)
        live = Box(1)
        occurrence = Occurrence(NS, 1, paths[0])
        incarnation = IncarnationId(store.store_identity, 1)
        registry.bind(live, occurrence, incarnation=incarnation)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (GROUP_NAMESPACE, store.codec.encode(2)))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            coord.retire_owner((NS, 1))
        assert registry.incarnation_for_occurrence(occurrence) == incarnation
        assert not dirty and not coord.placement_overlay


def test_owner_iterator_closes_its_snapshot_after_early_stop(tmp_path):
    with make_store(tmp_path / 'iterator.sqlite') as store:
        pin = fixture(store)
        values = store.iter_identity_occurrences_for_owner(pin, NS, 1)
        assert next(values) == (PATH, 1)
        values.close()
        assert not store.db.in_transaction
        assert store.read_owner_identity(pin, (NS, 1)).occurrences == ((PATH, 1),)
