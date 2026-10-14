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
        selected = None
        for ordinal, row in enumerate(self):
            if ordinal == index: selected = row
        return selected


class ConversionWorkspace:
    def __init__(self, codec, *, directory, entry_limit=4096, byte_limit=2*1024*1024):
        if type(entry_limit) is not int or entry_limit <= 0 or type(byte_limit) is not int or byte_limit <= 0:
            raise ValueError('conversion preparation budgets must be positive integers')
        self.codec, self.entry_limit, self.byte_limit = codec, entry_limit, byte_limit
        fd, path = tempfile.mkstemp(prefix='conversion-', suffix='.sqlite', dir=directory)
        os.close(fd)
        self.path = Path(path)
        self.db = None
        try:
            self.db = sqlite3.connect(path)
            self.db.execute('PRAGMA cache_size=-128')
            self.db.execute('PRAGMA temp_store=FILE')
            self.db.execute('CREATE TABLE replay_rows(stream INTEGER,ordinal INTEGER,payload BLOB,checksum TEXT,PRIMARY KEY(stream,ordinal)) WITHOUT ROWID')
        except BaseException:
            if self.db is not None:
                self.db.close()
            for suffix in ('', '-journal', '-wal', '-shm'):
                try: Path(str(self.path) + suffix).unlink()
                except FileNotFoundError: pass
            raise
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


class PreparedRows(ReplayRows):
    """Writer grouping uses disk indexes while preserving first-namespace order."""
    def namespace_groups(self):
        workspace = self.workspace
        # Authenticate the original complete sequence before consulting indexes.
        for _ in self: pass
        groups = workspace.db.execute('SELECT namespace,min(ordinal),count(*) FROM preparation_index WHERE stream=? GROUP BY namespace ORDER BY min(ordinal)', (self.stream,))
        total = 0
        for namespace, _first, count in groups:
            total += count
            def rows(namespace=namespace, count=count):
                seen = 0
                query = ('SELECT r.ordinal,r.payload,r.checksum FROM preparation_index i JOIN replay_rows r '
                         'ON r.stream=i.stream AND r.ordinal=i.ordinal WHERE i.stream=? AND i.namespace=? ORDER BY i.ordinal')
                for ordinal, payload, checksum in workspace.db.execute(query, (self.stream, namespace)):
                    if checksum != _framed_sha(b'conversion-row/v1', payload):
                        raise StoreIntegrityError('prepared group checksum mismatch')
                    item = self.decode(workspace.codec.decode(payload))
                    if item['namespace'] != namespace:
                        raise StoreIntegrityError('prepared namespace index mismatch')
                    seen += 1
                    yield item
                if seen != count:
                    raise StoreIntegrityError('prepared namespace inventory mismatch')
            yield namespace, rows()
        if total != len(self):
            raise StoreIntegrityError('prepared namespace index count mismatch')


def prepare_changes(workspace, store, changes, kind):
    """Reuse existing row validators/encoders with disk duplicate detection.

    The original mutable change is discarded after its encoded row is captured.
    Writers need only flags/schema/incarnation from it, never its mutable value.
    """
    from dataclasses import replace
    workspace.db.execute('CREATE TABLE IF NOT EXISTS preparation_keys(kind TEXT,namespace TEXT,key BLOB,path BLOB,PRIMARY KEY(kind,namespace,key,path)) WITHOUT ROWID')
    workspace.db.execute('CREATE TABLE IF NOT EXISTS preparation_index(stream INTEGER,ordinal INTEGER,namespace TEXT,PRIMARY KEY(stream,ordinal)) WITHOUT ROWID')
    workspace.db.execute('CREATE INDEX IF NOT EXISTS preparation_namespaces ON preparation_index(stream,namespace,ordinal)')
    stream = workspace._stream + 1
    ordinal = 0
    validate = {'version': store._prepare_version_changes, 'ordinary': store._prepare_ordinary_changes,
                'identity': store._prepare_identity_changes}[kind]

    def values():
        nonlocal ordinal
        for change in changes:
            item = validate((change,))[0]
            namespace = item.get('namespace', item.get('owner_namespace'))
            key = item.get('typed_key', item.get('owner_key'))
            path = item.get('occurrence_path', b'')
            try:
                workspace.db.execute('INSERT INTO preparation_keys VALUES (?,?,?,?)', (kind, namespace, key, path))
            except sqlite3.IntegrityError as exc:
                message = {'version': 'duplicate version change', 'ordinary': 'duplicate ordinary record change',
                           'identity': 'duplicate identity occurrence change'}[kind]
                raise ValueError(message) from exc
            if kind == 'version':
                workspace.db.execute('INSERT INTO preparation_index VALUES (?,?,?)', (stream, ordinal, namespace))
            captured = dict(item)
            captured['change'] = pack_change(change if kind == 'identity' else replace(change, value=None, memberships=()))
            yield captured
            ordinal += 1
    def decode(value):
        value['change'] = unpack_change(value['change'])
        return value
    rows = workspace.stage(values(), decode=decode)
    return PreparedRows(workspace, rows.stream, rows.count, rows.seal, decode) if kind == 'version' else rows


class DiskSet:
    """Checksummed disposable scrub inventory; no authority outside this copy."""
    def __init__(self, workspace):
        self.workspace = workspace
        workspace._stream += 1
        self.stream = workspace._stream
        workspace.db.execute('CREATE TABLE IF NOT EXISTS conversion_sets(stream INTEGER,key BLOB,checksum TEXT,PRIMARY KEY(stream,key)) WITHOUT ROWID')
        self.count, self.root = 0, 0

    def __contains__(self, key):
        row = self.workspace.db.execute('SELECT checksum FROM conversion_sets WHERE stream=? AND key=?', (self.stream, key)).fetchone()
        if row is None: return False
        if row != (_framed_sha(b'conversion-set/v1', key),):
            raise StoreIntegrityError('conversion scrub inventory checksum mismatch')
        return True

    def add(self, key):
        if key in self: return
        checksum = _framed_sha(b'conversion-set/v1', key)
        self.workspace.db.execute('INSERT INTO conversion_sets VALUES (?,?,?)', (self.stream, key, checksum))
        self.count += 1
        self.root ^= int(checksum, 16)

    def validate(self):
        count, root = 0, 0
        for key, checksum in self.workspace.db.execute('SELECT key,checksum FROM conversion_sets WHERE stream=?', (self.stream,)):
            if checksum != _framed_sha(b'conversion-set/v1', key):
                raise StoreIntegrityError('conversion scrub inventory checksum mismatch')
            count += 1; root ^= int(checksum, 16)
        if (count, root) != (self.count, self.root):
            raise StoreIntegrityError('conversion scrub inventory count/root mismatch')

    def equals(self, keys):
        other = DiskSet(self.workspace)
        for key in keys: other.add(key)
        self.validate(); other.validate()
        return self.workspace.db.execute('SELECT key FROM conversion_sets WHERE stream=? EXCEPT SELECT key FROM conversion_sets WHERE stream=? LIMIT 1', (self.stream,other.stream)).fetchone() is None and self.workspace.db.execute('SELECT key FROM conversion_sets WHERE stream=? EXCEPT SELECT key FROM conversion_sets WHERE stream=? LIMIT 1', (other.stream,self.stream)).fetchone() is None
