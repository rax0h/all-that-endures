"""Authenticated updates must preserve old mappings without scanning the map."""
import hashlib
import importlib
import random

import pytest
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_proof_nodes import Root, Leaf, Branch, empty_root, encode_node, node_digest
from simulation.tests.test_stage_0_5_proof_nodes import framed

DOMAIN = b'content'


def locator(key):
    return hashlib.sha256(framed(b'ate-proof-map-key/1', DOMAIN, key)).digest()


def value(text):
    return hashlib.sha256(text.encode()).digest()


class MemoryNodes:
    def __init__(self):
        self.data = {}
        self.reads = []
        self.writes = []

    def read(self, digest):
        self.reads.append(digest)
        return self.data[digest]

    def write(self, digest, raw):
        if digest in self.data:
            assert self.data[digest] == raw
        self.data[digest] = raw
        self.writes.append(digest)

    def store(self, node):
        raw = encode_node(node)
        digest = node_digest(DOMAIN, raw)
        self.data[digest] = raw
        count = 1 if type(node) is Leaf else sum(ref.count for _,ref in node.children)
        return Root(digest, count)


def proof_map(storage, domain=DOMAIN):
    module = importlib.import_module('ate_sim.persistence_proof_map')
    return module.ProofMap(domain, storage.read, storage.write)


def test_point_updates_keep_old_roots_and_noops_write_nothing():
    storage = MemoryNodes(); m = proof_map(storage)
    empty = empty_root(DOMAIN)
    assert m.get(empty, b'a') is None
    first = m.set(empty, b'a', value('one'))
    assert m.get(first, b'a') == value('one') and first.count == 1
    writes = len(storage.writes)
    assert m.set(first, b'a', value('one')) is first
    assert m.set(first, b'absent', None) is first
    assert len(storage.writes) == writes
    second = m.set(first, b'b', value('two'))
    third = m.set(second, b'a', value('three'))
    assert m.get(first, b'a') == value('one') and m.get(first, b'b') is None
    assert m.get(second, b'a') == value('one') and second.count == 2
    assert m.get(third, b'a') == value('three')
    removed = m.set(third, b'b', None)
    assert removed.count == 1 and m.get(removed, b'b') is None
    assert m.set(removed, b'a', None) == empty
    assert m.get(third, b'b') == value('two')


def test_prefix_splits_and_insertion_order_produce_one_canonical_root():
    keys = [f'key:{i}'.encode() for i in range(80)]
    roots = []
    for ordering in (keys, list(reversed(keys)), keys[::2]+keys[1::2]):
        storage = MemoryNodes(); m = proof_map(storage); root = empty_root(DOMAIN)
        for key in ordering: root = m.set(root, key, value(key.decode()))
        roots.append(root)
        assert dict(m.iter_leaves(root)) == {locator(key):value(key.decode()) for key in keys}
        assert root.count == 80
        for key in keys: assert m.get(root, key) == value(key.decode())
    assert roots[0] == roots[1] == roots[2]


def test_seeded_transitions_match_reference_map_and_retained_snapshots():
    storage = MemoryNodes(); m = proof_map(storage); root = empty_root(DOMAIN)
    rng = random.Random(193); expected = {}; retained = []
    keys = [f'k{i}'.encode() for i in range(16)]
    for i in range(200):
        key = rng.choice(keys); commit = None if rng.randrange(3) == 0 else value(str(i))
        root = m.set(root, key, commit)
        if commit is None: expected.pop(key,None)
        else: expected[key] = commit
        assert root.count == len(expected)
        for candidate in keys: assert m.get(root,candidate) == expected.get(candidate)
        assert dict(m.iter_leaves(root)) == {locator(k):v for k,v in expected.items()}
        if i % 20 == 0: retained.append((root,dict(expected)))
    for old, contents in retained:
        for key in keys: assert m.get(old,key) == contents.get(key)


@pytest.mark.parametrize('corruption', ['child-count','child-path','missing','bytes','root-count','empty-root','domain'])
def test_malformed_or_missing_proof_path_is_rejected(corruption):
    storage = MemoryNodes(); m = proof_map(storage)
    key = b'wanted'; wanted = locator(key); slot = wanted[0] >> 4
    leaf = storage.store(Leaf(wanted,value('old')))
    if corruption in ('child-count','child-path'):
        bad = Root(leaf.digest,2) if corruption == 'child-count' else storage.store(
            Leaf(bytes([(wanted[0]+16)%256])+wanted[1:],value('other')))
        sibling_slot = (slot+1)%16
        sibling_locator = bytes([sibling_slot << 4])+b'x'*31
        sibling = storage.store(Leaf(sibling_locator,value('sibling')))
        root = storage.store(Branch((),tuple(sorted(((slot,bad),(sibling_slot,sibling))))))
    elif corruption == 'root-count': root = Root(leaf.digest,2)
    elif corruption == 'empty-root': root = Root(leaf.digest,0)
    else:
        root = leaf
        if corruption == 'missing': del storage.data[leaf.digest]
        elif corruption == 'bytes': storage.data[leaf.digest] = storage.data[leaf.digest][:-1]+b'z'
        elif corruption == 'domain': m = proof_map(storage,b'other')
    with pytest.raises(StoreIntegrityError): m.get(root,key)
    with pytest.raises(StoreIntegrityError): m.set(root,key,value('new'))


def test_point_admission_leaves_unrelated_corruption_for_full_traversal():
    storage = MemoryNodes(); m = proof_map(storage); root = empty_root(DOMAIN)
    for i in range(64): root = m.set(root,str(i).encode(),value(str(i)))
    storage.reads.clear()
    assert m.get(root,b'0') == value('0')
    path = set(storage.reads)
    unrelated = next(d for d,raw in storage.data.items() if raw[:6] == b'ATEP\x01L'
                     and d not in path and raw[6:38] == locator(b'63'))
    del storage.data[unrelated]
    assert m.get(root,b'0') == value('0')
    with pytest.raises(StoreIntegrityError): list(m.iter_leaves(root))


def test_failed_write_cannot_change_the_accepted_old_mapping():
    storage = MemoryNodes(); m = proof_map(storage)
    old = m.set(empty_root(DOMAIN),b'key',value('old'))
    def failed(_digest,_raw): raise OSError('node write fault')
    m.write_node = failed
    with pytest.raises(OSError,match='node write fault'): m.set(old,b'key',value('new'))
    assert m.get(old,b'key') == value('old')
