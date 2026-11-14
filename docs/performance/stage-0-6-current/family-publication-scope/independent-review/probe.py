from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
from simulation.tests.test_persistence_lazy_store import make_store, metadata, open_store
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.ate_sim.persistence_lazy_participants import FamilySaveParticipant
from simulation.ate_sim.persistence_lazy_families import ParticipantDelta
from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList
from simulation.ate_sim import persistence_history_dependencies as deps
from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreConflictError

results=[]
for kind in ('family','dependencies'):
 for mode in ('owned','borrowed','exception','corrupt','write_rollback','codec','lease','wrong_plan','wrong_pin'):
  with TemporaryDirectory(dir=Path(__file__).parent) as temp:
   path=Path(temp)/'probe.sqlite'
   with make_store(path) as store:
    parent=store.capture_pin()
    if kind=='family':
     changes=(VersionChange('people',1,{'x':1}),VersionChange('people',2,{'x':2}))
     delta=ParticipantDelta.freeze(store.codec,'people',version_changes=changes)
     part=FamilySaveParticipant(store,parent,1,delta)
    else:
     part=deps.BackingDependencyPool(store,parent)
     aliases=[LazyHistoryList(store,parent,n,initial_values=[n]) for n in (1,2)]
     for alias in aliases:part.acquire(alias)
     delta=part.prepare_delta()
     changes=tuple(c for alias in aliases for c in alias.pending_changes())+delta.decode(store.codec)[0]
    successor=store.commit(parent,commit_token='probe',version_changes=changes,changes=(),new_segments=(),metadata=metadata(1,('people',) if kind=='family' else ())).pin
    seen=[]
    original=store._visible_record_row
    def inspect(*args,**kwargs):
     scope=store._validation_scope
     if not seen:
      seen.append(scope)
      assert scope.can_reuse(store,successor)==(mode!='borrowed')
      if mode=='exception':raise RuntimeError('review injected exception')
      if mode in ('write_rollback','lease'):
       store.db.execute('SAVEPOINT review')
       if mode=='lease':store.db.execute('DELETE FROM generation_pins WHERE token=?',(successor.token,))
       else:store.db.execute("UPDATE save_head SET seed=seed+1")
       store.db.execute('ROLLBACK TO review')
       store.db.execute('RELEASE review')
       assert not scope.can_reuse(store,successor)
      if mode=='codec':
       store.codec=type(store.codec)()
       assert not scope.can_reuse(store,successor)
      if mode=='owned':
       for n in range(300):scope.remember('probe',(n,),('data',n))
       assert scope.entries<=256 and scope.bytes<=256*1024
     return original(*args,**kwargs)
    if mode=='corrupt':
     part.validate_publication(delta,successor)
     namespace='people' if kind=='family' else deps.NAMESPACE
     store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?',(b'bad',namespace));store.db.commit()
    candidate=replace(delta) if mode=='wrong_plan' else delta
    pin=replace(successor,token='unregistered') if mode=='wrong_pin' else successor
    expected=(StoreIntegrityError,StoreConflictError) if mode in ('corrupt','wrong_plan','wrong_pin') else (RuntimeError,) if mode=='exception' else ()
    try:
     with patch.object(store,'_visible_record_row',inspect):
      with store.read_transaction() if mode=='borrowed' else nullcontext():
       part.validate_publication(candidate,pin)
    except expected:pass
    else:assert not expected, (kind,mode,'expected rejection')
    assert getattr(store,'_validation_scope',None) is None
    assert not store.db.in_transaction
    assert all(s.entries==0 and not s.can_reuse(store,successor) for s in seen)
    if expected:
     if kind=='family':assert not part.accepted and part._validated_pin is None
     else:assert part._prepared is delta and not part._persisted
    elif mode=='owned':
     part.accept_delta(delta,successor)
     token=successor.token
   if mode=='owned':
    with open_store(path) as restored:
     assert restored._require_pin(successor)==1
     if kind=='family':assert restored.read_version(successor,'people',2,expected_record_schema=1).value=={'x':2}
     else:
      for n in (1,2):assert deps.active_backing_dependencies(restored,successor,n)==(token,)
   results.append({'kind':kind,'mode':mode,'passed':True})
print(json.dumps(results,indent=2))
