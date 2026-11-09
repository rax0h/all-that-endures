"""Small real-year phase timings and separate fallback attribution.

This is not the retained millennium fixture or mature-world acceptance.
"""
import argparse
import copy
import hashlib
import json
import platform
import resource
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path


def failure_details(exc):
    result = dict(error=f'{type(exc).__name__}: {exc}')
    for name in ('stdout', 'stderr', 'returncode', 'timeout', 'actual'):
        value = getattr(exc, name, None)
        if isinstance(value, bytes): value = value.decode(errors='replace')
        if value is not None: result[name] = value
    return result


def check_restored(stdout, expected):
    actual = json.loads(stdout)
    if actual != [3, expected]:
        exc = ValueError('fresh restored continuation differs from eager control')
        exc.actual = actual
        raise exc


FRESH_RESTORE_CODE = '''
import json,sys
from ate_sim import persistence_proof_world as world_proof
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session,open_proof_world_session
proof_only=sys.argv[4]=='1'
opener=open_proof_world_session if proof_only else open_audited_proof_world_session
original_audit=world_proof._audit_world
audit_calls=0
def audit(*args,**kwargs):
    global audit_calls
    audit_calls+=1
    if proof_only:raise AssertionError('proof-only fresh restore attempted a full World audit')
    return original_audit(*args,**kwargs)
world_proof._audit_world=audit
with opener(sys.argv[1],rules_id=sys.argv[2],expected_commitment=bytes.fromhex(sys.argv[3])) as session:
    state=[session.world.year,session.world.digest()]
print(json.dumps(dict(state=state,world_audit_calls=audit_calls,opener=opener.__name__)))
'''


def restore_in_fresh_process(path,rules,commitment,expected,*,proof_only=False):
    if type(proof_only) is not bool:raise ValueError('proof_only must be boolean')
    result=subprocess.run([sys.executable,'-c',FRESH_RESTORE_CODE,str(path),rules,commitment.hex(),
        '1' if proof_only else '0'],check=True,capture_output=True,text=True,timeout=120)
    evidence=json.loads(result.stdout)
    check_restored(json.dumps(evidence['state']),expected)
    wanted='open_proof_world_session' if proof_only else 'open_audited_proof_world_session'
    if (evidence.get('opener')!=wanted or type(evidence.get('world_audit_calls')) is not int
            or evidence['world_audit_calls']<0 or proof_only and evidence['world_audit_calls']!=0):
        raise ValueError('fresh restore did not honor the selected opening mode')
    return evidence


def run(output,*,rank_proofs=False,proof_only=False):
    if type(rank_proofs) is not bool:raise ValueError('rank_proofs must be boolean')
    if type(proof_only) is not bool:raise ValueError('proof_only must be boolean')
    if proof_only and not rank_proofs:raise ValueError('proof-only requires rank proofs')
    from ate_sim.engine import Simulation
    from ate_sim.worldgen import generate_world
    from ate_sim.persistence_session import write_cold_snapshot
    from ate_sim.persistence_lazy import convert_cold_to_lazy
    from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session,open_proof_world_session
    from ate_sim import persistence_proof_world as world_proof
    from ate_sim import persistence_proof_manifest_publish as manifests

    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked execution source is dirty')
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='running', source=dict(head=git('rev-parse', 'HEAD'),
        runtime_tree=git('rev-parse', 'HEAD:simulation/ate_sim'), python=platform.python_version(),
        sqlite=sqlite3.sqlite_version, driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        fixture=dict(seed=843000, width=8, height=6, settlements=1, initial_year=2, saved_year=3,
            rank_proofs=rank_proofs,proof_only=proof_only),
        limitation='Small real generated world; not mature-world or cold-cache acceptance',
        phases=[],parent_world_audits=[])
    opener=open_proof_world_session if proof_only else open_audited_proof_world_session
    active_phase=None

    def publish():
        target = output/'receipt.json'
        temporary = output/'receipt.tmp'
        temporary.write_text(json.dumps(receipt, indent=2)+'\n')
        temporary.replace(target)

    def phase(label, action):
        nonlocal active_phase
        previous_phase,active_phase=active_phase,label
        entry = dict(name=label, status='running')
        receipt['phases'].append(entry); publish()
        start, cpu = time.perf_counter(), time.process_time()
        child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            result = action(); entry['status'] = 'complete'
            return result
        except BaseException as exc:
            entry.update(status='failed', **failure_details(exc))
            raise
        finally:
            child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
            entry.update(wall_seconds=time.perf_counter()-start, parent_cpu_seconds=time.process_time()-cpu,
                child_cpu_seconds=(child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime),
                parent_peak_rss_high_water_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                child_peak_rss_high_water_kib=child_after.ru_maxrss)
            publish()
            active_phase=previous_phase

    rules = 'stage-0-6-real-year-probe'
    def setup():
        world = generate_world(843000, width=8, height=6, settlements=1, mature=True)
        Simulation(world).run(2)
        control = copy.deepcopy(world); Simulation(control).run(1)
        write_cold_snapshot(world, output/'cold.sqlite', rules_id=rules)
        convert_cold_to_lazy(output/'cold.sqlite', output/'lazy.sqlite', rules_id=rules, native_graph_buckets=True)
        proof = copy_world_with_proofs(output/'lazy.sqlite', output/'accepted.sqlite', rules_id=rules,rank_proofs=rank_proofs)
        return proof.commitment, control.digest()

    original_parent_audit=world_proof._audit_world
    def parent_audit(*args,**kwargs):
        receipt['parent_world_audits'].append(dict(phase=active_phase))
        if proof_only:raise AssertionError('proof-only continuation attempted a full World audit')
        return original_parent_audit(*args,**kwargs)

    try:
        commitment, expected = phase('construction_and_eager_control', setup)
        # Genesis construction is fully audited. Ordinary continuation below
        # must honor the explicitly selected opening contract in every phase.
        world_proof._audit_world=parent_audit
        receipt['accepted_commitment'] = commitment.hex()
        accepted = output/'accepted.sqlite'
        original_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
        receipt['accepted_database_sha256'] = original_hash
        receipt['expected_digest'] = expected
        for mode in ('raw', 'diagnostic'):
            path = output/(mode+'.sqlite')
            phase(mode+'.copy', lambda: shutil.copyfile(accepted, path))
            session = phase(mode+('.open_and_proof_admission' if proof_only else '.open_and_full_admission'), lambda: opener(
                path, rules_id=rules, expected_commitment=commitment))
            try:
                phase(mode+'.simulation_year', lambda: Simulation(session.world).run(1))
                audits, returns, shape = [], [], {}
                original_audit, original_commit = world_proof._audit_world, manifests.commit_world_manifest
                def audit(*args, **kwargs):
                    start = time.perf_counter()
                    try: return original_audit(*args, **kwargs)
                    finally: audits.append(time.perf_counter()-start)
                def capture(*args, **kwargs):
                    versions = kwargs['version_changes']
                    shape.update(version_rows=len(versions), ordinary_rows=len(kwargs['changes']),
                        event_segments=len(kwargs['new_segments']),
                        namespaces=dict(Counter(c.namespace for c in versions)),
                        identity_rows=len(kwargs['identity_changes']))
                    shape['manifest_owned_control_rows'] = 1
                    counts = Counter()
                    for c in versions:
                        if not args[0]._interval_rows('lazy_record_versions', '1', ('namespace','typed_key'),
                                (c.namespace,args[0].codec.encode(c.key)),args[1].captured_head,'lazy_record_interval',limit=1):
                            counts[c.namespace] += 1
                    shape['new_version_rows_by_namespace'] = dict(counts)
                    return original_commit(*args, **kwargs)
                def trace(frame, event, result):
                    if (event == 'return' and (result is None or result is False)
                            and frame.f_code.co_name in ('_prepare', 'validate_value_transition')):
                        file = Path(frame.f_code.co_filename).name
                        name = frame.f_code.co_name
                        if (file, name) in {('persistence_proof_world_insert.py', '_prepare'),
                            ('persistence_proof_world_value.py', 'validate_value_transition')}:
                            returns.append(dict(module=file, function=name, line=frame.f_lineno,
                                                namespace=frame.f_locals.get('ns')))
                if mode == 'diagnostic':
                    world_proof._audit_world = audit
                    manifests.commit_world_manifest = capture
                    sys.setprofile(trace)
                try:
                    phase(mode+'.save', session.save)
                finally:
                    sys.setprofile(None)
                    world_proof._audit_world, manifests.commit_world_manifest = original_audit, original_commit
                child = session.proof_manifest[1]
                if mode == 'diagnostic':
                    receipt['diagnostic'] = dict(shape=shape, fallback_returns=returns,
                        full_world_audit_seconds=audits,
                        warning='Instrumented pass; timings are not substituted for raw pass')
            finally:
                phase(mode+'.close', session.close)
            receipt[mode+'_fresh_process']=phase(mode+'.fresh_process_restore_and_digest_verification',
                lambda:restore_in_fresh_process(path,rules,child,expected,proof_only=proof_only))
            receipt[mode+'_storage_bytes'] = {p.name:p.stat().st_size for p in output.glob(mode+'.sqlite*')}
        if hashlib.sha256(accepted.read_bytes()).hexdigest() != original_hash:
            raise ValueError('accepted fixture changed')
        receipt['status'] = 'complete'
    except BaseException as exc:
        receipt.update(status='failed', **failure_details(exc))
        raise
    finally:
        world_proof._audit_world=original_parent_audit
        publish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rank-proofs',action='store_true',help='Explicitly construct seventh-root rank authority')
    parser.add_argument('--proof-only',action='store_true',help='Open through accepted proofs without full-history admission')
    args=parser.parse_args()
    if args.proof_only and not args.rank_proofs:parser.error('--proof-only requires --rank-proofs')
    run(args.output,rank_proofs=args.rank_proofs,proof_only=args.proof_only)
