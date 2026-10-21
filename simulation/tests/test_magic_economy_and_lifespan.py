import math
import pytest
from ate_sim.currency import RankedCurrencyState
from ate_sim.rank import profile,annual_mortality,biological_age,cognition
from test_magic_understanding import configured_world
from ate_sim.threat_ecology import MagicalThreat,threat_ecology_step
from ate_sim.core import Layer,Ref


class ResolutionRNG:
    def stream(self,*args):
        class Draws:
            first=True
            def random(self):
                if self.first:self.first=False;return .99
                return 0.
        return Draws()


def test_tiered_transfers_conserve_each_denomination_without_minting():
    state=RankedCurrencyState()
    state.credit(1,{'diamond':2,'iron':10})
    minted=dict(state.minted)
    state.transfer(1,2,{'diamond':1})
    assert state.wallets[1]=={'diamond':1,'iron':10}
    assert state.wallets[2]=={'diamond':1}
    assert state.minted==minted
    with pytest.raises(ValueError):state.transfer(2,1,{'iron':1})
    assert state.wallets[2]=={'diamond':1}


def test_diamond_is_ageless_but_environment_is_not_harmless():
    assert profile(5).rank==5 and profile(5)!=profile(4)
    assert annual_mortality(10000,5)==0
    assert annual_mortality(10000,5,1.,1.)>0
    assert annual_mortality(700,4)>0


def test_ordinary_lifespan_has_a_finite_survival_tail_and_advancement_rejuvenates():
    survival=math.prod(1-annual_mortality(age,0) for age in range(18,150))
    assert survival<.00001
    ages=[biological_age(100,r) for r in range(6)]
    assert all(a>b for a,b in zip(ages,ages[1:]))
    assert cognition(5).magical_modeling>cognition(4).magical_modeling


def test_threat_gap_cannot_stack_into_two_tiers_and_harvest_retains_rank():
    world,p,path=configured_world()
    p.age=40;p.curiosity=1.;p.inhibition=0.;p.wealth=100.
    for a in path.abilities:a.rank=3
    p.rank=3
    origin=world.emit('ranked_magic_manifested',Layer.REALITY,location=Ref('settlement',p.settlement),rank=5)
    threat=MagicalThreat(1,'monster',5,p.settlement,0,1.,origin_event=origin.id,form='test predator')
    world.threat_ecology.threats[1]=threat
    threat_ecology_step(world,ResolutionRNG())
    assert threat.status=='active'
    for a in path.abilities:a.rank=4
    p.rank=4
    threat_ecology_step(world,ResolutionRNG())
    assert threat.status=='resolved'
    harvested=next(e for e in world.events if e.kind=='monster_remains_harvested')
    assert harvested.data['material_rank']==5
    assert harvested.data['valuation_denomination']=='diamond'
    assert harvested.causes==(world.threat_ecology.resolutions[origin.id],)
    lot=next(l for l in world.materials.lots.values() if l.origin_event==harvested.id)
    assert lot.material_rank==5 and lot.owner_id==p.id
    assert world.currency.wallets=={} # physical harvesting is not a magical coin loot power
