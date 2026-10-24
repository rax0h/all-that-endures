import importlib
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError,TypedCodec
from ate_sim.persistence_lazy_store import VersionChange,LazyRecordStore
from simulation.tests.proof_scope_fixtures import make_scope_store,metadata

def module():return importlib.import_module('ate_sim.persistence_proof_collection_directory')
def setup(tmp_path):
 s,p,_=make_scope_store(tmp_path/'d.sqlite',3,bootstrap=False);m=module();return m,s,p,m.bootstrap_collection_directory(s,p)

def test_complete_directory_pages_and_order_authorities(tmp_path):
 from ate_sim.persistence_proof_collection import read_collection_page
 m,s,p,a=setup(tmp_path);assert a[0].root.count==2
 s.reset_diagnostics();first=m.read_collection_namespaces(s,p,*a,limit=1)
 assert [c.namespace for c,e in first.entries]==['archive'] and first.next_after==b'archive'
 second=m.read_collection_namespaces(s,p,*a,after=first.next_after)
 assert [c.namespace for c,e in second.entries]==['people'] and second.next_after is None
 assert m.read_collection_namespace(s,p,*a,'missing') is None
 assert m.read_collection_namespace(s,p,*a,'ordinary') is None
 assert s._payload_reads==s._payload_check_reads==0
 assert read_collection_page(s,p,*first.entries[0]).positions==tuple((s.codec.encode(i),i) for i in range(3));s.close()

def test_empty_store_and_declared_empty_directory(tmp_path):
 m=module();s=LazyRecordStore.create(tmp_path/'empty.sqlite',codec=TypedCodec(),simulation_schema='8',rules_id='directory-test');p=s.capture_pin();a=m.bootstrap_collection_directory(s,p)
 assert a[0].root.count==0 and m.read_collection_namespaces(s,p,*a).entries==();s.close()
 m,s,p,a=setup(tmp_path)
 out=s.commit(p,commit_token='empty',version_changes=(VersionChange('archive',i,delete=True) for i in range(3)),changes=(),new_segments=(),metadata=metadata(2))
 b=m.bootstrap_collection_directory(s,out.pin);pair=m.read_collection_namespace(s,out.pin,*b,'archive')
 assert pair[0].declared and pair[0].member_count==0 and pair[0].next_ordinal==3;s.close()

def test_retained_directory_and_generation_independent_bodies(tmp_path):
 m,s,p,a=setup(tmp_path);old=s.capture_pin()
 bodies=s.db.execute('SELECT digest FROM ate_collection_directory_bodies ORDER BY digest').fetchall()
 out=s.commit(p,commit_token='metadata',version_changes=(),changes=(),new_segments=(),metadata=metadata(2))
 b=m.bootstrap_collection_directory(s,out.pin)
 assert a[0].root==b[0].root and a[1]!=b[1]
 assert s.db.execute('SELECT digest FROM ate_collection_directory_bodies ORDER BY digest').fetchall()==bodies
 assert m.read_collection_namespace(s,old,*a,'archive')[0].generation==1
 assert m.read_collection_namespace(s,out.pin,*b,'archive')[0].generation==2;s.close()

@pytest.mark.parametrize('fault',['expected','generation','counter','missing','descriptor','node','shadow','hook','budget','transaction','cursor','limit'])
def test_reject_invalid_directory_source(tmp_path,fault):
 m,s,p,a=setup(tmp_path);kw={}
 if fault=='expected':a=(a[0],b'x'*32)
 elif fault=='generation':a=(replace(a[0],generation=0),a[1])
 elif fault=='counter':s.db.execute('UPDATE lazy_namespace_state SET next_ordinal=next_ordinal+1')
 elif fault=='missing':s.db.execute("DELETE FROM lazy_namespace_state WHERE namespace='archive'")
 elif fault=='descriptor':s.db.execute("UPDATE ate_collection_directory_bodies SET raw=zeroblob(61)")
 elif fault=='node':s.db.execute('DELETE FROM ate_ordered_seek_nodes')
 elif fault=='shadow':s.db.execute('CREATE TEMP TABLE lazy_namespace_state AS SELECT * FROM main.lazy_namespace_state')
 elif fault=='hook':s.codec.decode=lambda _:pytest.fail('hook called')
 elif fault=='budget':kw['max_metadata_bytes']=1
 elif fault=='cursor':kw['after']=b'x'*4097
 elif fault=='limit':kw['limit']=True
 s.db.commit()
 if fault=='transaction':s.db.execute('BEGIN')
 with pytest.raises(StoreError):m.read_collection_namespaces(s,p,*a,**kw)
 if s.db.in_transaction:s.db.rollback()
 s.close()

def test_absence_rejects_coherent_added_physical_namespace(tmp_path):
 from ate_sim.persistence_lazy_store import _namespace_checksum
 m,s,p,a=setup(tmp_path)
 s.db.execute('INSERT INTO lazy_namespace_state VALUES(?,?,?,?,?,?)',('surplus',p.captured_head,None,0,0,_namespace_checksum('surplus',0,0,p.captured_head,None)));s.db.commit()
 with pytest.raises(StoreError):m.read_collection_namespace(s,p,*a,'surplus')
 s.close()

@pytest.mark.parametrize('existing',[False,True])
def test_constructor_rollback_after_partial_build(tmp_path,monkeypatch,existing):
 m=module();s,p,_=make_scope_store(tmp_path/'rollback.sqlite',3,bootstrap=False)
 tables=('ate_collection_directory_bodies','ate_collection_generations','ate_ordered_seek_nodes')
 if existing:
  m.bootstrap_collection_directory(s,p)
  p=s.commit(p,commit_token='metadata',version_changes=(),changes=(),new_segments=(),metadata=metadata(2)).pin
  before={t:s.db.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall() for t in tables}
 from ate_sim import persistence_proof_collection as collection
 original=collection._construct_collection
 def fail(store,g,ns):
  if ns=='people':raise StoreError('second namespace fault')
  return original(store,g,ns)
 monkeypatch.setattr(collection,'_construct_collection',fail)
 with pytest.raises(StoreError,match='second namespace fault'):m.bootstrap_collection_directory(s,p)
 assert not s.db.in_transaction
 if existing:assert {t:s.db.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall() for t in tables}==before
 else:assert not s.db.execute("SELECT 1 FROM sqlite_schema WHERE name IN ('ate_collection_directory_bodies','ate_collection_generations','ate_ordered_seek_nodes')").fetchall()
 s.close()

def test_coherent_counter_disagreement_rejected(tmp_path):
 from ate_sim.persistence_lazy_store import _namespace_checksum
 m,s,p,a=setup(tmp_path)
 s.db.execute('UPDATE lazy_namespace_state SET next_ordinal=?,row_checksum=? WHERE namespace=?',(4,_namespace_checksum('archive',3,4,1,None),'archive'));s.db.commit()
 with pytest.raises(StoreError):m.read_collection_namespace(s,p,*a,'archive')
 s.close()

def test_one_full_audit_for_all_namespaces(tmp_path):
 m=module();s,p,_=make_scope_store(tmp_path/'audit.sqlite',3,bootstrap=False);trace=[];s.db.set_trace_callback(trace.append)
 a=m.bootstrap_collection_directory(s,p);s.db.set_trace_callback(None)
 assert sum(q.lower()=='pragma integrity_check' for q in trace)==1
 assert a[0].root.count==2;s.close()

def test_orphan_source_namespace_rejected_before_construction(tmp_path):
 m=module();s,p,_=make_scope_store(tmp_path/'orphan.sqlite',3,bootstrap=False)
 s.db.execute("DELETE FROM lazy_namespace_state WHERE namespace='archive'");s.db.commit()
 with pytest.raises(StoreError,match='outside declared collection inventory'):m.bootstrap_collection_directory(s,p)
 assert not s.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_collection_directory_bodies'").fetchall();s.close()

def test_directory_types_never_invoke_comparison_hooks(tmp_path):
 m,s,p,a=setup(tmp_path);calls=[]
 class Hook:
  def __eq__(self,other):calls.append(other);return True
 with pytest.raises(StoreError):m.read_collection_namespace(s,p,a[0],Hook(),'archive')
 with pytest.raises(StoreError):m.certificate_commitment(replace(a[0],generation=Hook()))
 assert not calls;s.close()

@pytest.mark.parametrize('temporary',[True,False])
@pytest.mark.parametrize('operation',['read','bootstrap'])
def test_source_replacement_rejected_before_sql_callback(tmp_path,temporary,operation):
 m,s,p,a=setup(tmp_path);calls=[]
 s.db.create_function('directory_hook',1,lambda value:(calls.append(value),value)[1])
 if not temporary:s.db.execute('ALTER TABLE save_head RENAME TO saved_head')
 source='main.save_head' if temporary else 'saved_head'
 s.db.execute('CREATE '+('TEMP ' if temporary else '')+'VIEW save_head AS SELECT singleton,directory_hook(generation) AS generation,parent_generation,simulation_position,seed,next_ids,namespace_inventory,namespace_counts,head_checksum FROM '+source);s.db.commit()
 with pytest.raises(StoreError):
  if operation=='read':m.read_collection_namespace(s,p,*a,'archive')
  else:m.bootstrap_collection_directory(s,p)
 assert calls==[];s.close()

@pytest.mark.parametrize('table',['lazy_order_versions','lazy_record_versions'])
@pytest.mark.parametrize('expired',[False,True])
def test_absence_rejects_selected_orphan_source(tmp_path,table,expired):
 from ate_sim.persistence_lazy_store import _order_checksum,_version_checksum
 from ate_sim.incremental_store import _record_checksum
 m,s,p,a=setup(tmp_path)
 # Copy a checksum-valid row into the queried, undeclared namespace. The
 # presence rejection must precede any payload/checksum materialization.
 columns=[v[1] for v in s.db.execute('PRAGMA table_info('+table+')')]
 row=list(s.db.execute('SELECT * FROM '+table+" WHERE namespace='archive' LIMIT 1").fetchone());row[columns.index('namespace')]='orphan'
 values=dict(zip(columns,row));values['valid_from']=0 if expired else p.captured_head;values['valid_to']=p.captured_head if expired else None
 if table=='lazy_order_versions':values['row_checksum']=_order_checksum(values['namespace'],values['typed_key'],values['ordinal'],values['valid_from'],values['valid_to'])
 else:
  values['payload_checksum']=_record_checksum(values['namespace'],values['typed_key'],values['record_schema'],values['codec_version'],values['valid_from'],values['payload'])
  values['row_checksum']=_version_checksum(values['namespace'],values['typed_key'],values['record_schema'],values['codec_version'],values['valid_from'],values['valid_to'],values['memberships'],values['payload'])
 row=[values[k] for k in columns]
 s.db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in columns)+')',row);s.db.commit()
 with pytest.raises(StoreError):m.read_collection_namespace(s,p,*a,'orphan')
 s.close()

def test_old_absence_skips_large_new_namespace_and_requires_index(tmp_path):
 m,s,p,a=setup(tmp_path);old=s.capture_pin()
 out=s.commit(p,commit_token='future',version_changes=(VersionChange('future',i,{'v':i}) for i in range(1000)),changes=(),new_segments=(),metadata=dict(metadata(2),namespaces=('people','archive','ordinary','future')))
 steps=[0]
 def progress():steps[0]+=100;return 0
 s.db.set_progress_handler(progress,100)
 assert m.read_collection_namespace(s,old,*a,'future') is None
 s.db.set_progress_handler(None,0);assert steps[0]<20000
 s.db.execute('DROP INDEX ate_directory_order_namespace_start');s.db.commit()
 with pytest.raises(StoreError):m.read_collection_namespace(s,old,*a,'future')
 s.close()
