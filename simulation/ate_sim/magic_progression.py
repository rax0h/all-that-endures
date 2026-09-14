"""World-facing progression records; the archive never invents milestones."""
from .advancement import RANKS
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
               essences=path.essences, bodily_purge=True)


def practice_ability(world, person, index, meaningful_use, reflection=0., *, context):
    path = world.advancement.path(person.id)
    ability = path.abilities[index]
    before = ability.rank
    world.advancement.practice(person.id, index, meaningful_use, reflection)
    if ability.rank == before:
        return
    Layer, Ref = layer_ref()
    previous = ability.milestone_event or ability.origin_event
    event = world.emit('ability_rank_advanced', Layer.REALITY,
                       (Ref('person', person.id),), Ref('settlement', person.settlement),
                       () if previous is None else (previous,),
                       ability=ability.semantic_key, essence=ability.essence,
                       ability_rank_before=RANKS[before],
                       ability_rank_after=RANKS[ability.rank],
                       ability_level=ability.level, practice_context=context)
    ability.milestone_event = event.id
