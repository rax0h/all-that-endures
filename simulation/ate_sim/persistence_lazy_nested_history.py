"""Checked incarnation-owned typed history; publication belongs to the session."""
from collections import OrderedDict
from collections.abc import MutableSequence
from dataclasses import dataclass
import operator

from .incremental_store import StoreFormatError, StoreIntegrityError
from .persistence_lazy_store import VersionChange

DESCRIPTOR_NAMESPACE = 'aux.lazy.nested.descriptors'
PAGE_NAMESPACE = 'aux.lazy.nested.list_pages'
REFERENCE_TAG = 'typed-history/v1'
RECORD_SCHEMA = 1
PAGE_SIZE = 128
CACHE_PAGES = 4


@dataclass(frozen=True, slots=True)
class HistoryReference:
    kind: str
    incarnation: int

    def __post_init__(self):
        if self.kind != 'list' or type(self.incarnation) is not int or self.incarnation <= 0:
            raise ValueError('invalid typed history reference')


def reference(value):
    return (type(value) is HistoryReference and value.kind == 'list'
            and type(value.incarnation) is int and value.incarnation > 0)


def immutable_value(value):
    if value is None or type(value) in (bool, int, float, str, bytes):
        return True
    return type(value) in (tuple, frozenset) and all(immutable_value(item) for item in value)


def checked_value(store, pin, namespace, key):
    if getattr(store, '_active_read_transaction', False):
        if store._require_pin(pin) != pin.captured_head:
            raise StoreIntegrityError('nested history open pin moved')
        typed_key = store.codec.encode(key)
        row = store._visible_record_row(pin.captured_head, namespace, typed_key)
        if row is None:
            raise StoreIntegrityError('nested history authority is absent')
        value, schema, *_ = store._check_record_row(namespace, typed_key, row, decode=True)
        if schema != RECORD_SCHEMA:
            raise StoreFormatError('nested history schema mismatch')
        return value
    try:
        return store.read_version(pin, namespace, key, expected_record_schema=RECORD_SCHEMA).value
    except KeyError as exc:
        raise StoreIntegrityError('nested history authority is absent') from exc


def initial_list_changes(incarnation, values, codec):
    """Explicit conversion/new-value construction; never an ordinary open."""
    values = tuple(values)
    for value in values:
        if not immutable_value(value):
            raise TypeError('typed history values must be immutable schema values')
        codec.encode(value)
    return (VersionChange(DESCRIPTOR_NAMESPACE, incarnation, ('list', len(values), len(values)), record_schema=RECORD_SCHEMA),) + tuple(
        VersionChange(PAGE_NAMESPACE, (incarnation, number // PAGE_SIZE), values[number:number + PAGE_SIZE], record_schema=RECORD_SCHEMA)
        for number in range(0, len(values), PAGE_SIZE)
    )


def checked_list_extent(store, pin, incarnation, length):
    owns_snapshot = not getattr(store, '_active_read_transaction', False)
    generation = store._read_snapshot_start(pin) if owns_snapshot else pin.captured_head
    try:
        def present(number):
            key = store.codec.encode((incarnation, number))
            order = store._visible_order(PAGE_NAMESPACE, key, generation)
            rows = store.db.execute(
                'SELECT valid_from FROM lazy_record_versions WHERE namespace=? AND typed_key=? '
                'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) LIMIT 2',
                (PAGE_NAMESPACE, key, generation, generation),
            ).fetchall()
            store._metadata_rows += len(rows)
            if len(rows) > 1 or bool(rows) != (order is not None):
                raise StoreIntegrityError('invalid nested list page extent authority')
            return bool(rows)
        pages = (length + PAGE_SIZE - 1) // PAGE_SIZE
        if (pages and not present(pages - 1)) or present(pages):
            raise StoreIntegrityError('invalid nested list page extent')
    finally:
        if owns_snapshot:
            store._read_snapshot_end()


class LazyHistoryList(MutableSequence):
    """Typed list with bounded point/tail operations and explicit whole edits."""

    __hash__ = None

    def __init__(self, store, pin, incarnation, *, guard=None, changed=None, initial_values=None):
        if type(incarnation) is not int or incarnation <= 0:
            raise ValueError('invalid nested history incarnation')
        self._store, self._pin, self._incarnation = store, pin, incarnation
        self._guard, self._changed = guard, changed
        self._read_guard = None
        self._sorting_values = None
        self._cache = OrderedDict()
        self._dirty_pages = {}
        self._baseline_page_bytes = {}
        self._page_loads = 0
        self._new = initial_values is not None
        if self._new:
            self._length = self._base_length = 0
            for value in initial_values:
                self._append(self._validate(value))
        else:
            value = checked_value(store, pin, DESCRIPTOR_NAMESPACE, incarnation)
            if (type(value) is not tuple or len(value) != 3 or value[0] != 'list'
                    or type(value[1]) is not int or value[1] < 0
                    or type(value[2]) is not int or value[2] != value[1]):
                raise StoreIntegrityError('invalid nested list descriptor')
            self._length = self._base_length = value[1]
            checked_list_extent(store, pin, incarnation, self._length)

    def bind(self, guard, changed, read_guard=None):
        self._guard, self._changed = guard, changed
        self._read_guard = read_guard
        return self

    def storage_reference(self):
        return HistoryReference('list', self._incarnation)

    def _ensure(self):
        self._store._ensure_open()
        if self._read_guard is not None:
            self._read_guard()

    def _mutation(self):
        self._ensure()
        if self._guard is not None:
            self._guard()

    def _notify(self):
        if self._changed is not None:
            self._changed()

    def _validate(self, value):
        if not immutable_value(value):
            raise TypeError('typed history values must be immutable schema values')
        self._store.codec.encode(value)
        return value

    def _normalize(self, index):
        index = operator.index(index)
        if index < 0:
            index += self._length
        if not 0 <= index < self._length:
            raise IndexError('list index out of range')
        return index

    def _read_page(self, number):
        if number in self._dirty_pages:
            return self._dirty_pages[number]
        if number in self._cache:
            self._cache.move_to_end(number)
            return self._cache[number]
        value = checked_value(self._store, self._pin, PAGE_NAMESPACE, (self._incarnation, number))
        expected = min(PAGE_SIZE, self._base_length - number * PAGE_SIZE)
        if type(value) is not tuple or len(value) != expected or any(not immutable_value(item) for item in value):
            raise StoreIntegrityError('invalid nested list page')
        self._page_loads += 1
        self._cache[number] = value
        while len(self._cache) > CACHE_PAGES:
            self._cache.popitem(last=False)
        return value

    def _page(self, number):
        if number not in self._dirty_pages:
            if number * PAGE_SIZE < self._base_length:
                old = self._read_page(number)
                self._baseline_page_bytes[number] = self._store.codec.encode(tuple(old))
                self._dirty_pages[number] = list(old)
            else:
                self._dirty_pages[number] = []
        return self._dirty_pages[number]

    def __len__(self):
        self._ensure()
        if self._sorting_values is not None:
            return len(self._sorting_values)
        return self._length

    def __getitem__(self, index):
        self._ensure()
        if self._sorting_values is not None:
            return self._sorting_values[index]
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self._length))]
        index = self._normalize(index)
        return self._read_page(index // PAGE_SIZE)[index % PAGE_SIZE]

    def __setitem__(self, index, value):
        self._mutation()
        if self._sorting_values is not None:
            self._sorting_values[index] = [self._validate(item) for item in value] if isinstance(index, slice) else self._validate(value)
            return
        if isinstance(index, slice):
            values = list(self)
            values[index] = [self._validate(item) for item in value]
            self._replace_all(values)
        else:
            index = self._normalize(index)
            value = self._validate(value)
            self._page(index // PAGE_SIZE)[index % PAGE_SIZE] = value
        self._notify()

    def __delitem__(self, index):
        self._mutation()
        if self._sorting_values is not None:
            del self._sorting_values[index]
            return
        if not isinstance(index, slice):
            index = self._normalize(index)
            if index == self._length - 1:
                self._page(index // PAGE_SIZE).pop()
                self._length -= 1
                self._notify()
                return
        values = list(self)
        del values[index]
        self._replace_all(values)
        self._notify()

    def _append(self, value):
        page = self._page(self._length // PAGE_SIZE)
        if len(page) != self._length % PAGE_SIZE:
            raise StoreIntegrityError('nested list append page is inconsistent')
        page.append(value)
        self._length += 1

    def append(self, value):
        self._mutation()
        if self._sorting_values is not None:
            self._sorting_values.append(self._validate(value))
            return
        self._append(self._validate(value))
        self._notify()

    def extend(self, values):
        self._mutation()
        if self._sorting_values is not None:
            if values is self:
                values = tuple(self)
            self._sorting_values.extend(self._validate(value) for value in values)
            return
        if values is self:
            values = tuple(self)
        # Like list.extend, successful items remain when an iterator fails.
        try:
            for value in values:
                self._append(self._validate(value))
        finally:
            self._notify()

    def insert(self, index, value):
        self._mutation()
        index, value = operator.index(index), self._validate(value)
        if self._sorting_values is not None:
            self._sorting_values.insert(index, value)
            return
        index = max(0, index + self._length) if index < 0 else min(index, self._length)
        if index == self._length:
            self._append(value)
        else:
            values = list(self)
            values.insert(index, value)
            self._replace_all(values)
        self._notify()

    def _replace_all(self, values):
        old_pages = (max(self._length, self._base_length) + PAGE_SIZE - 1) // PAGE_SIZE
        for number in range(max(old_pages, (len(values) + PAGE_SIZE - 1) // PAGE_SIZE)):
            if number * PAGE_SIZE < self._base_length and number not in self._baseline_page_bytes:
                self._baseline_page_bytes[number] = self._store.codec.encode(tuple(self._read_page(number)))
            self._dirty_pages[number] = list(values[number * PAGE_SIZE:(number + 1) * PAGE_SIZE])
        self._length = len(values)
        self._cache.clear()

    def __iter__(self):
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def copy(self):
        return list(self)

    def reverse(self):
        self._mutation()
        if self._sorting_values is not None:
            self._sorting_values.reverse()
            return
        self._replace_all(list(reversed(list(self))))
        self._notify()

    def sort(self, *, key=None, reverse=False):
        self._mutation()
        if self._sorting_values is not None:
            self._sorting_values.sort(key=key, reverse=reverse)
            return
        values = list(self)
        self._sorting_values = values
        try:
            values.sort(key=key, reverse=reverse)
        finally:
            self._sorting_values = None
            self._replace_all(values)
            self._notify()

    def __eq__(self, other):
        if isinstance(other, (list, LazyHistoryList)):
            return list(self) == list(other)
        return NotImplemented

    def _compare(self, other, operation):
        if not isinstance(other, (list, LazyHistoryList)):
            return NotImplemented
        return operation(list(self), list(other))

    def __lt__(self, other):
        return self._compare(other, operator.lt)

    def __le__(self, other):
        return self._compare(other, operator.le)

    def __gt__(self, other):
        return self._compare(other, operator.gt)

    def __ge__(self, other):
        return self._compare(other, operator.ge)

    def __add__(self, other):
        if not isinstance(other, (list, LazyHistoryList)):
            return NotImplemented
        return list(self) + list(other)

    def __radd__(self, other):
        if not isinstance(other, list):
            return NotImplemented
        return other + list(self)

    def __mul__(self, count):
        return list(self) * count

    __rmul__ = __mul__

    def __imul__(self, count):
        self._mutation()
        if self._sorting_values is not None:
            self._sorting_values *= operator.index(count)
            return self
        self._replace_all(list(self) * operator.index(count))
        self._notify()
        return self

    def materialize(self, memo=None):
        memo = {} if memo is None else memo
        if id(self) not in memo:
            memo[id(self)] = list(self)
        return memo[id(self)]

    def pending_changes(self):
        self._ensure()
        out = []
        if self._new or self._length != self._base_length:
            out.append(VersionChange(DESCRIPTOR_NAMESPACE, self._incarnation, ('list', self._length, self._length), record_schema=RECORD_SCHEMA))
        for number, page in sorted(self._dirty_pages.items()):
            key = (self._incarnation, number)
            if number * PAGE_SIZE >= self._length:
                if number * PAGE_SIZE < self._base_length:
                    out.append(VersionChange(PAGE_NAMESPACE, key, delete=True, record_schema=RECORD_SCHEMA))
                continue
            value = tuple(page)
            if len(value) != min(PAGE_SIZE, self._length - number * PAGE_SIZE):
                raise StoreIntegrityError('incomplete nested list page')
            if self._store.codec.encode(value) == self._baseline_page_bytes.get(number):
                continue
            out.append(VersionChange(PAGE_NAMESPACE, key, value, record_schema=RECORD_SCHEMA))
        return tuple(out)

    def accept_save(self, pin):
        self._pin = pin
        self._base_length = self._length
        self._new = False
        self._dirty_pages.clear()
        self._baseline_page_bytes.clear()
        self._cache.clear()

    def diagnostics(self):
        return {'length': self._length, 'page_loads': self._page_loads,
                'cached_pages': len(self._cache), 'dirty_pages': len(self._dirty_pages),
                'cached_values': sum(len(page) for page in self._cache.values())}
