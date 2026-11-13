from dataclasses import replace
import pytest
from ate_sim import persistence_history_retirement as producer
from ate_sim import persistence_proof_world as proof
from ate_sim import persistence_proof_manifest_publish as manifests
from ate_sim.persistence_record_headers import NAMESPACE as RECORDS
from ate_sim.persistence_lazy_families import ParticipantDelta
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES
from ate_sim.mastery_training import ResponseModel
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_record_runtime import record_backing
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture,fast_open

@pytest.mark.parametrize('damage',['omit-initial','omit-background-descriptor','omit-background-dependency','omit-background-job','delete-live-target','jump-initial'])
def test_reject_frozen_retirement_tamper(tmp_path,monkeypatch,damage):
    path,pair=ranked_fixture(tmp_path,size=4,configure=configure)
    if damage.startswith('omit-background'):
        with fast_open(path,pair) as s:
            s.world.advancement.path(1).abilities[0].response_model=ResponseModel()
            s.save();pair=s.proof_manifest
    with fast_open(path,pair) as s:
        a=s.world.advancement.path(1).abilities[0]
        live_inc=record_backing(a.response_model)._incarnation
        if not damage.startswith('omit-background'):
            a.response_model=ResponseModel()
        else:
            s.world.people[1].wealth+=.125
        original=producer.prepare_world_retirement_delta
        seen=[]
        def corrupt(*args,**kw):
            d=original(*args,**kw);v,o,i=d.decode(args[0].codec);v=list(v)
            if damage=='omit-initial':
                v=[c for c in v if c.namespace!=producer.NAMESPACE]
            elif damage.startswith('omit-background'):
                ns={'omit-background-descriptor':RECORDS,'omit-background-dependency':DEPENDENCIES,'omit-background-job':producer.NAMESPACE}[damage]
                assert any(c.namespace==ns and c.delete for c in v),(damage,v)
                v=[c for c in v if c.namespace!=ns]
            elif damage=='delete-live-target':
                b=s.world.advancement.path(1).abilities[1].response_model
                inc=record_backing(b)._incarnation
                v.extend([VersionChange(RECORDS,(inc,0),delete=True),VersionChange(DEPENDENCIES,inc,delete=True)])
            elif damage=='jump-initial':
                v=[replace(c,value=(c.value[0],c.value[1],1,c.value[3],True)) if c.namespace==producer.NAMESPACE else c for c in v]
            seen.append(True)
            return ParticipantDelta.freeze(args[0].codec,'history-retirement',version_changes=v,ordinary_changes=o,identity_changes=i)
        old=s.pin.captured_head
        with monkeypatch.context() as m:
            m.setattr(producer,'prepare_world_retirement_delta',corrupt)
            with pytest.raises(StoreError) as error:s.save()
            print('REJECTION',damage,repr(error.value),'STATE',s._state,'AUTHORITY',getattr(s._proof_save_authority,'uncertain',None) if hasattr(s,'_proof_save_authority') else 'unknown',flush=True)
        assert seen
        assert s.store.db.execute('select generation from save_head').fetchone()==(old,)
        assert s.resolve_save()==old
        s.save()
