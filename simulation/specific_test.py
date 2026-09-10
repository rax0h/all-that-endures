from __future__ import annotations
import argparse,json
from collections import Counter
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation

def _lineage_depth(world,pid,memo):
 if pid in memo:return memo[pid]
 parents=world.genealogy.parents.get(pid,())
 if not parents:memo[pid]=0;return 0
 known=[p for p in parents if p in world.people];memo[pid]=1+(max(_lineage_depth(world,p,memo) for p in known) if known else 0);return memo[pid]
def magic_report(world):
 users=[]
 for pid,path in sorted(world.advancement.paths.items()):
  person=world.people.get(pid)
  if person is None:continue
  a=world.magic_resources.aspirations.get(pid);users.append({'person':pid,'alive':person.alive,'age':person.age,'species':person.species,'settlement':person.settlement,'rank':world.advancement.rank(pid),'base_essences':list(path.base_essences),'confluence':path.confluence,'confluence_name':path.confluence_name,'abilities':len(path.abilities),'specials':sum(x.special for x in path.abilities),'auras':sum(x.aura for x in path.abilities),'ability_names':[x.name for x in path.abilities],'aspiration':None if a is None else {'drive':round(a.drive,3),'desired_base':a.desired_base_essences,'desired_abilities':a.desired_abilities,'reason':a.reason,'search_years':a.search_years,'preparation':round(a.preparation,3)}})
 resources=list(world.magic_resources.resources.values());asp=list(world.magic_resources.aspirations.values())
 return {'living_users':sum(u['alive'] for u in users),'all_users':len(users),'rank_distribution':dict(sorted(Counter(u['rank'] for u in users if u['alive']).items())),'ability_count_distribution':dict(sorted(Counter(u['abilities'] for u in users if u['alive']).items())),'full_essence_users':sum(u['alive'] and u['confluence'] is not None for u in users),'completed_loadouts':sum(u['alive'] and u['abilities']==20 for u in users),'aspiration_desired_base':dict(sorted(Counter(a.desired_base_essences for a in asp).items())),'active_seekers':sum(a.desired_base_essences>0 for a in asp),'resources_total':len(resources),'resources_available':sum(r.consumed_year is None for r in resources),'resource_kinds':dict(Counter(r.kind for r in resources)),'users':users}
def history_report(world):
 events=Counter(e.kind for e in world.events);memo={};alive=[p for p in world.people.values() if p.alive]
 return {'year':world.year,'alive':len(alive),'people_total':len(world.people),'settlement_population':dict(Counter(p.settlement for p in alive)),'species_population':dict(Counter(p.species for p in alive)),'births':events['birth'],'deaths':events['death'],'resurrections':events['resurrection'],'migrations':events['household_migrated'],'trade_exchanges':events['trade_exchange'],'events_total':len(world.events),'top_event_kinds':dict(events.most_common(40)),'properties':len(world.economy.property),'relationships':len(world.social.edges),'practices':len(world.culture.practices),'institutions':len(world.culture.institutions),'laws':len(world.culture.laws),'knowledge_claims':len(world.knowledge.claims),'max_lineage_depth':max((_lineage_depth(world,p.id,memo) for p in world.people.values()),default=0)}
def institution_report(world):
 inst=[{'id':i.id,'kind':i.kind,'name':i.name,'founded_year':i.founded_year,'branches':list(i.branches),'members':len(i.members)} for i in sorted(world.institutions.institutions.values(),key=lambda x:x.id)];apps=list(world.institutions.applications.values());return {'institutions':inst,'branches':len(world.institutions.branches),'magic_records':len(world.institutions.magic_records),'society_applications':len(apps),'application_stages':dict(Counter(a.stage for a in apps)),'adventure_notices':len(world.institutions.notices),'open_notices':sum(n.status=='open' for n in world.institutions.notices.values())}
def metaphysics_report(world):
 souls=list(world.metaphysics.souls.values());churches=list(world.divinity.churches.values());return {'gods':len(world.divinity.gods),'churches':len(churches),'churches_by_god':dict(sorted(Counter(c.god for c in churches).items())),'clergy':sum(len(c.clergy) for c in churches),'followers':sum(len(c.followers) for c in churches),'manifestations':sum(len(g.manifestations) for g in world.divinity.gods.values()),'outworlders':sum(s.outworlder for s in souls),'resurrection_tokens':len(world.metaphysics.resurrection_tokens),'transcendent_mortals':dict(Counter(s.ontology for s in souls if s.ontology!='mortal'))}
def craft_report(world):
 lots=list(world.materials.lots.values());items=list(world.materials.items.values());mag=[l for l in lots if l.magical_properties];notable=sorted(items,key=lambda x:(('common','uncommon','rare','epic','legendary','mythic','transcendent').index(x.rarity),x.quality),reverse=True)[:20]
 return {'material_lots':len(lots),'material_kinds':dict(Counter(l.kind for l in lots)),'magical_material_lots':len(mag),'magical_properties':dict(Counter(p for l in mag for p in l.magical_properties)),'items_crafted':len(items),'item_rarities':dict(Counter(i.rarity for i in items)),'craftspeople':len(set(i.craftsperson for i in items)),'purchases':sum(1 for e in world.events if e.kind=='material_purchased'),'notable_items':[{'id':i.id,'kind':i.kind,'rarity':i.rarity,'quality':round(i.quality,3),'year':i.created_year,'settlement':i.settlement,'craftsperson':i.craftsperson,'materials':i.materials,'magical_properties':i.magical_properties} for i in notable],'magical_lots':[{'id':l.id,'kind':l.kind,'year':l.created_year,'settlement':l.settlement,'producer':l.producer,'quality':round(l.quality,3),'properties':l.magical_properties} for l in mag[:30]]}
def story_report(world):
 # Facts only: expose unusual biographies/objects for narrative inspection; prose is written outside the engine.
 ranked=[]
 for pid,path in world.advancement.paths.items():
  p=world.people.get(pid)
  if p:ranked.append((len(path.base_essences),len(path.abilities),world.advancement.rank(pid),p.age,pid))
 ranked.sort(reverse=True);items=sorted(world.materials.items.values(),key=lambda i:(('common','uncommon','rare','epic','legendary','mythic','transcendent').index(i.rarity),i.quality),reverse=True)
 return {'top_magical_lives':[{'person':pid,'base_essences':b,'abilities':a,'rank':r,'age':age,'alive':world.people[pid].alive,'settlement':world.people[pid].settlement} for b,a,r,age,pid in ranked[:12]],'top_crafted_objects':[{'item':i.id,'year':i.created_year,'kind':i.kind,'rarity':i.rarity,'craftsperson':i.craftsperson,'settlement':i.settlement,'properties':i.magical_properties,'materials':i.materials} for i in items[:12]]}
def causal_report(world):
 ids={e.id for e in world.events};bad=[e.id for e in world.events for c in e.causes if c not in ids or c>=e.id];return {'causal_integrity':not bad,'bad_events':bad[:50],'digest':world.digest()}
def run(seed,years,section='all'):
 world=generate_world(seed);Simulation(world).run(years);out={'seed':seed,'years':years}
 if section in ('all','history'):out['history']=history_report(world)
 if section in ('all','magic'):out['magic']=magic_report(world)
 if section in ('all','institutions'):out['institutions']=institution_report(world)
 if section in ('all','metaphysics'):out['metaphysics']=metaphysics_report(world)
 if section in ('all','craft'):out['craft']=craft_report(world)
 if section in ('all','stories'):out['stories']=story_report(world)
 if section in ('all','causal'):out['causal']=causal_report(world)
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=843000);p.add_argument('--years',type=int,default=100);p.add_argument('--section',choices=('all','history','magic','institutions','metaphysics','craft','stories','causal'),default='all');p.add_argument('--pretty',action='store_true');a=p.parse_args();print(json.dumps(run(a.seed,a.years,a.section),indent=2 if a.pretty else None,sort_keys=True))
if __name__=='__main__':main()