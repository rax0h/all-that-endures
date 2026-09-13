import pytest
from simulation.ate_sim.agency import AgencyState, agency_step
from simulation.ate_sim.core import RNG
from simulation.tests.test_resource_transaction_eligibility import setup_market
from simulation.ate_sim import magic_resources as magic


def test_recorded_work_can_fund_a_full_price_stone_without_a_subsidy(monkeypatch):
    w,holder,poor,buyer,resource,cause=setup_market('awakening_stone')
    buyer.wealth=0
    original=AgencyState.choose
    def choose(self,world,p,rng,attachment=None,dependents=None):
        if p.id==buyer.id:return 'work','wealth',1.
        return original(self,world,p,rng,attachment,dependents)
    monkeypatch.setattr(AgencyState,'choose',choose)
    for _ in range(33):
        w.year+=1;agency_step(w,RNG(17))
    assert buyer.wealth==pytest.approx(3.96)
    assert not magic._transfer_to_seeker(w,resource,holder,[holder,buyer],RNG(17))
    w.year+=1;agency_step(w,RNG(17))
    seller_before=holder.wealth
    assert magic._transfer_to_seeker(w,resource,holder,[holder,buyer],RNG(17))
    assert buyer.wealth==pytest.approx(.08) and holder.wealth==pytest.approx(seller_before+4)
    assert resource.origin_event==cause.id and resource.consumed_year is None
    magic.use_awakening_stone(w,buyer.id,resource.id)
    assert resource.consumed_by==buyer.id
    assert sum(a.person==buyer.id and a.action=='work' for a in w.agency.actions)==34


def test_earnings_require_work_and_an_active_adult_and_scale_with_effort(monkeypatch):
    w,adult,child,dead,_,_=setup_market()
    adult.wealth=child.wealth=dead.wealth=0;child.age=15;dead.alive=False
    monkeypatch.setattr(AgencyState,'choose',lambda *args,**kwargs:('work','wealth',.5))
    agency_step(w,RNG(17))
    assert adult.wealth==pytest.approx(.06) and child.wealth==dead.wealth==0
    monkeypatch.setattr(AgencyState,'choose',lambda *args,**kwargs:('learn','curiosity',1.))
    agency_step(w,RNG(17))
    assert adult.wealth==pytest.approx(.06)
