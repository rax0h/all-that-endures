"""Matched bounded populated diagnostic; never mature/endurance acceptance."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from simulation import continuation_receipts as r
from simulation.stage_0_5_mature_step_save import compare_receipts

RULES = 'proof-runtime-populated-diagnostic/1'
BASELINE_TREE = '48e3e21b3b8d4ccb57eab74e11412a1ec4e74b6a'


def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def main(workspace, output):
    workspace, output = Path(workspace).resolve(), Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    baseline, candidate = workspace/'baseline', workspace/'candidate'
    if git(baseline,'rev-parse','HEAD:simulation/ate_sim') != BASELINE_TREE:
        raise ValueError('baseline differs from the previously measured candidate')
    if git(candidate,'status','--porcelain','--untracked-files=no'):
        raise ValueError('candidate tracked source is dirty')
    fixture=output/'fixture';fixture.mkdir()
    world=generate_world(843000,mature=True)
    source_year=world.year
    cold,legacy,source=[fixture/name for name in ('cold.sqlite','legacy.sqlite','source.sqlite')]
    initial_digest=world.digest()
    write_cold_snapshot(world,cold,rules_id=RULES)
    # Eager rule control supplies an independently computed successor digest.
    Simulation(world).run(1)
    successor_digest=world.digest()
    convert_cold_to_lazy(cold,legacy,rules_id=RULES,native_graph_buckets=True)
    upgrade_lazy_snapshot(legacy,source,rules_id=RULES)
    with LazyRecordStore.open(source,codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA,expected_rules_id=RULES) as store:
        generation,identity=store.generation,store.store_identity
    authority=dict(schema='ate-performance-source/1',database=dict(sha256=r.file_hash(source),bytes=source.stat().st_size),
        rules_id=RULES,pin=dict(token=None,store_identity=identity,captured_head=generation),
        world=dict(seed=843000,year=source_year),
        provenance=dict(kind='generated-populated-diagnostic',initial_digest=initial_digest,
                        successor_digest=successor_digest,config=dict(seed=843000,mature=True)))
    authority_path=output/'source-authority.json';r.publish_receipt(authority_path,authority)
    harness=candidate/'simulation/stage_0_5_mature_step_save.py'
    for lane in ('baseline','candidate'):
        runtime=workspace/lane
        env=dict(os.environ,PYTHONPATH='.:simulation',PYTHONUNBUFFERED='1')
        command=[sys.executable,'-c',
            'import runpy,sys;runpy.run_path(sys.argv.pop(1),run_name="__main__")',str(harness),
            'run',str(source),str(output/lane),'--seconds','600',
            '--expected-sha256',authority['database']['sha256'],'--authority',str(authority_path),'--attributed']
        with (output/(lane+'-measurement.log')).open('w') as log:
            subprocess.run(command,cwd=runtime,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=660)
        receipt=r.load_receipt(output/lane/'result.json')
        actual_root=Path(receipt['runtime']['root']).resolve()
        if actual_root != runtime.resolve():raise ValueError('measurement imported the wrong runtime')
        saved=receipt['saved_database']
        verify=[sys.executable,'-c',
            'import runpy,sys;runpy.run_path(sys.argv.pop(1),run_name="__main__")',str(harness),
            'verify',str(output/lane/'operational.sqlite'),str(output/lane/'fresh-restore.json'),
            '--expected-sha256',saved['sha256'],'--expected-bytes',str(saved['bytes']),
            '--rules-id',RULES,'--expected-year',str(source_year+1),'--expected-seed','843000',
            '--expected-generation',str(generation+1),'--expected-store-identity',identity,
            '--expected-digest',successor_digest]
        with (output/(lane+'-restore.log')).open('w') as log:
            subprocess.run(verify,cwd=runtime,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    r.publish_receipt(output/'comparison.json',compare_receipts(
        r.load_receipt(output/'baseline/result.json'),r.load_receipt(output/'candidate/result.json')))
    if r.file_hash(source) != authority['database']['sha256']:raise ValueError('fixture source changed')
    print(json.dumps(dict(status='complete',comparison=str(output/'comparison.json'),
                         eager_successor_digest=successor_digest)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    main(args.workspace,args.output)
