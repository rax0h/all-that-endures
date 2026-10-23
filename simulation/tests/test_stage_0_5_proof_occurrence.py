"""Complete physical owner/group pages need accepted ordered authority."""
from dataclasses import replace
import hashlib
import tracemalloc

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError, StoreConflictError
from ate_sim.persistence_lazy_store import IdentityOccurrenceChange, VersionChange, _identity_occurrence_checksum
from simulation.tests.proof_occurrence_fixtures import occurrence_module, make_occurrence_store, construct_occurrence_certificates, metadata
from simulation.tests.test_stage_0_5_proof_order import frame


def setup_source(tmp_path):
    o = occurrence_module()
    store, pin = make_occurrence_store(tmp_path/'source.sqlite', 3)
    scopes = (o.GroupScope(1), o.OwnerScope('people', store.codec.encode(0)))
    certs = construct_occurrence_certificates(store, pin, scopes)
    return o, store, pin, certs


def read(o, store, pin, pair, **kwargs):
    return o.read_occurrence_page(store, pin, *pair, **kwargs)


def test_independent_framing_and_sql_tuple_order(tmp_path):
    o, store, pin, certs = setup_source(tmp_path)
    scope = o.OwnerScope('people', b'key\x00')
    domain = hashlib.sha256(frame(b'ate-occurrence-proof-domain/1', store.store_identity.encode(), b'1',
                                b'owner', b'people', b'key\x00')).digest()
    assert o.occurrence_domain(store.store_identity, 1, scope) == domain
    row = o.RawOccurrence('people', b'key\x00', b'path', 3)
    assert o.member_commitment(domain, row) == hashlib.sha256(frame(b'ate-occurrence-proof-member/1',
        domain, b'people', b'key\x00', b'path', b'\x00'*7+b'\x03')).digest()
    assert o.group_order_key('a', b'\x00', b'') == b'a\x00\x00\x00\xff\x00\x00\x00\x00'
    values = [('é', b'', b'\xff'), ('a', b'', b''), ('a', b'\x00', b''),
              ('a', b'\x00\x00', b''), ('a', b'\x00', b'\x00'), ('aa', b'', b'')]
    store.db.execute('CREATE TEMP TABLE order_vector(ns TEXT,k BLOB,p BLOB)')
    store.db.executemany('INSERT INTO order_vector VALUES(?,?,?)', values)
    sql = store.db.execute('SELECT ns,k,p FROM order_vector ORDER BY ns,k,p').fetchall()
    assert sorted(values, key=lambda x: o.group_order_key(*x)) == sql
    cert, expected = certs[0]
    from ate_sim.persistence_proof_order import root_commitment
    d = o.occurrence_domain(store.store_identity, 1, cert.scope)
    assert expected == hashlib.sha256(frame(b'ate-occurrence-certificate/1', d, (1).to_bytes(8,'big'),
        (6).to_bytes(8,'big'), root_commitment(d,cert.order))).digest()
    store.close()


def test_exact_owner_group_pages_and_no_owner_payloads(tmp_path):
    o, store, pin, certs = setup_source(tmp_path)
    sql = []; store.reset_diagnostics(); store.db.set_trace_callback(sql.append)
    rows = []; after = None
    while True:
        page = read(o, store, pin, certs[0], after=after, limit=3)
        rows.extend(page.rows)
        if page.next_after is None: break
        after = page.next_after
    expected = sorted([o.RawOccurrence('people', store.codec.encode(i), store.codec.encode((('field', field),)), 1)
        for i in range(4) for field in ('other','shared')], key=lambda r:(r.namespace,r.typed_key,r.path))
    assert rows == expected
    owner = read(o, store, pin, certs[1]).rows
    assert owner == tuple(r for r in expected if r.typed_key == store.codec.encode(0))
    assert store._payload_check_reads == 0 and store._payload_reads == 0
    store.db.set_trace_callback(None)
    assert not any('FROM '+table in s for s in sql for table in ('lazy_record_versions','records','segments','lazy_query_versions'))
    assert not store.db.in_transaction
    store.close()


def test_empty_owner_group_and_end_cursor_prove_absence(tmp_path):
    o, store, pin, certs = setup_source(tmp_path)
    empty = construct_occurrence_certificates(store,pin,(o.GroupScope(2),o.OwnerScope('people',store.codec.encode(999))))
    for pair in empty: assert read(o,store,pin,pair).rows == ()
    assert read(o,store,pin,certs[0],after=('zz',b'',b'')).rows == ()
    store.close()


def test_previous_pin_after_reassignment_and_delete(tmp_path):
    o, store, pin, certs = setup_source(tmp_path)
    old = store.capture_pin()
    oldrows = read(o,store,old,certs[0]).rows
    writer = store.commit(pin,commit_token='replace',version_changes=(),changes=(),new_segments=(),
        identity_changes=(IdentityOccurrenceChange('people',0,(('field','other'),),2),
                          IdentityOccurrenceChange('people',1,(('field','shared'),),delete=True)),
        next_incarnation_id=6,metadata=metadata(2)).pin
    new = construct_occurrence_certificates(store,writer,(o.GroupScope(1),o.OwnerScope('people',store.codec.encode(0))))
    assert read(o,store,old,certs[0]).rows == oldrows
    assert len(read(o,store,writer,new[0]).rows) == 6
    assert sorted(r.incarnation_id for r in read(o,store,writer,new[1]).rows) == [1,2]
    with pytest.raises((StoreConflictError,StoreIntegrityError)): read(o,store,writer,certs[0])
    store.release_pin(old)
    with pytest.raises(StoreConflictError): read(o,store,old,certs[0])
    store.close()


@pytest.mark.parametrize('field',['store','generation','codec','scope','allocator','expected'])
def test_wrong_context_and_allocator_rejected(tmp_path,field):
    o,store,pin,certs = setup_source(tmp_path); cert,expected = certs[0]
    if field == 'store': cert=replace(cert,store_identity='other')
    elif field == 'generation': cert=replace(cert,generation=0)
    elif field == 'codec': cert=replace(cert,codec_version=2)
    elif field == 'scope': cert=replace(cert,scope=o.GroupScope(2))
    elif field == 'allocator': cert=replace(cert,next_incarnation_id=7);expected=o.certificate_commitment(cert)
    else: expected=b'x'*32
    with pytest.raises((StoreConflictError,StoreIntegrityError)): read(o,store,pin,(cert,expected))
    store.close()


@pytest.mark.parametrize('fault',['missing','empty','surplus','coherent','overlap','other_group_overlap','checksum','lookahead','false_end'])
def test_corruption_and_hidden_overlap_rejected(tmp_path,fault):
    o,store,pin,certs = setup_source(tmp_path)
    rows=store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,valid_from,valid_to,row_checksum '
        'FROM lazy_identity_occurrence_versions WHERE incarnation_id=1 ORDER BY owner_namespace,owner_key,occurrence_path').fetchall()
    row=list(rows[4] if fault=='lookahead' else rows[-1] if fault=='false_end' else rows[1]); ns,key,path,inc,start,end,_=row
    if fault=='missing':store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_key=? AND occurrence_path=?',(key,path))
    elif fault=='empty':store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE incarnation_id=1')
    elif fault in ('checksum','lookahead','false_end'):
        store.db.execute("UPDATE lazy_identity_occurrence_versions SET row_checksum='bad' WHERE owner_key=? AND occurrence_path=?",(key,path))
    else:
        if fault=='surplus':row[2]=store.codec.encode((('field','between'),))
        elif fault=='coherent':row[3]=2;store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_key=? AND occurrence_path=?',(key,path))
        else:row[4]=0;row[3]=2 if fault=='other_group_overlap' else 1
        row[6]=_identity_occurrence_checksum(*row[:6])
        store.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',row)
    store.db.commit()
    kwargs=dict(limit=4) if fault=='lookahead' else dict(after=('zz',b'',b'')) if fault=='false_end' else {}
    with pytest.raises(StoreIntegrityError):read(o,store,pin,certs[0],**kwargs)
    store.close()


@pytest.mark.parametrize('column,value,budget',[('owner_key',b'x'*(2*1024*1024),True),
    ('occurrence_path',b'x'*(2*1024*1024),True),('owner_namespace','x'*(2*1024*1024),True),
    ('row_checksum','x'*64+'\x00'+'x'*(2*1024*1024),False)],ids=['key','path','namespace','nul-checksum'])
def test_large_metadata_guard_before_transfer(tmp_path,column,value,budget):
    o,store,pin,certs=setup_source(tmp_path)
    store.db.execute('UPDATE lazy_identity_occurrence_versions SET '+column+'=? WHERE owner_key=? AND occurrence_path=?',
        (value,store.codec.encode(0),store.codec.encode((('field','other'),))))
    store.db.commit();tracemalloc.start()
    try:
        with pytest.raises(o.OccurrenceProofBudgetError if budget else StoreIntegrityError):read(o,store,pin,certs[0])
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert peak<128*1024
    store.close()


def test_invalid_namespace_utf8_and_allocator_metadata_fail_closed(tmp_path):
    o,store,pin,certs=setup_source(tmp_path)
    with store.read_transaction():
        store.db.execute("UPDATE lazy_identity_occurrence_versions SET owner_namespace=CAST(X'FF' AS TEXT) WHERE incarnation_id=1")
        with pytest.raises(StoreIntegrityError):read(o,store,pin,certs[0])
        assert store.db.in_transaction
    store.db.execute("UPDATE lazy_identity_state SET row_checksum=?",('x'*(2*1024*1024),));store.db.commit()
    tracemalloc.start()
    try:
        with pytest.raises(StoreIntegrityError):read(o,store,pin,certs[0])
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert peak<128*1024
    store.close()


def test_indexes_are_explicit_transaction_owned_and_required(tmp_path):
    o,store,pin,certs=setup_source(tmp_path)
    with pytest.raises(StoreError):o.create_occurrence_indexes(store.db)
    store.db.execute('DROP INDEX ate_occurrence_group_current')
    with pytest.raises(StoreError):read(o,store,pin,certs[0])
    assert not store.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_occurrence_group_current'").fetchall()
    store.db.execute('BEGIN');o.create_occurrence_indexes(store.db);assert store.db.in_transaction;store.db.rollback()
    store.close()


def test_owned_nested_arbitrary_transactions_and_foreign_pin(tmp_path):
    o,store,pin,certs=setup_source(tmp_path)
    with store.read_transaction():
        with store.read_snapshot(pin):assert len(read(o,store,pin,certs[0]).rows)==8
        assert store.db.in_transaction
    store.db.execute('BEGIN')
    with pytest.raises(StoreError):read(o,store,pin,certs[0])
    assert store.db.in_transaction;store.db.rollback()
    other,foreign=make_occurrence_store(tmp_path/'foreign.sqlite')
    with pytest.raises(StoreConflictError):read(o,store,foreign,certs[0])
    store.close();other.close()


@pytest.mark.parametrize('limit,after',[(0,None),(129,None),(True,None),(1,('people','bad',b'')),(1,('people',b'',)),(1,('wrong',b'',b''))])
def test_invalid_limit_or_owner_cursor(tmp_path,limit,after):
    o,store,pin,certs=setup_source(tmp_path)
    with pytest.raises(StoreIntegrityError):read(o,store,pin,certs[1],limit=limit,after=after)
    store.close()


@pytest.mark.parametrize('definition',[
    'incarnation_id,owner_namespace,owner_key,occurrence_path) WHERE valid_to IS NOT NULL',
    'incarnation_id,owner_namespace COLLATE NOCASE,owner_key,occurrence_path) WHERE valid_to IS NULL',
    'incarnation_id,owner_namespace DESC,owner_key,occurrence_path) WHERE valid_to IS NULL'])
def test_wrong_reserved_index_definition_rejected_before_query(tmp_path,definition):
    o,store,pin,certs=setup_source(tmp_path)
    store.db.execute('DROP INDEX ate_occurrence_group_current')
    store.db.execute('CREATE INDEX ate_occurrence_group_current ON lazy_identity_occurrence_versions('+definition)
    with pytest.raises(StoreError):read(o,store,pin,certs[0])
    store.close()


def test_current_stream_detects_closed_overlap_in_another_group(tmp_path):
    o,store,pin,certs=setup_source(tmp_path)
    row=list(store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,valid_from,valid_to,row_checksum '
        'FROM lazy_identity_occurrence_versions WHERE incarnation_id=1 LIMIT 1').fetchone())
    row[3:6]=[2,0,2];row[6]=_identity_occurrence_checksum(*row[:6])
    store.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',row);store.db.commit()
    with pytest.raises(StoreIntegrityError):read(o,store,pin,certs[0])
    store.close()


def test_owner_value_commitment_rejects_coherent_incarnation_replacement(tmp_path):
    o,store,pin,certs=setup_source(tmp_path)
    row=list(store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,valid_from,valid_to,row_checksum '
        'FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? LIMIT 1',('people',store.codec.encode(0))).fetchone())
    row[3]=2;row[6]=_identity_occurrence_checksum(*row[:6])
    store.db.execute('UPDATE lazy_identity_occurrence_versions SET incarnation_id=?,row_checksum=? '
        'WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',(2,row[6],*row[:3]));store.db.commit()
    with pytest.raises(StoreIntegrityError):read(o,store,pin,certs[1])
    store.close()


@pytest.mark.parametrize('name',['lazy_identity_occurrence_interval','lazy_identity_state_interval'])
@pytest.mark.parametrize('cached',[True,False])
def test_required_interval_indexes_and_capability_cannot_take_legacy_fallback(tmp_path,name,cached):
    o,store,pin,certs=setup_source(tmp_path)
    if cached:
        store._interval_indexes.discard(name)
    else:
        store.db.execute('DROP INDEX '+name)
        store._interval_indexes.discard(name)
    with pytest.raises(StoreError):read(o,store,pin,certs[0])
    store.close()


@pytest.mark.parametrize('count',[1000,10000])
def test_old_empty_scope_rejects_newer_candidates_with_bounded_sql_work(tmp_path,count):
    o,store,pin,certs=setup_source(tmp_path)
    old=store.capture_pin()
    empty=construct_occurrence_certificates(store,old,(o.GroupScope(2),))[0]
    store.commit(pin,commit_token='newer',version_changes=(VersionChange('archive',i+10,{'v':i}) for i in range(count)),
        identity_changes=(IdentityOccurrenceChange('archive',i+10,(),2) for i in range(count)),
        next_incarnation_id=6,changes=(),new_segments=(),metadata=metadata(2))
    steps=0
    def progress():
        nonlocal steps
        steps+=1
        return 0
    store.db.set_progress_handler(progress,1)
    try:
        with pytest.raises(o.OccurrenceProofBudgetError):read(o,store,old,empty,limit=4)
    finally:store.db.set_progress_handler(None,0)
    assert steps<20000
    assert not store.db.in_transaction
    store.close()


def test_old_owner_with_newer_reassignment_explicitly_requires_other_selection_path(tmp_path):
    o,store,pin,certs=setup_source(tmp_path);old=store.capture_pin()
    store.commit(pin,commit_token='reassign-owner',version_changes=(),changes=(),new_segments=(),
        identity_changes=(IdentityOccurrenceChange('people',0,(('field','other'),),2),),
        next_incarnation_id=6,metadata=metadata(2))
    with pytest.raises(o.OccurrenceProofBudgetError):read(o,store,old,certs[1])
    store.close()
