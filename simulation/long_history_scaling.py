"""Lightweight continuation measurements; never export archives at milestones.

All inspections run outside the measured simulation interval. Checkpoints are
trusted local pickle files, as with the existing endurance command.
"""
import argparse
from collections import Counter
import gc
import json
from time import perf_counter

from ate_sim import Simulation, generate_world
from ate_sim.checkpoint import load, save
from ate_sim.advancement import RANKS
from ate_sim.currency import DENOMINATIONS
from scaling_telemetry import ScalingTelemetry


def current_audit(w):
    """State invariants, not a replacement for the chronological archive audit."""
    errors=[]
    for pid,p in w.people.items():
        path=w.advancement.path(pid)
        if p.rank!=w.advancement.rank(pid):errors.append(('body_rank',pid))
        if path is None:continue
        groups=Counter(a.essence for a in path.abilities)
        if len(path.base_essences)>3 or len(set(path.essences))!=len(path.essences) or any(e not in path.essences or n>5 for e,n in groups.items()):errors.append(('configuration',pid))
        if p.rank and (len(path.essences)!=4 or len(path.abilities)!=20 or set(groups.values())!={5}):errors.append(('incomplete_ranked_path',pid))
        for a in path.abilities:
            if a.rank<p.rank or a.rank>max(1,p.rank)+1 or (a.rank>max(1,p.rank) and (a.level!=0 or a.progress!=0)):errors.append(('ability_ceiling',pid))
    balances=Counter()
    for account in (*w.currency.wallets.values(),*w.currency.treasuries.values()):
        if any(d not in DENOMINATIONS or type(n) is not int or n<0 for d,n in account.items()):errors.append(('invalid_coins',account))
        balances.update(account)
    imbalance={d:balances[d]+w.currency.consumed.get(d,0)-w.currency.minted.get(d,0) for d in DENOMINATIONS}
    if any(imbalance.values()):errors.append(('currency',imbalance))
    return {'state_violations':errors,'currency_imbalance':imbalance}


def measure(w, end, interval=250, checkpoint_at=None, checkpoint_path=None):
    sim=Simulation(w);total=0.
    while w.year<end:
        first=w.year+1;last=min(end,((w.year//interval)+1)*interval)
        with ScalingTelemetry(w) as telemetry:
            start=perf_counter();sim.run(last-w.year);elapsed=perf_counter()-start
            total+=elapsed
            # Report all buckets, including 1-100 when a block straddles it.
            subsystem=Counter()
            for costs in telemetry.seconds.values():subsystem.update(costs)
            gc_seconds=sum(telemetry.gc_seconds.values())
        start=perf_counter()
        alive=w.current_people();paths=[w.advancement.path(p.id) for p in alive if w.advancement.path(p.id)]
        kinds=Counter();irons=Counter();causal_errors=0
        for e in w.events_between(first,last):
            kinds[e.kind]+=1
            causal_errors+=sum(c>=e.id or c not in w.event_ids for c in e.causes)
            if e.kind=='rank_advanced' and e.data['from_rank']==0:irons[e.year]+=1
        report={'first_year':first,'year':w.year,'simulation_seconds':elapsed,
                'seconds_per_year':elapsed/(last-first+1),'gc_seconds':gc_seconds,
                'subsystem_seconds':dict(subsystem),'living':len(alive),
                'rank_population':dict(Counter(RANKS[p.rank] for p in alive)),
                'essence_users':len(paths),'completed_paths':sum(len(p.abilities)==20 for p in paths),
                'resources':len(w.magic_resources.resources),
                'unused_resources':sum(r.consumed_year is None for r in w.magic_resources.resources.values()),
                'material_lots':len(w.materials.lots),'active_material_lots':sum(map(len,w.materials.active_lot_index.values())),
                'events':len(w.events),'event_storage':w.events.storage_stats(),
                'new_irons':sum(irons.values()),'years_without_irons':last-first+1-len(irons),
                'society_graduations':kinds['society_trainee_graduated'],
                'notices':dict(Counter(n.status for n in w.institutions.notices.values())),
                'causal_violations_in_block':causal_errors,**current_audit(w)}
        report['inspection_seconds']=perf_counter()-start
        print(json.dumps(report,sort_keys=True),flush=True)
        if causal_errors or report['state_violations']:raise ValueError('long-history audit failed')
        if w.year==checkpoint_at:
            start=perf_counter();save(w,checkpoint_path)
            print(json.dumps({'checkpoint_year':w.year,'checkpoint_seconds':perf_counter()-start}),flush=True)
        # Inspector temporarily materializes cold records; collect them outside
        # subsequent timing so diagnostic allocation is not charged to simulation.
        gc.collect()
    return total


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=843010)
    parser.add_argument('--until',type=int,default=3000)
    parser.add_argument('--checkpoint')
    parser.add_argument('--save-at',type=int)
    parser.add_argument('--save-path')
    args=parser.parse_args()
    if args.save_at is not None and (not args.save_path or args.save_at%250):parser.error('--save-at requires --save-path and a 250-year boundary')
    w=load(args.checkpoint) if args.checkpoint else generate_world(args.seed,mature=True)
    total=measure(w,args.until,checkpoint_at=args.save_at,checkpoint_path=args.save_path)
    start=perf_counter();digest=w.digest()
    print(json.dumps({'final_year':w.year,'simulation_seconds':total,'digest':digest,'digest_seconds':perf_counter()-start}),flush=True)


if __name__=='__main__':main()
