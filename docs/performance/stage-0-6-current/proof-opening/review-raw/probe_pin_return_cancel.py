"""Real SQLite + trace injection at capture_pin's post-COMMIT return boundary."""
import json, pathlib, sqlite3, sys
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open, pin_count
root=pathlib.Path('/tmp/ate-proof-opening-review/pin-return-fixture');root.mkdir(exist_ok=True)
path,pair=ranked_fixture(root,size=4)
with fast_open(path,pair) as session:
    assert not session.store.db.in_transaction
assert pin_count(path)==0
print('healthy_control_pin_count',pin_count(path),flush=True)
seen=[];handles=[]
def inject(frame,event,arg):
    if frame.f_code.co_name=='capture_pin' and event=='return' and not seen:
        # The original capture implementation has committed SQLite by this event.
        db=frame.f_locals['self'].db
        seen.append(dict(in_transaction=db.in_transaction,token=frame.f_locals['token'],returned_pin=repr(arg)))
        handles.append(db)
        raise KeyboardInterrupt('cancelled at committed pin return')
    return inject
sys.settrace(inject)
try:
    fast_open(path,pair)
except KeyboardInterrupt as exc:
    print('primary_error',repr(exc),flush=True)
finally:
    sys.settrace(None)
try:handles[0].execute('SELECT 1');closed=False
except sqlite3.ProgrammingError:closed=True
result=dict(injection=seen,connection_closed=closed,pin_count_after_failure=pin_count(path))
print(json.dumps(result,indent=2),flush=True)
(root.parent/'pin-return-cancel-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert seen and seen[0]['in_transaction'] is False
assert closed
assert result['pin_count_after_failure']==1,'Suspected cancellation leak did not reproduce'
