from copy import deepcopy
from unittest.mock import patch
from ate_sim.advancement import AdvancementState
from ate_sim.currency import COIN_VALUE,value_of
from ate_sim.magic_economy import _farm_output,spirit_economy_step
from ate_sim.core import RNG
from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world
from test_high_rank_economy import economy_world


def test_farm_output_obeys_demand_and_capacity():
    for tier in range(1,6):
        native=('lesser','iron','bronze','silver','gold','diamond')[tier]
        for demand in ({},{'iron':24},{'iron':9999,'bronze':20,'silver':7}):
            out=_farm_output(tier,24,demand,{})
            assert 0<value_of(out)<=24*COIN_VALUE[native]
            assert all(COIN_VALUE[d]<=COIN_VALUE[native] for d in out)
    assert _farm_output(5,24,{},{} )=={'diamond':24}
    assert _farm_output(5,24,{'iron':24},{'iron':24})=={'diamond':24}
    assert _farm_output(5,24,{'iron':24},{})=={'iron':48,'diamond':23}


def test_real_contract_requests_worked_coin_supply():
    w,p,_,adv=economy_world()
    b=w.institutions.branch_for('adventure_society',p.settlement)
    n=w.institutions.post_notice(b.id,0,'test_work',p.settlement,1);n.required_rank=1
    spirit_economy_step(w,RNG(7))
    assert w.currency.treasuries[adv.id]['iron']>=4
    e=next(e for e in w.events if e.kind=='spirit_coins_cultivated')
    assert e.data['capacity_rank']==5
    assert value_of(e.data['coin_created'])<=24*COIN_VALUE['diamond']
    assert sum(v.get('iron',0) for v in w.currency.wallets.values())+sum(v.get('iron',0) for v in w.currency.treasuries.values())==w.currency.minted['iron']


def test_training_batch_preserves_mid_session_advancement():
    state=AdvancementState()
    for essence in ('fire','water','wind'):state.absorb_essence(1,essence,0)
    for essence in state.path(1).essences:
        for _ in range(4):state.awaken_skill(1,'eyes',0,target_essence=essence)
    for a in state.path(1).abilities:a.level=9;a.progress=.99
    reference=deepcopy(state);session=state.practice_batch(1)
    for i in list(range(20))+[0,19]:
        session.practice(i,2.,.5);reference.practice(1,i,2.,.5)
        assert state==reference and session.rank==state.rank(1)
    assert state.rank(1)==2 and state.path(1).abilities[0].progress>0
    state.path(1).abilities.pop();session=state.practice_batch(1)
    session.practice(0,1000.,1000.)
    assert session.rank==0 and state.rank(1)==0


def test_inventory_selection_cache_tracks_mutations_and_is_not_checkpoint_state():
    from ate_sim.magic_resources import _circulation_stock,_wants
    from ate_sim.checkpoint import dumps,loads
    w=generate_world(843000,mature=True);p=next(p for p in w.people.values() if p.age>=18)
    def verify():
        held=[r for r in w.magic_resources.resources.values() if r.owner_kind=='person' and r.owner_id==p.id and r.consumed_year is None]
        assert w.magic_resources.inventory('person',p.id)==held
        e,s,x=_circulation_stock(w,p)
        assert e==[r for r in held if r.kind=='essence' and _wants(w,p,r)]
        assert s==[r for r in held if r.kind=='awakening_stone' and _wants(w,p,r)]
        assert x==[r for r in held if not _wants(w,p,r)]
    verify()
    for kind,key in [('essence','fire'),('awakening_stone','eyes')]:
        r=w.magic_resources.create(kind,key,'common',0,p.settlement,'person',p.id);verify()
        w.magic_resources.transfer(r.id,'settlement',p.settlement,1);verify()
        w.magic_resources.transfer(r.id,'person',p.id,1);verify()
        w.magic_resources.consume(r.id,p.id,0,1);verify()
    other=loads(dumps(w));assert other.digest()==w.digest()
    assert not any(k.startswith('_query_') for k in other.magic_resources.__dict__)


def test_optimized_training_and_stock_match_uncached_history():
    from ate_sim import magic_resources as resources
    indexed=Simulation(generate_world(843001,mature=True)).run(100)
    def inventory(self,owner_kind,owner_id,kind=None):
        return [self.resources[i] for i in sorted(self.owner_index.get((owner_kind,owner_id),())) if self.resources[i].consumed_year is None and (kind is None or self.resources[i].kind==kind)]
    def stock(world,p):
        held=inventory(world.magic_resources,'person',p.id)
        return ([r for r in held if r.kind=='essence' and resources._wants(world,p,r)],[r for r in held if r.kind=='awakening_stone' and resources._wants(world,p,r)],[r for r in held if not resources._wants(world,p,r)])
    class Direct:
        def __init__(self,state,pid):self.state=state;self.pid=pid;self.rank=state.rank(pid)
        def practice(self,i,use,reflection=0.):return self.state.practice(self.pid,i,use,reflection)
    with patch.object(resources.MagicResourceState,'inventory',inventory),patch.object(resources,'_circulation_stock',stock),patch.object(AdvancementState,'practice_batch',lambda state,pid:Direct(state,pid)):
        reference=Simulation(generate_world(843001,mature=True)).run(100)
    assert indexed.digest()==reference.digest()


def test_gold_workload_does_not_bypass_understanding():
    from ate_sim.rank_ecology import _career_training
    from ate_sim.magic_resources import _aspiration
    w,p,path,adv=economy_world()
    for a in path.abilities:a.rank=4
    p.rank=4;a=_aspiration(w,p);a.urgency=a.drive=1.;p.curiosity=1.
    _,_,uses,_=_career_training(w,p,path,a,True,1.)
    assert 9<=uses<=14
    assert all(not ability.understanding.ready(4) for ability in path.abilities)


def test_collection_policy_restores_caller_state_on_failure():
    import gc
    import pytest
    simulation=Simulation(generate_world(17));enabled=gc.isenabled()
    try:
        for original in (True,False):
            (gc.enable if original else gc.disable)()
            with patch.object(simulation,'step',side_effect=RuntimeError('test failure')):
                with pytest.raises(RuntimeError):simulation.run(1)
            assert gc.isenabled()==original
    finally:(gc.enable if enabled else gc.disable)()


def test_focused_gold_work_does_not_waste_sessions_on_diamond_abilities():
    from ate_sim.rank_ecology import rank_ecology_step
    from ate_sim.magic_resources import _aspiration
    from ate_sim import rank_ecology
    w,p,path,adv=economy_world()
    for ability in path.abilities:ability.rank=5
    path.abilities[-1].rank=4;p.rank=4
    aspiration=_aspiration(w,p);aspiration.drive=aspiration.urgency=1.;p.curiosity=1.
    used=[]
    original=rank_ecology.practice_ability
    def capture(world,person,index,*args,**kwargs):
        if person.id==p.id:used.append(index)
        return original(world,person,index,*args,**kwargs)
    with patch.object(rank_ecology,'practice_ability',capture):rank_ecology_step(w,RNG(92))
    assert used==[19]
    assert p.rank==4


def test_solved_trials_wait_for_integration_without_creating_more_exposure():
    from ate_sim.mastery_training import trial,needs_trial
    w,p,path,_=economy_world();a=path.abilities[0];a.rank=4;p.curiosity=p.health=1.
    for year in range(30):trial(w,p,a,RNG(83).stream('trial',year,p.id))
    assert a.response_model.coefficients and len(a.understanding.applications)==6
    assert not needs_trial(a) and not a.understanding.ready(4)
    count=len(w.events)
    for year in range(30,80):trial(w,p,a,RNG(83).stream('trial',year,p.id))
    assert len(w.events)==count and a.rank==4
    a.understanding.reflect(100,100)
    assert needs_trial(a)
    for year in range(80,100):trial(w,p,a,RNG(83).stream('trial',year,p.id))
    assert a.understanding.ready(4) and len(a.understanding.transfers)==2
    assert a.rank==4  # proofs still do not bypass ability development


def test_gc_schedule_preserves_history():
    reference=Simulation(generate_world(39,mature=True))
    with patch('gc.isenabled',return_value=False):reference.run(40)
    actual=Simulation(generate_world(39,mature=True)).run(40)
    assert actual.digest()==reference.w.digest()


def test_scoped_rank_cache_tracks_awakening_and_mid_session_advancement():
    import pickle
    from ate_sim.advancement import AdvancementState
    state=AdvancementState()
    with state.rank_scope():
        assert state.rank(1)==0
        for essence in ('fire','water','wind'):state.absorb_essence(1,essence,0)
        path=state.path(1)
        for essence in path.essences:
            for _ in range(4):state.awaken_skill(1,'eyes',1,target_essence=essence)
        assert state.rank(1)==1
        assert '_rank_cache' not in pickle.loads(pickle.dumps(state)).__dict__
        with state.rank_scope():
            batch=state.practice_batch(1)
            for i in range(20):batch.practice(i,100.)
            assert state.rank(1)==2
        assert state.rank(1)==2
    path.abilities[0].rank=1
    assert state.rank(1)==1  # direct fixture/checkpoint edits outside a step
