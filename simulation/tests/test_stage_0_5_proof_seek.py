"""Ordered roots must seek exact committed byte keys without source scans."""
import hashlib
import importlib
import random
import sqlite3
import tracemalloc
from dataclasses import replace

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError
from simulation.tests.test_stage_0_5_proof_order import frame


def module():return importlib.import_module('ate_sim.persistence_proof_seek')


def make_map(tmp_path):
    db=sqlite3.connect(tmp_path/'seek.sqlite',isolation_level=None)
    db.execute('PRAGMA cache_size=-2048');db.execute('PRAGMA temp_store=FILE')
    db.execute('PRAGMA temp.cache_size=-2048')
    m=module().OrderedSeekMap(db,b'test-domain')
    db.execute('BEGIN');m.create_schema();db.commit()
    return db,m


def value(n):return hashlib.sha256(str(n).encode()).digest()


def collect(m,root,after=None):
    result=[]
    while True:
        page=m.page(root,after=after,limit=17)
        if not page:break
        result.extend(page);after=page[-1][0]
    return result


def test_independent_node_bytes_and_empty_digest(tmp_path):
    db,m=make_map(tmp_path)
    assert m.empty.digest==hashlib.sha256(frame(b'ate-ordered-seek-empty/1',b'test-domain')).digest()
    db.execute('BEGIN');root=m.set(m.empty,b'a',b'v'*32);db.commit()
    raw=b'ATES\x01L'+(1).to_bytes(4,'big')+b'a'+b'v'*32
    assert root.digest==hashlib.sha256(frame(b'ate-ordered-seek-node/1',b'test-domain',raw)).digest()
    assert db.execute('SELECT raw FROM ate_ordered_seek_nodes WHERE digest=?',(root.digest,)).fetchone()[0]==raw
    assert m.get(root,b'a')==b'v'*32
    db.close()


def test_empty_prefix_zero_and_absent_middle_cursors(tmp_path):
    db,m=make_map(tmp_path)
    keys=[b'',b'\x00',b'\x00\x00',b'a',b'a\x00',b'aa',b'a\xff',b'b',b'\xff']
    db.execute('BEGIN');root=m.build((k,value(i)) for i,k in enumerate(keys));db.commit()
    expected=list(zip(keys,(value(i) for i in range(len(keys)))))
    assert collect(m,root)==expected
    for after in [b'',b'\x00\x01',b'`',b'a',b'a\x01',b'az',b'\xff',b'\xff\x00']:
        assert collect(m,root,after)==[row for row in expected if row[0]>after]
    m.verify(root)
    db.close()


def test_seeded_transitions_match_model_canonical_rebuild_and_retained_roots(tmp_path):
    db,m=make_map(tmp_path);root=m.empty;model={};old=[];rng=random.Random(713)
    keys=[bytes([i//6])+b'\x00prefix'+bytes([i%6]) for i in range(75)]
    for step in range(180):
        key=rng.choice(keys);v=None if rng.randrange(4)==0 else value(step)
        if step%30==0:old.append((root,dict(model)))
        db.execute('BEGIN');root=m.set(root,key,v);db.commit()
        if v is None:model.pop(key,None)
        else:model[key]=v
        assert root.count==len(model)
        if step%30==0:
            assert collect(m,root)==sorted(model.items())
            db.execute('BEGIN');rebuilt=m.build(iter(sorted(model.items())));db.commit()
            assert rebuilt==root
    for previous,expected in old:assert collect(m,previous)==sorted(expected.items())
    db.execute('BEGIN')
    for key in sorted(model):root=m.set(root,key,None)
    db.commit();assert root==m.empty
    db.close()


def test_no_op_preserves_root_identity_and_zero_immutable_writes(tmp_path):
    db,m=make_map(tmp_path);db.execute('BEGIN');root=m.set(m.empty,b'k',value(1));db.commit()
    m.reset_diagnostics();db.execute('BEGIN')
    assert m.set(root,b'k',value(1)) is root
    assert m.set(root,b'missing',None) is root
    db.commit();assert m.diagnostics()['written_nodes']==0
    db.close()


def test_deep_prefix_path_uses_iterative_seek_and_spilled_update(tmp_path):
    db,m=make_map(tmp_path);db.execute('BEGIN');root=m.empty
    for length in range(1100,0,-1):root=m.set(root,b'a'*length,value(length))
    db.commit();old=root
    assert m.get(root,b'a'*1100)==value(1100)
    assert m.page(root,after=b'a'*1097,limit=4)==tuple((b'a'*n,value(n)) for n in (1098,1099,1100))
    tracemalloc.start();db.execute('BEGIN')
    try:
        root=m.set(root,b'a'*1100,value(9999));_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    db.commit();assert peak<2*1024*1024
    assert m.get(root,b'a'*1100)==value(9999) and m.get(old,b'a'*1100)==value(1100)
    db.execute('BEGIN');rebuilt=m.build((b'a'*n,value(n)) for n in range(1,1101));db.commit()
    assert rebuilt==old
    assert db.execute('SELECT count(*) FROM ate_ordered_seek_paths').fetchone()[0]==0
    db.close()


@pytest.mark.parametrize('fault',['missing','raw','count','domain','large-blob','large-text'])
def test_corrupt_nodes_and_root_context_fail_closed(tmp_path,fault):
    db,m=make_map(tmp_path);db.execute('BEGIN');root=m.build([(b'a',value(1)),(b'b',value(2))]);db.commit()
    if fault=='missing':db.execute('DELETE FROM ate_ordered_seek_nodes WHERE digest=?',(root.digest,))
    elif fault in ('raw','large-blob','large-text'):
        raw=b'bad' if fault=='raw' else b'x'*(2*1024*1024) if fault=='large-blob' else 'x'*(2*1024*1024)
        db.execute('UPDATE ate_ordered_seek_nodes SET raw=? WHERE digest=?',(raw,root.digest))
    elif fault=='count':root=replace(root,count=3)
    else:m=module().OrderedSeekMap(db,b'foreign-domain')
    tracemalloc.start()
    try:
        with pytest.raises(StoreIntegrityError):m.page(root)
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert peak<128*1024
    db.close()


@pytest.mark.parametrize('rows',[[None],[(b'a',value(1)),(b'a',value(2))],[(b'b',value(1)),(b'a',value(2))],[(b'a',b'short')]])
def test_bad_build_stream_and_rollback_keep_parent(tmp_path,rows):
    db,m=make_map(tmp_path);db.execute('BEGIN');root=m.set(m.empty,b'parent',value(7));db.commit()
    count=db.execute('SELECT count(*) FROM ate_ordered_seek_nodes').fetchone()[0]
    db.execute('BEGIN')
    with pytest.raises(StoreIntegrityError):m.build(iter(rows))
    db.rollback();assert m.get(root,b'parent')==value(7)
    assert db.execute('SELECT count(*) FROM ate_ordered_seek_nodes').fetchone()[0]==count
    db.close()


def test_late_generator_and_post_insert_failure_rollback(tmp_path,monkeypatch):
    db,m=make_map(tmp_path);db.execute('BEGIN');root=m.build([(b'a',value(1)),(b'z',value(2))]);db.commit()
    count=db.execute('SELECT count(*) FROM ate_ordered_seek_nodes').fetchone()[0]
    def stream():
        yield b'b',value(3)
        raise RuntimeError('late source')
    db.execute('BEGIN')
    with pytest.raises(RuntimeError):m.build(stream())
    db.rollback()
    original=m._write
    def fail_after_write(node):
        original(node)
        raise RuntimeError('after insert')
    monkeypatch.setattr(m,'_write',fail_after_write);db.execute('BEGIN')
    with pytest.raises(RuntimeError):m.set(root,b'c',value(4))
    db.rollback();assert collect(m,root)==[(b'a',value(1)),(b'z',value(2))]
    assert db.execute('SELECT count(*) FROM ate_ordered_seek_nodes').fetchone()[0]==count
    db.close()


def test_caller_transaction_and_input_types(tmp_path):
    db,m=make_map(tmp_path)
    with pytest.raises(StoreError):m.set(m.empty,b'a',value(1))
    with pytest.raises(StoreError):m.create_schema()
    for after,limit in [('wrong',1),(None,0),(None,257),(None,True)]:
        with pytest.raises(StoreIntegrityError):m.page(m.empty,after=after,limit=limit)
    db.execute('BEGIN')
    with pytest.raises(StoreIntegrityError):m.set(m.empty,b'x'*32769,value(1))
    db.rollback();db.close()


def test_build_streams_active_sql_cursor_without_schema_lock(tmp_path):
    db,m=make_map(tmp_path)
    db.execute('CREATE TABLE source(k BLOB PRIMARY KEY,v BLOB)')
    db.executemany('INSERT INTO source VALUES(?,?)',[(b'a',value(1)),(b'b',value(2))])
    db.execute('BEGIN');cursor=db.execute('SELECT k,v FROM source ORDER BY k')
    try:root=m.build(cursor)
    finally:cursor.close()
    db.commit();assert collect(m,root)==[(b'a',value(1)),(b'b',value(2))]
    assert db.execute('SELECT count(*) FROM ate_ordered_seek_paths').fetchone()[0]==0
    db.close()


def test_sorted_construction_writes_only_final_radix_nodes(tmp_path):
    db,m=make_map(tmp_path);m.reset_diagnostics();db.execute('BEGIN')
    root=m.build((i.to_bytes(4,'big'),value(i)) for i in range(200));db.commit()
    assert root.count==200 and m.diagnostics()['written_nodes']<=399
    assert m.get(root,(199).to_bytes(4,'big'))==value(199)
    db.close()


def test_independent_branch_frame_and_wrong_child_prefix(tmp_path):
    db,m=make_map(tmp_path);db.execute('BEGIN');root=m.build([(b'a',value(1)),(b'b',value(2))]);db.commit()
    def leaf_digest(key,v):
        raw=b'ATES\x01L'+len(key).to_bytes(4,'big')+key+v
        return hashlib.sha256(frame(b'ate-ordered-seek-node/1',b'test-domain',raw)).digest()
    raw=(b'ATES\x01B'+(1).to_bytes(4,'big')+b'\x07\x02'+b'\x02'+(1).to_bytes(8,'big')+leaf_digest(b'a',value(1))+
         b'\x03'+(1).to_bytes(8,'big')+leaf_digest(b'b',value(2)))
    assert root.digest==hashlib.sha256(frame(b'ate-ordered-seek-node/1',b'test-domain',raw)).digest()
    forged=raw[:10]+b'\x08'+raw[11:]
    digest=hashlib.sha256(frame(b'ate-ordered-seek-node/1',b'test-domain',forged)).digest()
    db.execute('INSERT INTO ate_ordered_seek_nodes VALUES(?,?,?)',(b'test-domain',digest,forged))
    with pytest.raises(StoreIntegrityError):m.page(replace(root,digest=digest))
    db.close()
