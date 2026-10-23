"""Caller-owned SQLite ordered transitions match independent complete rebuilds."""
import bisect
import importlib
import random
import sqlite3
from dataclasses import replace

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_order import OrderEntry, root_commitment, verify_page
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation.tests.test_stage_0_5_proof_map import DOMAIN, value
from simulation.tests.test_stage_0_5_proof_order import independent_entry


def module():
    return importlib.import_module('ate_sim.persistence_proof_order_edit')


def setup(tmp_path):
    e = module(); db = sqlite3.connect(tmp_path/'order.sqlite')
    db.execute('PRAGMA temp_store=FILE'); db.execute('PRAGMA cache_size=-2048')
    store = ProofNodeStore(db);store.create_schema()
    m = ProofMap(DOMAIN, lambda d:store.read(DOMAIN,d),lambda d,raw:store.write(DOMAIN,d,raw))
    return e,db,store,m


def entries(values):
    keys=sorted(values)
    return {key:OrderEntry(key,values[key],keys[i-1] if i else None,
                          keys[i+1] if i+1<len(keys) else None) for i,key in enumerate(keys)}


def edits(values, delta):
    e=module(); parent=entries(values); keys=sorted(values)
    for key,new_value in sorted(delta.items()):
        at=bisect.bisect_left(keys,key);old=parent.get(key)
        if new_value is None and old is None:
            yield e.OrderEdit(key,None,None,None,None)
        else:
            right=at+1 if old else at
            yield e.OrderEdit(key,new_value,old,parent[keys[at-1]] if at else None,
                              parent[keys[right]] if right<len(keys) else None)


def initial(e,db,m,values):
    db.execute('BEGIN')
    root=e.build_ordered(m,db,iter(sorted(values.items())))
    db.commit();return root


def assert_mapping(m,root,values):
    expected=entries(values);keys=sorted(values)
    assert root.index.count==len(values)
    assert root.first==(keys[0] if keys else None) and root.last==(keys[-1] if keys else None)
    for key,entry in expected.items():assert m.get(root.index,key)==independent_entry(entry)
    rows=tuple(expected[key] for key in keys)
    assert verify_page(m,root,root_commitment(DOMAIN,root),rows=iter(rows))==rows


def test_construction_strict_stream_preserves_exact_positions(tmp_path):
    e,db,store,m=setup(tmp_path)
    from ate_sim.persistence_proof_order import query_order_key
    values={query_order_key(i,b'repeated'):value(str(i)) for i in range(5)}
    values[b'']=value('empty')
    root=initial(e,db,m,values);assert_mapping(m,root,values)
    assert store.diagnostics()['written_nodes']>len(values)
    assert db.execute("SELECT count(*) FROM sqlite_temp_master WHERE name LIKE 'ate_order_%'").fetchone()[0]==0
    db.close()


def test_seeded_transitions_match_independent_mapping_and_complete_rebuild(tmp_path):
    e,db,_,m=setup(tmp_path); values={bytes([i]):value(str(i)) for i in range(0,80,2)}
    root=initial(e,db,m,values);retained=[(root,dict(values))];rng=random.Random(9091)
    for step in range(25):
        delta={bytes([i]):None if rng.randrange(3)==0 else value(f'{step}:{i}') for i in rng.sample(range(90),12)}
        db.execute('BEGIN');new=e.update_ordered(m,db,root,root_commitment(DOMAIN,root),edits(values,delta))
        for key,commitment in delta.items():
            if commitment is None:values.pop(key,None)
            else:values[key]=commitment
        rebuilt=e.build_ordered(m,db,iter(sorted(values.items())))
        assert new==rebuilt;db.commit();root=new;assert_mapping(m,root,values)
        if step%5==0:retained.append((root,dict(values)))
    for old,expected in retained:assert_mapping(m,old,expected)
    db.close()


@pytest.mark.parametrize('delta', [
    {b'a':None,b'b':None,b'ab':value('insert')},
    {b'a':None,b'd':None,b'0':value('head'),b'z':value('tail')},
    {b'a':None,b'b':None,b'c':None,b'd':None},
    {b'a':None,b'aa':value('reinsert'),b'd':value('replace')},
])
def test_adjacent_disjoint_extrema_all_deletion_and_reinsertion(tmp_path,delta):
    e,db,_,m=setup(tmp_path);values={k:value(k.decode()) for k in [b'a',b'b',b'c',b'd']}
    root=initial(e,db,m,values);db.execute('BEGIN')
    new=e.update_ordered(m,db,root,root_commitment(DOMAIN,root),edits(values,delta));db.commit()
    expected=dict(values)
    for key,v in delta.items():
        if v is None:expected.pop(key,None)
        else:expected[key]=v
    assert_mapping(m,new,expected);assert_mapping(m,root,values);db.close()


@pytest.mark.parametrize('fault',['old','neighbor','missing-neighbor','gap','missing-old','expected-root','inconsistent-neighbor'])
def test_tampered_parent_and_absence_witnesses_are_rejected(tmp_path,fault):
    e,db,_,m=setup(tmp_path);values={k:value(k.decode()) for k in [b'a',b'b',b'c',b'd']}
    root=initial(e,db,m,values); expected=root_commitment(DOMAIN,root)
    delta=list(edits(values,{b'b':value('new')}))
    if fault=='old':delta[0]=replace(delta[0],old=replace(delta[0].old,value=value('forged')))
    elif fault=='neighbor':delta[0]=replace(delta[0],previous=replace(delta[0].previous,following=b'c'))
    elif fault=='missing-neighbor':delta[0]=replace(delta[0],following=None)
    elif fault=='gap':delta=list(edits(values,{b'ab':value('new')}));delta[0]=replace(delta[0],following=entries(values)[b'd'])
    elif fault=='missing-old':delta[0]=replace(delta[0],old=None)
    elif fault=='expected-root':expected=value('forged')
    else:
        delta=list(edits(values,{b'b':None,b'd':None}))
        delta[1]=replace(delta[1],previous=replace(delta[1].previous,value=value('forged')))
    db.execute('BEGIN')
    with pytest.raises(StoreIntegrityError):e.update_ordered(m,db,root,expected,iter(delta))
    db.rollback();assert_mapping(m,root,values);db.close()


def test_noop_preserves_root_identity_and_writes_no_nodes(tmp_path):
    e,db,store,m=setup(tmp_path);values={b'a':value('old'),b'c':value('old')}
    root=initial(e,db,m,values);store.reset_diagnostics();db.execute('BEGIN')
    assert e.update_ordered(m,db,root,root_commitment(DOMAIN,root),iter(())) is root
    assert e.update_ordered(m,db,root,root_commitment(DOMAIN,root),edits(values,{b'a':value('old'),b'b':None})) is root
    assert store.diagnostics()['write_requests']==0
    db.rollback();db.close()


@pytest.mark.parametrize('bad_rows', [[(b'b',value('b')),(b'a',value('a'))],[(b'a',value('a')),(b'a',value('a'))],[(b'a',True)],[(b'a',)],
                                   [None,(b'a',value('a'))],[(b'a',value('a')),None,(b'b',value('b'))]])
def test_bad_construction_stream_rolls_back(tmp_path,bad_rows):
    e,db,_,m=setup(tmp_path);db.execute('BEGIN')
    with pytest.raises(StoreIntegrityError):e.build_ordered(m,db,iter(bad_rows))
    db.rollback();assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]==0;db.close()


def test_rejects_missing_caller_transaction(tmp_path):
    e,db,_,m=setup(tmp_path)
    with pytest.raises(StoreError):e.build_ordered(m,db,iter([(b'a',value('a'))]))
    root=initial(e,db,m,{b'a':value('a')})
    with pytest.raises(StoreError):e.update_ordered(m,db,root,root_commitment(DOMAIN,root),iter(()))
    db.close()


@pytest.mark.parametrize('fault',['malformed','generator','write'])
def test_late_input_and_post_insert_write_failure_caller_rollback(tmp_path,fault):
    e,db,_,m=setup(tmp_path);values={k:value(k.decode()) for k in [b'a',b'b',b'c',b'd']}
    root=initial(e,db,m,values);count=db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]
    candidates=list(edits(values,{b'b':value('new'),b'c':None}))
    def stream():
        yield from candidates
        if fault=='malformed':yield b'invalid'
        elif fault=='generator':raise OSError('late input fault')
    original=m.write_node
    def fail_after_insert(digest,raw):
        original(digest,raw)
        raise OSError('post-insert fault')
    if fault=='write':m.write_node=fail_after_insert
    db.execute('SAVEPOINT transition')
    with pytest.raises(StoreIntegrityError if fault=='malformed' else OSError):
        e.update_ordered(m,db,root,root_commitment(DOMAIN,root),stream())
    if fault=='write':assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]>count
    db.execute('ROLLBACK TO transition');db.execute('RELEASE transition');m.write_node=original
    assert db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]==count
    assert_mapping(m,root,values);db.close()


def test_duplicate_or_unsorted_edits_are_rejected(tmp_path):
    e,db,_,m=setup(tmp_path);values={b'a':value('a'),b'b':value('b')};root=initial(e,db,m,values)
    delta=list(edits(values,{b'a':None,b'b':None}))
    for bad in (list(reversed(delta)),[delta[0],delta[0]]):
        db.execute('BEGIN')
        with pytest.raises(StoreIntegrityError):e.update_ordered(m,db,root,root_commitment(DOMAIN,root),iter(bad))
        db.rollback()
    db.close()
