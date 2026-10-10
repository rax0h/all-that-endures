"""MVCC counted sequences. The session's hybrid transaction is the only publisher.

Main-tree rank, permanent occurrence ID and leaf slot are separate authorities.
Member AVL trees preserve relative occurrence order through main-tree balancing.
Their roots live in an authenticated compressed radix directory: absence is a
checked path proof, never an absent SQL row interpreted as an empty result.
"""
from collections import OrderedDict, defaultdict
from collections.abc import MutableSequence
from contextlib import contextmanager
import math
import operator
import sys

from .incremental_store import StoreConflictError, StoreIntegrityError, _framed_sha
from .persistence_lazy_store import VersionChange
from .persistence_lazy_budget import SharedCacheBudget, CleanCacheOwner
from .persistence_history_types import HistoryMemberTypes

DESCRIPTOR_NAMESPACE = 'aux.lazy.sequence.descriptors'
NODE_NAMESPACE = 'aux.lazy.sequence.nodes'
PARENT_NAMESPACE = 'aux.lazy.sequence.parents'
LOCATOR_NAMESPACE = 'aux.lazy.sequence.occurrences'
MEMBER_NAMESPACE = 'aux.lazy.sequence.members'
DIRECTORY_NAMESPACE = 'aux.lazy.sequence.member_directory'
NAMESPACES = (DESCRIPTOR_NAMESPACE, NODE_NAMESPACE, PARENT_NAMESPACE,
              LOCATOR_NAMESPACE, MEMBER_NAMESPACE, DIRECTORY_NAMESPACE)
LEAF_SIZE = 128
FANOUT = 32
SCHEMA = 1
CACHE_ENTRIES = 64
CACHE_BYTES = 8 * 1024 * 1024
_MISSING = object()


def _positive(value):
    return type(value) is int and value > 0


def _checksum(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _link(link):
    return (type(link) is tuple and len(link) == 4 and _positive(link[0])
            and type(link[1]) is int and link[1] >= 0 and _checksum(link[2])
            and type(link[3]) is int and 0 <= link[3] < 64)


def _directory_link(link):
    return (type(link) is tuple and len(link) == 3 and type(link[0]) is bytes
            and len(link[0]) <= 32 and _positive(link[1]) and _checksum(link[2]))


def _resident(value):
    """Conservative recursive object accounting; not process RSS."""
    if type(value) in (tuple, list):
        return sys.getsizeof(value) + sum(_resident(item) for item in value)
    return sys.getsizeof(value)


def _chunks(values, capacity):
    # Balanced initial conversion avoids an underfull final non-root page.
    groups = max(1, math.ceil(len(values) / capacity))
    size, remainder = divmod(len(values), groups)
    start = 0
    for group in range(groups):
        end = start + size + (group < remainder)
        yield tuple(values[start:end])
        start = end


class LazyOrderedSequence(CleanCacheOwner, MutableSequence):
    """Positive integer IDs with exact list order, duplicate and equality rules.

    Explicit conversion/bulk operations may visit all values. Ordinary positional
    edits touch tree paths and at most two bounded leaves. All clean sidecars use
    one entry/byte budget; dirty overlays are separately accounted. Freezing a
    save prohibits further edits until that exact plan is acknowledged.
    """
    __hash__ = None
    _kind = 'sequence'

    def __init__(self, store, pin, incarnation, *, initial_values=None,
                 guard=None, changed=None, read_guard=None, value_mode=None,
                 cache_budget=None, checked_types=None, recursive=False):
        if not _positive(incarnation):
            raise ValueError('invalid sequence incarnation')
        self._store, self._pin, self._incarnation = store, pin, incarnation
        self._guard, self._changed, self._read_guard = guard, changed, read_guard
        self._value_validator = None
        self._recursive = recursive
        self._recursive_runtime = None
        self._recursive_preflight_leaves = set()
        self._batch_validator = None
        self._cache = OrderedDict()
        self._cache_bytes = 0
        self._cache_budget = cache_budget if cache_budget is not None else SharedCacheBudget()
        self._dirty, self._baseline = {}, {}
        self._prepared = self._accepted = None
        self._mutation_depth = 0
        self._new = initial_values is not None
        self._member_types = HistoryMemberTypes(store, pin, incarnation, 'sequence', new=self._new, required=checked_types)
        if value_mode not in (None, 'integer_ids', 'native'):
            raise ValueError('invalid sequence value mode')
        self._value_mode = value_mode or 'integer_ids'
        self._requested_value_mode = value_mode
        self._next_node = self._next_occurrence = 1
        self._length = self._revision = 0
        self._root = self._directory = None
        self._ensure()
        if self._new:
            with store.read_snapshot(pin):
                if self._raw(DESCRIPTOR_NAMESPACE, incarnation, absent=True) is not _MISSING:
                    raise StoreConflictError('sequence incarnation already has persisted backing')
            values = tuple(self._validate(v) for v in initial_values)
            self._build(values)
            self._member_types.replace_all(values)
            self._base_descriptor = None
        else:
            with store.read_snapshot(pin):
                descriptor = self._read(DESCRIPTOR_NAMESPACE, incarnation)
            self._load_descriptor(descriptor)
            self._base_descriptor = store.codec.encode(descriptor)
        self._member_types.check_length(self._length)

    def bind(self, guard, changed, read_guard=None):
        self._guard, self._changed, self._read_guard = guard, changed, read_guard
        return self

    def _ensure(self):
        self._store._ensure_open()
        if self._read_guard is not None:
            self._read_guard()
        self._store._require_pin(self._pin)

    def _validate(self, value):
        if self._value_validator is not None:
            self._value_validator(value)
        if self._recursive_runtime is not None:
            value = self._recursive_runtime.admit(value)
        if not self._valid_value(value):
            if self._value_mode == 'native':
                raise TypeError('sequence values must be immutable schema values')
            raise TypeError('sequence IDs must be positive integers')
        return value

    def _valid_value(self, value):
        if self._value_mode == 'integer_ids':
            return _positive(value)
        from .persistence_lazy_nested_history import immutable_value, stored_value
        return stored_value(value) if self._recursive else immutable_value(value)

    @staticmethod
    def _member_key(value):
        if _positive(value):
            return value
        if type(value) is bool:
            return 1 if value else None
        if type(value) is float and value > 0 and value.is_integer():
            return int(value)
        return None

    def _descriptor(self):
        fields = (self._incarnation, self._root, self._length,
                  self._next_occurrence, self._next_node, self._revision, self._directory)
        if self._value_mode == 'integer_ids':
            return ('ordered-sequence/v1', *fields)
        return ('ordered-sequence/v2', *fields, 'native')

    def _load_descriptor(self, value):
        if (type(value) is not tuple or not (
            (len(value) == 8 and value[0] == 'ordered-sequence/v1')
            or (len(value) == 9 and value[0] == 'ordered-sequence/v2' and value[8] == 'native'))):
            raise StoreIntegrityError('invalid counted sequence descriptor kind')
        mode = 'integer_ids' if len(value) == 8 else 'native'
        if self._requested_value_mode is not None and self._requested_value_mode != mode:
            raise StoreIntegrityError('sequence descriptor disagrees with required value mode')
        if (type(value[1]) is not int or value[1] != self._incarnation or not _link(value[2])
            or type(value[3]) is not int or value[3] < 0 or value[2][1] != value[3]
            or not _positive(value[4]) or not _positive(value[5])
            or value[2][0] >= value[5] or type(value[6]) is not int or value[6] < 0
            or (value[7] is not None and not _directory_link(value[7]))
            or (value[3] == 0 and value[7] is not None)
            or (mode == 'integer_ids' and value[3] > 0 and value[7] is None)):
            raise StoreIntegrityError('invalid counted sequence descriptor')
        self._value_mode = mode
        self._root, self._length, self._next_occurrence, self._next_node, self._revision, self._directory = value[2:8]

    @contextmanager
    def _mutation(self):
        self._ensure()
        if self._prepared is not None:
            raise StoreConflictError('sequence has a frozen unacknowledged save plan')
        if not self._mutation_depth:
            self._recursive_preflight_leaves.clear()
        self._mutation_depth += 1
        try:
            if self._guard is not None:
                self._guard()
            state = self._descriptor(), self._dirty.copy(), self._baseline.copy(), self._member_types.counts
            try:
                with self._store.read_snapshot(self._pin):
                    yield
            except BaseException:
                descriptor, self._dirty, self._baseline, self._member_types.counts = state
                self._load_descriptor(descriptor)
                self._clear_cache()
                raise
            if self._descriptor() != state[0]:
                self._revision += 1
                if self._changed is not None:
                    self._changed()
        finally:
            self._mutation_depth -= 1
            if not self._mutation_depth:
                self._recursive_preflight_leaves.clear()

    def _raw(self, namespace, key, *, absent=False):
        try:
            value = self._store.read_version(self._pin, namespace, key, expected_record_schema=SCHEMA).value
        except KeyError:
            if absent:
                return _MISSING
            raise StoreIntegrityError(f'missing sequence authority: {namespace}') from None
        return value

    def _read(self, namespace, key):
        marker = namespace, key
        if marker in self._dirty:
            value = self._dirty[marker]
            if value is None:
                raise StoreIntegrityError('sequence reached locally retired authority')
            return value
        if marker in self._cache:
            value, size = self._cache.pop(marker)
            self._cache[marker] = value, size
            self._cache_budget.touch(self, marker)
            return value
        value = self._raw(namespace, key)
        size = _resident(marker) + _resident(value)
        if size <= CACHE_BYTES:
            self._cache[marker] = value, size
            self._cache_bytes += size
            self._cache_budget.admit(self, marker, size)
            while len(self._cache) > CACHE_ENTRIES or self._cache_bytes > CACHE_BYTES:
                oldest = next(iter(self._cache))
                self._cache_budget.forget(self, oldest)
                self._budget_evict(oldest)
        return value

    def _budget_evict(self, marker):
        cached = self._cache.pop(marker, None)
        if cached is not None:
            self._cache_bytes -= cached[1]

    def _clear_cache(self):
        self._cache_budget.release(self)
        self._cache.clear()
        self._cache_bytes = 0

    def _put(self, namespace, key, value):
        marker = namespace, key
        if marker not in self._baseline:
            old = _MISSING if self._new else self._raw(namespace, key, absent=True)
            self._baseline[marker] = None if old is _MISSING else self._store.codec.encode(old)
        baseline = self._baseline[marker]
        encoded = None if value is None else self._store.codec.encode(value)
        if baseline == encoded:
            self._dirty.pop(marker, None)
            self._baseline.pop(marker, None)
        else:
            self._dirty[marker] = value
        self._cache_budget.forget(self, marker)
        self._budget_evict(marker)

    def _digest(self, namespace, key, value):
        return _framed_sha(b'counted-sequence-node/v1', self._store.codec.encode((namespace, key, value)))

    def _allocate_node(self):
        result = self._next_node
        self._next_node += 1
        return result

    def _allocate_occurrence(self):
        result = self._next_occurrence
        self._next_occurrence += 1
        return result

    def _node_commit(self, node_id, value):
        if type(value) is not tuple or len(value) != 2 or type(value[1]) is not tuple:
            raise StoreIntegrityError('invalid sequence node shape')
        entries = value[1]
        if value[0] == 'leaf':
            if (len(entries) > LEAF_SIZE or any(type(e) is not tuple or len(e) != 2
                or not _positive(e[0]) or e[0] >= self._next_occurrence or not self._valid_value(e[1]) for e in entries)
                or len({e[0] for e in entries}) != len(entries)):
                raise StoreIntegrityError('invalid sequence leaf occurrences')
            count, height = len(entries), 0
        elif value[0] == 'branch':
            if (not 1 <= len(entries) <= FANOUT or any(not _link(e) or e[1] < 1
                or e[0] >= self._next_node for e in entries)
                or len({e[0] for e in entries}) != len(entries)
                or len({e[3] for e in entries}) != 1):
                raise StoreIntegrityError('invalid sequence branch counts/children')
            count, height = sum(e[1] for e in entries), entries[0][3] + 1
        else:
            raise StoreIntegrityError('unknown sequence node kind')
        return node_id, count, self._digest(NODE_NAMESPACE, (self._incarnation, node_id), value), height

    def _nread(self, link, parent=_MISSING):
        if not _link(link) or link[0] >= self._next_node:
            raise StoreIntegrityError('invalid sequence node link')
        value = self._read(NODE_NAMESPACE, (self._incarnation, link[0]))
        if self._node_commit(link[0], value) != link:
            raise StoreIntegrityError('sequence node count/digest disagreement')
        if (value[0] == 'leaf' and self._recursive_runtime is not None and self._mutation_depth
                and link[0] not in self._recursive_preflight_leaves):
            self._recursive_runtime.validate_physical_children(
                (NODE_NAMESPACE, (self._incarnation, link[0])), value)
            self._recursive_preflight_leaves.add(link[0])
        if parent is not _MISSING:
            actual = self._read(PARENT_NAMESPACE, (self._incarnation, link[0]))
            if (type(actual) is not tuple or len(actual) != 2
                or (actual[0] is not None and not _positive(actual[0]))
                or type(actual[1]) is not int or not 0 <= actual[1] < FANOUT or actual != parent):
                raise StoreIntegrityError('sequence reciprocal parent disagreement')
        return value

    def _nwrite(self, node_id, kind, entries):
        value = kind, tuple(entries)
        link = self._node_commit(node_id, value)
        self._put(NODE_NAMESPACE, (self._incarnation, node_id), value)
        if kind == 'leaf':
            if self._recursive_runtime is not None and self._mutation_depth:
                # This operation validated the source leaves and incoming D.
                # Temporary rewritten/split leaves have no catalog placement
                # until the complete value journal succeeds.
                self._recursive_preflight_leaves.add(node_id)
            for slot, (occurrence, _) in enumerate(entries):
                self._put(LOCATOR_NAMESPACE, (self._incarnation, occurrence), (node_id, slot))
        else:
            for slot, child in enumerate(entries):
                self._put(PARENT_NAMESPACE, (self._incarnation, child[0]), (node_id, slot))
        return link

    def _check_leaf_locators(self, node_id, entries):
        # Validate before overwriting moved projections. Keep only the baseline
        # bytes for this bounded affected leaf; _nwrite/_delete prunes unchanged
        # rows or transfers them into the dirty journal, without a second read.
        for slot, (occurrence, _) in enumerate(entries):
            key = self._incarnation, occurrence
            actual = self._read(LOCATOR_NAMESPACE, key)
            if (type(actual) is not tuple or len(actual) != 2 or type(actual[0]) is not int
                or type(actual[1]) is not int or actual != (node_id, slot)):
                raise StoreIntegrityError('moved sequence locator disagrees with leaf')
            marker = LOCATOR_NAMESPACE, key
            if marker not in self._baseline:
                self._baseline[marker] = self._store.codec.encode(actual)

    def _check_child_parents(self, node_id, children):
        for slot, child in enumerate(children):
            key = self._incarnation, child[0]
            actual = self._read(PARENT_NAMESPACE, key)
            if (type(actual) is not tuple or len(actual) != 2 or type(actual[0]) is not int
                or type(actual[1]) is not int or actual != (node_id, slot)):
                raise StoreIntegrityError('moved sequence child parent disagrees with branch')
            marker = PARENT_NAMESPACE, key
            if marker not in self._baseline:
                self._baseline[marker] = self._store.codec.encode(actual)

    def _retire_node(self, node_id):
        self._put(NODE_NAMESPACE, (self._incarnation, node_id), None)
        self._put(PARENT_NAMESPACE, (self._incarnation, node_id), None)

    def _set_root(self, link):
        self._root = link
        self._length = link[1]
        self._put(PARENT_NAMESPACE, (self._incarnation, link[0]), (None, 0))

    def _build(self, values):
        entries = tuple((self._allocate_occurrence(), value) for value in values)
        level = [self._nwrite(self._allocate_node(), 'leaf', part) for part in _chunks(entries, LEAF_SIZE)]
        while len(level) > 1:
            level = [self._nwrite(self._allocate_node(), 'branch', part) for part in _chunks(level, FANOUT)]
        self._set_root(level[0])
        members = defaultdict(list)
        for occurrence, value in entries:
            key = self._member_key(value)
            if key is not None:
                members[key].append(occurrence)
        for value, occurrences in members.items():
            def build(start, end):
                if start == end:
                    return None
                middle = (start + end) // 2
                return self._mwrite(occurrences[middle], value, build(start, middle), build(middle + 1, end))
            self._dreplace(value, build(0, len(occurrences)))

    def _child(self, children, rank, inserting=False):
        for slot, link in enumerate(children):
            if rank < link[1] or (inserting and slot == len(children) - 1 and rank == link[1]):
                return slot, rank
            rank -= link[1]
        raise StoreIntegrityError('sequence rank exceeds committed child counts')

    def _locate(self, rank):
        link, parent = self._root, (None, 0)
        while True:
            kind, entries = self._nread(link, parent)
            if kind == 'leaf':
                return link, rank, entries[rank]
            slot, rank = self._child(entries, rank)
            parent, link = (link[0], slot), entries[slot]

    def _index(self, index):
        index = operator.index(index)
        if index < 0:
            index += self._length
        if not 0 <= index < self._length:
            raise IndexError('list index out of range')
        return index

    def __len__(self):
        self._ensure()
        return self._length

    @property
    def tree_height(self):
        return self._root[3]

    def __getitem__(self, index):
        self._ensure()
        if isinstance(index, slice):
            return [self[k] for k in range(*index.indices(self._length))]
        with self._store.read_snapshot(self._pin):
            leaf, _slot, (occurrence, value) = self._locate(self._index(index))
            if self._recursive_runtime is not None:
                value = self._recursive_runtime.decode(value, (NODE_NAMESPACE, (self._incarnation, leaf[0])), (('key', occurrence),))
            return self._checked_owner_value(value)

    def _checked_owner_value(self, value):
        if self._value_validator is not None:
            try:
                self._value_validator(value)
            except TypeError as exc:
                raise StoreIntegrityError('stored history member violates its current owner type') from exc
        return value

    def occurrence_id(self, index):
        self._ensure()
        with self._store.read_snapshot(self._pin):
            return self._locate(self._index(index))[2][0]

    def _occurrence(self, occurrence):
        if not _positive(occurrence) or occurrence >= self._next_occurrence:
            raise StoreIntegrityError('invalid sequence occurrence ID')
        locator = self._read(LOCATOR_NAMESPACE, (self._incarnation, occurrence))
        if (type(locator) is not tuple or len(locator) != 2 or not _positive(locator[0])
            or type(locator[1]) is not int or not 0 <= locator[1] < LEAF_SIZE):
            raise StoreIntegrityError('invalid sequence occurrence locator')
        node_id, slot = locator
        value = self._read(NODE_NAMESPACE, (self._incarnation, node_id))
        link = self._node_commit(node_id, value)
        if value[0] != 'leaf' or slot >= link[1] or value[1][slot][0] != occurrence:
            raise StoreIntegrityError('sequence occurrence locator disagrees with leaf')
        rank = slot
        seen = {node_id}
        while node_id != self._root[0]:
            parent = self._read(PARENT_NAMESPACE, (self._incarnation, node_id))
            if (type(parent) is not tuple or len(parent) != 2 or not _positive(parent[0])
                or type(parent[1]) is not int or not 0 <= parent[1] < FANOUT
                or parent[0] in seen):
                raise StoreIntegrityError('invalid/cyclic sequence parent locator')
            parent_id, position = parent
            parent_value = self._read(NODE_NAMESPACE, (self._incarnation, parent_id))
            parent_link = self._node_commit(parent_id, parent_value)
            if (parent_value[0] != 'branch' or position >= len(parent_value[1])
                or parent_value[1][position] != link):
                raise StoreIntegrityError('sequence parent does not commit located child')
            rank += sum(child[1] for child in parent_value[1][:position])
            node_id, link = parent_id, parent_link
            seen.add(node_id)
            if len(seen) > self._root[3] + 1:
                raise StoreIntegrityError('sequence parent depth exceeds descriptor')
        if link != self._root or self._read(PARENT_NAMESPACE, (self._incarnation, node_id)) != (None, 0):
            raise StoreIntegrityError('sequence occurrence does not reach committed root')
        return rank, value[1][slot][1]

    def rank_of_occurrence(self, occurrence):
        self._ensure()
        with self._store.read_snapshot(self._pin):
            return self._occurrence(occurrence)[0]

    def _insert(self, rank, value):
        self._member_types.add(value)
        occurrence = self._allocate_occurrence()
        def edit(link, offset, parent):
            kind, items = self._nread(link, parent)
            items = list(items)
            if kind == 'leaf':
                self._check_leaf_locators(link[0], items)
                items.insert(offset, (occurrence, value))
                capacity = LEAF_SIZE
            else:
                self._check_child_parents(link[0], items)
                slot, offset = self._child(items, offset, True)
                items[slot:slot + 1] = edit(items[slot], offset, (link[0], slot))
                capacity = FANOUT
            if len(items) <= capacity:
                return [self._nwrite(link[0], kind, items)]
            middle = len(items) // 2
            return [self._nwrite(link[0], kind, items[:middle]),
                    self._nwrite(self._allocate_node(), kind, items[middle:])]
        roots = edit(self._root, rank, (None, 0))
        root = roots[0] if len(roots) == 1 else self._nwrite(self._allocate_node(), 'branch', roots)
        self._set_root(root)
        key = self._member_key(value)
        if key is not None:
            self._dreplace(key, self._minsert(self._dget(key), occurrence, key))

    def insert(self, index, value):
        index = operator.index(index)
        with self._mutation():
            value = self._validate(value)
            rank = min(self._length, max(0, index + self._length if index < 0 else index))
            self._insert(rank, value)

    def append(self, value):
        self.insert(self._length, value)

    def extend(self, values):
        input_error = None
        with self._mutation():
            if values is self:
                values = tuple(self)
            if self._batch_validator is not None:
                values = self._batch_validator(values)
            iterator = iter(values)
            while True:
                try:
                    value = next(iterator)
                except StopIteration:
                    break
                except BaseException as exc:
                    # Native list.extend retains the consumed prefix when
                    # caller input fails. Leave the checked mutation scope
                    # successfully so that prefix is journaled and notified.
                    input_error = exc
                    break
                # Invalid stored values or tree/index failures still leave
                # this scope exceptionally and roll back its entire journal.
                self._insert(self._length, self._validate(value))
        if input_error is not None:
            raise input_error

    def _rebalance(self, children, slot, parent_id):
        if len(children) < 2:
            return children
        node = self._nread(children[slot], (parent_id, slot))
        minimum = LEAF_SIZE // 2 if node[0] == 'leaf' else FANOUT // 2
        if len(node[1]) >= minimum:
            return children
        left = slot - 1 if slot else 0
        a, b = children[left:left + 2]
        av, bv = self._nread(a, (parent_id, left)), self._nread(b, (parent_id, left + 1))
        if av[0] != bv[0]:
            raise StoreIntegrityError('sequence siblings have different kinds')
        if av[0] == 'leaf':
            self._check_leaf_locators(a[0], av[1])
            self._check_leaf_locators(b[0], bv[1])
        else:
            self._check_child_parents(a[0], av[1])
            self._check_child_parents(b[0], bv[1])
        items = av[1] + bv[1]
        capacity = LEAF_SIZE if av[0] == 'leaf' else FANOUT
        if len(items) <= capacity:
            replacement = [self._nwrite(a[0], av[0], items)]
            self._retire_node(b[0])
        else:
            middle = len(items) // 2
            replacement = [self._nwrite(a[0], av[0], items[:middle]),
                           self._nwrite(b[0], bv[0], items[middle:])]
        children[left:left + 2] = replacement
        return children

    def _delete(self, rank):
        occurrence, value = self._locate(rank)[2]
        self._member_types.add(value, -1)
        key = self._member_key(value)
        if key is not None:
            self._dreplace(key, self._mdelete(self._dget(key), occurrence, key))
        def edit(link, offset, parent):
            kind, entries = self._nread(link, parent)
            entries = list(entries)
            if kind == 'leaf':
                self._check_leaf_locators(link[0], entries)
                del entries[offset]
            else:
                self._check_child_parents(link[0], entries)
                slot, offset = self._child(entries, offset)
                entries[slot] = edit(entries[slot], offset, (link[0], slot))
                entries = self._rebalance(entries, slot, link[0])
            return self._nwrite(link[0], kind, entries)
        root = edit(self._root, rank, (None, 0))
        node = self._nread(root)
        if node[0] == 'branch' and len(node[1]) == 1:
            self._retire_node(root[0])
            root = node[1][0]
        self._set_root(root)
        self._put(LOCATOR_NAMESPACE, (self._incarnation, occurrence), None)

    def __delitem__(self, index):
        with self._mutation():
            if isinstance(index, slice):
                for rank in sorted(range(*index.indices(self._length)), reverse=True):
                    self._delete(rank)
            else:
                self._delete(self._index(index))

    def _assign(self, rank, value):
        link, slot, (occurrence, old) = self._locate(rank)
        if type(old) is type(value) and (old is value or old == value):
            return
        self._member_types.add(old, -1)
        self._member_types.add(value)
        old_key, new_key = self._member_key(old), self._member_key(value)
        if old_key is not None:
            self._dreplace(old_key, self._mdelete(self._dget(old_key), occurrence, old_key))
        def edit(link, offset, parent):
            kind, entries = self._nread(link, parent)
            entries = list(entries)
            if kind == 'leaf':
                self._check_leaf_locators(link[0], entries)
                entries[offset] = occurrence, value
            else:
                self._check_child_parents(link[0], entries)
                position, offset = self._child(entries, offset)
                entries[position] = edit(entries[position], offset, (link[0], position))
            return self._nwrite(link[0], kind, entries)
        self._set_root(edit(self._root, rank, (None, 0)))
        if new_key is not None:
            self._dreplace(new_key, self._minsert(self._dget(new_key), occurrence, new_key))

    def __setitem__(self, index, value):
        with self._mutation():
            values = tuple(self._validate(v) for v in value) if isinstance(index, slice) else (self._validate(value),)
            if not isinstance(index, slice):
                self._assign(self._index(index), values[0])
                return
            start, stop, step = index.indices(self._length)
            positions = range(start, stop, step)
            if step != 1:
                if len(values) != len(positions):
                    raise ValueError(f'attempt to assign sequence of size {len(values)} to extended slice of size {len(positions)}')
                for rank, item in zip(positions, values):
                    self._assign(rank, item)
            else:
                for rank in reversed(positions):
                    self._delete(rank)
                for offset, item in enumerate(values):
                    self._insert(start + offset, item)

    def _stream(self, rank):
        """One bounded leaf plus an O(height) stack; no transaction across yield."""
        link, parent, stack = self._root, (None, 0), []
        while True:
            with self._store.read_snapshot(self._pin):
                kind, entries = self._nread(link, parent)
            if kind == 'branch':
                slot, rank = self._child(entries, rank)
                stack.append((link[0], entries, slot + 1))
                parent, link = (link[0], slot), entries[slot]
                continue
            for entry in entries[rank:]:
                self._ensure()
                yield entry
            rank = 0
            while stack:
                parent_id, children, position = stack.pop()
                if position < len(children):
                    stack.append((parent_id, children, position + 1))
                    parent, link = (parent_id, position), children[position]
                    break
            else:
                return

    def iter_occurrences(self):
        # A mutation restarts at the current logical rank, matching native list
        # iterator behavior. Stable iterations decode each main node only once.
        rank = 0
        while rank < len(self):
            revision, stream = self._revision, self._stream(rank)
            while rank < self._length and revision == self._revision:
                try:
                    entry = next(stream)
                except StopIteration:
                    return
                yield entry
                rank += 1

    def __iter__(self):
        for occurrence, value in self.iter_occurrences():
            if self._recursive_runtime is not None:
                from .persistence_lazy_nested_history import immutable_value
                if not immutable_value(value):
                    leaf, _slot = self._read(LOCATOR_NAMESPACE, (self._incarnation, occurrence))
                    value = self._recursive_runtime.decode(value, (NODE_NAMESPACE, (self._incarnation, leaf)), (('key', occurrence),))
            yield self._checked_owner_value(value)

    def __eq__(self, other):
        if not self._list_operand(other):
            return False
        return len(self) == len(other) and all(a is b or a == b for a, b in zip(self, other))

    def copy(self):
        return list(self)

    @staticmethod
    def _list_operand(value):
        from .persistence_lazy_nested_history import LazyHistoryList
        return isinstance(value, (list, LazyHistoryList, LazyOrderedSequence))

    def _compare(self, other, operation):
        return operation(list(self), list(other)) if self._list_operand(other) else NotImplemented

    def __lt__(self, other):
        return self._compare(other, operator.lt)

    def __le__(self, other):
        return self._compare(other, operator.le)

    def __gt__(self, other):
        return self._compare(other, operator.gt)

    def __ge__(self, other):
        return self._compare(other, operator.ge)

    def __add__(self, other):
        return list(self) + list(other) if self._list_operand(other) else NotImplemented

    def __radd__(self, other):
        return other + list(self) if isinstance(other, list) else NotImplemented

    def __mul__(self, count):
        return list(self) * operator.index(count)

    __rmul__ = __mul__

    def __imul__(self, count):
        self[:] = list(self) * operator.index(count)
        return self

    def reverse(self):
        self[:] = self[::-1]

    def sort(self, *, key=None, reverse=False):
        self[:] = sorted(self, key=key, reverse=reverse)

    # Ordered occurrence index. Relative order is unchanged by main-node moves.
    def _member_commit(self, occurrence, node):
        if (type(node) is not tuple or len(node) != 4 or node[0] != 'member/v1'
            or not _positive(node[1]) or any(c is not None and (not _link(c) or c[1] < 1)
                                            for c in node[2:])):
            raise StoreIntegrityError('invalid sequence member node')
        left, right = node[2:]
        if (any(c is not None and (c[0] == occurrence or c[0] >= self._next_occurrence) for c in (left, right))
            or (left is not None and right is not None and left[0] == right[0])):
            raise StoreIntegrityError('duplicate/unallocated sequence membership child')
        lh, rh = (left[3] if left else -1), (right[3] if right else -1)
        if abs(lh - rh) > 1:
            raise StoreIntegrityError('unbalanced sequence membership authority')
        count = 1 + (left[1] if left else 0) + (right[1] if right else 0)
        return occurrence, count, self._digest(MEMBER_NAMESPACE, (self._incarnation, occurrence), node), max(lh, rh) + 1

    def _mread(self, link, value):
        if not _link(link) or not 0 < link[0] < self._next_occurrence:
            raise StoreIntegrityError('invalid sequence member link')
        node = self._read(MEMBER_NAMESPACE, (self._incarnation, link[0]))
        if self._member_commit(link[0], node) != link or node[1] != value:
            raise StoreIntegrityError('sequence member count/digest/value disagreement')
        return node

    def _mwrite(self, occurrence, value, left, right):
        node = 'member/v1', value, left, right
        link = self._member_commit(occurrence, node)
        self._put(MEMBER_NAMESPACE, (self._incarnation, occurrence), node)
        return link

    @staticmethod
    def _height(link):
        return link[3] if link else -1

    def _mbalance(self, occurrence, value, left, right):
        lh, rh = self._height(left), self._height(right)
        if lh - rh > 1:
            _, _, ll, lr = self._mread(left, value)
            if self._height(ll) >= self._height(lr):
                return self._mwrite(left[0], value, ll, self._mwrite(occurrence, value, lr, right))
            _, _, lrl, lrr = self._mread(lr, value)
            return self._mwrite(lr[0], value, self._mwrite(left[0], value, ll, lrl),
                                self._mwrite(occurrence, value, lrr, right))
        if rh - lh > 1:
            _, _, rl, rr = self._mread(right, value)
            if self._height(rr) >= self._height(rl):
                return self._mwrite(right[0], value, self._mwrite(occurrence, value, left, rl), rr)
            _, _, rll, rlr = self._mread(rl, value)
            return self._mwrite(rl[0], value, self._mwrite(occurrence, value, left, rll),
                                self._mwrite(right[0], value, rlr, rr))
        return self._mwrite(occurrence, value, left, right)

    def _minsert(self, root, occurrence, value):
        wanted = self._occurrence(occurrence)[0]
        def edit(link, lower=-1, upper=self._length):
            if link is None:
                return self._mwrite(occurrence, value, None, None)
            _, _, left, right = self._mread(link, value)
            rank, actual = self._occurrence(link[0])
            if actual != value or not lower < rank < upper:
                raise StoreIntegrityError('sequence membership order/value disagreement')
            if occurrence == link[0]:
                raise StoreIntegrityError('duplicate sequence occurrence insertion')
            if wanted < rank:
                left = edit(left, lower, rank)
            else:
                right = edit(right, rank, upper)
            return self._mbalance(link[0], value, left, right)
        return edit(root)

    def _mdelete(self, root, occurrence, value):
        wanted = self._occurrence(occurrence)[0]
        def edit(link, target, rank_wanted, lower=-1, upper=self._length):
            if link is None:
                raise StoreIntegrityError('sequence member occurrence is missing')
            _, _, left, right = self._mread(link, value)
            rank, actual = self._occurrence(link[0])
            if actual != value or not lower < rank < upper:
                raise StoreIntegrityError('sequence membership order/value disagreement')
            if link[0] == target:
                self._put(MEMBER_NAMESPACE, (self._incarnation, target), None)
                if left is None:
                    return right
                if right is None:
                    return left
                successor = right
                while True:
                    successor_node = self._mread(successor, value)
                    if successor_node[2] is None:
                        break
                    successor = successor_node[2]
                successor_rank, actual = self._occurrence(successor[0])
                if actual != value or not rank < successor_rank < upper:
                    raise StoreIntegrityError('sequence membership successor order disagreement')
                new_right = edit(right, successor[0], successor_rank, rank, upper)
                return self._mbalance(successor[0], value, left, new_right)
            if rank_wanted < rank:
                left = edit(left, target, rank_wanted, lower, rank)
            else:
                right = edit(right, target, rank_wanted, rank, upper)
            return self._mbalance(link[0], value, left, right)
        return edit(root, occurrence, wanted)

    # Directory links commit the complete member-tree root, including count.
    def _member_hash(self, value):
        return bytes.fromhex(_framed_sha(b'sequence-member-key/v1', self._store.codec.encode(value)))

    def _directory_commit(self, prefix, node):
        if type(node) is not tuple or len(node) != 3:
            raise StoreIntegrityError('invalid sequence member directory node')
        if node[0] == 'directory-leaf/v1':
            if (not _positive(node[1]) or not _link(node[2]) or node[2][1] < 1
                or prefix != self._member_hash(node[1])):
                raise StoreIntegrityError('invalid sequence directory leaf commitment')
            count = 1
        elif node[0] == 'directory-branch/v1':
            if (node[1] != prefix or type(prefix) is not bytes or len(prefix) >= 32
                or type(node[2]) is not tuple or not 2 <= len(node[2]) <= 256):
                raise StoreIntegrityError('invalid sequence directory branch')
            previous, count = -1, 0
            for child in node[2]:
                if type(child) is not tuple or len(child) != 4:
                    raise StoreIntegrityError('invalid sequence directory child')
                slot, child_prefix, size, checksum = child
                if (type(slot) is not int or not previous < slot < 256
                    or not _directory_link(child[1:]) or not child_prefix.startswith(prefix)
                    or len(child_prefix) <= len(prefix) or child_prefix[len(prefix)] != slot):
                    raise StoreIntegrityError('invalid sequence directory child order/count')
                previous, count = slot, count + size
        else:
            raise StoreIntegrityError('unknown sequence member directory kind')
        return prefix, count, self._digest(DIRECTORY_NAMESPACE, (self._incarnation, prefix), node)

    def _dread(self, link):
        if not _directory_link(link):
            raise StoreIntegrityError('invalid sequence directory root/link')
        node = self._read(DIRECTORY_NAMESPACE, (self._incarnation, link[0]))
        if self._directory_commit(link[0], node) != link:
            raise StoreIntegrityError('sequence directory count/digest disagreement')
        return node

    def _dwrite(self, prefix, node):
        link = self._directory_commit(prefix, node)
        self._put(DIRECTORY_NAMESPACE, (self._incarnation, prefix), node)
        return link

    def _dget(self, value):
        wanted, link = self._member_hash(value), self._directory
        while link is not None:
            node = self._dread(link)
            if not wanted.startswith(link[0]):
                return None
            if node[0] == 'directory-leaf/v1':
                if node[1] != value:
                    raise StoreIntegrityError('sequence member directory key collision')
                return node[2]
            slot = wanted[len(link[0])]
            link = next((c[1:] for c in node[2] if c[0] == slot), None)
        return None

    def _dreplace(self, value, member_root):
        wanted = self._member_hash(value)
        def leaf():
            return self._dwrite(wanted, ('directory-leaf/v1', value, member_root))
        def join(a, b):
            length = 0
            while length < min(len(a[0]), len(b[0])) and a[0][length] == b[0][length]:
                length += 1
            if length == min(len(a[0]), len(b[0])):
                raise StoreIntegrityError('sequence member directory hash collision')
            prefix = a[0][:length]
            return self._dwrite(prefix, ('directory-branch/v1', prefix,
                tuple(sorted(((a[0][length], *a), (b[0][length], *b))))))
        def edit(link):
            if link is None:
                if member_root is None:
                    raise StoreIntegrityError('retiring absent sequence membership root')
                return leaf()
            prefix = link[0]
            node = self._dread(link)
            if not wanted.startswith(prefix):
                if member_root is None:
                    raise StoreIntegrityError('retiring absent sequence membership value')
                return join(link, leaf())
            if node[0] == 'directory-leaf/v1':
                if node[1] != value:
                    raise StoreIntegrityError('sequence member directory key collision')
                if member_root is None:
                    self._put(DIRECTORY_NAMESPACE, (self._incarnation, prefix), None)
                    return None
                return leaf()
            slot = wanted[len(prefix)]
            children = {c[0]: c[1:] for c in node[2]}
            result = edit(children.get(slot))
            if result is None:
                children.pop(slot, None)
            else:
                children[slot] = result
            if len(children) == 1:
                self._put(DIRECTORY_NAMESPACE, (self._incarnation, prefix), None)
                return next(iter(children.values()))
            return self._dwrite(prefix, ('directory-branch/v1', prefix,
                tuple((s, *child) for s, child in sorted(children.items()))))
        self._directory = edit(self._directory)

    def _first(self, value):
        link, lower, upper = self._dget(value), -1, self._length
        if link is None:
            return None
        while True:
            node = self._mread(link, value)
            rank, actual = self._occurrence(link[0])
            if actual != value or not lower < rank < upper:
                raise StoreIntegrityError('sequence first member order/value disagreement')
            if node[2] is None:
                return rank
            upper, link = rank, node[2]

    def occurrences(self, value):
        """Exact current ranks; candidate selection pays only for requested IDs."""
        self._ensure()
        with self._store.read_snapshot(self._pin):
            member = self._member_key(value)
            if member is None:
                return tuple(rank for rank, item in enumerate(self) if item is value or item == value)
            ranks = []
            seen = set()
            def visit(link, lower, upper):
                if link is None:
                    return
                if link[0] in seen:
                    raise StoreIntegrityError('duplicate/cyclic sequence membership node')
                seen.add(link[0])
                node = self._mread(link, member)
                rank, actual = self._occurrence(link[0])
                if actual != member or not lower < rank < upper:
                    raise StoreIntegrityError('sequence membership order/value disagreement')
                visit(node[2], lower, rank)
                ranks.append(rank)
                visit(node[3], rank, upper)
            visit(self._dget(member), -1, self._length)
            return tuple(ranks)

    def candidate_positions(self, values):
        with self._store.read_snapshot(self._pin):
            return tuple(sorted({rank for value in values for rank in self.occurrences(value)}))

    def remove(self, value):
        with self._mutation():
            member = self._member_key(value)
            rank = self._first(member) if member is not None else next(
                (rank for rank, item in enumerate(self) if item is value or item == value), None)
            if rank is None:
                raise ValueError('list.remove(x): x not in list')
            self._delete(rank)

    def prepare_delta(self, context=None):
        from .persistence_lazy_families import ParticipantDelta
        self._ensure()
        if self._mutation_depth:
            raise StoreConflictError('sequence save preparation is blocked during mutation')
        if self._prepared is not None:
            return self._prepared[0]
        descriptor = self._descriptor()
        changes = list(self._member_types.pending_changes(self._length)) + [VersionChange(ns, key, value, delete=value is None)
                   for (ns, key), value in self._dirty.items()]
        if self._store.codec.encode(descriptor) != self._base_descriptor:
            changes.append(VersionChange(DESCRIPTOR_NAMESPACE, self._incarnation, descriptor))
        delta = ParticipantDelta.freeze(self._store.codec, f'sequence:{self._incarnation}', version_changes=changes)
        if changes:
            self._prepared = delta, self._pin.captured_head
        return delta

    def validate_publication(self, delta, successor_pin):
        self._store._ensure_open()
        if self._accepted == (delta.fingerprint, successor_pin):
            self._store._require_pin(successor_pin)
            return
        if (self._prepared is None or delta != self._prepared[0]
            or successor_pin.token != self._pin.token
            or successor_pin.captured_head != self._prepared[1] + 1):
            raise StoreConflictError('sequence acknowledgement does not match frozen plan/generation')
        with self._store.read_snapshot(successor_pin):
            for change in delta.decode(self._store.codec)[0]:
                try:
                    value = self._store.read_version(successor_pin, change.namespace, change.key,
                                                     expected_record_schema=SCHEMA).value
                except KeyError:
                    if change.delete:
                        continue
                    raise StoreIntegrityError('missing frozen sequence publication') from None
                if change.delete or self._store.codec.encode(value) != self._store.codec.encode(change.value):
                    raise StoreIntegrityError('sequence publication disagrees with frozen bytes')

    def accept_delta(self, delta, successor_pin):
        if self._accepted == (delta.fingerprint, successor_pin):
            self._store._require_pin(successor_pin)
            return
        self.validate_publication(delta, successor_pin)
        self._pin = successor_pin
        self._new = False
        self._base_descriptor = self._store.codec.encode(self._descriptor())
        self._member_types.accept_save()
        self._dirty.clear()
        self._baseline.clear()
        self._clear_cache()
        self._accepted = delta.fingerprint, successor_pin
        self._prepared = None

    def abort_delta(self, delta, commit_token):
        """Thaw a checked unpublished plan, retaining every unsaved edit."""
        self._store._ensure_open()
        if (self._mutation_depth or self._prepared is None or delta != self._prepared[0]
            or self._pin.captured_head != self._prepared[1]):
            raise StoreConflictError('sequence abort does not match its frozen plan')
        from .persistence_lazy_publication_guard import checked_uncommitted_publication
        with checked_uncommitted_publication(self._store, self._pin, commit_token):
            self._prepared = None

    def diagnostics(self):
        return {'clean_entries': len(self._cache), 'clean_bytes': self._cache_bytes,
                'dirty_entries': len(self._dirty),
                'dirty_bytes': sum(_resident(k) + _resident(v) for k, v in self._dirty.items())
                    + sum(_resident(k) + _resident(v) for k, v in self._baseline.items()),
                'tree_height': self.tree_height, 'length': self._length}

    def storage_reference(self):
        from .persistence_lazy_nested_history import HistoryReference
        return HistoryReference('sequence', self._incarnation)

    def materialize(self, memo=None):
        from .persistence_lazy_nested_history import materialize_history_value
        memo = {} if memo is None else memo
        return materialize_history_value(self, memo)

    def pending_changes(self):
        return self.prepare_delta().decode(self._store.codec)[0]

    def accept_save(self, pin):
        if self._prepared is not None:
            self.accept_delta(self._prepared[0], pin)
        else:
            if self._dirty or self._new or self._store.codec.encode(self._descriptor()) != self._base_descriptor:
                raise StoreConflictError('dirty sequence has no frozen acknowledged plan')
            self._store._require_pin(pin)
            self._pin = pin
            self._clear_cache()

    def scrub(self):
        """Explicit full-history validation, including orphan/extra projections."""
        self._ensure()
        expected = {ns: set() for ns in NAMESPACES}
        expected[DESCRIPTOR_NAMESPACE].add(self._incarnation)
        occurrences, members = {}, defaultdict(list)
        with self._store.read_snapshot(self._pin):
            def visit(link, parent, root=False):
                key = self._incarnation, link[0]
                if key in expected[NODE_NAMESPACE]:
                    raise StoreIntegrityError('duplicate/cyclic main sequence node')
                expected[NODE_NAMESPACE].add(key)
                expected[PARENT_NAMESPACE].add(key)
                kind, entries = self._nread(link, parent)
                if not root and len(entries) < (LEAF_SIZE // 2 if kind == 'leaf' else FANOUT // 2):
                    raise StoreIntegrityError('underfull main sequence node')
                if root and kind == 'branch' and len(entries) < 2:
                    raise StoreIntegrityError('uncollapsed sequence root')
                if kind == 'leaf':
                    for slot, (occurrence, value) in enumerate(entries):
                        if occurrence in occurrences:
                            raise StoreIntegrityError('duplicate main sequence occurrence')
                        occurrences[occurrence] = len(occurrences), value
                        member_key = self._member_key(value)
                        if member_key is not None:
                            members[member_key].append(occurrence)
                        expected[LOCATOR_NAMESPACE].add((self._incarnation, occurrence))
                        if self._read(LOCATOR_NAMESPACE, (self._incarnation, occurrence)) != (link[0], slot):
                            raise StoreIntegrityError('sequence scrub locator disagreement')
                else:
                    for slot, child in enumerate(entries):
                        visit(child, (link[0], slot))
            visit(self._root, (None, 0), True)
            if len(occurrences) != self._length:
                raise StoreIntegrityError('sequence scrub descriptor count disagreement')
            found_members = {}
            def directory(link):
                key = self._incarnation, link[0]
                if key in expected[DIRECTORY_NAMESPACE]:
                    raise StoreIntegrityError('duplicate/cyclic sequence directory node')
                expected[DIRECTORY_NAMESPACE].add(key)
                node = self._dread(link)
                if node[0] == 'directory-branch/v1':
                    for child in node[2]: directory(child[1:])
                    return
                value, root = node[1:]
                order = []
                def member(link, lower, upper):
                    if link is None:
                        return
                    key = self._incarnation, link[0]
                    if key in expected[MEMBER_NAMESPACE]:
                        raise StoreIntegrityError('duplicate/cyclic sequence member node')
                    expected[MEMBER_NAMESPACE].add(key)
                    m = self._mread(link, value)
                    rank, actual = occurrences.get(link[0], (-1, None))
                    if actual != value or not lower < rank < upper:
                        raise StoreIntegrityError('sequence scrub member order disagreement')
                    member(m[2], lower, rank)
                    order.append(link[0])
                    member(m[3], rank, upper)
                member(root, -1, self._length)
                found_members[value] = order
            if self._directory is not None:
                directory(self._directory)
            if dict(members) != found_members:
                raise StoreIntegrityError('sequence scrub membership completeness disagreement')
            for namespace in NAMESPACES:
                # Explicit scrub only. The ordinary point/edit paths never scan.
                actual = set()
                if not self._new:
                    rows = self._store.db.execute('SELECT typed_key FROM lazy_record_versions WHERE namespace=? '
                        'AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                        (namespace, self._pin.captured_head, self._pin.captured_head)).fetchall()
                    self._store._metadata_rows += len(rows)
                    for (encoded,) in rows:
                        key = self._store.codec.decode(encoded)
                        belongs = key == self._incarnation if namespace == DESCRIPTOR_NAMESPACE else (
                            type(key) is tuple and len(key) == 2 and key[0] == self._incarnation)
                        if belongs:
                            if key in actual:
                                raise StoreIntegrityError('overlapping sequence authority versions')
                            actual.add(key)
                for (ns, key), value in self._dirty.items():
                    if ns == namespace:
                        if value is None: actual.discard(key)
                        else: actual.add(key)
                if namespace == DESCRIPTOR_NAMESPACE and self._new:
                    actual.add(self._incarnation)
                if actual != expected[namespace]:
                    raise StoreIntegrityError(f'extra/missing sequence authority in {namespace}')
