from __future__ import annotations
from collections import Counter,defaultdict
from .biology import reproductive_window

def _advancement_timing(world):
 awakened=defaultdict(list);bronze_year={};completed_year={}
 for e in world.events:
  if e.kind=='ability_awakened' and e.actors:
   pid=e.actors[0].id;awakened[pid].append(e.year)
   if len(awakened[pid])==20:completed_year[pid]=e.year
  elif e.kind=='rank_advanced' and e.actors and e.data.get('to_rank',0)>=2:
   bronze_year.setdefault(e.actors[0].id,e.year)
 durations=[]
 for pid,by in bronze_year.items():
  cy=completed_year.get(pid)
  if cy is not None and by>=cy:durations.append(by-cy)
 buckets=Counter()
 for d in durations:
  buckets['0-1']+=d<=1;buckets['2-3']+=2<=d<=3;buckets['4-6']+=4<=d<=6;buckets['7+']+=d>=7
 return {'completed_to_bronze_samples':len(durations),'completed_to_bronze_years':dict(sorted(Counter(durations).items())),'completed_to_bronze_buckets':dict(buckets),'completed_to_bronze_mean':(round(sum(durations)/len(durations),3) if durations else None)}

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
    applications=Counter((a.society,a.stage) for a in world.institutions.applications.values())
    members={kind:(0 if (i:=world.institutions.institution_by_kind(kind)) is None else len(i.members)) for kind in ('adventure_society','magic_society')}
    notices=Counter(n.status for n in world.institutions.notices.values())
    wars=list(world.warfare.conflicts.values());magical_items=sum(1 for x in world.materials.items.values() if x.magical)
    inquiries=list(world.society_accountability.inquiries.values());findings=Counter(f for q in inquiries for f in q.findings)
    war_causes=Counter(c.cause for c in wars)
    result={'year':world.year,'population':len(living),'species':dict(species),'reproductive_age':dict(reproductive),'births_cumulative':dict(births),'deaths_cumulative':dict(deaths),'death_causes':{k:dict(v) for k,v in death_causes.items()},'mixed_parent_births':dict(mixed),'essence_ranks':dict(ranks),'complete_paths':complete,'society_members':members,'society_applications':{f'{k[0]}:{k[1]}':v for k,v in applications.items()},'magic_registry_records':len(world.institutions.magic_records),'adventure_notices':dict(notices),'wars_total':len(wars),'wars_active':sum(c.status=='war' for c in wars),'war_causes':dict(war_causes),'battles':sum(c.battles for c in wars),'war_deaths':sum(c.attacker_losses+c.defender_losses for c in wars),'society_inquiries':dict(Counter(q.status for q in inquiries)),'society_inquiry_findings':dict(findings),'crafted_items':len(world.materials.items),'magical_items':magical_items}
    result.update(_advancement_timing(world));return result
