"""Read-only chronological validation of simulated magical history.

This verifies ATE's documented invariants, not an independent certification of
book canon. Final snapshots never substitute for missing historical milestones.
"""
import argparse
from collections import Counter,defaultdict
import json
from ate_sim.history_archive import HistoryArchive
from ate_sim.advancement import RANKS
from ate_sim.currency import DENOMINATIONS


def validate(archive):
    abilities=defaultdict(dict)
    essences=defaultdict(set)
    bodies=defaultdict(int)
    violations=[]
    examples=defaultdict(list)
    wallets=defaultdict(Counter)
    treasuries=defaultdict(Counter)
    for row in archive.db.execute('SELECT payload FROM events ORDER BY year,id'):
        e=json.loads(row[0]);data=e['data'];kind=e['kind']
        actors=[a['id'] for a in e['actors'] if a['kind']=='person']
        if not actors:continue
        pid=actors[0]
        for denomination,count in data.get('coin_created',{}).items():wallets[pid][denomination]+=count
        for denomination,count in data.get('coin_deposit',{}).items():
            wallets[pid][denomination]-=count;treasuries[data['institution']][denomination]+=count
        for denomination,count in data.get('coin_consumed',{}).items():wallets[pid][denomination]-=count
        for denomination,count in data.get('coin_reward',{}).items():
            wallets[pid][denomination]+=count
            if 'treasury' in data:
                treasuries[data['treasury']][denomination]-=count
                if treasuries[data['treasury']][denomination]<0:violations.append({'event':e['id'],'issue':'unfunded Society reward'})
        if any(v<0 for v in wallets[pid].values()):violations.append({'person':pid,'event':e['id'],'issue':'unfunded deposit or consumption'})
        coins=data.get('coin_transfer',{})
        if coins and len(actors)>=2:
            payer,payee=(actors[0],actors[1]) if kind=='material_purchased' else (actors[1],actors[0])
            for denomination,count in coins.items():
                wallets[payer][denomination]-=count;wallets[payee][denomination]+=count
                if wallets[payer][denomination]<0:violations.append({'person':payer,'event':e['id'],'issue':'unfunded coin transfer'})
        if kind in ('essence_absorbed','confluence_absorbed'):
            essences[pid].add(data.get('essence',data.get('confluence')))
        elif kind=='ability_awakened':
            abilities[pid][data['ability']]=(data['essence'],1)
        elif kind=='ability_applied':
            task=archive.event(data['task_event'])
            keys=() if task is None else task['data'].get('used_abilities',(task['data'].get('ability'),))
            if task is None or data['ability'] not in keys or task['id']>=e['id'] or data['outcome']<=0:
                violations.append({'person':pid,'event':e['id'],'issue':'unsubstantiated ability application'})
            if data['generalization']:
                premises=[archive.event(c) for c in e['causes'][1:]]
                if len(premises)!=2 or not all(x and x['kind']=='ability_applied' and x['data']['ability']==data['ability'] and x['data']['difficulty']<data['difficulty'] and x['data']['constraint']!=data['constraint'] and x['data']['metric']==data['metric'] for x in premises):
                    violations.append({'person':pid,'event':e['id'],'issue':'invalid held-out generalization'})
                elif data['outcome']<min(x['data']['outcome'] for x in premises):
                    violations.append({'person':pid,'event':e['id'],'issue':'transfer lost prior performance'})
        elif kind=='essence_revelation_integrated':
            rank=RANKS.index(data['ability_rank']);proofs=data.get('transfer_proofs',[])
            valid=len(proofs)>=(1 if rank==3 else 2) and data['integration']>=rank
            for proof in proofs:
                source=archive.event(proof['event'])
                valid=valid and source is not None and source['id']<e['id'] and source['kind']=='ability_applied' and source['data']['ability']==data['ability'] and source['data']['generalization'] and source['data']['difficulty']>=rank and source['id'] in e['causes']
            if not valid:violations.append({'person':pid,'event':e['id'],'issue':'understanding evidence'})
        elif kind=='ability_rank_advanced':
            key=data['ability'];before=RANKS.index(data['ability_rank_before']);after=RANKS.index(data['ability_rank_after'])
            previous=abilities[pid].get(key)
            if previous is None or previous[1]!=before or after!=before+1:
                violations.append({'person':pid,'event':e['id'],'issue':'ability chronology'})
            if after>max(1,bodies[pid])+1:
                violations.append({'person':pid,'event':e['id'],'issue':'ability beyond body ceiling'})
            if before>=3:
                evidence=[archive.event(c) for c in e['causes']]
                if not any(x and x['kind']=='essence_revelation_integrated' and x['data']['ability']==key for x in evidence):
                    violations.append({'person':pid,'event':e['id'],'issue':'missing understanding milestone'})
            abilities[pid][key]=(data['essence'],after)
        elif kind=='rank_advanced':
            target=data['to_rank'];current=abilities[pid]
            counts=Counter(v[0] for v in current.values())
            valid=(data['from_rank']==bodies[pid] and target==bodies[pid]+1 and len(essences[pid])==4)
            if target>=2:
                valid=valid and len(current)==20 and len(counts)==4 and set(counts.values())=={5} and all(v[1]>=target for v in current.values())
            if target==5:valid=valid and data.get('core_taint')==0
            if not valid:violations.append({'person':pid,'event':e['id'],'issue':'body prerequisites'})
            bodies[pid]=target
            p=archive.record('person',pid)
            examples[pid].append({'year':e['year'],'age':None if p is None else e['year']-p['born'],
                'event':e['id'],'essences':sorted(essences[pid]),'abilities':dict(Counter(RANKS[v[1]] for v in current.values())),
                'body_rank':RANKS[target],
                'economic_tier':next((d for d in reversed(DENOMINATIONS) if wallets[pid].get(d,0)>0),'no recorded coins'),
                'coin_balance':dict(wallets[pid])})
    living=Counter();high=[];lower=defaultdict(list);unranked_humans=[]
    for row in archive.db.execute("SELECT payload FROM records WHERE kind='person' ORDER BY id"):
        p=json.loads(row[0])
        if p['rank']!=bodies[p['id']]:violations.append({'person':p['id'],'issue':'snapshot body disagrees with chronology'})
        actual=archive.record('wallet',p['id']) or {}
        if {d:n for d,n in actual.items() if n}!={d:n for d,n in wallets[p['id']].items() if n}:
            violations.append({'person':p['id'],'issue':'wallet disagrees with recorded transfers'})
        if p['species']=='human' and archive.record('path',p['id']) is None:
            unranked_humans.append({'person':p['id'],'age':p['age'],'alive':p['alive'],'born':p['born']})
        if not p['alive']:continue
        living[RANKS[p['rank']]]+=1
        if p['rank']<4 and len(lower[RANKS[p['rank']]])<3:
            lower[RANKS[p['rank']]].append({'person':p['id'],'species':p['species'],'age':p['age'],'progression':examples[p['id']]})
        if p['rank']>=4:
            high.append({'person':p['id'],'species':p['species'],'age':p['age'],'body_rank':RANKS[p['rank']],
                'wealth':p['wealth'],'wallet':archive.record('wallet',p['id']),
                'progression':examples[p['id']]})
    for row in archive.db.execute("SELECT id,payload FROM records WHERE kind='treasury'"):
        actual=json.loads(row[1]);expected=treasuries[int(row[0])]
        if {d:n for d,n in actual.items() if n}!={d:n for d,n in expected.items() if n}:violations.append({'institution':row[0],'issue':'treasury disagrees with recorded transfers'})
    return {'world_digest':archive.metadata()['world_digest'],'valid':not violations,
            'violations':violations,'living_ranks':dict(sorted(living.items())),
            'living_gold_and_diamond':high,'lower_rank_examples':dict(lower),
            'oldest_never_magical_humans':sorted(unranked_humans,key=lambda p:(-p['age'],p['person']))[:6]}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    args=parser.parse_args()
    with HistoryArchive(args.archive) as archive:report=validate(archive)
    print(json.dumps(report,sort_keys=True))
    raise SystemExit(0 if report['valid'] else 1)
