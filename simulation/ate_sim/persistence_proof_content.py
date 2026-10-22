"""Exact immutable source bindings, without row selection or World authority.

Version interval closure is intentionally separate from content. These hashes
cannot authorize an interval, prove ordered-query completeness, or retain an
overwritten payload. Existing checked readers remain unchanged.
"""
import hashlib

from .incremental_store import StoreIntegrityError


def _namespace(namespace):
    if type(namespace) is not str or not namespace or '\x00' in namespace:
        raise StoreIntegrityError('invalid proof content namespace')
    try:
        return namespace.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise StoreIntegrityError('invalid proof content namespace encoding') from exc


def _bytes(value):
    if type(value) is not bytes:
        raise StoreIntegrityError('invalid proof content bytes')
    return value


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise StoreIntegrityError('invalid proof content integer')
    return str(value).encode('ascii')


def _key(tag, *parts):
    return b''.join(len(part).to_bytes(8, 'big') + part for part in (tag, *parts))


def _commitment(tag, *parts):
    digest = hashlib.sha256()
    for part in (tag, *parts):
        digest.update(len(part).to_bytes(8, 'big'))
        digest.update(part)
    return digest.digest()


def version_key(namespace: str, typed_key: bytes) -> bytes:
    return _key(b'ate-proof-key-version/1', _namespace(namespace), _bytes(typed_key))


def record_key(namespace: str, typed_key: bytes) -> bytes:
    return _key(b'ate-proof-key-record/1', _namespace(namespace), _bytes(typed_key))


def segment_key(namespace: str, ordinal: int) -> bytes:
    return _key(b'ate-proof-key-segment/1', _namespace(namespace), _integer(ordinal))


def version_commitment(namespace, typed_key, *, valid_from, codec_version,
                       record_schema, memberships, payload) -> bytes:
    return _commitment(b'ate-proof-content-version/1', _namespace(namespace),
        _bytes(typed_key), _integer(valid_from), _integer(codec_version, 1),
        _integer(record_schema, 1), _bytes(memberships), _bytes(payload))


def record_commitment(namespace, typed_key, *, last_changed_generation,
                      codec_version, record_schema, payload) -> bytes:
    return _commitment(b'ate-proof-content-record/1', _namespace(namespace),
        _bytes(typed_key), _integer(last_changed_generation), _integer(codec_version, 1),
        _integer(record_schema, 1), _bytes(payload))


def segment_commitment(namespace, ordinal, *, created_generation, codec_version,
                       element_count, first_id, last_id, payload) -> bytes:
    return _commitment(b'ate-proof-content-segment/1', _namespace(namespace),
        _integer(ordinal), _integer(created_generation), _integer(codec_version, 1),
        _integer(element_count, 1), _bytes(first_id), _bytes(last_id), _bytes(payload))
