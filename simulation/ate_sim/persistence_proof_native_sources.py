"""Native byte fetches bound to the admitted World, before value decoding.

This is source authority, not relation completeness or proof-only admission.
The existing audited opener and native publisher remain the only authorities.
"""
from contextlib import contextmanager

from .incremental_store import StoreError, StoreIntegrityError, StoreConflictError, _record_checksum
from .persistence_proof_content import version_key, record_key, record_commitment, segment_key
from . import persistence_proof_publication as content
from . import persistence_proof_record as records

MAX_BODY_BYTES = 64 * 1048576
MAX_METADATA_BYTES = 1048576


def active(store):
    authority = getattr(store, '_world_proof_authority', None)
    if authority is None:
        return None
    from .persistence_proof_world_session import _WorldProofAuthority
    if type(authority) is not _WorldProofAuthority:
        raise StoreIntegrityError('invalid native source authority')
    # Initial full audit establishes the externally accepted manifest. The
    # writer's explicit capability owns transient rows and validates publication.
    guard = getattr(store.db, '_native_write_guard', None)
    if authority.epoch is None:
        return None
    if store.db._callback_guard or getattr(store.db, '_native_sql_callback_depth', 0):
        raise StoreConflictError('native sources unavailable in publisher/SQLite callbacks')
    if guard is not None and guard is getattr(authority, '_write_guard', None) and guard.depth > 0:
        return None
    return authority


def before_snapshot(store, authority, pin):
    """Reject context drift before any inherited variable-sized metadata read."""
    if authority.uncertain and not authority.busy:
        raise StoreError('native source publication requires exact recovery')
    if (pin.store_identity != authority.pair[0].store_identity
            or pin.captured_head != authority.pair[0].generation
            or getattr(store, '_checked_snapshot_depth', 0) and
               getattr(store, '_checked_snapshot_generation', None) != pin.captured_head):
        raise StoreConflictError('native source cannot borrow a different generation snapshot')
    _epoch(store, authority)


def _epoch(store, authority):
    actual, expected = authority._epoch(), authority.epoch
    guard = getattr(store.db, '_native_write_guard', None)
    owned = authority.busy and guard is not None and guard is getattr(authority, '_write_guard', None)
    if (actual[:3] != expected[:3] or actual[4] != expected[4]
            or not owned and actual != expected):
        raise StoreConflictError('native source snapshot epoch differs from accepted authority')


def snapshot_preflight(store, authority):
    # A tiny SELECT establishes SQLite's actual read view. Recheck the epoch
    # there, closing the gap between a pre-BEGIN guard and concurrent commit.
    row = store.db.execute("SELECT CASE WHEN typeof(generation)='integer' THEN generation END FROM main.save_head WHERE singleton=1").fetchone()
    _epoch(store, authority)
    if row != (authority.pair[0].generation,):
        raise StoreConflictError('native source physical head differs from accepted generation')
    from .persistence_proof_version import _guard_operational_metadata
    _guard_operational_metadata(store, MAX_METADATA_BYTES)


def _locator(namespace, typed=b''):
    if type(namespace) is not str or type(typed) is not bytes:
        raise StoreIntegrityError('invalid native source locator')
    if len(namespace.encode()) + len(typed) > MAX_METADATA_BYTES:
        raise StoreError('native source locator exceeds explicit budget')


@contextmanager
def _snapshot(store, authority, generation=None, *, pin=None):
    pin, manifest = authority.read_pin if pin is None else pin, authority.pair[0]
    if (pin is None or pin.captured_head != manifest.generation
            or generation is not None and generation != manifest.generation):
        raise StoreConflictError('native source generation differs from accepted manifest')
    with store.read_snapshot(pin) as captured:
        if captured != manifest.generation:
            raise StoreConflictError('native source snapshot differs from accepted manifest')
        yield manifest


def version_row(store, authority, generation, namespace, typed):
    _locator(namespace, typed)
    with _snapshot(store, authority, generation) as manifest:
        valid = ("typeof(valid_from)='integer' AND valid_from>=0 AND valid_from<="+str(generation)
            +" AND valid_to IS NULL AND typeof(payload)='blob' AND typeof(memberships)='blob'"
            +" AND typeof(record_schema)='integer' AND record_schema>0 AND typeof(codec_version)='integer' AND codec_version="+str(store.codec.version)
            +" AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64"
            +" AND typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64")
        sizes = store._interval_rows('lazy_record_versions', valid+",length(payload)+length(memberships),"
            "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END,"
            "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END",
            ('namespace', 'typed_key'), (namespace, typed), generation, 'lazy_record_interval', limit=2)
        store._metadata_rows += len(sizes)
        if len(sizes) > 1:
            raise StoreIntegrityError('overlapping native source versions')
        if sizes and (sizes[0][0] != 1 or type(sizes[0][1]) is not int or sizes[0][1] < 0):
            raise StoreIntegrityError('invalid native source metadata or interval')
        if sizes and sizes[0][1] > MAX_BODY_BYTES:
            raise StoreError('native source body exceeds explicit budget')
        wanted = content._map(store).get(manifest.roots[0], version_key(namespace, typed))
        row = content._source_version(store, generation, namespace, typed, max_bytes=MAX_BODY_BYTES)
        actual = None if row is None else content._version_value(namespace, typed, row, store.codec.version)
        if actual != wanted:
            raise StoreIntegrityError('native source differs from accepted version root')
        if row is None:
            return None
        p, m, s, start, end = row.payload, row.memberships, row.record_schema, row.valid_from, row.valid_to
        return (start, end, p, sizes[0][2], store.codec.version, s, m, sizes[0][3])


def _record_columns(store, manifest):
    valid = ("typeof(record_schema)='integer' AND record_schema>0 AND typeof(codec_version)='integer' AND codec_version="+str(store.codec.version)
        +" AND typeof(last_changed_generation)='integer' AND last_changed_generation BETWEEN 0 AND "+str(manifest.generation)
        +" AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64"
        +" AND typeof(typed_key)='blob' AND length(typed_key)+length(CAST(namespace AS BLOB))<="+str(MAX_METADATA_BYTES))
    return (f"CASE WHEN {valid} AND typeof(payload)='blob' AND length(payload)<={MAX_BODY_BYTES} THEN payload END,"
        "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END,"
        "CASE WHEN typeof(codec_version)='integer' THEN codec_version END,"
        "CASE WHEN typeof(record_schema)='integer' THEN record_schema END,"
        "CASE WHEN typeof(last_changed_generation)='integer' THEN last_changed_generation END")


def _record(store, manifest, namespace, typed, row):
    wanted = records._map(store).get(manifest.roots[1], record_key(namespace, typed))
    if row is None:
        if wanted is not None:
            raise StoreIntegrityError('native source missing from accepted ordinary root')
        return None
    payload, checksum, codec, schema, revision = row
    if (type(payload) is not bytes or type(schema) is not int or schema < 1
            or codec != store.codec.version or type(revision) is not int
            or not 0 <= revision <= manifest.generation
            or checksum != _record_checksum(namespace, typed, schema, codec, revision, payload)):
        raise StoreIntegrityError('invalid or oversized native ordinary source')
    actual = record_commitment(namespace, typed, last_changed_generation=revision,
        codec_version=codec, record_schema=schema, payload=payload)
    if actual != wanted:
        raise StoreIntegrityError('native source differs from accepted ordinary root')
    return row


def record_row(store, authority, namespace, typed):
    _locator(namespace, typed)
    with _snapshot(store, authority) as manifest:
        if store._ordinary_namespace_is_lazy(namespace):
            raise StoreError(f'{namespace!r} is lazy authority; use read_version')
        row = store.db.execute('SELECT '+_record_columns(store, manifest)+' FROM records WHERE namespace=? AND typed_key=?',
            (namespace, typed)).fetchone()
        return _record(store, manifest, namespace, typed, row)


@contextmanager
def record_rows(store, authority, namespace):
    _locator(namespace)
    with _snapshot(store, authority) as manifest:
        if store._ordinary_namespace_is_lazy(namespace):
            raise StoreError(f'{namespace!r} is lazy authority; use iter_keys/read_version')
        from .persistence_proof_native_roster import check_count
        expected=check_count(store,authority,manifest,namespace)
        cursor = store.db.execute("SELECT CASE WHEN typeof(typed_key)='blob' AND length(typed_key)<=? THEN typed_key END,"
            +_record_columns(store, manifest)+' FROM records WHERE namespace=?', (MAX_METADATA_BYTES-len(namespace.encode()), namespace))
        def checked():
            seen=0
            for typed, *row in cursor:
                seen+=1
                if seen>expected:raise StoreIntegrityError('native ordinary source roster exceeds accepted count')
                _locator(namespace, typed)
                yield typed, *_record(store, manifest, namespace, typed, tuple(row))
            if seen!=expected:raise StoreIntegrityError('native ordinary source roster ended before accepted count')
        try:
            yield checked()
        finally:
            cursor.close()


def segment_row(store, authority, namespace, ordinal):
    _locator(namespace)
    with _snapshot(store, authority) as manifest:
        wanted = content._map(store, True).get(manifest.roots[5], segment_key(namespace, ordinal))
        valid = ("typeof(payload)='blob' AND typeof(first_id)='blob' AND typeof(last_id)='blob'"
            +" AND typeof(codec_version)='integer' AND codec_version="+str(store.codec.version)
            +" AND typeof(element_count)='integer' AND element_count>=0 AND typeof(created_generation)='integer' AND created_generation BETWEEN 0 AND "+str(manifest.generation)
            +" AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64")
        metadata = store.db.execute('SELECT '+valid+",length(payload),length(first_id)+length(last_id),"
            "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END "
            'FROM segments WHERE namespace=? AND ordinal=?', (namespace, ordinal)).fetchone()
        if metadata is not None:
            if metadata[0] != 1 or any(type(v) is not int or v < 0 for v in metadata[1:3]):
                raise StoreIntegrityError('invalid native event source metadata')
            if metadata[1] > MAX_BODY_BYTES or metadata[2] > MAX_METADATA_BYTES:
                raise StoreError('native event source exceeds explicit budget')
        row = content._source_event(store, manifest.generation, namespace, ordinal, MAX_BODY_BYTES, MAX_METADATA_BYTES)
        actual = None if row is None else content._event_value(namespace, ordinal, row, store.codec.version)
        if actual != wanted:
            raise StoreIntegrityError('native source differs from accepted event root')
        if row is None:
            return None
        p, first, last, count, created = row.payload, row.first_id, row.last_id, row.element_count, row.created_generation
        return (p, metadata[3],
            store.codec.version, count, first, last, created)
