# CI rerun marker: owner-scoped identity + partnership overlays
import gc
import weakref
from dataclasses import dataclass

import pytest

from simulation.ate_sim.persistence_lazy_identity import (
    IdentityRegistryError,
    IncarnationId,
    LazyIdentityRegistry,
    Occurrence,
)


@dataclass
class Box:
    value: object = None


def occ(owner, key, *path):
    return Occurrence(owner, key, tuple(path))


def test_equal_distinct_objects_get_distinct_incarnations_and_old_alias_stays_old():
    registry = LazyIdentityRegistry("store-a")
    first = Box(1)
    second = Box(1)
    place = occ("people", 1)

    first_id = registry.bind(first, place)
    assert registry.object_for_incarnation(first_id) is first
    registry.detach_occurrence(place, expected=first_id)

    second_id = registry.bind(second, place)
    assert second_id != first_id
    assert registry.incarnation_for_object(first) == first_id
    assert registry.incarnation_for_occurrence(place) == second_id
    assert registry.object_for_incarnation(first_id) is first
    assert registry.object_for_incarnation(second_id) is second


def test_owner_occurrence_index_tracks_attach_move_detach_and_replace():
    registry = LazyIdentityRegistry("store-a")
    first = Box("first")
    second = Box("second")
    left = occ("people", 1, ("field", "a"))
    right = occ("people", 2, ("field", "b"))

    first_id = registry.bind(first, left)
    registry.attach_occurrence(first, right)
    assert registry.occurrences_for_owner("people", 1) == (left,)
    assert registry.occurrences_for_owner("people", 2) == (right,)

    moved = occ("people", 3, ("field", "c"))
    registry.move(first, right, moved)
    assert registry.occurrences_for_owner("people", 2) == ()
    assert registry.occurrences_for_owner("people", 3) == (moved,)

    registry.detach_occurrence(left, expected=first_id)
    assert registry.occurrences_for_owner("people", 1) == ()

    second_id = registry.bind(second, left)
    assert second_id != first_id
    assert registry.occurrences_for_owner("people", 1) == (left,)


def test_move_remove_and_reinsert_same_object_preserves_incarnation():
    registry = LazyIdentityRegistry("store-a")
    value = Box("same")
    a = occ("people", 1)
    b = occ("people", 2)

    identity = registry.bind(value, a)
    assert registry.move(value, a, b) == identity
    assert registry.incarnation_for_occurrence(a) is None
    assert registry.incarnation_for_occurrence(b) == identity

    assert registry.detach_occurrence(b, expected=identity) == identity
    assert registry.is_detached(value)
    assert registry.attach_occurrence(value, a) == identity
    assert registry.incarnation_for_occurrence(a) == identity


def test_delete_then_different_object_never_reuses_incarnation():
    registry = LazyIdentityRegistry("store-a")
    place = occ("people", 1)
    old = Box("x")
    old_id = registry.bind(old, place)
    registry.detach_occurrence(place, expected=old_id)

    replacement = Box("x")
    replacement_id = registry.bind(replacement, place)
    assert replacement_id.value == old_id.value + 1
    assert replacement_id != old_id
    assert registry.incarnation_for_object(old) == old_id


def test_retained_child_survives_parent_collection_with_owner_placement_intact():
    registry = LazyIdentityRegistry("store-a")
    parent = Box()
    child = Box("child")
    parent.value = child

    parent_id = registry.bind(parent, occ("people", 1))
    child_occ = occ("people", 1, ("field", "value"))
    child_id = registry.bind(child, child_occ)

    parent_ref = weakref.ref(parent)
    del parent
    gc.collect()

    assert parent_ref() is None
    assert registry.object_for_incarnation(parent_id) is None
    assert registry.object_for_incarnation(child_id) is child
    assert registry.incarnation_for_occurrence(child_occ) == child_id
    assert registry.is_detached(child) is False


def test_cross_owner_sharing_merges_and_split_changes_only_projection():
    registry = LazyIdentityRegistry("store-a")
    shared = Box("shared")
    left = occ("people", 1, ("field", "shared"))
    right = occ("households", 2, ("field", "shared"))

    identity = registry.bind(shared, left)
    registry.attach_occurrence(shared, right)
    assert registry.incarnation_for_occurrence(left) == identity
    assert registry.incarnation_for_occurrence(right) == identity
    assert registry.derived_owner_groups() == (
        frozenset({("people", 1), ("households", 2)}),
    )

    registry.detach_occurrence(right, expected=identity)
    assert registry.incarnation_for_object(shared) == identity
    assert registry.derived_owner_groups() == (
        frozenset({("people", 1)}),
    )

    registry.attach_occurrence(shared, right)
    assert registry.incarnation_for_object(shared) == identity
    assert registry.derived_owner_groups() == (
        frozenset({("people", 1), ("households", 2)}),
    )


def test_group_merge_via_shared_incarnation_does_not_rewrite_other_incarnations():
    registry = LazyIdentityRegistry("store-a")
    a = Box("a")
    b = Box("b")
    a_id = registry.bind(a, occ("people", 1, ("field", "a")))
    b_id = registry.bind(b, occ("people", 2, ("field", "b")))

    registry.attach_occurrence(a, occ("people", 2, ("field", "also-a")))
    groups = registry.derived_owner_groups()
    assert groups == (frozenset({("people", 1), ("people", 2)}),)
    assert registry.incarnation_for_object(a) == a_id
    assert registry.incarnation_for_object(b) == b_id


def test_weak_cleanup_drops_live_maps_without_global_sweep_but_keeps_occurrence_label():
    registry = LazyIdentityRegistry("store-a")
    value = Box("temporary")
    place = occ("people", 1)
    identity = registry.bind(value, place)
    ref = weakref.ref(value)

    del value
    gc.collect()

    assert ref() is None
    assert registry.object_for_incarnation(identity) is None
    diag = registry.diagnostics()
    assert diag["weak_forward_entries"] == 0
    assert diag["weak_reverse_entries"] == 0
    # Placement is persistent/logical metadata and does not strongly retain obj.
    assert registry.incarnation_for_occurrence(place) == identity


def test_stale_cleanup_token_cannot_remove_newer_live_binding():
    registry = LazyIdentityRegistry("store-a")
    old = Box("old")
    old_id = registry.bind(old)
    old_reverse = registry._by_object_id[id(old)]
    stale_ref, _inc, stale_token = old_reverse

    newer = Box("new")
    newer_id = registry.bind(newer)
    new_reverse = registry._by_object_id[id(newer)]

    registry._cleanup(
        id(newer),
        newer_id,
        stale_token,
        stale_ref,
    )
    assert registry._by_object_id[id(newer)] == new_reverse
    assert registry.object_for_incarnation(newer_id) is newer
    assert registry.object_for_incarnation(old_id) is old


def test_persisted_occurrence_can_be_seeded_before_object_load_then_bound_exactly():
    registry = LazyIdentityRegistry("store-a", next_incarnation=3)
    identity = IncarnationId("store-a", 9)
    place = occ("people", 9, ("field", "wallet"))
    registry.attach_existing(identity, place)

    assert registry.next_incarnation == 10
    assert registry.object_for_incarnation(identity) is None
    loaded = Box("wallet")
    assert registry.bind(loaded, incarnation=identity) == identity
    assert registry.object_for_incarnation(identity) is loaded
    assert registry.incarnation_for_occurrence(place) == identity


def test_foreign_incarnation_and_duplicate_live_instance_are_rejected():
    registry = LazyIdentityRegistry("store-a")
    with pytest.raises(IdentityRegistryError, match="another store"):
        registry.bind(Box(), incarnation=IncarnationId("store-b", 1))

    first = Box("one")
    identity = registry.bind(first)
    with pytest.raises(IdentityRegistryError, match="different live"):
        registry.bind(Box("two"), incarnation=identity)


def test_close_drops_registry_metadata_without_mutating_user_objects():
    registry = LazyIdentityRegistry("store-a")
    value = Box({"still": "mine"})
    registry.bind(value, occ("people", 1))
    registry.close()

    assert value.value == {"still": "mine"}
    with pytest.raises(IdentityRegistryError, match="closed"):
        registry.incarnation_for_object(value)
