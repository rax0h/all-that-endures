"""Foreign lease negative control: rejected duplicate token must not become owned."""
import json,pathlib,sqlite3
from unittest.mock import patch
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open,pin_count,RULES
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_adapters import WorldCodec,SCHEMA
root=pathlib.Path('/tmp/ate-proof-opening-review/closure-collision');root.mkdir(exist_ok=True)
path,pair=ranked_fixture(root,size=4)
foreign=LazyRecordStore.open(path,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=RULES)
foreign_pin=foreign.capture_pin();before=foreign.db.execute('SELECT * FROM generation_pins').fetchall()
try:
    with patch('ate_sim.persistence_lazy_store.uuid.uuid4',return_value=foreign_pin.token):
        try:fast_open(path,pair)
        except sqlite3.IntegrityError as exc:error=str(exc)
        else:raise AssertionError('duplicate token unexpectedly captured')
    after=foreign.db.execute('SELECT * FROM generation_pins').fetchall()
    result=dict(error=error,before=before,after=after,foreign_connection_usable=foreign.db.execute('SELECT 1').fetchone()==(1,),foreign_pin_preserved=before==after)
    print(json.dumps(result,indent=2))
    (root.parent/'closure-capture-collision-result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert before and after==[],'Suspected deletion did not reproduce'
finally:
    foreign.release_pin(foreign_pin,cleanup_budget=0);foreign.close()
