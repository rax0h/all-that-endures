"""Verify R2 closure before the registry exists, for both cancellation kinds."""
import hashlib,json,pathlib,shutil,sqlite3,sys
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open,pin_count
from ate_sim.persistence_lazy import LazyWorldSession
from ate_sim import persistence_proof_world as world_proof
root=pathlib.Path('/tmp/ate-proof-opening-review/closure-extra');root.mkdir(exist_ok=True)
source,pair=ranked_fixture(root,size=4)
with fast_open(source,pair) as session:assert not session.store.db.in_transaction
assert pin_count(source)==0
source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
original=world_proof._audit_world
def forbidden(*a,**k):raise AssertionError('closure probe invoked World audit')
world_proof._audit_world=forbidden
results=[]
try:
    for error in (KeyboardInterrupt,SystemExit):
        path=root/(error.__name__+'.sqlite');shutil.copyfile(source,path);held=[]
        def inject(frame,event,arg):
            if frame.f_code is LazyWorldSession.__init__.__code__ and event=='line' and not held:
                obj=frame.f_locals.get('self');owner=frame.f_locals.get('_opening_resources')
                if owner is not None and owner.session is obj and not hasattr(obj,'_registry'):
                    held.append(obj)
                    raise error('cancelled before registry allocation')
            return inject
        sys.settrace(inject)
        try:fast_open(path,pair)
        except error as exc:primary=str(exc)
        else:raise AssertionError('probe did not cancel')
        finally:sys.settrace(None)
        obj=held[0]
        try:obj.store.db.execute('SELECT 1');closed=False
        except sqlite3.ProgrammingError:closed=True
        result=dict(error=error.__name__,primary=primary,registry_ever_allocated=hasattr(obj,'_registry'),connection_closed=closed,pins_remaining=pin_count(path),active=obj._active,state=obj._state)
        assert primary=='cancelled before registry allocation'
        assert not result['registry_ever_allocated'] and closed and result['pins_remaining']==0 and not obj._active and obj._state=='closed'
        results.append(result)
finally:world_proof._audit_world=original
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
(root.parent/'closure-partial-session-result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
