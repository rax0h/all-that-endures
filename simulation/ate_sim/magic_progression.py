"""World-facing progression records; the archive never invents milestones."""
from .advancement import RANKS, Understanding
from .core_types import layer_ref


def record_body_transition(world, person, before, *, context, causes=()):
    after = world.advancement.rank(person.id);person.rank = after
    if after == before:return
    if after < before:raise ValueError('normal essence progression cannot lower body rank')
    Layer, Ref = layer_ref();path = world.advancement.path(person.id)
    prerequisites = tuple(dict.fromkeys((*causes, *(a.milestone_event or a.origin_event for a in path.abilities if a.milestone_event is not None or a.origin_event is not None))))
    world.emit('rank_advanced', Layer.REALITY, (Ref('person', person.id),),Ref('settlement', person.settlement), prerequisites,from_rank=before, to_rank=after, body_rank_before=RANKS[before],body_rank_after=RANKS[after], practice_context=context,prerequisite_abilities=tuple(a.semantic_key for a in path.abilities),ability_ranks=tuple(a.rank for a in path.abilities),essences=path.essences, bodily_purge=True,core_taint=path.core_fraction,path_contemplation=path.integration.contemplation)


def practice_ability(world, person, index, meaningful_use, reflection=0., *, context, core=0., core_event=None):
    path=world.advancement.path(person.id);ability=path.abilities[index];before=ability.rank;understanding=ability.understanding
    world.advancement.practice(person.id,index,meaningful_use,reflection,core)
    if core>0:
        Layer,Ref=layer_ref();world.emit('monster_core_progress_integrated',Layer.REALITY,(Ref('person',person.id),),Ref('settlement',person.settlement),(() if core_event is None else (core_event,)),ability=ability.semantic_key,essence=ability.essence,core_strength=core,core_taint=path.core_fraction,grants_understanding=False)
    if ability.rank == before:return
    Layer, Ref = layer_ref();previous = ability.milestone_event or ability.origin_event;causes = (() if previous is None else (previous,))
    if before>=3:
        revelation=world.emit('essence_revelation_integrated',Layer.REALITY,(Ref('person',person.id),),Ref('settlement',person.settlement),tuple(dict.fromkeys((*understanding.evidence.values(),*(t['event'] for t in understanding.transfers)))),ability=ability.semantic_key,essence=ability.essence,ability_rank=RANKS[before],experience_contexts=tuple(sorted(understanding.evidence)),integration=understanding.integration,transfer_proofs=understanding.transfers,path_contemplation=path.integration.contemplation,path_essence_groups=tuple(sorted(path.integration.essence_groups)),model='ATE relevant application, introspection and held-out generalization approximation');causes=(*causes,revelation.id)
    event=world.emit('ability_rank_advanced',Layer.REALITY,(Ref('person',person.id),),Ref('settlement',person.settlement),causes,ability=ability.semantic_key,essence=ability.essence,ability_rank_before=RANKS[before],ability_rank_after=RANKS[ability.rank],ability_level=ability.level,practice_context=context);ability.milestone_event=event.id;ability.understanding=Understanding()


def observe_experience(world,event):return


def record_application(world,person,ability,source,*,constraint,difficulty,outcome):
    if ability.rank not in (3,4) or outcome<=0:return
    if ability not in world.advancement.path(person.id).abilities:return
    keys=source.data.get('used_abilities',(source.data.get('ability'),));recorded_rank=source.data.get('challenge_complexity',source.data.get('task_rank',source.data.get('item_rank',source.data.get('threat_rank'))))
    if ability.semantic_key not in keys or recorded_rank!=difficulty:return
    if not any(a.kind=='person' and a.id==person.id for a in source.actors):return
    u=ability.understanding
    if constraint in u.applications:return
    Layer,Ref=layer_ref();priors=list(u.applications.values());metric=source.data.get('service',source.kind);challenging=[x for x in priors if x['difficulty']<difficulty and x['metric']==metric];output_floor=min((x['outcome'] for x in challenging[-2:]),default=float('inf'));transfer=len(challenging)>=2 and outcome>=output_floor and u.integration>=2+len(u.transfers) and difficulty>=ability.rank and len(u.transfers)<(1 if ability.rank==3 else 2)
    if len(priors)>=6 and not transfer:
        same=sum(x['metric']==metric for x in priors)
        if same>=2:return
        counts={x['metric']:sum(y['metric']==x['metric'] for y in priors) for x in priors};redundant=[k for k,x in u.applications.items() if counts[x['metric']]>2]
        if not redundant:return
        oldest=min(redundant,key=lambda k:u.applications[k]['event']);del u.applications[oldest];u.evidence.pop(oldest,None)
    causes=(source.id,)
    if transfer:causes+=tuple(x['event'] for x in challenging[-2:])
    e=world.emit('ability_applied',Layer.REALITY,(Ref('person',person.id),),source.location,causes,ability=ability.semantic_key,essence=ability.essence,function=ability.function,domain=ability.domain,ability_rank=RANKS[ability.rank],ability_level=ability.level,task_event=source.id,constraint=constraint,difficulty=difficulty,outcome=outcome,generalization=transfer,principle=ability.function if transfer else None,metric=metric,output_floor=output_floor if transfer else None,basis='same ability, distinct constraints, harder held-out application')
    if len(u.applications)>=6:
        oldest=min(u.applications,key=lambda k:(u.applications[k]['difficulty'],u.applications[k]['event']));del u.applications[oldest];u.evidence.pop(oldest,None)
    u.applications[constraint]={'event':e.id,'difficulty':difficulty,'outcome':outcome,'metric':metric};u.evidence[constraint]=e.id
    if transfer:u.transfers.append({'event':e.id,'difficulty':difficulty,'premises':list(causes[1:])})