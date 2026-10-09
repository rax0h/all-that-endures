"""Large sharing-group witnesses spill without becoming another authority."""
import gc
import importlib
from pathlib import Path

import pytest

from simulation.ate_sim.incremental_store import TypedCodec, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_store import IdentityOccurrenceChange, VersionChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata


def spool_module():
    return importlib.import_module('simulation.ate_sim.persistence_lazy_spill')


def test_spill_is_immutable_checked_and_releases_its_private_file():
    cls = spool_module().CheckedSpool
    spool = cls(TypedCodec(), entry_limit=8, byte_limit=1024)
    values = [(number, True, float(number)) for number in range(100)]
    for value in values: spool.add(value)
    assert spool.spilled and spool.resident_bytes <= 2048
    result = spool.freeze()
    path = Path(result.path)
    assert path.is_file() and len(result) == 100
    assert list(result) == values and result[17] == values[17]
    with pytest.raises(RuntimeError): result.add((101,))
    result._db.execute('UPDATE entries SET checksum=? WHERE ordinal=17', ('bad',))
    result._db.commit()
    with pytest.raises(StoreIntegrityError): list(result)
    del result, spool
    gc.collect()
    assert not path.exists()


def test_small_spool_returns_exact_native_tuples_and_oversized_item_spills():
    cls = spool_module().CheckedSpool
    spool = cls(TypedCodec(), entry_limit=8, byte_limit=4096)
    for item in (True, 1., 2): spool.add(item)
    result = spool.freeze()
    assert type(result) is tuple and tuple(type(v) for v in result) == (bool, float, int)
    spool = cls(TypedCodec(), entry_limit=8, byte_limit=1024)
    spool.add('x' * 20000)
    assert spool.spilled and spool.resident_bytes < 2048
    assert list(spool.freeze()) == ['x' * 20000]


def shared_group(store, count=128, child_factory=list):
    module = importlib.import_module('simulation.ate_sim.persistence_lazy_identity_catalog')
    pin = store.capture_pin()
    version = VersionChange('world.people', 1, {key: child_factory() for key in range(count)})
    identities = tuple(IdentityOccurrenceChange('world.people', 1, (('key', key),), 1) for key in range(count))
    delta = module.initial_catalog_delta(store.codec, (version,), identities, next_incarnation_id=2, generation=1)
    return store.commit(pin, commit_token='initial', version_changes=(version, *delta.decode(store.codec)[0]),
        identity_changes=identities, next_incarnation_id=2, changes=(), new_segments=(),
        metadata=metadata(1, ('world.people', 'world_identity_links'))).pin


def test_checked_group_spills_membership_and_links_with_exact_completeness(tmp_path):
    module = importlib.import_module('simulation.ate_sim.persistence_lazy_identity_catalog')
    with make_store(tmp_path / 'group.sqlite') as store:
        pin = shared_group(store)
        catalog = module.IdentityCatalog(store, occurrence_limit=8, byte_limit=1024)
        group = catalog.read_identity_group(pin, 1)
        assert group.occurrences.spilled and group.links.spilled
        assert len(group.occurrences) == 128 and len(group.links) == 127
        assert {path[-1][1] for ns, key, path in group.occurrences} == set(range(128))
        assert all(anchor == group.anchor for _, anchor in group.links)
        assert group.occurrences.resident_bytes + group.links.resident_bytes < 4096
        assert not store.db.in_transaction
        store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE occurrence_path=?',
                         (store.codec.encode((('key', 127),)),))
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match='(count|digest|completeness)'):
            catalog.read_identity_group(pin, 1)


def test_streaming_reverse_lookup_closes_snapshot_and_rejects_reassigned_overlap(tmp_path):
    with make_store(tmp_path / 'reverse.sqlite') as store:
        pin = shared_group(store)
        rows = store.iter_identity_occurrences_for_incarnation(pin, 1)
        assert next(rows)[0] == 'world.people'
        rows.close()
        assert not store.db.in_transaction
        from simulation.ate_sim.persistence_lazy_store import _identity_occurrence_checksum
        key, path = store.codec.encode(1), store.codec.encode((('key', 0),))
        store.db.execute('UPDATE lazy_identity_occurrence_versions SET incarnation_id=2,row_checksum=? '
            'WHERE occurrence_path=?', (_identity_occurrence_checksum('world.people', key, path, 2, 1, None), path))
        store.db.commit()
        with pytest.raises(StoreIntegrityError): list(store.iter_identity_occurrences_for_incarnation(pin, 2))


def test_coordinator_replays_spilled_group_and_overlays_without_resident_membership_dict(tmp_path):
    from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId, Occurrence
    from simulation.ate_sim.persistence_lazy_identity_coordinator import IdentityCoordinator
    from simulation.tests.test_stage_0_5_final_identity_coordinator import Box
    with make_store(tmp_path / 'routing.sqlite') as store:
        store.codec.register_record('SpillBox', Box)
        pin = shared_group(store, child_factory=lambda: Box(0))
        owner = store.read_version(pin, 'world.people', 1, expected_record_schema=1).value
        registry = LazyIdentityRegistry(store.store_identity, next_incarnation=2)
        obj = owner[0]
        registry.bind(obj, Occurrence('world.people', 1, (('key', 0),)),
                      incarnation=IncarnationId(store.store_identity, 1))
        dirty = set()
        def install(owner_key, path, value):
            owner[path[0][1]] = value
        coord = IdentityCoordinator(store, pin, registry, load_owner=lambda key: owner,
            resolve_path=lambda value, path: value[path[0][1]], install_path=install,
            mark_dirty=dirty.add, preflight=lambda: None, occurrence_limit=8, byte_limit=1024)
        group = coord.discover_group(1)
        assert group.occurrences.spilled
        placements = coord._current_placements(group)
        assert placements.spilled and len(placements) == 128
        assert coord.routes_for_mutation(obj) == (('world.people', 1),)
        assert all(value is obj for value in owner.values())
        assert dirty == {('world.people', 1)}
        assert coord.diagnostics()['clean_occurrences'] <= 8
        assert coord.diagnostics()['spilled_group_bytes'] > 0
        assert coord.diagnostics()['dirty_group_python_bytes'] < 8192
        replacement = Box(1)
        coord.replace_placement(('world.people', 1), (('key', 127),), replacement)
        assert len(coord._current_placements(group)) == 127
        assert all(path != (('key', 127),) for _, _, path in coord._current_placements(group))


def test_spilled_order_commitment_rejects_recomputed_row_checksum():
    cls = spool_module().CheckedSpool
    codec = TypedCodec()
    spool = cls(codec, entry_limit=1, byte_limit=1024)
    spool.add((1,)); spool.add((2,))
    frozen = spool.freeze()
    from simulation.ate_sim.incremental_store import _framed_sha
    changed = codec.encode((3,))
    frozen._db.execute('UPDATE entries SET payload=?,checksum=? WHERE ordinal=1',
                      (changed, _framed_sha(b'checked-spill-row/v1', changed)))
    frozen._db.commit()
    with pytest.raises(StoreIntegrityError, match='commitment'): list(frozen)


def test_spilled_group_old_pin_and_reanchored_current_projection_are_exact(tmp_path):
    module = importlib.import_module('simulation.ate_sim.persistence_lazy_identity_catalog')
    with make_store(tmp_path / 'old-pin.sqlite') as store:
        writer = shared_group(store)
        old = store.capture_pin()
        catalog = module.IdentityCatalog(store, occurrence_limit=8, byte_limit=1024)
        version = VersionChange('world.people', 1, {key: [] for key in range(1, 128)})
        deletion = IdentityOccurrenceChange('world.people', 1, (('key', 0),), delete=True)
        delta = catalog.prepare_delta(writer, (version,), (deletion,), next_incarnation_id=2)
        writer = store.commit(writer, commit_token='changed', changes=(), new_segments=(),
            version_changes=(version, *delta.decode(store.codec)[0]), identity_changes=(deletion,),
            metadata=metadata(2, ('world.people', 'world_identity_links'))).pin
        historical, current = catalog.read_identity_group(old, 1), catalog.read_identity_group(writer, 1)
        assert historical.occurrences.spilled and current.occurrences.spilled
        assert len(historical.occurrences) == 128 and len(current.occurrences) == 127
        assert historical.anchor != current.anchor
        assert len(historical.links) == 127 and len(current.links) == 126
        assert all(anchor == historical.anchor for _, anchor in historical.links)
        assert all(anchor == current.anchor for _, anchor in current.links)
        store.release_pin(old)


def test_catalog_abort_closes_streaming_snapshot_and_rejects_missing_link(tmp_path):
    module = importlib.import_module('simulation.ate_sim.persistence_lazy_identity_catalog')
    with make_store(tmp_path / 'abort.sqlite') as store:
        pin = shared_group(store)
        catalog = module.IdentityCatalog(store, occurrence_limit=8, byte_limit=1024)
        store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND ordinal=17', (module.LINK_NAMESPACE,))
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match='(count|digest|completeness)'):
            catalog.read_identity_group(pin, 1)
        assert not store.db.in_transaction and store._checked_snapshot_depth == 0
