"""Disposable checked conversion inventories, never persistence authority.

Rows go directly to private SQLite: there is no aggregate Python staging buffer.
One encoded input row and SQLite's bounded cache remain input-sized costs. The
existing store commit and private-copy publisher alone install durable authority.
"""
from collections.abc import Sequence
import hashlib
import operator
import os
from pathlib import Path
import sqlite3
import tempfile

from .incremental_store import Membership, RecordChange, StoreIntegrityError, _framed_sha
from .persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from .persistence_lazy_budget import resident_bytes


def pack_change(change):
    if isinstance(change, VersionChange):
        return ('version', change.namespace, change.key, change.value, change.delete,
                change.record_schema, tuple((m.index_name, m.value, m.ordinal) for m in change.memberships),
                change.reinsertion)
    if isinstance(change, RecordChange):
        return ('ordinary', change.namespace, change.key, change.value, change.delete,
                change.record_schema, tuple((m.index_name, m.value, m.ordinal) for m in change.memberships))
    if isinstance(change, IdentityOccurrenceChange):
        return ('identity', change.owner_namespace, change.owner_key, change.occurrence_path,
                change.incarnation_id, change.delete)
    raise TypeError('unsupported conversion change')


def unpack_change(value):
    if value[0] == 'version':
        return VersionChange(value[1], value[2], value[3], delete=value[4], record_schema=value[5],
                             memberships=tuple(Membership(*m) for m in value[6]), reinsertion=value[7])
    if value[0] == 'ordinary':
        return RecordChange(value[1], value[2], value[3], delete=value[4], record_schema=value[5],
                            memberships=tuple(Membership(*m) for m in value[6]))
    if value[0] == 'identity':
        return IdentityOccurrenceChange(*value[1:5], delete=value[5])
    raise StoreIntegrityError('unknown staged conversion adapter')


def _update(h, ordinal, payload):
    for part in (str(ordinal).encode('ascii'), payload):
        h.update(len(part).to_bytes(8, 'big')); h.update(part)


class ReplayRows(Sequence):
    def __init__(self, workspace, stream, count, seal, decode):
        self.workspace, self.stream, self.count, self.seal, self.decode = workspace, stream, count, seal, decode

    def __len__(self):
        return self.count

    def __iter__(self):
        workspace = self.workspace
        workspace.ensure_open()
        h = hashlib.sha256()
        count = 0
        cursor = workspace.db.execute('SELECT ordinal,payload,checksum FROM replay_rows WHERE stream=? ORDER BY ordinal', (self.stream,))
        try:
            for ordinal, payload, checksum in cursor:
                workspace.ensure_open()
                if ordinal != count or checksum != _framed_sha(b'conversion-row/v1', payload):
                    raise StoreIntegrityError('conversion staging row/order checksum mismatch')
                _update(h, ordinal, payload)
                value = workspace.codec.decode(payload)
                if workspace.codec.encode(value) != payload:
                    raise StoreIntegrityError('noncanonical conversion staging payload')
                count += 1
                yield self.decode(value)
            if count != self.count or h.hexdigest() != self.seal:
                raise StoreIntegrityError('conversion staging count/order commitment mismatch')
        finally:
            cursor.close()

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.count))]
        index = operator.index(index)
        if index < 0: index += self.count
        if not 0 <= index < self.count: raise IndexError('conversion row index')
        # Indexed access is explicit output; ordinary conversion streams rows.
        for ordinal, row in enumerate(self):
            if ordinal == index: return row
        raise StoreIntegrityError('missing staged conversion row')


class ConversionWorkspace:
    def __init__(self, codec, *, directory, entry_limit=4096, byte_limit=2*1024*1024):
        if type(entry_limit) is not int or entry_limit <= 0 or type(byte_limit) is not int or byte_limit <= 0:
            raise ValueError('conversion preparation budgets must be positive integers')
        self.codec, self.entry_limit, self.byte_limit = codec, entry_limit, byte_limit
        fd, path = tempfile.mkstemp(prefix='conversion-', suffix='.sqlite', dir=directory)
        os.close(fd)
        self.path = Path(path)
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA cache_size=-128')
        self.db.execute('PRAGMA temp_store=FILE')
        self.db.execute('CREATE TABLE replay_rows(stream INTEGER,ordinal INTEGER,payload BLOB,checksum TEXT,PRIMARY KEY(stream,ordinal)) WITHOUT ROWID')
        self._stream = 0
        self._closed = False
        self._metrics = dict(buffer_entries_high_water=0, buffer_bytes_high_water=0,
                             largest_row_bytes=0, largest_row_resident_bytes=0, staged_rows=0, staged_bytes=0)

    @property
    def metrics(self):
        return dict(self._metrics, disk_bytes=self.path.stat().st_size if not self._closed else 0,
                    python_index_bytes=resident_bytes((self._metrics, self._stream)))

    def ensure_open(self):
        if self._closed: raise RuntimeError('conversion workspace is closed')

    def stage(self, values, *, encode=lambda v: v, decode=lambda v: v):
        self.ensure_open()
        self._stream += 1
        stream, count, h = self._stream, 0, hashlib.sha256()
        for value in values:
            adapted = encode(value)
            payload = self.codec.encode(adapted)
            self._metrics['largest_row_bytes'] = max(self._metrics['largest_row_bytes'], len(payload))
            self._metrics['largest_row_resident_bytes'] = max(self._metrics['largest_row_resident_bytes'], resident_bytes((adapted, payload)))
            self.db.execute('INSERT INTO replay_rows VALUES (?,?,?,?)',
                            (stream, count, payload, _framed_sha(b'conversion-row/v1', payload)))
            _update(h, count, payload)
            count += 1
            self._metrics['staged_bytes'] += len(payload)
        self.db.commit()
        self._metrics['staged_rows'] += count
        return ReplayRows(self, stream, count, h.hexdigest(), decode)

    def stage_versions(self, changes):
        def adapter(change):
            if not isinstance(change, VersionChange): raise TypeError('version_changes must contain VersionChange')
            return pack_change(change)
        return self.stage(changes, encode=adapter, decode=unpack_change)

    def stage_ordinary(self, changes):
        return self.stage(changes, encode=pack_change, decode=unpack_change)

    def stage_identity(self, changes):
        return self.stage(changes, encode=pack_change, decode=unpack_change)

    def close(self):
        if self._closed: return
        self._closed = True
        try: self.db.close()
        finally:
            for suffix in ('', '-journal', '-wal', '-shm'):
                try: Path(str(self.path) + suffix).unlink()
                except FileNotFoundError: pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
