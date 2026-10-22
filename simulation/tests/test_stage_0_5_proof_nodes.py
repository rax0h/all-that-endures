"""Durable map bytes must be unambiguous before they can authenticate state."""
import hashlib
import importlib

import pytest
from ate_sim.incremental_store import StoreIntegrityError


def nodes():
    return importlib.import_module('ate_sim.persistence_proof_nodes')


def framed(*parts):
    return b''.join(len(part).to_bytes(8, 'big') + part for part in parts)


def child(slot, count=1, digest=b'x'*32):
    return bytes([slot]) + count.to_bytes(8, 'big') + digest


def test_known_canonical_bytes_and_domain_separation():
    n = nodes()
    leaf = n.Leaf(bytes(range(32)), b'v'*32)
    raw = b'ATEP\x01L' + bytes(range(32)) + b'v'*32
    assert n.encode_node(leaf) == raw
    assert n.decode_node(raw) == leaf
    want = hashlib.sha256(framed(b'ate-proof-map-node/1', b'content', raw)).digest()
    assert n.node_digest(b'content', raw) == want
    assert n.node_digest(b'topology', raw) != want
    branch = n.Branch((10, 11, 12), ((2, n.Root(b'x'*32, 1)), (15, n.Root(b'y'*32, 4))))
    branch_raw = b'ATEP\x01B\x03\xab\xc0\x02' + child(2) + child(15, 4, b'y'*32)
    assert n.encode_node(branch) == branch_raw
    assert n.decode_node(branch_raw) == branch
    assert n.empty_root(b'content') == n.Root(
        hashlib.sha256(framed(b'ate-proof-map-empty/1', b'content')).digest(), 0)
    assert n.key_locator(b'content', b'key') == hashlib.sha256(
        framed(b'ate-proof-map-key/1', b'content', b'key')).digest()
    assert n.key_locator(b'content', b'1') != n.key_locator(b'content', b'01')
    assert n.key_locator(b'content', b'key') != n.key_locator(b'other', b'key')


@pytest.mark.parametrize('raw', [
    b'', b'ATEP\x02L'+b'x'*64, b'ATEP\x01L'+b'x'*63,
    b'ATEP\x01L'+b'x'*65,
    b'ATEP\x01B\x01\x11\x02'+child(0)+child(1), # nonzero padding
    b'ATEP\x01B\x40'+b'\x00'*32+b'\x02'+child(0)+child(1), # exhausted locator
    b'ATEP\x01B\x00\x00', b'ATEP\x01B\x00\x01'+child(0),
    b'ATEP\x01B\x00\x11'+child(0)*17,
    b'ATEP\x01B\x00\x02'+child(0)+child(0),
    b'ATEP\x01B\x00\x02'+child(1)+child(0),
    b'ATEP\x01B\x00\x02'+child(0,0)+child(1),
    b'ATEP\x01B\x00\x02'+child(0,2**64-1)+child(1),
    b'ATEP\x01B\x00\x02'+child(0)+child(16),
    b'ATEP\x01B\x00\x02'+child(0)+child(1)+b'extra',
])
def test_reject_noncanonical_nodes(raw):
    with pytest.raises(StoreIntegrityError): nodes().decode_node(raw)


@pytest.mark.parametrize('kind', ['short-leaf', 'short-digest', 'bad-slot', 'bool-count', 'negative-prefix'])
def test_encoder_rejects_noncanonical_objects(kind):
    n = nodes()
    root = n.Root(b'x'*32, 1)
    obj = n.Leaf(b'x', b'y'*32) if kind == 'short-leaf' else n.Branch((), ((0,root),(1,root)))
    if kind == 'short-digest': obj = n.Leaf(b'x'*32, b'y')
    elif kind == 'bad-slot': obj = n.Branch((), ((0,root),(16,root)))
    elif kind == 'bool-count': obj = n.Branch((), ((0,n.Root(b'x'*32,True)),(1,root)))
    elif kind == 'negative-prefix': obj = n.Branch((-1,), ((0,root),(1,root)))
    with pytest.raises(StoreIntegrityError): n.encode_node(obj)
