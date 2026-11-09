"""Real SQLite + cancellation after constructor completed, before caller owns session."""
import json,pathlib,sqlite3,sys
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open,pin_count
from ate_sim.persistence_lazy import LazyWorldSession
root=pathlib.Path('/tmp/ate-proof-opening-review/session-return-fixture');root.mkdir(exist_ok=True)
path,pair=ranked_fixture(root,size=4)
held=[]
def inject(frame,event,arg):
    if frame.f_code is LazyWorldSession.__init__.__code__ and event=='return' and not held:
        held.append(frame.f_locals['self'])
        raise KeyboardInterrupt('cancelled at constructed session return')
    return inject
sys.settrace(inject)
try:fast_open(path,pair)
except KeyboardInterrupt as exc:print('primary_error',repr(exc))
finally:sys.settrace(None)
s=held[0]
try:s.store.db.execute('SELECT 1');closed=False
except sqlite3.ProgrammingError:closed=True
result=dict(connection_closed=closed,pin_count_after_failure=pin_count(path),registry_closed=s._registry._closed,session_active=s._active,session_state=s._state,registry_diagnostics=s._registry.diagnostics())
print(json.dumps(result,indent=2))
(root.parent/'session-return-cancel-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert closed and result['pin_count_after_failure']==0
assert result['registry_closed'] is False and result['session_active'] is True
