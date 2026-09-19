"""Lightweight deep-time observation run for ATE.

This is deliberately NOT a canonical validator. It uses a fresh seed, preserves
normal simulation behavior, emits broad live-state snapshots at sparse
checkpoints, and avoids archive export and canonical digest construction.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from time import perf_counter, process_time
import argparse
import json

from ate_sim.worldgen import generate_world, PEOPLES
from ate_sim.engine import Simulation

CHECKPOINTS=(1000,5000,7500,10000)
RANK_NAMES={0:'unranked',1:'iron',2:'bronze',3:'silver',4:'gold',5:'diamond'}


def _pct(values,q):
    if not values:return 0
    values=sorted(values)
    return values[min(len(values)-1,int((len(values)-1)*q))]


def _counter(d):
    return dict(sorted(d.items(),key=lambda kv:str(kv[0])))


def _interval_activity(world,start_event):
    kinds=Counter();birth_species=Counter();death_species=Counter();rank_advances=Counter()
    first_year=None;last_year=None
    for i in range(start_event,len(world.events)):
        e=world.events[i];kinds[e.kind]+=1
        if first_year is None:first_year=e.year
        last_year=e.year
        if e.kind=='birth':birth_species[e.data.get('species','unknown')]+=1
        elif e.kind=='death':death_species[e.data.get('species','unknown')]+=1
        elif e.kind=='rank_advanced':rank_advances[RANK_NAMES.get(e.data.get('to_rank',0),str(e.data.get('to_rank',0)))]+=1
    return {
        'events':len(world.events)-start_event,
        'first_event_year':first_year,'last_event_year':last_year,
        'event_kinds':_counter(kinds),
        'births_by_species':_counter(birth_species),
        'deaths_by_species':_counter(death_species),
        'rank_advances':_counter(rank_advances),
    }


def snapshot(world,start_event,founding_species,interval_wall,interval_cpu):
    alive=list(world.current_people());alive_ids={p.id for p in alive}
    species=Counter(p.species for p in alive);settlement_pop=Counter(p.settlement for p in alive)
    ages=defaultdict(list);occupations=Counter();species_settlement=defaultdict(Counter)
    for p in alive:
        ages[p.species].append(p.age);occupations[p.occupation]+=1;species_settlement[p.settlement][p.species]+=1

    paths=world.advancement.paths
    essence_users=[p for p in alive if p.id in paths]
    completed=[p for p in essence_users if len(paths[p.id].abilities)==20]
    rank_counts=Counter(RANK_NAMES.get(p.rank,str(p.rank)) for p in completed)
    rank_by_species=defaultdict(Counter)
    for p in completed:rank_by_species[p.species][RANK_NAMES.get(p.rank,str(p.rank))]+=1

    species_detail={}
    for name in sorted(set(PEOPLES)|set(founding_species)|set(species)):
        people=[p for p in alive if p.species==name]
        vals=ages.get(name,[])
        users=sum(p.id in paths for p in people)
        full=sum(p.id in paths and len(paths[p.id].abilities)==20 for p in people)
        species_detail[name]={
            'population':len(people),'share':round(len(people)/max(1,len(alive)),4),
            'age_median':_pct(vals,.5),'age_p90':_pct(vals,.9),'age_max':max(vals,default=0),
            'essence_users':users,'completed_paths':full,
            'completed_rank_counts':_counter(rank_by_species.get(name,{})),
        }

    # Individual upper-rank progress: a large Silver shelf is expected, so show
    # whether those people are still advancing internally.
    silvers=[p for p in completed if p.rank==3];golds=[p for p in completed if p.rank==4]
    silver_gold=[sum(a.rank>=4 for a in paths[p.id].abilities) for p in silvers]
    gold_diamond=[sum(a.rank>=5 for a in paths[p.id].abilities) for p in golds]

    aspirations=[a for pid,a in world.magic_resources.aspirations.items() if pid in alive_ids]
    current_cadets=[a for a in aspirations if a.cadet_class_year is not None and a.cadet_graduated_year is None]
    living_graduates=[a for a in aspirations if a.cadet_graduated_year is not None]
    resources=list(world.magic_resources.resources.values())
    available=[r for r in resources if r.consumed_year is None]
    resource_total=Counter(r.kind for r in resources);resource_available=Counter(r.kind for r in available)
    resource_owner=Counter((r.owner_kind or 'unowned') for r in available);resource_rarity=Counter(r.rarity for r in available)

    institutions=world.institutions.institutions
    institution_summary={}
    for inst in institutions.values():
        institution_summary[inst.kind]={
            'id':inst.id,'founded_year':inst.founded_year,'branches':len(inst.branches),
            'members_total':len(inst.members),'members_living':sum(pid in alive_ids for pid in inst.members),
        }
    notice_status=Counter(n.status for n in world.institutions.notices.values())
    application_status=Counter('pending' if a.passed is None else ('passed' if a.passed else 'failed') for a in world.institutions.applications.values())

    wallet_totals=Counter()
    for pid,wallet in world.currency.wallets.items():
        if pid in alive_ids:
            for denom,n in wallet.items():wallet_totals[denom]+=n
    treasury_totals=Counter()
    for treasury in world.currency.treasuries.values():
        for denom,n in treasury.items():treasury_totals[denom]+=n

    lots=world.materials.lots;items=world.materials.items
    active_lots=sum(len(ids) for ids in world.materials.active_lot_index.values())
    lot_ranks=Counter(l.material_rank for l in lots.values())
    item_ranks=Counter(i.item_rank for i in items.values())
    magical_items=sum(bool(i.magical) for i in items.values())

    threats=world.threat_ecology.threats
    active_threats=[t for t in threats.values() if t.status=='active']
    active_threat_rank=Counter(RANK_NAMES.get(t.rank,str(t.rank)) for t in active_threats)
    active_threat_kind=Counter(t.kind for t in active_threats)

    fields={}
    for sid in sorted(world.settlements):
        f=world.ambient_magic.fields.get(sid)
        if f is not None:
            fields[str(sid)]={'level':round(f.level,4),'peak':round(f.peak,4),'critical_years':f.critical_years,'quintessence':round(f.quintessence,3),'surges':f.surges}

    infra_by_kind=defaultdict(list)
    for a in world.infrastructure.assets.values():infra_by_kind[a.kind].append(a.condition)
    infrastructure={k:{'count':len(v),'condition_avg':round(sum(v)/len(v),4),'condition_min':round(min(v),4)} for k,v in sorted(infra_by_kind.items())}

    practices=Counter(p.domain for p in world.culture.practices.values())
    laws=Counter(l.domain for l in world.culture.laws.values())
    active_adoptions=sum(v>.008 for v in world.culture.adoption.values())
    communities=Counter(c.kind for c in world.communities.communities.values() if c.active)
    living_memberships=sum(pid in alive_ids and strength>=.01 for (pid,_),strength in world.communities.memberships.items())

    skill_domains=defaultdict(list)
    for (pid,domain),skill in world.skills.skills.items():
        if pid in alive_ids:skill_domains[domain].append(skill.level)
    skills={d:{'holders':len(v),'median':round(_pct(v,.5),4),'p90':round(_pct(v,.9),4)} for d,v in sorted(skill_domains.items())}

    living_partnerships=sum(a in alive_ids and b in alive_ids for a,b in world.social.partnerships)
    churches=list(world.divinity.churches.values())
    church_followers=sum(sum(pid in alive_ids for pid in c.followers) for c in churches)
    god_manifestations=sum(len(g.manifestations) for g in world.divinity.gods.values())
    astral_interventions=sum(len(g.interventions) for g in world.divinity.great_astral_beings.values())
    ontologies=Counter(s.ontology for s in world.metaphysics.souls.values() if s.person in alive_ids)
    available_resurrection=sum(t.consumed_year is None for t in world.metaphysics.resurrection_tokens.values())

    conflicts=list(world.warfare.conflicts.values())
    active_conflicts=sum(c.status=='war' for c in conflicts)
    trade_routes={
        f'{a}-{b}':{'strength':round(r.strength,4),'exchanges':r.exchanges,'last_used':r.last_used}
        for (a,b),r in sorted(world.trade_routes.items())
    }

    settlements={}
    for sid,s in sorted(world.settlements.items()):
        q=world.local[sid]
        settlements[str(sid)]={
            'population':settlement_pop.get(sid,0),
            'species':_counter(species_settlement.get(sid,{})),
            'food_stock':round(s.food_stock,2),'scarcity':round(q.scarcity,4),
            'prosperity':round(s.prosperity,4),'defense':round(s.defense,4),
            'roads':round(s.roads,4),'irrigation':round(s.irrigation,4),
            'rain':round(q.rain,4),'drought':round(q.drought,4),'flood':round(q.flood,4),
            'active_threats':sum(t.location==sid for t in active_threats),
        }

    interval=_interval_activity(world,start_event)
    expected={
        'birth':interval['event_kinds'].get('birth',0),
        'death':interval['event_kinds'].get('death',0),
        'ability_awakened':interval['event_kinds'].get('ability_awakened',0),
        'rank_advanced':interval['event_kinds'].get('rank_advanced',0),
        'society_cadet_graduated':interval['event_kinds'].get('society_cadet_graduated',0),
        'material_produced':interval['event_kinds'].get('material_produced',0),
        'item_crafted':interval['event_kinds'].get('item_crafted',0),
        'ranked_magic_manifested':interval['event_kinds'].get('ranked_magic_manifested',0),
        'ranked_threat_resolved':interval['event_kinds'].get('ranked_threat_resolved',0),
        'magic_resource_discovered':interval['event_kinds'].get('magic_resource_discovered',0),
    }
    warnings=[]
    if not alive:warnings.append('population extinct')
    extinct=sorted(set(founding_species)-set(species))
    if extinct:warnings.append('founding species extinct: '+','.join(extinct))
    for k,v in expected.items():
        if v==0:warnings.append('no interval activity: '+k)

    integrity=[]
    if sum(species.values())!=len(alive):integrity.append('species population sum mismatch')
    if sum(settlement_pop.values())!=len(alive):integrity.append('settlement population sum mismatch')
    bad_refs=sum(p.settlement not in world.settlements or p.household not in world.households for p in alive)
    if bad_refs:integrity.append(f'{bad_refs} living people have missing settlement/household references')
    rank_mismatch=sum(p.id in paths and p.rank!=world.advancement.rank(p.id) for p in alive)
    if rank_mismatch:integrity.append(f'{rank_mismatch} living magic users have stale body rank')
    negative_currency=sum(n<0 for wallet in world.currency.wallets.values() for n in wallet.values())+sum(n<0 for treasury in world.currency.treasuries.values() for n in treasury.values())
    if negative_currency:integrity.append(f'{negative_currency} negative currency balances')
    indexed_available=sum(len(ids) for ids in world.magic_resources.owner_index.values())
    owned_available=sum(r.consumed_year is None and r.owner_kind is not None and r.owner_id is not None for r in resources)
    if indexed_available!=owned_available:integrity.append('magic resource owner index mismatch')

    return {
        'record':'longevity_snapshot','seed':world.seed,'year':world.year,
        'interval':{
            'wall_seconds':round(interval_wall,3),'cpu_seconds':round(interval_cpu,3),
            **interval,
        },
        'health':{'integrity_ok':not integrity,'integrity_issues':integrity,'warnings':warnings,'extinct_founding_species':extinct},
        'demography':{
            'alive':len(alive),'people_ever':len(world.people),'species':species_detail,
            'settlement_population':_counter(settlement_pop),'occupations':_counter(occupations),
            'households_total':len(world.households),'households_living':sum(h.alive and any(pid in alive_ids for pid in h.members) for h in world.households.values()),
            'genealogical_birth_records':len(world.genealogy.parents),
        },
        'settlements':settlements,
        'magic':{
            'essence_users_living':len(essence_users),'essence_user_share':round(len(essence_users)/max(1,len(alive)),4),
            'completed_paths_living':len(completed),'completed_rank_counts':_counter(rank_counts),
            'incomplete_paths_living':len(essence_users)-len(completed),
            'rank_counts_by_species':{k:_counter(v) for k,v in sorted(rank_by_species.items())},
            'silver_progress':{
                'living':len(silvers),'with_any_gold_ability':sum(n>0 for n in silver_gold),
                'with_10plus_gold_abilities':sum(n>=10 for n in silver_gold),
                'with_15plus_gold_abilities':sum(n>=15 for n in silver_gold),
                'with_19plus_gold_abilities':sum(n>=19 for n in silver_gold),
                'gold_abilities_median':_pct(silver_gold,.5),'gold_abilities_p90':_pct(silver_gold,.9),
            },
            'gold_progress':{
                'living':len(golds),'with_any_diamond_ability':sum(n>0 for n in gold_diamond),
                'diamond_abilities_median':_pct(gold_diamond,.5),'diamond_abilities_p90':_pct(gold_diamond,.9),
            },
            'aspirants_living':len(aspirations),'completion_goal_living':sum(a.completion_goal for a in aspirations),
            'adventurer_aspirants_living':sum(a.adventurer_aspiration for a in aspirations),
            'cadets_current':len(current_cadets),'cadet_graduates_living':len(living_graduates),
            'resources_total':len(resources),'resources_by_kind':_counter(resource_total),
            'resources_available':len(available),'available_by_kind':_counter(resource_available),
            'available_by_owner_kind':_counter(resource_owner),'available_by_rarity':_counter(resource_rarity),
            'ambient_fields':fields,
        },
        'institutions':{
            'core':institution_summary,'branches':len(world.institutions.branches),
            'magic_records':len(world.institutions.magic_records),
            'notices_total':len(world.institutions.notices),'notice_status':_counter(notice_status),
            'applications_total':len(world.institutions.applications),'application_status':_counter(application_status),
            'communities_active_by_kind':_counter(communities),'living_community_memberships':living_memberships,
            'churches':len(churches),'living_church_followers':church_followers,
        },
        'economy':{
            'ordinary_wealth_living_total':round(sum(p.wealth for p in alive),2),
            'ordinary_wealth_living_median':round(_pct([p.wealth for p in alive],.5),3),
            'properties':len(world.economy.property),'trade_routes':trade_routes,
            'wallet_coins_living':_counter(wallet_totals),'treasury_coins':_counter(treasury_totals),
            'currency_minted':_counter(world.currency.minted),'currency_consumed':_counter(world.currency.consumed),
            'material_lots_total':len(lots),'material_lots_active':active_lots,'material_lot_ranks':_counter(lot_ranks),
            'crafted_items_total':len(items),'magical_items_total':magical_items,'crafted_item_ranks':_counter(item_ranks),
        },
        'ecology_and_conflict':{
            'threats_total':len(threats),'threats_active':len(active_threats),
            'active_threats_by_rank':_counter(active_threat_rank),'active_threats_by_kind':_counter(active_threat_kind),
            'threat_resolutions_total':len(world.threat_ecology.resolutions),
            'wars_total':len(conflicts),'wars_active':active_conflicts,
            'battles_total':sum(c.battles for c in conflicts),
            'war_losses_total':sum(c.attacker_losses+c.defender_losses for c in conflicts),
            'infrastructure':infrastructure,
        },
        'society_and_knowledge':{
            'relationships_total':len(world.social.edges),'partnerships_total':len(world.social.partnerships),
            'partnerships_living':living_partnerships,
            'skills':skills,'knowledge_claims':len(world.knowledge.claims),'belief_records':len(world.knowledge.beliefs),
            'cultural_practices_by_domain':_counter(practices),'culture_institutions':len(world.culture.institutions),
            'laws_by_domain':_counter(laws),'active_cultural_adoptions':active_adoptions,
            'transmission_records':len(world.transmission.records),
        },
        'metaphysics_and_divinity':{
            'living_ontologies':_counter(ontologies),'souls_total':len(world.metaphysics.souls),
            'resurrection_tokens_total':len(world.metaphysics.resurrection_tokens),'resurrection_tokens_available':available_resurrection,
            'churches':len(churches),'god_manifestations':god_manifestations,'great_astral_interventions':astral_interventions,
        },
        'state_size':{
            'events_total':len(world.events),'relationships_total':len(world.social.edges),
            'people_total':len(world.people),'households_total':len(world.households),
            'magic_resources_total':len(resources),'materials_total':len(lots),'items_total':len(items),
            'applications_total':len(world.institutions.applications),'notices_total':len(world.institutions.notices),
            'agency_recent_actions':len(world.agency.actions),
        },
    }


def main(seed=917263,years=10000,checkpoints=CHECKPOINTS):
    checkpoints=tuple(sorted(set(int(x) for x in checkpoints if 0<int(x)<=years)))
    if not checkpoints or checkpoints[-1]!=years:checkpoints=(*checkpoints,years)
    world=generate_world(seed);sim=Simulation(world)
    founding_species=sorted({p.species for p in world.current_people()})
    print(json.dumps({'record':'longevity_start','seed':seed,'years':years,'checkpoints':checkpoints,'founding_species':founding_species},sort_keys=True),flush=True)
    last_year=0;event_start=0
    for mark in checkpoints:
        wall=perf_counter();cpu=process_time();sim.run(mark-last_year)
        wall_elapsed=perf_counter()-wall;cpu_elapsed=process_time()-cpu
        if world.year!=mark:raise RuntimeError(f'expected year {mark}, got {world.year}')
        report=snapshot(world,event_start,founding_species,wall_elapsed,cpu_elapsed)
        report['interval']['years']=mark-last_year
        report['interval']['seconds_per_year']=round(cpu_elapsed/max(1,mark-last_year),6)
        print(json.dumps(report,sort_keys=True),flush=True)
        event_start=len(world.events);last_year=mark
    print(json.dumps({'record':'longevity_complete','seed':seed,'year':world.year,'snapshots':list(checkpoints),'events_total':len(world.events)},sort_keys=True),flush=True)
    return world


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Sparse, broad deep-time health observation without archive export or canonical digest.')
    parser.add_argument('--seed',type=int,default=917263)
    parser.add_argument('--years',type=int,default=10000)
    parser.add_argument('--checkpoints',type=int,nargs='*',default=list(CHECKPOINTS))
    args=parser.parse_args()
    main(args.seed,args.years,args.checkpoints)
