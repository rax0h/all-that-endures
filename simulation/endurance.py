from __future__ import annotations
import argparse,json,os
from ate_sim import Simulation,generate_world
from ate_sim.checkpoint import load,save
from ate_sim.diagnostics import world_snapshot
from ate_sim.narrative_sampler import sample_history

def main():
 p=argparse.ArgumentParser(description='Continue one authoritative All That Endures world without reseeding history.')
 p.add_argument('--seed',type=int,default=843000);p.add_argument('--years',type=int,default=1000);p.add_argument('--checkpoint');p.add_argument('--out',required=True);p.add_argument('--report')
 a=p.parse_args();w=load(a.checkpoint) if a.checkpoint and os.path.exists(a.checkpoint) else generate_world(a.seed);start=w.year;Simulation(w).run(a.years);sha=save(w,a.out)
 report={'start_year':start,'end_year':w.year,'seed':w.seed,'checkpoint_sha256':sha,'snapshot':world_snapshot(w),'narrative_samples':sample_history(w,3)}
 text=json.dumps(report,sort_keys=True,indent=2)
 if a.report:open(a.report,'w',encoding='utf-8').write(text+'\n')
 print(text)
if __name__=='__main__':main()
