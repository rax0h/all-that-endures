import gc
import weakref
import pytest
from ate_sim import rank_ecology as ecology
from ate_sim import persistence_history_runtime as records
from ate_sim.advancement import AbilityProgress
from ate_sim.core import RNG
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

@pytest.mark.parametrize('mode', ['normal', 'ceiling', 'exception', 'old_lease'])
def test_lifetime(tmp_path, monkeypatch, mode):
    def setup(world):
        configure(world)
        if mode == 'ceiling':
            for a in world.advancement.path(1).abilities: a.rank=5
    path,pair=ranked_fixture(tmp_path,size=4,configure=setup)
    refs={}
    original=records.RecursiveHistoryRuntime.load_record
    def observed(self,value):
        result=original(self,value)
        if isinstance(result,AbilityProgress):refs[id(result)]=weakref.ref(result)
        return result
    monkeypatch.setattr(records.RecursiveHistoryRuntime,'load_record',observed)
    with fast_open(path,pair) as session:
        if mode=='old_lease':
            held=session.world.advancement.path(1).abilities[0]
            child=held.response_model
            session.world.people[1].wealth+=.25
            session.save()
            assert held is session.world.advancement.path(1).abilities[0]
            assert held.response_model is child
        if mode=='exception':
            def fail(*args,**kwargs):raise RuntimeError('review fault')
            monkeypatch.setattr(ecology,'_career_training',fail)
            try:ecology.rank_ecology_step(session.world,RNG(32))
            except RuntimeError:pass
            else:assert False
        else:ecology.rank_ecology_step(session.world,RNG(32))
        if mode=='old_lease':
            assert held is session.world.advancement.path(1).abilities[0]
            assert held.response_model is child
            session.save()
            del held,child
        gc.collect()
        alive=[r() for r in refs.values() if r() is not None]
        # Dirty bodies have their ordinary publication lifetime; clean bodies
        # must not be held by the annual caller after return or unwinding.
        clean=[a for a in alive if records.record_backing(a)._dirty_record is None]
        assert not clean
        print(mode, 'observed',len(refs),'alive',len(alive),'clean',len(clean))

@pytest.mark.parametrize('damage',['corrupt','released'])
def test_source_boundary(tmp_path,damage):
    from ate_sim.incremental_store import StoreError
    path,pair=ranked_fixture(tmp_path,size=4,configure=configure)
    with fast_open(path,pair) as session:
        if damage=='corrupt':
            session.store.db.execute("UPDATE lazy_record_versions SET payload=? WHERE namespace=?",(b'broken','aux.lazy.records.headers'))
            session.store.db.commit()
        else:session.store.release_pin(session.pin,cleanup_budget=0)
        with pytest.raises(StoreError):ecology.rank_ecology_step(session.world,RNG(32))
