"""Closed registered-record backing headers, borrowing the existing publisher.

These are checked storage primitives, not World activation or a live registry.
Incoming mutable children must already be projected into checked references.
"""
from dataclasses import dataclass

from .incremental_store import StoreIntegrityError

NAMESPACE = 'aux.lazy.records.headers'
TAG = 'recursive-record/v1'
REFERENCE_TAG = 'typed-record/v1'
SCHEMA = 1


def _positive(value):
    return type(value) is int and value > 0


@dataclass(frozen=True, slots=True)
class RecordReference:
    incarnation: int

    def __post_init__(self):
        if not _positive(self.incarnation):
            raise ValueError('invalid typed record reference')


def record_reference(value):
    return type(value) is RecordReference and _positive(value.incarnation)


def _schema_name(cls):
    return f'{cls.__module__.split(".")[-1]}.{cls.__name__}/v1'


def _declared_class(name):
    from .persistence_schema import RECORD_FIELDS
    if type(name) is not str:
        raise StoreIntegrityError('record header has no declared type name')
    # Schema constants only: stored names never cause imports or class loading.
    for cls in RECORD_FIELDS:
        if not cls.__dataclass_params__.frozen and _schema_name(cls) == name:
            return cls
    raise StoreIntegrityError('record header has an undeclared mutable type')


def stored_record_field(value):
    from .persistence_lazy_nested_history import immutable_value, reference
    from .persistence_event_id_reference import event_id_reference
    if record_reference(value) or reference(value) or event_id_reference(value) or immutable_value(value):
        return True
    return type(value) is tuple and all(stored_record_field(v) for v in value)


def checked_record_header(value):
    """Check ordered declared fields and exact non-field event seal metadata."""
    from .core import Event
    from .persistence_schema import RECORD_FIELDS
    if type(value) is not tuple or len(value) != 4 or value[0] != TAG:
        raise StoreIntegrityError('invalid recursive record header')
    cls = _declared_class(value[1])
    values, state = value[2:]
    if (type(values) is not tuple or len(values) != len(RECORD_FIELDS[cls])
            or any(not stored_record_field(v) for v in values)):
        raise StoreIntegrityError('recursive record field schema or value mismatch')
    if cls is Event:
        if (type(state) is not tuple or len(state) != 2
                or any(type(v) is not bool for v in state)
                or (not state[0] and state[1])):
            raise StoreIntegrityError('invalid recursive event seal metadata')
    elif state is not None:
        raise StoreIntegrityError('non-event record has event seal metadata')
    return cls, values, state


def record_header(record, *, values=None):
    """Project an explicit mutable schema record; never materialize children."""
    from .core import Event
    from .persistence_adapters import _check_record
    from .persistence_schema import RECORD_FIELDS
    _check_record(record)
    cls = type(record)
    if cls.__dataclass_params__.frozen:
        raise TypeError('frozen value records do not have mutable backings')
    if values is None:
        values = tuple(getattr(record, field) for field in RECORD_FIELDS[cls])
    if (type(values) is not tuple or len(values) != len(RECORD_FIELDS[cls])
            or any(not stored_record_field(v) for v in values)):
        raise TypeError('record backing fields require closed values or checked references')
    state = None
    if cls is Event:
        present = '_sealed' in vars(record)
        sealed = vars(record).get('_sealed', False)
        if type(sealed) is not bool:
            raise TypeError('event seal state must be bool')
        state = present, sealed
    return TAG, _schema_name(cls), values, state


def restore_record_header(header):
    """Restore only the declared object body; runtime child binding is separate."""
    from .core import Event
    from .persistence_schema import RECORD_FIELDS
    cls, values, state = checked_record_header(header)
    result = object.__new__(cls)
    for field, value in zip(RECORD_FIELDS[cls], values):
        object.__setattr__(result, field, value)
    if cls is Event and state[0]:
        object.__setattr__(result, '_sealed', state[1])
    return result


def read_record_header(store, pin, incarnation):
    """One checked pinned payload read; no catalog/bootstrap construction."""
    if not _positive(incarnation):
        raise ValueError('invalid record backing incarnation')
    try:
        value = store.read_version(pin, NAMESPACE, (incarnation, 0),
                                   expected_record_schema=SCHEMA).value
    except KeyError as exc:
        raise StoreIntegrityError('mandatory record backing header is absent') from exc
    checked_record_header(value)
    return value


def record_reference_placements(header):
    from .persistence_schema import RECORD_FIELDS
    from .persistence_lazy_nested_history import reference
    from .persistence_event_id_reference import event_id_reference
    cls, values, _state = checked_record_header(header)
    out = []
    def visit(value, path):
        if record_reference(value) or reference(value) or event_id_reference(value):
            out.append((path, value.incarnation))
        elif type(value) is tuple:
            for slot, child in enumerate(value):
                visit(child, path + (('index', slot),))
    for field, value in zip(RECORD_FIELDS[cls], values):
        visit(value, (('field', field),))
    return tuple(out)


def record_physical_path(header, path):
    from .persistence_schema import RECORD_FIELDS
    cls, _values, _state = checked_record_header(header)
    if not path:
        return ()
    if path[0][0] != 'field' or path[0][1] not in RECORD_FIELDS[cls]:
        raise StoreIntegrityError('record member path has an undeclared field')
    return (('index', 2), ('index', RECORD_FIELDS[cls].index(path[0][1]))) + path[1:]
