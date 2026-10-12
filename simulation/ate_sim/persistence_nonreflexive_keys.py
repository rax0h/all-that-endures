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


def stored_immutable_key(value):
    """Accept genuine legacy immutable values and the closed projected schema."""
    from .persistence_lazy_nested_history import immutable_value
    return immutable_value(value) or _stored_key_value(value)


def storage_equality_key(value):
    from .persistence_lazy_nested_history import immutable_value, equality_key
    return equality_key(value) if immutable_value(value) else canonical_stored_key(value)


def stored_reference_placements(value, path=()):
    """Enumerate references in a checked value, including immutable components."""
    from .core import Ref
    from .persistence_lazy_nested_history import reference
    from .persistence_record_headers import record_reference
    from .persistence_event_id_reference import event_id_reference
    out = []
    def visit(item, current):
        if reference(item) or record_reference(item) or event_id_reference(item) or nonreflexive_key_reference(item):
            out.append((current, item.incarnation))
        elif type(item) is tuple:
            for slot, child in enumerate(item):
                visit(child, current + (('index', slot),))
        elif type(item) is Ref:
            visit(item.kind, current + (('field', 'kind'),))
            visit(item.id, current + (('field', 'id'),))
        elif type(item) is frozenset:
            for child in item:
                visit(child, current + (('key', child),))
    visit(value, path)
    return tuple(out)


def valid_immutable_member_steps(path):
    return type(path) is tuple and all(
        type(part) is tuple and len(part) == 2 and type(part[0]) is str and (
            part[0] == 'index' and type(part[1]) is int and part[1] >= 0
            or part[0] == 'field' and type(part[1]) is str and part[1] in ('kind', 'id')
            or part[0] == 'key' and stored_immutable_key(part[1]))
        for part in path)


def _stored_member(value, step):
    from .core import Ref
    kind, slot = step
    if kind == 'index' and type(value) is tuple and type(slot) is int and 0 <= slot < len(value):
        return value[slot]
    if kind == 'field' and type(value) is Ref and slot in ('kind', 'id'):
        return getattr(value, slot)
    if kind == 'key' and type(value) is frozenset:
        matches = [child for child in value if child is slot or child == slot]
        if len(matches) == 1:
            return matches[0]
    raise StoreIntegrityError('stored immutable member path is absent or has the wrong shape')


def resolve_stored_member_path(value, path):
    if not valid_immutable_member_steps(path):
        raise StoreIntegrityError('invalid stored immutable member path')
    for step in path:
        value = _stored_member(value, step)
    return value


def replace_stored_member_path(value, path, replacement):
    from .core import Ref
    if not valid_immutable_member_steps(path):
        raise StoreIntegrityError('invalid stored immutable member path')
    if not path:
        return replacement
    kind, slot = path[0]
    old = _stored_member(value, path[0])
    updated = replace_stored_member_path(old, path[1:], replacement)
    if kind == 'index':
        values = list(value)
        values[slot] = updated
        return tuple(values)
    if kind == 'field':
        return Ref(updated, value.id) if slot == 'kind' else Ref(value.kind, updated)
    return frozenset(updated if child is old else child for child in value)
