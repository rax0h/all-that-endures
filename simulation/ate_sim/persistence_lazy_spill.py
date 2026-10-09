"""Private immutable checked spill buffers, never publication/identity authority.

Only already checked metadata enters these buffers. They preserve captured
values while bounding Python residency; a private SQLite file supplies sorting
and replay. Frozen buffers commit to encoded rows and their order. Their files
are released with the last reference. No live graph or object registry is held.
"""
from collections.abc import Sequence
import hashlib
import operator
import os
import sqlite3
import sys
import tempfile

from .incremental_store import StoreIntegrityError, _framed_sha
from .persistence_lazy_budget import resident_bytes


class CheckedSpool(Sequence):
    def __init__(self, codec, *, entry_limit=4096, byte_limit=2 * 1024 * 1024,
                 order='ordinal', unique=False):
        if (type(entry_limit) is not int or entry_limit <= 0
                or type(byte_limit) is not int or byte_limit <= 0
                or order not in ('ordinal', 'encoded', 'placement')):
            raise ValueError('invalid checked spill budget/order')
        self.codec, self.entry_limit, self.byte_limit = codec, entry_limit, byte_limit
        self.order, self.unique = order, unique
        self._memory, self._keys = [], set()
        self._weight = self._count = 0
        self._db = self.path = None
        self._frozen = self._closed = False
        self._seals = {}

    @property
    def spilled(self):
        return self._db is not None

    @property
    def resident_bytes(self):
        return sys.getsizeof(self) + resident_bytes((self._memory, self._keys, self._seals, self.path))

    @property
    def disk_bytes(self):
        return os.path.getsize(self.path) if self.path is not None and not self._closed else 0

    def _start_spill(self):
        fd, self.path = tempfile.mkstemp(prefix='ate-checked-membership-', suffix='.sqlite')
        os.close(fd)
        self._db = sqlite3.connect(self.path)
        self._db.execute('PRAGMA cache_size=-128')
        self._db.execute('PRAGMA temp_store=FILE')
        self._db.execute('CREATE TABLE entries(ordinal INTEGER PRIMARY KEY,payload BLOB NOT NULL,'
                         'checksum TEXT NOT NULL,namespace TEXT,typed_key BLOB,typed_path BLOB)')
        self._db.execute('CREATE INDEX encoded_entries ON entries(payload)')
        self._db.execute('CREATE INDEX placement_entries ON entries(namespace,typed_key,typed_path)')
        if self.unique:
            self._db.execute('CREATE UNIQUE INDEX unique_entries ON entries(payload)')
        for ordinal, entry in enumerate(self._memory):
            self._insert(ordinal, entry)
        self._memory.clear()
        self._keys.clear()
        self._weight = 0

    def _insert(self, ordinal, entry):
        _value, payload, checksum, namespace, key, path = entry
        try:
            self._db.execute('INSERT INTO entries VALUES (?,?,?,?,?,?)',
                             (ordinal, payload, checksum, namespace, key, path))
        except sqlite3.IntegrityError as exc:
            raise StoreIntegrityError('duplicate checked spill membership') from exc

    def add(self, value):
        if self._closed or self._frozen:
            raise RuntimeError('checked spill is closed or immutable')
        payload = self.codec.encode(value)
        if self.unique and self._db is None and payload in self._keys:
            raise StoreIntegrityError('duplicate checked spill membership')
        namespace = key = path = None
        if self.order == 'placement':
            namespace, native_key, native_path = value
            key, path = self.codec.encode(native_key), self.codec.encode(native_path)
        entry = value, payload, _framed_sha(b'checked-spill-row/v1', payload), namespace, key, path
        weight = resident_bytes(entry) + 64
        if self._db is None and (self._count >= self.entry_limit or self._weight + weight > self.byte_limit):
            self._start_spill()
        if self._db is None:
            self._memory.append(entry)
            if self.unique:
                self._keys.add(payload)
            self._weight += weight
        else:
            self._insert(self._count, entry)
        self._count += 1

    @staticmethod
    def _order(order):
        return {'ordinal': 'ordinal', 'encoded': 'payload,ordinal',
                'placement': 'namespace,typed_key,typed_path,ordinal'}[order]

    def _rows(self, order):
        if self._closed:
            raise RuntimeError('checked spill is closed')
        if self._db is not None:
            cursor = self._db.execute('SELECT ordinal,payload,checksum FROM entries ORDER BY ' + self._order(order))
            try:
                yield from cursor
            finally:
                cursor.close()
        else:
            rows = [(i, entry) for i, entry in enumerate(self._memory)]
            if order == 'encoded':
                rows.sort(key=lambda row: (row[1][1], row[0]))
            elif order == 'placement':
                rows.sort(key=lambda row: (*row[1][3:], row[0]))
            for ordinal, entry in rows:
                yield ordinal, entry[1], entry[2]

    def _encoded(self, order):
        h = hashlib.sha256()
        count = 0
        for ordinal, payload, checksum in self._rows(order):
            if (type(ordinal) is not int or not 0 <= ordinal < self._count or type(payload) is not bytes
                    or checksum != _framed_sha(b'checked-spill-row/v1', payload)):
                raise StoreIntegrityError('checked spill row/checksum mismatch')
            for part in (str(ordinal).encode('ascii'), payload):
                h.update(len(part).to_bytes(8, 'big')); h.update(part)
            count += 1
            yield payload
        if count != self._count or (order in self._seals and h.hexdigest() != self._seals[order]):
            raise StoreIntegrityError('checked spill count/order commitment mismatch')

    def freeze(self):
        if self._frozen:
            return self
        if self._db is None:
            result = tuple(self.codec.decode(payload) for payload in self._encoded(self.order))
            self.close()
            return result
        self._db.commit()
        for order in {self.order, 'encoded'}:
            h = hashlib.sha256()
            for ordinal, payload, _checksum in self._rows(order):
                for part in (str(ordinal).encode('ascii'), payload):
                    h.update(len(part).to_bytes(8, 'big')); h.update(part)
            self._seals[order] = h.hexdigest()
        self._frozen = True
        return self

    def encoded_sorted(self):
        yield from self._encoded('encoded')

    def __iter__(self):
        for payload in self._encoded(self.order):
            value = self.codec.decode(payload)
            if self.codec.encode(value) != payload:
                raise StoreIntegrityError('noncanonical checked spill payload')
            yield value

    def __len__(self):
        return self._count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        index = operator.index(index)
        if index < 0:
            index += self._count
        if not 0 <= index < self._count:
            raise IndexError('checked spill index out of range')
        # Random access is an explicit output operation; group consumers stream.
        for offset, value in enumerate(self):
            if offset == index:
                return value
        raise StoreIntegrityError('checked spill is missing indexed value')

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._db is not None:
            self._db.close()
        self._memory.clear(); self._keys.clear()
        if self.path is not None:
            for suffix in ('', '-journal', '-wal', '-shm'):
                try:
                    os.unlink(self.path + suffix)
                except FileNotFoundError:
                    pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
