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


def snapshot(world, include_digest=False):
    alive=[p for p in world.people.values() if p.alive]
    by_settlement=Counter(p.settlement for p in alive);by_species=Counter(p.species for p in alive);events=Counter(e.kind for e in world.events)
    practices_by_origin=Counter(p.origin_settlement for p in world.culture.practices.values());practice_domains=Counter(p.domain for p in world.culture.practices.values());adoption_by_settlement=defaultdict(list)
    for (sid,pid),value in world.culture.adoption.items():
        if value>=.20:adoption_by_settlement[sid].append((pid,round(value,3)))
    cultural_signatures={str(sid):sorted(vals,key=lambda x:(-x[1],x[0]))[:8] for sid,vals in adoption_by_settlement.items()};memo={};max_depth=max((lineage_depth(world,p.id,memo) for p in world.people.values()),default=0);living_households=sum(1 for h in world.households.values() if h.alive and any(world.people[i].alive for i in h.members))

    paths=world.advancement.paths;living_users=[p for p in alive if p.id in paths];base_counts=Counter(len(paths[p.id].base_essences) for p in living_users);ability_counts=Counter(len(paths[p.id].abilities) for p in living_users);rank_counts=Counter(world.advancement.rank(p.id) for p in living_users);confluences=sum(1 for p in living_users if paths[p.id].confluence is not None);completed=sum(1 for p in living_users if len(paths[p.id].abilities)==20);auras=sum(sum(a.aura for a in paths[p.id].abilities) for p in living_users)
    aspirations=[(pid,a) for pid,a in world.magic_resources.aspirations.items() if pid in world.people and world.people[pid].alive]
    interested=[(pid,a) for pid,a in aspirations if a.desired_base_essences>0];completion=[(pid,a) for pid,a in interested if a.completion_goal];adventurers=[(pid,a) for pid,a in interested if a.adventurer_aspiration]

    # Read-only Stage 0.5 access diagnostics. These derive only from existing state;
    # they must never alter aspiration, advancement, resource ownership or RNG.
    adult_ids={p.id for p in alive if p.age>=16}
    aspirant_ids={pid for pid,_ in aspirations if pid in adult_ids};interested_ids={pid for pid,_ in interested if pid in adult_ids};completion_ids={pid for pid,_ in completion if pid in adult_ids}
    completion_base=Counter();completion_abilities=Counter();search_years=[];ranked_without_complete=0
    for pid in sorted(completion_ids):
        path=paths.get(pid);bases=0 if path is None else len(path.base_essences);abilities=0 if path is None else len(path.abilities)
        completion_base[bases]+=1;completion_abilities[abilities]+=1
        search_years.append(world.magic_resources.aspirations[pid].search_years)
        if world.advancement.rank(pid)>0 and abilities!=20:ranked_without_complete+=1
    ability_bands={'0':0,'1-4':0,'5-9':0,'10-14':0,'15-19':0,'20':0}
    for n,count in completion_abilities.items():
        band='0' if n==0 else ('1-4' if n<5 else ('5-9' if n<10 else ('10-14' if n<15 else ('15-19' if n<20 else '20'))))
        ability_bands[band]+=count

    resources=list(world.magic_resources.resources.values());available=[r for r in resources if r.consumed_year is None];resource_kinds=Counter(r.kind for r in resources);available_kinds=Counter(r.kind for r in available);inst_kinds=Counter(i.kind for i in world.institutions.institutions.values());notice_status=Counter(n.status for n in world.institutions.notices.values());disclosures=Counter(r.disclosure for r in world.institutions.magic_records.values())
    available_owner=Counter((r.kind,r.owner_kind or 'unowned') for r in available);available_location=Counter((r.kind,r.location) for r in available)
    committed_need_essence=sum(1 for pid in completion_ids if paths.get(pid) is None or len(paths[pid].base_essences)<3)
    committed_need_stones=sum(1 for pid in completion_ids if paths.get(pid) is not None and len(paths[pid].abilities)<20)

    lots=list(world.materials.lots.values());items=list(world.materials.items.values());year=max(1,world.year);pop=max(1,len(alive));households=max(1,living_households)
    production_by_year=Counter(l.created_year for l in lots);production_by_settlement=Counter(l.settlement for l in lots);active_crafters={i.craftsperson for i in items if world.people.get(i.craftsperson) and world.people[i.craftsperson].alive}
    supplier_pairs={(l.producer,i.craftsperson) for i in items for lid in i.materials for l in [world.materials.lots.get(lid)] if l is not None and l.producer!=i.craftsperson}

    result={
        'year':world.year,'alive':len(alive),'people_total':len(world.people),'living_households':living_households,'households_total':len(world.households),'settlement_population':dict(sorted(by_settlement.items())),'species_population':dict(sorted(by_species.items())),'events_total':len(world.events),'event_kinds':dict(events.most_common(25)),'practices':len(world.culture.practices),'practice_domains':dict(sorted(practice_domains.items())),'practice_origins':dict(sorted(practices_by_origin.items())),'culture_institutions':len(world.culture.institutions),'laws':len(world.culture.laws),'properties':len(world.economy.property),'relationships':len(world.social.edges),'genealogical_births':len(world.genealogy.parents),'max_lineage_depth':max_depth,'knowledge_claims':len(world.knowledge.claims),'cultural_signatures':cultural_signatures,
        'essence_users_living':len(living_users),'essence_user_base_essences':dict(sorted(base_counts.items())),'essence_user_abilities':dict(sorted(ability_counts.items())),'essence_user_ranks':dict(sorted(rank_counts.items())),'living_confluences':confluences,'completed_loadouts':completed,'living_auras':auras,
        'magic_aspirants_living':len(aspirations),'magic_interested_living':len(interested),'magic_completion_goal_living':len(completion),'magic_adventurer_aspirants_living':len(adventurers),'magic_completion_goal_share':round(len(completion)/len(interested),4) if interested else 0.0,'magic_adventurer_completion_share':round(sum(a.completion_goal for _,a in adventurers)/len(adventurers),4) if adventurers else 0.0,
        'magic_access_adults':len(adult_ids),'magic_access_adults_with_aspiration_state':len(aspirant_ids),'magic_access_interested_adults':len(interested_ids),'magic_access_committed_adults':len(completion_ids),'magic_access_committed_base_essences':dict(sorted(completion_base.items())),'magic_access_committed_ability_bands':ability_bands,'magic_access_committed_need_essence':committed_need_essence,'magic_access_committed_need_stones':committed_need_stones,'magic_access_search_years_mean':round(sum(search_years)/len(search_years),2) if search_years else 0.0,'magic_access_search_years_max':max(search_years,default=0),'magic_access_ranked_without_20_20':ranked_without_complete,
        'magic_resources_total':len(resources),'magic_resources_by_kind':dict(sorted(resource_kinds.items())),'magic_resources_available':len(available),'magic_resources_available_by_kind':dict(sorted(available_kinds.items())),'magic_resources_available_by_owner':{f'{kind}:{owner}':count for (kind,owner),count in sorted(available_owner.items())},'magic_resources_available_by_location':{f'{kind}:{location}':count for (kind,location),count in sorted(available_location.items(),key=lambda x:(x[0][0],-1 if x[0][1] is None else x[0][1]))},'magic_resource_purchases':events['magic_resource_purchased'],'magic_resource_transfers':events['magic_resource_transferred'],'essence_absorptions':events['essence_absorbed'],'awakening_stones_used':events['awakening_stone_used'],'abilities_awakened':events['ability_awakened'],
        'material_lots_total':len(lots),'material_lots_per_year':round(len(lots)/year,3),'material_lots_per_100_living_people_year':round((len(lots)/year)/pop*100,3),'material_lots_by_settlement':dict(sorted(production_by_settlement.items())),'material_peak_lots_in_year':max(production_by_year.values(),default=0),'material_purchases':events['material_purchased'],'crafted_items_total':len(items),'crafted_items_per_100_living_households_year':round((len(items)/year)/households*100,3),'living_active_craftspeople':len(active_crafters),'supplier_relationships_observed':len(supplier_pairs),'magical_material_lots':sum(bool(l.magical_properties) for l in lots),'magical_items':sum(bool(i.magical) for i in items),
        'core_institutions':dict(sorted(inst_kinds.items())),'institution_branches':len(world.institutions.branches),'magic_registry_records':len(world.institutions.magic_records),'magic_registry_disclosure':dict(sorted(disclosures.items())),'adventure_notices':len(world.institutions.notices),'adventure_notice_status':dict(sorted(notice_status.items())),
    }
    complete_users=[p for p in living_users if len(paths[p.id].abilities)==20]
    incomplete_users=[p for p in living_users if len(paths[p.id].abilities)!=20]
    result['completed_path_ranks']=dict(sorted(Counter(world.advancement.rank(p.id) for p in complete_users).items()))
    result['incomplete_path_ranks']=dict(sorted(Counter(world.advancement.rank(p.id) for p in incomplete_users).items()))
    if include_digest:result['digest']=world.digest()
    return result


def main(seed=843000, years=1000, max_seconds=None, archive=None):
    from time import perf_counter
    import os, cProfile, pstats, io, platform
    profile_tail=int(os.environ.get('ATE_PROFILE_TAIL','0'))
    if years<=0:raise ValueError('years must be positive')
    if max_seconds is not None and (max_seconds<=0 or profile_tail):
        raise ValueError('performance gates require a positive limit and an unprofiled run')
    profiler=cProfile.Profile() if profile_tail else None
    profiled_years=0
    from scaling_telemetry import ScalingTelemetry, BUCKET_ENDS
    world=generate_world(seed);sim=Simulation(world)
    marks=sorted(set([m for m in BUCKET_ENDS if m<=years]+[years]))
    last=0;simulation_seconds=0.;diagnostic_seconds=0.
    with ScalingTelemetry(world) as telemetry:
        for mark in marks:
            start=perf_counter()
            if profiler is not None and mark==years:
                warm=max(0,years-last-profile_tail)
                sim.run(warm)
                profiled_years=years-last-warm
                profiler.enable()
                sim.run(profiled_years)
                profiler.disable()
            else:sim.run(mark-last)
            elapsed=perf_counter()-start;simulation_seconds+=elapsed
            print(json.dumps(telemetry.report(last+1,elapsed),sort_keys=True),flush=True)
            start=perf_counter()
            report=snapshot(world,include_digest=False)
            diagnostic_seconds+=perf_counter()-start
            print(json.dumps(report,sort_keys=True),flush=True)
            last=mark
    if profiler is not None:
        stream=io.StringIO()
        pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumtime').print_stats(50)
        print(json.dumps({'record':'late_profile','profiled_years':profiled_years,'text':stream.getvalue()}),flush=True)
    start=perf_counter();digest=world.digest();digest_seconds=perf_counter()-start
    start=perf_counter()
    if world.year!=years:raise SystemExit(f'expected year {years}, got {world.year}')
    if not all(c<e.id for e in world.events for c in e.causes):raise SystemExit('causal integrity failure')
    validation_seconds=perf_counter()-start
    print(json.dumps({'record':'benchmark','python_version':platform.python_version(),'platform':platform.platform(),'seed':seed,'years':years,'simulation_seconds':simulation_seconds,'profile_tail_requested':profile_tail,'diagnostic_seconds':diagnostic_seconds,'digest_seconds':digest_seconds,'validation_seconds':validation_seconds,'digest':digest,'max_seconds':max_seconds,'performance_passed':None if max_seconds is None else simulation_seconds<=max_seconds},sort_keys=True),flush=True)
    if archive is not None:
        from ate_sim.history_archive import export_archive
        print(json.dumps(export_archive(world, archive, digest=digest), sort_keys=True), flush=True)
    if max_seconds is not None and simulation_seconds>max_seconds:
        raise SystemExit(f'simulation exceeded {max_seconds:.2f}s budget: {simulation_seconds:.2f}s')
    return world


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Deterministic simulation benchmark; archive diagnostics and digest are timed separately.')
    parser.add_argument('seed',nargs='?',type=int,default=843000)
    parser.add_argument('years',nargs='?',type=int,default=1000)
    parser.add_argument('--max-seconds',type=float,help='Fail if actual simulation wall time exceeds this limit; incompatible with ATE_PROFILE_TAIL.')
    parser.add_argument('--archive', help='Create a new indexed SQLite history archive after simulation; timed separately.')
    args=parser.parse_args()
    main(args.seed,args.years,args.max_seconds,args.archive)