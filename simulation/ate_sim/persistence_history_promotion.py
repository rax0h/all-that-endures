"""Promotion of actual unpublished list output; no persisted-history migration."""
from .incremental_store import StoreConflictError, StoreIntegrityError
from .persistence_lazy_nested_history import LazyHistoryList, DESCRIPTOR_NAMESPACE
from .persistence_lazy_sequence import LazyOrderedSequence


def prepare_unpublished_list(history):
    """Build counted output from D and leave the live alias untouched on failure.

    A persisted append history needs the complete copy-upgrade/promotion design.
    It must never be silently read in full by a current owner assignment.
    """
    if type(history) is not LazyHistoryList or not history._new:
        raise StoreConflictError('persisted append-history promotion requires an explicit copy upgrade')
    history._ensure()
    if history._sorting_values is not None:
        raise StoreConflictError('list promotion is blocked during a whole-list sort')
    with history._store.read_snapshot(history._pin):
        try:
            history._store.read_version(history._pin, DESCRIPTOR_NAMESPACE, history._incarnation,
                expected_record_schema=1)
        except KeyError:
            pass
        else:
            raise StoreIntegrityError('unpublished promotion has an existing append backing')
    return LazyOrderedSequence(history._store, history._pin, history._incarnation,
        initial_values=history, value_mode='native', cache_budget=history._cache_budget,
        guard=history._guard, changed=history._changed, read_guard=history._read_guard,
        checked_types=history._member_types.enabled)


def install_unpublished_list(history, prepared):
    """Keep the registry's exact object and weak references, replacing its backing."""
    if (type(history) is not LazyHistoryList or type(prepared) is not LazyOrderedSequence
            or not history._new or not prepared._new
            or history._store is not prepared._store or history._pin != prepared._pin
            or history._incarnation != prepared._incarnation):
        raise StoreIntegrityError('unpublished promotion has a different canonical source')
    state = dict(prepared.__dict__)
    state['_value_validator'] = history._value_validator
    state['_batch_validator'] = history._batch_validator
    history._clear_cache()
    # Both concrete pure-Python MutableSequence implementations have the same
    # dict/weakref layout. No second canonical object is registered or exposed.
    history.__class__ = LazyOrderedSequence
    history.__dict__ = state
    return history
