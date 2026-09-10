import argparse
from collections import Counter
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation

SEEDS=(843000,843001,843002)
YEARS=300
LONG_SEED=843000
LONG_YEARS=1000

def signature(world,sid):
    vals=[(pid,v) for (place,pid),v in world.culture.adoption.items() if place==sid and v>=.20]
    return tuple(pid for pid,_ in sorted(vals,key=lambda x:(-x[1],x[0]))[:6])

def run_seed(seed,years=YEARS):
    w=generate_world(seed)
    initial_species={p.species for p in w.people.values()}
    Simulation(w).run(years)
    alive=[p for p in w.people.values() if p.alive]
    surviving_species={p.species for p in alive}
    occupied={p.settlement for p in alive}
    event_counts=Counter(e.kind for e in w.events)
    signatures={signature(w,sid) for sid in w.settlements if signature(w,sid)}
    result={
        'seed':seed,'years':years,'alive':len(alive),'initial_species':len(initial_species),
        'surviving_species':len(surviving_species),'occupied_settlements':len(occupied),
        'practices':len(w.culture.practices),'cultural_signatures':len(signatures),
        'trade':event_counts['trade_exchange'],'migration':event_counts['household_migrated'],
        'births':event_counts['birth'],'deaths':event_counts['death']
    }
    print(result)
    assert len(alive)>=50, result
    assert len(occupied)>=3, result
    assert len(surviving_species)>=max(2,(len(initial_species)+1)//2), result
    assert len(w.culture.practices)<160, result
    assert len(signatures)>=2, result
    assert event_counts['trade_exchange']>=10, result
    return result

def main(include_long=False):
    results=[run_seed(seed) for seed in SEEDS]
    assert sum(r['migration'] for r in results)>0, results
    if include_long:
        long=run_seed(LONG_SEED,LONG_YEARS)
        assert long['surviving_species']>=max(3,(long['initial_species']+1)//2), long
        assert long['occupied_settlements']==5, long
        results.append(long)
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Run multi-seed calibration without duplicating the dedicated millennium validation.')
    parser.add_argument('--include-long',action='store_true',help='also run the legacy 1000-year calibration check')
    args=parser.parse_args()
    main(include_long=args.include_long)
