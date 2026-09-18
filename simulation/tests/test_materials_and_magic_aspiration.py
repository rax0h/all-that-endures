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


def test_civilian_magic_interest_can_be_broad_without_forcing_every_user_to_full_path():
    w=generate_world(843001);Simulation(w).run(40)
    aspirations=list(w.magic_resources.aspirations.values())
    assert aspirations
    interested=[a for a in aspirations if a.desired_base_essences>0]
    assert interested
    assert any(not a.completion_goal for a in interested)
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


def test_absorbing_first_essence_does_not_force_ordinary_civilian_into_full_path():
    w=generate_world(843002);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    a=_aspiration(w,p);a.adventurer_aspiration=False;a.drive=.35;a.completion_goal=False;a.desired_base_essences=1;a.desired_abilities=5
    found=w.emit('test_essence_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='fire')
    r=w.magic_resources.create('essence','fire',ESSENCES['fire']['rarity'],w.year,p.settlement,'person',p.id,found.id)
    absorb_essence_resource(w,p.id,r.id)
    assert not a.completion_goal
    assert a.desired_base_essences==1
    assert a.desired_abilities==5


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


def test_ordinary_manifestations_stock_local_shops_even_without_seekers():
    w=generate_world(843006);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=16 and p.settlement==sid]
    assert people
    for p in people:
        w.magic_resources.aspirations[p.id]=MagicAspiration(.05,0,0,'test',w.year)
    before=len(w.magic_resources.inventory('settlement',sid,'essence'))
    added=__import__('ate_sim.magic_resources',fromlist=['_collect_ordinary_manifestations'])._collect_ordinary_manifestations(w,Simulation(w).rng,sid,people)
    stock=w.magic_resources.inventory('settlement',sid,'essence')
    assert added>0 and len(stock)==before+added
    assert all(str(r.rarity).lower() in ('common','uncommon') for r in stock[-added:])
    assert any(e.kind=='ordinary_essence_manifestations_collected' for e in w.events)


def test_real_civilian_work_can_create_magic_demand_without_named_profession():
    w=generate_world(843007);Simulation(w).run(1);sid=min(w.settlements)
    p=next(p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid)
    p.occupation='labor';p.curiosity=.8;p.inhibition=.8
    w.advancement.paths.pop(p.id,None)
    for skill in ('agriculture','construction','craft','knowledge','defense'):
        w.skills.get(p.id,skill).level=0.
    w.skills.get(p.id,'craft').level=2.0
    p.parents=()
    for other in list(w.social.neighbors(p.id)):
        w.social.edges[w.social.key(p.id,other)].attachment=0.
    a=MagicAspiration(.05,0,0,'capability',w.year,urgency=0.,risk_tolerance=.1)
    w.magic_resources.aspirations[p.id]=a
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,[p],adventure,magic)
    assert a.desired_base_essences>=1 and a.desired_abilities>=5
    assert a.reason=='craft capability'
    assert not a.completion_goal


def test_ordinary_manifestation_collection_is_shelf_bounded():
    w=generate_world(843008);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=16 and p.settlement==sid]
    mod=__import__('ate_sim.magic_resources',fromlist=['_collect_ordinary_manifestations'])
    rng=Simulation(w).rng
    first=mod._collect_ordinary_manifestations(w,rng,sid,people)
    second=mod._collect_ordinary_manifestations(w,rng,sid,people)
    assert first>0
    assert second==0


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


def test_generic_aspirant_does_not_accumulate_search_years_for_shop_access():
    w=generate_world(843012);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    w.advancement.paths.pop(p.id,None)
    a=MagicAspiration(.6,3,20,'ordinary access',w.year,urgency=.8)
    w.magic_resources.aspirations[p.id]=a
    Simulation(w).run(1)
    assert a.search_years==0


def test_social_exposure_and_ordinary_work_do_not_make_civilian_a_completionist():
    w=generate_world(843013);Simulation(w).run(1);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid][:5]
    assert len(people)>=2
    p=people[0];p.occupation='labor';p.curiosity=.55
    w.advancement.paths.pop(p.id,None)
    w.skills.get(p.id,'craft').level=1.5
    a=MagicAspiration(.55,1,5,'craft capability',w.year,completion_goal=False)
    w.magic_resources.aspirations[p.id]=a
    # Give several local contacts magic so social exposure is definitely present.
    for q in people[1:]:
        if w.advancement.path(q.id) is None:
            key=next(iter(ESSENCES));e=w.emit('test_social_user',Layer.REALITY,(Ref('person',q.id),),Ref('settlement',sid))
            rr=w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],w.year,sid,'person',q.id,e.id);absorb_essence_resource(w,q.id,rr.id)
        w.social.get(p.id,q.id).attachment=.8
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,people,adventure,magic)
    assert not a.completion_goal
    assert a.desired_base_essences==1
    assert a.desired_abilities==5


def test_high_commitment_civilian_can_choose_to_complete_after_starting_magic():
    w=generate_world(843014);Simulation(w).run(1);sid=min(w.settlements)
    p=next(p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid)
    p.occupation='labor';p.curiosity=1.;p.inhibition=0.
    w.advancement.paths.pop(p.id,None)
    a=MagicAspiration(.82,1,5,'curiosity',w.year,completion_goal=False)
    w.magic_resources.aspirations[p.id]=a
    key=next(iter(ESSENCES));e=w.emit('test_started_path',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid))
    rr=w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],w.year,sid,'person',p.id,e.id);absorb_essence_resource(w,p.id,rr.id)
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,[p],adventure,magic)
    assert a.completion_goal
    assert a.desired_base_essences==3
    assert a.desired_abilities==20


def test_magic_ecology_does_not_turn_started_ordinary_user_into_completionist():
    w=generate_world(843015);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    p.occupation='labor';w.advancement.paths.pop(p.id,None)
    a=MagicAspiration(.55,1,5,'ordinary access',w.year,completion_goal=False,adventurer_aspiration=False)
    w.magic_resources.aspirations[p.id]=a
    key=next(iter(ESSENCES));e=w.emit('test_started_ordinary_path',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement))
    rr=w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],w.year,p.settlement,'person',p.id,e.id)
    absorb_essence_resource(w,p.id,rr.id)
    from ate_sim.magic_resources import magic_ecology_step
    class FixedRNG:
        def stream(self,*args):return self
        def random(self):return .99
    magic_ecology_step(w,FixedRNG())
    assert not a.completion_goal
    assert a.desired_base_essences==1
    assert a.desired_abilities==5


def test_adventurer_intent_can_emerge_after_initial_aspiration_and_commits_full_path():
    w=generate_world(843016);Simulation(w).run(1);sid=min(w.settlements)
    p=next(p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid)
    p.curiosity=.85;p.inhibition=.15
    w.advancement.paths.pop(p.id,None)
    a=MagicAspiration(.68,1,5,'ordinary access',w.year,completion_goal=False,risk_tolerance=.9,adventurer_aspiration=False)
    w.magic_resources.aspirations[p.id]=a
    w.skills.get(p.id,'defense').level=1.2
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,[p],adventure,magic)
    assert a.adventurer_aspiration
    assert a.completion_goal
    assert a.desired_base_essences==3
    assert a.desired_abilities==20


def test_magical_parent_history_can_create_interest_after_parent_is_absent():
    w=generate_world(843017);Simulation(w).run(1);sid=min(w.settlements)
    people=[p for p in w.people.values() if p.alive and p.age>=18 and p.settlement==sid]
    assert len(people)>=2
    parent,p=people[:2]
    if w.advancement.path(parent.id) is None:
        key=next(iter(ESSENCES));e=w.emit('test_magical_parent',Layer.REALITY,(Ref('person',parent.id),),Ref('settlement',sid))
        rr=w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],w.year,sid,'person',parent.id,e.id)
        absorb_essence_resource(w,parent.id,rr.id)
    p.parents=(parent.id,);p.occupation='labor';p.curiosity=.45;p.inhibition=.60
    w.advancement.paths.pop(p.id,None)
    for skill in ('agriculture','construction','craft','knowledge','defense'):
        w.skills.get(p.id,skill).level=0.
    for other in list(w.social.neighbors(p.id)):
        w.social.edges[w.social.key(p.id,other)].attachment=0.
    w.magic_resources.aspirations[p.id]=MagicAspiration(.20,0,0,'capability',w.year,urgency=0.)
    parent.alive=False
    adventure,magic=magical_civ._institutional_capacity(w,sid)
    magical_civ._review_magic_demand(w,[p],adventure,magic)
    a=w.magic_resources.aspirations[p.id]
    assert a.desired_base_essences==1 and a.desired_abilities==5
    assert a.reason=='social magical exposure'
    assert not a.completion_goal
