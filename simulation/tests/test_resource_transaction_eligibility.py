from copy import deepcopy
import pytest
from simulation.ate_sim import generate_world
from simulation.ate_sim import magic_resources as magic
from simulation.ate_sim import magic_trade
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


def test_full_path_aspirant_buys_and_absorbs_all_three_affordable_bases_in_one_visit():
    w,h,poor,buyer,_,_=setup_market()
    w.people={buyer.id:buyer};buyer.wealth=10
    a=magic._aspiration(w,buyer);a.desired_base_essences=3;a.desired_abilities=20;a.completion_goal=True
    w.magic_resources.resources.clear();w.magic_resources.owner_index.clear()
    stock=[w.magic_resources.create('essence',ESSENCE_IDS[i],'common',0,buyer.settlement,'settlement',buyer.settlement) for i in range(3)]
    magic_trade._retail_browse(w,{buyer.settlement:[buyer]})
    path=w.advancement.path(buyer.id)
    assert path is not None and len(path.base_essences)==3
    assert all(resource.consumed_by==buyer.id for resource in stock)
    assert buyer.wealth==pytest.approx(7)
    assert sum(e.kind=='magic_resource_purchased' for e in w.events)==3


def test_failed_shop_purchase_leaves_stock_for_later_buyer():
    w,h,poor,buyer,_,_=setup_market()
    w.people={p.id:p for p in (h,poor,buyer)}
    h.wealth=poor.wealth=buyer.wealth=0
    w.magic_resources.resources.clear();w.magic_resources.owner_index.clear()
    resource=w.magic_resources.create('essence',ESSENCE_IDS[0],'common',0,h.settlement,'settlement',h.settlement)
    magic_trade._retail_browse(w,{h.settlement:[h,poor,buyer]})
    assert resource.owner_kind=='settlement' and not resource.transfers
    buyer.wealth=1
    magic_trade._retail_browse(w,{h.settlement:[h,poor,buyer]})
    assert resource.owner_kind=='person' and resource.owner_id==buyer.id
    assert buyer.wealth==0


def test_civilian_essence_prices_put_rarity_not_basic_access_on_the_curve():
    class R:
        kind='essence'
        def __init__(self,rarity):self.rarity=rarity
    prices=[magic_trade._retail_price(R(r)) for r in ('common','uncommon','Rare','Epic','Legendary','Mythic','Transcendent')]
    assert prices==sorted(prices)
    assert prices[0]==1 and prices[1]==1.5 and prices[-1]==21


def test_transfer_is_deterministic_with_affordable_candidates():
    w,h,poor,buyer,r,_=setup_market();other=deepcopy(w)
    magic._transfer_to_seeker(w,r,h,[h,poor,buyer],RNG(17))
    magic._transfer_to_seeker(other,other.magic_resources.resources[r.id],other.people[h.id],[other.people[p.id] for p in (h,poor,buyer)],RNG(17))
    assert w.digest()==other.digest()


def test_urgent_long_waiting_shopper_arrives_before_low_urgency_shopper():
    w,h,poor,buyer,_,_=setup_market()
    w.people={p.id:p for p in (h,buyer)}
    h.wealth=buyer.wealth=10
    ah=magic._aspiration(w,h);ab=magic._aspiration(w,buyer)
    ah.desired_base_essences=ab.desired_base_essences=1
    ah.urgency=.10;ah.drive=.10;ah.preparation=0.;ah.search_years=0
    ab.urgency=.95;ab.drive=.60;ab.preparation=.40;ab.search_years=20
    w.magic_resources.resources.clear();w.magic_resources.owner_index.clear()
    r=w.magic_resources.create('essence',ESSENCE_IDS[0],'common',0,h.settlement,'settlement',h.settlement)
    class SameArrival:
        def stream(self,*args):return self
        def random(self):return .5
    magic_trade._retail_browse(w,{h.settlement:[h,buyer]},SameArrival())
    assert r.owner_kind=='person' and r.owner_id==buyer.id
