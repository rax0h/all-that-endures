"""Complete ordered relation certificates; no World or interval authority."""
from dataclasses import dataclass

from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import Root, MAX_COUNT, _digest, empty_root


@dataclass(frozen=True)
class OrderEntry:
    key: bytes
    value: bytes
    previous: bytes | None
    following: bytes | None


@dataclass(frozen=True)
class OrderRoot:
    index: Root
    first: bytes | None
    last: bytes | None


def _optional(key):
    if key is None:
        return b'0', b''
    if type(key) is not bytes:
        raise StoreIntegrityError('invalid ordered proof key')
    return b'1', key


def entry_commitment(domain, entry):
    if (type(entry) is not OrderEntry or type(entry.key) is not bytes
            or type(entry.value) is not bytes or len(entry.value) != 32):
        raise StoreIntegrityError('invalid ordered proof entry')
    previous, following = _optional(entry.previous), _optional(entry.following)
    if (entry.previous is not None and entry.previous >= entry.key
            or entry.following is not None and entry.following <= entry.key):
        raise StoreIntegrityError('invalid ordered proof neighbor order')
    return _digest(b'ate-proof-order-entry/1', domain, entry.key, entry.value, *previous, *following)


def root_commitment(domain, root):
    if (type(root) is not OrderRoot or type(root.index) is not Root
            or type(root.index.digest) is not bytes or len(root.index.digest) != 32
            or type(root.index.count) is not int or not 0 <= root.index.count <= MAX_COUNT):
        raise StoreIntegrityError('invalid ordered proof root')
    first, last = _optional(root.first), _optional(root.last)
    count = root.index.count
    if (not count and (root.index != empty_root(domain) or root.first is not None or root.last is not None)
            or count and (root.first is None or root.last is None)
            or count == 1 and root.first != root.last
            or count > 1 and root.first >= root.last):
        raise StoreIntegrityError('invalid ordered proof extrema/count')
    return _digest(b'ate-proof-order-root/1', domain, root.index.digest,
                   count.to_bytes(8, 'big'), *first, *last)


def query_order_key(ordinal, typed_record_key):
    if (type(ordinal) is not int or not 0 <= ordinal < 2**63
            or type(typed_record_key) is not bytes):
        raise StoreIntegrityError('invalid ordered query position')
    return ordinal.to_bytes(8, 'big') + typed_record_key


def _check_root(proof_map, root, expected_commitment):
    actual = root_commitment(proof_map.map_domain, root)
    if type(expected_commitment) is not bytes or len(expected_commitment) != 32 or actual != expected_commitment:
        raise StoreIntegrityError('ordered descriptor commitment disagreement')
    proof_map._reference(root.index)


def _check_entry(proof_map, root, entry):
    commitment = entry_commitment(proof_map.map_domain, entry)
    if proof_map.get(root.index, entry.key) != commitment:
        raise StoreIntegrityError('ordered entry membership disagreement')
    if (not root.index.count or not root.first <= entry.key <= root.last
            or (entry.previous is None) != (entry.key == root.first)
            or (entry.following is None) != (entry.key == root.last)):
        raise StoreIntegrityError('ordered entry endpoint disagreement')


def verify_page(proof_map, root, expected_commitment, *, rows, after=None,
                before=None, limit=128, boundary=None):
    """Check a contiguous raw page before filtering, decoding or exposure."""
    _check_root(proof_map, root, expected_commitment)
    _optional(after); _optional(before)
    if type(limit) is not int or not 1 <= limit <= 128:
        raise StoreIntegrityError('invalid ordered page limit')
    page = []
    for row in rows:
        if len(page) == limit:
            raise StoreIntegrityError('surplus ordered page row')
        page.append(row)
    if after is not None and before is not None and after >= before:
        if page or boundary is not None:
            raise StoreIntegrityError('nonempty reversed ordered range')
        return ()
    if page:
        if boundary is not None or len(page) > root.index.count:
            raise StoreIntegrityError('surplus ordered boundary/rows')
        for i, entry in enumerate(page):
            _check_entry(proof_map, root, entry)
            if (after is not None and entry.key <= after
                    or before is not None and entry.key >= before):
                raise StoreIntegrityError('ordered page outside range')
            if i:
                previous = page[i-1]
                if (previous.key >= entry.key or previous.following != entry.key
                        or entry.previous != previous.key):
                    raise StoreIntegrityError('ordered page adjacency disagreement')
        first, last = page[0], page[-1]
        if first.previous is not None and (after is None or first.previous > after):
            raise StoreIntegrityError('ordered page omitted its range beginning')
        if len(page) < limit and last.following is not None and (before is None or last.following < before):
            raise StoreIntegrityError('ordered page ended before range completion')
        return tuple(page)
    if not root.index.count:
        if boundary is not None:
            raise StoreIntegrityError('surplus empty-root boundary')
        return ()
    if boundary is None:
        raise StoreIntegrityError('empty ordered page needs a boundary proof')
    _check_entry(proof_map, root, boundary)
    left = (after is not None and boundary.key <= after
            and (boundary.following is None or before is not None and boundary.following >= before))
    right = (before is not None and boundary.key >= before
             and (boundary.previous is None or after is not None and boundary.previous <= after))
    if not (left or right):
        raise StoreIntegrityError('false ordered range absence')
    return ()
