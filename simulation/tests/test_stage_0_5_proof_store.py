"""Immutable nodes participate in caller transactions and survive exact reopen."""
import hashlib
import importlib
import sqlite3

import pytest
from ate_sim.incremental_store import StoreError, StoreIntegrityError
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_nodes import Leaf, empty_root, encode_node, node_digest
from simulation.tests.test_stage_0_5_proof_nodes import framed
from simulation.tests.test_stage_0_5_proof_map import DOMAIN, value


def store(db):
    return importlib.import_module('ate_sim.persistence_proof_store').ProofNodeStore(db)


def mapping(s):
    return ProofMap(DOMAIN,lambda digest:s.read(DOMAIN,digest),
                    lambda digest,raw:s.write(DOMAIN,digest,raw))


def test_caller_owns_commit_and_old_roots_survive_reopen(tmp_path):
    path = tmp_path/'nodes.sqlite'
    db = sqlite3.connect(path); s = store(db); s.create_schema(); m = mapping(s)
    with pytest.raises(StoreError,match='transaction'):
        m.set(empty_root(DOMAIN),b'key',value('one'))
    db.execute('BEGIN')
    first = m.set(empty_root(DOMAIN),b'key',value('one'))
    assert db.in_transaction
    with sqlite3.connect(path) as other:
        assert other.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0] == 0
    db.commit()
    db.execute('BEGIN')
    second = m.set(first,b'key',value('two'))
    assert db.in_transaction
    db.commit(); db.close()
    with sqlite3.connect(path) as reopened:
        m = mapping(store(reopened))
        assert m.get(first,b'key') == value('one')
        assert m.get(second,b'key') == value('two')


def test_rollback_and_savepoint_publish_no_reusable_node(tmp_path):
    db = sqlite3.connect(tmp_path/'nodes.sqlite'); s = store(db); s.create_schema(); m = mapping(s)
    db.execute('BEGIN')
    old = m.set(empty_root(DOMAIN),b'key',value('one'))
    db.commit()
    for begin,rollback in [('BEGIN',('ROLLBACK',)),('SAVEPOINT edit',('ROLLBACK TO edit','RELEASE edit'))]:
        db.execute(begin)
        unpublished = m.set(old,b'key',value('two'))
        assert db.in_transaction
        for command in rollback:db.execute(command)
        with pytest.raises(StoreIntegrityError):m.get(unpublished,b'key')
        assert m.get(old,b'key') == value('one')
        assert s.diagnostics()['clean_cache_bytes'] == 0
    db.close()


def test_duplicate_write_does_not_overwrite_conflicting_stored_bytes(tmp_path):
    with sqlite3.connect(tmp_path/'nodes.sqlite') as db:
        s = store(db);s.create_schema();raw = encode_node(Leaf(b'k'*32,value('one')))
        digest = node_digest(DOMAIN,raw)
        db.execute('BEGIN')
        s.write(DOMAIN,digest,raw)
        before = db.total_changes
        s.write(DOMAIN,digest,raw)
        assert db.total_changes == before
        corrupt = encode_node(Leaf(b'k'*32,value('corrupt')))
        with pytest.raises(StoreIntegrityError):s.write(DOMAIN,digest,corrupt)
        assert s.read(DOMAIN,digest) == raw
        db.execute('UPDATE ate_proof_nodes SET node_bytes=? WHERE map_domain=? AND digest=?',
                   (corrupt,DOMAIN,digest))
        with pytest.raises(StoreIntegrityError):s.write(DOMAIN,digest,raw)
        with pytest.raises(StoreIntegrityError):s.read(DOMAIN,digest)
        assert db.execute('SELECT node_bytes FROM ate_proof_nodes').fetchone()[0] == corrupt


@pytest.mark.parametrize('raw', [b'ATEP\x01L'+b'x'*63,b'x'*697])
def test_hash_consistent_malformed_or_oversized_nodes_are_rejected(tmp_path,raw):
    with sqlite3.connect(tmp_path/'nodes.sqlite') as db:
        s = store(db);s.create_schema()
        digest = hashlib.sha256(framed(b'ate-proof-map-node/1',DOMAIN,raw)).digest()
        db.execute('PRAGMA ignore_check_constraints=ON')
        db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)',(DOMAIN,digest,raw))
        with pytest.raises(StoreIntegrityError):s.read(DOMAIN,digest)


def test_point_replacement_reads_only_bounded_node_path(tmp_path):
    with sqlite3.connect(tmp_path/'nodes.sqlite') as db:
        s = store(db);s.create_schema();m = mapping(s); root = empty_root(DOMAIN)
        db.execute('BEGIN')
        for i in range(1024):root = m.set(root,str(i).encode(),value(str(i)))
        db.commit()
        s.reset_diagnostics();sql=[];db.set_trace_callback(sql.append)
        db.execute('BEGIN')
        changed = m.set(root,b'7',value('new'))
        stats = s.diagnostics()
        assert stats['read_nodes'] <= 66 and stats['written_nodes'] <= 65
        assert stats['clean_cache_bytes'] == 0
        assert all('records' not in statement.lower() for statement in sql)
        db.commit(); db.set_trace_callback(None)
        assert m.get(root,b'7') == value('7') and m.get(changed,b'7') == value('new')
        assert root.count == changed.count == 1024


def test_nul_prefixed_text_cannot_bypass_node_transfer_budget(tmp_path):
    import gc
    import tracemalloc
    with sqlite3.connect(tmp_path/'nodes.sqlite') as db:
        s = store(db);s.create_schema()
        text = '\0' + 'x'*(2*1024*1024)
        db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)',(DOMAIN,b'x'*32,text))
        db.commit();del text;gc.collect()
        assert db.execute('SELECT typeof(node_bytes),length(node_bytes) FROM ate_proof_nodes').fetchone() == ('text',0)
        tracemalloc.start()
        try:
            with pytest.raises(StoreIntegrityError):s.read(DOMAIN,b'x'*32)
            _,peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak < 128*1024, f'corrupt non-BLOB body transferred {peak} Python bytes'
