import hashlib,json,pathlib,platform,sqlite3,sys,tempfile
from unittest.mock import patch
expected=json.loads(pathlib.Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
assert sys.version==expected['python'] and platform.python_compiler()==expected['compiler'] and sqlite3.sqlite_version==expected['sqlite']
for path,key in [(pathlib.Path(sys.executable).resolve(),'executable_sha256'),(pathlib.Path(expected['sqlite_extension_path']),'sqlite_extension_sha256')]:
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected[key]
for lib in expected['loaded_sqlite_libraries']:
 assert hashlib.sha256(pathlib.Path(lib['path']).read_bytes()).hexdigest()==lib['sha256']
with sqlite3.connect(':memory:') as db:
 assert db.execute('select sqlite_source_id()').fetchone()[0]==expected['sqlite_source_id']
 assert [r[0] for r in db.execute('pragma compile_options')]==expected['sqlite_compile_options']
print('Qualified runtime full fingerprint verified',flush=True)
from simulation.tests.test_stage_0_5_publication_proof_reuse import prepared,make_store
from simulation.ate_sim.persistence_lazy_participants import CoordinatorSaveParticipant
from simulation.ate_sim.persistence_validation_scope import ValidationScope
from simulation.ate_sim.incremental_store import StoreIntegrityError
for mode in ['normal','borrowed','exception','small_budget','corruption_after_validation','rollback_after_validation']:
 with tempfile.TemporaryDirectory() as folder, make_store(pathlib.Path(folder)/'probe.sqlite') as store:
  coord,delta,pin=prepared(store)
  if mode=='small_budget':coord.catalog.byte_limit=128
  part=CoordinatorSaveParticipant(coord,delta,coord.pin,pin.captured_head)
  seen=[]
  original=ValidationScope.remember
  def remember(scope,*args,**kwargs):
   result=original(scope,*args,**kwargs)
   seen.append((scope._valid,scope.byte_limit,scope.bytes,scope.entries))
   return result
  with patch.object(ValidationScope,'remember',remember):
   if mode=='borrowed':
    with store.read_snapshot(pin):
     part.validate_publication(delta,pin)
     assert part._publication_proof is not None and not part._publication_proof.standalone
     assert getattr(store,'_validation_scope',None) is None
   elif mode=='exception':
    with patch.object(coord,'validate_publication',side_effect=RuntimeError('probe')):
     try:part.validate_publication(delta,pin)
     except RuntimeError:pass
     else:raise AssertionError('exception lost')
    assert part._publication_proof is None and part._row_proved_pin is None
   else:
    part.validate_publication(delta,pin)
    assert part._publication_proof.standalone
    if mode=='corruption_after_validation':
     from simulation.ate_sim.persistence_lazy_identity_catalog import OWNER_NAMESPACE
     store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?',(b'bad',OWNER_NAMESPACE));store.db.commit()
     assert not part._publication_proof.matches(coord,delta,pin)
     try:coord.accept_delta(delta,pin,proof=part._publication_proof)
     except StoreIntegrityError:pass
     else:raise AssertionError('corruption accepted')
    elif mode=='rollback_after_validation':
     store.db.execute('SAVEPOINT x');store.db.execute('UPDATE lazy_record_versions SET payload=payload');store.db.execute('ROLLBACK TO x');store.db.execute('RELEASE x')
     assert not part._publication_proof.matches(coord,delta,pin)
  assert getattr(store,'_validation_scope',None) is None and not store.db.in_transaction
  print(mode,'OK','scope_peak',max((x[2] for x in seen),default=0),'catalog_budget',coord.catalog.byte_limit,'scopes',sorted(set((x[0],x[1]) for x in seen)),flush=True)
