from collections import Counter
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.magic_resources import _aspiration,absorb_essence_resource,MagicAspiration
from ate_sim.semantic_dictionary import ESSENCES
from ate_sim import magical_civilization as magical_civ
from unittest.mock import patch
from ate_sim.core import Layer,Ref


def test_material_crafting_consumes_real_produced_lots():
    w=generate_world(843000);Simulation(w).run(30)
    assert w.materials.lots
    for item in w.materials.items.values():
        assert item.materials
        for lid in item.materials:
            lot=w.materials.lots[lid]
            assert lot.origin_event in w.event_ids
            assert lot.consumed>0
            assert item.created_year>=lot.created_year


def test_material_production_is_not_fixed_one_lot_per_settlement_year():
    w=generate_world(843000);Simulation(w).run(40)
    produced=[e for e in w.events if e.kind=='material_produced']
    assert produced
    by_year_settlement=Counter((e.year,e.location.id) for e in produced if e.location is not None)
    assert any(count>1 for count in by_year_settlement.values())
    assert len(produced)!=40*len(w.settlements)


def test_civilian_magic_interest_can_be_broad_while_serious_aspirants_skew_to_completion():
    w=generate_world(843001);Simulation(w).run(40)
    aspirations=list(w.magic_resources.aspirations.values())
    assert aspirations
    interested=[a for a in aspirations if a.desired_base_essences>0]
    assert interested
    assert sum(a.completion_goal for a in interested)>len(interested)/2
    assert all(a.desired_base_essences==3 and a.desired_abilities==20 for a in interested if a.completion_goal)
    assert all(a.completion_goal for a in interested if a.adventurer_aspiration)


def test_adventurer_aspirant_treats_full_configuration_as_the_goal():
    w=generate_world(843004);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    p.occupation='adventurer';p.curiosity=.95;p.inhibition=.1
    w.magic_resources.aspirations.pop(p.id,None)
    a=_aspiration(w,p)
    assert a.adventurer_aspiration
    assert a.completion_goal
    assert a.desired_base_essences==3
    assert a.desired_abilities==20
    assert a.urgency>=.55


def test_absorbing_first_essence_turns_committed_interest_into_full_completion_goal():
    w=generate_world(843002);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    a=_aspiration(w,p);a.drive=.35;a.completion_goal=False;a.desired_base_essences=1;a.desired_abilities=5
    found=w.emit('test_essence_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='fire')
    r=w.magic_resources.create('essence','fire',ESSENCES['fire']['rarity'],w.year,p.settlement,'person',p.id,found.id)
    absorb_essence_resource(w,p.id,r.id)
    assert a.completion_goal
    assert a.desired_base_essences==3
    assert a.desired_abilities==20


def test_transcendent_craft_cannot_be_randomly_rolled_by_mortal():
    w=generate_world(843002);Simulation(w).run(60)
    for item in w.materials.items.values():
        if item.rarity=='transcendent':
            assert w.metaphysics.soul(item.craftsperson).ontology!='mortal'


def test_supply_signal_measures_real_seekers_against_literal_shelf_stock():
    w=generate_world(843005);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid][:3]
    assert len(people)==3
    for p in people:
        w.advancement.paths.pop(p.id,None)
        w.magic_resources.aspirations[p.id]=MagicAspiration(.6,1,5,'test',0)
    common=next(k for k,v in ESSENCES.items() if str(v['rarity']).lower()=='common')
    w.magic_resources.create('essence',common,ESSENCES[common]['rarity'],0,sid,'settlement',sid)
    seekers,stock,pressure=magical_civ._essence_supply_signal(w,people,sid)
    assert (seekers,stock)==(3,1)
    assert pressure==2/3


def test_shortage_response_expedition_can_replenish_shop_with_existing_resource():
    w=generate_world(843006);Simulation(w).run(1);sid=min(w.settlements)
    people=magical_civ._living(w,sid)
    assert people
    for p in people:
        a=_aspiration(w,p);a.desired_base_essences=max(a.desired_base_essences,3)
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    assert adventure is not None or magic is not None
    w.ambient_magic.field(sid).level=1.2
    settlement=w.settlements[sid];w.cells[(settlement.x,settlement.y)].hazard=1.
    common=next(k for k,v in ESSENCES.items() if str(v['rarity']).lower()=='common')
    class ZeroRNG:
        def stream(self,*args):return self
        def random(self):return 0.
    def make_resource(world,rng,place,finder,kind=None,cause=None,method='test'):
        e=world.emit('test_supply_find',Layer.REALITY,(Ref('person',finder.id),),Ref('settlement',place),(() if cause is None else (cause,)))
        return world.magic_resources.create('essence',common,ESSENCES[common]['rarity'],world.year,place,'person',finder.id,e.id)
    before=len(w.magic_resources.inventory('settlement',sid,'essence'))
    with patch.object(magical_civ,'_make_resource',side_effect=make_resource):
        magical_civ._expedition_step(w,ZeroRNG(),sid,people,magical_civ._practitioners(w,people),adventure,magic)
    after=w.magic_resources.inventory('settlement',sid,'essence')
    assert len(after)>before
    assert any(e.kind=='essence_source_harvested' for e in w.events)
    assert all(r.origin_event in w.event_ids for r in after)


def test_real_civilian_work_can_create_magic_demand_without_named_profession():
    w=generate_world(843007);Simulation(w).run(1);sid=min(w.settlements)
    p=next(p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid)
    p.occupation='labor';w.skills.get(p.id,'craft').level=1.5
    p.parents=()
    for other in list(w.social.neighbors(p.id)):
        w.social.edges[w.social.key(p.id,other)].attachment=0.
    a=MagicAspiration(.05,0,0,'capability',w.year,urgency=0.)
    w.magic_resources.aspirations[p.id]=a
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,[p],adventure,magic)
    assert a.desired_base_essences>=1 and a.desired_abilities>=5
    assert a.reason=='craft capability'


def test_common_source_harvest_is_bounded_even_under_full_shortage():
    w=generate_world(843008);Simulation(w).run(1);sid=min(w.settlements)
    people=magical_civ._living(w,sid)
    for p in people:
        a=_aspiration(w,p);a.desired_base_essences=max(a.desired_base_essences,3)
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    w.ambient_magic.field(sid).level=1.2
    settlement=w.settlements[sid];w.cells[(settlement.x,settlement.y)].hazard=1.
    common=next(k for k,v in ESSENCES.items() if str(v['rarity']).lower()=='common')
    class ZeroRNG:
        def stream(self,*args):return self
        def random(self):return 0.
    def make_resource(world,rng,place,finder,kind=None,cause=None,method='test'):
        e=world.emit('test_supply_find',Layer.REALITY,(Ref('person',finder.id),),Ref('settlement',place),(() if cause is None else (cause,)))
        return world.magic_resources.create('essence',common,ESSENCES[common]['rarity'],world.year,place,'person',finder.id,e.id)
    with patch.object(magical_civ,'_make_resource',side_effect=make_resource):
        magical_civ._expedition_step(w,ZeroRNG(),sid,people,magical_civ._practitioners(w,people),adventure,magic)
    harvests=[e for e in w.events if e.kind=='essence_source_harvested']
    assert harvests and all(1<=e.data['quantity']<=5 for e in harvests)


def test_social_exposure_does_not_make_low_openness_civilian_automatically_seek_magic():
    w=generate_world(843009);Simulation(w).run(1);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid]
    p=people[0];p.occupation='labor';p.curiosity=.05;p.attachment=.20;p.parents=()
    w.advancement.paths.pop(p.id,None)
    for skill in ('agriculture','construction','craft','knowledge','defense'):
        w.skills.get(p.id,skill).level=0.
    a=MagicAspiration(.05,0,0,'capability',w.year,urgency=0.)
    w.magic_resources.aspirations[p.id]=a
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,[p],adventure,magic)
    assert a.desired_base_essences==0


def test_external_pressure_raises_urgency_only_for_existing_seeker():
    w=generate_world(843010);Simulation(w).run(1);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid][:2]
    assert len(people)==2
    seeker,uninterested=people
    w.advancement.paths.pop(seeker.id,None);w.advancement.paths.pop(uninterested.id,None)
    w.magic_resources.aspirations[seeker.id]=MagicAspiration(.40,1,5,'test',w.year,urgency=.20,compromise_tolerance=.20)
    w.magic_resources.aspirations[uninterested.id]=MagicAspiration(.20,0,0,'test',w.year,urgency=0.)
    w.settlements[sid].memory['monster_surge']=.8
    magical_civ._apply_external_magic_pressure(w,sid,people,[])
    assert w.magic_resources.aspirations[seeker.id].urgency>.20
    assert w.magic_resources.aspirations[seeker.id].compromise_tolerance>.20
    assert w.magic_resources.aspirations[uninterested.id].desired_base_essences==0
    assert w.magic_resources.aspirations[uninterested.id].urgency==0.


def test_first_essence_event_records_active_search_delay_and_age():
    w=generate_world(843011);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    w.advancement.paths.pop(p.id,None)
    a=_aspiration(w,p);a.desired_base_essences=1;a.search_years=9;a.urgency=.77
    found=w.emit('test_first_essence',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='fire')
    resource=w.magic_resources.create('essence','fire',ESSENCES['fire']['rarity'],w.year,p.settlement,'person',p.id,found.id)
    absorb_essence_resource(w,p.id,resource.id)
    event=next(e for e in reversed(w.events) if e.kind=='essence_absorbed')
    assert event.data['first_essence'] is True
    assert event.data['search_years']==9
    assert event.data['age']==p.age
    assert event.data['urgency']==.77


def test_urgent_first_access_seeker_is_not_excluded_from_expeditions_by_existing_users():
    w=generate_world(843012);Simulation(w).run(1);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid][:3]
    assert len(people)==3
    seeker=people[0]
    w.advancement.paths.pop(seeker.id,None)
    a=_aspiration(w,seeker);a.desired_base_essences=1;a.urgency=.9;a.risk_tolerance=.8;a.search_years=12
    users=[p for p in people[1:] if w.advancement.path(p.id) is not None]
    if not users:
        # Give one comparison resident an existing path through a real owned essence.
        u=people[1];key=next(iter(ESSENCES));e=w.emit('test_existing_user',Layer.REALITY,(Ref('person',u.id),),Ref('settlement',sid))
        rr=w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],w.year,sid,'person',u.id,e.id);absorb_essence_resource(w,u.id,rr.id);users=[u]
    first,candidates=magical_civ._expedition_candidates(w,people,users,[],1.0)
    assert seeker in first and seeker in candidates
    assert any(p.id in {u.id for u in users} for p in candidates)
