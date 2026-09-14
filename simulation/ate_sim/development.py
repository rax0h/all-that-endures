from __future__ import annotations
from .core import Layer,Ref

def development_step(world,rng):
    world.infrastructure.decay(.0007)
    adults_by_settlement={sid:[] for sid in world.settlements}
    for p in world.current_people():
        if p.alive and p.age>=18:adults_by_settlement[p.settlement].append(p)
    for sid,s in world.settlements.items():
        adults=adults_by_settlement[sid]
        if not adults:continue
        q=world.local[sid];rr=rng.stream('development',world.year,sid)
        domain='agriculture' if q.scarcity>.10 else ('construction' if s.roads<.35 or s.irrigation<.35 else 'craft')
        workers=sorted(adults,key=lambda p:(-p.curiosity,p.id))[:max(1,min(8,len(adults)//8+1))]
        for p in workers:world.skills.practice(p.id,domain,.08+.10*p.curiosity)
        skilled=sorted(adults,key=lambda p:world.skills.get(p.id,domain).level,reverse=True)
        if len(skilled)>1 and world.skills.get(skilled[0].id,domain).level>.12 and rr.random()<.10:
            teacher=skilled[0];student=skilled[-1];level=world.skills.teach(teacher.id,student.id,domain,.72)
            e=world.emit('skill_taught',Layer.KNOWLEDGE,(Ref('person',teacher.id),Ref('person',student.id)),Ref('settlement',sid),domain=domain,level=round(level,4));world.transmission.record(world.year,'apprenticeship','skill',0,'person',teacher.id,'person',student.id,e.id,reliability=.72)
        local_assets=[a for a in world.infrastructure.assets.values() if sid in a.settlements]
        construction=sum(world.skills.get(p.id,'construction').level for p in adults)/max(1,len(adults))
        for asset in local_assets:
            if asset.kind in ('irrigation','road'):
                effort=.002+.010*construction*s.prosperity
                world.infrastructure.maintain(asset.id,effort)
        irrigation=[a for a in local_assets if a.kind=='irrigation']
        if irrigation:s.irrigation=max(.03,min(1.,sum(a.condition for a in irrigation)/len(irrigation)))
    # Trade routes become physical roads only after repeated use; history builds infrastructure.
    for (a,b),route in sorted(world.trade_routes.items()):
        existing=[x for x in world.infrastructure.assets.values() if x.kind=='road' and set(x.settlements)=={a,b}]
        if not existing and route.exchanges>=8:
            e=world.emit('road_established',Layer.SOCIETY,location=Ref('settlement',a),destination=b,exchanges=route.exchanges)
            road=world.infrastructure.create('road',(a,b),min(.65,.18+route.strength),20+80*route.strength,world.year,e.id);world.lineage.register('infrastructure',road.id,(('settlement',a),('settlement',b)),e.id,world.year)
        roads=[x for x in world.infrastructure.assets.values() if x.kind=='road' and a in x.settlements]
        if roads:world.settlements[a].roads=max(.03,min(1.,sum(x.condition for x in roads)/len(roads)))
        roads=[x for x in world.infrastructure.assets.values() if x.kind=='road' and b in x.settlements]
        if roads:world.settlements[b].roads=max(.03,min(1.,sum(x.condition for x in roads)/len(roads)))
