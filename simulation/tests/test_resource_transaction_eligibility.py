from copy import deepcopy
import pytest
from simulation.ate_sim import generate_world
from simulation.ate_sim import magic_resources as magic
from simulation.ate_sim.core import RNG, Layer, Ref
from simulation.ate_sim.semantic_dictionary import ESSENCE_IDS, STONE_IDS


def setup_market(kind='essence', rarity='common'):
    w=generate_world(17)
    holder,poor,buyer=[p for p in w.people.values() if p.age>=18][:3]
    for p in (holder,poor,buyer):
        p.settlement=holder.settlement
        w.advancement.paths.pop(p.id,None)
        w.magic_resources.aspirations[p.id]=magic.MagicAspiration(.7,3,20,'test',0,urgency=.9 if p is poor else .6)
        if kind=='awakening_stone':w.advancement.absorb_essence(p.id,ESSENCE_IDS[0],0)
    holder.wealth=5;poor.wealth=0;buyer.wealth=50
    cause=w.emit('magic_resource_discovered',Layer.REALITY,location=Ref('settlement',holder.settlement))
    key=ESSENCE_IDS[0] if kind=='essence' else STONE_IDS[0]
    r=w.magic_resources.create(kind,key,rarity,0,holder.settlement,'person',holder.id,cause.id)
    return w,holder,poor,buyer,r,cause


@pytest.mark.parametrize('kind,rarity,price',[('essence','common',8),('awakening_stone','common',4),('essence','Rare',10.8)])
def test_affordable_alternative_pays_full_price_and_can_use_resource(kind,rarity,price):
    w,h,poor,buyer,r,cause=setup_market(kind,rarity)
    refreshed=[]
    assert magic._transfer_to_seeker(w,r,h,[h,poor,buyer],RNG(17),refreshed.append)
    assert r.owner_id==buyer.id and r.owner_kind=='person'
    assert buyer.wealth==pytest.approx(50-price) and h.wealth==pytest.approx(5+price)
    assert poor.wealth==0 and refreshed==[buyer]
    trade=next(e for e in w.events if e.id==r.transfers[-1])
    assert trade.data['price']==pytest.approx(price) and trade.data['reason']=='aspirant purchase'
    assert cause.id in trade.causes and r.origin_event==cause.id
    assert r.consumed_year is None
    if kind=='essence':magic.absorb_essence_resource(w,buyer.id,r.id)
    else:magic.use_awakening_stone(w,buyer.id,r.id)
    assert r.consumed_by==buyer.id and r.consumed_event is not None
    assert w.magic_resources.resources[r.id] is r  # The consumed archive remains.


def test_no_affordable_buyer_does_not_move_stock_money_or_create_relationships():
    w,h,poor,buyer,r,_=setup_market();buyer.wealth=7.99
    before=(len(w.events),len(w.social.edges),h.wealth,buyer.wealth)
    assert not magic._transfer_to_seeker(w,r,h,[h,poor,buyer],RNG(17))
    assert before==(len(w.events),len(w.social.edges),h.wealth,buyer.wealth)
    assert r.owner_id==h.id and not r.transfers and r.consumed_year is None


def test_existing_relationship_gift_and_seeker_priority_are_preserved():
    w,h,poor,buyer,r,_=setup_market();w.social.get(h.id,poor.id).attachment=.8
    assert magic._transfer_to_seeker(w,r,h,[h,poor,buyer],RNG(17))
    assert r.owner_id==poor.id and h.wealth==5 and buyer.wealth==50 and poor.wealth==0
    assert w.events[-1].data['reason']=='relationship gift'


def test_affordability_does_not_bypass_essence_compatibility():
    w,h,poor,buyer,r,_=setup_market();w.advancement.absorb_essence(buyer.id,r.key,0)
    assert not magic._transfer_to_seeker(w,r,h,[h,poor,buyer],RNG(17))
    assert r.owner_id==h.id


def test_settlement_cache_falls_through_after_first_buyer_spends_their_money():
    w,h,poor,buyer,_,_=setup_market()
    w.people={p.id:p for p in (h,poor,buyer)}
    h.wealth=7;buyer.wealth=14
    w.magic_resources.aspirations[h.id].urgency=.8
    w.magic_resources.resources.clear();w.magic_resources.owner_index.clear()
    stock=[w.magic_resources.create('essence',ESSENCE_IDS[0],'common',0,h.settlement,'settlement',h.settlement) for _ in range(4)]
    class NoRandomActions:
        def stream(self,*args):return self
        def random(self):return 1.
    magic.magic_ecology_step(w,NoRandomActions())
    assert [r.owner_id for r in stock[:3]]==[h.id,buyer.id,buyer.id]
    assert stock[3].owner_kind=='settlement'
    assert h.wealth==buyer.wealth==poor.wealth==0
    assert sum(e.kind=='magic_resource_purchased' for e in w.events)==3


def test_transfer_is_deterministic_with_affordable_candidates():
    w,h,poor,buyer,r,_=setup_market();other=deepcopy(w)
    magic._transfer_to_seeker(w,r,h,[h,poor,buyer],RNG(17))
    magic._transfer_to_seeker(other,other.magic_resources.resources[r.id],other.people[h.id],[other.people[p.id] for p in (h,poor,buyer)],RNG(17))
    assert w.digest()==other.digest()
