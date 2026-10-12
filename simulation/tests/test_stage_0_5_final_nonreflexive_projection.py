"""Key projection preserves native equality through the existing registry."""
import pytest

from ate_sim.core import Ref, Layer
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_identity import LazyIdentityRegistry, IncarnationId
from ate_sim import persistence_nonreflexive_keys as keys


SHAPES = {
    'float': lambda value: value,
    'tuple': lambda value: ('key', value),
    'frozenset': lambda value: frozenset(('key', value)),
    'ref': lambda value: Ref('key', value),
    'deep': lambda value: (Ref(value, (value,)), frozenset((('nested', value),))),
}


def projector(registry):
    return lambda value: keys.NonreflexiveKeyReference(registry.bind_nonreflexive_key(value).value)


def restorer(registry):
    return lambda value: registry.object_for_incarnation(IncarnationId(registry.store_identity, value.incarnation))


@pytest.mark.parametrize('shape', SHAPES)
def test_distinct_nan_keys_have_distinct_encoded_addresses_and_exact_native_restoration(shape):
    registry = LazyIdentityRegistry('keys')
    original = SHAPES[shape](float('nan'))
    distinct = SHAPES[shape](float('nan'))
    assert original != distinct
    codec = WorldCodec(identity_links_recorded=True)
    project, restore = projector(registry), restorer(registry)
    first = keys.project_immutable_key(original, project)
    second = keys.project_immutable_key(distinct, project)
    assert codec.encode(first) != codec.encode(second)
    assert keys.project_immutable_key(original, project) == first
    payload = keys.project_immutable_key(original, project, canonical=False)
    assert keys.canonical_stored_key(payload) == first
    restored = keys.restore_immutable_key(codec.decode(codec.encode(payload)), restore)
    assert type(restored) is type(original)
    if shape == 'float':
        assert restored is original
    else:
        assert restored == original
    assert restored != distinct


def test_shared_nan_components_keep_native_composite_key_equality():
    registry = LazyIdentityRegistry('keys')
    nan = float('nan')
    native = [Ref(nan, (True, nan)), Ref(nan, (1.0, nan))]
    assert native[0] == native[1]
    project = projector(registry)
    stored = [keys.project_immutable_key(value, project) for value in native]
    assert stored[0] == stored[1]
    assert registry.next_incarnation == 2
    codec = WorldCodec()
    restored = [keys.restore_immutable_key(codec.decode(codec.encode(value)), restorer(registry)) for value in stored]
    assert restored[0] == restored[1]
    assert restored[0].kind is restored[0].id[1] is restored[1].kind is nan


@pytest.mark.parametrize('values', [
    (True, 1, 1.0), (-0.0, False, 0),
    ((True, Layer.SOCIETY), (1.0, 'society')),
    (frozenset((True,)), frozenset((1.0,))),
    (Ref(Layer.SOCIETY, True), Ref('society', 1.0)),
])
def test_existing_numeric_enum_and_container_equality_remains_canonical(values):
    def no_nan(_):
        pytest.fail('reflexive key allocated a NaN identity')
    codec = WorldCodec()
    addresses = [codec.encode(keys.project_immutable_key(value, no_nan)) for value in values]
    assert all(value == values[0] for value in values)
    assert len(set(addresses)) == 1
    for value in values:
        payload = keys.project_immutable_key(value, no_nan, canonical=False)
        restored = keys.restore_immutable_key(codec.decode(codec.encode(payload)), no_nan)
        assert type(restored) is type(value) and restored == value


@pytest.mark.parametrize('bad', [object(), [1], (float('nan'), object()), Ref('key', [1])])
def test_finite_key_preflight_rejects_entire_bad_input_before_nan_allocation(bad):
    calls = []
    def project(value):
        calls.append(value)
        return keys.NonreflexiveKeyReference(1)
    with pytest.raises(TypeError, match='immutable'):
        keys.project_immutable_key(bad, project)
    assert calls == []


def test_lookup_only_projection_never_allocates_for_an_unknown_nan():
    registry = LazyIdentityRegistry('keys')
    held, unknown = float('nan'), float('nan')
    expected = keys.project_immutable_key((held,), projector(registry))
    before = registry.next_incarnation
    def lookup(value):
        identity = registry.incarnation_for_object(value)
        if identity is None:
            raise KeyError(value)
        return keys.NonreflexiveKeyReference(identity.value)
    assert keys.project_immutable_key((held,), lookup) == expected
    with pytest.raises(KeyError):
        keys.project_immutable_key((unknown,), lookup)
    assert registry.next_incarnation == before


@pytest.mark.parametrize('bad', [None, 1, 'token', Ref('key', 1)])
def test_projection_rejects_an_unchecked_callback_result(bad):
    with pytest.raises(TypeError, match='checked.*reference'):
        keys.project_immutable_key(float('nan'), lambda _: bad)


@pytest.mark.parametrize('bad', [float('nan'), (float('nan'),), Ref('key', float('nan')), object()])
def test_stored_key_validation_rejects_unprojected_or_undeclared_values(bad):
    with pytest.raises(StoreIntegrityError):
        keys.canonical_stored_key(bad)


@pytest.mark.parametrize('bad', [None, 1.0, True, 'nan'])
def test_restoration_rejects_a_non_native_nan_canonical_object(bad):
    with pytest.raises(StoreIntegrityError, match='native NaN'):
        keys.restore_immutable_key(keys.NonreflexiveKeyReference(1), lambda _: bad)


def test_forged_reference_is_rejected_in_stored_keys_and_projection_callback():
    forged = keys.NonreflexiveKeyReference(1)
    object.__setattr__(forged, 'incarnation', True)
    with pytest.raises(StoreIntegrityError):
        keys.canonical_stored_key((forged,))
    with pytest.raises(StoreIntegrityError):
        keys.restore_immutable_key(Ref('key', forged), lambda _: float('nan'))
    with pytest.raises(TypeError, match='checked.*reference'):
        keys.project_immutable_key(float('nan'), lambda _: forged)


def test_held_restored_nested_component_preserves_identity_after_original_key_is_released():
    registry = LazyIdentityRegistry('keys')
    source = Ref('key', (float('nan'),))
    payload = keys.project_immutable_key(source, projector(registry), canonical=False)
    held = keys.restore_immutable_key(payload, restorer(registry)).id[0]
    del source
    assert registry.collect_nonreflexive_keys() == 0
    assert keys.project_immutable_key(Ref('key', (held,)), projector(registry)) == keys.canonical_stored_key(payload)
    del held
    assert registry.collect_nonreflexive_keys() == 1
