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
    """Run a demand-bounded magical service market.

    Ranked practitioners can be numerous in a mature civilization; client need,
    liquidity and local market throughput are the limiting factors. Never run one
    synthetic service attempt per ranked provider per year.
    """
    living=world.living_by_settlement() if living is None else living
    for sid,people in sorted(living.items()):
        clients=[p for p in people if p.alive and world.currency.wallets.get(p.id)]
        providers=[p for p in people if p.alive and p.rank>=1]
        if not clients or not providers:continue
        requests=[]
        for client in clients:
            household=world.households[client.household]
            if client.health<.9:
                kind='healing';need=1-client.health
            elif household.food<3:
                kind='provision';need=3-household.food
            elif world.year%2==0 and world.skills.get(client.id,'knowledge').level<.7:
                kind='instruction';need=.7-world.skills.get(client.id,'knowledge').level
            elif household.preparedness<.8:
                kind='protection';need=.8-household.preparedness
            else:continue
            requests.append((need,client.id,client,kind))
        if not requests:continue
        requests.sort(key=lambda x:(-x[0],x[1]))
        # Local demand and transaction capacity, not provider count, bound work.
        slots=min(12,max(2,len(people)//40),len(requests))
        ordered_providers=sorted(providers,key=lambda p:(-p.rank,-world.skills.get(p.id,'knowledge').level,p.id))
        for _,_,client,kind in requests[:slots]:
            difficulty=max(1,client.rank if kind=='healing' else supported_rank(world.ambient_magic.field(sid).level))
            start=int(rng.stream('magical_service_market',world.year,client.id).random()*len(ordered_providers))%len(ordered_providers)
            # Try only a bounded provider window; an unmet request can remain unmet.
            for offset in range(min(8,len(ordered_providers))):
                provider=ordered_providers[(start+offset)%len(ordered_providers)]
                if provider.id==client.id:continue
                path=world.advancement.path(provider.id)
                if path is None:continue
                constraint=f'{kind}:{client.species}:{sid}:{int(world.local[sid].scarcity*4)}'
                for ability in sorted(path.abilities,key=lambda a:(a.rank,a.level,a.semantic_key)):
                    if magical_service(world,provider,client,ability,kind=kind,difficulty=difficulty,constraint=constraint):
                        break
                else:
                    continue
                break


def apprenticeship_step(world,living=None):
    """Allocate real Society apprenticeship slots to suitable recruits.

    A person becomes Society-committed only when a branch has capacity, funded
    work and infrastructure that genuinely needs maintenance. Existing contracted
    trainees keep priority until they complete their path; completion releases the
    slot for another cohort. This creates a continuous Iron pipeline without a
    prevalence/rank quota or an unbounded pool of nominal completionists.
    """
    from .magic_resources import _aspiration
    Layer,Ref=layer_ref();inst=world.institutions.institution_by_kind('adventure_society')
    if inst is None:return
    living=world.living_by_settlement() if living is None else living
    treasury=world.currency.treasuries.get(inst.id,{})
    assets_by_sid={sid:[] for sid in living}
    for asset in world.infrastructure.assets.values():
        if asset.condition>=1.:continue
        for sid in asset.settlements:
            if sid in assets_by_sid:assets_by_sid[sid].append(asset)
    for assets in assets_by_sid.values():
        assets.sort(key=lambda a:(a.condition,a.id))
    for sid,people in sorted(living.items()):
        branch=world.institutions.branch_for('adventure_society',sid)
        assets=assets_by_sid.get(sid,[])
        if branch is None or not assets:continue
        open_notices=sum(world.institutions.notices[nid].status!='resolved'
                         for nid in branch.notices if nid in world.institutions.notices)
        capacity=max(4,min(18,4+int(8*branch.authority)+min(5,open_notices)))
        contracted=[];recruitable=[]
        for p in people:
            if not p.alive or p.age<16:continue
            path=world.advancement.path(p.id)
            if path and len(path.abilities)==20:continue
            a=_aspiration(world,p)
            if a.reason=='Adventure Society apprenticeship' and a.completion_goal:
                contracted.append(p);continue
            motive=world.agency.motives.get(p.id);status=0. if motive is None else motive.status
            defense=world.skills.get(p.id,'defense').level
            field_fit=(p.occupation in ('adventurer','guard','hunter','soldier')
                       or defense>=.55
                       or (a.risk_tolerance>=.58 and p.curiosity>=.48)
                       or (a.risk_tolerance>=.54 and status>=.40))
            if p.health<.58 or not field_fit:continue
            score=(.24*p.health+.20*a.risk_tolerance+.18*p.curiosity
                   +.14*(1-p.inhibition)+.12*min(1.,defense/2.)+.12*status)
            threshold=.58-.16*min(1.,.42+.30*branch.authority+.035*min(6,open_notices))
            if score<threshold:continue
            recruitable.append((score,p))
        contracted.sort(key=lambda p:(
            -(len(world.advancement.path(p.id).abilities) if world.advancement.path(p.id) else 0),
            -_aspiration(world,p).preparation,p.id))
        recruitable.sort(key=lambda x:(-x[0],x[1].id))
        selected=list(contracted[:capacity])
        selected_ids={p.id for p in selected}
        for _,p in recruitable:
            if len(selected)>=capacity:break
            if p.id in selected_ids:continue
            selected.append(p);selected_ids.add(p.id)
        for p in selected:
            if treasury.get('iron',0)<4:break
            asset=next((a for a in assets if a.condition<1.),None)
            if asset is None:break
            before=asset.condition
            world.infrastructure.maintain(asset.id,.2*(.5+p.health))
            effect=asset.condition-before
            if effect<=0:continue
            a=_aspiration(world,p)
            newly_recruited=not (a.reason=='Adventure Society apprenticeship' and a.completion_goal)
            if newly_recruited:
                a.adventurer_aspiration=True;a.completion_goal=True
                a.desired_base_essences=3;a.desired_abilities=20
                a.reason='Adventure Society apprenticeship'
                a.drive=max(a.drive,.46);a.urgency=max(a.urgency,.48)
                world.emit('society_apprentice_recruited',Layer.SOCIETY,
                    (Ref('person',p.id),Ref('institution',inst.id)),Ref('settlement',sid),
                    branch=branch.id,capacity=capacity,basis='funded field apprenticeship')
            world.skills.practice(p.id,'construction',.2)
            world.skills.practice(p.id,'defense',.08)
            a.preparation=min(1.,a.preparation+.025);a.urgency=max(a.urgency,.48)
            coins=world.currency.treasury_transfer(inst.id,p.id,{'iron':4})
            world.emit('society_apprentice_work',Layer.SOCIETY,
                (Ref('person',p.id),Ref('institution',inst.id)),Ref('settlement',sid),
                branch=branch.id,work='public infrastructure maintenance',
                infrastructure=asset.id,improvement=effect,coin_reward=coins,
                treasury=inst.id,eligibility='funded Society apprenticeship',
                training_contract=True)
