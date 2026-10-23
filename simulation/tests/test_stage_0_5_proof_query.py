"""Physical pinned source rows must match complete accepted query proofs."""
import hashlib
import tracemalloc
from dataclasses import replace

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError, StoreConflictError, Membership
from ate_sim.persistence_lazy_store import VersionChange, _query_checksum
from simulation.tests.proof_query_fixtures import query_module,make_store,construct_certificate,metadata
from simulation.tests.test_stage_0_5_proof_order import frame


def test_scope_member_certificate_bindings_match_independent_frames(tmp_path):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');certificate,_=construct_certificate(store,pin)
    scope=certificate.scope
    domain=hashlib.sha256(frame(b'ate-query-proof-domain/1',store.store_identity.encode(),b'1',
        b'people',b'cohort',store.codec.encode('active'))).digest()
    assert q.query_domain(store.store_identity,1,scope)==domain
    assert q.member_commitment(domain,b'key\x00\xff',3)==hashlib.sha256(frame(
        b'ate-query-proof-member/1',domain,b'key\x00\xff',b'\x00'*7+b'\x03')).digest()
    from ate_sim.persistence_proof_order import root_commitment
    assert q.certificate_commitment(certificate)==hashlib.sha256(frame(b'ate-query-certificate/1',domain,
        b'\x00'*7+b'\x01',root_commitment(domain,certificate.order))).digest()
    assert domain!=q.query_domain(store.store_identity,1,replace(scope,index_value=b'\x00nan\xff'))
    store.close()


def test_exact_pagination_cursors_repeated_keys_and_zero_payload_work(tmp_path):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite',30);cert,expected=construct_certificate(store,pin)
    store.reset_diagnostics();sql=[];store.db.set_trace_callback(sql.append)
    try:
        actual=[];after=None
        while True:
            page=q.read_query_page(store,pin,cert,expected,after=after,limit=3)
            actual.extend(page.positions)
            if page.next_after is None:break
            after=page.next_after
    finally:store.db.set_trace_callback(None)
    assert actual==[(store.codec.encode(i),ordinal) for i in range(8) for ordinal in (2*i,2*i+1)]
    assert not any('FROM lazy_record_versions' in s or 'FROM records' in s or 'FROM segments' in s for s in sql)
    assert store._payload_check_reads==0 and store._payload_reads==0
    with store.read_transaction():
        assert len(q.read_query_page(store,pin,cert,expected,limit=8).positions)==8
    store.close()


def test_previous_pin_and_current_proofs_select_distinct_exact_sources(tmp_path):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');old_pin=store.capture_pin()
    old,old_expected=construct_certificate(store,old_pin)
    changed=store.commit(pin,commit_token='change',version_changes=[VersionChange('people',2,{'wealth':20},
        memberships=(Membership('cohort','active',40),))],changes=(),new_segments=(),metadata=metadata(2))
    current,current_expected=construct_certificate(store,changed.pin)
    previous=q.read_query_page(store,old_pin,old,old_expected).positions
    new=q.read_query_page(store,changed.pin,current,current_expected).positions
    assert (store.codec.encode(2),4) in previous and (store.codec.encode(2),5) in previous
    assert (store.codec.encode(2),40) in new and (store.codec.encode(2),4) not in new
    with pytest.raises((StoreConflictError,StoreIntegrityError)):
        q.read_query_page(store,changed.pin,old,old_expected)
    store.release_pin(old_pin)
    with pytest.raises(StoreConflictError):q.read_query_page(store,old_pin,old,old_expected)
    store.close()


@pytest.mark.parametrize('field',['store','generation','codec','scope','root','expected'])
def test_wrong_certificate_context_is_rejected(tmp_path,field):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin)
    if field=='store':cert=replace(cert,store_identity='foreign')
    elif field=='generation':cert=replace(cert,generation=0)
    elif field=='codec':cert=replace(cert,codec_version=2)
    elif field=='scope':cert=replace(cert,scope=replace(cert.scope,index_value=store.codec.encode('other')))
    elif field=='root':cert=replace(cert,order=replace(cert.order,last=b'forged'))
    else:expected=b'x'*32
    with pytest.raises((StoreConflictError,StoreIntegrityError)):q.read_query_page(store,pin,cert,expected)
    store.close()


@pytest.mark.parametrize('fault',['checksum','type','interval','missing','surplus','overlap','empty','predecessor','lookahead'])
def test_physical_metadata_corruption_omission_and_overlap_fail_closed(tmp_path,fault):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin)
    if fault=='checksum':store.db.execute("UPDATE lazy_query_versions SET row_checksum='bad' WHERE ordinal=2")
    elif fault=='type':store.db.execute("UPDATE lazy_query_versions SET record_key='text' WHERE ordinal=2")
    elif fault=='interval':store.db.execute('UPDATE lazy_query_versions SET valid_from=0 WHERE ordinal=2')
    elif fault=='missing':store.db.execute('DELETE FROM lazy_query_versions WHERE ordinal=2')
    elif fault=='empty':store.db.execute('DELETE FROM lazy_query_versions')
    elif fault=='predecessor':store.db.execute("UPDATE lazy_query_versions SET row_checksum='bad' WHERE ordinal=1")
    elif fault=='lookahead':store.db.execute("UPDATE lazy_query_versions SET row_checksum='bad' WHERE ordinal=4")
    else:
        row=store.db.execute('SELECT namespace,index_name,index_value,record_key,ordinal,valid_from,valid_to '
                             'FROM lazy_query_versions WHERE ordinal=2').fetchone()
        ns,name,val,key,ordinal,start,end=row
        if fault=='surplus':key=store.codec.encode(999);ordinal=3
        else:start=0
        checksum=_query_checksum(ns,name,val,key,ordinal,start,end)
        store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',(ns,name,val,key,ordinal,start,end,checksum))
    store.db.commit()
    kwargs=dict(limit=4) if fault=='lookahead' else dict(after=(1,store.codec.encode(0)),limit=4) if fault=='predecessor' else {}
    with pytest.raises(StoreIntegrityError):q.read_query_page(store,pin,cert,expected,**kwargs)
    store.close()


def test_real_empty_query_and_end_cursor_have_authenticated_absence(tmp_path):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin,'empty')
    assert q.read_query_page(store,pin,cert,expected).positions==()
    cert,expected=construct_certificate(store,pin)
    assert q.read_query_page(store,pin,cert,expected,after=(99,b'')).positions==()
    store.close()


@pytest.mark.parametrize('limit,after',[(0,None),(129,None),(True,None),(1.0,None),(1,('bad',b'')),(1,(0,'bad')),(1,[0,b''])])
def test_invalid_limits_and_raw_cursors_are_rejected(tmp_path,limit,after):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin)
    with pytest.raises(StoreIntegrityError):q.read_query_page(store,pin,cert,expected,limit=limit,after=after)
    store.close()


def test_foreign_pin_and_arbitrary_borrowed_transaction_are_rejected(tmp_path):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin)
    other,other_pin=make_store(tmp_path/'other.sqlite')
    with pytest.raises(StoreConflictError):q.read_query_page(store,other_pin,cert,expected)
    store.db.execute('BEGIN')
    with pytest.raises(StoreError):q.read_query_page(store,pin,cert,expected)
    store.db.rollback();other.close();store.close()


def test_metadata_does_not_admit_or_validate_owner_objects(tmp_path):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin)
    store.db.execute("UPDATE lazy_record_versions SET payload=X'00' WHERE namespace='people'");store.db.commit()
    store.reset_diagnostics()
    page=q.read_query_page(store,pin,cert,expected,limit=8)
    assert len(page.positions)==8 and all(type(key) is bytes for key,_ in page.positions)
    assert store._payload_check_reads==0
    with pytest.raises(StoreIntegrityError):store.query_memberships(pin,'people','cohort','active',limit=8)
    store.close()


@pytest.mark.parametrize('field',['key-text','checksum-text','key-blob'])
def test_oversized_physical_metadata_is_rejected_before_python_transfer(tmp_path,field):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite');cert,expected=construct_certificate(store,pin)
    huge='\x00'+'x'*(2*1024*1024)
    if field=='key-text':store.db.execute('UPDATE lazy_query_versions SET record_key=? WHERE ordinal=0',(huge,))
    elif field=='checksum-text':store.db.execute('UPDATE lazy_query_versions SET row_checksum=? WHERE ordinal=0',(huge,))
    else:store.db.execute('UPDATE lazy_query_versions SET record_key=? WHERE ordinal=0',(huge.encode(),))
    store.db.commit();tracemalloc.start()
    try:
        with pytest.raises(StoreError):q.read_query_page(store,pin,cert,expected)
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert peak<128*1024
    store.close()


@pytest.mark.parametrize('case', ['lookahead', 'predecessor', 'end-boundary', 'hidden-closed', 'previous-closed'])
def test_each_fetched_position_rejects_hidden_visible_intervals(tmp_path,case):
    q=query_module();store,pin=make_store(tmp_path/'source.sqlite')
    cert,expected=construct_certificate(store,pin)
    if case=='previous-closed':
        old_pin=store.capture_pin()
        store.commit(pin,commit_token='advance',version_changes=(),changes=(),new_segments=(),metadata=metadata(2))
        pin=old_pin
    ordinal={'lookahead':4,'predecessor':1,'end-boundary':15}.get(case,2)
    row=store.db.execute('SELECT namespace,index_name,index_value,record_key,ordinal FROM lazy_query_versions '
        'WHERE ordinal=?',(ordinal,)).fetchone()
    end=pin.captured_head+1 if case in ('hidden-closed','previous-closed') else None
    checksum=_query_checksum(*row,0,end)
    store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',(*row,0,end,checksum))
    store.db.commit()
    kwargs={'limit':4} if case=='lookahead' else {'after':(1,store.codec.encode(0)),'limit':4} if case=='predecessor' else {'after':(99,b'')} if case=='end-boundary' else {}
    with pytest.raises(StoreIntegrityError):q.read_query_page(store,pin,cert,expected,**kwargs)
    store.close()
