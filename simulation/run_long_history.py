from collections import Counter, defaultdict
import json
import sys
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


def lineage_depth(world, pid, memo):
    if pid in memo:return memo[pid]
    parents=world.genealogy.parents.get(pid,())
    if not parents:memo[pid]=0;return 0
    memo[pid]=1+max(lineage_depth(world,p,memo) for p in parents if p in world.people);return memo[pid]


def snapshot(world):
    alive=[p for p in world.people.values() if p.alive]
    by_settlement=Counter(p.settlement for p in alive);by_species=Counter(p.species for p in alive);events=Counter(e.kind for e in world.events)
    practices_by_origin=Counter(p.origin_settlement for p in world.culture.practices.values());practice_domains=Counter(p.domain for p in world.culture.practices.values());adoption_by_settlement=defaultdict(list)
    for (sid,pid),value in world.culture.adoption.items():
        if value>=.20:adoption_by_settlement[sid].append((pid,round(value,3)))
    cultural_signatures={str(sid):sorted(vals,key=lambda x:(-x[1],x[0]))[:8] for sid,vals in adoption_by_settlement.items()};memo={};max_depth=max((lineage_depth(world,p.id,memo) for p in world.people.values()),default=0);living_households=sum(1 for h in world.households.values() if h.alive and any(world.people[i].alive for i in h.members))
    paths=world.advancement.paths;living_users=[p for p in alive if p.id in paths];base_counts=Counter(len(paths[p.id].base_essences) for p in living_users);ability_counts=Counter(len(paths[p.id].abilities) for p in living_users);rank_counts=Counter(world.advancement.rank(p.id) for p in living_users);confluences=sum(1 for p in living_users if paths[p.id].confluence is not None);completed=sum(1 for p in living_users if len(paths[p.id].abilities)==20);auras=sum(sum(a.aura for a in paths[p.id].abilities) for p in living_users)
    resources=list(world.magic_resources.resources.values());available=[r for r in resources if r.consumed_year is None];resource_kinds=Counter(r.kind for r in resources);available_kinds=Counter(r.kind for r in available);inst_kinds=Counter(i.kind for i in world.institutions.institutions.values());notice_status=Counter(n.status for n in world.institutions.notices.values());disclosures=Counter(r.disclosure for r in world.institutions.magic_records.values())
    return {
        'year':world.year,'alive':len(alive),'people_total':len(world.people),'living_households':living_households,'households_total':len(world.households),'settlement_population':dict(sorted(by_settlement.items())),'species_population':dict(sorted(by_species.items())),'events_total':len(world.events),'event_kinds':dict(events.most_common(25)),'practices':len(world.culture.practices),'practice_domains':dict(sorted(practice_domains.items())),'practice_origins':dict(sorted(practices_by_origin.items())),'culture_institutions':len(world.culture.institutions),'laws':len(world.culture.laws),'properties':len(world.economy.property),'relationships':len(world.social.edges),'genealogical_births':len(world.genealogy.parents),'max_lineage_depth':max_depth,'knowledge_claims':len(world.knowledge.claims),'cultural_signatures':cultural_signatures,
        'essence_users_living':len(living_users),'essence_user_base_essences':dict(sorted(base_counts.items())),'essence_user_abilities':dict(sorted(ability_counts.items())),'essence_user_ranks':dict(sorted(rank_counts.items())),'living_confluences':confluences,'completed_loadouts':completed,'living_auras':auras,
        'magic_resources_total':len(resources),'magic_resources_by_kind':dict(sorted(resource_kinds.items())),'magic_resources_available':len(available),'magic_resources_available_by_kind':dict(sorted(available_kinds.items())),
        'core_institutions':dict(sorted(inst_kinds.items())),'institution_branches':len(world.institutions.branches),'magic_registry_records':len(world.institutions.magic_records),'magic_registry_disclosure':dict(sorted(disclosures.items())),'adventure_notices':len(world.institutions.notices),'adventure_notice_status':dict(sorted(notice_status.items())),'digest':world.digest(),
    }


def main(seed=843000, years=1000):
    world=generate_world(seed);sim=Simulation(world);marks=[m for m in (100,300,500,750,1000) if m<=years];last=0
    for mark in marks:
        sim.run(mark-last);print(json.dumps(snapshot(world),sort_keys=True));last=mark
    if last<years:sim.run(years-last);print(json.dumps(snapshot(world),sort_keys=True))
    if world.year!=years:raise SystemExit(f'expected year {years}, got {world.year}')
    causes={e.id for e in world.events}
    if not all(c in causes and c<e.id for e in world.events for c in e.causes):raise SystemExit('causal integrity failure')
    return world


if __name__ == '__main__':
    seed=int(sys.argv[1]) if len(sys.argv)>1 else 843000;years=int(sys.argv[2]) if len(sys.argv)>2 else 1000;main(seed,years)
