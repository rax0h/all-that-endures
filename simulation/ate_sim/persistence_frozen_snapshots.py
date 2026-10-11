"""Deep immutable certification reuses checked frozen backing descriptors."""
from .incremental_store import StoreIntegrityError
from .persistence_lazy_nested_history import reference, immutable_value, DESCRIPTOR_NAMESPACE


def immutable_snapshot_value(value, reference_is_immutable=None):
    if reference(value):
        return (value.kind in ('frozen-list', 'frozen-map')
                and reference_is_immutable is not None and reference_is_immutable(value))
    if type(value) is tuple:
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
    if not reference(value) or value.kind != 'frozen-map':
        return False
    if (not hasattr(store, '_visible_record_row')
            or not getattr(store, '_active_read_transaction', False)
            or not store.db.in_transaction):
        raise StoreIntegrityError('frozen snapshot capture requires checked lazy transaction')
    key = store.codec.encode(value.incarnation)
    row = store._visible_record_row(generation, DESCRIPTOR_NAMESPACE, key)
    if row is None:
        raise StoreIntegrityError('frozen snapshot descriptor is absent')
    descriptor, schema, *_ = store._check_record_row(DESCRIPTOR_NAMESPACE, key, row, decode=True)
    if schema != 1:
        raise StoreIntegrityError('frozen snapshot descriptor schema mismatch')
    return checked_frozen_descriptor(descriptor, kind=value.kind)[3]
