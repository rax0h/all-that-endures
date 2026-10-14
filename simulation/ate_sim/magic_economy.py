"""Finite spirit-coin supply, funded contracts and magical services.

Farm yields, tax shares and service prices are explicit ATE approximations.
Harvesting monsters does not call any currency production function.
"""
from .core_types import layer_ref
from .currency import denomination_for_rank,COIN_VALUE,DENOMINATIONS,ranked_reward
from .threat_ecology import supported_rank
from .magic_progression import record_application


def spirit_economy_step(world,rng):
    Layer,Ref=layer_ref()
    society=world.institutions.institution_by_kind('adventure_society')
    if society is None:return
    farms={a.settlements[0]:a for a in world.infrastructure.assets_of_kind('spirit_coin_farm')}
    living=world.living_by_settlement()
    for sid,people in sorted(living.items()):
        eligible=[p for p in people if p.age>=16 and p.rank>=1 and world.skills.get(p.id,'craft').level>=.7]
        if not eligible:continue
        farmer=max(eligible,key=lambda p:(min(p.rank,supported_rank(world.ambient_magic.field(sid).level)),world.skills.get(p.id,'craft').level,-p.id))
        farm=farms.get(sid)
        if farm is None:
            if farmer.wealth<6 or not world.materials.has_available(sid):continue
            lot=world.materials.best_at_rank(sid,0) or world.materials.best_at_rank(sid,1)
            if lot is None:continue
            if lot.owner_kind!='person' or lot.material_rank>1:continue
            seller=world.people.get(lot.owner_id)
            if seller is None:continue
            if seller.id!=farmer.id:
                farmer.wealth-=1;seller.wealth+=1
                bought=world.emit('material_purchased',Layer.SOCIETY,(Ref('person',farmer.id),Ref('person',seller.id)),Ref('settlement',sid),(lot.origin_event,),material_lot=lot.id,price=1.,coin_transfer={},price_domain='ordinary_wealth')
                lot.owner_id=farmer.id;lot.transfers.append(bought.id)
            world.materials.consume(lot,1.);farmer.wealth-=6
            e=world.emit('spirit_coin_farm_built',Layer.REALITY,(Ref('person',farmer.id),),Ref('settlement',sid),(lot.origin_event,),material_lot=lot.id,ordinary_cost=6)
            farm=world.infrastructure.create('spirit_coin_farm',(sid,),1.,1.,world.year,e.id)
        path=world.advancement.path(farmer.id)
        abilities=[a for a in path.abilities if a.function in ('control','creation','transformation','enhancement')] if path else []
        if not abilities:continue
        operator=min(abilities,key=lambda a:(len(a.understanding.applications),a.semantic_key))
        ambient=world.ambient_magic.field(sid).level
        tier=min(farmer.rank,operator.rank,supported_rank(ambient),5)
        if farm.condition<.5:continue
        # One working operator, one annual harvest, limited by site AND operator.
        denomination=denomination_for_rank(tier);coins={denomination:max(1,int(24*farm.condition))}
        world.currency.credit(farmer.id,coins)
        e=world.emit('spirit_coins_cultivated',Layer.REALITY,(Ref('person',farmer.id),),Ref('settlement',sid),(farm.origin_event,),farm=farm.id,ambient=ambient,production_rank=tier,challenge_complexity=tier,used_abilities=(operator.semantic_key,),coin_created=coins,mechanism='worked ambient coin cultivation')
        record_application(world,farmer,operator,e,constraint=f'cultivation:{sid}:{int(world.local[sid].rain*4)}',difficulty=tier,outcome=float(coins[denomination]))
        levy={denomination:coins[denomination]//2}
        world.currency.treasury_transfer(society.id,farmer.id,levy,deposit=True)
        world.emit('society_treasury_funded',Layer.SOCIETY,(Ref('person',farmer.id),Ref('institution',society.id)),Ref('settlement',sid),(e.id,),coin_deposit=levy,institution=society.id,mechanism='farm protection agreement')
        world.infrastructure.maintain(farm.id,.03)
    for p in world.current_people():
        if not p.alive or p.rank<2:continue
        # An annual reserve supplement where local magic cannot support the body.
        # Not an assertion about literal meals/day; higher-tier overdraw is forbidden.
        denomination=denomination_for_rank(p.rank)
        if supported_rank(world.ambient_magic.field(p.settlement).level)>=p.rank:continue
        if world.currency.wallets.get(p.id,{}).get(denomination,0)<1:continue
        coins=world.currency.consume(p.id,{denomination:1})
        recovered=min(.01,1-p.health);p.health+=recovered
        world.emit('spirit_coin_sustenance',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),coin_consumed=coins,body_rank=p.rank,recovered_health=recovered,mechanism='safe own-tier magical reserve supplement')


def magical_service(world,provider,client,ability,*,kind,difficulty,constraint):
    """A priced service changes a real client/household state; no work, no proof.

    Function eligibility, actual need, tier capability, liquidity and successful
    output all precede evidence. Lower-tier clients cannot buy higher-tier work
    using a flattened ordinary-wealth scalar.
    """
    Layer,Ref=layer_ref()
    functions={'healing':{'recovery','healing','restoration'},
               'protection':{'control','support','enhancement','detection','sense','creation','defense','preservation','storage','environmental control'},
               'instruction':{'communication','influence','analysis','guidance','coordination','prediction','teamwork'},
               'provision':{'creation','transformation','control','exchange'}}
    if ability.function not in functions.get(kind,set()) or ability.rank<difficulty:return False
    h=world.households[client.household]
    need=(1-world.skills.get(client.id,'knowledge').level) if kind=='instruction' else (1-client.health) if kind=='healing' else ((1-h.preparedness) if kind=='protection' else max(0.,5-h.food))
    if need<=.01:return False
    denomination=denomination_for_rank(difficulty)
    if world.currency.wallets.get(client.id,{}).get(denomination,0)<2:return False
    output=min(need,.02*(1+ability.level/10))
    coins=world.currency.transfer(client.id,provider.id,{denomination:2})
    if kind=='instruction':world.skills.get(client.id,'knowledge').level+=output
    elif kind=='healing':client.health+=output
    elif kind=='protection':h.preparedness+=output
    else:h.food+=output
    # Difficulty of understanding is distinct from energy/body tier. Multiple
    # coupled constraints can make lower-tier work conceptually demanding.
    local=world.local[client.settlement]
    complexity=min(5,max(difficulty,1+int(need>.25)+int(local.scarcity>.2)+int(local.flood>.04)+int(client.grief>.2)))
    e=world.emit('magical_service_completed',Layer.REALITY,(Ref('person',provider.id),Ref('person',client.id)),Ref('settlement',client.settlement),
        ability=ability.semantic_key,function=ability.function,service=kind,task_rank=difficulty,challenge_complexity=complexity,output=output,coin_transfer=coins,coin_payer=client.id,coin_payee=provider.id)
    record_application(world,provider,ability,e,constraint=constraint,difficulty=complexity,outcome=output)
    return True


def magical_services_step(world,rng):
    for sid,people in sorted(world.living_by_settlement().items()):
        clients=[p for p in people if p.alive and world.currency.wallets.get(p.id)]
        if not clients:continue
        providers=[p for p in people if p.alive and p.rank>=1]
        for p in providers:
            path=world.advancement.path(p.id)
            if path is None:continue
            # One actual service per provider/year; no all-pairs marketplace.
            rr=rng.stream('magical_service',world.year,p.id)
            client=clients[int(rr.random()*len(clients))%len(clients)]
            if client.id==p.id:continue
            kind='instruction' if world.skills.get(client.id,'knowledge').level<.7 and world.year%2==0 else 'healing' if client.health<.9 else ('provision' if world.households[client.household].food<3 else 'protection')
            difficulty=max(1,client.rank if kind=='healing' else supported_rank(world.ambient_magic.field(sid).level))
            for ability in sorted(path.abilities,key=lambda a:(a.rank,a.level,a.semantic_key)):
                # Disease/embodiment, ecology and household conditions define cases.
                constraint=f'{kind}:{client.species}:{sid}:{int(world.local[sid].scarcity*4)}'
                if magical_service(world,p,client,ability,kind=kind,difficulty=difficulty,constraint=constraint):break


def treasury_liquidity_step(world,institution_id,people=None):
    """Recover needed low denominations through exact-value voluntary exchange.

    This creates no monetary value.  The institution gives an existing higher
    coin and receives the exact lower-denomination value from a real wallet.
    """
    Layer,Ref=layer_ref()
    people=list(world.current_people()) if people is None else list(people)
    treasury=world.currency.treasuries.setdefault(institution_id,{})
    institution=world.institutions.institutions.get(institution_id)
    if institution is None:return 0

    active=world.institutions.active_notices()
    target={d:0 for d in DENOMINATIONS}
    for n in active:
        for d,count in ranked_reward(n.required_rank,1.,include_change=False).items():
            target[d]+=count
    # Keep a small operating buffer for low-tier purchases/contracts without
    # inventing an output quota.
    target['iron']=max(target['iron'],12)
    exchanges=0
    for lower_index in range(1,len(DENOMINATIONS)-1):
        lower=DENOMINATIONS[lower_index]
        short=max(0,target.get(lower,0)-treasury.get(lower,0))
        if short<=0:continue
        for higher_index in range(lower_index+1,len(DENOMINATIONS)):
            higher=DENOMINATIONS[higher_index]
            ratio=COIN_VALUE[higher]//COIN_VALUE[lower]
            if ratio<=0:continue
            while treasury.get(higher,0)>0 and treasury.get(lower,0)<target.get(lower,0):
                holder=next((p for p in people if p.alive and world.currency.wallets.get(p.id,{}).get(lower,0)>=ratio),None)
                if holder is None:break
                result=world.currency.treasury_exchange(institution_id,holder.id,{higher:1},{lower:ratio})
                world.emit('society_currency_exchange',Layer.SOCIETY,
                    (Ref('person',holder.id),Ref('institution',institution_id)),
                    Ref('settlement',holder.settlement),
                    institution=institution_id,treasury_gives=result['treasury_gives'],
                    person_gives=result['person_gives'],exchange_value=COIN_VALUE[higher],
                    mechanism='exact-value public change')
                exchanges+=1
            if treasury.get(lower,0)>=target.get(lower,0):break
    return exchanges


def apprenticeship_step(world):
    """Run annual Adventure Society cadet cohorts using physical Society reserves.

    Recruitment, resource ownership and advancement remain separate authorities:
    the institution owns the cohort; the resource system owns real essences/stones;
    advancement alone decides whether a completed path becomes Iron.
    """
    from .magic_resources import _aspiration,_commit_to_full_path,absorb_essence_resource,use_awakening_stone
    Layer,Ref=layer_ref();inst=world.institutions.institution_by_kind('adventure_society')
    if inst is None:return
    living=world.living_by_settlement()

    active_cadet_ids=set()
    for cohort in world.institutions.cadet_cohorts.values():
        if cohort.closed_year is None:
            active_cadet_ids.update(pid for pid in cohort.cadets if pid not in cohort.graduates)

    # One real class per branch/year. Capacity comes from branch authority and
    # local population, not a global target.
    for branch_id in sorted(inst.branches):
        branch=world.institutions.branches[branch_id];people=list(living.get(branch.settlement,()))
        if not people:continue
        capacity=max(2,min(14,2+int(branch.authority*6)+len(people)//90))
        candidates=[]
        for p in people:
            if p.age<16 or p.id in inst.members or p.id in active_cadet_ids:continue
            path=world.advancement.path(p.id)
            if path is not None and len(path.abilities)==20 and world.advancement.rank(p.id)>=1:continue
            a=_aspiration(world,p)
            defense=world.skills.get(p.id,'defense').level
            intent=a.adventurer_aspiration or (a.risk_tolerance>=.58 and p.curiosity>=.48 and (defense>=.35 or a.drive>=.52))
            if not intent:continue
            score=.34*a.drive+.24*a.preparation+.18*a.risk_tolerance+.14*p.curiosity+.10*min(1.,defense)
            candidates.append((score,p))
        candidates.sort(key=lambda x:(x[0],-x[1].id),reverse=True)
        selected=[p for _,p in candidates[:capacity]]
        if selected:
            formed=world.emit('society_cadet_class_formed',Layer.SOCIETY,
                tuple(Ref('person',p.id) for p in selected),Ref('settlement',branch.settlement),
                branch=branch.id,class_year=world.year,capacity=capacity,admitted=len(selected))
            cohort=world.institutions.create_cadet_cohort(branch.id,world.year,capacity,formed.id)
            for p in selected:
                a=_aspiration(world,p);a.adventurer_aspiration=True;_commit_to_full_path(a)
                cohort.cadets.add(p.id);active_cadet_ids.add(p.id)
                world.emit('society_cadet_admitted',Layer.SOCIETY,(Ref('person',p.id),),
                    Ref('settlement',branch.settlement),(formed.id,),branch=branch.id,
                    cohort=cohort.id,class_year=cohort.class_year)

    # Oldest cohorts and most-complete cadets receive reserves first.
    reserve=lambda kind:world.magic_resources.inventory('institution',inst.id,kind)
    cadets=[]
    for cohort in sorted(world.institutions.cadet_cohorts.values(),key=lambda x:(x.class_year,x.id)):
        if cohort.closed_year is not None:continue
        for pid in cohort.cadets:
            if pid in cohort.graduates:continue
            p=world.people.get(pid)
            if p is None or not p.alive:continue
            path=world.advancement.path(pid);base=0 if path is None else len(path.base_essences);abilities=0 if path is None else len(path.abilities)
            cadets.append((cohort.class_year,-abilities,-base,p.id,cohort))
    cadets.sort(key=lambda x:(x[0],x[1],x[2],x[3]))

    for _,_,_,pid,cohort in cadets:
        p=world.people[pid];path=world.advancement.path(pid);base=0 if path is None else len(path.base_essences)
        while base<3:
            stock=reserve('essence')
            viable=[r for r in stock if path is None or r.key not in path.base_essences]
            if not viable:break
            resource=min(viable,key=lambda r:(r.created_year,r.id));source=resource.location
            issue=world.emit('society_cadet_resource_issued',Layer.SOCIETY,
                (Ref('person',pid),Ref('institution',inst.id)),Ref('settlement',p.settlement),
                ((resource.origin_event,) if resource.origin_event else ()),resource=resource.id,
                resource_kind=resource.kind,branch=cohort.branch,cohort=cohort.id,
                class_year=cohort.class_year,source_location=source,destination=p.settlement,
                delivery_days=0 if source in (None,p.settlement) else 14)
            world.magic_resources.transfer(resource.id,'person',pid,issue.id,p.settlement)
            absorb_essence_resource(world,pid,resource.id);path=world.advancement.path(pid);base=len(path.base_essences)
        if path is not None and base>=3:
            while len(path.abilities)<20:
                stock=reserve('awakening_stone')
                if not stock:break
                resource=min(stock,key=lambda r:(r.created_year,r.id));source=resource.location
                issue=world.emit('society_cadet_resource_issued',Layer.SOCIETY,
                    (Ref('person',pid),Ref('institution',inst.id)),Ref('settlement',p.settlement),
                    ((resource.origin_event,) if resource.origin_event else ()),resource=resource.id,
                    resource_kind=resource.kind,branch=cohort.branch,cohort=cohort.id,
                    class_year=cohort.class_year,source_location=source,destination=p.settlement,
                    delivery_days=0 if source in (None,p.settlement) else 14)
                world.magic_resources.transfer(resource.id,'person',pid,issue.id,p.settlement)
                if use_awakening_stone(world,pid,resource.id) is None:break
                path=world.advancement.path(pid)
        path=world.advancement.path(pid)
        if path is not None and len(path.abilities)==20 and world.advancement.rank(pid)>=1:
            cohort.graduates.add(pid);inst.members.add(pid)
            world.emit('society_cadet_graduated',Layer.SOCIETY,
                (Ref('person',pid),Ref('institution',inst.id)),Ref('settlement',p.settlement),
                ((cohort.origin_event,) if cohort.origin_event else ()),branch=cohort.branch,
                cohort=cohort.id,class_year=cohort.class_year,graduation_year=world.year,
                body_rank=world.advancement.rank(pid),abilities=len(path.abilities))

    for cohort in world.institutions.cadet_cohorts.values():
        if cohort.closed_year is not None:continue
        unresolved=[pid for pid in cohort.cadets if pid not in cohort.graduates and world.people.get(pid) is not None and world.people[pid].alive]
        if not unresolved:cohort.closed_year=world.year
