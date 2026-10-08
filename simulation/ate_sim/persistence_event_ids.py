"""Exact event-ID set facade; normal consecutive authority stays compact.

This class is deliberately not a set subclass: CPython copies a set subclass's
native storage in set(subclass), ignoring overridden iteration. Persistence
integration must encode the compact descriptor during ordinary saves, and
materialize only for explicit portable export/detach operations.
"""

from collections.abc import MutableSet, Set
import operator
import sys


RANGE_TAG = "event-ids-range/v1"
AUTHORITY_REFERENCE = ('event-id-authority-ref/v1',)


class EventIdSet(MutableSet):
    __hash__ = None

    def __init__(self, values=()):
        self._guard_callback = None
        self._changed_callback = None
        self._member_visits = 0
        self._install_values(set(values))

    def _install_values(self, values):
        if not values:
            self._end, self._exact = 0, None
        elif all(type(value) is int and value > 0 for value in values):
            end = max(values)
            if len(values) == end:
                self._end, self._exact = end, None
            else:
                self._end, self._exact = None, values
        else:
            self._end, self._exact = None, values

    @classmethod
    def from_checked_values(cls, values):
        return cls(values)

    @classmethod
    def from_range_descriptor(cls, end):
        if type(end) is not int or end < 0:
            raise ValueError("range end must be an exact nonnegative int")
        result = cls()
        result._end = end
        return result

    @property
    def range_end(self):
        return self._end

    def descriptor(self):
        return None if self._end is None else (RANGE_TAG, self._end)

    def bind(self, guard, changed):
        self._guard_callback = guard
        self._changed_callback = changed

    def _guard(self):
        if self._guard_callback is not None:
            self._guard_callback()

    def _changed(self):
        if self._changed_callback is not None:
            self._changed_callback()

    def __len__(self):
        return len(self._exact) if self._end is None else self._end

    def __iter__(self):
        values = iter(self._exact) if self._end is None else iter(range(1, self._end + 1))
        expected_length = len(self)

        def visit():
            for value in values:
                if len(self) != expected_length:
                    raise RuntimeError("Set changed size during iteration")
                self._member_visits += 1
                yield value
            if len(self) != expected_length:
                raise RuntimeError("Set changed size during iteration")
        return visit()

    def __contains__(self, value):
        if self._end is None:
            return value in self._exact
        if type(value) in (int, bool):
            return 1 <= value <= self._end
        if type(value) is float:
            return value.is_integer() and 1 <= value <= self._end
        try:
            hashed = hash(value)
        except TypeError:
            if isinstance(value, set):
                # Native set membership permits an unhashable set probe by
                # treating it as a frozenset. A range contains no such value.
                return False
            raise
        if self._end < sys.hash_info.modulus:
            return 1 <= hashed <= self._end and hashed == value
        # Exotic explicit probes into enormous virtual ranges retain native
        # hash/equality semantics; ordinary exact integer probes stay O(1).
        return any(hash(item) == hashed and item == value for item in self)

    def add(self, value):
        self._guard()
        hash(value)  # add, unlike membership, rejects unhashable set probes.
        if value in self:
            return
        if self._end is not None and type(value) is int and value == self._end + 1:
            self._end += 1
        else:
            if self._end is not None:
                self._exact, self._end = set(self), None
            self._exact.add(value)
        self._changed()

    def discard(self, value):
        self._guard()
        if value not in self:
            return
        if self._end is not None and value == self._end:
            self._end -= 1
        else:
            if self._end is not None:
                self._exact, self._end = set(self), None
            self._exact.discard(value)
        self._changed()

    def remove(self, value):
        self._guard()
        if value not in self:
            raise KeyError(value)
        if self._end is not None and value == self._end:
            self._end -= 1
        else:
            if self._end is not None:
                self._exact, self._end = set(self), None
            self._exact.remove(value)
        self._changed()

    def pop(self):
        self._guard()
        if not self:
            raise KeyError("pop from an empty set")
        if self._end is not None:
            result = self._end
            self._end -= 1
        else:
            result = self._exact.pop()
        self._changed()
        return result

    def clear(self):
        self._guard()
        if self:
            self._end, self._exact = 0, None
            self._changed()

    def _update(self, name, *others, guarded=False):
        if not guarded:
            self._guard()
        before = set(self)
        result = before.copy()
        try:
            getattr(result, name)(*others)
        finally:
            # Preserve native partial update/difference on failing iterables,
            # and don't suppress representative changes through equality.
            representatives = {value: value for value in before}
            missing = object()
            changed = before != result or any(
                representatives.get(value, missing) is not value for value in result
            )
            if changed:
                self._install_values(result)
                self._changed()

    def update(self, *others):
        self._update("update", *others)

    def intersection_update(self, *others):
        self._update("intersection_update", *others)

    def difference_update(self, *others):
        self._update("difference_update", *others)

    def symmetric_difference_update(self, other):
        self._update("symmetric_difference_update", other)

    def copy(self):
        return set(self)

    def union(self, *others):
        return set(self).union(*others)

    def intersection(self, *others):
        return set(self).intersection(*others)

    def difference(self, *others):
        return set(self).difference(*others)

    def symmetric_difference(self, other):
        return set(self).symmetric_difference(other)

    def isdisjoint(self, other):
        return all(value not in self for value in other)

    def issubset(self, other):
        return set(self).issubset(other)

    def issuperset(self, other):
        return set(self).issuperset(other)

    @staticmethod
    def _operator_operand(other):
        return isinstance(other, (set, frozenset, EventIdSet))

    def _binary(self, other, op, reflected=False):
        if not self._operator_operand(other):
            return NotImplemented
        other = set(other) if isinstance(other, EventIdSet) else other
        return op(other, set(self)) if reflected else op(set(self), other)

    def __or__(self, other): return self._binary(other, operator.or_)
    def __and__(self, other): return self._binary(other, operator.and_)
    def __sub__(self, other): return self._binary(other, operator.sub)
    def __xor__(self, other): return self._binary(other, operator.xor)
    def __ror__(self, other): return self._binary(other, operator.or_, True)
    def __rand__(self, other): return self._binary(other, operator.and_, True)
    def __rsub__(self, other): return self._binary(other, operator.sub, True)
    def __rxor__(self, other): return self._binary(other, operator.xor, True)

    def _inplace(self, other, name):
        self._guard()
        if not self._operator_operand(other):
            return NotImplemented
        self._update(name, other, guarded=True)
        return self

    def __ior__(self, other): return self._inplace(other, "update")
    def __iand__(self, other): return self._inplace(other, "intersection_update")
    def __isub__(self, other): return self._inplace(other, "difference_update")
    def __ixor__(self, other): return self._inplace(other, "symmetric_difference_update")

    def _compare(self, other, op):
        if not isinstance(other, Set):
            return NotImplemented
        return op(set(self), set(other))

    def __eq__(self, other): return self._compare(other, operator.eq)
    def __le__(self, other): return self._compare(other, operator.le)
    def __lt__(self, other): return self._compare(other, operator.lt)
    def __ge__(self, other): return self._compare(other, operator.ge)
    def __gt__(self, other): return self._compare(other, operator.gt)

    def __repr__(self):
        return repr(set(self))

    def materialize(self, memo):
        if id(self) not in memo:
            memo[id(self)] = set(self)
        return memo[id(self)]

    def diagnostics(self):
        return {
            "resident_members": 0 if self._end is not None else len(self._exact),
            "member_visits": self._member_visits,
            "range_end": self._end,
        }
