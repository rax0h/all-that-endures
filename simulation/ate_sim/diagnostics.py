from __future__ import annotations
from collections import Counter,defaultdict
from .biology import reproductive_window

def world_snapshot(world):
    living=[p for p in world.people.values() if p.alive]
    species=Counter(p.species for p in living);reproductive=Counter(p.species for p in living if reproductive_window(p))
    births=Counter();deaths=Counter();death_causes=defaultdict(Counter);mixed=Counter()
    for e in world.events:
        if e.kind=='birth':
            sp=e.data.get('species','unknown');births[sp]+=1
            if len(e.actors)>=3:
                parents=[world.people.get(x.id) for x in e.actors[1:3]]
                if all(parents) and parents[0].species!=parents[1].species:mixed[sp]+=1
        elif e.kind=='death':
            sp=e.data.get('species','unknown');deaths[sp]+=1;death_causes[sp][e.data.get('cause','unknown')]+=1
    ranks=Counter(world.advancement.rank(p.id) for p in living if world.advancement.essence_user(p.id))
    complete=sum(1 for p in living if (path:=world.advancement.path(p.id)) is not None and len(path.abilities)==20)
    return {'year':world.year,'population':len(living),'species':dict(species),'reproductive_age':dict(reproductive),'births_cumulative':dict(births),'deaths_cumulative':dict(deaths),'death_causes':{k:dict(v) for k,v in death_causes.items()},'mixed_parent_births':dict(mixed),'essence_ranks':dict(ranks),'complete_paths':complete}
