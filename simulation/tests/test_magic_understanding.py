from ate_sim.advancement import AdvancementState
from ate_sim.worldgen import generate_world
from ate_sim.core import Layer,Ref
from ate_sim.magic_progression import practice_ability


def configured_world():
    world=generate_world(91)
    person=next(iter(world.people.values()))
    world.advancement=AdvancementState()
    for essence in ('fire','water','wind'):
        world.advancement.absorb_essence(person.id,essence,0)
    path=world.advancement.path(person.id)
    for essence in path.essences:
        for _ in range(4):world.advancement.awaken_skill(person.id,'eyes',0,target_essence=essence)
    for a in path.abilities:a.rank=4;a.level=9;a.progress=.99
    person.rank=4
    return world,person,path


def experience(world,p,kind,**data):
    return world.emit(kind,Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),**data)


def test_repeated_teaching_and_reflection_cannot_generate_diamond():
    world,p,path=configured_world()
    for _ in range(500):
        experience(world,p,'skill_taught',domain='craft')
        practice_ability(world,p,0,100.,100.,context='teach')
    assert path.abilities[0].rank==4
    assert len(path.abilities[0].understanding.evidence)==1


def test_distinct_experience_integration_has_actual_causal_evidence():
    world,p,path=configured_world()
    causes=[]
    for domain in ('craft','knowledge'):
        causes.append(experience(world,p,'skill_taught',domain=domain).id)
    for key in ('fire','water'):
        causes.append(experience(world,p,'magical_expedition_resource_recovered',key=key).id)
    practice_ability(world,p,0,100.,100.,context='learn')
    assert path.abilities[0].rank==5
    revelation=next(e for e in world.events if e.kind=='essence_revelation_integrated')
    assert set(revelation.causes)==set(causes)
    assert 'approximation' in revelation.data['model']
    assert world.events[-1].causes[-1]==revelation.id
    assert world.advancement.rank(p.id)==4


def test_evidence_is_bounded_and_leaves_room_for_a_second_family():
    world,p,path=configured_world()
    for i in range(100):experience(world,p,'skill_taught',domain=str(i))
    assert len(path.abilities[0].understanding.evidence)==3
    for i in range(100):experience(world,p,'magical_expedition_resource_recovered',key=str(i))
    assert len(path.abilities[0].understanding.evidence)==6


def test_gold_evidence_does_not_carry_over_from_silver():
    world,p,path=configured_world()
    for ability in path.abilities:ability.rank=3
    experience(world,p,'skill_taught',domain='craft')
    experience(world,p,'magical_expedition_resource_recovered',key='fire')
    practice_ability(world,p,0,100.,100.,context='learn')
    assert path.abilities[0].rank==4
    assert path.abilities[0].understanding.evidence=={}
