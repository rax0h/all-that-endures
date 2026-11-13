"""Independent narrow review probes; run only outside raw timing windows."""
import itertools
import json
import random
import sqlite3
import subprocess
import types

from ate_sim import persistence_proof_batch as candidate
from ate_sim import persistence_proof_map as maps
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_proof_nodes import Branch, Leaf, Root, empty_root, decode_node
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation.tests.test_stage_0_5_proof_map import DOMAIN, MemoryNodes, proof_map, value
from simulation.tests.test_stage_0_5_proof_batch import reachable

BASE = '1e84f17da40ff126a3a5129da828bb4e82d527cd'
baseline = types.ModuleType('ate_sim.review_baseline_batch')
baseline.__package__ = 'ate_sim'
exec(compile(subprocess.check_output([
    'git', 'show', BASE + ':simulation/ate_sim/persistence_proof_batch.py'
]), 'baseline_persistence_proof_batch.py', 'exec'), baseline.__dict__)


def direct_locator(_domain, key):
    assert type(key) is bytes and len(key) == 32
    return key


def clone(storage):
    result = MemoryNodes()
    result.data = dict(storage.data)
    return result


def check_case(storage, old, changes):
    reference = clone(storage)
    m = proof_map(reference)
    expected = old
    for key, commitment in changes:
        expected = m.set(expected, key, commitment)
    outcomes = []
    for implementation in (baseline, candidate):
        tested = clone(storage)
        got = implementation.update_sorted(proof_map(tested), old, iter(changes))
        assert got == expected
        if got == old:
            assert got is old and not tested.writes
        assert len(tested.reads) == len(set(tested.reads))
        assert len(tested.writes) == len(set(tested.writes))
        assert set(tested.writes) <= reachable(tested, got)
        outcomes.append((got, set(tested.reads), set(tested.writes)))
        assert dict(proof_map(tested).iter_leaves(got)) == dict(m.iter_leaves(expected))
        assert dict(proof_map(tested).iter_leaves(old)) == dict(m.iter_leaves(old))
    assert outcomes[0] == outcomes[1]


def exhaustive():
    keys = [b'\xab' * 31 + bytes([tail]) for tail in (0, 1, 16, 255)]
    count = 0
    for mask in range(16):
        storage = MemoryNodes()
        m = proof_map(storage)
        old = empty_root(DOMAIN)
        for i, key in enumerate(keys):
            if mask & (1 << i):
                old = m.set(old, key, value('old'))
        for choices in itertools.product(range(4), repeat=4):
            # Omit, delete, identical old commitment, or changed commitment.
            changes = [(key, (None, value('old'), value('new'))[choice - 1])
                       for key, choice in zip(keys, choices) if choice]
            check_case(storage, old, changes)
            count += 1
    return count


def randomized():
    rng = random.Random(270113)
    count = 0
    for common in (0, 1, 20, 57, 58, 60, 62, 63):
        prefix = [rng.randrange(16) for _ in range(common)]
        keys = set()
        for _ in range(80):
            ns = prefix + [rng.randrange(16) for _ in range(64-common)]
            keys.add(bytes((ns[i] << 4) | ns[i+1] for i in range(0, 64, 2)))
        keys = sorted(keys)
        storage = MemoryNodes()
        m = proof_map(storage)
        old = empty_root(DOMAIN)
        for step in range(40):
            changes = sorted((key, rng.choice([None, value('old'), value(str(step))]))
                             for key in rng.sample(keys, rng.randrange(1, len(keys)+1)))
            check_case(storage, old, changes)
            old = candidate.update_sorted(m, old, changes)
            count += 1
    return count


def outcome(implementation, storage, root, changes):
    tested = clone(storage)
    try:
        result = implementation.update_sorted(proof_map(tested), root, iter(changes))
        status = ('ok', result)
    except Exception as exc:
        status = (type(exc).__name__, str(exc))
    return status, tested.reads, tested.writes


def corruption():
    keys = [b'\xab' * 29 + i.to_bytes(3, 'big') for i in (0, 1, 16, 17, 4095)]
    storage = MemoryNodes()
    m = proof_map(storage)
    root = empty_root(DOMAIN)
    for key in keys:
        root = m.set(root, key, value('old'))
    count = 0
    for digest in reachable(storage, root):
        for fault in ('missing', 'bytes'):
            bad = clone(storage)
            if fault == 'missing':
                del bad.data[digest]
            else:
                bad.data[digest] = bad.data[digest][:-1] + bytes([bad.data[digest][-1] ^ 1])
            for mask in range(1, 1 << len(keys)):
                for deletion in (False, True):
                    changes = [(key, None if deletion else value('new'))
                               for i, key in enumerate(keys) if mask & (1 << i)]
                    assert outcome(baseline, bad, root, changes) == outcome(candidate, bad, root, changes)
                    count += 1
    # Root count, deep swapped child paths, and bad promoted counts.
    malformed = [Root(root.digest, root.count + 1)]
    node = decode_node(storage.data[root.digest])
    swapped = tuple((slot, node.children[-1-i][1]) for i, (slot, _) in enumerate(node.children))
    malformed.append(storage.store(Branch(node.prefix, swapped)))
    changed_count = list(node.children)
    slot, ref = changed_count[-1]
    changed_count[-1] = (slot, Root(ref.digest, ref.count + 1))
    malformed.append(storage.store(Branch(node.prefix, tuple(changed_count))))
    for bad_root in malformed:
        for mask in range(1, 1 << len(keys)):
            changes = [(key, None) for i, key in enumerate(keys) if mask & (1 << i)]
            assert outcome(baseline, storage, bad_root, changes) == outcome(candidate, storage, bad_root, changes)
            count += 1
    return count


def rollback():
    count = 0
    keys = [b'\xab' * 29 + i.to_bytes(3, 'big') for i in (0, 1, 16, 17, 4095)]
    for implementation in (baseline, candidate):
        for fault in ('generator', 'malformed', 'after-write'):
            db = sqlite3.connect(':memory:')
            store = ProofNodeStore(db)
            store.create_schema()
            read = lambda digest: store.read(DOMAIN, digest)
            write = lambda digest, raw: store.write(DOMAIN, digest, raw)
            m = maps.ProofMap(DOMAIN, read, write)
            db.execute('BEGIN')
            old = implementation.update_sorted(m, m.empty, [(key, value('old')) for key in keys])
            db.commit()
            before = db.execute('SELECT * FROM ate_proof_nodes ORDER BY 1,2').fetchall()
            changes = [(key, value('new')) for key in keys]
            if fault == 'generator':
                def broken():
                    yield from changes[:3]
                    raise OSError('late review generator failure')
                source = broken()
                error = OSError
            elif fault == 'malformed':
                source = changes[:-1] + [(keys[-1], b'bad')]
                error = StoreIntegrityError
            else:
                calls = 0
                def failed_write(digest, raw):
                    nonlocal calls
                    write(digest, raw)
                    calls += 1
                    if calls == 3:
                        raise RuntimeError('late review callback failure after insert')
                m.write_node = failed_write
                source = changes
                error = RuntimeError
            db.execute('SAVEPOINT review')
            try:
                implementation.update_sorted(m, old, source)
            except error:
                pass
            else:
                raise AssertionError('fault failed to propagate')
            assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0] > len(before)
            db.execute('ROLLBACK TO review')
            db.execute('RELEASE review')
            assert db.execute('SELECT * FROM ate_proof_nodes ORDER BY 1,2').fetchall() == before
            assert dict(m.iter_leaves(old)) == {key: value('old') for key in keys}
            db.close()
            count += 1
    return count


def main():
    original = maps.key_locator, candidate.key_locator
    maps.key_locator = candidate.key_locator = baseline.key_locator = direct_locator
    try:
        print(json.dumps({'baseline': BASE, 'exhaustive_cases': exhaustive(),
                          'randomized_transitions': randomized(),
                          'corruption_cases': corruption(), 'rollback_cases': rollback(),
                          'status': 'passed'}, sort_keys=True))
    finally:
        maps.key_locator, candidate.key_locator = original


if __name__ == '__main__':
    main()
