"""Compressed batch work follows stored prefixes without virtual-level walks."""
import cProfile
import pstats
import random

import pytest

from ate_sim import persistence_proof_batch as batch
from ate_sim import persistence_proof_map as maps
from ate_sim.persistence_proof_nodes import empty_root
from simulation.tests.test_stage_0_5_proof_map import DOMAIN, MemoryNodes, proof_map, value


def test_single_compressed_leaf_update_has_constant_merge_work():
    storage = MemoryNodes(); m = proof_map(storage)
    old = m.set(empty_root(DOMAIN), b'leaf', value('before'))
    storage.reads.clear(); storage.writes.clear()
    profile = cProfile.Profile()
    profile.enable()
    changed = batch.update_sorted(m, old, [(b'leaf', value('after'))])
    profile.disable()
    calls = sum(v[1] for (file, _, name), v in pstats.Stats(profile).stats.items()
                if file.endswith('persistence_proof_batch.py') and name == 'merge')
    assert calls <= 4
    assert len(storage.reads) == 1 and len(storage.writes) == 1
    assert changed == m.set(old, b'leaf', value('after'))
    assert m.get(old, b'leaf') == value('before')


def forced_locators(monkeypatch):
    def locate(_domain, key):
        return b'\xab' * 29 + int(key).to_bytes(3, 'big')
    monkeypatch.setattr(batch, 'key_locator', locate)
    monkeypatch.setattr(maps, 'key_locator', locate)
    return locate


@pytest.mark.parametrize('seed', [3, 91, 208])
def test_long_compressed_prefix_batches_match_point_updates(monkeypatch, seed):
    locate = forced_locators(monkeypatch)
    storage = MemoryNodes(); m = proof_map(storage); root = empty_root(DOMAIN)
    rng = random.Random(seed); keys = [str(i).encode() for i in range(300)]
    expected = {}
    for i in [150, 290, 299]:
        root = m.set(root, keys[i], value(str(i)));expected[keys[i]] = value(str(i))
    snapshots = []
    for step in range(12):
        changes = [(key, None if rng.randrange(3) == 0 else value(f'{step}:{key}'))
                   for key in rng.sample(keys, 40)]
        before = root; sequential = root
        for key, new in changes:
            sequential = m.set(sequential, key, new)
            if new is None:expected.pop(key, None)
            else:expected[key] = new
        root = batch.update_sorted(m, root, sorted(changes, key=lambda row:locate(DOMAIN,row[0])))
        assert root == sequential
        assert dict(m.iter_leaves(root)) == {locate(DOMAIN,k):v for k,v in expected.items()}
        snapshots.append((root,dict(expected)))
        assert before.count >= 0
    for old, contents in snapshots:
        assert dict(m.iter_leaves(old)) == {locate(DOMAIN,k):v for k,v in contents.items()}


def test_many_absent_deletes_do_not_grow_wrapper_stack(monkeypatch):
    forced_locators(monkeypatch)
    storage = MemoryNodes();m = proof_map(storage)
    root = m.set(empty_root(DOMAIN), b'4095', value('retained'))
    storage.reads.clear();storage.writes.clear()
    changes = ((str(i).encode(), None) for i in range(4095))
    assert batch.update_sorted(m, root, changes) is root
    assert storage.writes == [] and len(storage.reads) == 1
