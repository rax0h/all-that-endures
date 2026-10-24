"""Complete physical scope authority; raw pages still require World admission."""
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from ate_sim.persistence_proof_occurrence import OwnerScope,GroupScope
from ate_sim.persistence_proof_query import QueryScope
from ate_sim.persistence_proof_occurrence_seek import read_occurrence_seek_page
from ate_sim.persistence_proof_query_seek import read_query_seek_page
from simulation.tests.proof_scope_fixtures import scope_module,make_scope_store,scopes,read_scope,commit_scope,metadata


def page(store,pin,pair,scope):
    cert,expected=read_scope(store,pin,pair,scope)
    return (read_query_seek_page if type(scope) is QueryScope else read_occurrence_seek_page)(store,pin,cert,expected)


def test_complete_constructor_and_existing_raw_pages(tmp_path):
    store,pin,pair=make_scope_store(tmp_path/'complete.sqlite',20)
    assert tuple(r.count for r in pair[0].roots)==(21,21,21,21)
    store.reset_diagnostics()
    for scope in scopes(store):
        p=page(store,pin,pair,scope)
        assert len(p.positions if type(scope) is QueryScope else p.rows)==1
    assert store.diagnostics().payload_reads==0 and store.diagnostics().payload_check_reads==0
    store.close()


@pytest.mark.parametrize('kind',['owner','group','query'])
def test_authenticated_empty_scopes(tmp_path,kind):
    store,pin,pair=make_scope_store(tmp_path/'empty.sqlite')
    scope={'owner':OwnerScope('people',store.codec.encode(77)),'group':GroupScope(2),
           'query':QueryScope('people','cohort',store.codec.encode('absent'))}[kind]
    p=page(store,pin,pair,scope)
    assert (p.positions if kind=='query' else p.rows)==() and p.next_after is None
    store.close()


@pytest.mark.parametrize('fault',['descriptor','missing-descriptor','node','row','expected','released','transaction','hook','budget'])
def test_corruption_context_and_bounds(tmp_path,fault):
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'bad.sqlite');kwargs={}
    if fault=='descriptor':store.db.execute('UPDATE ate_scope_descriptors SET root_count=root_count+1')
    elif fault=='missing-descriptor':store.db.execute('DELETE FROM ate_scope_descriptors')
    elif fault=='node':store.db.execute('DELETE FROM ate_proof_nodes')
    elif fault=='row':store.db.execute('UPDATE ate_scope_generations SET next_incarnation_id=next_incarnation_id+1')
    elif fault=='expected':pair=(pair[0],b'x'*32)
    elif fault=='released':store.release_pin(pin)
    elif fault=='hook':store.codec.decode=lambda _:pytest.fail('caller codec hook invoked')
    elif fault=='budget':kwargs['max_metadata_bytes']=1
    store.db.commit()
    if fault=='transaction':store.db.execute('BEGIN')
    with pytest.raises(StoreError):read_scope(store,pin,pair,scopes(store)[0],**kwargs)
    if store.db.in_transaction:store.db.rollback()
    store.close()


def test_constructor_current_pin_owned_transaction_and_no_repair(tmp_path):
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'owned.sqlite')
    with pytest.raises(StoreError):s.bootstrap_scope_proofs(store,pin)
    store.db.execute('BEGIN')
    with pytest.raises(StoreError):s.bootstrap_scope_proofs(store,pin)
    store.db.rollback();old=store.capture_pin()
    new=store.commit(pin,commit_token='advance',version_changes=(),changes=(),new_segments=(),metadata=metadata(2)).pin
    with pytest.raises(StoreConflictError):s.bootstrap_scope_proofs(store,old)
    store.close()


@pytest.mark.parametrize('fault',['oversize','nul-text','wrong-affinity'])
def test_constructor_guards_scope_metadata_before_full_audit(tmp_path,fault):
    s=scope_module();store,pin,_=make_scope_store(tmp_path/'guard.sqlite',bootstrap=False)
    if fault=='oversize':store.db.execute('UPDATE lazy_query_versions SET index_value=zeroblob(4097)')
    elif fault=='nul-text':store.db.execute('UPDATE lazy_query_versions SET index_name=?',('a\0'+'x'*1000000,))
    else:store.db.execute("UPDATE lazy_query_versions SET index_value='text'")
    store.db.commit();store.verify_all=lambda:pytest.fail('audit ran before rejecting metadata')
    with pytest.raises(StoreError):s.bootstrap_scope_proofs(store,pin)
    assert store.db.execute("SELECT count(*) FROM sqlite_schema WHERE name='ate_scope_generations'").fetchone()[0]==0
    store.close()


def result_pair(result):return result.certificate,result.commitment


def test_actual_atomic_membership_move_old_new_and_stable_unrelated_scope(tmp_path):
    store,pin,pair=make_scope_store(tmp_path/'commit.sqlite',20);old=store.capture_pin()
    unrelated=OwnerScope('archive',store.codec.encode(10));before=read_scope(store,pin,pair,unrelated)[0].root
    result=commit_scope(store,pin,pair);new=result_pair(result);writer=result.commit.pin
    assert result.commit.outcome=='committed' and result.commit.generation==2
    assert page(store,old,pair,scopes(store)[1]).rows[0].incarnation_id==1
    assert page(store,writer,new,scopes(store)[1]).rows==()
    assert page(store,writer,new,GroupScope(2)).rows[0].incarnation_id==2
    assert page(store,old,pair,scopes(store)[2]).positions==((store.codec.encode(0),0),)
    assert page(store,writer,new,scopes(store)[2]).positions==()
    assert page(store,writer,new,QueryScope('people','cohort',store.codec.encode('new'))).positions==((store.codec.encode(0),7),)
    assert read_scope(store,writer,new,unrelated)[0].root==before
    store.close()


def test_allocator_metadata_and_noop_share_all_scope_roots(tmp_path):
    store,pin,pair=make_scope_store(tmp_path/'shared.sqlite',20)
    result=commit_scope(store,pin,pair,version_changes=(),identity_changes=(),next_incarnation_id=100)
    assert result.certificate.roots==pair[0].roots and result.certificate.next_incarnation_id==100
    count=store.db.execute('SELECT count(*) FROM ate_scope_descriptors').fetchone()[0]
    noop=commit_scope(store,result.commit.pin,result_pair(result),token='noop',version_changes=(),identity_changes=(),metadata=metadata(2))
    assert noop.commit.outcome=='not_committed' and result_pair(noop)==result_pair(result)
    assert store.db.execute('SELECT count(*) FROM ate_scope_descriptors').fetchone()[0]==count
    store.close()


def test_last_members_removed_then_reinsert(tmp_path):
    from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
    from ate_sim.incremental_store import Membership
    store,pin,pair=make_scope_store(tmp_path/'delete.sqlite')
    result=commit_scope(store,pin,pair,version_changes=(VersionChange('people',0,delete=True),),identity_changes=(IdentityOccurrenceChange('people',0,(),delete=True),))
    assert tuple(r.count for r in result.certificate.roots)==(0,0,0,0)
    result=commit_scope(store,result.commit.pin,result_pair(result),token='insert',version_changes=(VersionChange('people',0,{'wealth':3},memberships=(Membership('cohort','active',0),)),),identity_changes=(IdentityOccurrenceChange('people',0,(),1),))
    assert tuple(r.count for r in result.certificate.roots)==(1,1,1,1)
    assert page(store,result.commit.pin,result_pair(result),scopes(store)[2]).positions==((store.codec.encode(0),0),)
    store.close()


@pytest.mark.parametrize('phase',['during_version_writes','during_identity_writes','before_head','before_commit'])
def test_transaction_fault_retains_old_authority(tmp_path,phase):
    store,pin,pair=make_scope_store(tmp_path/'fault.sqlite');before=store.db.execute('SELECT count(*) FROM ate_scope_descriptors').fetchone()[0]
    def hook(p):
        if p==phase:raise RuntimeError('injected')
    store._phase_hook=hook
    with pytest.raises(RuntimeError,match='injected'):commit_scope(store,pin,pair)
    store._phase_hook=lambda _:None
    assert store.generation==1 and store.db.execute('SELECT count(*) FROM ate_scope_generations').fetchone()[0]==1
    assert store.db.execute('SELECT count(*) FROM ate_scope_descriptors').fetchone()[0]==before
    assert page(store,pin,pair,scopes(store)[1]).rows[0].incarnation_id==1
    store.close()


@pytest.mark.parametrize('phase',['before_transaction','before_commit','after_commit'])
def test_sql_callback_cannot_escape_publication(tmp_path,phase):
    store,pin,pair=make_scope_store(tmp_path/'escape.sqlite')
    def hook(p):
        if p==phase:store.db.execute('COMMIT')
    store._phase_hook=hook
    with pytest.raises(StoreError):commit_scope(store,pin,pair)
    store._phase_hook=lambda _:None
    if phase=='after_commit':
        recovered=scope_module().resolve_scope_commit(store,pin,*pair,commit_token='next')
        assert recovered.commit.outcome=='committed' and recovered.certificate.generation==2
    else:assert store.generation==1
    store.close()


def test_lost_ack_exact_recovery_no_replay(tmp_path):
    store,pin,pair=make_scope_store(tmp_path/'ack.sqlite')
    def hook(p):
        if p=='after_commit':raise RuntimeError('lost ack')
    store._phase_hook=hook
    with pytest.raises(RuntimeError):commit_scope(store,pin,pair)
    store._phase_hook=lambda _:None
    with pytest.raises(StoreError):scope_module().resolve_scope_commit(store,pin,*pair,commit_token='wrong')
    result=scope_module().resolve_scope_commit(store,pin,*pair,commit_token='next')
    assert result.commit.outcome=='committed'
    assert page(store,result.commit.pin,result_pair(result),GroupScope(2)).rows[0].incarnation_id==2
    again=scope_module().resolve_scope_commit(store,pin,*pair,commit_token='next')
    assert result_pair(again)==result_pair(result)
    store.close()


def test_default_writer_gap_fails_closed_and_old_pin_still_exact(tmp_path):
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'gap.sqlite');old=store.capture_pin()
    writer=store.commit(pin,commit_token='default',version_changes=(),changes=(),new_segments=(),metadata=metadata(2)).pin
    assert page(store,old,pair,scopes(store)[1]).rows[0].incarnation_id==1
    cert=replace(pair[0],generation=2)
    with pytest.raises(StoreError):read_scope(store,writer,(cert,s.certificate_commitment(cert)),scopes(store)[0])
    repaired=s.bootstrap_scope_proofs(store,writer)
    assert repaired[0].roots==pair[0].roots
    store.close()


def test_combined_ordinary_root_and_scope_roots_share_one_commit(tmp_path):
    from ate_sim.incremental_store import RecordChange
    from ate_sim.persistence_proof_record import bootstrap_record_proofs,read_record_proof_bytes
    store,pin,pair=make_scope_store(tmp_path/'combined.sqlite');records=bootstrap_record_proofs(store,pin);old=store.capture_pin()
    result=commit_scope(store,pin,pair,record_authority=records,changes=(RecordChange('ordinary',1,{'ordinary':2}),))
    assert result.record.commit==result.commit and result.record.certificate.generation==result.certificate.generation==2
    assert read_record_proof_bytes(store,old,*records,'ordinary',store.codec.encode(1),expected_record_schema=1).payload==store.codec.encode({'ordinary':1})
    assert read_record_proof_bytes(store,result.commit.pin,result.record.certificate,result.record.commitment,'ordinary',store.codec.encode(1),expected_record_schema=1).payload==store.codec.encode({'ordinary':2})
    store.close()


def test_spilled_changed_inputs_publish_same_scopes(tmp_path):
    store,pin,pair=make_scope_store(tmp_path/'spill.sqlite')
    result=commit_scope(store,pin,pair,preparation_budget=(1,1))
    assert page(store,result.commit.pin,result_pair(result),GroupScope(2)).rows[0].incarnation_id==2
    store.close()


def test_missing_actual_parent_placement_cannot_preserve_ghost_root(tmp_path):
    from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
    store,pin,pair=make_scope_store(tmp_path/'missing-old-placement.sqlite')
    store.db.execute("DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace='people'");store.db.commit()
    with pytest.raises(StoreIntegrityError):commit_scope(store,pin,pair,version_changes=(),identity_changes=(IdentityOccurrenceChange('people',0,(),delete=True),))
    assert store.generation==1
    store.close()


def test_coherently_removed_parent_query_still_rejects_ghost_root(tmp_path):
    from ate_sim.persistence_lazy_store import VersionChange,_version_checksum
    store,pin,pair=make_scope_store(tmp_path/'missing-old-query.sqlite');key=store.codec.encode(0)
    row=store.db.execute("SELECT record_schema,codec_version,valid_from,valid_to,payload FROM lazy_record_versions WHERE namespace='people'").fetchone()
    schema,codec,start,end,payload=row;members=store.codec.encode(())
    store.db.execute("UPDATE lazy_record_versions SET memberships=?,row_checksum=? WHERE namespace='people'",(members,_version_checksum('people',key,schema,codec,start,end,members,payload)))
    store.db.execute("DELETE FROM lazy_query_versions WHERE namespace='people'");store.db.commit()
    store.verify_all()  # Coherent physical rows are insufficient accepted-root authority.
    with pytest.raises(StoreIntegrityError):commit_scope(store,pin,pair,version_changes=(VersionChange('people',0,{'wealth':2}),),identity_changes=())
    assert store.generation==1
    store.close()


@pytest.mark.parametrize('field,value',[('generation',True),('codec_version',True),('next_incarnation_id',True),('roots',()),('store_identity','bad\0identity')])
def test_strict_directory_certificate_fields(tmp_path,field,value):
    store,pin,pair=make_scope_store(tmp_path/'types.sqlite')
    with pytest.raises(StoreError):scope_module().certificate_commitment(replace(pair[0],**{field:value}))
    store.close()


def test_scoped_descriptors_bind_exact_scope_and_context(tmp_path):
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'binding.sqlite',2)
    owner,group,query=scopes(store)
    a=read_scope(store,pin,pair,owner)[0];b=read_scope(store,pin,pair,OwnerScope('archive',store.codec.encode(0)))[0]
    assert a.root!=b.root  # Same path, different physical owner/group content.
    store.db.execute('UPDATE ate_scope_descriptors SET root_digest=?,root_count=? WHERE root_digest=?',(b.root.digest,b.root.count,a.root.digest));store.db.commit()
    with pytest.raises(StoreIntegrityError):read_scope(store,pin,pair,owner)
    store.close()


@pytest.mark.parametrize('kind',['query','placement'])
def test_actual_written_metadata_is_checked_outside_fault_hooks(tmp_path,kind,monkeypatch):
    from ate_sim.persistence_lazy_store import LazyRecordStore,_query_checksum,_identity_occurrence_checksum
    store,pin,pair=make_scope_store(tmp_path/'written.sqlite')
    method='_write_lazy_changes' if kind=='query' else '_write_identity_changes';original=getattr(LazyRecordStore,method)
    def corrupt(self,*args,**kwargs):
        original(self,*args,**kwargs)
        if kind=='query':
            key=self.codec.encode(0);value=self.codec.encode('other')
            self.db.execute("UPDATE lazy_query_versions SET index_value=?,row_checksum=? WHERE namespace='people' AND valid_to IS NULL",(value,_query_checksum('people','cohort',value,key,7,2,None)))
        else:
            key=self.codec.encode(0);path=self.codec.encode(())
            self.db.execute("UPDATE lazy_identity_occurrence_versions SET incarnation_id=1,row_checksum=? WHERE owner_namespace='people' AND valid_to IS NULL",(_identity_occurrence_checksum('people',key,path,1,2,None),))
    monkeypatch.setattr(LazyRecordStore,method,corrupt)
    with pytest.raises(StoreIntegrityError):commit_scope(store,pin,pair)
    assert store.generation==1 and store.db.execute('SELECT count(*) FROM ate_scope_generations').fetchone()[0]==1
    store.close()


def test_external_write_invalidates_parent_epoch(tmp_path):
    import sqlite3
    store,pin,pair=make_scope_store(tmp_path/'external.sqlite')
    def external(phase):
        if phase=='before_transaction':
            from ate_sim.incremental_store import _record_checksum
            payload=store.codec.encode({'ordinary':999});key=store.codec.encode(1)
            with sqlite3.connect(store.path) as other:other.execute('UPDATE records SET payload=?,payload_checksum=? WHERE namespace=? AND typed_key=?',(payload,_record_checksum('ordinary',key,1,store.codec.version,1,payload),'ordinary',key))
    store._phase_hook=external
    with pytest.raises(StoreConflictError):commit_scope(store,pin,pair)
    assert store.generation==1
    store.close()


@pytest.mark.parametrize('fault',['missing-root','stale-parent'])
def test_noncommitted_recovery_binds_actual_supplied_parent(tmp_path,fault):
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'aborted.sqlite')
    if fault=='stale-parent':
        advanced=commit_scope(store,pin,pair);current_pair=result_pair(advanced);current=advanced.commit.pin
    else:current_pair,current=pair,pin
    def hook(p):
        if p=='before_transaction':raise RuntimeError('aborted')
    store._phase_hook=hook
    with pytest.raises(RuntimeError):commit_scope(store,current,current_pair,token='aborted')
    store._phase_hook=lambda _:None
    if fault=='missing-root':store.db.execute('DELETE FROM ate_scope_generations');store.db.commit()
    with pytest.raises(StoreError):s.resolve_scope_commit(store,pin,*pair,commit_token='aborted')
    store.close()


def test_multiple_membership_and_identity_changes_match_full_reconstruction(tmp_path):
    from ate_sim.incremental_store import Membership
    from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'rebuild.sqlite',10)
    result=commit_scope(store,pin,pair,version_changes=(VersionChange('people',0,{'wealth':4},memberships=tuple(Membership('cohort','active',i) for i in range(12))),
        VersionChange('archive',0,delete=True),VersionChange('people',3,{'new':True},memberships=(Membership('cohort','active',3),))),
        identity_changes=(IdentityOccurrenceChange('people',0,(),25),IdentityOccurrenceChange('archive',0,(),delete=True),IdentityOccurrenceChange('people',3,(('field','new'),),25)),next_incarnation_id=26)
    writer=result.commit.pin;new=result_pair(result)
    p=page(store,writer,new,scopes(store)[2]);assert len(p.positions)==13 and p.positions==tuple(sorted(p.positions,key=lambda x:(x[1],x[0])))
    assert len(page(store,writer,new,GroupScope(25)).rows)==2
    store.db.execute('DELETE FROM ate_scope_generations WHERE generation=2');store.db.commit()
    rebuilt=s.bootstrap_scope_proofs(store,writer)
    assert rebuilt==new
    store.close()


def test_combined_lost_ack_recovers_both_component_roots(tmp_path):
    from ate_sim.incremental_store import RecordChange
    from ate_sim.persistence_proof_record import bootstrap_record_proofs
    s=scope_module();store,pin,pair=make_scope_store(tmp_path/'combined-ack.sqlite');records=bootstrap_record_proofs(store,pin)
    def hook(p):
        if p=='after_commit':raise RuntimeError('lost acknowledgement')
    store._phase_hook=hook
    with pytest.raises(RuntimeError):commit_scope(store,pin,pair,record_authority=records,changes=(RecordChange('ordinary',1,{'ordinary':2}),))
    store._phase_hook=lambda _:None
    result=s.resolve_scope_commit(store,pin,*pair,commit_token='next',record_authority=records)
    assert result.record.commit==result.commit and result.certificate.generation==result.record.certificate.generation==2
    store.close()
