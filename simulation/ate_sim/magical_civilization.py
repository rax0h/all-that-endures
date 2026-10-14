from __future__ import annotations

from .core_types import layer_ref
from .magic_resources import (
    _aspiration,_commit_to_full_path,_make_resource,_wanted_resources,
    _transfer_to_seeker,_SettlementMarket,absorb_essence_resource,use_awakening_stone,
)
from .materials import _produce_lot,_craft_once
from .institutions import apply_for_society,full_essence_user

EXPEDITION_ACTIVITY_RATE=.62


def _practitioners(world,people):
    paths=world.advancement.paths
    return [p for p in people if p.id in paths]


def _institutional_capacity(world,sid):
    return (
        world.institutions.branch_for('adventure_society',sid),
        world.institutions.branch_for('magic_society',sid),
    )


def _review_magic_demand(world,people,adventure,magic):
    """Update concrete magical goals from current life without inventing psyche.

    This is a material/vocational demand review.  It reads existing traits,
    work, family, social ties, institutions and environmental pressure.  It does
    not create memories, beliefs or personality state.
    """
    paths=world.advancement.paths;aspirations=world.magic_resources.aspirations
    skills_get=world.skills.get;neighbors=world.social.neighbors
    local_user_ids={p.id for p in people if p.id in paths}
    for p in people:
        a=aspirations.get(p.id)
        if a is None:a=_aspiration(world,p)
        path=paths.get(p.id)
        if path is not None and a.completion_goal:
            a.desired_base_essences=3;a.desired_abilities=20

        family=sum(1 for x in p.parents if x in paths)
        contacts=sum(1 for x in neighbors(p.id) if x in local_user_ids)
        work_levels={
            'agriculture':skills_get(p.id,'agriculture').level,
            'construction':skills_get(p.id,'construction').level,
            'craft':skills_get(p.id,'craft').level,
            'knowledge':skills_get(p.id,'knowledge').level,
            'defense':skills_get(p.id,'defense').level,
        }
        work_domain,work_level=max(work_levels.items(),key=lambda x:x[1])
        named=p.occupation in (
            'adventurer','guard','hunter','soldier','farmer','crafter','smith',
            'healer','merchant','scholar','builder','architect','craft apprentice',
            'magical craftsperson',
        )
        work_need=named or (work_level>=1.60 and p.curiosity>=.55)
        settlement=world.settlements[p.settlement];cell=world.cells[(settlement.x,settlement.y)]
        local=world.local[p.settlement];pressure=max(settlement.memory.get('monster_surge',0.),p.fear)
        scarcity_need=local.scarcity>=.18 and work_levels['agriculture']>=.45
        household_crisis=local.scarcity>=.24 and world.households[p.household].food<4
        institutional_access=adventure is not None or magic is not None
        already=a.desired_base_essences>0
        social_start=(family>=1 and p.curiosity>=.42) or (contacts>=5 and p.curiosity>=.60)
        social_continue=already and ((family>=1 and p.curiosity>=.38) or (contacts>=4 and p.curiosity>=.50))
        motive=world.agency.motives.get(p.id);status=0. if motive is None else motive.status
        work_start=work_need and (already or p.curiosity>=.48 or status>=.38)

        reason=None
        if social_start or social_continue:reason='social magical exposure'
        elif work_start and institutional_access:reason=f'{work_domain} capability'
        elif scarcity_need and institutional_access:reason='food-production pressure'
        elif household_crisis and institutional_access and p.attachment>=.45:reason='household scarcity'
        elif (cell.hazard>=.72 or pressure>=.48) and institutional_access:reason='local magical pressure'

        started=path is not None and len(path.base_essences)>0
        mastery=min(1.,.62*p.curiosity+.28*(1-p.inhibition)+.10*status)
        adventure_intent=(
            a.adventurer_aspiration
            or (a.risk_tolerance>=.72 and p.curiosity>=.60
                and (work_levels['defense']>=.85 or pressure>=.28))
        )
        if adventure_intent:a.adventurer_aspiration=True
        personal_mastery=started and mastery>=.84
        professional_mastery=started and work_level>=2.40 and mastery>=.72
        magical_profession=started and p.occupation=='magical craftsperson' and mastery>=.66
        if adventure_intent or personal_mastery or professional_mastery or magical_profession:
            _commit_to_full_path(a)

        if reason is None:continue
        a.drive=min(1.,max(a.drive,.34+.05*min(3,family+contacts)+(.06 if work_need else 0.)+.04*min(1.,work_level)))
        a.urgency=min(1.,max(a.urgency,.30+.28*pressure+(.10 if work_need else 0.)+(.08 if scarcity_need or household_crisis else 0.)))
        a.desired_base_essences=max(a.desired_base_essences,1)
        a.desired_abilities=max(a.desired_abilities,5)
        if a.reason=='capability' or not already:a.reason=reason


def _apply_external_magic_pressure(world,sid,people,users):
    """Increase urgency for existing seekers; never manufacture interest."""
    if not people:return
    active=world.threat_ecology.active(sid);surge=world.settlements[sid].memory.get('monster_surge',0.)
    threat_rank=max((t.rank for t in active),default=0);user_share=len(users)/max(1,len(people))
    for p in people:
        a=_aspiration(world,p);path=world.advancement.path(p.id)
        base=0 if path is None else len(path.base_essences)
        if a.desired_base_essences<=base or a.desired_base_essences<=0:continue
        motive=world.agency.motives.get(p.id);status=0. if motive is None else motive.status
        threat=max(surge,p.fear,min(1.,threat_rank/3.))
        competition=min(1.,user_share*2.0)*(.55+.35*status)
        external=max(threat,competition)
        if external<.12:continue
        a.urgency=max(a.urgency,min(1.,.34+.46*threat+.30*competition+.10*a.drive))
        a.compromise_tolerance=max(a.compromise_tolerance,min(.95,.42+.45*external))
        a.risk_tolerance=max(a.risk_tolerance,min(.92,.28+.38*external+.18*a.drive))


def _cadet_supply_plan(world,adventure_society):
    need={'essence':0,'awakening_stone':0}
    if adventure_society is None:return {**need,'institution_id':None}
    for cohort in world.institutions.cadet_cohorts.values():
        if cohort.closed_year is not None:continue
        for pid in cohort.cadets:
            if pid in cohort.graduates:continue
            p=world.people.get(pid)
            if p is None or not p.alive:continue
            path=world.advancement.path(pid);base=0 if path is None else len(path.base_essences)
            need['essence']+=max(0,3-base)
            if base>=3 and path is not None:need['awakening_stone']+=max(0,20-len(path.abilities))
    for resource in world.magic_resources.inventory('institution',adventure_society.id):
        if resource.kind in need:need[resource.kind]=max(0,need[resource.kind]-1)
    need['institution_id']=adventure_society.id
    return need


def _expedition_step(world,rng,sid,people,users,adventure,magic,supply_plan):
    if not people or supply_plan['institution_id'] is None:return
    if supply_plan['essence']<=0 and supply_plan['awakening_stone']<=0:return

    settlement=world.settlements[sid];cell=world.cells[(settlement.x,settlement.y)]
    ambient=world.ambient_magic.field(sid).level
    aspirations={}
    aspirants=[]
    for p in people:
        a=_aspiration(world,p);aspirations[p.id]=a
        if a.adventurer_aspiration:aspirants.append(p)

    adv_inst=world.institutions.institution_by_kind('adventure_society')
    local_members=0 if adv_inst is None else sum(p.id in adv_inst.members for p in people)
    institutional=(0. if adventure is None else 2.*adventure.authority)+(0. if magic is None else 1.5*magic.authority)
    field_capacity=len(users)+.45*len(aspirants)+1.5*local_members+institutional
    if field_capacity<=0:return

    rr=rng.stream('magical_field_economy',world.year,sid)
    pressure=max(0.,ambient-.30)+.35*cell.hazard+.08*min(10,field_capacity)
    attempts=min(8,max(1,int(EXPEDITION_ACTIVITY_RATE*pressure*(1.2+len(people)/90.))))
    user_ids={p.id for p in users}
    candidates=sorted(
        users+[p for p in aspirants if p.id not in user_ids],
        key=lambda p:(aspirations[p.id].risk_tolerance,aspirations[p.id].preparation,p.health,-p.id),
        reverse=True,
    )
    if not candidates:return

    Layer,Ref=layer_ref()
    for n in range(attempts):
        total_gap=supply_plan['essence']+supply_plan['awakening_stone']
        if total_gap<=0:break
        erng=rng.stream('magical_expedition',world.year,sid*100+n);leader=candidates[n%len(candidates)]
        a=aspirations[leader.id]
        readiness=.20+.22*a.preparation+.18*a.risk_tolerance+.08*leader.rank
        if adventure is not None:readiness+=.14
        if magic is not None:readiness+=.08
        danger=.08+.22*cell.hazard+.10*max(0.,ambient-.8)
        expedition=world.emit('magical_expedition',Layer.SOCIETY,(Ref('person',leader.id),),Ref('settlement',sid),
            society_branch=None if adventure is None else adventure.id,ambient_magic=round(ambient,3),
            readiness=round(readiness,3),danger=round(danger,3))
        if erng.random()>min(.86,readiness+.16*ambient):
            world.emit('magical_expedition_returned_empty',Layer.SOCIETY,(Ref('person',leader.id),),
                Ref('settlement',sid),(expedition.id,));continue

        cache_size=min(total_gap,1+min(2,int(field_capacity//60)))
        recovered=0
        for _ in range(cache_size):
            eg=supply_plan['essence'];sg=supply_plan['awakening_stone']
            if eg<=0 and sg<=0:break
            if eg<=0:kind='awakening_stone'
            elif sg<=0:kind='essence'
            else:
                stone_weight=sg*.62;essence_weight=eg*.38
                kind='awakening_stone' if erng.random()<stone_weight/(stone_weight+essence_weight) else 'essence'
            found=_make_resource(world,erng,sid,leader,kind,expedition.id,'Society demand-backed field recovery',
                owner_kind='institution',owner_id=supply_plan['institution_id'])
            supply_plan[kind]=max(0,supply_plan[kind]-1);recovered+=1
            world.emit('magical_expedition_resource_recovered',Layer.SOCIETY,
                (Ref('person',leader.id),Ref('institution',supply_plan['institution_id'])),
                Ref('settlement',sid),(expedition.id,found.origin_event),resource=found.id,
                resource_kind=found.kind,key=found.key,cache_size=cache_size,custody='institution')
        if recovered:a.preparation=min(1.,a.preparation+.025)


def _resource_circulation(world,rng,sid,people,magic):
    if not people:return
    rr=rng.stream('magical_circulation',world.year,sid)
    people_by_id={p.id:p for p in people};market=_SettlementMarket(world,people)
    holder_ids=[pid for pid in people_by_id if world.magic_resources.owner_index.get(('person',pid))]
    holder_set=set(holder_ids)
    def note_transfer(q):
        if q.id not in holder_set:holder_set.add(q.id);holder_ids.append(q.id)
    rounds=3+(3 if magic is not None else 0)
    for _ in range(rounds):
        if not holder_ids:break
        for holder_id in tuple(holder_ids):
            holder=people_by_id[holder_id];path=world.advancement.path(holder.id);a=_aspiration(world,holder)
            base=0 if path is None else len(path.base_essences)
            if base<a.desired_base_essences:
                ess=_wanted_resources(world,holder,world.magic_resources.inventory('person',holder.id,'essence'))
                viable=[r for r in ess if path is None or r.key not in path.base_essences]
                if viable and rr.random()<.55+.30*a.urgency and rr.random()<max(.25,a.compromise_tolerance):
                    absorb_essence_resource(world,holder.id,viable[int(rr.random()*len(viable))%len(viable)].id)
                    path=world.advancement.path(holder.id)
            if path is not None and len(path.abilities)<min(a.desired_abilities,path.capacity):
                stones=_wanted_resources(world,holder,world.magic_resources.inventory('person',holder.id,'awakening_stone'))
                if stones and rr.random()<max(.22,.82-.55*a.stone_selectiveness):
                    use_awakening_stone(world,holder.id,stones[int(rr.random()*len(stones))%len(stones)].id)
            held=world.magic_resources.inventory('person',holder.id)
            surplus=_wanted_resources(world,holder,held,wanted=False) if held else []
            if surplus and rr.random()<(.58 if magic is not None else .28):
                _transfer_to_seeker(world,surplus[int(rr.random()*len(surplus))%len(surplus)],
                    holder,people,rr,on_transfer=note_transfer,market=market)


def _society_pipeline(world,rng,people,adventure,magic,existing):
    for p in people:
        if not full_essence_user(world,p.id):continue
        a=_aspiration(world,p);targets=[]
        path=world.advancement.path(p.id)
        # Cadet graduates are inserted directly by the cohort pipeline.  This
        # application route remains for independently qualified Iron users.
        if a.adventurer_aspiration and path is not None and len(path.abilities)==20 and world.advancement.rank(p.id)>=1:
            targets.append(('adventure_society',adventure,.72))
        craft=world.skills.get(p.id,'craft').level;knowledge=world.skills.get(p.id,'knowledge').level
        if p.curiosity>.52 or craft>=1.2 or knowledge>=1.2:
            targets.append(('magic_society',magic,.48+.22*p.curiosity))
        for society,branch,intent in targets:
            inst=world.institutions.institution_by_kind(society)
            if branch is None or inst is None or p.id in inst.members or (p.id,society) in existing:continue
            srng=rng.stream('society_career_intent',world.year,p.id+(0 if society=='adventure_society' else 1000000))
            if srng.random()<min(.92,intent+.12*a.urgency+.10*a.preparation):
                apply_for_society(world,p.id,society);existing.add((p.id,society))


def _magical_workshops(world,rng,sid,people,users,magic):
    if not people:return
    settlement=world.settlements[sid]
    producers=sorted(people,key=lambda p:(world.skills.get(p.id,'agriculture').level+world.skills.get(p.id,'craft').level,p.health,-p.id),reverse=True)
    desired=min(24,max(0,len(people)//18+int(settlement.prosperity*3)-1))
    active_lots=len(world.materials.active_lot_index.get(sid,()))
    buffer=max(36,min(240,36+len(people)))
    extra=min(desired,max(0,buffer-active_lots));Layer,Ref=layer_ref()
    for n in range(extra):
        _produce_lot(world,sid,producers[n%len(producers)],rng.stream('civilization_material_batch',world.year,sid*100+n),Layer,Ref)
    crafters=[p for p in users if world.skills.get(p.id,'craft').level>=.7]
    if not crafters:return
    magical_lots=world.materials.magical_available_count(sid)
    commissions=min(12,magical_lots,len(crafters)*(2 if magic is not None else 1))
    for n in range(commissions):
        crafter=crafters[n%len(crafters)];crng=rng.stream('magical_commission',world.year,sid*100+n)
        if crng.random()<(.78 if magic is not None else .48):_craft_once(world,sid,crafter,crng,Layer,Ref)


def magical_civilization_step(world,rng):
    """Bounded feedback between people, institutions, ecology and physical magic."""
    by_settlement=world.adults_by_settlement(16)
    applications=world.institutions.application_pairs()
    adventure_society=world.institutions.institution_by_kind('adventure_society')
    supply_plan=_cadet_supply_plan(world,adventure_society)

    for sid in sorted(world.settlements):
        people=list(by_settlement.get(sid,()))
        if not people:continue
        users=_practitioners(world,people);adventure,magic=_institutional_capacity(world,sid)
        review=[p for p in people if p.age<=17 or ((world.year+p.id)&1)==0]
        if review:_review_magic_demand(world,review,adventure,magic)
        _apply_external_magic_pressure(world,sid,people,users)
        _expedition_step(world,rng,sid,people,users,adventure,magic,supply_plan)
        _resource_circulation(world,rng,sid,people,magic)
        _society_pipeline(world,rng,people,adventure,magic,applications)
        _magical_workshops(world,rng,sid,people,users,magic)
