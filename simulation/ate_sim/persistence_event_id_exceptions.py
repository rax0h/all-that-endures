"""Paged edits to a captured exact consecutive event-ID prefix.

The public facade retains identity. Its two internal histories publish through
the existing hybrid transaction; they are never independent current links.
"""
from collections.abc import MutableSet
from bisect import bisect_left

from .incremental_store import StoreIntegrityError
from .persistence_event_ids import EventIdSet, EXCEPTION_TAG
from .persistence_lazy_nested_history import HistoryReference, immutable_value


def checked_descriptor(value):
    if (type(value) is not tuple or len(value) != 5 or value[0] != EXCEPTION_TAG
            or type(value[1]) is not int or value[1] < 0
            or type(value[2]) is not HistoryReference or value[2].kind != 'sequence'
            or type(value[3]) is not HistoryReference or value[3].kind != 'set'
            or value[2].incarnation == value[3].incarnation
            or type(value[4]) is not int or value[4] < 0):
        raise StoreIntegrityError('invalid exceptional event-ID descriptor')
    return value


class PagedEventIdExceptions(MutableSet):
    __hash__ = None

    def __init__(self, end, removed, added, *, expected_length=None):
        self.prefix = EventIdSet.from_range_descriptor(end)
        self.removed, self.added = removed, added
        if len(removed) > end or (expected_length is not None and len(self) != expected_length):
            raise StoreIntegrityError('exceptional event-ID counts disagree')

    @property
    def histories(self):
        return self.removed, self.added

    def descriptor(self):
        return (EXCEPTION_TAG, self.prefix.range_end, self.removed.storage_reference(),
                self.added.storage_reference(), len(self))

    def __len__(self):
        return self.prefix.range_end - len(self.removed) + len(self.added)

    def __contains__(self, value):
        # Native range probes include bool/float and hash/equality objects.
        if value in self.prefix:
            representative = self._prefix_representative(value)
            if not self._removed_contains(representative):
                return True
        if immutable_value(value):
            return value in self.added
        return self._additional_probe(value) is not _MISSING

    def _additional_probe(self, value):
        # Unsupported hash/equality probes retain native behavior. Their
        # explicit comparison work traverses only additional exceptions.
        if isinstance(value, set):
            value = frozenset(value)
        hashed = hash(value)
        return next((item for item in self.added
                     if hash(item) == hashed and (item is value or item == value)), _MISSING)

    def _prefix_representative(self, value):
        if type(value) in (int, bool, float):
            return int(value)
        return hash(value)

    def _removed_contains(self, value):
        position = bisect_left(self.removed, value)
        return position < len(self.removed) and self.removed[position] == value

    def _remove_prefix_value(self, value):
        position = bisect_left(self.removed, value)
        if position == len(self.removed) or self.removed[position] != value:
            self.removed.insert(position, value)

    def __iter__(self):
        for value in range(1, self.prefix.range_end + 1):
            if not self._removed_contains(value):
                yield value
        yield from self.added

    def add(self, value):
        hash(value)
        if value in self:
            return
        if type(value) is int and value in self.prefix:
            del self.removed[bisect_left(self.removed, value)]
        else:
            # Keep True/1.0 as the representative after deleting integer1.
            self.added.add(value)

    def discard(self, value):
        if value in self.prefix:
            representative = self._prefix_representative(value)
            if not self._removed_contains(representative):
                self._remove_prefix_value(representative)
                return
        if not immutable_value(value):
            value = self._additional_probe(value)
            if value is _MISSING:
                return
        self.added.discard(value)

    def remove(self, value):
        if value not in self:
            raise KeyError(value)
        self.discard(value)

    def pop(self):
        if self.added:
            return self.added.pop()
        end, count = self.prefix.range_end, len(self.removed)
        if end == count:
            raise KeyError('pop from an empty set')
        if count and self.removed[-1] == end:
            # Sorted holes have monotone value-rank. Locate the consecutive
            # removed suffix without walking every hole in that suffix.
            low, high, target = 0, count, end - count + 1
            while low < high:
                middle = (low + high) // 2
                if self.removed[middle] - middle < target:
                    low = middle + 1
                else:
                    high = middle
            end = self.removed[low] - 1
        self._remove_prefix_value(end)
        return end

    def diagnostics(self):
        return {'prefix_end': self.prefix.range_end, 'removed': self.removed.diagnostics(),
                'added': self.added.diagnostics()}


_MISSING = object()
