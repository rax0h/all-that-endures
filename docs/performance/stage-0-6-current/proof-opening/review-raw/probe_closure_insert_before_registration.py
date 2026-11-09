"""Cancellation before registration must roll back its uncommitted INSERT only."""
import json,pathlib,sqlite3,sys
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open,pin_count,RULES
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_adapters import WorldCodec,SCHEMA
from ate_sim.persistence_proof_open import _remember_pin
root=pathlib.Path('/tmp/ate-proof-opening-review/closure-insert-boundary');root.mkdir(exist_ok=True)
path,pair=ranked_fixture(root,size=4)
foreign=LazyRecordStore.open(path,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=RULES)
foreign_pin=foreign.capture_pin();before=foreign.db.execute('SELECT * FROM generation_pins').fetchall();results=[]
try:
    for error in (KeyboardInterrupt,SystemExit):
        held=[];observed=[]
        def inject(frame,event,arg):
            if frame.f_code is _remember_pin.__code__ and event=='call' and not held:
                resources=frame.f_locals['resources'];db=frame.f_locals['store'].db
                held.append(db)
                observed.append(dict(in_transaction=db.in_transaction,registered_pin=resources.pin is not None))
                raise error('cancelled after INSERT before registration')
            return inject
        sys.settrace(inject)
        try:fast_open(path,pair)
        except error as exc:primary=str(exc)
        else:raise AssertionError('probe did not cancel')
        finally:sys.settrace(None)
        try:held[0].execute('SELECT 1');closed=False
        except sqlite3.ProgrammingError:closed=True
        after=foreign.db.execute('SELECT * FROM generation_pins').fetchall()
        result=dict(error=error.__name__,primary=primary,injection=observed,owned_connection_closed=closed,foreign_pin_preserved=before==after,foreign_connection_usable=foreign.db.execute('SELECT 1').fetchone()==(1,))
        assert primary=='cancelled after INSERT before registration' and closed and before==after
        assert observed==[dict(in_transaction=True,registered_pin=False)]
        results.append(result)
finally:
    foreign.release_pin(foreign_pin,cleanup_budget=0);foreign.close()
assert pin_count(path)==0
(root.parent/'closure-insert-before-registration-result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
