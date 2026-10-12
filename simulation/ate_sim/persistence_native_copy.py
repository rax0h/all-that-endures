"""Explicit finite native input copy, with no persistent identity authority.

Only declared source classes are normalized. The existing runtime validates and
admits the result; ordinary admission never calls this full-graph operation.
"""
from .core import Event
from .event_log import FrozenDict, FrozenList
from .record_index import RecordTable
from .persistence_schema import RECORD_FIELDS
from .persistence_lazy_nested_history import immutable_value, HISTORY_TYPES
from .incremental_store import StoreError


def copy_native_input(value, *, publisher=None):
    """Clone actual input using one sharing memo, leaving all source state intact.

    Mutable source tracking/index metadata is intentionally absent from the
    standalone output. Nested EventLog partition authority and arbitrary Python
    subclasses are outside this concrete finite-value contract.
    """
    from .persistence_tracking import (
        TrackedDict, TrackedList, TrackedSet, _RootDict, _RootList,
        _RootSet, _RootRecordTable, _binding,
    )
    from .persistence_record_runtime import record_backing
    from .persistence_adapters import _check_record
    from .persistence_event_ids import EventIdSet
    from .persistence_lazy_household_members import LazyHouseholdMembers
    dictionaries = (dict, TrackedDict, _RootDict, RecordTable, _RootRecordTable, FrozenDict)
    lists = (list, TrackedList, _RootList, FrozenList, LazyHouseholdMembers)
    sets = (set, TrackedSet, _RootSet, EventIdSet)
    memo, active = {}, set()

    def check_tracker(tracker):
        tracker._ensure_active()
        if publisher is None or tracker is not publisher._eager_tracker:
            raise StoreError('cross-session native copy input requires a separate coherent source capture')

    def clone(source):
        cls = type(source)
        if immutable_value(source):
            return source
        ident = id(source)
        if ident in active:
            raise TypeError('cyclic native copy input is outside the typed schema')
        if ident in memo:
            return memo[ident]
        if cls not in (*dictionaries, *lists, *sets, *HISTORY_TYPES, tuple) and cls not in RECORD_FIELDS:
            raise TypeError('native copy input has an undeclared source class')
        # Read existing backing leases, never fire mutation/index callbacks.
        backing = record_backing(source) if cls in RECORD_FIELDS else None
        if backing is not None:
            backing._ensure()
            if backing._runtime.session() is not publisher:
                raise StoreError('cross-session native record copy requires a coherent source capture')
        binding = _binding(source)
        if binding is not None:
            check_tracker(binding.session)
        tracker = getattr(source, '_session', None) if cls in (TrackedDict, TrackedList, TrackedSet,
            _RootDict, _RootList, _RootSet, _RootRecordTable) else None
        if tracker is not None:
            check_tracker(tracker)
        if cls in HISTORY_TYPES or cls is LazyHouseholdMembers:
            source._ensure()
            if publisher is None or source._store is not publisher.store or source._pin != publisher.pin:
                raise StoreError('cross-session native history copy requires a coherent source capture')
        active.add(ident)
        try:
            if cls in RECORD_FIELDS:
                _check_record(source)
                if cls.__dataclass_params__.frozen:
                    raise TypeError('native copy input has an invalid immutable value record')
                result = object.__new__(cls)
                memo[ident] = result
                for field in RECORD_FIELDS[cls]:
                    object.__setattr__(result, field, clone(getattr(source, field)))
                if cls is Event and '_sealed' in vars(source):
                    state = vars(source)['_sealed']
                    if type(state) is not bool:
                        raise TypeError('Event seal state must be a boolean')
                    object.__setattr__(result, '_sealed', state)
            elif cls is tuple:
                result = tuple(clone(child) for child in source)
            else:
                kind = source._kind if cls in HISTORY_TYPES else (
                    'map' if cls in dictionaries else 'list' if cls in lists else 'set')
                role = getattr(source, '_descriptor_kind', kind) if cls in HISTORY_TYPES else None
                readonly_map = cls is FrozenDict or role == 'frozen-map'
                readonly_list = cls is FrozenList or role == 'frozen-list'
                result = (FrozenDict() if readonly_map else FrozenList() if readonly_list else
                          {} if kind == 'map' else [] if kind in ('list', 'sequence') else set())
                memo[ident] = result
                if kind == 'map':
                    if cls in (FrozenDict, FrozenList) and vars(source):
                        raise TypeError('frozen snapshot has unclassified non-field state')
                    for key, child in source.items():
                        dict.__setitem__(result, clone(key), clone(child))
                elif kind in ('list', 'sequence'):
                    if cls is FrozenList and vars(source):
                        raise TypeError('frozen snapshot has unclassified non-field state')
                    list.extend(result, (clone(child) for child in source))
                else:
                    result.update(clone(child) for child in source)
            memo[ident] = result
            return result
        finally:
            active.remove(ident)

    return clone(value)
