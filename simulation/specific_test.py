from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation

RARITIES=('common','uncommon','rare','epic','legendary','mythic','transcendent')

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
 resources=list(world.magic_resources.resources.values());asp=list(world.magic_resources.aspirations.values());events=Counter(e.kind for e in world.events)
 return {'living_users':sum(u['alive'] for u in users),'all_users':len(users),'rank_distribution':dict(sorted(Counter(u['rank'] for u in users if u['alive']).items())),'ability_count_distribution':dict(sorted(Counter(u['abilities'] for u in users if u['alive']).items())),'full_essence_users':sum(u['alive'] and u['confluence'] is not None for u in users),'completed_loadouts':sum(u['alive'] and u['abilities']==20 for u in users),'aspiration_desired_base':dict(sorted(Counter(a.desired_base_essences for a in asp).items())),'active_seekers':sum(a.desired_base_essences>0 for a in asp),'resources_total':len(resources),'resources_available':sum(r.consumed_year is None for r in resources),'resource_kinds':dict(Counter(r.kind for r in resources)),'purchases':events['magic_resource_purchased'],'transfers':events['magic_resource_transferred'],'inheritances':events['magic_resource_inherited'],'recoveries':events['magic_resource_recovered'],'users':users}

def history_report(world):
 events=Counter(e.kind for e in world.events);memo={};alive=[p for p in world.people.values() if p.alive];route_exchanges=sum(r.exchanges for r in world.trade_routes.values())
 transactions={k:events[k] for k in ('trade_exchange','material_purchased','magic_resource_purchased','magic_resource_transferred','property_inherited','inheritance')}
 return {'year':world.year,'alive':len(alive),'people_total':len(world.people),'settlement_population':dict(Counter(p.settlement for p in alive)),'species_population':dict(Counter(p.species for p in alive)),'births':events['birth'],'deaths':events['death'],'resurrections':events['resurrection'],'migrations':events['household_migrated'],'trade_route_exchanges':route_exchanges,'economic_transaction_events':transactions,'trade_note':'trade_exchange is an aggregate inter-settlement food-route shipment, not an individual market transaction','events_total':len(world.events),'top_event_kinds':dict(events.most_common(40)),'properties':len(world.economy.property),'relationships':len(world.social.edges),'practices':len(world.culture.practices),'institutions':len(world.culture.institutions),'laws':len(world.culture.laws),'knowledge_claims':len(world.knowledge.claims),'max_lineage_depth':max((_lineage_depth(world,p.id,memo) for p in world.people.values()),default=0)}

def institution_report(world):
 inst=[{'id':i.id,'kind':i.kind,'name':i.name,'founded_year':i.founded_year,'branches':list(i.branches),'members':len(i.members)} for i in sorted(world.institutions.institutions.values(),key=lambda x:x.id)];apps=list(world.institutions.applications.values());return {'institutions':inst,'branches':len(world.institutions.branches),'magic_records':len(world.institutions.magic_records),'society_applications':len(apps),'application_stages':dict(Counter(a.stage for a in apps)),'adventure_notices':len(world.institutions.notices),'open_notices':sum(n.status=='open' for n in world.institutions.notices.values())}

def metaphysics_report(world):
 souls=list(world.metaphysics.souls.values());churches=list(world.divinity.churches.values());return {'gods':len(world.divinity.gods),'churches':len(churches),'churches_by_god':dict(sorted(Counter(c.god for c in churches).items())),'clergy':sum(len(c.clergy) for c in churches),'followers':sum(len(c.followers) for c in churches),'manifestations':sum(len(g.manifestations) for g in world.divinity.gods.values()),'outworlders':sum(s.outworlder for s in souls),'resurrection_tokens':len(world.metaphysics.resurrection_tokens),'transcendent_mortals':dict(Counter(s.ontology for s in souls if s.ontology!='mortal'))}

def _lot_audit(world,lot):
 transfer_events=[e for e in world.events if e.id in set(lot.transfers)]
 return {'lot':lot.id,'kind':lot.kind,'created_year':lot.created_year,'settlement':lot.settlement,'producer':lot.producer,'origin_event':lot.origin_event,'quantity':round(lot.quantity,3),'consumed':round(lot.consumed,3),'remaining':round(max(0.,lot.quantity-lot.consumed),3),'quality':round(lot.quality,3),'material_rank':lot.material_rank,'magical_properties':list(lot.magical_properties),'current_owner':[lot.owner_kind,lot.owner_id],'transfers':[{'event':e.id,'year':e.year,'kind':e.kind,'actors':[[a.kind,a.id] for a in e.actors],'data':e.data} for e in transfer_events]}

def _item_audit(world,item):
 lots=[world.materials.lots[x] for x in item.materials if x in world.materials.lots]
 return {'item':item.id,'kind':item.kind,'created_year':item.created_year,'settlement':item.settlement,'craftsperson':item.craftsperson,'origin_event':item.origin_event,'quality':round(item.quality,3),'rarity':item.rarity,'item_rank':item.item_rank,'magical':item.magical,'magical_properties':list(item.magical_properties),'owner':[item.owner_kind,item.owner_id],'materials':[ _lot_audit(world,l) for l in lots ]}

def craft_report(world):
 lots=list(world.materials.lots.values());items=list(world.materials.items.values());mag=[l for l in lots if l.magical_properties];notable=sorted(items,key=lambda x:(RARITIES.index(x.rarity),x.quality),reverse=True)[:12]
 by_crafter=defaultdict(list)
 for i in items:by_crafter[i.craftsperson].append(i)
 craft_lives=[]
 for pid,made in by_crafter.items():
  p=world.people.get(pid);supplier_ids=set();purchased=0
  for i in made:
   for lid in i.materials:
    lot=world.materials.lots.get(lid)
    if lot and lot.producer!=pid:supplier_ids.add(lot.producer)
    if lot and lot.transfers:purchased+=1
  craft_lives.append({'person':pid,'alive':bool(p and p.alive),'age':None if p is None else p.age,'occupation':None if p is None else p.occupation,'rank':world.advancement.rank(pid),'settlement':None if p is None else p.settlement,'wealth':None if p is None else round(p.wealth,3),'items_made':len(made),'first_year':min(i.created_year for i in made),'last_year':max(i.created_year for i in made),'kinds':dict(Counter(i.kind for i in made)),'rarities':dict(Counter(i.rarity for i in made)),'magical_items':sum(i.magical for i in made),'external_suppliers':len(supplier_ids),'purchased_input_items':purchased})
 craft_lives.sort(key=lambda x:(x['items_made'],x['magical_items'],x['last_year']),reverse=True)
 return {'material_lots':len(lots),'material_kinds':dict(Counter(l.kind for l in lots)),'magical_material_lots':len(mag),'magical_properties':dict(Counter(p for l in mag for p in l.magical_properties)),'items_crafted':len(items),'item_rarities':dict(Counter(i.rarity for i in items)),'magical_items':sum(i.magical for i in items),'craftspeople':len(by_crafter),'material_purchases':sum(1 for e in world.events if e.kind=='material_purchased'),'notable_item_forensics':[_item_audit(world,i) for i in notable],'top_craftspeople':craft_lives[:20],'magical_lot_forensics':[_lot_audit(world,l) for l in mag[:20]]}

def story_report(world):
 ranked=[]
 for pid,path in world.advancement.paths.items():
  p=world.people.get(pid)
  if p:ranked.append((len(path.base_essences),len(path.abilities),world.advancement.rank(pid),p.age,pid))
 ranked.sort(reverse=True);items=sorted(world.materials.items.values(),key=lambda i:(RARITIES.index(i.rarity),i.quality),reverse=True)
 return {'top_magical_lives':[{'person':pid,'base_essences':b,'abilities':a,'rank':r,'age':age,'alive':world.people[pid].alive,'settlement':world.people[pid].settlement,'occupation':world.people[pid].occupation} for b,a,r,age,pid in ranked[:12]],'top_crafted_objects':[_item_audit(world,i) for i in items[:8]],'writing_audit_note':'These are evidence packets, not a claim that player-facing prose has passed literary review. Use them as the factual basis for prose/dialogue inspection.'}

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
