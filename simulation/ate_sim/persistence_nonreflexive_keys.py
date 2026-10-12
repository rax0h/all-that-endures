"""Closed immutable NaN bodies for the existing identity/storage architecture.

These primitives do not enable recursive key admission or a new World format.
Native object identity belongs to LazyIdentityRegistry, not this module.
"""
from dataclasses import dataclass
import math
import struct

from .incremental_store import StoreIntegrityError

NAMESPACE = 'aux.lazy.keys.nan_atoms'
TAG = 'native-nan-key/v1'
REFERENCE_TAG = 'typed-nan-key/v1'
SCHEMA = 1


@dataclass(frozen=True, slots=True)
class NonreflexiveKeyReference:
    incarnation: int

    def __post_init__(self):
        if type(self.incarnation) is not int or self.incarnation <= 0:
            raise ValueError('invalid native NaN key reference')


def nonreflexive_key_reference(value):
    return (type(value) is NonreflexiveKeyReference
            and type(value.incarnation) is int and value.incarnation > 0)


def nonreflexive_key_header(value):
    if type(value) is not float or not math.isnan(value):
        raise TypeError('nonreflexive key body requires a native NaN')
    # One fixed-size authority preserves the native sign and NaN payload bits.
    return TAG, struct.pack('>d', value)


def checked_nonreflexive_key_header(value):
    if (type(value) is not tuple or len(value) != 2 or value[0] != TAG
            or type(value[1]) is not bytes or len(value[1]) != 8
            or not math.isnan(struct.unpack('>d', value[1])[0])):
        raise StoreIntegrityError('invalid native NaN key body')
    return value[1]


def restore_nonreflexive_key_header(value):
    return struct.unpack('>d', checked_nonreflexive_key_header(value))[0]


def read_nonreflexive_key_header(store, pin, incarnation):
    if type(incarnation) is not int or incarnation <= 0:
        raise ValueError('invalid native NaN key incarnation')
    try:
        value = store.read_version(pin, NAMESPACE, (incarnation, 0),
                                   expected_record_schema=SCHEMA).value
    except KeyError as exc:
        raise StoreIntegrityError('mandatory native NaN key body is absent') from exc
    checked_nonreflexive_key_header(value)
    return value


def _key_tree(value, visit_nan, *, canonical):
    """Map only a prevalidated closed key tree; no arbitrary class callbacks."""
    from .core import Ref, Layer
    if nonreflexive_key_reference(value) or (type(value) is float and math.isnan(value)):
        return visit_nan(value)
    if type(value) is Layer:
        return value.value if canonical else value
    if type(value) is bool:
        return int(value) if canonical else value
    if type(value) is float and canonical and value.is_integer():
        return int(value)
    if type(value) is Ref:
        return Ref(_key_tree(value.kind, visit_nan, canonical=canonical),
                   _key_tree(value.id, visit_nan, canonical=canonical))
    if type(value) is tuple:
        return tuple(_key_tree(child, visit_nan, canonical=canonical) for child in value)
    if type(value) is frozenset:
        return frozenset(_key_tree(child, visit_nan, canonical=canonical) for child in value)
    return value


def project_immutable_key(value, project_nan, *, canonical=True):
    """Project native key components into checked IDs after finite preflight.

    canonical=False retains the original bool/float/enum representative for
    payload restoration. The callback borrows the existing registry/runtime;
    lookup-only callbacks may raise KeyError without allocating an identity.
    """
    from .persistence_lazy_nested_history import immutable_value
    if type(canonical) is not bool or not immutable_value(value):
        raise TypeError('key projection requires a closed immutable native key')
    hash(value)
    def checked_projection(nan):
        result = project_nan(nan)
        if not nonreflexive_key_reference(result):
            raise TypeError('native NaN key projection requires a checked key reference')
        return result
    return _key_tree(value, checked_projection, canonical=canonical)


def _stored_key_value(value, active=None):
    from .core import Ref, Layer
    if nonreflexive_key_reference(value):
        return True
    if value is None or type(value) in (bool, int, str, bytes, Layer):
        return True
    if type(value) is float:
        return not math.isnan(value)
    if type(value) not in (Ref, tuple, frozenset):
        return False
    active = set() if active is None else active
    if id(value) in active:
        return False
    active.add(id(value))
    try:
        if type(value) is Ref:
            if set(vars(value)) != {'kind', 'id'}:
                return False
            return _stored_key_value(value.kind, active) and _stored_key_value(value.id, active)
        return all(_stored_key_value(child, active) for child in value)
    finally:
        active.remove(id(value))


def canonical_stored_key(value):
    """Closed storage-key equality; raw NaNs must already have checked IDs."""
    if not _stored_key_value(value):
        raise StoreIntegrityError('invalid or unprojected stored immutable key')
    return _key_tree(value, lambda token: token, canonical=True)


def restore_immutable_key(value, restore_nan):
    """Restore native key representatives through one canonical-object resolver."""
    if not _stored_key_value(value):
        raise StoreIntegrityError('invalid or unprojected stored immutable key')
    def checked_restore(token):
        result = restore_nan(token)
        if type(result) is not float or not math.isnan(result):
            raise StoreIntegrityError('key reference did not resolve to its native NaN')
        return result
    return _key_tree(value, checked_restore, canonical=False)
