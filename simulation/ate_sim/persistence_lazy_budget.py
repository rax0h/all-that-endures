"""Shared clean cache limits; dirty overlays and leases are separate authorities.

Owners supply an eviction callback that only drops clean payload and sidecars.
The manager holds weak owners, supports unhashable collection proxies and never
visits a live-object registry. Caller weights include decoded payload/sidecars;
manager metadata residency is reported separately from those weights.
"""
from collections import OrderedDict
import sys
import weakref

HISTORY_ENTRIES = 64
HISTORY_BYTES = 8 * 1024 * 1024
IDENTITY_OCCURRENCES = 4096
IDENTITY_BYTES = 2 * 1024 * 1024
RECORD_BYTES = 32 * 1024 * 1024


def resident_bytes(value, seen=None):
    """Recursive Python residency estimate, distinct from traced peaks or RSS."""
    seen = set() if seen is None else seen
    marker = id(value)
    if marker in seen:
        return 0
    seen.add(marker)
    result = sys.getsizeof(value)
    if isinstance(value, dict):
        result += sum(resident_bytes(k, seen) + resident_bytes(v, seen)
                      for k, v in value.items())
    elif type(value) in (tuple, list, set, frozenset):
        result += sum(resident_bytes(item, seen) for item in value)
    return result


class SharedCacheBudget:
    def __init__(self, *, entry_limit=HISTORY_ENTRIES, byte_limit=HISTORY_BYTES):
        if (type(entry_limit) is not int or entry_limit <= 0
                or type(byte_limit) is not int or byte_limit <= 0):
            raise ValueError('cache limits must be positive integers')
        self.entry_limit, self.byte_limit = entry_limit, byte_limit
        self._entries = OrderedDict()
        self._owners = {}
        self._bytes = self._serial = self._evictions = 0

    def _owner(self, owner, create=False):
        marker = id(owner)
        row = self._owners.get(marker)
        if row is not None and row[0]() is owner:
            return row
        if not create:
            return None
        self._serial += 1
        token = self._serial
        budget_ref = weakref.ref(self)

        def collected(ref):
            budget = budget_ref()
            if budget is None:
                return
            current = budget._owners.get(marker)
            if current is not None and current[0] is ref and current[1] == token:
                for key in tuple(current[2]):
                    budget._discard((token, key))

        row = weakref.ref(owner, collected), token, set()
        self._owners[marker] = row
        return row

    def _discard(self, marker, *, evict=False):
        entry = self._entries.pop(marker, None)
        if entry is None:
            return
        owner_marker, ref, size = entry
        self._bytes -= size
        row = self._owners.get(owner_marker)
        if row is not None and row[1] == marker[0]:
            row[2].discard(marker[1])
            if not row[2]:
                del self._owners[owner_marker]
        if evict:
            owner = ref()
            if owner is not None:
                owner._budget_evict(marker[1])
            self._evictions += 1

    def admit(self, owner, key, size):
        if type(size) is not int or size < 0:
            raise ValueError('cache entry weight must be a nonnegative integer')
        hash(key)
        # Replacing a local clean entry must not evict its newly installed value.
        self.forget(owner, key)
        if size > self.byte_limit:
            owner._budget_evict(key)
            self._evictions += 1
            return False
        row = self._owner(owner, True)
        marker = row[1], key
        row[2].add(key)
        self._entries[marker] = id(owner), row[0], size
        self._bytes += size
        while len(self._entries) > self.entry_limit or self._bytes > self.byte_limit:
            self._discard(next(iter(self._entries)), evict=True)
        return marker in self._entries

    def touch(self, owner, key):
        row = self._owner(owner)
        if row is not None and (row[1], key) in self._entries:
            self._entries.move_to_end((row[1], key))

    def forget(self, owner, key):
        row = self._owner(owner)
        if row is not None:
            self._discard((row[1], key))

    def release(self, owner):
        row = self._owner(owner)
        if row is not None:
            for key in tuple(row[2]):
                self._discard((row[1], key), evict=True)

    def clear(self):
        """Release the bounded clean inventory, without visiting other owners."""
        while self._entries:
            self._discard(next(iter(self._entries)), evict=True)

    def diagnostics(self):
        return {'entries': len(self._entries), 'bytes': self._bytes,
                'owners': len(self._owners), 'evictions': self._evictions,
                'metadata_python_bytes': resident_bytes((self._entries, self._owners))}


class CleanCacheOwner:
    def _initialize_cache(self, cache_budget):
        self._cache = OrderedDict()
        self._cache_weights = {}
        self._cache_bytes = 0
        self._cache_budget = cache_budget if cache_budget is not None else SharedCacheBudget()

    def _cache_value(self, key, value, local_limit):
        self._drop_clean(key)
        size = resident_bytes((key, value)) + 64
        self._cache[key] = value
        self._cache_weights[key] = size
        self._cache_bytes += size
        self._cache_budget.admit(self, key, size)
        while len(self._cache) > local_limit:
            self._drop_clean(next(iter(self._cache)))

    def _budget_evict(self, key):
        self._cache.pop(key, None)
        self._cache_bytes -= self._cache_weights.pop(key, 0)

    def _drop_clean(self, key):
        self._cache_budget.forget(self, key)
        self._budget_evict(key)

    def _clear_cache(self):
        self._cache_budget.release(self)
        self._cache.clear()
        self._cache_weights.clear()
        self._cache_bytes = 0


def schema_resident_bytes(value, seen=None):
    """Count resident schema values without calling lazy collection readers.

    Compact page-backed proxies are charged for their reference object here;
    their decoded pages and sidecars belong to the shared history budget.
    """
    from .persistence_schema import RECORD_FIELDS
    seen = set() if seen is None else seen
    marker = id(value)
    if marker in seen:
        return 0
    seen.add(marker)
    size = sys.getsizeof(value)
    fields = RECORD_FIELDS.get(type(value))
    if fields is not None:
        size += sys.getsizeof(getattr(value, '__dict__', {}))
        size += sum(schema_resident_bytes(getattr(value, field), seen) for field in fields)
    elif isinstance(value, dict):
        size += sum(schema_resident_bytes(k, seen) + schema_resident_bytes(v, seen)
                    for k, v in dict.items(value))
    elif isinstance(value, list):
        size += sum(schema_resident_bytes(v, seen) for v in list.__iter__(value))
    elif isinstance(value, set):
        size += sum(schema_resident_bytes(v, seen) for v in set.__iter__(value))
    elif type(value) in (tuple, frozenset):
        size += sum(schema_resident_bytes(v, seen) for v in value)
    return size


class RecordCacheLRU(OrderedDict):
    """Global byte accounting for clean records and pinned query caches.

    The LRU owns only cache metadata. Eviction drops clean table entries and
    sidecars without detaching registry occurrences or retained live aliases.
    The session's budget can change before admission (useful for measurements).
    """
    def __init__(self, session):
        super().__init__()
        self._cache_session = weakref.ref(session)
        self._record_owner = None

    def bind_record_owner(self, table):
        if self._record_owner is not None and self._record_owner() is not table:
            raise ValueError('record cache already has an owner')
        self._record_owner = weakref.ref(table)

    def _budget(self):
        session = self._cache_session()
        return None if session is None else session._record_cache_budget

    def _weight(self, key, value):
        table = None if self._record_owner is None else self._record_owner()
        if table is None:
            return schema_resident_bytes((key, value)) + 128
        if key in table._dirty or not dict.__contains__(table, key):
            return None
        payload = dict.__getitem__(table, key)
        sidecars = tuple(getattr(table, field, {}).get(key) for field in (
            '_baseline_payload', '_baseline_presence', '_baseline_incarnation',
            '_baseline_ordinal', '_baseline_identity_labels',
        ))
        return schema_resident_bytes((key, payload, sidecars)) + 128

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        budget = self._budget()
        if budget is not None:
            weight = self._weight(key, value)
            if weight is not None:
                budget.admit(self, key, weight)
            else:
                budget.forget(self, key)

    def pop(self, key, *default):
        result = super().pop(key, *default)
        budget = self._budget()
        if budget is not None:
            budget.forget(self, key)
        return result

    def popitem(self, last=True):
        key, value = super().popitem(last=last)
        budget = self._budget()
        if budget is not None:
            budget.forget(self, key)
        return key, value

    def clear(self):
        budget = self._budget()
        if budget is not None:
            for key in tuple(self):
                budget.forget(self, key)
        super().clear()

    def _budget_evict(self, key):
        OrderedDict.pop(self, key, None)
        table = None if self._record_owner is None else self._record_owner()
        if table is None or key in table._dirty:
            return
        if dict.__contains__(table, key):
            dict.__delitem__(table, key)
        for field in ('_baseline_payload', '_baseline_presence', '_baseline_incarnation',
                      '_baseline_ordinal', '_baseline_identity_labels'):
            getattr(table, field, {}).pop(key, None)
