"""Bounded diagnostic profile; never substitute its timings for mature acceptance."""
from dataclasses import asdict
import cProfile
import io
import json
from pathlib import Path
import pstats
import shutil
import subprocess
import sys
from simulation import stage_0_6_genesis_checkpoint as c
from simulation.stage_0_6_genesis_stages import Recorder,restore_in_fresh_process
from ate_sim.engine import Simulation
from ate_sim.persistence_proof_world_session import open_proof_world_session

root=Path.cwd();output=Path(__file__).parent
info=json.loads((output/'input.json').read_text())
assert subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()==info['runtime_tree']
source=Path(sys.argv[1]);c.verify_database(source,info['database'])
working=source.parent/'profile-working.sqlite';shutil.copyfile(source,working)
rec=Recorder(output/'phases',dict(open=60,first_step=180,save=120,warm_step=180,fresh_verify=120))
session=None;profiles={}

def phase(name,operation):
    profile=cProfile.Profile();before=asdict(session.store.diagnostics()) if session else {}
    profile.enable()
    try:return rec.measure(name,operation)
    finally:
        profile.disable();stats=pstats.Stats(profile)
        stream=io.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(120)
        (output/(name+'.txt')).write_text(stream.getvalue())
        functions=[]
        for (file,line,function),(primitive,calls,own,cumulative,callers) in stats.stats.items():
            functions.append(dict(file=file,line=line,function=function,primitive_calls=primitive,calls=calls,
                own_seconds=own,cumulative_seconds=cumulative,callers=[dict(function=list(k),values=list(v) if isinstance(v,tuple) else v) for k,v in callers.items()]))
        (output/(name+'-calls.json')).write_text(json.dumps(sorted(functions,key=lambda x:-x['cumulative_seconds']),indent=2)+'\n')
        after=asdict(session.store.diagnostics()) if session else {}
        profiles[name]=dict(before=before,after=after)

try:
    session=phase('open',lambda:open_proof_world_session(working,rules_id=info['rules_id'],expected_commitment=bytes.fromhex(info['proof_commitment'])))
    rec.store=session.store
    assert session.world.year==1 and session.proof_manifest[0].generation==0
    phase('first_step',lambda:Simulation(session.world).run(1))
    phase('save',session.save)
    commitment=session.proof_manifest[1].hex()
    assert session.world.year==2 and session.proof_manifest[0].generation==1
    phase('warm_step',lambda:Simulation(session.world).run(1))
    session.close();session=None;rec.store=None
    receipt=dict(context=dict(rules_id=info['rules_id'],source=info['database'],expected_saved_digest=info['expected_saved_digest']),proof_commitment=commitment)
    restored=rec.measure('fresh_verify',lambda:restore_in_fresh_process(working,receipt,120))
    report=dict(kind='diagnostic-instrumented-small-world-only',runtime_tree=info['runtime_tree'],python=sys.version,
        phases=rec.phases,logical_io=profiles,restored=restored,
        limitation='cProfile overhead; different local software from hosted; no mature latency or cross-source checkpoint compatibility claim')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v['wall_seconds'] for k,v in rec.phases.items()}),flush=True)
finally:
    if session is not None:session.close()
    c.verify_database(source,info['database'])
