"""Canonical immutable map nodes; no World format or runtime authority yet."""
from dataclasses import dataclass
import hashlib

from .incremental_store import StoreIntegrityError


MAX_NODE_BYTES = 696
MAX_COUNT = 2**64 - 1


@dataclass(frozen=True)
class Root:
    digest: bytes
    count: int


@dataclass(frozen=True)
class Leaf:
    locator: bytes
    commitment: bytes


@dataclass(frozen=True)
class Branch:
    prefix: tuple[int, ...]
    children: tuple[tuple[int, Root], ...]


def _bytes(value, length=None):
    if type(value) is not bytes or length is not None and len(value) != length:
        raise StoreIntegrityError('invalid proof bytes')
    return value


def _digest(*parts):
    h = hashlib.sha256()
    for part in parts:
        _bytes(part)
        h.update(len(part).to_bytes(8, 'big'))
        h.update(part)
    return h.digest()


def empty_root(map_domain: bytes) -> Root:
    return Root(_digest(b'ate-proof-map-empty/1', map_domain), 0)


def key_locator(map_domain: bytes, typed_key: bytes) -> bytes:
    return _digest(b'ate-proof-map-key/1', map_domain, typed_key)


def node_digest(map_domain: bytes, raw: bytes) -> bytes:
    _bytes(raw)
    if len(raw) > MAX_NODE_BYTES:
        raise StoreIntegrityError('oversized proof node')
    return _digest(b'ate-proof-map-node/1', map_domain, raw)


def encode_node(node: Leaf | Branch) -> bytes:
    if type(node) is Leaf:
        return b'ATEP\x01L' + _bytes(node.locator, 32) + _bytes(node.commitment, 32)
    if type(node) is not Branch:
        raise StoreIntegrityError('unsupported proof node')
    prefix, children = node.prefix, node.children
    if (type(prefix) is not tuple or len(prefix) > 63
            or any(type(n) is not int or not 0 <= n <= 15 for n in prefix)
            or type(children) is not tuple or not 2 <= len(children) <= 16):
        raise StoreIntegrityError('invalid proof branch')
    packed = bytes((prefix[i] << 4) | (prefix[i+1] if i+1 < len(prefix) else 0)
                   for i in range(0, len(prefix), 2))
    raw = bytearray(b'ATEP\x01B' + bytes([len(prefix)]) + packed + bytes([len(children)]))
    previous, total = -1, 0
    for child in children:
        if type(child) is not tuple or len(child) != 2:
            raise StoreIntegrityError('invalid proof child')
        slot, root = child
        if (type(slot) is not int or not previous < slot <= 15 or type(root) is not Root
                or type(root.count) is not int or not 1 <= root.count <= MAX_COUNT):
            raise StoreIntegrityError('invalid proof child slot/count')
        _bytes(root.digest, 32)
        total += root.count
        if total > MAX_COUNT:
            raise StoreIntegrityError('proof count overflow')
        raw.extend(bytes([slot]) + root.count.to_bytes(8, 'big') + root.digest)
        previous = slot
    return bytes(raw)


def decode_node(raw: bytes) -> Leaf | Branch:
    _bytes(raw)
    if len(raw) > MAX_NODE_BYTES:
        raise StoreIntegrityError('oversized proof node')
    if raw[:6] == b'ATEP\x01L':
        if len(raw) != 70:
            raise StoreIntegrityError('invalid proof leaf length')
        return Leaf(raw[6:38], raw[38:])
    if raw[:6] != b'ATEP\x01B' or len(raw) < 8:
        raise StoreIntegrityError('invalid proof node tag/length')
    length = raw[6]
    count_offset = 7 + (length+1)//2
    if length > 63 or count_offset >= len(raw):
        raise StoreIntegrityError('invalid proof prefix length')
    if length % 2 and raw[count_offset-1] & 15:
        raise StoreIntegrityError('noncanonical proof prefix padding')
    count = raw[count_offset]
    if not 2 <= count <= 16 or len(raw) != count_offset+1+count*41:
        raise StoreIntegrityError('invalid proof child inventory length')
    prefix = tuple((raw[7+i//2] >> (4 if i % 2 == 0 else 0)) & 15 for i in range(length))
    children = tuple((raw[i], Root(raw[i+9:i+41], int.from_bytes(raw[i+1:i+9], 'big')))
                     for i in range(count_offset+1, len(raw), 41))
    result = Branch(prefix, children)
    # The encoder checks order, counts, exact types and canonical shape too.
    if encode_node(result) != raw:
        raise StoreIntegrityError('noncanonical proof branch bytes')
    return result
