"""World-facing progression records; the archive never invents milestones."""
from .advancement import RANKS, Understanding
from .core_types import layer_ref


def record_body_transition(world, person, before, *, context, causes=()):
    after = world.advancement.rank(person.id)
    person.rank = after
    if after == before:
        return
    if after < before:
        raise ValueError('normal essence progression cannot lower body rank')
    Layer, Ref = layer_ref()
    path = world.advancement.path(person.id)
    prerequisites = tuple(dict.fromkeys((*causes, *(
        a.milestone_event or a.origin_event for a in path.abilities
        if a.milestone_event is not None or a.origin_event is not None))))
    world.emit('rank_advanced', Layer.REALITY, (Ref('person', person.id),),
               Ref('settlement', person.settlement), prerequisites,
               from_rank=before, to_rank=after, body_rank_before=RANKS[before],
               body_rank_after=RANKS[after], practice_context=context,
               prerequisite_abilities=tuple(a.semantic_key for a in path.abilities),
               ability_ranks=tuple(a.rank for a in path.abilities),
               essences=path.essences, bodily_purge=True,core_taint=path.core_fraction)


def practice_ability(world, person, index, meaningful_use, reflection=0., *, context):
    path = world.advancement.path(person.id)
    ability = path.abilities[index]
    before = ability.rank
    understanding=ability.understanding
    world.advancement.practice(person.id, index, meaningful_use, reflection)
    if ability.rank == before:
        return
    Layer, Ref = layer_ref()
    previous = ability.milestone_event or ability.origin_event
    causes = (() if previous is None else (previous,))
    if before>=3:
        revelation=world.emit('essence_revelation_integrated',Layer.REALITY,
            (Ref('person',person.id),),Ref('settlement',person.settlement),
            tuple(dict.fromkeys(understanding.evidence.values())),
            ability=ability.semantic_key,essence=ability.essence,
            ability_rank=RANKS[before],
            experience_contexts=tuple(sorted(understanding.evidence)),
            integration=understanding.integration,
            model='ATE evidence and applied reflection approximation')
        causes=(*causes,revelation.id)
    event = world.emit('ability_rank_advanced', Layer.REALITY,
                       (Ref('person', person.id),), Ref('settlement', person.settlement),
                       causes,
                       ability=ability.semantic_key, essence=ability.essence,
                       ability_rank_before=RANKS[before],
                       ability_rank_after=RANKS[ability.rank],
                       ability_level=ability.level, practice_context=context)
    ability.milestone_event = event.id
    ability.understanding = Understanding()


# Only consequential, actually recorded experiences supply opportunities. Generic
# annual work/teach selections are deliberately absent. Repeating an identical
# context cannot add evidence; application/reflection alone cannot create it.
EXPERIENCE_KINDS = {
    'item_crafted': 'craft', 'ranked_threat_resolved': 'confrontation',
    'magical_expedition_resource_recovered': 'exploration',
    'magical_expedition_returned_empty': 'exploration',
    'skill_taught': 'learning', 'household_migrated': 'migration',
}


def observe_experience(world,event):
    family=EXPERIENCE_KINDS.get(event.kind)
    if family is None:return
    data=event.data
    aspect=data.get('item_kind',data.get('form',data.get('key',data.get('domain',event.kind))))
    sid=None if event.location is None else event.location.id
    signature=f'{family}:{aspect}:{sid}'
    for ref in event.actors:
        if ref.kind!='person':continue
        path=world.advancement.path(ref.id)
        if path is None:continue
        for ability in path.abilities:
            if ability.rank not in (3,4):continue
            if family=='craft' and ability.function not in ('creation','enhancement','control','transformation','repair','manipulation','support'):continue
            evidence=ability.understanding.evidence
            if signature not in evidence and len(evidence)<8 and sum(k.split(':',1)[0]==family for k in evidence)<3:evidence[signature]=event.id
