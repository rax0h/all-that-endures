import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory,read_collection_namespace,read_collection_namespaces
from simulation.tests.proof_publication_fixtures import make_publication_store,metadata,Authorities

def m():return importlib.import_module('ate_sim.persistence_proof_directory_publish')
def setup(tmp_path):
 s,p,a=make_publication_store(tmp_path/'d.sqlite',3);d=bootstrap_collection_directory(s,p);return s,p,a,d

def save(s,p,a,d,names=('people',),changes=(),token='next',**kw):
 return m().commit_directory(s,p,*d,*a.content,namespaces=names,scope_authority=a.scope,record_authority=a.record,commit_token=token,version_changes=changes,identity_changes=(),changes=(),new_segments=(),metadata=metadata(p.captured_head+1),**kw)

def next_a(r):return Authorities((r.content.certificate,r.content.commitment),(r.content.scope.record.certificate,r.content.scope.record.commitment),(r.content.scope.certificate,r.content.scope.commitment))

def test_successor_directory_is_complete_and_retained(tmp_path):
 s,p,a,d=setup(tmp_path);old=s.capture_pin()
 r=save(s,p,a,d,changes=(VersionChange('people',0,{'wealth':2},reinsertion=True),VersionChange('people',1,{})))
 assert [c.namespace for c,e in read_collection_namespaces(s,r.content.commit.pin,*r.directory).entries]==['archive','people']
 assert read_collection_namespace(s,old,*d,'people')[0].next_ordinal==1
 c=read_collection_namespace(s,r.content.commit.pin,*r.directory,'people')[0]
 assert (c.member_count,c.next_ordinal)==(2,3)
 assert read_collection_namespace(s,r.content.commit.pin,*r.directory,'archive')[0].member_count==3;s.close()

@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_atomic_failure_recovery(tmp_path,phase):
 s,p,a,d=setup(tmp_path);before=s.db.execute('SELECT count(*) FROM ate_directory_generations').fetchone()
 def fault(at):
  if at==phase:raise RuntimeError('fault')
 s._phase_hook=fault
 with pytest.raises(RuntimeError):save(s,p,a,d,changes=(VersionChange('people',1,{}),))
 s._phase_hook=lambda _:None
 r=m().resolve_directory(s,p,*d,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='next')
 assert r.content.commit.outcome==('committed' if phase=='after_commit' else 'not_committed')
 if phase!='after_commit':assert s.db.execute('SELECT count(*) FROM ate_directory_generations').fetchone()==before
 else:assert read_collection_namespace(s,r.content.commit.pin,*r.directory,'people')[0].member_count==2
 s.close()

def test_untouched_namespace_remains_usable_on_next_save(tmp_path):
 s,p,a,d=setup(tmp_path);r=save(s,p,a,d,changes=(VersionChange('people',1,{}),))
 r2=save(s,r.content.commit.pin,next_a(r),r.directory,names=('archive',),changes=(VersionChange('archive',0,delete=True),),token='third')
 assert read_collection_namespace(s,r2.content.commit.pin,*r2.directory,'archive')[0].member_count==2;s.close()

@pytest.mark.parametrize('changes',[(),(VersionChange('archive',99,delete=True),),(VersionChange('archive',99,{}),)])
def test_introduced_namespace_and_metadata_only(tmp_path,changes):
 s,p,a=make_publication_store(tmp_path/'new.sqlite');d=bootstrap_collection_directory(s,p)
 r=save(s,p,a,d,names=('archive',) if changes else (),changes=changes)
 child=read_collection_namespace(s,r.content.commit.pin,*r.directory,'archive')
 assert (child is not None)==bool(changes)
 if changes:assert child[0].member_count==(0 if changes[0].delete else 1)
 else:assert r.directory[0].root==d[0].root
 s.close()

def test_unlisted_changed_namespace_fails_without_partial_publication(tmp_path):
 s,p,a,d=setup(tmp_path)
 with pytest.raises(StoreError):save(s,p,a,d,changes=(VersionChange('archive',0,delete=True),))
 assert s.generation==1;s.close()

@pytest.mark.parametrize('fault',['expected','row','descriptor','shadow','view','duplicate','overflow','transaction','private'])
def test_invalid_authority_or_inputs_fail_closed(tmp_path,fault):
 s,p,a,d=setup(tmp_path);kw={}
 if fault=='expected':d=(d[0],b'x'*32)
 elif fault=='row':s.db.execute('UPDATE ate_directory_generations SET certificate=?',(b'[]',))
 elif fault=='descriptor':s.db.execute('DELETE FROM ate_collection_directory_bodies')
 elif fault=='shadow':s.db.execute('CREATE TEMP TABLE save_head AS SELECT * FROM main.save_head')
 elif fault=='view':
  s.db.execute('ALTER TABLE save_head RENAME TO saved_head');s.db.execute('CREATE VIEW save_head AS SELECT * FROM saved_head')
 elif fault=='duplicate':kw['names']=('people','people')
 elif fault=='overflow':kw['names']=tuple('n'+str(i) for i in range(129))
 elif fault=='private':kw['_scope_proof']=object()
 s.db.commit()
 if fault=='transaction':s.db.execute('BEGIN')
 with pytest.raises(StoreError):save(s,p,a,d,**kw)
 if s.db.in_transaction:s.db.rollback()
 s.close()

def test_noop_does_not_publish_directory(tmp_path):
 s,p,a,d=setup(tmp_path)
 r=m().commit_directory(s,p,*d,*a.content,namespaces=(),scope_authority=a.scope,record_authority=a.record,commit_token='noop',version_changes=(),identity_changes=(),changes=(),new_segments=(),metadata=metadata(1))
 assert r.directory==d and r.content.commit.outcome=='not_committed'
 assert s.db.execute('SELECT count(*) FROM ate_directory_generations').fetchone()[0]==1;s.close()

def test_recovery_uses_exact_receipt_and_reopen(tmp_path):
 from ate_sim.persistence_lazy_store import LazyRecordStore
 s,p,a,d=setup(tmp_path);path=s.path if hasattr(s,'path') else tmp_path/'d.sqlite'
 r=save(s,p,a,d,changes=(VersionChange('people',1,{}),));s.close()
 from ate_sim.incremental_store import TypedCodec
 s=LazyRecordStore.open(path,codec=TypedCodec(),expected_simulation_schema='8',expected_rules_id='content-publication-test')
 r2=m().resolve_directory(s,p,*d,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='next')
 assert r2.directory==r.directory
 with pytest.raises(StoreError):m().resolve_directory(s,p,*d,*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='wrong')
 s.close()

@pytest.mark.parametrize('new_namespace',[False,True])
def test_first_save_from_completely_empty_directory(tmp_path,new_namespace):
 from ate_sim.incremental_store import TypedCodec
 from ate_sim.persistence_lazy_store import LazyRecordStore
 from ate_sim.persistence_proof_record import bootstrap_record_proofs
 from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
 from ate_sim.persistence_proof_publication import bootstrap_content_proofs
 s=LazyRecordStore.create(tmp_path/'empty.sqlite',codec=TypedCodec(),simulation_schema='8',rules_id='empty')
 p=s.capture_pin();record=bootstrap_record_proofs(s,p);scope=bootstrap_scope_proofs(s,p);a=Authorities(bootstrap_content_proofs(s,p),record,scope);d=bootstrap_collection_directory(s,p)
 assert d[0].root.count==0
 r=save(s,p,a,d,names=('people',) if new_namespace else (),changes=(VersionChange('people',0,{}),) if new_namespace else ())
 page=read_collection_namespaces(s,r.content.commit.pin,*r.directory)
 assert [c.namespace for c,e in page.entries]==(['people'] if new_namespace else [])
 s.close()
