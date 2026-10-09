"""Checked MVCC coalesced retired-ID ranges, published by the hybrid plan.

Ordinary point reads and edits visit AVL paths. Enumeration/scrub and initial
conversion are explicit archive operations. A range is metadata, never a new
identity or permission to reuse an incarnation for another object.
"""
from collections import OrderedDict
from contextlib import contextmanager

from .incremental_store import StoreIntegrityError, _framed_sha
from .persistence_lazy_store import VersionChange
from .persistence_lazy_sequence import _resident

HEADER_NAMESPACE = 'aux.lazy.identity.retired'
NODE_NAMESPACE = 'aux.lazy.identity.retired_nodes'
EMPTY_HEADER = ('identity-retired-directory/v2', 0, None)
CACHE_ENTRIES = 64
CACHE_BYTES = 2 * 1024 * 1024
_ABSENT = object()


def _positive(n):
    return type(n) is int and n > 0


def _link(link):
    return (type(link) is tuple and len(link) == 7 and _positive(link[0])
        and _positive(link[1]) and type(link[2]) is str and len(link[2]) == 64
        and type(link[3]) is int and link[3] >= 0 and _positive(link[4])
        and _positive(link[5]) and link[4] <= link[0] <= link[5]
        and _positive(link[6]) and link[6] >= link[1])


def checked_header(header):
    if (type(header) is not tuple or len(header) != 3 or header[0] != EMPTY_HEADER[0]
        or type(header[1]) is not int or header[1] < 0
        or (header[2] is not None and not _link(header[2]))
        or (header[2] is None and header[1] != 0)
        or (header[2] is not None and header[1] != header[2][1])):
        raise StoreIntegrityError('invalid retirement directory root commitment')
    return header


class RetiredIdentityRanges:
    def __init__(self, store, pin, *, initial=False, header=None):
        self.store, self.pin, self.initial = store, pin, initial
        self._cache, self._cache_bytes = OrderedDict(), 0
        self._dirty, self._baseline, self._undo = {}, {}, None
        store._require_pin(pin)
        if initial:
            with store.read_snapshot(pin):
                if any(store._namespace_state_at(ns, pin.captured_head) is not None
                       for ns in (HEADER_NAMESPACE, NODE_NAMESPACE)):
                    raise StoreIntegrityError('initial retirement directory would overwrite existing authority')
            if header is not None:
                raise ValueError('initial retirement directory has no previous header')
            self._base = None
            self.root = None
        else:
            if header is None:
                header = self._raw(HEADER_NAMESPACE, 0)
            self._base = store.codec.encode(checked_header(header))
            self.root = header[2]

    @property
    def header(self):
        return (EMPTY_HEADER[0], self.root[1] if self.root else 0, self.root)

    def _raw(self, namespace, key, *, absent=False):
        try:
            return self.store.read_version(self.pin, namespace, key, expected_record_schema=1).value
        except KeyError:
            if absent:
                return _ABSENT
            raise StoreIntegrityError('missing checked retirement authority') from None

    def _commitment(self, node):
        if (type(node) is not tuple or len(node) != 5 or node[0] != 'retired-range/v1'
            or not _positive(node[1]) or type(node[2]) is not int or node[2] < node[1]
            or any(child is not None and not _link(child) for child in node[3:])):
            raise StoreIntegrityError('invalid retired interval node')
        _, lo, hi, left, right = node
        lh, rh = (left[3] if left else -1), (right[3] if right else -1)
        if (abs(lh - rh) > 1 or (left and left[5] + 1 >= lo)
            or (right and hi + 1 >= right[4])):
            raise StoreIntegrityError('retired intervals overlap, adjoin or are unbalanced')
        return (lo, 1 + (left[1] if left else 0) + (right[1] if right else 0),
            _framed_sha(b'identity-retired-node/v1', self.store.codec.encode((NODE_NAMESPACE, lo, node))),
            1 + max(lh, rh), left[4] if left else lo, right[5] if right else hi,
            hi - lo + 1 + (left[6] if left else 0) + (right[6] if right else 0))

    def _read(self, link):
        if not _link(link):
            raise StoreIntegrityError('invalid retired interval link')
        key = link[0]
        if key in self._dirty:
            node = self._dirty[key]
        elif key in self._cache:
            node, size = self._cache.pop(key)
            self._cache[key] = node, size
        else:
            node = self._raw(NODE_NAMESPACE, key)
            size = _resident(key) + _resident(node)
            if size <= CACHE_BYTES:
                self._cache[key] = node, size
                self._cache_bytes += size
                while len(self._cache) > CACHE_ENTRIES or self._cache_bytes > CACHE_BYTES:
                    _, (_, released) = self._cache.popitem(last=False)
                    self._cache_bytes -= released
        if node is None or self._commitment(node) != link:
            raise StoreIntegrityError('retired interval count/digest/locator disagreement')
        return node

    def _put(self, key, node):
        if self._undo is not None and key not in self._undo:
            self._undo[key] = self._dirty.get(key, _ABSENT), self._baseline.get(key, _ABSENT)
        if key not in self._baseline:
            old = _ABSENT if self.initial else self._raw(NODE_NAMESPACE, key, absent=True)
            self._baseline[key] = None if old is _ABSENT else self.store.codec.encode(old)
        if (None if node is None else self.store.codec.encode(node)) == self._baseline[key]:
            self._dirty.pop(key, None)
            self._baseline.pop(key, None)
        else:
            self._dirty[key] = node
        cached = self._cache.pop(key, None)
        if cached:
            self._cache_bytes -= cached[1]

    def _write(self, lo, hi, left, right):
        node = ('retired-range/v1', lo, hi, left, right)
        link = self._commitment(node)
        self._put(lo, node)
        return link

    @staticmethod
    def _height(link):
        return link[3] if link else -1

    def _balance(self, lo, hi, left, right):
        if self._height(left) - self._height(right) > 1:
            _, llo, lhi, ll, lr = self._read(left)
            if self._height(ll) >= self._height(lr):
                return self._write(llo, lhi, ll, self._write(lo, hi, lr, right))
            _, mlo, mhi, ml, mr = self._read(lr)
            return self._write(mlo, mhi, self._write(llo, lhi, ll, ml), self._write(lo, hi, mr, right))
        if self._height(right) - self._height(left) > 1:
            _, rlo, rhi, rl, rr = self._read(right)
            if self._height(rr) >= self._height(rl):
                return self._write(rlo, rhi, self._write(lo, hi, left, rl), rr)
            _, mlo, mhi, ml, mr = self._read(rl)
            return self._write(mlo, mhi, self._write(lo, hi, left, ml), self._write(rlo, rhi, mr, rr))
        return self._write(lo, hi, left, right)

    def _insert(self, link, lo, hi):
        if link is None:
            return self._write(lo, hi, None, None)
        _, key, end, left, right = self._read(link)
        if lo < key:
            left = self._insert(left, lo, hi)
        elif lo > key:
            right = self._insert(right, lo, hi)
        else:
            end = hi
        return self._balance(key, end, left, right)

    def _delete(self, link, key):
        if link is None:
            raise StoreIntegrityError('retired interval deletion has no witness')
        _, lo, hi, left, right = self._read(link)
        if key < lo:
            left = self._delete(left, key)
        elif key > lo:
            right = self._delete(right, key)
        else:
            self._put(key, None)
            if left is None: return right
            if right is None: return left
            successor = right
            while True:
                node = self._read(successor)
                if node[3] is None: break
                successor = node[3]
            _, lo, hi, _, _ = node
            right = self._delete(right, lo)
        return self._balance(lo, hi, left, right)

    def _neighbors(self, inc):
        link, before, after = self.root, None, None
        while link is not None:
            _, lo, hi, left, right = self._read(link)
            if inc < lo:
                after, link = (lo, hi), left
            elif inc > hi:
                before, link = (lo, hi), right
            else:
                return (lo, hi), before, after
        return None, before, after

    @contextmanager
    def _mutation(self):
        self.store._require_pin(self.pin)
        root = self.root
        self._undo = {}
        try:
            with self.store.read_snapshot(self.pin): yield
        except BaseException:
            self.root = root
            for key, (dirty, baseline) in self._undo.items():
                if dirty is _ABSENT: self._dirty.pop(key, None)
                else: self._dirty[key] = dirty
                if baseline is _ABSENT: self._baseline.pop(key, None)
                else: self._baseline[key] = baseline
            self._cache.clear(); self._cache_bytes = 0
            raise
        finally:
            self._undo = None

    def contains(self, inc):
        if not _positive(inc): raise ValueError('invalid retirement incarnation')
        with self.store.read_snapshot(self.pin):
            return self._neighbors(inc)[0] is not None

    def add(self, inc):
        if not _positive(inc): raise ValueError('invalid retirement incarnation')
        with self._mutation():
            found, before, after = self._neighbors(inc)
            if found is not None: return
            lo = hi = inc
            if before and before[1] + 1 == inc:
                lo = before[0]
                self.root = self._delete(self.root, before[0])
            if after and after[0] == inc + 1:
                hi = after[1]
                self.root = self._delete(self.root, after[0])
            self.root = self._insert(self.root, lo, hi)

    def remove(self, inc):
        if not _positive(inc): raise ValueError('invalid retirement incarnation')
        with self._mutation():
            found, _, _ = self._neighbors(inc)
            if found is None: return
            lo, hi = found
            self.root = self._delete(self.root, lo)
            if lo < inc: self.root = self._insert(self.root, lo, inc - 1)
            if inc < hi: self.root = self._insert(self.root, inc + 1, hi)

    def intervals(self):
        """Explicit full enumeration, for scrub/conversion evidence only."""
        with self.store.read_snapshot(self.pin):
            out = []
            def walk(link):
                if link is not None:
                    _, lo, hi, left, right = self._read(link)
                    walk(left); out.append((lo, hi)); walk(right)
            walk(self.root)
            return tuple(out)

    def pending_changes(self):
        out = tuple(VersionChange(NODE_NAMESPACE, key, node, delete=node is None)
                    for key, node in self._dirty.items())
        if self.store.codec.encode(self.header) != self._base:
            out += (VersionChange(HEADER_NAMESPACE, 0, self.header),)
        if self.initial and not any(v.namespace == NODE_NAMESPACE for v in out):
            out += (VersionChange(NODE_NAMESPACE, ('empty-retired-declaration/v1',), delete=True),)
        return out

    def diagnostics(self):
        return {'clean_entries': len(self._cache), 'clean_bytes': self._cache_bytes,
                'dirty_entries': len(self._dirty),
                'dirty_bytes': (_resident(self._dirty) + _resident(self._baseline)
                    + sum(_resident(key) + _resident(value) for key, value in self._dirty.items())
                    + sum(_resident(key) + _resident(value) for key, value in self._baseline.items()))}

    def scrub(self):
        with self.store.read_snapshot(self.pin):
            self._cache.clear()
            self._cache_bytes = 0
            if not self.initial and self.store.codec.encode(self._raw(HEADER_NAMESPACE, 0)) != self._base:
                raise StoreIntegrityError('retirement directory header changed underneath captured authority')
            visited = set()
            def walk(link):
                if link is None: return
                if link[0] in visited: raise StoreIntegrityError('duplicate/cyclic retirement node')
                visited.add(link[0])
                node = self._read(link)
                walk(node[3]); walk(node[4])
            walk(self.root)
            rows = () if self.initial else self.store.db.execute(
                'SELECT typed_key FROM lazy_record_versions WHERE namespace=? AND valid_from<=? '
                'AND (valid_to IS NULL OR ?<valid_to)',
                (NODE_NAMESPACE, self.pin.captured_head, self.pin.captured_head)).fetchall()
            self.store._metadata_rows += len(rows)
            keys = [self.store.codec.decode(row[0]) for row in rows]
            if len(set(keys)) != len(keys): raise StoreIntegrityError('overlapping retirement nodes')
            actual = set(keys)
            for key, node in self._dirty.items():
                if node is None: actual.discard(key)
                else: actual.add(key)
            if actual != visited: raise StoreIntegrityError('extra/missing retired interval nodes')
