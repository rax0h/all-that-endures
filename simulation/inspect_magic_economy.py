"""Post-run rank-relative opportunity, transaction and mastery report."""
import argparse,json
from collections import Counter,defaultdict
from ate_sim.history_archive import HistoryArchive
from ate_sim.advancement import RANKS
from ate_sim.currency import COIN_VALUE


def inspect(archive):
    counts=defaultdict(Counter);examples=defaultdict(list)
    people={int(r[0]):json.loads(r[1]) for r in archive.db.execute("SELECT id,payload FROM records WHERE kind='person'")}
    wallets={int(r[0]):json.loads(r[1]) for r in archive.db.execute("SELECT id,payload FROM records WHERE kind='wallet'")}
    high={pid:p for pid,p in people.items() if p['alive'] and p['rank']>=4}
    for row in archive.db.execute('SELECT payload FROM events ORDER BY year,id'):
        e=json.loads(row[0]);d=e['data'];k=e['kind']
        if k=='society_treasury_observed':
            for denom,n in d.get('opening_balance',{}).items():counts['opening_supply'][denom]+=n
        actors=[a['id'] for a in e['actors'] if a['kind']=='person'];pid=actors[0] if actors else None
        if k=='ranked_magic_manifested':
            counts['manifestations_by_rank'][str(d['rank'])]+=1
            counts['ecological_ceiling_at_manifestation'][d['ecological_ceiling']]+=1
        if k=='ranked_threat_resolved':
            counts['resolutions_by_threat_rank'][str(d['threat_rank'])]+=1
            counts['resolutions_by_kind_and_rank'][f"{d.get('manifestation_kind','unknown')}: {d['threat_rank']}"]+=1
            counts['participation_body_and_threat'][f"{d['responder_rank']} -> {d['threat_rank']}"]+=1
            if pid in high:counts['living_high_rankers_lifetime_threats'][f"person {pid}: threat {d['threat_rank']}"]+=1
            if d['threat_rank']>=4:examples['high_threat_resolutions'].append(e)
        if k=='adventure_notice_resolved':
            counts['paid_contract_task_and_recipient_rank'][f"{d['reward_rank']} -> {d['responder_rank']}"]+=1
            for denom,n in d['coin_reward'].items():counts['contract_coins'][denom]+=n
        if k=='monster_remains_harvested':counts['physical_harvests_by_rank'][str(d['material_rank'])]+=d['quantity']
        if k=='magical_service_completed':counts['services_by_task_rank'][str(d['task_rank'])]+=1
        if k=='ability_applied':
            counts['applications_by_ability_rank'][d['ability_rank']]+=1
            if d['generalization']:
                counts['held_out_transfers_by_ability_rank'][d['ability_rank']]+=1
                if len(examples['transfer_proofs'])<12:examples['transfer_proofs'].append(e)
        if k=='essence_revelation_integrated' and d['ability_rank']=='gold':
            if len(examples['diamond_ability_evidence'])<6:examples['diamond_ability_evidence'].append(e)
        if any(COIN_VALUE.get(denom,0)>=COIN_VALUE['gold'] and n>0 for denom,n in d.get('coin_transfer',{}).items()):
            if len(examples['high_rank_transactions'])<12:examples['high_rank_transactions'].append(e)
            if d.get('coin_transfer',{}).get('diamond',0)>0 and len(examples['diamond_transactions'])<6:examples['diamond_transactions'].append(e)
        for field,category in [('coin_created','created'),('coin_consumed','consumed'),('coin_deposit','treasury_deposits')]:
            for denom,n in d.get(field,{}).items():counts[category][denom]+=n
    balances=defaultdict(Counter);all_wallets=Counter()
    for pid,wallet in wallets.items():
        all_wallets.update(wallet)
        if people[pid]['alive']:balances[RANKS[people[pid]['rank']]].update(wallet)
    treasuries=Counter()
    for row in archive.db.execute("SELECT payload FROM records WHERE kind='treasury'"):treasuries.update(json.loads(row[0]))
    conservation={d:counts['opening_supply'][d]+counts['created'][d]-counts['consumed'][d]-all_wallets[d]-treasuries[d] for d in COIN_VALUE}
    threats=[json.loads(row[0]) for row in archive.db.execute("SELECT payload FROM records WHERE kind='threat'")]
    for t in threats:counts['final_threat_status'][f"rank {t['rank']}: {t['status']}"]+=1
    notices=[json.loads(row[0]) for row in archive.db.execute("SELECT payload FROM records WHERE kind='notice'")]
    for n in notices:counts['contracts_by_task_rank_and_status'][f"rank {n['required_rank']}: {n['status']}"]+=1
    blockers=Counter()
    for rid,raw in archive.db.execute("SELECT id,payload FROM records WHERE kind='path'"):
        person=people[int(rid)];path=json.loads(raw)
        if not person['alive'] or person['rank']<3 or len(path['abilities'])!=20:continue
        for ability in path['abilities']:
            if ability['rank']>person['rank']:continue
            u=ability['understanding']
            reason='no successful modeled application' if not u['applications'] else 'no harder held-out transfer' if not u['transfers'] else 'integration or within-rank practice'
            blockers[reason]+=1
    return {'mastery_blockers':dict(blockers),'world_digest':archive.metadata()['world_digest'],'counts':dict(counts),'living_wallets_by_body_rank':dict(balances),
            'treasuries':dict(treasuries),'currency_conservation_residual':conservation,
            'ambient_fields':[json.loads(r[0]) for r in archive.db.execute("SELECT payload FROM records WHERE kind='ambient_field'")],
            'examples':dict(examples)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive');args=parser.parse_args()
    with HistoryArchive(args.archive) as archive:report=inspect(archive)
    print(json.dumps(report,sort_keys=True))
    raise SystemExit(1 if any(report['currency_conservation_residual'].values()) else 0)
