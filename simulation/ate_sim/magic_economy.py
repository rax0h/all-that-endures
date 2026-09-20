"""Finite spirit-coin supply, funded contracts and magical services.

Farm yields, tax shares and service prices are explicit ATE approximations.
Harvesting monsters does not call any currency production function.
"""
from .core_types import layer_ref
from .currency import denomination_for_rank, COIN_VALUE, ranked_reward
from .threat_ecology import supported_rank
from .magic_progression import record_application


def _coin_demand(world, society, living):
    """Actual contracts plus two payrolls for available apprentice places."""
    demand={}
    for notice in world.institutions.notices.values():
        if notice.status=='resolved':continue
        for denomination,n in ranked_reward(notice.required_rank,1.,include_change=False).items():
            demand[denomination]=demand.get(denomination,0)+n
    for sid,people in living.items():
        if world.institutions.branch_for('adventure_society',sid) is None:continue
        candidates=0
        for p in people:
            a=world.magic_resources.aspirations.get(p.id);path=world.advancement.path(p.id)
            if p.alive and p.age>=16 and a and a.completion_goal and a.drive>=.4 and (path is None or len(path.abilities)<20):candidates+=1
        demand['iron']=demand.get('iron',0)+8*min(3,candidates)
    return demand


def _farm_output(tier, quantity, demand, treasury):
    """Finite worked cultivation, not conversion of already-existing coins.

    Lower-tier output is requested by real pending payments. Remaining capacity
    grows the native tier. Half the harvest funds the protection agreement.
    Value-equivalent cultivation capacity is an explicit ATE yield approximation.
    """
    native=denomination_for_rank(tier);budget=quantity*COIN_VALUE[native];out={}
    for denomination,value in COIN_VALUE.items():
        if value>=COIN_VALUE[native]:break
        shortage=max(0,demand.get(denomination,0)-treasury.get(denomination,0))
        count=min(2*shortage,budget//value)
        if count:out[denomination]=count;budget-=count*value
    count=budget//COIN_VALUE[native]
    if count:out[native]=count
    return out


def spirit_economy_step(world,rng):
    Layer,Ref=layer_ref()
    society=world.institutions.institution_by_kind('adventure_society')
    if society is None:return
    farms={a.settlements[0]:a for a in world.infrastructure.assets.values() if a.kind=='spirit_coin_farm'}
    living=world.living_by_settlement()
    demand=_coin_demand(world,society,living)
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
        denomination=denomination_for_rank(tier)
        coins=_farm_output(tier,max(1,int(24*farm.condition)),demand,world.currency.treasuries.get(society.id,{}))
        produced_tier=max(rank for rank in range(1,tier+1) if coins.get(denomination_for_rank(rank),0))
        world.currency.credit(farmer.id,coins)
        e=world.emit('spirit_coins_cultivated',Layer.REALITY,(Ref('person',farmer.id),),Ref('settlement',sid),(farm.origin_event,),farm=farm.id,ambient=ambient,production_rank=produced_tier,capacity_rank=tier,challenge_complexity=produced_tier,used_abilities=(operator.semantic_key,),coin_created=coins,mechanism='worked ambient coin cultivation')
        record_application(world,farmer,operator,e,constraint=f'cultivation:{sid}:{int(world.local[sid].rain*4)}',difficulty=produced_tier,outcome=float(coins[denomination_for_rank(produced_tier)]))
        levy={d:n//2 for d,n in coins.items() if n//2}
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


SERVICE_FUNCTIONS={'healing':{'recovery','healing','restoration'},
               'protection':{'control','support','enhancement','detection','sense','creation','defense','preservation','storage','environmental control'},
               'instruction':{'communication','influence','analysis','guidance','coordination','prediction','teamwork'},
               'provision':{'creation','transformation','control','exchange'}}

def magical_service(world,provider,client,ability,*,kind,difficulty,constraint):
    """A priced service changes a real client/household state; no work, no proof.

    Function eligibility, actual need, tier capability, liquidity and successful
    output all precede evidence. Lower-tier clients cannot buy higher-tier work
    using a flattened ordinary-wealth scalar.
    """
    Layer,Ref=layer_ref()
    if ability.function not in SERVICE_FUNCTIONS.get(kind,()) or ability.rank<difficulty:return False
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
            # Every attempt has the same payer, price and difficulty. A missing
            # denomination makes all attempts impossible before ability lookup.
            if world.currency.wallets.get(client.id,{}).get(denomination_for_rank(difficulty),0)<2:continue
            candidates=(a for a in path.abilities if a.function in SERVICE_FUNCTIONS[kind] and a.rank>=difficulty)
            for ability in sorted(candidates,key=lambda a:(a.rank,a.level,a.semantic_key)):
                # Disease/embodiment, ecology and household conditions define cases.
                constraint=f'{kind}:{client.species}:{sid}:{int(world.local[sid].scarcity*4)}'
                if magical_service(world,p,client,ability,kind=kind,difficulty=difficulty,constraint=constraint):break


def apprenticeship_step(world):
    """Paid public work supports committed trainees; no essence is handed out.

    Three places per existing Society branch, funded from its actual treasury.
    Incomplete trainees have continuity; completion releases the place. Wages
    buy real market stock at normal prices and support repeated generations.
    """
    from .magic_resources import _aspiration
    Layer,Ref=layer_ref();inst=world.institutions.institution_by_kind('adventure_society')
    if inst is None:return
    for sid,people in sorted(world.living_by_settlement().items()):
        branch=world.institutions.branch_for('adventure_society',sid)
        if branch is None:continue
        candidates=[]
        for p in people:
            if not p.alive or p.age<16:continue
            path=world.advancement.path(p.id)
            if path and len(path.abilities)==20:continue
            aspiration=_aspiration(world,p)
            if not aspiration.completion_goal or aspiration.drive<.4:continue
            candidates.append(p)
        candidates.sort(key=lambda p:(-(len(world.advancement.path(p.id).abilities) if world.advancement.path(p.id) else 0),-_aspiration(world,p).preparation,-p.curiosity,p.id))
        for p in candidates[:3]:
            if world.currency.treasuries.get(inst.id,{}).get('iron',0)<4:break
            # Existing infrastructure continuously needs maintenance; saturating
            # a permanent defense scalar must not erase work for later centuries.
            assets=[a for a in world.infrastructure.assets.values() if sid in a.settlements and a.condition<1.]
            if not assets:continue
            asset=min(assets,key=lambda a:(a.condition,a.id));before=asset.condition
            world.infrastructure.maintain(asset.id,.2*(.5+p.health));effect=asset.condition-before
            if effect<=0:continue
            world.skills.practice(p.id,'construction',.2)
            coins=world.currency.treasury_transfer(inst.id,p.id,{'iron':4})
            world.emit('society_apprentice_work',Layer.SOCIETY,(Ref('person',p.id),Ref('institution',inst.id)),Ref('settlement',sid),
                branch=branch.id,work='public infrastructure maintenance',infrastructure=asset.id,improvement=effect,coin_reward=coins,treasury=inst.id,eligibility='committed incomplete path')


def society_change_step(world):
    """Exchange existing coins at par; keep two annual branch payrolls in change.

    Completed users keep twenty Iron for expenses. No coins are minted, broken,
    or flattened into a scalar balance; both counterparties must have inventory.
    """
    from .currency import COIN_VALUE
    society=world.institutions.institution_by_kind('adventure_society')
    if society is None:return
    target=24*len(society.branches)
    treasury=world.currency.treasuries.get(society.id,{})
    if treasury.get('iron',0)>=target:return
    Layer,Ref=layer_ref()
    for p in world.current_people():
        if not p.alive or p.rank<1:continue
        surplus=max(0,world.currency.wallets.get(p.id,{}).get('iron',0)-20)
        for denomination in ('bronze','silver','gold','diamond'):
            ratio=COIN_VALUE[denomination]//COIN_VALUE['iron']
            deficit=target-treasury.get('iron',0)
            if deficit<=0:return
            count=min(treasury.get(denomination,0),surplus//ratio,(deficit+ratio-1)//ratio)
            if count<=0:continue
            change={'iron':count*ratio};payment={denomination:count}
            world.currency.treasury_transfer(society.id,p.id,change,deposit=True)
            world.currency.treasury_transfer(society.id,p.id,payment)
            world.emit('society_change_exchanged',Layer.SOCIETY,(Ref('person',p.id),Ref('institution',society.id)),Ref('settlement',p.settlement),
                coin_deposit=change,institution=society.id,coin_reward=payment,treasury=society.id,
                mechanism='equal-value exchange of existing coins',retained_iron=20)
            surplus-=count*ratio
