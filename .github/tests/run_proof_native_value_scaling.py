"""Actual native first-access scalar save; admission/copy are explicit setup."""
import argparse,hashlib,json,re,sqlite3,subprocess,time,tracemalloc
from pathlib import Path
from simulation.tests.proof_world_fixtures import make_world
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
from ate_sim import persistence_proof_world as world

class _VMWorkBudget:
 def __init__(self,limit):self.limit,self.steps=limit,0
 def __call__(self):self.steps+=1;return int(self.steps>self.limit)

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 files={'driver_sha256':Path(__file__),'fixture_sha256':Path('simulation/tests/proof_world_fixtures.py'),'authority_fixture_sha256':Path('simulation/tests/test_stage_0_5_final_catalog_copy.py')}
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),sqlite=sqlite3.sqlite_version,**{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()})
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,a,ra,d=make_world(output/f'source-{n}',size=n);path=s.path;s.release_pin(p);s.close()
  path_out=output/f'proof-{n}.sqlite';copy=copy_world_with_proofs(path,path_out,rules_id=RULES);construction=time.perf_counter()-start
  counts={'history_body':0};calls=[];original=world._audit_world
  def no_full(*a,**k):calls.append(True);raise AssertionError('native scalar save invoked full World audit')
  start=time.perf_counter();session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=copy.commitment);admission=time.perf_counter()-start
  def trace(sql):
   t=sql.lower()
   if t.startswith('select') and (re.search(r'(?:select|,|then)\s*payload\b',t) or re.match(r'select\s+\*',t)) and any(ns in t for ns in ('aux.lazy.nested.list_pages','aux.lazy.nested.entries','aux.lazy.sequence.nodes','from segments')):counts['history_body']+=1
  try:
   session.store.reset_diagnostics();session.store.db.set_trace_callback(trace);world._audit_world=no_full;tracemalloc.start();start=time.perf_counter()
   try:session.skills[1,'craft'].level=.5;assert session.save()==1;elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();session.store.db.set_trace_callback(None);world._audit_world=original
   first=session.proof_manifest
   assert first[0].roots[2:]==copy.manifest.roots[2:] and not calls and counts['history_body']==0 and peak<8*1048576
  finally:session.close()
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=first[1]);vm=_VMWorkBudget(6000000)
  try:
   session.store.db.set_progress_handler(vm,1);world._audit_world=no_full
   try:assert session.skills[1,'craft'].level==.5;session.skills[1,'craft'].level=.75;assert session.save()==2
   finally:session.store.db.set_progress_handler(None,0);world._audit_world=original
   final=session.proof_manifest
   assert not calls and vm.steps<=vm.limit and final[0].roots[2:]==first[0].roots[2:]
  finally:session.close()
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1])
  try:
   world._audit_world=no_full;start=time.perf_counter()
   try:session.skills[1,'craft'].level=.875;assert session.save()==3;raw_elapsed=time.perf_counter()-start
   finally:world._audit_world=original
   final=session.proof_manifest
  finally:session.close()
  # A shared history value changes one existing physical page. Setup derives its
  # exact raw locator; first native owner/history access stays inside measurement.
  from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1])
  raw=session.store.read_version(session.pin,'world.skills.skills',(1,'craft'),expected_record_schema=1).value
  target_key=session.store.codec.encode((raw.provenance.incarnation,0));selected=target_key.hex().lower();body={'selected':0,'unrelated':0}
  def history_trace(sql):
   t=sql.lower()
   if t.startswith('select') and (re.search(r'(?:select|,|then)\s*payload\b',t) or re.match(r'select\s+\*',t)) and any(ns in t for ns in ('aux.lazy.nested.list_pages','aux.lazy.nested.entries','aux.lazy.sequence.nodes','from segments')):
    body['selected' if PAGE_NAMESPACE in t and (selected in t if type(selected) is str else any(k in t for k in selected)) else 'unrelated']+=1
  try:
   session.store.db.set_trace_callback(history_trace);world._audit_world=no_full;start=time.perf_counter()
   try:session.skills[1,'craft'].provenance[0]=999;assert session.save()==4;backing_elapsed=time.perf_counter()-start
   finally:session.store.db.set_trace_callback(None);world._audit_world=original
   final=session.proof_manifest
   assert body['selected']>0 and body['unrelated']==0 and not calls
  finally:session.close()
  # Independently guard total SQL work on another cold native session.
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1]);backing_vm=_VMWorkBudget(6000000)
  try:
   session.store.db.set_progress_handler(backing_vm,1);world._audit_world=no_full
   try:session.skills[1,'craft'].provenance[0]=998;assert session.save()==5
   finally:session.store.db.set_progress_handler(None,0);world._audit_world=original
   final=session.proof_manifest
   backing_body=dict(body)
   assert not calls and backing_vm.steps<=backing_vm.limit
  finally:session.close()
  # Resize the selected last page; authenticated descriptor/type facts change.
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1])
  selected=session.store.codec.encode((raw.provenance.incarnation,(n-1)//128)).hex().lower();body={'selected':0,'unrelated':0}
  try:
   session.store.db.set_trace_callback(history_trace);world._audit_world=no_full;start=time.perf_counter()
   try:session.skills[1,'craft'].provenance.append(997);assert session.save()==6;tail_elapsed=time.perf_counter()-start
   finally:session.store.db.set_trace_callback(None);world._audit_world=original
   final=session.proof_manifest;tail_body=dict(body)
   assert tail_body['selected']>0 and tail_body['unrelated']==0 and not calls
  finally:session.close()
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1]);tail_vm=_VMWorkBudget(6000000)
  try:
   session.store.db.set_progress_handler(tail_vm,1);world._audit_world=no_full
   try:assert session.skills[1,'craft'].provenance.pop()==997;assert session.save()==7
   finally:session.store.db.set_progress_handler(None,0);world._audit_world=original
   final=session.proof_manifest
   assert not calls and tail_vm.steps<=tail_vm.limit
  finally:session.close()
  # Cross a physical page boundary, with only old-tail/new-page reads allowed.
  growth_count=128
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1])
  selected=tuple(session.store.codec.encode((raw.provenance.incarnation,p)).hex().lower() for p in ((n-1)//128,(n+127)//128));body={'selected':0,'unrelated':0}
  try:
   session.store.db.set_trace_callback(history_trace);world._audit_world=no_full;start=time.perf_counter()
   try:session.skills[1,'craft'].provenance.extend([997]*growth_count);assert session.save()==8;page_elapsed=time.perf_counter()-start
   finally:session.store.db.set_trace_callback(None);world._audit_world=original
   final=session.proof_manifest;page_body=dict(body)
   assert page_body['selected']>0 and page_body['unrelated']==0 and not calls
  finally:session.close()
  # A second boundary-crossing save independently guards interval-one VM work.
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1]);page_vm=_VMWorkBudget(6000000)
  try:
   session.store.db.set_progress_handler(page_vm,1);world._audit_world=no_full
   try:session.skills[1,'craft'].provenance.extend([998]*128);assert session.save()==9
   finally:session.store.db.set_progress_handler(None,0);world._audit_world=original
   final=session.proof_manifest
   assert not calls and page_vm.steps<=page_vm.limit
  finally:session.close()
  # Remove one page under checked audit, then measure authenticated reuse.
  with open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1]) as setup:
   values=setup.skills[1,'craft'].provenance
   for _ in range(128):values.pop()
   assert setup.save()==10;final=setup.proof_manifest
  session=open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1])
  selected=tuple(session.store.codec.encode((raw.provenance.incarnation,p)).hex().lower() for p in ((n+127)//128,(n+255)//128));body={'selected':0,'unrelated':0};reuse_vm=_VMWorkBudget(6000000)
  try:
   session.store.db.set_trace_callback(history_trace);session.store.db.set_progress_handler(reuse_vm,1);world._audit_world=no_full;start=time.perf_counter()
   try:session.skills[1,'craft'].provenance.extend([999]*128);assert session.save()==11;reuse_elapsed=time.perf_counter()-start
   finally:session.store.db.set_trace_callback(None);session.store.db.set_progress_handler(None,0);world._audit_world=original
   final=session.proof_manifest;reuse_body=dict(body)
   assert reuse_body['selected']>0 and reuse_body['unrelated']==0 and not calls and reuse_vm.steps<=reuse_vm.limit
  finally:session.close()
  with open_audited_proof_world_session(path_out,rules_id=RULES,expected_commitment=final[1]) as reopened:
   assert reopened.skills[1,'craft'].level==.875 and reopened.skills[1,'craft'].provenance is reopened.skills[2,'craft'].provenance
   assert reopened.skills[2,'craft'].provenance[-1]==999
   assert reopened.skills[2,'craft'].provenance[0]==998 and len(reopened.skills[2,'craft'].provenance)==n+growth_count+128
  row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,audited_admission_seconds=admission,native_first_access_and_save_ms=elapsed*1000,native_first_access_and_save_unprofiled_ms=raw_elapsed*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,vm_measurement='separate fresh-session first-access native save, interval-one guard',sql=counts,full_audits_during_save=0,backing_first_access_and_save_ms=backing_elapsed*1000,backing_sql=backing_body,backing_vm_steps=backing_vm.steps,tail_first_access_and_save_ms=tail_elapsed*1000,tail_sql=tail_body,tail_vm_steps=tail_vm.steps,page_growth_first_access_and_save_ms=page_elapsed*1000,page_growth_sql=page_body,page_growth_vm_steps=page_vm.steps,regrowth_profiled_first_access_and_save_ms=reuse_elapsed*1000,regrowth_sql=reuse_body,regrowth_vm_steps=reuse_vm.steps,regrowth_added_values=128,page_growth_added_values=growth_count,page_growth_vm_added_values=128,archive_unit='retained history values')
  results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(raw_elapsed*1000,2),'ms unprofiled native first-access save;',round(elapsed*1000,2),'ms with allocation profiling;',round(backing_elapsed*1000,2),'ms backing value save;',round(tail_elapsed*1000,2),'ms tail resize;',round(page_elapsed*1000,2),'ms page growth; zero unrelated history bodies',flush=True)
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
