from __future__ import annotations
from collections import Counter,defaultdict
from .biology import reproductive_window

def _timing_summary(values):
 if not values:return {'samples':0,'mean':None,'median':None,'distribution':{}}
 vals=sorted(values);n=len(vals);median=vals[n//2] if n%2 else round((vals[n//2-1]+vals[n//2])/2,3)
 return {'samples':n,'mean':round(sum(vals)/n,3),'median':median,'distribution':dict(sorted(Counter(vals).items()))}

def _advancement_timing(world):
 awakened=defaultdict(list);completed_year={};rank_years=defaultdict(dict)
 for e in world.events:
  if e.kind=='ability_awakened' and e.actors:
   pid=e.actors[0].id;awakened[pid].append(e.year)
   if len(awakened[pid])==20:completed_year[pid]=e.year
  elif e.kind=='rank_advanced' and e.actors:
   pid=e.actors[0].id;rank=e.data.get('to_rank',0)
   if rank>=2:rank_years[pid].setdefault(rank,e.year)
 names={2:'bronze',3:'silver',4:'gold',5:'diamond'};out={}
 for rank,name in names.items():
  durations=[]
  for pid,years in rank_years.items():
   cy=completed_year.get(pid);ry=years.get(rank)
   if cy is not None and ry is not None and ry>=cy:durations.append(ry-cy)
  out[f'completed_to_{name}']=_timing_summary(durations)
 bronze=out['completed_to_bronze'];buckets=Counter()
 for d,count in bronze['distribution'].items():
  buckets['0-1']+=count if d<=1 else 0;buckets['2-3']+=count if 2<=d<=3 else 0;buckets['4-6']+=count if 4<=d<=6 else 0;buckets['7+']+=count if d>=7 else 0
 out['completed_to_bronze']['buckets']=dict(buckets)
 return out

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
    coin_holders=sum(1 for w in world.currency.wallets.values() if sum(w.values())>0)
    result={'year':world.year,'population':len(living),'species':dict(species),'reproductive_age':dict(reproductive),'births_cumulative':dict(births),'deaths_cumulative':dict(deaths),'death_causes':{k:dict(v) for k,v in death_causes.items()},'mixed_parent_births':dict(mixed),'essence_ranks':dict(ranks),'complete_paths':complete,'living_bronze_plus':sum(v for k,v in ranks.items() if k>=2),'living_silver_plus':sum(v for k,v in ranks.items() if k>=3),'living_gold_plus':sum(v for k,v in ranks.items() if k>=4),'living_diamonds':ranks.get(5,0),'society_members':members,'society_applications':{f'{k[0]}:{k[1]}':v for k,v in applications.items()},'magic_registry_records':len(world.institutions.magic_records),'adventure_notices':dict(notices),'wars_total':len(wars),'wars_active':sum(c.status=='war' for c in wars),'war_causes':dict(war_causes),'battles':sum(c.battles for c in wars),'war_deaths':sum(c.attacker_losses+c.defender_losses for c in wars),'society_inquiries':dict(Counter(q.status for q in inquiries)),'society_inquiry_findings':dict(findings),'ranked_coin_minted':dict(world.currency.minted),'ranked_coin_holders':coin_holders,'crafted_items':len(world.materials.items),'magical_items':magical_items}
    complete_ranks=Counter(world.advancement.rank(p.id) for p in living if (path:=world.advancement.path(p.id)) is not None and len(path.abilities)==20)
    incomplete_ranks=Counter(world.advancement.rank(p.id) for p in living if (path:=world.advancement.path(p.id)) is not None and len(path.abilities)!=20)
    result['completed_path_ranks']=dict(sorted(complete_ranks.items()))
    result['incomplete_path_ranks']=dict(sorted(incomplete_ranks.items()))
    result.update(_advancement_timing(world));return result
