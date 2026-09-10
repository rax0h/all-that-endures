from __future__ import annotations
import argparse
import json
from collections import Counter
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


def _lineage_depth(world,pid,memo):
    if pid in memo:return memo[pid]
    parents=world.genealogy.parents.get(pid,())
    if not parents:memo[pid]=0;return 0
    known=[p for p in parents if p in world.people]
    memo[pid]=1+(max(_lineage_depth(world,p,memo) for p in known) if known else 0);return memo[pid]

def magic_report(world):
    users=[]
    for pid,path in sorted(world.advancement.paths.items()):
        person=world.people.get(pid)
        if person is None:continue
        users.append({'person':pid,'alive':person.alive,'age':person.age,'species':person.species,'settlement':person.settlement,'rank':world.advancement.rank(pid),'base_essences':list(path.base_essences),'confluence':path.confluence,'confluence_name':path.confluence_name,'abilities':len(path.abilities),'specials':sum(a.special for a in path.abilities),'auras':sum(a.aura for a in path.abilities),'ability_names':[a.name for a in path.abilities]})
    resources=list(world.magic_resources.resources.values())
    return {'living_users':sum(1 for u in users if u['alive']),'all_users':len(users),'rank_distribution':dict(sorted(Counter(u['rank'] for u in users if u['alive']).items())),'ability_count_distribution':dict(sorted(Counter(u['abilities'] for u in users if u['alive']).items())),'full_essence_users':sum(1 for u in users if u['alive'] and u['confluence'] is not None),'completed_loadouts':sum(1 for u in users if u['alive'] and u['abilities']==20),'invalid_completed_auras':[u['person'] for u in users if u['abilities']==20 and u['auras']!=1],'resources_total':len(resources),'resources_available':sum(r.consumed_year is None for r in resources),'resource_kinds':dict(Counter(r.kind for r in resources)),'users':users}

def history_report(world):
    events=Counter(e.kind for e in world.events);memo={};alive=[p for p in world.people.values() if p.alive]
    return {'year':world.year,'alive':len(alive),'people_total':len(world.people),'settlement_population':dict(Counter(p.settlement for p in alive)),'species_population':dict(Counter(p.species for p in alive)),'births':events['birth'],'deaths':events['death'],'resurrections':events['resurrection'],'migrations':events['household_migrated'],'trade_exchanges':events['trade_exchange'],'events_total':len(world.events),'top_event_kinds':dict(events.most_common(35)),'properties':len(world.economy.property),'relationships':len(world.social.edges),'practices':len(world.culture.practices),'institutions':len(world.culture.institutions),'laws':len(world.culture.laws),'knowledge_claims':len(world.knowledge.claims),'max_lineage_depth':max((_lineage_depth(world,p.id,memo) for p in world.people.values()),default=0)}

def institution_report(world):
    inst=[{'id':i.id,'kind':i.kind,'name':i.name,'founded_year':i.founded_year,'branches':list(i.branches),'members':len(i.members)} for i in sorted(world.institutions.institutions.values(),key=lambda x:x.id)]
    apps=list(world.institutions.applications.values())
    return {'institutions':inst,'branches':len(world.institutions.branches),'magic_records':len(world.institutions.magic_records),'magic_disclosures':dict(Counter(r.disclosure for r in world.institutions.magic_records.values())),'society_applications':len(apps),'application_stages':dict(Counter(a.stage for a in apps)),'adventure_notices':len(world.institutions.notices),'open_notices':sum(n.status=='open' for n in world.institutions.notices.values()),'notices':[{'id':n.id,'year':n.year,'kind':n.kind,'location':n.location,'status':n.status,'cause_event':n.cause_event} for n in sorted(world.institutions.notices.values(),key=lambda x:x.id)]}

def metaphysics_report(world):
    souls=list(world.metaphysics.souls.values());churches=list(world.divinity.churches.values())
    return {'gods':len(world.divinity.gods),'god_ids':sorted(world.divinity.gods),'churches':len(churches),'churches_by_god':dict(sorted(Counter(c.god for c in churches).items())),'clergy':sum(len(c.clergy) for c in churches),'followers':sum(len(c.followers) for c in churches),'manifestations':sum(len(g.manifestations) for g in world.divinity.gods.values()),'outworlders':sum(s.outworlder for s in souls),'resurrection_tokens':len(world.metaphysics.resurrection_tokens),'unused_resurrection_tokens':sum(t.consumed_year is None for t in world.metaphysics.resurrection_tokens.values()),'transcendent_mortals':dict(Counter(s.ontology for s in souls if s.ontology!='mortal'))}

def causal_report(world):
    ids={e.id for e in world.events};bad=[e.id for e in world.events for c in e.causes if c not in ids or c>=e.id];return {'causal_integrity':not bad,'bad_events':bad[:50],'digest':world.digest()}

def run(seed,years,section='all'):
    world=generate_world(seed);Simulation(world).run(years);out={'seed':seed,'years':years}
    if section in ('all','history'):out['history']=history_report(world)
    if section in ('all','magic'):out['magic']=magic_report(world)
    if section in ('all','institutions'):out['institutions']=institution_report(world)
    if section in ('all','metaphysics'):out['metaphysics']=metaphysics_report(world)
    if section in ('all','causal'):out['causal']=causal_report(world)
    return out

def main():
    p=argparse.ArgumentParser(description='Run a deterministic targeted All That Endures simulation probe.');p.add_argument('--seed',type=int,default=843000);p.add_argument('--years',type=int,default=100);p.add_argument('--section',choices=('all','history','magic','institutions','metaphysics','causal'),default='all');p.add_argument('--pretty',action='store_true');a=p.parse_args();print(json.dumps(run(a.seed,a.years,a.section),indent=2 if a.pretty else None,sort_keys=True))

if __name__=='__main__':main()
