from __future__ import annotations
from .core import Household, Layer, Ref

def partnership_step(world,rng):
    adults=[p for p in world.people.values() if p.alive and p.age>=18]
    by_settlement={}
    for p in adults:by_settlement.setdefault(p.settlement,[]).append(p)
    paired=set()
    for a,b in world.social.partnerships:
        pa,pb=world.people.get(a),world.people.get(b)
        if pa and pb and pa.alive and pb.alive:paired.update((a,b))
    ancestry={}
    for sid,people in by_settlement.items():
        people=sorted(people,key=lambda p:p.id); n=len(people)
        for i,a in enumerate(people):
            if a.id in paired:continue
            rr=rng.stream("partnership",world.year,a.id)
            if rr.random()>.18:continue
            candidates=[]; aa=ancestry.setdefault(a.id,world.genealogy.ancestors(a.id,2))
            # Bounded deterministic neighborhood keeps the system linear enough for millennium runs.
            for offset in range(1,min(25,n)):
                b=people[(i+offset)%n]
                if b.id==a.id or b.id in paired or b.household==a.household:continue
                bb=ancestry.setdefault(b.id,world.genealogy.ancestors(b.id,2))
                if a.id in bb or b.id in aa or aa.intersection(bb):continue
                rel=world.social.get(a.id,b.id);compatibility=1-abs(a.temperament-b.temperament)
                score=.35*compatibility+.25*(a.attachment+b.attachment)/2+.20*rel.trust+.20*rel.familiarity
                candidates.append((score,b))
            if not candidates:continue
            score,b=max(candidates,key=lambda x:x[0])
            if score<.43:continue
            e=world.emit("partnership_formed",Layer.SOCIETY,(Ref("person",a.id),Ref("person",b.id)),Ref("settlement",sid),compatibility=score)
            world.social.record(a.id,b.id,e.id,trust=.12,attachment=.20,obligation=.08);world.social.partner(a.id,b.id,e.id);paired.update((a.id,b.id))
            if a.household!=b.household and rr.random()<.62:
                source=world.households[a.household];source2=world.households[b.household];nhid=world.next_household;world.next_household+=1
                share=max(4.,source.wealth*.12+source2.wealth*.12);source.wealth=max(0.,source.wealth-source.wealth*.12);source2.wealth=max(0.,source2.wealth-source2.wealth*.12)
                nh=Household(nhid,sid,wealth=share,food=8.,preparedness=max(.05,(source.preparedness+source2.preparedness)/2),lineage=source.lineage);world.households[nhid]=nh;world.settlements[sid].households.append(nhid)
                for p in (a,b):
                    old=world.households[p.household]
                    if p.id in old.members:old.members.remove(p.id)
                    nh.members.append(p.id);p.household=nhid
                he=world.emit("household_formed",Layer.SOCIETY,(Ref("person",a.id),Ref("person",b.id)),Ref("settlement",sid),(e.id,),household=nhid);world.economy.create("dwelling",sid,"household",nhid,max(5.,share*.5),world.year,he.id)

def household_split_step(world,rng):
    for hid,h in list(world.households.items()):
        living=[world.people[p] for p in h.members if world.people[p].alive];adults=[p for p in living if p.age>=18]
        if len(living)<8 or len(adults)<3:continue
        rr=rng.stream("household_split",world.year,hid)
        if rr.random()>.012:continue
        movers=sorted(adults,key=lambda p:(-p.age,p.id))[:max(1,len(adults)//3)];nhid=world.next_household;world.next_household+=1;share=h.wealth*.28;h.wealth-=share
        nh=Household(nhid,h.settlement,wealth=share,food=max(3.,h.food*.25),preparedness=max(.05,h.preparedness*.8),lineage=h.lineage);world.households[nhid]=nh;world.settlements[h.settlement].households.append(nhid)
        for p in movers:
            if p.id in h.members:h.members.remove(p.id)
            nh.members.append(p.id);p.household=nhid
        e=world.emit("household_split",Layer.SOCIETY,tuple(Ref("person",p.id) for p in movers),Ref("settlement",h.settlement),origin_household=hid,new_household=nhid);world.economy.create("dwelling",h.settlement,"household",nhid,max(5.,share*.5),world.year,e.id)

def inheritance_property_step(world):
    for prop in world.economy.property.values():
        if prop.owner_kind!="household":continue
        h=world.households.get(prop.owner_id)
        if h and h.alive:continue
        heirs=[]
        if h:
            for pid in h.members:heirs.extend(world.genealogy.children.get(pid,[]))
        heirs=[pid for pid in heirs if pid in world.people and world.people[pid].alive]
        if heirs:
            heir=min(heirs);e=world.emit("property_inherited",Layer.SOCIETY,(Ref("person",heir),),Ref("settlement",prop.settlement),property=prop.id);world.economy.transfer(prop.id,"person",heir,e.id)

def household_step(world,rng):partnership_step(world,rng);household_split_step(world,rng);inheritance_property_step(world)
