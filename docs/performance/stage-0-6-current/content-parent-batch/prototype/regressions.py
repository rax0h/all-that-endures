"""Streamed expected memberships check only the union of authenticated paths."""
import importlib
import pytest

from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_proof_nodes import empty_root
from simulation.tests.test_stage_0_5_proof_map import DOMAIN, MemoryNodes, locator, proof_map, value
from simulation.tests.test_stage_0_5_proof_batch import ordered, update


def verify(m, root, members):
    return importlib.import_module('ate_sim.persistence_proof_verify_batch').verify_sorted(m, root, members)


def test_many_parent_checks_read_each_selected_node_once_without_writes():
    storage = MemoryNodes()
    m = proof_map(storage)
    items = [(f'key:{i}'.encode(), value(str(i))) for i in range(512)]
    root = update(m, empty_root(DOMAIN), iter(ordered(items)))
    members = ordered(items + [(f'missing:{i}'.encode(), None) for i in range(128)])
    for key, expected in members:
        assert m.get(root, key) == expected
    point_reads = len(storage.reads)
    storage.reads.clear(); storage.writes.clear()
    verify(m, root, iter(members))
    assert len(storage.reads) == len(set(storage.reads))
    assert len(storage.reads) < point_reads / 2
    assert not storage.writes


@pytest.mark.parametrize('spill', [False, True])
def test_content_parent_checks_use_streamed_proofs_before_source_writes(tmp_path, monkeypatch, spill):
    if spill:
        monkeypatch.setattr(importlib.import_module('ate_sim.persistence_proof_parent_inputs'), 'BUFFER_BYTES', 0)
    from ate_sim.persistence_proof_map import ProofMap
    from ate_sim.persistence_lazy_store import VersionChange
    from simulation.tests.proof_publication_fixtures import (
        make_publication_store, commit_publication, next_authorities, publication_module,
    )
    p = publication_module()
    store, pin, authority = make_publication_store(tmp_path/'content.sqlite', 32)
    original = p._guard_content_parent
    get = ProofMap.get
    active = False
    validated = False
    def guard(*args, **kwargs):
        nonlocal active, validated
        active = True
        try:
            result = original(*args, **kwargs)
            validated = True
            return result
        finally:
            active = False
    def checked_get(*args, **kwargs):
        assert not active, 'content parent repeats point proofs'
        return get(*args, **kwargs)
    def phase(name):
        if name in ('during_version_writes', 'during_segment_writes'):
            assert validated, 'source writes preceded authenticated parent'
    monkeypatch.setattr(p, '_guard_content_parent', guard)
    monkeypatch.setattr(ProofMap, 'get', checked_get)
    store._phase_hook = phase
    try:
        changes = [VersionChange('people', 0, {'wealth': 2})]
        changes += [VersionChange('archive', i, {'old': i+1}) for i in range(32)]
        result = commit_publication(store, pin, authority, version_changes=changes)
        assert result.commit.outcome == 'committed' and validated
        assert not store.db.execute("SELECT 1 FROM sqlite_temp_master WHERE name='ate_content_predecessors'").fetchone()
        new = next_authorities(result)
        row = p.read_version_content_bytes(store, result.commit.pin, *new.content,
            'archive', store.codec.encode(31), expected_record_schema=1)
        assert store.codec.decode(row.payload) == {'old': 32}
    finally:
        store.close()


@pytest.mark.parametrize('seed', range(12))
def test_stream_matches_independent_present_absent_and_retained_maps(seed):
    import random
    rng = random.Random(seed)
    storage = MemoryNodes(); m = proof_map(storage)
    keys = [f'{i}'.encode() for i in range(50)]
    states = []; root = empty_root(DOMAIN); expected = {}
    for _ in range(4):
        changes = [(k, None if rng.randrange(3) == 0 else value(str(rng.random())))
                   for k in rng.sample(keys, 20)]
        root = update(m, root, iter(ordered(changes)))
        for key, commitment in changes:
            if commitment is None: expected.pop(key, None)
            else: expected[key] = commitment
        states.append((root, expected.copy()))
    storage.writes.clear()
    for saved, contents in states:
        members = ordered((k, contents.get(k)) for k in keys)
        verify(m, saved, iter(members))
        for key, wanted in members:
            assert m.get(saved, key) == wanted
        wrong = members.copy()
        key, old = wrong[len(wrong)//2]
        wrong[len(wrong)//2] = key, value('wrong') if old is None else None
        with pytest.raises(StoreIntegrityError): verify(m, saved, iter(wrong))
    assert not storage.writes


@pytest.mark.parametrize('members', [
    [(b'a', b'short')], [(bytearray(b'a'), None)], [(b'a', False)],
    [(b'a',)], [b'ab'], [(b'a', None), (b'a', None)],
])
def test_malformed_duplicate_members_reject_without_writes(members):
    storage = MemoryNodes(); m = proof_map(storage)
    with pytest.raises(StoreIntegrityError): verify(m, m.empty, iter(members))
    assert not storage.writes


def test_unsorted_and_late_input_failure_propagate_without_writes():
    storage = MemoryNodes(); m = proof_map(storage)
    with pytest.raises(StoreIntegrityError):
        verify(m, m.empty, iter(reversed(ordered([(b'a', None), (b'b', None)]))))
    def failing():
        yield b'a', None
        raise RuntimeError('member source failed')
    with pytest.raises(RuntimeError, match='member source failed'):
        verify(m, m.empty, failing())
    assert not storage.writes


@pytest.mark.parametrize('fault', ['missing', 'bytes', 'count', 'path', 'domain'])
def test_selected_corruption_is_rejected_including_after_previous_valid_call(fault):
    from ate_sim.persistence_proof_nodes import Root, Branch, decode_node
    storage = MemoryNodes(); m = proof_map(storage)
    members = [(b'a', value('a')), (b'b', value('b'))]
    root = update(m, m.empty, iter(ordered(members)))
    verify(m, root, iter(ordered(members)))
    node = decode_node(storage.data[root.digest])
    if fault == 'count': root = Root(root.digest, root.count + 1)
    elif fault == 'path':
        slots = [slot for slot, _ in node.children]
        root = storage.store(Branch(node.prefix, tuple(zip(slots, [r for _, r in reversed(node.children)]))))
    elif fault == 'domain': m = proof_map(storage, b'wrong-domain')
    elif fault == 'missing': del storage.data[root.digest]
    else: storage.data[root.digest] = storage.data[root.digest][:-1] + b'!'
    storage.writes.clear()
    with pytest.raises(StoreIntegrityError): verify(m, root, iter(ordered(members)))
    assert not storage.writes


def test_empty_inputs_validate_root_without_node_reads():
    from ate_sim.persistence_proof_nodes import Root
    storage = MemoryNodes(); m = proof_map(storage)
    verify(m, m.empty, iter(()))
    assert not storage.reads
    with pytest.raises(StoreIntegrityError): verify(m, Root(b'x'*32, 0), iter(()))


def test_maximum_depth_reads_exact_path_and_never_unselected_siblings():
    from ate_sim.persistence_proof_nodes import Leaf, Branch
    storage = MemoryNodes(); m = proof_map(storage)
    key = b'deep'; raw = locator(key)
    nibbles = tuple(n for byte in raw for n in (byte >> 4, byte & 15))
    root = storage.store(Leaf(raw, value('old')))
    for depth in reversed(range(64)):
        sibling_slot = (nibbles[depth] + 1) % 16
        prefix = nibbles[:depth] + (sibling_slot,) + (0,) * (63-depth)
        encoded = bytes((prefix[i] << 4) | prefix[i+1] for i in range(0, 64, 2))
        sibling = storage.store(Leaf(encoded, value(str(depth))))
        root = storage.store(Branch(nibbles[:depth], tuple(sorted(((nibbles[depth], root), (sibling_slot, sibling))))))
    storage.reads.clear(); storage.writes.clear()
    verify(m, root, iter([(key, value('old'))]))
    assert len(storage.reads) == 65 and len(set(storage.reads)) == 65
    assert not storage.writes


@pytest.mark.parametrize('parent', [0, 1])
@pytest.mark.parametrize('spill', [False, True])
def test_parent_stream_failure_rolls_back_cleans_temp_and_can_retry(tmp_path, monkeypatch, parent, spill):
    if spill:
        monkeypatch.setattr(importlib.import_module('ate_sim.persistence_proof_parent_inputs'), 'BUFFER_BYTES', 0)
    from simulation.tests.proof_publication_fixtures import make_publication_store, commit_publication, publication_module
    module = importlib.import_module('ate_sim.persistence_proof_verify_batch')
    original = module.verify_sorted
    store, pin, authority = make_publication_store(tmp_path/'failed.sqlite', 3)
    calls = []
    def fault(*args, **kwargs):
        index = len(calls); calls.append(index)
        if index == parent: raise RuntimeError('parent stream failed')
        return original(*args, **kwargs)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(module, 'verify_sorted', fault)
            with pytest.raises(RuntimeError, match='parent stream failed'):
                commit_publication(store, pin, authority, token='failed')
        assert store.generation == pin.captured_head
        assert not store.db.execute("SELECT 1 FROM sqlite_temp_master WHERE name='ate_content_predecessors'").fetchone()
        for table in ('ate_record_roots', 'ate_scope_generations', 'ate_content_generations'):
            assert store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 1
        result = publication_module().resolve_content_commit(store, pin, *authority.content,
            scope_authority=authority.scope, record_authority=authority.record, commit_token='failed')
        assert result.commit.outcome == 'not_committed'
        retry = commit_publication(store, pin, authority, token='retry')
        assert retry.commit.outcome == 'committed'
    finally:
        store.close()


def test_small_parent_batch_avoids_temp_metadata_writes(tmp_path, monkeypatch):
    from ate_sim.persistence_sqlite_guard import GuardedConnection
    from simulation.tests.proof_publication_fixtures import make_publication_store, commit_publication
    store, pin, authority = make_publication_store(tmp_path/'memory.sqlite', 3)
    execute = GuardedConnection.execute
    def checked(db, sql, *args, **kwargs):
        assert 'ate_content_predecessors' not in sql, 'small parent batch wrote a TEMP spool'
        return execute(db, sql, *args, **kwargs)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(GuardedConnection, 'execute', checked)
            result = commit_publication(store, pin, authority)
        assert result.commit.outcome == 'committed'
    finally:
        store.close()
