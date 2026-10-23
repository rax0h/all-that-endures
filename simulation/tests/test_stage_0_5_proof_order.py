"""Ordered certificates must reject incomplete or reordered result pages."""
import hashlib
import importlib
import sqlite3
from dataclasses import replace

import pytest

from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_proof_nodes import Root, empty_root
from simulation.tests.test_stage_0_5_proof_map import DOMAIN, MemoryNodes, proof_map, value


def module():
    return importlib.import_module('ate_sim.persistence_proof_order')


def frame(*parts):
    return b''.join(len(p).to_bytes(8, 'big') + p for p in parts)


def optional(key):
    return (b'0', b'') if key is None else (b'1', key)


def independent_entry(entry):
    return hashlib.sha256(frame(b'ate-proof-order-entry/1', DOMAIN, entry.key, entry.value,
        *optional(entry.previous), *optional(entry.following))).digest()


def fixture():
    c = module(); storage = MemoryNodes(); m = proof_map(storage)
    keys = [b'', b'a', b'aa', b'b', b'c']
    entries = [c.OrderEntry(k, value(str(i)), keys[i-1] if i else None,
                           keys[i+1] if i+1 < len(keys) else None) for i,k in enumerate(keys)]
    index = empty_root(DOMAIN)
    for entry in entries:
        index = m.set(index, entry.key, independent_entry(entry))
    root = c.OrderRoot(index, keys[0], keys[-1])
    return c, storage, m, root, entries, c.root_commitment(DOMAIN, root)


def test_exact_order_entry_and_descriptor_vectors():
    c, _, _, root, entries, commitment = fixture()
    for entry in entries:
        assert c.entry_commitment(DOMAIN, entry) == independent_entry(entry)
    assert commitment == hashlib.sha256(frame(b'ate-proof-order-root/1', DOMAIN,
        root.index.digest, b'\x00'*7+b'\x05', b'1', b'', b'1', b'c')).digest()
    assert c.entry_commitment(DOMAIN, entries[1]) != c.entry_commitment(b'other', entries[1])
    assert c.root_commitment(DOMAIN, root) != c.root_commitment(b'other', root)


def test_query_order_key_matches_sql_with_ties_and_repeated_records():
    c = module(); db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE entries(ordinal INTEGER, typed_key BLOB)')
    rows = [(4,b'b'), (0,b'\xff'), (4,b'a'), (0,b''), (4,b'\x00'), (8,b'a')]
    db.executemany('INSERT INTO entries VALUES(?,?)', rows)
    expected = list(db.execute('SELECT ordinal,typed_key FROM entries ORDER BY ordinal,typed_key'))
    assert sorted(rows, key=lambda x:c.query_order_key(*x)) == expected
    assert c.query_order_key(4,b'a') == b'\x00'*7+b'\x04a'
    for bad in (-1, 2**63, True, 1.0):
        with pytest.raises(StoreIntegrityError): c.query_order_key(bad,b'a')
    db.close()


@pytest.mark.parametrize('after,before,limit,positions,boundary', [
    (None,None,128,[0,1,2,3,4],None), (b'a',None,2,[2,3],None),
    (b'b',None,128,[4],None), (None,b'aa',128,[0,1],None),
    (b'ab',b'b',128,[],2), (None,b'',128,[],0),
    (b'c',None,128,[],4), (b'a',b'a',128,[],None),
])
def test_full_partial_ranged_and_empty_pages(after,before,limit,positions,boundary):
    c,_,m,root,entries,expected = fixture()
    rows = tuple(entries[i] for i in positions)
    assert c.verify_page(m,root,expected,rows=iter(rows),after=after,before=before,limit=limit,
                         boundary=None if boundary is None else entries[boundary]) == rows


@pytest.mark.parametrize('positions', [[1,2,3,4], [0,2,3,4], [0,1,2,3], [0,1,1,2,3,4], [0,2,1,3,4]])
def test_omission_duplicate_reorder_and_truncated_tail_are_rejected(positions):
    c,_,m,root,entries,expected = fixture()
    with pytest.raises(StoreIntegrityError):
        c.verify_page(m,root,expected,rows=(entries[i] for i in positions))


@pytest.mark.parametrize('bad', ['descriptor','neighbors','value','key','empty','surplus-boundary','range','domain'])
def test_forged_roots_entries_and_false_empty_results_are_rejected(bad):
    c,_,m,root,entries,expected = fixture(); rows = list(entries); kwargs = {}
    if bad == 'descriptor': root = replace(root,last=b'z')
    elif bad == 'neighbors': rows[2] = replace(rows[2],previous=b'')
    elif bad == 'value': rows[2] = replace(rows[2],value=value('forged'))
    elif bad == 'key': rows[2] = replace(rows[2],key=b'ab')
    elif bad == 'empty': rows=[];kwargs['boundary']=entries[2]
    elif bad == 'surplus-boundary': kwargs['boundary']=entries[0]
    elif bad == 'range': kwargs['after']=b'a'
    elif bad == 'domain': m=proof_map(MemoryNodes(), b'wrong')
    with pytest.raises(StoreIntegrityError): c.verify_page(m,root,expected,rows=rows,**kwargs)


def test_stale_page_does_not_authenticate_against_successor_root():
    c,_,m,root,entries,_ = fixture()
    changed = replace(entries[2],value=value('new'))
    successor = replace(root,index=m.set(root.index, changed.key, independent_entry(changed)))
    with pytest.raises(StoreIntegrityError):
        c.verify_page(m,successor,c.root_commitment(DOMAIN,successor),rows=entries)


def test_empty_root_and_empty_byte_endpoints_remain_distinct():
    c = module(); m=proof_map(MemoryNodes()); root=c.OrderRoot(m.empty,None,None)
    expected=c.root_commitment(DOMAIN,root)
    assert c.verify_page(m,root,expected,rows=[]) == ()
    with pytest.raises(StoreIntegrityError): c.root_commitment(DOMAIN,replace(root,first=b''))
    only=c.OrderEntry(b'',value('only'),None,None)
    singleton=c.OrderRoot(m.set(m.empty,b'',independent_entry(only)),b'',b'')
    assert c.verify_page(m,singleton,c.root_commitment(DOMAIN,singleton),rows=[only]) == (only,)


def test_page_limit_stops_unbounded_input_after_one_surplus_row():
    c,_,m,root,entries,expected = fixture(); consumed=[]
    def unbounded():
        while True:
            consumed.append(1);yield entries[0]
    with pytest.raises(StoreIntegrityError): c.verify_page(m,root,expected,rows=unbounded(),limit=1)
    assert len(consumed) <= 2
    for limit in (0,129,True,1.0):
        with pytest.raises(StoreIntegrityError): c.verify_page(m,root,expected,rows=[],limit=limit)


@pytest.mark.parametrize('bad', ['pointer-type','pointer-order','value-type','root-count','root-extrema'])
def test_malformed_order_proof_fields_are_rejected(bad):
    c,_,m,root,entries,_=fixture()
    with pytest.raises(StoreIntegrityError):
        if bad == 'pointer-type': c.entry_commitment(DOMAIN,replace(entries[1],previous=''))
        elif bad == 'pointer-order': c.entry_commitment(DOMAIN,replace(entries[1],following=b''))
        elif bad == 'value-type': c.entry_commitment(DOMAIN,replace(entries[1],value=True))
        elif bad == 'root-count': c.root_commitment(DOMAIN,replace(root,index=Root(root.index.digest,True)))
        else: c.root_commitment(DOMAIN,replace(root,first=b'z'))
