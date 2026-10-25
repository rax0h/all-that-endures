import importlib
import pytest
from ate_sim.incremental_store import StoreError,RecordChange,NewSegment
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
from simulation.tests.proof_publication_fixtures import make_publication_store,metadata

def m():return importlib.import_module('ate_sim.persistence_proof_inventory')
def setup(tmp_path):
 s,p,a=make_publication_store(tmp_path/'i.sqlite',3);d=bootstrap_collection_directory(s,p);i=m().bootstrap_inventory(s,p);return s,p,a,d,i

def save(s,p,a,d,i,**kw):
 args=dict(namespaces=('people',),commit_token='next',scope_authority=a.scope,record_authority=a.record,version_changes=(),identity_changes=(),changes=(),new_segments=(),metadata=metadata(p.captured_head+1));args.update(kw)
 return m().commit_inventory(s,p,*i,d,a.content,**args)

def test_complete_raw_inventory_and_empty_declarations(tmp_path):
 s,p,a,d,i=setup(tmp_path);s.reset_diagnostics()
 page=m().read_inventory_namespaces(s,p,*i,limit=2)
 assert page.entries==(('archive',3,0),('events',0,4)) and page.next_after==b'events'
 assert m().read_inventory_namespaces(s,p,*i,after=page.next_after).entries==(('ordinary',1,0),('people',1,0))
 assert m().read_inventory_namespace(s,p,*i,'absent') is None
 assert s._payload_reads==s._payload_check_reads==0;s.close()

def test_atomic_mixed_counts_and_retained_head(tmp_path):
 s,p,a,d,i=setup(tmp_path);old=s.capture_pin()
 r=save(s,p,a,d,i,version_changes=(VersionChange('people',1,{}),),changes=(RecordChange('ordinary',1,{}),),new_segments=(NewSegment('events',4,[4],element_count=1,first_id=4,last_id=4),))
 assert r.content.commit.outcome=='committed'
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,'people')==('people',2,0)
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,'ordinary')==('ordinary',2,0)
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,'events')==('events',0,5)
 assert m().read_inventory_namespace(s,old,*i,'people')==('people',1,0)
 s.verify_all();s.close()

@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_failure_and_exact_recovery(tmp_path,phase):
 s,p,a,d,i=setup(tmp_path)
 def fault(at):
  if phase==at:raise RuntimeError('fault')
 s._phase_hook=fault
 with pytest.raises(RuntimeError):save(s,p,a,d,i,version_changes=(VersionChange('people',0,delete=True),))
 s._phase_hook=lambda _:None
 r=m().resolve_inventory(s,p,*i,d,a.content,commit_token='next',scope_authority=a.scope,record_authority=a.record)
 assert r.content.commit.outcome==('committed' if phase=='after_commit' else 'not_committed')
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,'people')==('people',0 if phase=='after_commit' else 1,0)
 s.close()

def test_metadata_only_and_noop(tmp_path):
 s,p,a,d,i=setup(tmp_path);r=save(s,p,a,d,i,namespaces=())
 assert r.inventory[0].root==i[0].root and r.inventory[0].head.simulation_position!=i[0].head.simulation_position;s.close()
 s,p,a,d,i=setup(tmp_path/'other');r=save(s,p,a,d,i,namespaces=(),metadata=metadata(1))
 assert r.content.commit.outcome=='not_committed' and r.inventory==i;s.close()

@pytest.mark.parametrize('changes',[('lazy-delete',),('ordinary-delete',),('reinsert',),('absent-delete',)])
def test_count_transition_edges(tmp_path,changes):
 s,p,a,d,i=setup(tmp_path);kind=changes[0]
 kwargs={}
 if kind=='lazy-delete':kwargs['version_changes']=(VersionChange('people',0,delete=True),)
 elif kind=='ordinary-delete':kwargs.update(namespaces=(),changes=(RecordChange('ordinary',0,delete=True),))
 elif kind=='reinsert':kwargs['version_changes']=(VersionChange('people',0,{},reinsertion=True),)
 else:kwargs['version_changes']=(VersionChange('people',999,delete=True),)
 r=save(s,p,a,d,i,**kwargs);ns='ordinary' if kind=='ordinary-delete' else 'people'
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,ns)==(ns,0 if kind.endswith('delete') and kind!='absent-delete' else 1,0)
 s.verify_all();s.close()

@pytest.mark.parametrize('new_namespace',[False,True])
def test_empty_world_first_save(tmp_path,new_namespace):
 from ate_sim.incremental_store import TypedCodec
 from ate_sim.persistence_lazy_store import LazyRecordStore
 from ate_sim.persistence_proof_record import bootstrap_record_proofs
 from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
 from ate_sim.persistence_proof_publication import bootstrap_content_proofs
 from simulation.tests.proof_publication_fixtures import Authorities
 s=LazyRecordStore.create(tmp_path/'empty.sqlite',codec=TypedCodec(),simulation_schema='8',rules_id='empty');p=s.capture_pin()
 record=bootstrap_record_proofs(s,p);scope=bootstrap_scope_proofs(s,p);a=Authorities(bootstrap_content_proofs(s,p),record,scope);d=bootstrap_collection_directory(s,p);i=m().bootstrap_inventory(s,p)
 r=save(s,p,a,d,i,namespaces=('people',) if new_namespace else (),version_changes=(VersionChange('people',0,{}),) if new_namespace else ())
 page=m().read_inventory_namespaces(s,r.content.commit.pin,*r.inventory)
 assert page.entries==(('archive',0,0),('events',0,0),('ordinary',0,0),('people',1 if new_namespace else 0,0));s.close()

@pytest.mark.parametrize('fault',['expected','head','allocator','node','row','temp','view','hook','cursor','limit','transaction','private'])
def test_malformed_sources_rejected(tmp_path,fault):
 from ate_sim.incremental_store import _head_checksum
 from ate_sim.persistence_lazy_store import _identity_state_checksum
 s,p,a,d,i=setup(tmp_path);kw={}
 if fault=='expected':i=(i[0],b'x'*32)
 elif fault=='head':
  row=list(s._checked_head_row());row[4]=s.codec.encode({'changed':1});row[-1]=_head_checksum(*row[:-1]);s.db.execute('UPDATE save_head SET next_ids=?,head_checksum=?',(row[4],row[-1]))
 elif fault=='allocator':s.db.execute('UPDATE lazy_identity_state SET next_incarnation_id=?,row_checksum=?',(99,_identity_state_checksum(99,1,None)))
 elif fault=='node':s.db.execute('DELETE FROM ate_ordered_seek_nodes')
 elif fault=='row':s.db.execute('UPDATE ate_inventory_generations SET certificate=?',(b'[]',))
 elif fault=='temp':s.db.execute('CREATE TEMP TABLE save_head AS SELECT * FROM main.save_head')
 elif fault=='view':
  s.db.execute('ALTER TABLE save_head RENAME TO old_head');s.db.execute('CREATE VIEW save_head AS SELECT * FROM old_head')
 elif fault=='hook':s.codec.decode=lambda _:pytest.fail('decoder hook invoked')
 elif fault=='cursor':kw['after']=b'x'*4097
 elif fault=='limit':kw['limit']=True
 elif fault=='private':kw['_scope_proof']=object()
 s.db.commit()
 if fault=='transaction':s.db.execute('BEGIN')
 with pytest.raises(StoreError):
  if fault=='private':save(s,p,a,d,i,**kw)
  else:m().read_inventory_namespaces(s,p,*i,**kw)
 if s.db.in_transaction:s.db.rollback()
 s.close()

def test_actual_written_counts_must_match_derived_delta(tmp_path,monkeypatch):
 from ate_sim.incremental_store import _head_checksum
 from ate_sim.persistence_lazy_store import LazyRecordStore
 s,p,a,d,i=setup(tmp_path);original=LazyRecordStore._write_ordinary_changes
 def wrong(self,*args,**kwargs):
  original(self,*args,**kwargs)
  # Mutate the writer's shared count accumulator before the head is published.
  args[2]['ordinary']=(99,0)
 monkeypatch.setattr(LazyRecordStore,'_write_ordinary_changes',wrong)
 with pytest.raises(StoreError):save(s,p,a,d,i,changes=(RecordChange('ordinary',1,{}),))
 assert s.generation==1;s.close()

def test_namespace_metadata_change_and_exact_raw_values(tmp_path):
 s,p,a,d,i=setup(tmp_path);meta=metadata(2);meta.update(namespaces=(*meta['namespaces'],'zero'),next_ids={'actor':11},seed=88,simulation_position=('year',42))
 r=save(s,p,a,d,i,namespaces=(),metadata=meta)
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,'zero')==('zero',0,0)
 h=r.inventory[0].head
 assert (h.seed,h.next_ids,h.simulation_position)==(88,s.codec.encode({'actor':11}),s.codec.encode(('year',42)));s.close()

def test_successive_save_and_reopen_recovery(tmp_path):
 from ate_sim.incremental_store import TypedCodec
 from ate_sim.persistence_lazy_store import LazyRecordStore
 from simulation.tests.proof_publication_fixtures import Authorities
 s,p,a,d,i=setup(tmp_path);r=save(s,p,a,d,i,version_changes=(VersionChange('people',1,{}),));p2=r.content.commit.pin
 a2=Authorities((r.content.certificate,r.content.commitment),(r.content.scope.record.certificate,r.content.scope.record.commitment),(r.content.scope.certificate,r.content.scope.commitment))
 r2=save(s,p2,a2,r.directory,r.inventory,commit_token='third',version_changes=(VersionChange('people',0,delete=True),));s.close()
 s=LazyRecordStore.open(tmp_path/'i.sqlite',codec=TypedCodec(),expected_simulation_schema='8',expected_rules_id='content-publication-test')
 recovered=m().resolve_inventory(s,p2,*r.inventory,r.directory,a2.content,commit_token='third',scope_authority=a2.scope,record_authority=a2.record)
 assert recovered.inventory==r2.inventory
 with pytest.raises(StoreError):m().resolve_inventory(s,p2,*r.inventory,r.directory,a2.content,commit_token='wrong',scope_authority=a2.scope,record_authority=a2.record)
 assert m().read_inventory_namespace(s,recovered.content.commit.pin,*recovered.inventory,'people')==('people',1,0);s.close()

@pytest.mark.parametrize('operation',['insert','update','delete'])
def test_auxiliary_lazy_records_preserve_head_count_semantics(tmp_path,operation):
 from simulation.tests.proof_publication_fixtures import Authorities
 s,p,a,d,i=setup(tmp_path)
 if operation!='insert':
  first=save(s,p,a,d,i,namespaces=('aux.lazy.test',),version_changes=(VersionChange('aux.lazy.test',0,{}),))
  p=first.content.commit.pin;d=first.directory;i=first.inventory
  a=Authorities((first.content.certificate,first.content.commitment),(first.content.scope.record.certificate,first.content.scope.record.commitment),(first.content.scope.certificate,first.content.scope.commitment))
 r=save(s,p,a,d,i,namespaces=('aux.lazy.test',),commit_token='aux-final',version_changes=(VersionChange('aux.lazy.test',0,{'new':1},delete=operation=='delete'),))
 assert r.inventory[0].head.namespace_counts==i[0].head.namespace_counts
 assert m().read_inventory_namespace(s,r.content.commit.pin,*r.inventory,'aux.lazy.test') is None
 s.verify_all();s.close()

@pytest.mark.parametrize('table',['lazy_record_versions','lazy_order_versions'])
def test_bootstrap_rejects_checksummed_orphan_namespace(tmp_path,table):
 from ate_sim.persistence_lazy_store import _order_checksum,_version_checksum
 from ate_sim.incremental_store import _record_checksum
 s,p,a,d,i=setup(tmp_path);columns=[v[1] for v in s.db.execute('PRAGMA table_info('+table+')')]
 row=dict(zip(columns,s.db.execute('SELECT * FROM '+table+" WHERE namespace='people' LIMIT 1").fetchone()));row['namespace']='ghost'
 if table=='lazy_order_versions':row['row_checksum']=_order_checksum(row['namespace'],row['typed_key'],row['ordinal'],row['valid_from'],row['valid_to'])
 else:
  row['row_checksum']=_version_checksum(row['namespace'],row['typed_key'],row['record_schema'],row['codec_version'],row['valid_from'],row['valid_to'],row['memberships'],row['payload'])
 s.db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in columns)+')',[row[k] for k in columns]);s.db.commit()
 # Characterize the inherited audit gap; the constructor must supplement it.
 s.verify_all()
 before=s.db.execute('SELECT * FROM ate_inventory_generations ORDER BY generation').fetchall()
 with pytest.raises(StoreError):m().bootstrap_inventory(s,p)
 assert not s.db.in_transaction and s.db.execute('SELECT * FROM ate_inventory_generations ORDER BY generation').fetchall()==before;s.close()

@pytest.mark.parametrize('operation',['read','bootstrap'])
def test_node_source_replacement_rejected_before_callback(tmp_path,operation):
 s,p,a,d,i=setup(tmp_path);calls=[]
 s.db.create_function('inventory_node_hook',1,lambda value:(calls.append(value),value)[1])
 s.db.execute('ALTER TABLE ate_ordered_seek_nodes RENAME TO saved_nodes')
 s.db.execute('CREATE VIEW ate_ordered_seek_nodes AS SELECT domain,digest,inventory_node_hook(raw) AS raw FROM saved_nodes');s.db.commit()
 with pytest.raises(StoreError):
  if operation=='read':m().read_inventory_namespaces(s,p,*i)
  else:m().bootstrap_inventory(s,p)
 assert calls==[];s.close()
