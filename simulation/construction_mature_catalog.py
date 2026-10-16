"""Verify only the mature catalog using the saved candidate and storage receipt."""
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as old
from simulation import construction_mature_storage as storage
from simulation import checkpoint_mature_capture as legacy

ROOT = Path('evidence')
WORKFLOW = '.github/workflows/stage-0-5-mature-catalog.yml'
BRANCH = 'sol/stage-0-5-mature-catalog'
RUNTIME_SHA, RUNTIME_TREE = storage.RUNTIME_SHA, storage.RUNTIME_TREE
CONTEXT, SOURCE_CONFIG = storage.CONTEXT, storage.SOURCE_CONFIG
SOURCE_WORKFLOW_SHA, SOURCE_GENERATION = storage.SOURCE_WORKFLOW_SHA, storage.SOURCE_GENERATION
CANDIDATE_MANIFEST_SHA = storage.CANDIDATE_MANIFEST_SHA
CANDIDATE_DATABASE, CANDIDATE_PIN = storage.CANDIDATE_DATABASE, storage.CANDIDATE_PIN
STORAGE_RECEIPT_SHA = '8e4324023fd60da647d2147eaa46d2cb171026037ecca07873080f7b086f3d65'
STORAGE_RECEIPT_BYTES = 691
# The existing metadata reserve also covers the small prerequisite receipt ZIP.
WORK_FREE_BYTES, START_FREE_BYTES = storage.WORK_FREE_BYTES, storage.START_FREE_BYTES


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('mature catalog rerun requires inspection before retry')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA']
            or current.get('path') != WORKFLOW or current.get('head_branch') != BRANCH):
        raise ValueError('mature catalog executing workflow mismatch')
    runs = artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}', 'workflow_runs')
    matching = [r['id'] for r in runs if r.get('path') == WORKFLOW
        and r.get('head_sha') == current['head_sha'] and r.get('head_branch') == BRANCH]
    if not matching or min(matching) != run_id:
        raise ValueError('duplicate mature catalog run; inspect the earlier run')


def check_helpers():
    storage.check_helpers()
    if old.file_hash('simulation/construction_mature_storage.py') != '7117313e3003d368dce5f658a363bd57a92e2d34e355ee81af1f9b287a61ce36':
        raise ValueError('storage helper differs from reviewed candidate')


def download_candidate():
    candidate = ROOT/'candidate'
    proof = artifacts.download(candidate, run_id=38867766111,
        workflow_sha='8b8c108f032f1e6d58339cc436310402b40a10ce',
        workflow_path=storage.ordering.WORKFLOW, name='construction-mature-ordered', job='mature-orders',
        members={'candidate.sqlite', 'manifest.json'}, artifact_id=12032507300,
        expected_digest='b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4')
    if proof['archive_bytes'] != storage.CANDIDATE_ARCHIVE_BYTES:
        raise ValueError('ordered candidate archive size mismatch')
    return candidate, proof


def download_storage():
    directory = ROOT/'storage'
    proof = artifacts.download(directory, run_id=38872643738,
        workflow_sha='4f1a7d7f0bd6c90704b5370f5e508669afe3b00f',
        workflow_path=storage.WORKFLOW, name='construction-mature-storage', job='mature-storage',
        members={'storage.json'}, artifact_id=12037828504,
        expected_digest='7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4')
    if proof['archive_bytes'] != 554:
        raise ValueError('storage receipt archive size mismatch')
    return directory/'storage.json', proof


def run_catalog(candidate, storage_receipt, receipt):
    candidate, storage_receipt, receipt = Path(candidate), Path(storage_receipt), Path(receipt)
    if receipt.exists(): raise FileExistsError(receipt)
    if old.file_hash(candidate/'manifest.json') != CANDIDATE_MANIFEST_SHA:
        raise ValueError('ordered mature candidate lineage mismatch')
    m = old._json(candidate/'manifest.json')
    if (not isinstance(m, dict) or m.get('stage') != 'unverified' or m.get('context') != CONTEXT
            or m.get('database') != CANDIDATE_DATABASE or m.get('pin') != CANDIDATE_PIN
            or m.get('source_generation') != SOURCE_GENERATION):
        raise ValueError('ordered mature candidate lineage mismatch')
    source = json.loads(m['source_receipt'])
    if (not isinstance(source, dict) or source.get('config') != SOURCE_CONFIG
            or source.get('workflow_sha') != SOURCE_WORKFLOW_SHA):
        raise ValueError('ordered mature source configuration mismatch')
    if (storage_receipt.stat().st_size != STORAGE_RECEIPT_BYTES
            or old.file_hash(storage_receipt) != STORAGE_RECEIPT_SHA):
        raise ValueError('retained storage receipt differs from inspected artifact')
    # The unchanged helper validates typed candidate authority and the exact
    # original storage receipt, then runs only the original catalog verifier.
    with redirect_stdout(storage._DiagnosticOutput(sys.stdout)), legacy.progress():
        old.verify_catalog(candidate, storage_receipt, receipt, context=CONTEXT)
    if (old.file_hash(storage_receipt) != STORAGE_RECEIPT_SHA
            or old.file_hash(candidate/'manifest.json') != CANDIDATE_MANIFEST_SHA):
        raise ValueError('catalog changed retained prerequisite')
    return old._json(receipt)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], text=True).strip()
    if sha != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != RUNTIME_SHA or tree != RUNTIME_TREE:
        raise ValueError('mature catalog harness/runtime differs from reviewed candidate')
    check_helpers(); unique_launch()
    if shutil.disk_usage('.').free < START_FREE_BYTES:
        raise ValueError(f'need {START_FREE_BYTES} bytes disk headroom before catalog downloads')
    candidate, candidate_proof = download_candidate()
    storage_receipt, storage_proof = download_storage()
    if shutil.disk_usage('.').free < WORK_FREE_BYTES:
        raise ValueError(f'need {WORK_FREE_BYTES} bytes disk headroom before catalog verification')
    (ROOT/'catalog').mkdir()
    started, cpu = time.monotonic(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_SELF)
    result = run_catalog(candidate, storage_receipt, ROOT/'catalog/catalog.json')
    # Completed original receipts remain uploadable if later diagnostics fail.
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        old._write_new(ROOT/'catalog-summary.json', dict(stage='catalog-verified',
            execution_harness_sha=sha, runtime_sha=RUNTIME_SHA, context=CONTEXT,
            wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu,
            filesystem_output_blocks=usage.ru_oublock-before.ru_oublock,
            peak_rss_kib=usage.ru_maxrss, candidate_artifact=candidate_proof,
            storage_artifact=storage_proof, receipt=result,
            receipt_sha256=old.file_hash(ROOT/'catalog/catalog.json'),
            receipt_bytes=(ROOT/'catalog/catalog.json').stat().st_size,
            disk_free_bytes=shutil.disk_usage('.').free))
    except Exception:
        pass


if __name__ == '__main__': main()
