"""Run one isolated save against the identical accepted small-year fixture.

Select the runtime with PYTHONPATH. Run baseline then candidate sequentially
after other tests have stopped. This driver never launches the mature fixture.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run(args):
    from ate_sim.engine import Simulation
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    from ate_sim import persistence_proof_world as proof
    import ate_sim

    accepted = args.accepted.resolve()
    source_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
    args.work.mkdir(parents=True, exist_ok=False)
    path = args.work / 'save.sqlite'
    shutil.copyfile(accepted, path)
    result = dict(label=args.label, runtime_package=str(Path(ate_sim.__file__).parent),
        source_commit=args.source_commit, runtime_tree=args.runtime_tree,
        driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        accepted_database_sha256=source_hash, expected_digest=args.expected,
        limitation='Small generated year only; warm local filesystem; not mature-world acceptance')
    started = time.perf_counter()
    session = open_audited_proof_world_session(path, rules_id='stage-0-6-real-year-probe',
        expected_commitment=bytes.fromhex(args.commitment))
    result['open_seconds'] = time.perf_counter() - started
    try:
        started = time.perf_counter()
        Simulation(session.world).run(1)
        result['step_seconds'] = time.perf_counter() - started
        audit_times = []
        original = proof._audit_world
        def audit(*a, **kw):
            start = time.perf_counter()
            try:return original(*a, **kw)
            finally:audit_times.append(time.perf_counter()-start)
        proof._audit_world = audit
        try:
            start = time.perf_counter()
            generation = session.save()
            result['save_seconds'] = time.perf_counter() - start
        finally:proof._audit_world = original
        result.update(generation=generation, save_world_audits=len(audit_times),
            save_world_audit_seconds=audit_times, saved_commitment=session.proof_manifest[1].hex())
    finally:session.close()
    restored = subprocess.run([sys.executable, '-c',
        "import json,sys;from ate_sim.persistence_proof_world_session import open_audited_proof_world_session;"
        "s=open_audited_proof_world_session(sys.argv[1],rules_id='stage-0-6-real-year-probe',expected_commitment=bytes.fromhex(sys.argv[2]));"
        "print(json.dumps([s.world.year,s.world.digest()]));s.close()",
        str(path), result['saved_commitment']], check=True, text=True, capture_output=True, timeout=180)
    if json.loads(restored.stdout) != [3, args.expected]:
        raise ValueError('fresh-process result differs from independent eager control')
    if hashlib.sha256(accepted.read_bytes()).hexdigest() != source_hash:
        raise ValueError('accepted input changed')
    result.update(status='complete', fresh_process_eager_match=True, accepted_input_unchanged=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('label', 'commitment', 'expected', 'source-commit', 'runtime-tree'):parser.add_argument('--'+name, required=True)
    for name in ('accepted', 'work', 'output'):parser.add_argument('--'+name, required=True, type=Path)
    run(parser.parse_args())
