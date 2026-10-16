"""Restore ordering from retained mature construction; save before verification."""
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as old
from simulation import construction_checkpoint as construction
from simulation import construction_mature_commit as commit
from simulation import checkpoint_mature_capture as legacy

ROOT = Path('evidence')
WORKFLOW = '.github/workflows/stage-0-5-mature-orders.yml'
BRANCH = 'sol/stage-0-5-mature-orders'
RUNTIME_SHA, RUNTIME_TREE = commit.RUNTIME_SHA, commit.RUNTIME_TREE
CONTEXT = commit.CONTEXT
SOURCE_CONFIG, SOURCE_WORKFLOW_SHA = commit.SOURCE_CONFIG, commit.SOURCE_WORKFLOW_SHA
PREPARED_PRODUCER = commit.PREPARED_PRODUCER
PREPARED_FILES, PREPARED_PIN = commit.PREPARED_FILES, commit.PREPARED_PIN
PREPARED_MANIFEST_SHA = '15954ddf26504c15f195b1915fabb337911609fbbf7ca7359181c8b59b121557'
COMMITTED_RUN = 38851921152
COMMITTED_WORKFLOW_SHA = '0acb45ef35748f7eda3f8d212c5c33c5d408be8f'
COMMITTED_PRODUCER = dict(mode='ci', run_id=COMMITTED_RUN,
    job='mature-commit', workflow_sha=COMMITTED_WORKFLOW_SHA)
COMMITTED_FILES = {'target.sqlite': dict(bytes=29405450240,
    sha256='06b18a6eb568863e8236ac270e507343cfefc9e7c7aaed4c58175619f53d28ad')}
COMMITTED_PIN = dict(PREPARED_PIN, captured_head=125)
COMMITTED_ARCHIVE_BYTES = 4332758248

# Original ordering updates the private database under SQLite DELETE journaling.
# Reserve one full target copy, one full rollback journal, and 8 GiB of margin.
# Earlier immutable inputs and the larger in-flight ZIP must also fit at start.
ORDER_FREE_BYTES = 2*COMMITTED_FILES['target.sqlite']['bytes'] + 8*1024**3
START_FREE_BYTES = (ORDER_FREE_BYTES + COMMITTED_FILES['target.sqlite']['bytes']
    + sum(v['bytes'] for v in PREPARED_FILES.values()) + COMMITTED_ARCHIVE_BYTES + 64*1024**2)


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('mature ordering rerun requires inspection before retry')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA']
            or current.get('path') != WORKFLOW or current.get('head_branch') != BRANCH):
        raise ValueError('mature ordering executing workflow mismatch')
    runs = artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}', 'workflow_runs')
    matching = [r['id'] for r in runs if r.get('path') == WORKFLOW
        and r.get('head_sha') == current['head_sha'] and r.get('head_branch') == BRANCH]
    if not matching or min(matching) != run_id:
        raise ValueError('duplicate mature ordering run; inspect the earlier run')


def check_helpers():
    commit.check_helpers()
    for path, digest in {
        'simulation/construction_mature_commit.py': '245584bdb8aab90b00b679528ca0b21d9d8f7c19e0d696db79fdfc0ac7abf0bd',
        'simulation/checkpoint_mature_capture.py': 'e7bbb3c00ecd8f0b266610314cd56d5c96d193959c7a8dede94697b4baa0c1a2',
    }.items():
        if old.file_hash(path) != digest:
            raise ValueError('ordering helper differs from reviewed candidate')


def download_prepared():
    prepared = ROOT/'prepared'
    proof = artifacts.download(prepared, run_id=commit.PREPARED_RUN,
        workflow_sha=commit.PREPARED_WORKFLOW_SHA, name='construction-mature-prepared',
        job='mature-prepare', workflow_path=commit.preparation.WORKFLOW,
        members={'target.sqlite', 'spool.sqlite', 'manifest.json'}, artifact_id=12024550042,
        expected_digest='01db7a227f4a50a0bab347a211c09e2409880875de685cff1e32a01724322e06')
    if proof['archive_bytes'] != 3631292089:
        raise ValueError('prepared archive size mismatch')
    return prepared, proof


def download_committed():
    committed = ROOT/'committed'
    proof = artifacts.download(committed, run_id=COMMITTED_RUN,
        workflow_sha=COMMITTED_WORKFLOW_SHA, workflow_path=commit.WORKFLOW,
        name='construction-mature-committed', job='mature-commit',
        members={'target.sqlite', 'manifest.json'}, artifact_id=12030703178,
        expected_digest='ec5dbeb0224a7bae109771b59da2bdca6eca451ebf67f1f5102fc77b91506077')
    if proof['archive_bytes'] != COMMITTED_ARCHIVE_BYTES:
        raise ValueError('committed archive size mismatch')
    return committed, proof


def run_orders(prepared, committed, candidate):
    prepared, committed = Path(prepared), Path(committed)
    if old.file_hash(prepared/'manifest.json') != PREPARED_MANIFEST_SHA:
        raise ValueError('prepared mature ordering lineage mismatch')
    p, c = old._json(prepared/'manifest.json'), old._json(committed/'manifest.json')
    if (not isinstance(p, dict) or p.get('stage') != 'prepared'
            or p.get('producer') != PREPARED_PRODUCER or p.get('context') != CONTEXT
            or p.get('files') != PREPARED_FILES or p.get('pin') != PREPARED_PIN):
        raise ValueError('prepared mature ordering lineage mismatch')
    receipt = json.loads(p['source_receipt'])
    if (not isinstance(receipt, dict) or receipt.get('config') != SOURCE_CONFIG
            or receipt.get('workflow_sha') != SOURCE_WORKFLOW_SHA):
        raise ValueError('prepared mature source configuration mismatch')
    if (not isinstance(c, dict) or c.get('stage') != 'committed'
            or c.get('producer') != COMMITTED_PRODUCER or c.get('context') != CONTEXT
            or c.get('files') != COMMITTED_FILES or c.get('pin') != COMMITTED_PIN
            or c.get('prepared_manifest_sha256') != PREPARED_MANIFEST_SHA
            or any(c.get(k) != p.get(k) for k in
                ('rules_id', 'source_receipt', 'source_receipt_sha256', 'source_generation'))):
        raise ValueError('committed mature ordering lineage mismatch')
    # The original helper checks exact files, typed manifests, generation/pin,
    # and all consumed order/state commitments before retaining any candidate.
    with legacy.progress():
        return construction.restore_orders(prepared, committed, candidate, context=CONTEXT)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], text=True).strip()
    if sha != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != RUNTIME_SHA or tree != RUNTIME_TREE:
        raise ValueError('mature ordering harness/runtime differs from reviewed candidate')
    check_helpers()
    unique_launch()
    if shutil.disk_usage('.').free < START_FREE_BYTES:
        raise ValueError(f'need {START_FREE_BYTES} bytes disk headroom before ordering downloads')
    prepared, prepared_proof = download_prepared()
    committed, committed_proof = download_committed()
    if shutil.disk_usage('.').free < ORDER_FREE_BYTES:
        raise ValueError(f'need {ORDER_FREE_BYTES} bytes disk headroom before ordering copy')
    started, cpu = time.monotonic(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_SELF)
    manifest = run_orders(prepared, committed, ROOT/'candidate')
    # The closed unverified candidate is the durable boundary. Diagnostic
    # failures after it must not suppress the mandatory artifact upload.
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        old._write_new(ROOT/'orders-summary.json', dict(stage='unverified',
            runtime_sha=RUNTIME_SHA, execution_harness_sha=sha, context=CONTEXT,
            wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu,
            filesystem_output_blocks=usage.ru_oublock-before.ru_oublock,
            peak_rss_kib=usage.ru_maxrss, prepared_artifact=prepared_proof,
            committed_artifact=committed_proof, database=manifest['database'], pin=manifest['pin'],
            manifest_sha256=old.file_hash(ROOT/'candidate/manifest.json'),
            prepared_manifest_sha256=PREPARED_MANIFEST_SHA,
            committed_manifest_sha256=old.file_hash(committed/'manifest.json'),
            disk_free_bytes=shutil.disk_usage('.').free))
    except Exception:
        pass


if __name__ == '__main__': main()
