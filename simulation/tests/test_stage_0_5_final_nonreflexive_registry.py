"""The existing registry owns exact native NaN identity with bounded cleanup."""
import math
from dataclasses import dataclass

import pytest

from ate_sim.persistence_lazy_identity import (
    IdentityRegistryError, IncarnationId, LazyIdentityRegistry,
)
from ate_sim.core import Ref


def test_distinct_nan_objects_have_distinct_ids_and_repeated_binding_reuses_id():
    registry = LazyIdentityRegistry('keys')
    left, right = float('nan'), float('nan')
    first = registry.bind_nonreflexive_key(left)
    second = registry.bind_nonreflexive_key(right)
    assert first != second
    assert registry.bind_nonreflexive_key(left) == first
    assert registry.incarnation_for_object(left) == first
    assert registry.object_for_incarnation(first) is left
    assert registry.object_for_incarnation(second) is right
    registry.collect_nonreflexive_keys()
    assert registry.object_for_incarnation(first) is left


def test_unheld_nan_releases_forward_and_reverse_identity():
    registry = LazyIdentityRegistry('keys')
    value = float('nan')
    identity = registry.bind_nonreflexive_key(value)
    del value
    assert registry.collect_nonreflexive_keys() == 1
    assert registry.object_for_incarnation(identity) is None
    assert registry.diagnostics()['strong_object_roots'] == 0
    assert registry.diagnostics()['nonreflexive_key_queue'] == 0
    replacement = float('nan')
    assert registry.bind_nonreflexive_key(replacement).value > identity.value


@pytest.mark.parametrize('wrap', [tuple, frozenset, lambda values: (Ref('key', values[0]),)])
def test_native_nested_key_component_keeps_one_identity_until_key_is_released(wrap):
    registry = LazyIdentityRegistry('keys')
    value = float('nan')
    identity = registry.bind_nonreflexive_key(value)
    key = wrap([value])
    del value
    assert registry.collect_nonreflexive_keys() == 0
    component = next(iter(key))
    if type(component) is Ref:
        component = component.id
    assert registry.incarnation_for_object(component) == identity
    del component, key
    assert registry.collect_nonreflexive_keys() == 1
    assert registry.object_for_incarnation(identity) is None


def test_nonreflexive_collection_checks_only_its_bounded_queue():
    registry = LazyIdentityRegistry('keys')
    values = [float('nan') for _ in range(600)]
    identities = [registry.bind_nonreflexive_key(value) for value in values]
    held = values[-1]
    del values
    registry.live_bindings = lambda: pytest.fail('collection inventoried live registry')
    registry.derived_owner_groups = lambda: pytest.fail('collection inventoried placements')
    assert registry.collect_nonreflexive_keys() == 256
    assert registry._nonreflexive_checks == 256
    assert registry.collect_nonreflexive_keys() == 256
    assert registry._nonreflexive_checks == 512
    assert registry.collect_nonreflexive_keys() == 87
    assert registry._nonreflexive_checks == 600
    assert registry.object_for_incarnation(identities[-1]) is held
    assert len(registry._by_incarnation) == len(registry._by_object_id) == 1
    del held
    assert registry.collect_nonreflexive_keys() == 1


def test_nan_rebinding_uses_existing_checked_incarnation_rules():
    registry = LazyIdentityRegistry('keys')
    value, other = float('nan'), float('nan')
    identity = IncarnationId('keys', 40)
    assert registry.bind_nonreflexive_key(value, incarnation=identity) == identity
    assert registry.next_incarnation == 41
    with pytest.raises(IdentityRegistryError, match='different live'):
        registry.bind_nonreflexive_key(other, incarnation=identity)
    with pytest.raises(IdentityRegistryError, match='another incarnation'):
        registry.bind_nonreflexive_key(value, incarnation=IncarnationId('keys', 41))
    with pytest.raises(IdentityRegistryError, match='another store'):
        registry.bind_nonreflexive_key(other, incarnation=IncarnationId('foreign', 1))


@pytest.mark.parametrize('value', [True, 1, 1.0, float('inf'), 'nan', None, object()])
def test_nonreflexive_binding_rejects_other_types_without_allocating(value):
    registry = LazyIdentityRegistry('keys')
    with pytest.raises(TypeError, match='native NaN'):
        registry.bind_nonreflexive_key(value)
    assert registry.next_incarnation == 1


def test_nonreflexive_binding_rejects_float_subclasses():
    class ExoticFloat(float):
        pass
    registry = LazyIdentityRegistry('keys')
    with pytest.raises(TypeError, match='native NaN'):
        registry.bind_nonreflexive_key(ExoticFloat('nan'))
    assert registry.next_incarnation == 1


def test_normal_mutable_bindings_remain_weak_and_close_releases_nan_roots():
    import gc
    import weakref
    @dataclass
    class Box:
        value: object
    registry = LazyIdentityRegistry('keys')
    box = Box(1)
    identity = registry.bind(box)
    ref = weakref.ref(box)
    value = float('nan')
    registry.bind_nonreflexive_key(value)
    assert math.isnan(value)
    assert registry.diagnostics()['strong_object_roots'] == 1
    del box
    gc.collect()
    assert ref() is None and registry.object_for_incarnation(identity) is None
    registry.close()
    assert not registry._by_incarnation and not registry._by_object_id
    assert not registry._nonreflexive_queue


@pytest.mark.parametrize('budget', [-1, 257, True, 1.0])
def test_collection_budget_is_an_exact_bounded_integer(budget):
    registry = LazyIdentityRegistry('keys')
    with pytest.raises(ValueError, match='budget'):
        registry.collect_nonreflexive_keys(budget=budget)


def test_collection_work_is_fixed_for_different_live_key_history_sizes():
    checks = []
    for size in (1000, 10000):
        registry = LazyIdentityRegistry('keys')
        # Explicit input setup, all native values intentionally retained as R.
        values = [float('nan') for _ in range(size)]
        identities = [registry.bind_nonreflexive_key(value) for value in values]
        registry.live_bindings = lambda: pytest.fail('collection inventoried registry')
        before = registry._nonreflexive_checks
        assert registry.collect_nonreflexive_keys() == 0
        checks.append(registry._nonreflexive_checks - before)
        assert registry.object_for_incarnation(identities[0]) is values[0]
        registry.close()
    assert checks == [256, 256]


def test_nonreflexive_apis_obey_registry_close_guard():
    registry = LazyIdentityRegistry('keys')
    registry.close()
    with pytest.raises(IdentityRegistryError, match='closed'):
        registry.bind_nonreflexive_key(float('nan'))
    with pytest.raises(IdentityRegistryError, match='closed'):
        registry.collect_nonreflexive_keys()
