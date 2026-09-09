from __future__ import annotations
from math import hypot
from .core import Layer, Ref, TradeRoute
from .culture import Institution, Law

def _distance(world,a:int,b:int)->float:
    sa,sb=world.settlements[a],world.settlements[b]
    return max(1.0,hypot(sa.x-sb.x,sa.y-sb.y))

def _household_living(world,hid:int):
    return [world.people[pid] for pid in world.households[hid].members if world.people[pid].alive]

def _settlement_population(world,sid:int): return sum(p.alive and p.settlement==sid for p in world.people.values())

def _capacity(world,sid:int):
    s=world.settlements[sid]; c=world.cells[(s.x,s.y)]
    return max(24.,90.+150.*c.fertility+55.*s.irrigation+35.*s.roads-45.*c.hazard)

def _move_household(world,hid:int,destination:int,cause:int|None=None):
    h=world.households[hid];origin=h.settlement
    if origin==destination:return None
    if hid in world.settlements[origin].households:world.settlements[origin].households.remove(hid)
    world.settlements[destination].households.append(hid);h.settlement=destination
    for p in _household_living(world,hid):p.settlement=destination
    causes=() if cause is None else (cause,)
    event=world.emit("household_migrated",Layer.SOCIETY,tuple(Ref("person",p.id) for p in _household_living(world,hid)),Ref("settlement",destination),causes,household=hid,origin=origin,destination=destination)
    for (sid,pid),adoption in list(world.culture.adoption.items()):
        if sid==origin and adoption>.15:world.culture.adoption[(destination,pid)]=max(world.culture.adoption.get((destination,pid),0.),adoption*.28)
    return event

def migration_step(world,rng):
    ids=sorted(world.settlements)
    for hid,h in list(world.households.items()):
        living=_household_living(world,hid)
        if not h.alive or not living:continue
        origin=h.settlement;local=world.local[origin];s0=world.settlements[origin]
        crowd=max(0.,_settlement_population(world,origin)/_capacity(world,origin)-.78)
        pressure=.50*local.scarcity+.20*max(0.,.18-h.preparedness)+.15*max(0.,.2-s0.prosperity)+.45*crowd
        rr=rng.stream("migration",world.year,hid)
        if rr.random()>=.035*min(1.5,pressure):continue
        options=[]
        for dest in ids:
            if dest==origin:continue
            q=world.local[dest];s=world.settlements[dest];room=max(.05,1-_settlement_population(world,dest)/_capacity(world,dest))
            attraction=((1-q.scarcity)*.35+s.prosperity*.25+s.roads*.12+s.defense*.08+room*.35)/(_distance(world,origin,dest)**.72)
            options.append((attraction,dest))
        if options:_move_household(world,hid,max(options)[1])

def trade_step(world,rng):
    ids=sorted(world.settlements)
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            sa,sb=world.settlements[a],world.settlements[b];distance=_distance(world,a,b);key=(a,b)
            route=world.trade_routes.get(key)
            base_connectivity=(sa.roads+sb.roads+.20)/(distance**.75)
            if route is None and base_connectivity>.025:
                route=TradeRoute(a,b,strength=min(.18,.03+base_connectivity*.25),last_used=world.year);world.trade_routes[key]=route
            if route is None:continue
            route.strength=max(.01,route.strength*.9985)
            demand_a=max(0.,90.-sa.food_stock);demand_b=max(0.,90.-sb.food_stock);surplus_a=max(0.,sa.food_stock-105.);surplus_b=max(0.,sb.food_stock-105.)
            rr=rng.stream("trade",world.year,a*1000+b)
            exchange_chance=min(.75,.06+route.strength*.55+base_connectivity*.35)
            if rr.random()>exchange_chance:continue
            if surplus_a<=0 and surplus_b<=0:
                # Routes persist through non-food exchange even when food is balanced.
                amount=0.
            else:
                if surplus_b>surplus_a:a1,b1=b,a;source,target=sb,sa;surplus=surplus_b;demand=demand_a
                else:a1,b1=a,b;source,target=sa,sb;surplus=surplus_a;demand=demand_b
                amount=min(24.,surplus*.16,max(4.,demand+4.));source.food_stock-=amount;target.food_stock+=amount
            route.exchanges+=1;route.last_used=world.year;route.strength=min(1.,route.strength+.012+.002*amount)
            sa.prosperity=min(1.,sa.prosperity+.0015*(1+amount));sb.prosperity=min(1.,sb.prosperity+.0015*(1+amount))
            e=world.emit("trade_exchange",Layer.SOCIETY,location=Ref("settlement",b),origin=a,destination=b,food=round(amount,3),route_strength=route.strength)
            for (sid,pid),adoption in list(world.culture.adoption.items()):
                if sid==a and adoption>.30:world.culture.adoption[(b,pid)]=max(world.culture.adoption.get((b,pid),0.),adoption*(.035+.07*route.strength))
                elif sid==b and adoption>.30:world.culture.adoption[(a,pid)]=max(world.culture.adoption.get((a,pid),0.),adoption*(.035+.07*route.strength))
            claim=world.knowledge.claim("trade_route",f"{a}:{b} is viable",True,e.id)
            for p in [x for x in world.people.values() if x.alive and x.settlement in (a,b)][:12]:world.knowledge.beliefs[(p.id,claim)]=min(.95,.55+.35*route.strength)

def institution_step(world,rng):
    for sid,s in world.settlements.items():
        existing=[i for i in world.culture.institutions.values() if i.settlement==sid];strong=[pid for (place,pid),adopt in world.culture.adoption.items() if place==sid and adopt>.62];rr=rng.stream("institutions",world.year,sid)
        if strong and len(existing)<4 and rr.random()<.006*(1+s.prosperity):
            institution_kind=world.culture.practices[strong[0]].domain+" guild";iid=world.culture.next_institution;world.culture.next_institution+=1;inst=Institution(iid,sid,institution_kind,world.year,set(strong[:4]),authority=.18+s.prosperity*.25,assets=20+s.prosperity*80,legitimacy=.45);world.culture.institutions[iid]=inst;world.emit("institution_founded",Layer.SOCIETY,location=Ref("settlement",sid),institution=iid,institution_kind=institution_kind);existing.append(inst)
        for inst in existing:
            success=sum(world.culture.adoption.get((sid,p),0.) for p in inst.practices)/max(1,len(inst.practices));inst.legitimacy=max(0.,min(1.,inst.legitimacy+.002*(success-.35)))
            for pid in inst.practices:world.culture.adoption[(sid,pid)]=min(1.,world.culture.adoption.get((sid,pid),0.)+.0015*inst.legitimacy)

def law_step(world,rng):
    for sid,s in world.settlements.items():
        local=world.local[sid];laws=[law for law in world.culture.laws.values() if law.settlement==sid];rr=rng.stream("law",world.year,sid);need=max(local.scarcity,world.cells[(s.x,s.y)].hazard-s.defense)
        if len(laws)<3 and rr.random()<.004*(1+need):
            domain="resource" if local.scarcity>.2 else "security";lid=world.culture.next_law;world.culture.next_law+=1;e=world.emit("law_adopted",Layer.SOCIETY,location=Ref("settlement",sid),law=lid,domain=domain);law=Law(lid,sid,domain,strictness=.25+.45*need,enforcement=.15+.45*s.defense,origin_event=e.id);world.culture.laws[lid]=law;laws.append(law)
        for law in laws:
            if law.domain=="security":s.defense=min(1.,s.defense+.0008*law.enforcement)
            elif law.domain=="resource":s.food_stock+=.04*law.enforcement

def civilization_step(world,rng):
    migration_step(world,rng);trade_step(world,rng);institution_step(world,rng);law_step(world,rng)
