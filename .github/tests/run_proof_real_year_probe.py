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


def run(output):
    from ate_sim.engine import Simulation
    from ate_sim.worldgen import generate_world
    from ate_sim.persistence_session import write_cold_snapshot
    from ate_sim.persistence_lazy import convert_cold_to_lazy
    from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    from ate_sim import persistence_proof_world as world_proof
    from ate_sim import persistence_proof_manifest_publish as manifests

    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked execution source is dirty')
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='running', source=dict(head=git('rev-parse', 'HEAD'),
        runtime_tree=git('rev-parse', 'HEAD:simulation/ate_sim'), python=platform.python_version(),
        sqlite=sqlite3.sqlite_version, driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        fixture=dict(seed=843000, width=8, height=6, settlements=1, initial_year=2, saved_year=3),
        limitation='Small real generated world; not mature-world or cold-cache acceptance', phases=[])

    def publish():
        target = output/'receipt.json'
        temporary = output/'receipt.tmp'
        temporary.write_text(json.dumps(receipt, indent=2)+'\n')
        temporary.replace(target)

    def phase(label, action):
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

    rules = 'stage-0-6-real-year-probe'
    def setup():
        world = generate_world(843000, width=8, height=6, settlements=1, mature=True)
        Simulation(world).run(2)
        control = copy.deepcopy(world); Simulation(control).run(1)
        write_cold_snapshot(world, output/'cold.sqlite', rules_id=rules)
        convert_cold_to_lazy(output/'cold.sqlite', output/'lazy.sqlite', rules_id=rules, native_graph_buckets=True)
        proof = copy_world_with_proofs(output/'lazy.sqlite', output/'accepted.sqlite', rules_id=rules)
        return proof.commitment, control.digest()

    try:
        commitment, expected = phase('construction_and_eager_control', setup)
        accepted = output/'accepted.sqlite'
        original_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
        receipt['accepted_database_sha256'] = original_hash
        receipt['expected_digest'] = expected
        for mode in ('raw', 'diagnostic'):
            path = output/(mode+'.sqlite')
            phase(mode+'.copy', lambda: shutil.copyfile(accepted, path))
            session = phase(mode+'.open_and_full_admission', lambda: open_audited_proof_world_session(
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
            def restore():
                result = subprocess.run([sys.executable, '-c',
                    "import json,sys;from ate_sim.persistence_proof_world_session import open_audited_proof_world_session;"
                    "s=open_audited_proof_world_session(sys.argv[1],rules_id=sys.argv[2],expected_commitment=bytes.fromhex(sys.argv[3]));"
                    "print(json.dumps([s.world.year,s.world.digest()]));s.close()",
                    str(path), rules, child.hex()], check=True, capture_output=True, text=True, timeout=120)
                check_restored(result.stdout, expected)
            phase(mode+'.fresh_process_restore_and_digest_verification', restore)
            receipt[mode+'_storage_bytes'] = {p.name:p.stat().st_size for p in output.glob(mode+'.sqlite*')}
        if hashlib.sha256(accepted.read_bytes()).hexdigest() != original_hash:
            raise ValueError('accepted fixture changed')
        receipt['status'] = 'complete'
    except BaseException as exc:
        receipt.update(status='failed', **failure_details(exc))
        raise
    finally:
        publish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
