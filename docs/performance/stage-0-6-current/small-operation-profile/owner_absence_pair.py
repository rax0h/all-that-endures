"""Compare raw save and warm timings on fresh copies of an accepted small proof."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


BASE = 'b8d9b2a5ba723fa40e397846289dea6d2932db8a'
SMOKE = 44873730573
PROOFS = 14695106875
CHANGES = {
    'simulation/ate_sim/persistence_lazy_identity_catalog.py',
    'simulation/ate_sim/persistence_lazy_identity_coordinator.py',
}


def git(root, *command):
    return subprocess.check_output(['git', *command], cwd=root, text=True).strip()


def check_source(root, head):
    import ate_sim
    import simulation
    if (git(root, 'rev-parse', 'HEAD') != head
            or git(root, 'status', '--porcelain', '--untracked-files=all', '--', 'simulation')
            or Path(ate_sim.__file__).resolve().parent != root / 'simulation/ate_sim'
            or {Path(path).resolve() for path in simulation.__path__} != {root / 'simulation'}):
        raise ValueError('operation comparison source differs')


def authenticate(scratch):
    from simulation import continuation_receipts as receipts
    from simulation import stage_0_6_genesis_checkpoint as checkpoints
    from simulation import stage_0_6_genesis_resume as resume
    from simulation import stage_0_6_genesis_transport as transport

    root = Path.cwd()
    check_source(root, BASE)
    green = resume.inspect_green(root)
    fresh_ref = resume.require_smoke(root, SMOKE, scratch/'acceptance')
    fresh = resume.restore_receipt(root, fresh_ref, scratch/'fresh', mode='smoke', stage='fresh_restore')
    proof_ref = resume.find_reference(root, SMOKE, PROOFS, mode='smoke', stage='proofs')
    proof = resume.restore_receipt(root, proof_ref, scratch/'proof', mode='smoke', stage='proofs')
    if fresh['parent']['receipt']['parent']['receipt'] != proof:
        raise ValueError('proof is not the accepted small ancestor')
    database = proof['database']
    if database['bytes'] > 64*1024*1024 or database['year'] != 1 or database['generation'] != 0:
        raise ValueError('comparison requires the small generation-zero proof')
    source = scratch/'source'
    transport.restore(proof['data_ref'], source, member='candidate.sqlite', member_bytes=database['bytes'],
                      compatible=lambda head: resume.compatible(root, head))
    checkpoints.verify_database(source/'candidate.sqlite', database)
    runtime, details = resume.runtime_description()
    receipts.publish_receipt(scratch/'input.json', dict(
        green=green, runtime=runtime, details=details, fresh_ref=fresh_ref, proof_ref=proof_ref, proof=proof))


def trial(scratch, output, head):
    from simulation import continuation_receipts as receipts
    from simulation import stage_0_6_genesis_checkpoint as checkpoints
    from simulation import stage_0_6_genesis_resume as resume
    from simulation import stage_0_6_genesis_stages as stages

    root = Path.cwd()
    check_source(root, head)
    proof = receipts.load_receipt(scratch/'input.json')['proof']
    runtime, _ = resume.runtime_description()
    if runtime != proof['context']['execution_runtime']:
        raise ValueError('runtime differs from authenticated proof context')
    original = scratch/'source/candidate.sqlite'
    checkpoints.verify_database(original, proof['database'])
    if shutil.disk_usage(scratch).free < 2*proof['database']['bytes'] + 64*1024*1024:
        raise ValueError('insufficient operation trial copy and journal headroom')
    with tempfile.TemporaryDirectory(prefix='owner-pair-trial-', dir=scratch) as private:
        work = Path(private)/'working.sqlite'
        try:
            timing = stages._measure(original, work, proof, output/'operations', time.monotonic()+80)
            saved = dict(context=proof['context'], proof_commitment=timing['saved_commitment'])
            fresh = stages.restore_in_fresh_process(work, saved, 40)
        finally:
            checkpoints.verify_database(original, proof['database'])
    receipts.publish_receipt(output/'trial.json', dict(head=head,
        engine=git(root, 'rev-parse', 'HEAD:simulation/ate_sim'), fresh=fresh, timing=timing))


def compare(baseline, output):
    root = Path.cwd()
    script = Path(__file__).resolve()
    head = os.environ['GITHUB_SHA']
    changes = set(git(root, 'diff', '--name-only', BASE, head, '--', 'simulation',
                      ':(exclude)simulation/tests').splitlines())
    if changes != CHANGES or git(baseline, 'rev-parse', 'HEAD') != BASE:
        raise ValueError('unexpected candidate delta or baseline')
    output.mkdir(parents=True, exist_ok=False)
    env = {key: value for key, value in os.environ.items() if key not in ('GH_TOKEN', 'GITHUB_TOKEN')}
    env['PYTHONHASHSEED'] = '0'
    # Sequential on one runner. Every trial gets a new database copy.
    order = ((baseline, BASE), (root, head), (root, head), (baseline, BASE))
    with tempfile.TemporaryDirectory(prefix='owner-pair-') as directory:
        scratch = Path(directory)
        subprocess.run([sys.executable, script, 'authenticate', scratch], cwd=baseline, check=True, timeout=110)
        (output/'input.json').write_bytes((scratch/'input.json').read_bytes())
        rows = []
        for number, (checkout, commit) in enumerate(order, 1):
            folder = output/f'trial-{number}'
            folder.mkdir()
            subprocess.run([sys.executable, script, 'trial', scratch, folder, commit],
                           cwd=checkout, env=env, check=True, timeout=130)
            row = json.loads((folder/'trial.json').read_bytes())
            phases = row['timing']['phases']
            rows.append(dict(head=commit, fresh=row['fresh'],
                seconds={key: phases[key]['wall_seconds'] for key in ('open','first_step','save','warm_step')}))
    if not all(row['fresh'] == rows[0]['fresh'] for row in rows):
        raise ValueError('fresh continuation differs across trials')
    (output/'pair.json').write_text(json.dumps(rows, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    mode, *args = sys.argv[1:]
    if mode == 'authenticate':
        authenticate(Path(args[0]))
    elif mode == 'trial':
        trial(Path(args[0]), Path(args[1]), args[2])
    elif mode == 'compare':
        compare(Path(args[0]).resolve(), Path(args[1]).resolve())
    else:
        raise SystemExit('unexpected comparison mode')
