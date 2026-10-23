"""Closed raw version reads against accepted content roots; no World admission.

Certificates are data and require an expected commitment from outer authority.
This module neither constructs authority nor decodes payloads or memberships.
Ordinary overwritten records and their retention are deliberately separate.
"""
from dataclasses import dataclass

from .incremental_store import StoreError, StoreConflictError, StoreIntegrityError, _framed_sha
from .persistence_lazy_store import _version_checksum, MAX_PINS
from .persistence_proof_content import _namespace, _integer, version_key, version_commitment
from .persistence_proof_nodes import Root, _digest
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore


@dataclass(frozen=True)
class VersionCertificate:
    store_identity: str
    generation: int
    codec_version: int
    content: Root


@dataclass(frozen=True)
class RawVersion:
    payload: bytes
    memberships: bytes
    record_schema: int
    valid_from: int
    valid_to: int | None


class VersionProofBudgetError(StoreError):
    """An explicitly larger bounded read is required for this encoded body."""


def version_domain(store_identity, codec_version):
    return _digest(b'ate-version-proof-domain/1', _namespace(store_identity), _integer(codec_version, 1))


def certificate_commitment(certificate):
    if (type(certificate) is not VersionCertificate or type(certificate.generation) is not int
            or not 0 <= certificate.generation < 2**63):
        raise StoreIntegrityError('invalid version certificate')
    domain = version_domain(certificate.store_identity, certificate.codec_version)
    ProofMap(domain, None, None)._reference(certificate.content)
    return _digest(b'ate-version-certificate/1', domain, certificate.generation.to_bytes(8, 'big'),
                   certificate.content.digest, certificate.content.count.to_bytes(8, 'big'))


def _guard_operational_metadata(store, max_metadata_bytes):
    """Probe constant-size facts inside the snapshot BEFORE inherited fetches.

    No second transaction or authority. Limit all inventories before the
    existing validators materialize them; variable legitimate fields share an
    explicit caller budget, rather than a new format restriction.
    """
    total = 0
    head = store.db.execute("SELECT typeof(generation)='integer' "
        "AND typeof(parent_generation) IN ('integer','null') AND typeof(seed) IN ('integer','null') "
        "AND typeof(head_checksum)='text' AND length(CAST(head_checksum AS BLOB))=64 "
        "AND typeof(simulation_position)='blob' AND typeof(next_ids)='blob' "
        "AND typeof(namespace_inventory)='blob' AND typeof(namespace_counts)='blob',"
        "length(simulation_position)+length(next_ids)+length(namespace_inventory)+length(namespace_counts) "
        'FROM save_head WHERE singleton=1').fetchone()
    store._metadata_rows += int(head is not None)
    if head is None or head[0] != 1 or type(head[1]) is not int:
        raise StoreIntegrityError('invalid proof snapshot head metadata')
    total += head[1]
    # Fixed schema literals only. Each probe transfers booleans/counts, never
    # a token/checksum/blob. Capacity is the store's existing MAX_PINS bound.
    layouts = (
        ('generation_pins', ('token', 'store_uuid'), (), "typeof(generation)='integer'"),
        ('pin_receipts', ('pin_token', 'outcome'), ('commit_token',),
         "typeof(generation)='integer' AND typeof(parent_generation)='integer'"),
        ('pin_attempts', ('pin_token', 'state'), ('commit_token',),
         "typeof(parent_generation)='integer' AND typeof(generation) IN ('integer','null')"),
    )
    if total > max_metadata_bytes:
        raise VersionProofBudgetError('snapshot metadata exceeds explicit proof-read budget')
    for table, text_fields, blob_fields, integers in layouts:
        typed = ' AND '.join([integers, "typeof(row_checksum)='text'",
            'length(CAST(row_checksum AS BLOB))=64'] +
            [f"typeof({field})='text'" for field in text_fields] +
            [f"typeof({field})='blob'" for field in blob_fields])
        sizes = '+'.join([f'length(CAST({field} AS BLOB))' for field in text_fields] +
                         [f'length({field})' for field in blob_fields] + ['64'])
        rows = store.db.execute(f'SELECT {typed},{sizes} FROM {table} LIMIT {MAX_PINS+1}').fetchall()
        store._metadata_rows += len(rows)
        if len(rows) > MAX_PINS or any(valid != 1 or type(size) is not int for valid, size in rows):
            raise StoreIntegrityError('invalid proof snapshot operational metadata')
        total += sum(size for _, size in rows)
        if total > max_metadata_bytes:
            raise VersionProofBudgetError('snapshot metadata exceeds explicit proof-read budget')


def read_version_bytes(store, pin, certificate, expected_commitment, namespace, typed_key,
                       *, expected_record_schema, max_bytes=1048576, max_metadata_bytes=1048576):
    """Return exact retained source bytes or authenticated absence in one snapshot.

    Raw bytes still require reference/topology and canonical identity admission
    before any World object can be exposed. Every call checks actual fetched
    data and proof paths; no object-lifetime or generation-only reuse flag.
    """
    actual = certificate_commitment(certificate)
    if type(expected_commitment) is not bytes or len(expected_commitment) != 32 or expected_commitment != actual:
        raise StoreIntegrityError('version certificate commitment disagreement')
    if (certificate.store_identity != store.store_identity or certificate.store_identity != pin.store_identity
            or certificate.generation != pin.captured_head or certificate.codec_version != store.codec.version):
        raise StoreConflictError('version certificate store/codec/pin disagreement')
    encoded = version_key(namespace, typed_key)
    if (type(expected_record_schema) is not int or expected_record_schema <= 0
            or type(max_bytes) is not int or not 1 <= max_bytes <= 64*1024*1024
            or type(max_metadata_bytes) is not int or not 1 <= max_metadata_bytes <= 64*1024*1024):
        raise StoreIntegrityError('invalid version schema/read budget')
    if (store.db.in_transaction and not store._active_read_transaction
            and not getattr(store, '_checked_snapshot_depth', 0)):
        raise StoreError('version proof reader cannot borrow an arbitrary transaction')
    with store.read_snapshot(pin, _preflight=lambda: _guard_operational_metadata(store, max_metadata_bytes)) as generation:
        head = int(store._checked_head_row()[0])
        if generation not in (head, head-1):
            raise StoreConflictError('version pin exceeds two-snapshot visibility')
        domain = version_domain(certificate.store_identity, certificate.codec_version)
        nodes = ProofNodeStore(store.db)
        proof_map = ProofMap(domain, lambda d: nodes.read(domain, d), None)
        wanted = proof_map.get(certificate.content, encoded)
        # SQL guards run BEFORE transfer, including for malformed TEXT with NUL.
        body_ok = ("typeof(payload)='blob' AND typeof(memberships)='blob' "
                   f'AND length(payload)+length(memberships)<={max_bytes}')
        columns = ("CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
            "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
            f'CASE WHEN {body_ok} THEN payload END,'
            f'CASE WHEN {body_ok} THEN memberships END,'
            "CASE WHEN typeof(payload)='blob' THEN length(payload) END,"
            "CASE WHEN typeof(memberships)='blob' THEN length(memberships) END,"
            "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END,"
            "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END,"
            "CASE WHEN typeof(codec_version)='integer' THEN codec_version END,"
            "CASE WHEN typeof(record_schema)='integer' THEN record_schema END")
        rows = store._interval_rows('lazy_record_versions', columns, ('namespace', 'typed_key'),
            (namespace, typed_key), generation, 'lazy_record_interval', limit=2)
        store._metadata_rows += len(rows)
        if len(rows) > 1:
            raise StoreIntegrityError('overlapping visible proof record versions')
        if not rows:
            if wanted is not None:
                raise StoreIntegrityError('accepted version is missing from source')
            return None
        start, end, end_type, payload, memberships, payload_size, membership_size, payload_hash, row_hash, codec, schema = rows[0]
        if (type(start) is not int or not 0 <= start <= generation
                or end_type not in ('null', 'integer')
                or end_type == 'integer' and (type(end) is not int or end <= generation or end <= start)
                or codec != certificate.codec_version or schema != expected_record_schema
                or type(payload_size) is not int or type(membership_size) is not int
                or type(payload_hash) is not str or type(row_hash) is not str):
            raise StoreIntegrityError('invalid physical version metadata')
        if payload_size + membership_size > max_bytes:
            raise VersionProofBudgetError('version body exceeds explicit proof-read budget')
        if (type(payload) is not bytes or len(payload) != payload_size
                or type(memberships) is not bytes or len(memberships) != membership_size):
            raise StoreIntegrityError('invalid physical version body')
        store._payload_check_reads += 1
        store._payload_check_bytes += len(payload)
        if (payload_hash != _framed_sha(b'lazy-payload-v1', payload)
                or row_hash != _version_checksum(namespace, typed_key, schema, codec, start, end, memberships, payload)):
            raise StoreIntegrityError('physical version checksum disagreement')
        commitment = version_commitment(namespace, typed_key, valid_from=start, codec_version=codec,
                                        record_schema=schema, memberships=memberships, payload=payload)
        if wanted != commitment:
            raise StoreIntegrityError('source version disagrees with accepted content root')
        return RawVersion(payload, memberships, schema, start, end)
