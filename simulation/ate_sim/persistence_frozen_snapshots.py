"""Deep immutable certification reuses checked frozen backing descriptors."""
from .incremental_store import StoreIntegrityError
from .persistence_lazy_nested_history import reference, immutable_value, DESCRIPTOR_NAMESPACE
from .persistence_nonreflexive_keys import nonreflexive_key_reference, read_nonreflexive_key_header


def immutable_snapshot_value(value, reference_is_immutable=None):
    if nonreflexive_key_reference(value):
        return reference_is_immutable is not None and reference_is_immutable(value)
    if reference(value):
        return (value.kind in ('frozen-list', 'frozen-map')
                and reference_is_immutable is not None and reference_is_immutable(value))
    if type(value) is tuple:
        return all(immutable_snapshot_value(child, reference_is_immutable) for child in value)
    from .core import Ref
    if type(value) is Ref:
        return (immutable_snapshot_value(value.kind, reference_is_immutable)
                and immutable_snapshot_value(value.id, reference_is_immutable))
    if type(value) is frozenset:
        return all(immutable_snapshot_value(child, reference_is_immutable) for child in value)
    return immutable_value(value)


def checked_frozen_descriptor(value, *, kind=None):
    if (type(value) is not tuple or len(value) != 4
            or value[0] not in ('frozen-list', 'frozen-map')
            or (kind is not None and value[0] != kind)
            or type(value[1]) is not int or value[1] < 0
            or type(value[2]) is not int or value[2] < value[1]
            or (value[0] == 'frozen-list' and value[2] != value[1])
            or type(value[3]) is not bool):
        raise StoreIntegrityError('invalid frozen snapshot descriptor certification')
    return value


def read_frozen_certification(store, pin, value):
    if nonreflexive_key_reference(value):
        read_nonreflexive_key_header(store, pin, value.incarnation)
        return True
    if not reference(value) or value.kind not in ('frozen-list', 'frozen-map'):
        return False
    try:
        descriptor = store.read_version(pin, DESCRIPTOR_NAMESPACE, value.incarnation, expected_record_schema=1).value
    except KeyError as exc:
        raise StoreIntegrityError('frozen snapshot descriptor is absent') from exc
    return checked_frozen_descriptor(descriptor, kind=value.kind)[3]


def verify_frozen_certification(history):
    """Explicit full scrub; ordinary reads rely on checked certification rows."""
    resolver = lambda value: read_frozen_certification(history._store, history._pin, value)
    values = iter(history) if history._kind == 'list' else (entry[2] for entry in history._ordered_entries())
    actual = True
    for value in values:
        actual = immutable_snapshot_value(value, resolver) and actual
    if actual != history._deep_immutable:
        raise StoreIntegrityError('frozen snapshot certification disagrees with backing values')


def read_capture_certification(store, generation, value):
    """Check one descriptor in the caller's already active capture transaction."""
    atom = nonreflexive_key_reference(value)
    if not atom and (not reference(value) or value.kind != 'frozen-map'):
        return False
    if (not hasattr(store, '_visible_record_row')
            or not getattr(store, '_active_read_transaction', False)
            or not store.db.in_transaction):
        raise StoreIntegrityError('frozen snapshot capture requires checked lazy transaction')
    from .persistence_nonreflexive_keys import NAMESPACE as NAN_HEADERS, checked_nonreflexive_key_header
    namespace = NAN_HEADERS if atom else DESCRIPTOR_NAMESPACE
    key = store.codec.encode((value.incarnation, 0) if atom else value.incarnation)
    row = store._visible_record_row(generation, namespace, key)
    if row is None:
        raise StoreIntegrityError('frozen snapshot descriptor is absent')
    descriptor, schema, *_ = store._check_record_row(namespace, key, row, decode=True)
    if schema != 1:
        raise StoreIntegrityError('frozen snapshot descriptor schema mismatch')
    if atom:
        checked_nonreflexive_key_header(descriptor)
        return True
    return checked_frozen_descriptor(descriptor, kind=value.kind)[3]
