"""Affected-group routing through the sole live registry, with placement overlays."""
import importlib
from dataclasses import dataclass

import pytest

from simulation.ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId, Occurrence
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata
from simulation.tests.test_stage_0_5_final_identity_catalog import groups, NS


@dataclass
class Box:
    value: int


def coordinator(store, pin, loads, dirty):
    module = importlib.import_module("simulation.ate_sim.persistence_lazy_identity_coordinator")
    store.codec.register_record("CoordinatorBox", Box)
    registry = LazyIdentityRegistry(store.store_identity, next_incarnation=1001, prune_dead_occurrences=True)
    owners = {}
    def load(owner):
        if owner not in owners:
            loads.append(owner)
            owners[owner] = Box(**store.read_version(instance.pin, *owner, expected_record_schema=1).value)
        return owners[owner]
    def replace(owner, path, obj):
        assert path == ()
        owners[owner] = obj
    instance = module.IdentityCoordinator(store, pin, registry,
        load_owner=load, resolve_path=lambda value, path: value,
        install_path=replace, mark_dirty=lambda owner: dirty.add(owner), preflight=lambda: None)
    return instance, registry, owners, load


@pytest.mark.parametrize("history", [1000, 10000])
def test_mutation_discovers_only_pinned_group_and_binds_unloaded_peer(tmp_path, history):
    with make_store(tmp_path / "routes.sqlite") as store:
        pin = groups(store, history)
        loads, dirty = [], set()
        coord, registry, owners, load = coordinator(store, pin, loads, dirty)
        registry.live_bindings = lambda: pytest.fail("global registry inventory")
        obj = load((NS, 1))
        registry.bind(obj, Occurrence(NS, 1, ()), incarnation=IncarnationId(store.store_identity, 1))
        before = store.diagnostics()
        assert set(coord.routes_for_mutation(obj)) == {(NS, 1), (NS, 2)}
        assert owners[NS, 2] is obj
        assert loads == [(NS, 1), (NS, 2)]
        assert dirty == {(NS, 1), (NS, 2)}
        assert store.diagnostics().payload_reads - before.payload_reads < 12
        assert coord.diagnostics()["discovered_occurrences"] == 2


def test_retained_alias_never_resurrects_replaced_or_deleted_placement(tmp_path):
    with make_store(tmp_path / "replacement.sqlite") as store:
        pin = groups(store, 1000)
        loads, dirty = [], set()
        coord, registry, owners, load = coordinator(store, pin, loads, dirty)
        old = load((NS, 1))
        registry.bind(old, Occurrence(NS, 1, ()), incarnation=IncarnationId(store.store_identity, 1))
        coord.routes_for_mutation(old)
        fresh = Box(value=1)
        coord.replace_placement((NS, 1), (), fresh)
        coord.replace_placement((NS, 2), (), None)
        dirty.clear()
        assert coord.routes_for_mutation(old) == ()
        assert dirty == set()
        assert owners[NS, 1] is fresh
        assert registry.incarnation_for_object(fresh) != registry.incarnation_for_object(old)


def test_coordinator_noop_does_not_query_archive_or_walk_registry(tmp_path):
    with make_store(tmp_path / "noop.sqlite") as store:
        pin = groups(store, 1000)
        coord, registry, owners, load = coordinator(store, pin, [], set())
        registry.live_bindings = lambda: pytest.fail("global registry inventory")
        before = store.diagnostics()
        delta = coord.prepare_delta(())
        assert delta.decode(store.codec) == ((), (), ())
        assert store.diagnostics() == before


def test_shared_scalar_write_freezes_identity_delta_and_accepts_exact_successor(tmp_path):
    with make_store(tmp_path / "save.sqlite") as store:
        pin = groups(store, 1000)
        coord, registry, owners, load = coordinator(store, pin, [], set())
        obj = load((NS, 1))
        registry.bind(obj, Occurrence(NS, 1, ()), incarnation=IncarnationId(store.store_identity, 1))
        coord.routes_for_mutation(obj)
        obj.value = 10
        payloads = tuple(VersionChange(*owner, {"value": obj.value}) for owner in ((NS, 1), (NS, 2)))
        delta = coord.prepare_delta(payloads)
        versions, records, identities = delta.decode(store.codec)
        assert identities == ()
        successor = store.commit(pin, commit_token="save", version_changes=payloads + versions,
            changes=records, new_segments=(), identity_changes=identities,
            metadata=metadata(2, (NS, "world_identity_links"))).pin
        coord.validate_publication(delta, successor)
        coord.accept_delta(delta, successor)
        assert coord.diagnostics()["dirty_owners"] == 0
        assert registry.object_for_incarnation(IncarnationId(store.store_identity, 1)) is obj


def test_repeated_replacement_and_cancel_drop_intermediate_group_routes(tmp_path):
    with make_store(tmp_path / "cancel.sqlite") as store:
        pin = groups(store, 1000)
        coord, registry, owners, load = coordinator(store, pin, [], set())
        original = load((NS, 1))
        registry.bind(original, Occurrence(NS, 1, ()), incarnation=IncarnationId(store.store_identity, 1))
        first = Box(value=1)
        second = Box(value=1)
        coord.replace_placement((NS, 1), (), first)
        coord.replace_placement((NS, 1), (), second)
        coord.replace_placement((NS, 1), (), original)
        assert coord.routes_for_mutation(first) == ()
        assert coord.routes_for_mutation(second) == ()
        for _ in range(1000):
            coord.replace_placement((NS, 1), (), Box(value=1))
            coord.replace_placement((NS, 1), (), original)
        assert coord.prepare_delta(()).decode(store.codec) == ((), (), ())
        stats = coord.diagnostics()
        assert stats["dirty_groups"] == 0
        assert stats["dirty_owners"] == 0
        assert stats["discovered_groups"] <= 256
        assert stats["clean_occurrences"] <= 4096
        assert stats["clean_python_bytes"] <= 2 * 1024 * 1024


def test_missing_forward_placement_is_not_reclassified_as_a_new_owner_path(tmp_path):
    with make_store(tmp_path / "missing-placement.sqlite") as store:
        pin = groups(store, 1000)
        coord, registry, owners, load = coordinator(store, pin, [], set())
        store.db.execute("DELETE FROM lazy_identity_occurrence_versions WHERE owner_key=?",
                         (store.codec.encode(1),))
        store.db.commit()
        from simulation.ate_sim.incremental_store import StoreIntegrityError
        with pytest.raises(StoreIntegrityError):
            coord.replace_placement((NS, 1), (), Box(value=1))


def test_bad_later_peer_is_rejected_before_any_shared_copy_is_installed(tmp_path):
    from simulation.ate_sim.persistence_lazy_store import IdentityOccurrenceChange
    from simulation.ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta
    from simulation.ate_sim.incremental_store import StoreIntegrityError
    with make_store(tmp_path / "bad-peer.sqlite") as store:
        pin = store.capture_pin()
        versions = tuple(VersionChange(NS, k, {"value": 1 if k < 3 else 999}) for k in (1, 2, 3))
        placements = tuple(IdentityOccurrenceChange(NS, k, (), 1) for k in (1, 2, 3))
        delta = initial_catalog_delta(store.codec, versions, placements, next_incarnation_id=2, generation=1)
        pin = store.commit(pin, commit_token="peers", version_changes=versions + delta.decode(store.codec)[0],
            changes=(), new_segments=(), identity_changes=placements, next_incarnation_id=2,
            metadata=metadata(1, (NS, "world_identity_links"))).pin
        coord, registry, owners, load = coordinator(store, pin, [], set())
        obj = load((NS, 1))
        registry.bind(obj, Occurrence(NS, 1, ()), incarnation=IncarnationId(store.store_identity, 1))
        with pytest.raises(StoreIntegrityError, match="copies disagree"):
            coord.routes_for_mutation(obj)
        assert owners[NS, 2] is not obj
        assert coord.diagnostics()["dirty_owners"] == 0
