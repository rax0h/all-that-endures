"""Verify the retained mature candidate's storage; retain one checked receipt."""
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
from simulation import construction_mature_orders as ordering
from simulation import checkpoint_mature_capture as legacy

ROOT = Path('evidence')
WORKFLOW = '.github/workflows/stage-0-5-mature-storage.yml'
BRANCH = 'sol/stage-0-5-mature-storage'
RUNTIME_SHA, RUNTIME_TREE = ordering.RUNTIME_SHA, ordering.RUNTIME_TREE
CONTEXT = ordering.CONTEXT
SOURCE_CONFIG, SOURCE_WORKFLOW_SHA = ordering.SOURCE_CONFIG, ordering.SOURCE_WORKFLOW_SHA
SOURCE_GENERATION = 124
CANDIDATE_MANIFEST_SHA = 'fd457aee712a4cfcfe69d10445e38294b21b34b5fe8496cbadb4484f6fbadf73'
CANDIDATE_DATABASE = dict(name='candidate.sqlite', bytes=29601284096,
    sha256='d96a0932ab0cb101de69e10ce4f0519de896d5cae44ee947c100b8af1429c7ee')
CANDIDATE_PIN = ordering.COMMITTED_PIN
CANDIDATE_ARCHIVE_BYTES = 4342414844
# Verification is read-only. Reserve an additional candidate-sized allowance
# for SQLite scratch plus 8 GiB, separately from transport and retained input.
WORK_FREE_BYTES = CANDIDATE_DATABASE['bytes'] + 8*1024**3
START_FREE_BYTES = WORK_FREE_BYTES + CANDIDATE_DATABASE['bytes'] + CANDIDATE_ARCHIVE_BYTES + 64*1024**2


class _DiagnosticOutput:
    """Logging failures must not strand a receipt already saved by the verifier."""
    def __init__(self, stream): self.stream = stream

    def write(self, value):
        try: self.stream.write(value)
        except Exception: pass
        return len(value)

    def flush(self):
        try: self.stream.flush()
        except Exception: pass


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('mature storage rerun requires inspection before retry')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA']
            or current.get('path') != WORKFLOW or current.get('head_branch') != BRANCH):
        raise ValueError('mature storage executing workflow mismatch')
    runs = artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}', 'workflow_runs')
    matching = [r['id'] for r in runs if r.get('path') == WORKFLOW
        and r.get('head_sha') == current['head_sha'] and r.get('head_branch') == BRANCH]
    if not matching or min(matching) != run_id:
        raise ValueError('duplicate mature storage run; inspect the earlier run')


def check_helpers():
    ordering.check_helpers()
    if old.file_hash('simulation/construction_mature_orders.py') != '9287091395fb37ed090d148f89b58617b1927e43dbd8e57532102d23d7c4d3f5':
        raise ValueError('ordering helper differs from reviewed candidate')


def download_candidate():
    candidate = ROOT/'candidate'
    proof = artifacts.download(candidate, run_id=38867766111,
        workflow_sha='8b8c108f032f1e6d58339cc436310402b40a10ce',
        workflow_path=ordering.WORKFLOW, name='construction-mature-ordered', job='mature-orders',
        members={'candidate.sqlite', 'manifest.json'}, artifact_id=12032507300,
        expected_digest='b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4')
    if proof['archive_bytes'] != CANDIDATE_ARCHIVE_BYTES:
        raise ValueError('ordered candidate archive size mismatch')
    return candidate, proof


def run_storage(candidate, receipt):
    candidate, receipt = Path(candidate), Path(receipt)
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
    # The unchanged verifier validates all candidate bytes and typed authority,
    # runs store.verify_all() in a read-only snapshot, then durably writes the
    # original storage receipt. Only diagnostic output errors are suppressed.
    with redirect_stdout(_DiagnosticOutput(sys.stdout)), legacy.progress():
        old.verify_storage(candidate, receipt, context=CONTEXT)
    return old._json(receipt)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], text=True).strip()
    if sha != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != RUNTIME_SHA or tree != RUNTIME_TREE:
        raise ValueError('mature storage harness/runtime differs from reviewed candidate')
    check_helpers()
    unique_launch()
    if shutil.disk_usage('.').free < START_FREE_BYTES:
        raise ValueError(f'need {START_FREE_BYTES} bytes disk headroom before candidate download')
    candidate, proof = download_candidate()
    if shutil.disk_usage('.').free < WORK_FREE_BYTES:
        raise ValueError(f'need {WORK_FREE_BYTES} bytes disk headroom before storage verification')
    (ROOT/'storage').mkdir()
    started, cpu = time.monotonic(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_SELF)
    result = run_storage(candidate, ROOT/'storage/storage.json')
    # A completed receipt must remain uploadable if later diagnostics fail.
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        old._write_new(ROOT/'storage-summary.json', dict(stage='storage-verified',
            execution_harness_sha=sha, runtime_sha=RUNTIME_SHA, context=CONTEXT,
            wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu,
            filesystem_output_blocks=usage.ru_oublock-before.ru_oublock,
            peak_rss_kib=usage.ru_maxrss, candidate_artifact=proof, receipt=result,
            receipt_sha256=old.file_hash(ROOT/'storage/storage.json'),
            receipt_bytes=(ROOT/'storage/storage.json').stat().st_size,
            disk_free_bytes=shutil.disk_usage('.').free))
    except Exception:
        pass


if __name__ == '__main__': main()
