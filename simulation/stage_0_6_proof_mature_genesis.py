"""Authenticated mature proof genesis followed by real continuation measurements."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from unittest.mock import patch

from simulation import continuation_receipts as r
from simulation.stage_0_6_mature_benchmark import check_source, Recorder, machine, resources
from simulation.stage_0_6_retained_launch import prepare_retained
from simulation.stage_0_6_retained_producer import PIN

ORIGINAL = Path('simulation/stage_0_5_save1002_preflight.json')
TARGETS = dict(open=10, save=2, warm_step=1)
EXPECTED_DIGEST = '2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7'


def check_request(config, original, authority):
    if config.get('schema') != 'ate-stage06-proof-genesis-request/1' or config.get('operation') != 'convert-then-one-year':
        raise ValueError('invalid mature genesis request')
    expected_world = dict(seed=authority.source_config['seed'], year=original['expected_previous_year'])
    expected_pin = dict(store_identity=authority.store_identity, captured_head=original['expected_previous_generation'])
    if (not r.same(config.get('database'), original['candidate_database'])
            or not r.same(config.get('world'), expected_world) or not r.same(config.get('pin'), expected_pin)
            or config.get('expected_saved_digest') != EXPECTED_DIGEST):
        raise ValueError('mature genesis request differs from original accepted authority')
    wanted = {'construction', 'open', 'first_step', 'save', 'warm_step', 'fresh_restore'}
    budgets = config.get('budgets')
    if (not isinstance(budgets, dict) or set(budgets) != wanted
            or any(type(n) is not int or not 1 <= n <= 14400 for n in budgets.values())
            or sum(budgets.values()) > 19000):
        raise ValueError('invalid mature genesis phase budgets')


FRESH = '''
import json,sys
from ate_sim import persistence_proof_world as proof
from ate_sim.persistence_proof_world_session import open_proof_world_session
def reject(*args,**kwargs):raise AssertionError('fresh proof opening attempted full World audit')
proof._audit_world=reject
with open_proof_world_session(sys.argv[1],rules_id=sys.argv[2],expected_commitment=bytes.fromhex(sys.argv[3])) as s:
    if s.world.year!=1002 or s.world.seed!=843000 or s.proof_manifest[0].generation!=1:
        raise ValueError('fresh saved World context differs')
    result=dict(year=s.world.year,seed=s.world.seed,generation=s.proof_manifest[0].generation,digest=s.world.digest(),world_audits=0)
print(json.dumps(result))
'''


def fresh_restore(path, rules, commitment, expected, seconds):
    completed = subprocess.run([sys.executable,'-c',FRESH,str(path),rules,commitment.hex()],
        check=True,capture_output=True,text=True,timeout=seconds)
    result = json.loads(completed.stdout)
    if not r.same(result,dict(year=1002,seed=843000,generation=1,digest=expected,world_audits=0)):
        raise ValueError('fresh proof continuation differs from accepted year1002')
    return result


def measure(source, destination, authority, config, output):
    from ate_sim import persistence_proof_world_copy as genesis
    from ate_sim import persistence_catalog_copy as catalog
    from ate_sim import persistence_proof_world as world_proof
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.persistence_proof_world_session import open_proof_world_session
    from ate_sim.engine import Simulation
    output = Path(output)
    rec = Recorder(output, config['budgets'])
    result = dict(schema='ate-stage06-mature-proof-genesis/1',status='running',acceptance='pending',
        machine=machine(),source=authority,targets_seconds=TARGETS,phases=rec.phases,
        scope='explicit proof opener; default reader and audited reader unchanged')
    session = None
    active = 'starting'
    sequence = 0
    stopped = threading.Event()
    def progress(phase, *_):
        nonlocal active, sequence
        active = str(phase)
        row = dict(phase=active,sequence=sequence,unix_time=time.time(),resources=resources())
        r.publish_receipt(output/('construction-progress-%04d.json'%sequence),row)
        sequence += 1
        print(json.dumps(row),flush=True)
    def heartbeat():
        while not stopped.wait(30):
            print(json.dumps(dict(heartbeat=active,unix_time=time.time(),resources=resources())),flush=True)
    thread = threading.Thread(target=heartbeat,daemon=True)
    thread.start()
    def no_audit(*args, **kwargs):
        raise AssertionError('proof-only continuation attempted full World audit')
    failure = None
    try:
        with patch.object(genesis,'_genesis_phase',progress), patch.object(catalog,'_copy_phase',progress), \
                patch.object(LazyRecordStore,'_copy_phase_hook',staticmethod(progress)):
            copied = rec.measure('construction',lambda:genesis.copy_world_with_proofs(
                source,destination,rules_id=authority['rules_id'],rank_proofs=True))
        result.update(genesis_commitment=copied.commitment.hex(),genesis_store_identity=copied.manifest.store_identity)
        r.publish_receipt(output/'genesis.json',dict(commitment=copied.commitment.hex(),
            store_identity=copied.manifest.store_identity,generation=0,source=authority,
            database_bytes=destination.stat().st_size))
        # Genesis used a complete audit. All interactive phases must now use
        # the explicit proof opener without any fallback to that full audit.
        with patch.object(world_proof,'_audit_world',no_audit):
            active = 'open'
            session = rec.measure('open',lambda:open_proof_world_session(destination,
                rules_id=authority['rules_id'],expected_commitment=copied.commitment))
            rec.store = session.store
            if session.world.year != 1001 or session.world.seed != 843000:
                raise ValueError('proof genesis World differs from accepted source')
            active = 'first_step'
            rec.measure('first_step',lambda:Simulation(session.world).run(1))
            active = 'save'
            rec.measure('save',session.save)
            child = session.proof_manifest[1]
            result.update(saved_commitment=child.hex(),saved_generation=session.proof_manifest[0].generation,
                          saved_year=session.world.year)
            active = 'warm_step'
            rec.measure('warm_step',lambda:Simulation(session.world).run(1))
            if session.world.year != 1003:
                raise ValueError('warm continuation did not reach year1003')
            session.close();session=None;rec.store=None
        active = 'fresh_restore'
        result['fresh_restore'] = rec.measure('fresh_restore',lambda:fresh_restore(destination,
            authority['rules_id'],child,config['expected_saved_digest'],config['budgets']['fresh_restore']))
        result['targets_met'] = {name:rec.phases[name]['wall_seconds']<=target for name,target in TARGETS.items()}
        result.update(status='complete',acceptance='targets-met' if all(result['targets_met'].values()) else 'targets-missed')
        return result
    except BaseException as exc:
        failure = exc
        result.update(status='timeout' if isinstance(exc,TimeoutError) or type(exc).__name__=='BudgetExpired' else 'error',
                      acceptance='not-accepted',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        stopped.set();thread.join(timeout=2)
        primary = failure
        for operation in ('close','source_hash'):
            try:
                if operation == 'close':
                    if session is not None:session.close()
                else:
                    unchanged = r.file_hash(source)==authority['database']['sha256']
                    result['source_unchanged']=unchanged
                    if not unchanged:raise ValueError('original source changed')
            except BaseException as exc:
                result.update(status='error',acceptance='not-accepted')
                if failure is None:
                    failure=exc
                    result['cleanup_error']=type(exc).__name__+': '+str(exc)
                else:failure.add_note(operation+' cleanup failed: '+str(exc))
        try:r.publish_receipt(output/'result.json',result)
        except BaseException as exc:
            if failure is None:raise
            failure.add_note('result publication failed: '+str(exc))
        if primary is None and failure is not None:raise failure


def launch(root, config, *, expected_sha):
    from simulation import construction_mature_continuation_stages as stages
    root = Path(root).resolve()
    if root != Path.cwd().resolve():raise ValueError('mature genesis root differs from execution checkout')
    if os.environ.get('GITHUB_RUN_ATTEMPT') != '1':raise ValueError('mature genesis rerun requires a new request')
    identity = check_source(root,config,expected_sha)
    original = r.load_receipt(root/ORIGINAL)
    authority = stages.mature_authority()
    check_request(config,original,authority)
    required = 3*config['database']['bytes']+PIN.archive_bytes+12*1024**3
    if shutil.disk_usage(root).free < required:raise ValueError('insufficient mature source/copy/journal/proof headroom')
    output = root/'evidence/mature-genesis'
    r.publish_receipt(output/'launch.json',dict(request=config,execution=identity,required_free_bytes=required))
    source, transport = prepare_retained(root,config,identity,
        r.ArtifactRef.from_dict(original['inputs']['candidate']),
        r.ArtifactRef.from_dict(original['inputs']['previous']),original['candidate_database'],authority)
    r.publish_receipt(output/'source-authority.json',source)
    r.publish_receipt(output/'source-transport.json',transport)
    return measure(root/'source/candidate.sqlite',root/'proof.sqlite',source,config,output)


def record_exit(root, status):
    if type(status) is not int:raise ValueError('invalid mature command status')
    result_path=Path(root)/'evidence/mature-genesis/result.json'
    result=r.load_receipt(result_path) if result_path.exists() else {}
    if status==0 and result.get('status')!='complete':raise ValueError('command succeeded without complete mature evidence')
    timed_out=status in (124,137,143) or result.get('status')=='timeout'
    row=dict(schema='ate-stage06-mature-genesis-exit/1',exit_status=status,
        status='complete' if status==0 else 'timeout' if timed_out else 'error',
        censored=timed_out,acceptance=result.get('acceptance','not-accepted'))
    r.publish_receipt(Path(root)/'evidence/mature-genesis/command-exit.json',row)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','record-exit'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--status',type=int)
    args=parser.parse_args()
    if args.command=='record-exit':record_exit(args.root,args.status)
    else:
        try:
            result=launch(args.root,r.load_receipt(args.config),expected_sha=os.environ['GITHUB_SHA'])
        except BaseException as exc:
            r.publish_receipt(args.root/'evidence/mature-genesis/launch-error.json',
                dict(status='error',acceptance='not-accepted',error=type(exc).__name__+': '+str(exc)))
            raise
        raise SystemExit(0 if result['acceptance']=='targets-met' else 1)
