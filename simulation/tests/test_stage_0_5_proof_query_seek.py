"""Root-selected query intervals, including retained scopes under newer load."""
from dataclasses import replace
import hashlib
import pytest
from ate_sim.incremental_store import StoreError,StoreIntegrityError,StoreConflictError,Membership
from ate_sim.persistence_lazy_store import VersionChange,_query_checksum
from ate_sim.persistence_proof_query import QueryScope
from simulation.tests.proof_query_fixtures import make_store,metadata
from simulation.tests.proof_query_seek_fixtures import construct_query_seek,query_seek_module
from simulation.tests.test_stage_0_5_proof_order import frame


def setup(tmp_path):
    q=query_seek_module();store,pin=make_store(tmp_path/'query.sqlite')
    pair=construct_query_seek(store,pin,QueryScope('people','cohort',store.codec.encode('active')))
    return q,store,pin,pair


def test_pages_literal_order_framing_no_payload(tmp_path):
    q,store,pin,pair=setup(tmp_path);cert,expected=pair
    from ate_sim.persistence_proof_query import query_domain
    domain=hashlib.sha256(frame(b'ate-query-seek-domain/1',query_domain(store.store_identity,1,cert.scope))).digest()
    assert q.seek_domain(store.store_identity,1,cert.scope)==domain
    assert expected==hashlib.sha256(frame(b'ate-query-seek-certificate/1',domain,(1).to_bytes(8,'big'),cert.root.digest,(16).to_bytes(8,'big'))).digest()
    sql=[];store.db.set_trace_callback(sql.append);store.reset_diagnostics()
    positions=[];after=None
    while True:
        page=q.read_query_seek_page(store,pin,*pair,after=after,limit=3);positions.extend(page.positions)
        if page.next_after is None:break
        after=page.next_after
    assert positions==[(store.codec.encode(i//2),i) for i in range(16)]
    assert q.read_query_seek_page(store,pin,*pair,after=(3,b'not-present'),limit=1).positions==((store.codec.encode(2),4),)
    assert store.diagnostics().payload_reads==0
    assert not any('then payload end' in s.lower() for s in sql)
    store.close()


@pytest.mark.parametrize('count',[1000,10000])
def test_old_nonempty_and_empty_roots_ignore_real_newer_rows(tmp_path,count):
    q,store,pin,pair=setup(tmp_path);old=store.capture_pin()
    empty=construct_query_seek(store,pin,QueryScope('people','cohort',store.codec.encode('empty')))
    def changes():
        yield VersionChange('people',1,{},memberships=(Membership('cohort','empty',0),))
        for i in range(count):yield VersionChange('people',1000+i,{},memberships=(Membership('cohort','active',i),Membership('cohort','empty',i)))
    writer=store.commit(pin,commit_token='frontier',version_changes=changes(),changes=(),new_segments=(),metadata=metadata(2)).pin
    assert store.db.execute("SELECT count(*) FROM lazy_query_versions WHERE index_value=? AND valid_from=2",(pair[0].scope.index_value,)).fetchone()[0]==count
    steps=0
    def progress():
        nonlocal steps
        steps+=1;return 0
    store.db.set_progress_handler(progress,1)
    assert q.read_query_seek_page(store,old,*pair,limit=4).positions==((store.codec.encode(0),0),(store.codec.encode(0),1),(store.codec.encode(1),2),(store.codec.encode(1),3))
    assert q.read_query_seek_page(store,old,*empty).positions==()
    store.db.set_progress_handler(None,0);assert steps<20000
    current=construct_query_seek(store,writer,pair[0].scope);assert current[0].root.count==count+14
    store.close()


@pytest.mark.parametrize('fault',['missing','checksum','overlap','end-text','node'])
def test_selected_corruption(tmp_path,fault):
    q,store,pin,pair=setup(tmp_path);key=store.codec.encode(0)
    where='namespace=? AND record_key=? AND ordinal=0';args=('people',key)
    if fault=='node':store.db.execute('DELETE FROM ate_ordered_seek_nodes WHERE digest=?',(pair[0].root.digest,))
    elif fault=='missing':store.db.execute('DELETE FROM lazy_query_versions WHERE '+where,args)
    elif fault=='checksum':store.db.execute("UPDATE lazy_query_versions SET row_checksum=? WHERE "+where,('0'*64,*args))
    elif fault=='end-text':store.db.execute("UPDATE lazy_query_versions SET valid_to='bad' WHERE "+where,args)
    else:
        row=list(store.db.execute('SELECT namespace,index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum FROM lazy_query_versions WHERE '+where,args).fetchone())
        row[5:7]=[0,2];row[7]=_query_checksum(*row[:7]);store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',row)
    store.db.commit()
    with pytest.raises(StoreIntegrityError):q.read_query_seek_page(store,pin,*pair)
    store.close()


@pytest.mark.parametrize('fault',['expected','generation','scope','codec','released','cached-index','physical-index','transaction','hook','extended-codec','budget'])
def test_authority_capability_and_budget(tmp_path,fault):
    q,store,pin,pair=setup(tmp_path);cert,expected=pair;kwargs={}
    if fault=='expected':expected=b'x'*32
    elif fault=='generation':cert=replace(cert,generation=0);expected=q.certificate_commitment(cert)
    elif fault=='scope':cert=replace(cert,scope=QueryScope('people','cohort',b'other'))
    elif fault=='codec':cert=replace(cert,codec_version=2);expected=q.certificate_commitment(cert)
    elif fault=='released':store.release_pin(pin)
    elif fault=='cached-index':store._interval_indexes.discard('lazy_query_interval')
    elif fault=='physical-index':store.db.execute('DROP INDEX lazy_query_interval');store.db.commit()
    elif fault=='transaction':store.db.execute('BEGIN')
    elif fault=='hook':store.codec.decode=lambda _:None
    elif fault=='extended-codec':store.codec.register_record('test',__import__('dataclasses').make_dataclass('Arbitrary',[]))
    else:kwargs['max_metadata_bytes']=1
    with pytest.raises((StoreError,StoreIntegrityError,StoreConflictError)):q.read_query_seek_page(store,pin,cert,expected,**kwargs)
    if store.db.in_transaction:store.db.rollback()
    store.close()


def test_owned_nested_snapshots_and_surplus_not_admitted(tmp_path):
    q,store,pin,pair=setup(tmp_path)
    with store.read_transaction():
        with store.read_snapshot(pin):assert len(q.read_query_seek_page(store,pin,*pair).positions)==16
    key=store.codec.encode(999);scope=pair[0].scope
    row=(scope.namespace,scope.index_name,scope.index_value,key,0,1,None)
    store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',(*row,_query_checksum(*row)));store.db.commit()
    assert len(q.read_query_seek_page(store,pin,*pair).positions)==16
    assert store.db.execute('SELECT count(*) FROM lazy_query_versions').fetchone()[0]==17
    store.close()
