"""Retained ordinary content is checked bytes, not mutable World admission."""
from dataclasses import replace
import hashlib
import pytest
from ate_sim.incremental_store import RecordChange,StoreError,StoreIntegrityError,StoreConflictError
from ate_sim.persistence_proof_nodes import Root
from simulation.tests.proof_record_fixtures import record_module,make_record_store,read_record,metadata
from simulation.tests.test_stage_0_5_proof_order import frame


def test_framing_current_absence_and_no_world_decode(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'record.sqlite',1000);cert,expected=pair
    domain=hashlib.sha256(frame(b'ate-record-proof-domain/1',store.store_identity.encode(),b'1')).digest()
    assert r.record_domain(store.store_identity,1)==domain
    assert expected==hashlib.sha256(frame(b'ate-record-certificate/1',domain,(1).to_bytes(8,'big'),cert.root.digest,(1001).to_bytes(8,'big'))).digest()
    store.reset_diagnostics();sql=[];store.db.set_trace_callback(sql.append)
    got=read_record(store,pin,pair)
    assert got.payload==store.codec.encode({'wealth':1}) and got.record_schema==1 and got.last_changed_generation==1
    assert read_record(store,pin,pair,key=999) is None
    assert store.diagnostics().payload_reads==0
    assert not any('from records' in s.lower() for s in sql)
    store.close()


def test_old_body_survives_default_overwrite_but_missing_new_root_rejects(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'old.sqlite');old=store.capture_pin()
    writer=store.commit(pin,commit_token='overwrite',version_changes=(),changes=(RecordChange('people',0,{'wealth':2}),),new_segments=(),metadata=metadata(2)).pin
    assert store.read_record('people',0,expected_record_schema=1)=={'wealth':2}
    assert read_record(store,old,pair).payload==store.codec.encode({'wealth':1})
    cert=replace(pair[0],generation=2)
    with pytest.raises(StoreIntegrityError):read_record(store,writer,(cert,r.certificate_commitment(cert)))
    store.close()


@pytest.mark.parametrize('fault',['body','checksum','missing-body','node','root-row','root-schema','body-text','body-large','expected','generation','released','hook','transaction','budget','metadata-budget'])
def test_corruption_authority_and_bounds(tmp_path,fault):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'bad.sqlite');kwargs={}
    where="namespace='people'"
    if fault=='body':store.db.execute("UPDATE ate_retained_records SET payload=x'00' WHERE "+where)
    elif fault=='checksum':store.db.execute('UPDATE ate_retained_records SET payload_checksum=? WHERE '+where,('0'*64,))
    elif fault=='missing-body':store.db.execute('DELETE FROM ate_retained_records WHERE '+where)
    elif fault=='node':store.db.execute('DELETE FROM ate_proof_nodes')
    elif fault=='root-row':store.db.execute('UPDATE ate_record_roots SET root_count=root_count+1')
    elif fault=='root-schema':
        store.db.execute('ALTER TABLE ate_record_roots RENAME TO old_roots');store.db.execute('CREATE TABLE ate_record_roots AS SELECT * FROM old_roots')
    elif fault=='body-text':store.db.execute("UPDATE ate_retained_records SET payload='bad' WHERE "+where)
    elif fault=='body-large':store.db.execute('UPDATE ate_retained_records SET payload=zeroblob(1048577) WHERE '+where)
    elif fault=='expected':pair=(pair[0],b'x'*32)
    elif fault=='generation':
        cert=replace(pair[0],generation=0);pair=(cert,r.certificate_commitment(cert))
    elif fault=='released':store.release_pin(pin)
    elif fault=='hook':store.codec.decode=lambda _:pytest.fail('caller hook invoked')
    elif fault=='budget':kwargs['max_bytes']=1
    elif fault=='metadata-budget':kwargs['max_metadata_bytes']=1
    store.db.commit()
    if fault=='transaction':store.db.execute('BEGIN')
    with pytest.raises(StoreError):read_record(store,pin,pair,**kwargs)
    if store.db.in_transaction:store.db.rollback()
    store.close()


def test_bootstrap_rejects_corrupt_source_and_arbitrary_transaction(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'import.sqlite')
    store.db.execute('BEGIN')
    with pytest.raises(StoreError):r.bootstrap_record_proofs(store,pin)
    store.db.rollback();store.db.execute("UPDATE records SET payload=x'00' WHERE namespace='people'");store.db.commit()
    with pytest.raises(StoreIntegrityError):r.bootstrap_record_proofs(store,pin)
    store.close()


def test_bootstrap_body_budget_precedes_full_audit(tmp_path):
    r=record_module();store,pin,_=make_record_store(tmp_path/'budget.sqlite')
    store.verify_all=lambda:pytest.fail('full audit ran before rejecting unsupported body budget')
    with pytest.raises(r.RecordProofBudgetError):r.bootstrap_record_proofs(store,pin,max_body_bytes=1)
    store.close()


def commit_proof(store,pin,pair,*,value=2,token='next',**kwargs):
    return record_module().commit_record_proof(store,pin,*pair,commit_token=token,
        changes=(RecordChange('people',0,{'wealth':value}),),version_changes=(),new_segments=(),metadata=metadata(pin.captured_head+1),**kwargs)


def test_atomic_actual_commit_old_new_and_delete_reinsert(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'commit.sqlite',1000);old=store.capture_pin()
    result=commit_proof(store,pin,pair);new_pair=(result.certificate,result.commitment)
    assert result.commit.outcome=='committed' and result.commit.generation==2
    assert read_record(store,old,pair).payload==store.codec.encode({'wealth':1})
    assert read_record(store,result.commit.pin,new_pair).payload==store.codec.encode({'wealth':2})
    store.release_pin(old)
    deleted=r.commit_record_proof(store,result.commit.pin,*new_pair,commit_token='delete',changes=(RecordChange('people',0,delete=True),),
        version_changes=(),new_segments=(),metadata=metadata(3))
    assert read_record(store,deleted.commit.pin,(deleted.certificate,deleted.commitment)) is None
    reinsert=commit_proof(store,deleted.commit.pin,(deleted.certificate,deleted.commitment),value=4,token='reinsert')
    assert read_record(store,reinsert.commit.pin,(reinsert.certificate,reinsert.commitment)).payload==store.codec.encode({'wealth':4})
    store.close()


@pytest.mark.parametrize('phase',['during_ordinary_writes','before_head','before_commit'])
def test_rollback_keeps_data_head_roots_and_bodies_together(tmp_path,phase):
    store,pin,pair=make_record_store(tmp_path/'rollback.sqlite');before=store.db.execute('SELECT count(*) FROM ate_retained_records').fetchone()[0]
    def fail(at):
        if at==phase:raise OSError('injected rollback')
    store._phase_hook=fail
    with pytest.raises(OSError):commit_proof(store,pin,pair)
    store._phase_hook=lambda _:None
    assert store.generation==1 and read_record(store,pin,pair).payload==store.codec.encode({'wealth':1})
    assert store.db.execute('SELECT count(*) FROM ate_record_roots').fetchone()[0]==1
    assert store.db.execute('SELECT count(*) FROM ate_retained_records').fetchone()[0]==before
    store.close()


def test_failed_proof_write_rolls_back_already_written_data(tmp_path,monkeypatch):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'proof-write.sqlite');real=r._retain_body
    def fail(*args,**kwargs):
        real(*args,**kwargs);raise OSError('proof body write failure')
    monkeypatch.setattr(r,'_retain_body',fail)
    with pytest.raises(OSError):commit_proof(store,pin,pair)
    assert store.generation==1 and store.read_record('people',0,expected_record_schema=1)=={'wealth':1}
    assert store.db.execute('SELECT count(*) FROM ate_retained_records').fetchone()[0]==1
    store.close()


@pytest.mark.parametrize('phase',['before_head','before_commit'])
def test_coherent_late_changed_row_tamper_rejected(tmp_path,phase):
    from ate_sim.incremental_store import _record_checksum
    store,pin,pair=make_record_store(tmp_path/'late.sqlite')
    def tamper(at):
        if at==phase:
            payload=store.codec.encode({'wealth':999});key=store.codec.encode(0)
            checksum=_record_checksum('people',key,1,store.codec.version,2,payload)
            store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',(payload,checksum,'people',key))
    store._phase_hook=tamper
    with pytest.raises(StoreIntegrityError):commit_proof(store,pin,pair)
    store._phase_hook=lambda _:None
    assert store.generation==1 and store.read_record('people',0,expected_record_schema=1)=={'wealth':1}
    store.close()


def test_lost_ack_exact_token_resolves_root_without_replay(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'ack.sqlite')
    store._phase_hook=lambda at:(_ for _ in ()).throw(OSError('lost ack')) if at=='after_commit' else None
    with pytest.raises(OSError):commit_proof(store,pin,pair,token='lost')
    store._phase_hook=lambda _:None
    with pytest.raises(StoreConflictError):r.resolve_record_commit(store,pin,*pair,commit_token='wrong')
    recovered=r.resolve_record_commit(store,pin,*pair,commit_token='lost')
    assert recovered.commit.generation==2 and read_record(store,recovered.commit.pin,(recovered.certificate,recovered.commitment)).payload==store.codec.encode({'wealth':2})
    again=r.resolve_record_commit(store,pin,*pair,commit_token='lost')
    assert again.certificate==recovered.certificate and store.generation==2
    assert store.db.execute('SELECT count(*) FROM ate_retained_records').fetchone()[0]==2
    store.close()


def test_noop_and_spilled_prepared_rows(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'noop.sqlite')
    noop=r.commit_record_proof(store,pin,*pair,commit_token='noop',changes=(),version_changes=(),new_segments=(),metadata=metadata())
    assert noop.commit.outcome=='not_committed' and (noop.certificate,noop.commitment)==pair
    result=commit_proof(store,pin,pair,preparation_budget=(1,1024))
    assert read_record(store,result.commit.pin,(result.certificate,result.commitment)).payload==store.codec.encode({'wealth':2})
    store.close()


def test_conflicting_retained_body_rejects_without_transferring_large_blob(tmp_path):
    import tracemalloc
    r=record_module();store,pin,pair=make_record_store(tmp_path/'duplicate.sqlite')
    source=store.db.execute("SELECT namespace,typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation FROM records WHERE namespace='people'").fetchone()
    store.db.execute('UPDATE ate_retained_records SET payload=zeroblob(2097152)');store.db.commit()
    tracemalloc.start()
    try:
        with pytest.raises(StoreIntegrityError):r._retain_body(store,*source)
        peak=tracemalloc.get_traced_memory()[1]
    finally:tracemalloc.stop()
    assert peak<131072
    store.db.rollback();store.close()


def test_actual_written_row_binding_is_independent_of_fault_hook_guard(tmp_path,monkeypatch):
    from ate_sim.incremental_store import _record_checksum
    store,pin,pair=make_record_store(tmp_path/'actual.sqlite');real=store._write_ordinary_changes
    def wrong_write(*args,**kwargs):
        result=real(*args,**kwargs);payload=store.codec.encode({'wealth':999});key=store.codec.encode(0)
        store.db.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',
            (payload,_record_checksum('people',key,1,store.codec.version,2,payload),'people',key))
        return result
    monkeypatch.setattr(store,'_write_ordinary_changes',wrong_write)
    with pytest.raises(StoreIntegrityError):commit_proof(store,pin,pair)
    assert store.generation==1
    store.close()


def test_external_write_invalidates_parent_operation_epoch(tmp_path):
    import sqlite3
    from ate_sim.incremental_store import _record_checksum
    store,pin,pair=make_record_store(tmp_path/'external.sqlite')
    def external(at):
        if at=='before_transaction':
            payload=store.codec.encode({'wealth':999});key=store.codec.encode(0)
            with sqlite3.connect(store.path) as other:
                other.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',
                    (payload,_record_checksum('people',key,1,store.codec.version,1,payload),'people',key))
    store._phase_hook=external
    with pytest.raises(StoreConflictError):commit_proof(store,pin,pair)
    assert store.generation==1 and store.db.execute('SELECT count(*) FROM ate_record_roots').fetchone()[0]==1
    store.close()


@pytest.mark.parametrize('phase',['during_ordinary_writes','before_head','before_commit'])
@pytest.mark.parametrize('metadata_only',[False,True])
@pytest.mark.parametrize('control',['commit','rollback-rebegin','executescript'])
def test_hook_cannot_escape_original_writer_transaction(tmp_path,phase,metadata_only,control):
    store,pin,pair=make_record_store(tmp_path/'escape.sqlite')
    def escape(at):
        if at==phase:
            if control=='commit':store.db.commit()
            elif control=='rollback-rebegin':store.db.rollback();store.db.execute('BEGIN IMMEDIATE')
            else:store.db.executescript('SELECT 1;')
    store._phase_hook=escape
    with pytest.raises(StoreError):
        if metadata_only:
            record_module().commit_record_proof(store,pin,*pair,commit_token='metadata',changes=(),version_changes=(),new_segments=(),metadata=metadata(2))
        else:commit_proof(store,pin,pair)
    store._phase_hook=lambda _:None
    assert store.generation==1 and store.read_record('people',0,expected_record_schema=1)=={'wealth':1}
    assert store.db.execute('SELECT count(*) FROM ate_record_roots').fetchone()[0]==1
    store.close()


@pytest.mark.parametrize('phase',['before_transaction','after_commit'])
def test_outside_transaction_hook_cannot_write_and_commit(tmp_path,phase):
    store,pin,pair=make_record_store(tmp_path/'outside.sqlite')
    def escape(at):
        if at==phase:
            store.db.execute("UPDATE records SET payload=x'00' WHERE namespace='people'");store.db.commit()
    store._phase_hook=escape
    with pytest.raises(StoreError):commit_proof(store,pin,pair)
    store._phase_hook=lambda _:None
    expected=1 if phase=='before_transaction' else 2
    assert store.generation==expected
    assert store.read_record('people',0,expected_record_schema=1)=={'wealth':expected}
    assert store.db.execute('SELECT count(*) FROM ate_record_roots').fetchone()[0]==expected
    store.close()


@pytest.mark.parametrize('already_resolved',[False,True])
def test_not_committed_recovery_rejects_stale_parent(tmp_path,already_resolved):
    r=record_module();store,pin,old_pair=make_record_store(tmp_path/'stale-recovery.sqlite')
    first=commit_proof(store,pin,old_pair);current=(first.certificate,first.commitment)
    store._phase_hook=lambda at:(_ for _ in ()).throw(OSError('aborted latest attempt')) if at=='before_transaction' else None
    with pytest.raises(OSError):commit_proof(store,first.commit.pin,current,token='abort')
    store._phase_hook=lambda _:None
    if already_resolved:store.resolve_commit(first.commit.pin,'abort')
    with pytest.raises(StoreConflictError):r.resolve_record_commit(store,pin,*old_pair,commit_token='abort')
    actual=r.resolve_record_commit(store,first.commit.pin,*current,commit_token='abort')
    assert actual.commit.outcome=='not_committed' and actual.certificate.generation==actual.commit.generation==2
    store.close()


def test_bootstrap_rejects_future_revision_before_publishing(tmp_path):
    from ate_sim.incremental_store import _record_checksum
    r=record_module();store,pin,_=make_record_store(tmp_path/'future.sqlite',bootstrap=False)
    key=store.codec.encode(0);payload=store.codec.encode({'wealth':1})
    store.db.execute('UPDATE records SET last_changed_generation=2,payload_checksum=?',(_record_checksum('people',key,1,1,2,payload),));store.db.commit()
    with pytest.raises(StoreIntegrityError):r.bootstrap_record_proofs(store,pin)
    assert store.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_record_roots'").fetchone() is None
    store.close()


@pytest.mark.parametrize('column',['payload_checksum','namespace','typed_key','record_schema'])
def test_bootstrap_bounds_malformed_metadata_before_transfer(tmp_path,column):
    import tracemalloc
    r=record_module();store,pin,_=make_record_store(tmp_path/'metadata.sqlite',bootstrap=False)
    # Embedded NUL defeats length(TEXT); metadata probes must use byte lengths.
    large=('0'*64+'\x00'+'x'*2097152) if column!='typed_key' else b'x'*2097152
    store.db.execute('UPDATE records SET '+column+'=?',(large,));store.db.commit()
    tracemalloc.start()
    try:
        with pytest.raises(StoreError):r.bootstrap_record_proofs(store,pin)
        peak=tracemalloc.get_traced_memory()[1]
    finally:tracemalloc.stop()
    assert peak<131072
    store.close()


def test_existing_authorizer_survives_readonly_hook_and_rejects_removal(tmp_path):
    import sqlite3
    store,pin,pair=make_record_store(tmp_path/'authorizer.sqlite')
    store.db.execute('CREATE TABLE policy_secret(value)');store.db.execute('INSERT INTO policy_secret VALUES(1)');store.db.commit()
    def policy(action,first,second,database,source):
        return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_READ and first=='policy_secret' else sqlite3.SQLITE_OK
    store.db.set_authorizer(policy)
    store._phase_hook=lambda _:store.db.execute('SELECT 1').fetchone()
    result=commit_proof(store,pin,pair)
    assert result.commit.outcome=='committed'
    with pytest.raises(sqlite3.DatabaseError):store.db.execute('SELECT value FROM policy_secret').fetchone()
    store._phase_hook=lambda _:store.db.set_authorizer(None)
    with pytest.raises(StoreError):commit_proof(store,result.commit.pin,(result.certificate,result.commitment),token='remove-policy')
    with pytest.raises(sqlite3.DatabaseError):store.db.execute('SELECT value FROM policy_secret').fetchone()
    store.close()


def test_not_committed_recovery_requires_actual_parent_root(tmp_path):
    r=record_module();store,pin,pair=make_record_store(tmp_path/'missing-recovery-root.sqlite')
    store._phase_hook=lambda at:(_ for _ in ()).throw(OSError('aborted')) if at=='before_transaction' else None
    with pytest.raises(OSError):commit_proof(store,pin,pair,token='abort')
    store._phase_hook=lambda _:None;store.db.execute('DELETE FROM ate_record_roots');store.db.commit()
    with pytest.raises(StoreIntegrityError):r.resolve_record_commit(store,pin,*pair,commit_token='abort')
    store.close()
