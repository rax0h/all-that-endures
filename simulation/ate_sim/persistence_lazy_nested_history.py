"""Checked incarnation-owned typed history; publication belongs to the session."""
from collections import OrderedDict
from collections.abc import MutableSequence, MutableMapping, MutableSet, Mapping, Set
from dataclasses import dataclass
import operator
import weakref

from .incremental_store import StoreFormatError, StoreIntegrityError, Membership
from .persistence_lazy_store import VersionChange, _query_checksum
from .persistence_lazy_budget import CleanCacheOwner, resident_bytes

DESCRIPTOR_NAMESPACE = 'aux.lazy.nested.descriptors'
PAGE_NAMESPACE = 'aux.lazy.nested.list_pages'
ENTRY_NAMESPACE = 'aux.lazy.nested.entries'
REFERENCE_TAG = 'typed-history/v1'
RECORD_SCHEMA = 1
PAGE_SIZE = 128
CACHE_PAGES = 4


@dataclass(frozen=True, slots=True)
class HistoryReference:
    kind: str
    incarnation: int

    def __post_init__(self):
        if self.kind not in ('list', 'map', 'set', 'sequence') or type(self.incarnation) is not int or self.incarnation <= 0:
            raise ValueError('invalid typed history reference')


def reference(value):
    return (type(value) is HistoryReference and value.kind in ('list', 'map', 'set', 'sequence')
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


class LazyHistoryList(CleanCacheOwner, MutableSequence):
    """Typed list with bounded point/tail operations and explicit whole edits."""

    __hash__ = None
    _kind = 'list'

    def __init__(self, store, pin, incarnation, *, guard=None, changed=None,
                 initial_values=None, cache_budget=None):
        if type(incarnation) is not int or incarnation <= 0:
            raise ValueError('invalid nested history incarnation')
        self._store, self._pin, self._incarnation = store, pin, incarnation
        self._guard, self._changed = guard, changed
        self._read_guard = None
        self._value_validator = None
        self._batch_validator = None
        self._sorting_values = None
        self._initialize_cache(cache_budget)
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
        if self._value_validator is not None:
            self._value_validator(value)
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
            self._cache_budget.touch(self, number)
            return self._cache[number]
        value = checked_value(self._store, self._pin, PAGE_NAMESPACE, (self._incarnation, number))
        expected = min(PAGE_SIZE, self._base_length - number * PAGE_SIZE)
        if type(value) is not tuple or len(value) != expected or any(not immutable_value(item) for item in value):
            raise StoreIntegrityError('invalid nested list page')
        self._page_loads += 1
        self._cache_value(number, value, CACHE_PAGES)
        return value

    def _page(self, number):
        if number not in self._dirty_pages:
            if number * PAGE_SIZE < self._base_length:
                old = self._read_page(number)
                self._baseline_page_bytes[number] = self._store.codec.encode(tuple(old))
                self._dirty_pages[number] = list(old)
                self._drop_clean(number)
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
            value = [self._validate(item) for item in value]
            values = list(self)
            values[index] = value
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
        if self._batch_validator is not None:
            values = self._batch_validator(values)
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
        self._clear_cache()

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
                else:
                    self._dirty_pages.pop(number, None)
                    self._baseline_page_bytes.pop(number, None)
                continue
            value = tuple(page)
            if len(value) != min(PAGE_SIZE, self._length - number * PAGE_SIZE):
                raise StoreIntegrityError('incomplete nested list page')
            if self._store.codec.encode(value) == self._baseline_page_bytes.get(number):
                self._dirty_pages.pop(number, None)
                self._baseline_page_bytes.pop(number, None)
                continue
            out.append(VersionChange(PAGE_NAMESPACE, key, value, record_schema=RECORD_SCHEMA))
        return tuple(out)

    def accept_save(self, pin):
        self._pin = pin
        self._base_length = self._length
        self._new = False
        self._dirty_pages.clear()
        self._baseline_page_bytes.clear()
        self._clear_cache()

    def diagnostics(self):
        return {'length': self._length, 'page_loads': self._page_loads,
                'cached_pages': len(self._cache), 'dirty_pages': len(self._dirty_pages),
                'clean_bytes': self._cache_bytes,
                'dirty_bytes': resident_bytes((self._dirty_pages, self._baseline_page_bytes)),
                'cached_values': sum(len(page) for page in self._cache.values())}


def equality_key(value):
    """Canonical storage key for native equality, preserving payload keys."""
    if not immutable_value(value):
        raise TypeError('typed history keys must be immutable schema values')
    hash(value)
    if type(value) is bool:
        return int(value)
    if type(value) is float and value.is_integer():
        return int(value)
    if type(value) is tuple:
        return tuple(equality_key(item) for item in value)
    if type(value) is frozenset:
        return frozenset(equality_key(item) for item in value)
    return value


def initial_scalar_changes(incarnation, kind, values, codec):
    if kind not in ('map', 'set'):
        raise ValueError('invalid scalar history kind')
    values = dict(values) if kind == 'map' else {key: None for key in values}
    changes = [VersionChange(DESCRIPTOR_NAMESPACE, incarnation, (kind, len(values), len(values)), record_schema=RECORD_SCHEMA)]
    for ordinal, (key, value) in enumerate(values.items()):
        canonical = equality_key(key)
        if not immutable_value(value):
            raise TypeError('typed history values must be immutable schema values')
        codec.encode((canonical, key, value))
        changes.append(VersionChange(ENTRY_NAMESPACE, (incarnation, canonical), (ordinal, key, value),
            record_schema=RECORD_SCHEMA, memberships=(Membership('incarnation', incarnation, ordinal),)))
    return tuple(changes)


def checked_scalar_entry(store, pin, incarnation, canonical):
    owns_snapshot = not getattr(store, '_active_read_transaction', False)
    generation = store._read_snapshot_start(pin) if owns_snapshot else pin.captured_head
    key = store.codec.encode((incarnation, canonical))
    try:
        row = store._visible_record_row(generation, ENTRY_NAMESPACE, key)
        order = store._visible_order(ENTRY_NAMESPACE, key, generation)
        if row is None:
            dangling = store.db.execute('SELECT 1 FROM lazy_query_versions WHERE namespace=? AND record_key=? '
                'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) LIMIT 1',
                (ENTRY_NAMESPACE, key, generation, generation)).fetchone()
            store._metadata_rows += int(dangling is not None)
            if order is not None or dangling:
                raise StoreIntegrityError('nested scalar absence has dangling authority')
            return None
        value, schema, *_rest, memberships = store._check_record_row(ENTRY_NAMESPACE, key, row, decode=True)
        if (schema != RECORD_SCHEMA or order is None or type(value) is not tuple or len(value) != 3
                or type(value[0]) is not int or value[0] < 0 or not immutable_value(value[1])
                or not immutable_value(value[2]) or store.codec.encode(equality_key(value[1])) != store.codec.encode(canonical)
                or memberships != (('incarnation', incarnation, value[0]),)):
            raise StoreIntegrityError('invalid nested scalar entry')
        encoded_incarnation = store.codec.encode(incarnation)
        rows = store.db.execute('SELECT valid_from,valid_to,row_checksum FROM lazy_query_versions '
            'WHERE namespace=? AND index_name=? AND index_value=? AND record_key=? AND ordinal=? '
            'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) LIMIT 2',
            (ENTRY_NAMESPACE, 'incarnation', encoded_incarnation, key, value[0], generation, generation)).fetchall()
        store._metadata_rows += len(rows)
        if len(rows) != 1 or rows[0][2] != _query_checksum(ENTRY_NAMESPACE, 'incarnation', encoded_incarnation,
                key, value[0], rows[0][0], rows[0][1]):
            raise StoreIntegrityError('invalid nested scalar membership witness')
        return value
    finally:
        if owns_snapshot:
            store._read_snapshot_end()


class _HistoryIterator:
    def __init__(self, history, entries, *, reverse=False):
        self._history = history
        keys = [entry[1] for entry in entries]
        self._state = dict.fromkeys(keys) if history._kind == 'map' else set(keys)
        self._iterator = reversed(self._state) if reverse else iter(self._state)

    def __iter__(self):
        return self

    def __next__(self):
        self._history._ensure()
        return next(self._iterator)

    def added(self, key):
        if self._history._kind == 'map':
            self._state[key] = None
        else:
            self._state.add(key)

    def removed(self, key):
        if self._history._kind == 'map':
            del self._state[key]
        else:
            self._state.remove(key)


class _ScalarHistory(CleanCacheOwner):
    _kind = None
    __hash__ = None

    def __init__(self, store, pin, incarnation, *, initial_values=None, cache_budget=None):
        if type(incarnation) is not int or incarnation <= 0:
            raise ValueError('invalid nested history incarnation')
        self._store, self._pin, self._incarnation = store, pin, incarnation
        self._guard = self._changed = self._read_guard = None
        self._initialize_cache(cache_budget)
        self._iterators = weakref.WeakSet()
        self._dirty_entries, self._baseline_bytes = {}, {}
        self._entry_loads = self._structure_revision = 0
        self._new = initial_values is not None
        if self._new:
            self._count = self._base_count = self._next_ordinal = self._base_next = 0
            values = dict(initial_values) if self._kind == 'map' else {key: None for key in initial_values}
            for key, value in values.items():
                self._set(key, value)
        else:
            value = checked_value(store, pin, DESCRIPTOR_NAMESPACE, incarnation)
            if (type(value) is not tuple or len(value) != 3 or value[0] != self._kind
                    or type(value[1]) is not int or value[1] < 0 or type(value[2]) is not int
                    or value[2] < value[1]):
                raise StoreIntegrityError('invalid nested scalar descriptor')
            _, self._count, self._next_ordinal = value
            self._base_count, self._base_next = self._count, self._next_ordinal

    def bind(self, guard, changed, read_guard=None):
        self._guard, self._changed, self._read_guard = guard, changed, read_guard
        return self

    def storage_reference(self):
        return HistoryReference(self._kind, self._incarnation)

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

    def _canonical(self, key):
        key = equality_key(key)
        self._store.codec.encode(key)
        return key

    def _baseline(self, canonical):
        if canonical in self._cache:
            self._cache.move_to_end(canonical)
            self._cache_budget.touch(self, canonical)
            return self._cache[canonical]
        value = None if self._new else checked_scalar_entry(self._store, self._pin, self._incarnation, canonical)
        if value is not None:
            if value[0] >= self._base_next or (self._kind == 'set' and value[2] is not None):
                raise StoreIntegrityError('nested scalar entry exceeds descriptor')
            self._entry_loads += 1
        self._cache_value(canonical, value, 256)
        return value

    def _entry(self, canonical):
        return self._dirty_entries[canonical] if canonical in self._dirty_entries else self._baseline(canonical)

    def _remember_baseline(self, canonical):
        if canonical not in self._baseline_bytes:
            baseline = self._baseline(canonical)
            self._baseline_bytes[canonical] = None if baseline is None else self._store.codec.encode(baseline)

    def _journal(self, canonical, entry):
        encoded = None if entry is None else self._store.codec.encode(entry)
        if encoded == self._baseline_bytes[canonical]:
            self._dirty_entries.pop(canonical, None)
            self._baseline_bytes.pop(canonical, None)
        else:
            self._dirty_entries[canonical] = entry
        self._drop_clean(canonical)

    def _set(self, key, value):
        canonical = self._canonical(key)
        if not immutable_value(value):
            raise TypeError('typed history values must be immutable schema values')
        self._store.codec.encode(value)
        old = self._entry(canonical)
        self._remember_baseline(canonical)
        if old is None:
            entry = (self._next_ordinal, key, value)
            self._next_ordinal += 1
            self._count += 1
            self._structure_revision += 1
            for iterator in self._iterators:
                iterator.added(key)
        else:
            entry = (old[0], old[1], value)
        self._journal(canonical, entry)

    def _delete(self, key):
        canonical = self._canonical(key)
        old = self._entry(canonical)
        if old is None:
            raise KeyError(key)
        self._remember_baseline(canonical)
        self._journal(canonical, None)
        self._count -= 1
        self._structure_revision += 1
        for iterator in self._iterators:
            iterator.removed(old[1])
        # Reclaim only unpublished trailing ordinals, including add/remove.
        self._next_ordinal = max((entry[0] + 1 for entry in self._dirty_entries.values() if entry is not None), default=self._base_next)
        self._next_ordinal = max(self._base_next, self._next_ordinal)
        return old

    def __len__(self):
        self._ensure()
        return self._count

    def __contains__(self, key):
        self._ensure()
        return self._entry(self._canonical(key)) is not None

    def _ordered_entries(self):
        self._ensure()
        rows = () if self._new else self._store.query_memberships(self._pin, ENTRY_NAMESPACE, 'incarnation', self._incarnation,
            exclude_keys=((self._incarnation, key) for key in self._dirty_entries))
        entries = []
        for key, ordinal in rows:
            if type(key) is not tuple or len(key) != 2 or key[0] != self._incarnation:
                raise StoreIntegrityError('nested scalar membership addresses wrong child')
            entry = self._entry(key[1])
            if entry is None or entry[0] != ordinal:
                raise StoreIntegrityError('nested scalar membership disagrees with entry')
            entries.append(entry)
        entries.extend(entry for entry in self._dirty_entries.values() if entry is not None)
        if len(entries) != self._count or len({entry[0] for entry in entries}) != len(entries):
            raise StoreIntegrityError('nested scalar descriptor count/order mismatch')
        return sorted(entries, key=lambda entry: entry[0])

    def __iter__(self):
        iterator = _HistoryIterator(self, self._ordered_entries())
        self._iterators.add(iterator)
        return iterator

    def pending_changes(self):
        self._ensure()
        changes = []
        if self._new or (self._count, self._next_ordinal) != (self._base_count, self._base_next):
            changes.append(VersionChange(DESCRIPTOR_NAMESPACE, self._incarnation, (self._kind, self._count, self._next_ordinal), record_schema=RECORD_SCHEMA))
        for canonical, entry in sorted(self._dirty_entries.items(), key=lambda item: self._store.codec.encode(item[0])):
            changes.append(VersionChange(ENTRY_NAMESPACE, (self._incarnation, canonical), entry, record_schema=RECORD_SCHEMA,
                delete=entry is None, memberships=() if entry is None else (Membership('incarnation', self._incarnation, entry[0]),)))
        return tuple(changes)

    def accept_save(self, pin):
        self._pin = pin
        self._base_count, self._base_next = self._count, self._next_ordinal
        self._new = False
        self._dirty_entries.clear()
        self._baseline_bytes.clear()
        self._clear_cache()

    def diagnostics(self):
        return {'length': self._count, 'entry_loads': self._entry_loads,
                'clean_bytes': self._cache_bytes,
                'dirty_bytes': resident_bytes((self._dirty_entries, self._baseline_bytes)),
                'cached_entries': len(self._cache), 'dirty_entries': len(self._dirty_entries)}


class LazyHistoryMap(_ScalarHistory, MutableMapping):
    _kind = 'map'
    __hash__ = None

    def __getitem__(self, key):
        self._ensure()
        entry = self._entry(self._canonical(key))
        if entry is None:
            raise KeyError(key)
        return entry[2]

    def __setitem__(self, key, value):
        self._mutation()
        self._set(key, value)
        self._notify()

    def __delitem__(self, key):
        self._mutation()
        self._delete(key)
        self._notify()

    def copy(self):
        return dict(self.items())

    @classmethod
    def fromkeys(cls, iterable, value=None):
        return dict.fromkeys(iterable, value)

    def update(self, *args, **kwargs):
        self._mutation()
        super().update(*args, **kwargs)

    def pop(self, key, *default):
        self._mutation()
        if len(default) > 1:
            raise TypeError('pop expected at most 2 arguments')
        try:
            value = self[key]
        except KeyError:
            if default:
                return default[0]
            raise
        del self[key]
        return value

    def setdefault(self, key, default=None):
        self._mutation()
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def clear(self):
        self._mutation()
        for key in list(self):
            del self[key]

    def popitem(self):
        self._mutation()
        entries = self._ordered_entries()
        if not entries:
            raise KeyError('popitem(): dictionary is empty')
        key = entries[-1][1]
        return key, self.pop(key)

    def __reversed__(self):
        iterator = _HistoryIterator(self, self._ordered_entries(), reverse=True)
        self._iterators.add(iterator)
        return iterator

    def __or__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        return self.copy() | dict(other)

    def __ror__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        return dict(other) | self.copy()

    def __ior__(self, other):
        self._mutation()
        self.update(other)
        return self

    def materialize(self, memo=None):
        memo = {} if memo is None else memo
        if id(self) not in memo:
            memo[id(self)] = self.copy()
        return memo[id(self)]


class LazyHistorySet(_ScalarHistory, MutableSet):
    _kind = 'set'
    __hash__ = None

    @classmethod
    def _from_iterable(cls, values):
        return set(values)

    def add(self, value):
        self._mutation()
        hash(value)
        self._set(value, None)
        self._notify()

    def discard(self, value):
        self._mutation()
        if type(value) is set:
            value = frozenset(value)
        if value in self:
            self._delete(value)
        self._notify()

    def remove(self, value):
        self._mutation()
        if type(value) is set:
            value = frozenset(value)
        self._delete(value)
        self._notify()

    def __and__(self, other):
        if not isinstance(other, Set):
            return NotImplemented
        if len(self) < len(other):
            return {value for value in self if value in other}
        return {value for value in other if value in self}

    __rand__ = __and__

    def __contains__(self, value):
        if type(value) is set:
            value = frozenset(value)
        return super().__contains__(value)

    def pop(self):
        self._mutation()
        try:
            value = next(iter(self))
        except StopIteration:
            raise KeyError('pop from an empty set') from None
        self.remove(value)
        return value

    def clear(self):
        self._mutation()
        for value in list(self):
            self.remove(value)

    def __ior__(self, other):
        self._mutation()
        if not isinstance(other, Set):
            return NotImplemented
        self.update(other)
        return self

    def __isub__(self, other):
        self._mutation()
        if not isinstance(other, Set):
            return NotImplemented
        self.difference_update(other)
        return self

    def __iand__(self, other):
        self._mutation()
        if not isinstance(other, Set):
            return NotImplemented
        self.intersection_update(other)
        return self

    def __ixor__(self, other):
        self._mutation()
        if not isinstance(other, Set):
            return NotImplemented
        self.symmetric_difference_update(other)
        return self

    def intersection(self, *others):
        if not others:
            return set(self)
        result = self & others[0] if isinstance(others[0], Set) else {value for value in others[0] if value in self}
        for other in others[1:]:
            result.intersection_update(other)
        return result

    def update(self, *others):
        self._mutation()
        for values in others:
            for value in values:
                self.add(value)

    def difference_update(self, *others):
        self._mutation()
        for values in others:
            for value in values:
                self.discard(value)

    def intersection_update(self, *others):
        self._mutation()
        remaining = self.intersection(*others)
        for value in list(self):
            if value not in remaining:
                self.discard(value)

    def symmetric_difference_update(self, other):
        self._mutation()
        for value in set(other):
            if value in self:
                self.remove(value)
            else:
                self.add(value)

    def union(self, *others):
        result = set(self)
        result.update(*others)
        return result

    def difference(self, *others):
        result = set(self)
        result.difference_update(*others)
        return result

    def symmetric_difference(self, other):
        return set(self).symmetric_difference(other)

    def issubset(self, other):
        return set(self).issubset(other)

    def issuperset(self, other):
        return all(value in self for value in other)

    def copy(self):
        return set(self)

    def materialize(self, memo=None):
        memo = {} if memo is None else memo
        if id(self) not in memo:
            memo[id(self)] = set(self)
        return memo[id(self)]


from .persistence_lazy_sequence import LazyOrderedSequence

HISTORY_CLASSES = {'list': LazyHistoryList, 'map': LazyHistoryMap, 'set': LazyHistorySet,
                   'sequence': LazyOrderedSequence}
HISTORY_TYPES = tuple(HISTORY_CLASSES.values())


def has_pending_overlay(history):
    """Inspect unsaved state without loading pages or freezing a sequence."""
    if type(history) not in HISTORY_TYPES:
        raise TypeError('expected typed history')
    if history._new:
        return True
    if type(history) is LazyHistoryList:
        return bool(history._dirty_pages) or history._length != history._base_length
    if type(history) in (LazyHistoryMap, LazyHistorySet):
        return bool(history._dirty_entries) or (
            history._count, history._next_ordinal) != (history._base_count, history._base_next)
    return bool(history._dirty) or history._store.codec.encode(
        history._descriptor()) != history._base_descriptor
