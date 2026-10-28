"""Batch transitions preserve mappings, write only final paths and stream deltas."""
import importlib
import random
import sqlite3

import pytest

from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_proof_nodes import Branch, Leaf, Root, decode_node, empty_root
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation.tests.test_stage_0_5_proof_map import (
    DOMAIN, MemoryNodes, locator, proof_map, value,
)


def update(m, root, changes):
    return importlib.import_module('ate_sim.persistence_proof_batch').update_sorted(m, root, changes)


def ordered(items):
    return sorted(items, key=lambda item: locator(item[0]))


def reachable(storage, root):
    found = set()
    pending = [root] if root.count else []
    while pending:
        ref = pending.pop()
        if ref.digest in found:
            continue
        found.add(ref.digest)
        node = decode_node(storage.data[ref.digest])
        if type(node) is Branch:
            pending.extend(child for _, child in node.children)
    return found


def test_batch_matches_independent_mapping_and_canonical_sequential_root():
    storage = MemoryNodes(); m = proof_map(storage); root = empty_root(DOMAIN)
    expected = {}; snapshots = []; rng = random.Random(883)
    keys = [f'key:{i}'.encode() for i in range(75)]
    for step in range(30):
        chosen = rng.sample(keys, 20)
        delta = [(key, None if rng.randrange(3) == 0 else value(f'{step}:{key}')) for key in chosen]
        previous = root
        sequential = root
        for key, commitment in delta:
            sequential = m.set(sequential, key, commitment)
            if commitment is None:
                expected.pop(key, None)
            else:
                expected[key] = commitment
        root = update(m, root, iter(ordered(delta)))
        assert root == sequential and root.count == len(expected)
        assert dict(m.iter_leaves(root)) == {locator(k): v for k, v in expected.items()}
        assert previous.count >= 0
        snapshots.append((root, dict(expected)))
    for old, contents in snapshots:
        assert dict(m.iter_leaves(old)) == {locator(k): v for k, v in contents.items()}
    assert update(m, root, iter(ordered((k, None) for k in keys))) == empty_root(DOMAIN)


def test_only_final_nodes_are_written_once():
    storage = MemoryNodes(); m = proof_map(storage)
    root = update(m, empty_root(DOMAIN), iter(ordered((str(i).encode(), value(str(i))) for i in range(500))))
    assert len(storage.writes) == len(set(storage.writes))
    assert set(storage.writes) == reachable(storage, root)
    old_nodes = reachable(storage, root)
    storage.writes.clear(); storage.reads.clear()
    changed = update(m, root, iter(ordered((str(i).encode(), value('new')) for i in range(80))))
    assert len(storage.writes) == len(set(storage.writes))
    assert set(storage.writes) <= reachable(storage, changed)
    assert len(storage.reads) == len(set(storage.reads))
    assert old_nodes <= set(storage.data)


def test_empty_and_noop_batches_keep_root_identity():
    storage = MemoryNodes(); m = proof_map(storage)
    root = m.set(empty_root(DOMAIN), b'present', value('old'))
    storage.writes.clear(); storage.reads.clear()
    assert update(m, root, iter(())) is root
    assert storage.reads == []
    assert update(m, root, iter(ordered([(b'present', value('old')), (b'absent', None)]))) is root
    assert storage.writes == []


@pytest.mark.parametrize('changes', [
    [(b'a', b'short')], [(bytearray(b'a'), value('x'))], [(b'a', True)],
    [(b'a',)], [b'ab'], [(b'a', value('x')), (b'a', value('y'))],
])
def test_stream_rejects_duplicate_unsorted_and_malformed_changes(changes):
    storage = MemoryNodes(); m = proof_map(storage)
    with pytest.raises(StoreIntegrityError):
        update(m, empty_root(DOMAIN), iter(changes))
    with pytest.raises(StoreIntegrityError):
        update(m, empty_root(DOMAIN), iter(reversed(ordered([(b'a', value('a')), (b'b', value('b'))]))))


@pytest.mark.parametrize('fault', ['missing', 'bytes', 'count', 'path', 'promoted'])
def test_affected_corruption_and_promoted_sibling_are_rejected(fault):
    storage = MemoryNodes(); m = proof_map(storage)
    keys = [b'a', b'b']; root = empty_root(DOMAIN)
    for key in keys:
        root = m.set(root, key, value(key.decode()))
    node = decode_node(storage.data[root.digest])
    if fault == 'count':
        root = Root(root.digest, root.count + 1)
    elif fault == 'path':
        slots = [slot for slot, _ in node.children]
        root = storage.store(Branch(node.prefix, tuple(zip(slots, [ref for _, ref in reversed(node.children)]))))
    else:
        target = b'b' if fault == 'promoted' else b'a'
        digest = next(d for d, raw in storage.data.items() if raw[:6] == b'ATEP\x01L' and raw[6:38] == locator(target))
        if fault in ('missing', 'promoted'):
            del storage.data[digest]
        else:
            storage.data[digest] = storage.data[digest][:-1] + b'!'
    with pytest.raises(StoreIntegrityError):
        update(m, root, iter([(b'a', None if fault == 'promoted' else value('new'))]))


def test_maximum_depth_batch_is_bounded():
    storage = MemoryNodes(); m = proof_map(storage)
    key = b'deep'; raw_locator = locator(key)
    nibbles = tuple(n for byte in raw_locator for n in (byte >> 4, byte & 15))
    root = storage.store(Leaf(raw_locator, value('old')))
    for depth in reversed(range(64)):
        sibling_slot = (nibbles[depth] + 1) % 16
        sibling_prefix = nibbles[:depth] + (sibling_slot,) + (0,) * (63-depth)
        sibling_bytes = bytes((sibling_prefix[i] << 4) | sibling_prefix[i+1] for i in range(0, 64, 2))
        sibling = storage.store(Leaf(sibling_bytes, value(str(depth))))
        root = storage.store(Branch(nibbles[:depth], tuple(sorted(((nibbles[depth], root), (sibling_slot, sibling))))))
    storage.reads.clear(); storage.writes.clear()
    changed = update(m, root, iter([(key, value('new'))]))
    assert len(storage.reads) == 65 and len(storage.writes) == 65
    assert m.get(changed, key) == value('new') and m.get(root, key) == value('old')


def test_sqlite_batch_rollback_and_generator_fault_keep_old_roots(tmp_path):
    db = sqlite3.connect(tmp_path/'nodes.sqlite')
    store = ProofNodeStore(db); store.create_schema()
    from ate_sim.persistence_proof_map import ProofMap
    m = ProofMap(DOMAIN, lambda digest: store.read(DOMAIN, digest),
                 lambda digest, raw: store.write(DOMAIN, digest, raw))
    db.execute('BEGIN')
    old = update(m, empty_root(DOMAIN), iter(ordered((str(i).encode(), value('old')) for i in range(1024))))
    db.commit()
    before = db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]
    store.reset_diagnostics(); db.execute('SAVEPOINT batch')
    changed = update(m, old, iter([(b'0', value('new'))]))
    assert store.diagnostics()['read_nodes'] <= 66
    assert m.get(changed, b'0') == value('new')
    db.execute('ROLLBACK TO batch'); db.execute('RELEASE batch')
    assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0] == before
    assert m.get(old, b'0') == value('old')
    def broken():
        yield from ordered([(b'0', value('changed')), (b'1', value('changed'))])
        raise OSError('delta generator fault')
    db.execute('BEGIN')
    with pytest.raises(OSError, match='delta generator fault'):
        update(m, old, broken())
    assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0] > before
    db.rollback()
    assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0] == before
    assert m.get(old, b'0') == value('old')
    db.close()

@pytest.mark.parametrize('fault',['late-malformed','after-insert'])
def test_late_batch_failures_rollback_written_nodes_and_preserve_root(tmp_path,fault):
 from ate_sim.persistence_proof_map import ProofMap
 db=sqlite3.connect(tmp_path/'late.sqlite');storage=ProofNodeStore(db);storage.create_schema()
 m=ProofMap(DOMAIN,lambda d:storage.read(DOMAIN,d),lambda d,raw:storage.write(DOMAIN,d,raw))
 db.execute('BEGIN')
 old=update(m,empty_root(DOMAIN),iter(ordered((str(i).encode(),value('old')) for i in range(1024))));db.commit()
 before=db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]
 def insert_then_fail(d,raw):
  storage.write(DOMAIN,d,raw)
  raise RuntimeError('after real insertion')
 changes=ordered((str(i).encode(),value('new')) for i in range(512))
 if fault=='late-malformed':changes[-1]=(changes[-1][0],b'bad')
 tested=m if fault=='late-malformed' else ProofMap(DOMAIN,lambda d:storage.read(DOMAIN,d),insert_then_fail)
 db.execute('BEGIN')
 with pytest.raises(StoreIntegrityError if fault=='late-malformed' else RuntimeError):update(tested,old,iter(changes))
 assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]>before
 db.rollback();assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]==before
 assert m.get(old,b'0')==value('old');db.close()
