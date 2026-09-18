"""Finite spirit-coin supply, funded contracts and magical services.

Farm yields, tax shares and service prices are explicit ATE approximations.
Harvesting monsters does not call any currency production function.
"""
from .core_types import layer_ref
from .currency import denomination_for_rank
from .threat_ecology import supported_rank
from .magic_progression import record_application


def spirit_economy_step(world,rng,living=None):
    Layer,Ref=layer_ref()
    society=world.institutions.institution_by_kind('adventure_society')
    if society is None:return
    farms={a.settlements[0]:a for a in world.infrastructure.assets.values() if a.kind=='spirit_coin_farm'}
    living=world.living_by_settlement() if living is None else living
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


def magical_services_step(world,rng,living=None):
    living=world.living_by_settlement() if living is None else living
    for sid,people in sorted(living.items()):
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


def apprenticeship_step(world,living=None):
    """Fund the Society's broad replacement pipeline with real work and real money.

    The Adventure Society wants as many viable Iron-rank responders as its local
    civilization can sustain. Committed incomplete-path recruits therefore do
    patrol, drills, logistics and public works for an actual stipend from the
    conserved Society treasury. Nothing here grants an essence, stone, ability
    or rank: trainees still buy physical stock and satisfy every progression
    prerequisite in the normal systems.
    """
    from .magic_resources import _aspiration
    Layer,Ref=layer_ref();inst=world.institutions.institution_by_kind('adventure_society')
    if inst is None:return
    living=world.living_by_settlement() if living is None else living
    treasury=world.currency.treasuries.get(inst.id,{})
    for sid,people in sorted(living.items()):
        branch=world.institutions.branch_for('adventure_society',sid)
        if branch is None:continue
        open_notices=sum(world.institutions.notices[nid].status!='resolved'
                         for nid in branch.notices if nid in world.institutions.notices)
        # Capacity follows branch authority and real workload, not a target rank count.
        capacity=max(4,min(18,4+int(8*branch.authority)+min(5,open_notices)))
        candidates=[]
        for p in people:
            if not p.alive or p.age<16:continue
            path=world.advancement.path(p.id)
            if path and len(path.abilities)==20:continue
            aspiration=_aspiration(world,p)
            if not aspiration.completion_goal or aspiration.drive<.30:continue
            candidates.append(p)
        candidates.sort(key=lambda p:(
            -(len(world.advancement.path(p.id).abilities) if world.advancement.path(p.id) else 0),
            -_aspiration(world,p).preparation,-_aspiration(world,p).urgency,
            -p.curiosity,p.id))
        for p in candidates[:capacity]:
            if treasury.get('iron',0)<3:break
            aspiration=_aspiration(world,p)
            rr=world.year+p.id
            work='public defense patrol' if rr%2 else 'Society field drills and logistics'
            world.skills.practice(p.id,'defense',.24 if rr%2 else .18)
            world.skills.practice(p.id,'construction',.08 if rr%2 else .12)
            aspiration.preparation=min(1.,aspiration.preparation+.025)
            aspiration.urgency=max(aspiration.urgency,.48)
            coins=world.currency.treasury_transfer(inst.id,p.id,{'iron':3})
            world.emit('society_apprentice_work',Layer.SOCIETY,
                (Ref('person',p.id),Ref('institution',inst.id)),Ref('settlement',sid),
                branch=branch.id,work=work,coin_reward=coins,treasury=inst.id,
                eligibility='committed incomplete path',training_contract=True)
