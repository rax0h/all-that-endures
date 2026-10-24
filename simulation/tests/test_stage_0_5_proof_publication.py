"""Production content roots must describe actual retained source bytes."""
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from simulation.tests.proof_publication_fixtures import publication_module,make_publication_store,read_version,read_event,metadata,commit_publication,next_authorities


def test_physical_store_empty_segment_has_an_exact_content_commitment(tmp_path):
    from ate_sim.persistence_proof_content import segment_commitment
    store,pin,_=make_publication_store(tmp_path/'empty-preimage.sqlite',bootstrap=False,empty_event=True)
    payload,checksum,codec,count,first,last,generation=store.db.execute('SELECT payload,payload_checksum,codec_version,element_count,first_id,last_id,created_generation FROM segments').fetchone()
    assert count==0 and store.verify_all()['segments']==1
    value=segment_commitment('events',0,created_generation=generation,codec_version=codec,element_count=count,first_id=first,last_id=last,payload=payload)
    assert len(value)==32
    store.close()


@pytest.mark.parametrize('empty_event',[False,True])
def test_real_constructor_exact_version_events_and_absence(tmp_path,empty_event):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'content.sqlite',7,empty_event=empty_event)
    assert a.content[0].versions.count==8 and a.content[0].events.count==8
    store.reset_diagnostics();version=read_version(store,pin,a);event=read_event(store,pin,a)
    assert version.payload==store.codec.encode({'wealth':1}) and version.valid_from==1
    assert event.payload==store.codec.encode([] if empty_event else ['first']) and event.element_count==(0 if empty_event else 1)
    assert event.created_generation==1
    assert read_event(store,pin,a,1000000) is None
    assert p.read_version_content_bytes(store,pin,*a.content,'people',store.codec.encode(999),expected_record_schema=1) is None
    assert store.diagnostics().payload_reads==0
    store.close()


@pytest.mark.parametrize('fault',['version-body','event-body','event-checksum','event-large','event-text','root-row','root-schema','nodes','expected','released','transaction','codec-hook','body-budget','metadata-budget'])
def test_selected_content_corruption_context_and_budgets(tmp_path,fault):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'bad.sqlite');kwargs={}
    if fault=='version-body':store.db.execute("UPDATE lazy_record_versions SET payload=x'00' WHERE namespace='people'")
    elif fault=='event-body':store.db.execute("UPDATE segments SET payload=x'00'")
    elif fault=='event-checksum':store.db.execute("UPDATE segments SET payload_checksum=?",('0'*64,))
    elif fault=='event-large':store.db.execute('UPDATE segments SET payload=zeroblob(1048577)')
    elif fault=='event-text':store.db.execute("UPDATE segments SET payload='bad'")
    elif fault=='root-row':store.db.execute("UPDATE ate_content_generations SET roots=zeroblob(80)")
    elif fault=='root-schema':
        store.db.execute('ALTER TABLE ate_content_generations RENAME TO old_content');store.db.execute('CREATE TABLE ate_content_generations AS SELECT * FROM old_content')
    elif fault=='nodes':store.db.execute('DELETE FROM ate_proof_nodes')
    elif fault=='expected':a=a._replace(content=(a.content[0],b'x'*32))
    elif fault=='released':store.release_pin(pin)
    elif fault=='codec-hook':store.codec.decode=lambda _:pytest.fail('caller hook invoked')
    elif fault=='body-budget':kwargs['max_bytes']=1
    elif fault=='metadata-budget':kwargs['max_metadata_bytes']=1
    store.db.commit()
    if fault=='transaction':store.db.execute('BEGIN')
    with pytest.raises(StoreError):(read_version if fault=='version-body' else read_event)(store,pin,a,**kwargs)
    if store.db.in_transaction:store.db.rollback()
    store.close()


def test_constructor_requires_current_owned_snapshot_and_cannot_repair(tmp_path):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'owned.sqlite');old=store.capture_pin()
    with pytest.raises(StoreError):p.bootstrap_content_proofs(store,pin)
    store.db.execute('BEGIN')
    with pytest.raises(StoreError):p.bootstrap_content_proofs(store,pin)
    store.db.rollback()
    store.commit(pin,commit_token='default',version_changes=(),changes=(),new_segments=(),metadata=metadata(2))
    with pytest.raises(StoreConflictError):p.bootstrap_content_proofs(store,old)
    store.close()


@pytest.mark.parametrize('fault',['version-large','version-checksum','version-key','event-large','event-id','event-checksum'])
def test_constructor_guards_before_full_audit(tmp_path,fault):
    p=publication_module();store,pin,_=make_publication_store(tmp_path/'guard.sqlite',bootstrap=False)
    if fault=='version-large':store.db.execute('UPDATE lazy_record_versions SET payload=zeroblob(67108865)')
    elif fault=='version-checksum':store.db.execute('UPDATE lazy_record_versions SET row_checksum=?',('a\0'+'x'*1000000,))
    elif fault=='version-key':store.db.execute('UPDATE lazy_record_versions SET typed_key=zeroblob(1048577)')
    elif fault=='event-large':store.db.execute('UPDATE segments SET payload=zeroblob(67108865)')
    elif fault=='event-id':store.db.execute('UPDATE segments SET first_id=zeroblob(1048577)')
    else:store.db.execute('UPDATE segments SET payload_checksum=?',('a\0'+'x'*1000000,))
    store.db.commit();store.verify_all=lambda:pytest.fail('audit before byte/type guard')
    with pytest.raises(StoreError):p.bootstrap_content_proofs(store,pin)
    store.close()


def test_unified_actual_save_and_retained_all_component_roots(tmp_path):
    from ate_sim.persistence_proof_record import read_record_proof_bytes
    from ate_sim.persistence_proof_scope import read_scope_certificate
    from ate_sim.persistence_proof_occurrence import GroupScope
    from ate_sim.persistence_proof_occurrence_seek import read_occurrence_seek_page
    store,pin,a=make_publication_store(tmp_path/'commit.sqlite',7);old=store.capture_pin()
    result=commit_publication(store,pin,a);new=next_authorities(result);writer=result.commit.pin
    assert result.commit.outcome=='committed' and result.commit==result.scope.commit==result.scope.record.commit
    assert result.certificate.generation==new.record[0].generation==new.scope[0].generation==2
    assert read_version(store,old,a).payload==store.codec.encode({'wealth':1})
    assert read_version(store,writer,new).payload==store.codec.encode({'wealth':2})
    assert read_event(store,old,a,1000001) is None
    assert read_event(store,writer,new,1000001).payload==store.codec.encode(['second'])
    assert read_record_proof_bytes(store,old,*a.record,'ordinary',store.codec.encode(0),expected_record_schema=1).payload==store.codec.encode({'value':1})
    assert read_record_proof_bytes(store,writer,*new.record,'ordinary',store.codec.encode(0),expected_record_schema=1).payload==store.codec.encode({'value':2})
    cert,expected=read_scope_certificate(store,writer,*new.scope,GroupScope(2))
    assert read_occurrence_seek_page(store,writer,cert,expected).rows[0].incarnation_id==2
    store.close()


def test_noop_and_metadata_only_share_content_roots(tmp_path):
    store,pin,a=make_publication_store(tmp_path/'shared.sqlite')
    kwargs=dict(version_changes=(),identity_changes=(),changes=(),new_segments=())
    noop=commit_publication(store,pin,a,metadata=metadata(1),**kwargs)
    assert noop.commit.outcome=='not_committed' and next_authorities(noop)==a
    result=commit_publication(store,pin,a,token='metadata',**kwargs)
    assert result.certificate.versions==a.content[0].versions and result.certificate.events==a.content[0].events
    assert result.scope.certificate.roots==a.scope[0].roots and result.scope.record.certificate.root==a.record[0].root
    store.close()


def test_delete_and_reinsert_keeps_retained_exact_bytes(tmp_path):
    from ate_sim.persistence_lazy_store import VersionChange
    store,pin,a=make_publication_store(tmp_path/'delete.sqlite');old=store.capture_pin()
    deleted=commit_publication(store,pin,a,version_changes=(VersionChange('people',0,delete=True),),identity_changes=(),changes=(),new_segments=())
    assert read_version(store,deleted.commit.pin,next_authorities(deleted)) is None
    assert read_version(store,old,a).payload==store.codec.encode({'wealth':1})
    store.release_pin(old)
    reinserted=commit_publication(store,deleted.commit.pin,next_authorities(deleted),token='insert',version_changes=(VersionChange('people',0,{'wealth':3}),),identity_changes=(),changes=(),new_segments=())
    assert read_version(store,reinserted.commit.pin,next_authorities(reinserted)).payload==store.codec.encode({'wealth':3})
    store.close()


@pytest.mark.parametrize('phase',['during_version_writes','during_segment_writes','before_head','before_commit'])
def test_unified_rollback_preserves_all_roots_and_data(tmp_path,phase):
    store,pin,a=make_publication_store(tmp_path/'rollback.sqlite')
    def fault(p):
        if p==phase:raise RuntimeError('injected rollback')
    store._phase_hook=fault
    with pytest.raises(RuntimeError):commit_publication(store,pin,a)
    store._phase_hook=lambda _:None
    for table in ('ate_record_roots','ate_scope_generations','ate_content_generations'):assert store.db.execute('SELECT count(*) FROM '+table).fetchone()[0]==1
    assert store.generation==1 and read_event(store,pin,a,1000001) is None
    assert read_version(store,pin,a).payload==store.codec.encode({'wealth':1})
    store.close()


def test_last_content_root_fault_rolls_back_already_staged_components(tmp_path,monkeypatch):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'last-root.sqlite')
    def fail(*args,**kwargs):raise RuntimeError('last root fault')
    monkeypatch.setattr(p,'_write_root',fail)
    with pytest.raises(RuntimeError):commit_publication(store,pin,a)
    for table in ('ate_record_roots','ate_scope_generations','ate_content_generations'):assert store.db.execute('SELECT count(*) FROM '+table).fetchone()[0]==1
    assert store.generation==1
    store.close()


def test_actual_parent_content_rejects_coherent_payload_tamper(tmp_path):
    from ate_sim.incremental_store import _framed_sha
    from ate_sim.persistence_lazy_store import _version_checksum
    store,pin,a=make_publication_store(tmp_path/'parent.sqlite');key=store.codec.encode(0);payload=store.codec.encode({'wealth':999})
    members=store.db.execute("SELECT memberships FROM lazy_record_versions WHERE namespace='people'").fetchone()[0]
    store.db.execute("UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace='people'",(payload,_framed_sha(b'lazy-payload-v1',payload),_version_checksum('people',key,1,store.codec.version,1,None,members,payload)))
    store.db.commit();store.verify_all()
    with pytest.raises(StoreIntegrityError):commit_publication(store,pin,a)
    assert store.generation==1
    store.close()


@pytest.mark.parametrize('kind',['version','event'])
def test_actual_successor_bytes_checked_outside_phase_hooks(tmp_path,kind,monkeypatch):
    from ate_sim.persistence_lazy_store import LazyRecordStore,_version_checksum
    from ate_sim.incremental_store import _framed_sha,_segment_checksum
    store,pin,a=make_publication_store(tmp_path/'written.sqlite');name='_write_lazy_changes' if kind=='version' else '_write_segments';original=getattr(LazyRecordStore,name)
    def corrupt(self,*args,**kwargs):
        result=original(self,*args,**kwargs);payload=self.codec.encode({'wrong':True})
        if kind=='version':
            key=self.codec.encode(0);members=self.db.execute("SELECT memberships FROM lazy_record_versions WHERE namespace='people' AND valid_to IS NULL").fetchone()[0]
            self.db.execute("UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace='people' AND valid_to IS NULL",(payload,_framed_sha(b'lazy-payload-v1',payload),_version_checksum('people',key,1,self.codec.version,2,None,members,payload)))
        else:
            first=last=self.codec.encode(1000001)
            self.db.execute('UPDATE segments SET payload=?,payload_checksum=? WHERE ordinal=1000001',(payload,_segment_checksum('events',1000001,first,last,1,self.codec.version,2,payload)))
        return result
    monkeypatch.setattr(LazyRecordStore,name,corrupt)
    with pytest.raises(StoreIntegrityError):commit_publication(store,pin,a)
    assert store.generation==1
    store.close()


def test_lost_ack_recovers_exact_unified_roots_without_replay(tmp_path):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'ack.sqlite')
    def fault(phase):
        if phase=='after_commit':raise RuntimeError('lost acknowledgement')
    store._phase_hook=fault
    with pytest.raises(RuntimeError):commit_publication(store,pin,a)
    store._phase_hook=lambda _:None
    with pytest.raises(StoreError):p.resolve_content_commit(store,pin,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='wrong')
    result=p.resolve_content_commit(store,pin,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='next')
    again=p.resolve_content_commit(store,pin,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='next')
    assert next_authorities(again)==next_authorities(result) and result.commit.generation==2
    assert read_event(store,result.commit.pin,next_authorities(result),1000001).payload==store.codec.encode(['second'])
    store.close()


def test_spilled_preparation_and_default_writer_gap(tmp_path):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'spill.sqlite')
    result=commit_publication(store,pin,a,preparation_budget=(1,1));new=next_authorities(result)
    assert read_version(store,result.commit.pin,new).payload==store.codec.encode({'wealth':2})
    writer=store.commit(result.commit.pin,commit_token='default',version_changes=(),changes=(),new_segments=(),metadata=metadata(3)).pin
    cert=replace(new.content[0],generation=3);missing=new._replace(content=(cert,p.certificate_commitment(cert)))
    with pytest.raises(StoreIntegrityError):read_event(store,writer,missing)
    store.close()


@pytest.mark.parametrize('phase',['before_transaction','before_commit','after_commit'])
def test_unified_sql_callbacks_are_read_only(tmp_path,phase):
    store,pin,a=make_publication_store(tmp_path/'hook.sqlite')
    def fault(p):
        if p==phase:store.db.execute('COMMIT')
    store._phase_hook=fault
    with pytest.raises(StoreError):commit_publication(store,pin,a)
    assert store.generation==(2 if phase=='after_commit' else 1)
    store.close()


def test_empty_event_append_publishes_exact_opaque_ids_and_body(tmp_path):
    from ate_sim.incremental_store import NewSegment
    store,pin,a=make_publication_store(tmp_path/'empty-append.sqlite')
    result=commit_publication(store,pin,a,new_segments=(NewSegment('events',1,[],element_count=0,first_id=None,last_id=None),))
    raw=read_event(store,result.commit.pin,next_authorities(result),1)
    assert raw.payload==store.codec.encode([]) and raw.first_id==raw.last_id==store.codec.encode(None) and raw.element_count==0
    store.close()


@pytest.mark.parametrize('fault',['stale-parent','missing-content-root'])
def test_noncommitted_recovery_matches_actual_parent(tmp_path,fault):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'aborted.sqlite')
    if fault=='stale-parent':
        advanced=commit_publication(store,pin,a);current=advanced.commit.pin;current_authorities=next_authorities(advanced)
    else:current,current_authorities=pin,a
    def abort(phase):
        if phase=='before_transaction':raise RuntimeError('aborted')
    store._phase_hook=abort
    with pytest.raises(RuntimeError):commit_publication(store,current,current_authorities,token='aborted')
    store._phase_hook=lambda _:None
    if fault=='missing-content-root':store.db.execute('DELETE FROM ate_content_generations');store.db.commit()
    with pytest.raises(StoreError):p.resolve_content_commit(store,pin,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='aborted')
    store.close()


def test_external_write_invalidates_unified_parent_operation(tmp_path):
    import sqlite3
    from ate_sim.incremental_store import _record_checksum
    store,pin,a=make_publication_store(tmp_path/'epoch.sqlite')
    def external(phase):
        if phase=='before_transaction':
            key=store.codec.encode(0);payload=store.codec.encode({'value':999})
            with sqlite3.connect(store.path) as other:other.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',(payload,_record_checksum('ordinary',key,1,store.codec.version,1,payload),'ordinary',key))
    store._phase_hook=external
    with pytest.raises(StoreConflictError):commit_publication(store,pin,a)
    assert store.generation==1
    store.close()


@pytest.mark.parametrize('temporary',[False,True])
def test_trigger_on_last_content_root_cannot_escape_actual_checks(tmp_path,temporary):
    store,pin,a=make_publication_store(tmp_path/'trigger.sqlite')
    store.db.execute('CREATE '+('TEMP ' if temporary else '')+"TRIGGER corrupt_content AFTER INSERT ON ate_content_generations BEGIN DELETE FROM segments WHERE ordinal=1000001; END")
    store.db.commit()
    with pytest.raises(StoreError):commit_publication(store,pin,a)
    assert store.generation==1
    store.close()


def test_stale_pin_conflict_returns_no_successor_authority(tmp_path):
    store,pin,a=make_publication_store(tmp_path/'stale.sqlite');old=store.capture_pin()
    commit_publication(store,pin,a)
    conflict=commit_publication(store,old,a,token='stale')
    assert conflict.commit.outcome=='conflict' and conflict.certificate is None and conflict.commitment is None
    store.close()


@pytest.mark.parametrize('field,value',[('generation',True),('codec_version',True),('store_identity','bad\0identity')])
def test_content_certificate_rejects_type_aliases(tmp_path,field,value):
    p=publication_module();store,pin,a=make_publication_store(tmp_path/'strict.sqlite')
    with pytest.raises(StoreError):p.certificate_commitment(replace(a.content[0],**{field:value}))
    store.close()
