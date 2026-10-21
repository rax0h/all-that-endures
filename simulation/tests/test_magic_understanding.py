from ate_sim.advancement import AdvancementState,Understanding
from ate_sim.worldgen import generate_world
from ate_sim.core import Layer,Ref
from ate_sim.magic_progression import practice_ability,record_application
from ate_sim.rank_ecology import _martial_school_context
from ate_sim.engine import Simulation


def configured_world():
    world=generate_world(91)
    person=next(iter(world.people.values()))
    world.advancement=AdvancementState()
    for essence in ('fire','water','wind'):world.advancement.absorb_essence(person.id,essence,0)
    path=world.advancement.path(person.id)
    for essence in path.essences:
        for _ in range(4):world.advancement.awaken_skill(person.id,'eyes',0,target_essence=essence)
    for a in path.abilities:a.rank=4;a.level=9;a.progress=.99
    person.rank=4
    return world,person,path


def application(world,p,a,constraint,difficulty):
    # A task-producer fixture: explicitly names the actually applied ability.
    event=world.emit('magical_service_completed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),ability=a.semantic_key,task_rank=difficulty,output=.02)
    record_application(world,p,a,event,constraint=constraint,difficulty=difficulty,outcome=.02)
    return event


def test_migration_teaching_and_participation_do_not_credit_any_ability():
    w,p,path=configured_world()
    for kind in ('skill_taught','household_migrated','magical_expedition_resource_recovered'):
        w.emit(kind,Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),domain='craft')
    for _ in range(100):practice_ability(w,p,0,100,100,context='teach')
    assert path.abilities[0].rank==4
    assert all(not a.understanding.evidence for a in path.abilities)


def test_deliberate_reflection_integrates_evidenced_experience_without_replacing_transfer():
    u=Understanding()
    u.applications={
        'a':{'event':1,'difficulty':2,'outcome':1.,'metric':'control'},
        'b':{'event':2,'difficulty':2,'outcome':1.,'metric':'control'},
        'c':{'event':3,'difficulty':2,'outcome':1.,'metric':'control'},
    }
    for _ in range(32):u.reflect(4.,.6,3)
    assert u.integration==3.
    assert not u.ready(3)
    u.transfers.append({'event':4,'difficulty':3,'premises':[1,2]})
    assert u.ready(3)


def test_gold_integration_remains_slower_than_silver_integration():
    silver=Understanding(applications={str(i):{'event':i,'difficulty':3,'outcome':1.,'metric':'control'} for i in range(4)})
    gold=Understanding(applications={str(i):{'event':i,'difficulty':4,'outcome':1.,'metric':'control'} for i in range(4)})
    for _ in range(20):
        silver.reflect(4.,.8,3)
        gold.reflect(4.,.8,4)
    assert silver.integration>gold.integration
    assert silver.integration>=2.5
    assert gold.integration<2.


def test_easy_variety_and_reflection_do_not_substitute_for_harder_transfer():
    w,p,path=configured_world();a=path.abilities[0]
    for i in range(100):
        application(w,p,a,str(i),1)
        practice_ability(w,p,0,100,100,context='learn')
    assert a.rank==4 and len(a.understanding.evidence)==6
    assert not a.understanding.transfers
    assert all(not b.understanding.evidence for b in path.abilities[1:])


def test_gold_requires_two_harder_held_out_applications_after_integration():
    w,p,path=configured_world();a=path.abilities[0]
    application(w,p,a,'initial-a',2);application(w,p,a,'initial-b',3)
    practice_ability(w,p,0,100,100,context='learn')
    application(w,p,a,'transfer-a',4)
    practice_ability(w,p,0,100,100,context='learn')
    assert a.rank==4
    # Repeating the same held-out problem adds nothing.
    application(w,p,a,'transfer-a',4)
    assert len(a.understanding.transfers)==1
    application(w,p,a,'transfer-b',4)
    practice_ability(w,p,0,100,100,context='learn')
    assert a.rank==5 and w.advancement.rank(p.id)==4
    revelation=next(e for e in w.events if e.kind=='essence_revelation_integrated')
    assert len(revelation.data['transfer_proofs'])==2
    for proof in revelation.data['transfer_proofs']:
        event=w.events[proof['event']-1]
        assert len(event.causes)==3 and event.data['generalization']
        assert all(w.events[i-1].data['difficulty']<event.data['difficulty'] for i in proof['premises'])
    assert a.understanding.evidence=={}


def test_uncredited_ability_and_failed_output_cannot_supply_evidence():
    w,p,path=configured_world();a,b=path.abilities[:2]
    e=application(w,p,a,'a',2)
    record_application(w,p,b,e,constraint='b',difficulty=2,outcome=1)
    record_application(w,p,a,e,constraint='failed',difficulty=2,outcome=0)
    assert not b.understanding.evidence
    assert 'failed' not in a.understanding.evidence


def test_accomplished_society_veteran_can_found_lineage_training_school():
    w,p,path=configured_world();p.age=40;w.year=5
    adv=w.institutions.institution_by_kind('adventure_society')
    assert adv is not None
    adv.members.add(p.id)
    context=_martial_school_context(w,Simulation(w).rng,sorted(w.current_people(),key=lambda x:x.id),adv.members)
    schools=[x for x in w.communities.communities.values() if x.kind=='martial_school']
    assert len(schools)==1
    school=schools[0]
    assert w.communities.memberships[(p.id,school.id)]==1.
    assert context[p.id]>=4
    event=next(e for e in w.events if e.kind=='martial_school_founded')
    assert event.actors[0].id==p.id and event.data['founder_rank']==4
