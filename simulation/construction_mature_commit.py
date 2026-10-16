"""Commit the pinned mature preparation; save before ordering or verification."""
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
from simulation import construction_mature_prepare as preparation
from simulation import checkpoint_mature_capture as legacy

ROOT = Path('evidence')
RUNTIME_SHA = preparation.RUNTIME_SHA
RUNTIME_TREE = preparation.RUNTIME_TREE
WORKFLOW = '.github/workflows/stage-0-5-mature-commit.yml'
BRANCH = 'sol/stage-0-5-mature-commit'
PREPARED_RUN = 38833265909
PREPARED_WORKFLOW_SHA = 'c669c29a0c04544da451a35d2631cde9cc79d253'
PREPARED_HARNESS = '2c9166dcfc60370852d6fa38820dee8ec3d2e916'
PREPARED_PRODUCER = dict(mode='ci', run_id=PREPARED_RUN,
    job='mature-prepare', workflow_sha=PREPARED_WORKFLOW_SHA)
CONTEXT = dict(runtime_sha=RUNTIME_SHA, harness_sha=PREPARED_HARNESS,
    source_artifact=dict(id=legacy.SOURCE_ARTIFACT, run_id=legacy.SOURCE_RUN,
                         archive_sha256=legacy.SOURCE_DIGEST))
SOURCE_CONFIG = legacy.SOURCE_CONFIG
SOURCE_WORKFLOW_SHA = legacy.SOURCE_WORKFLOW_SHA
PREPARED_FILES = {
    'spool.sqlite': dict(bytes=21538623488,
        sha256='fb52dda66172398245716edf59eef4477637676012563daaffbc6c31e8f417f0'),
    'target.sqlite': dict(bytes=808775680,
        sha256='13f661b7c35d6aae4cc46a7d30a001b12c264f00e6b9b0b04774c52718c53201'),
}
PREPARED_PIN = dict(captured_head=124,
    store_identity='06d24556-2bb1-4086-93f7-448f23b7eb5a',
    token='26242f24-ba41-49c0-ac97-12de79b0b6a9')


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('mature commit rerun requires inspection before replay')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA']
            or current.get('path') != WORKFLOW or current.get('head_branch') != BRANCH):
        raise ValueError('mature commit executing workflow mismatch')
    runs = artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}', 'workflow_runs')
    matching = [r['id'] for r in runs if r.get('path') == WORKFLOW
        and r.get('head_sha') == current['head_sha'] and r.get('head_branch') == BRANCH]
    if not matching or min(matching) != run_id:
        raise ValueError('duplicate mature commit run; inspect the earlier run')


def check_helpers():
    expected = dict(preparation.GREEN_HELPERS)
    expected['simulation/construction_mature_prepare.py'] = '12108ba18d1d1ef842445003437b124e8d82de56eae7c8409fdc5a3518ce5924'
    for path, digest in expected.items():
        if old.file_hash(path) != digest:
            raise ValueError('construction helper differs from green candidate')


def download_prepared():
    prepared = ROOT/'prepared'
    proof = artifacts.download(prepared, run_id=PREPARED_RUN,
        workflow_sha=PREPARED_WORKFLOW_SHA, name='construction-mature-prepared',
        job='mature-prepare', workflow_path=preparation.WORKFLOW,
        members={'target.sqlite', 'spool.sqlite', 'manifest.json'},
        artifact_id=12024550042,
        expected_digest='01db7a227f4a50a0bab347a211c09e2409880875de685cff1e32a01724322e06')
    if proof['archive_bytes'] != 3631292089:
        raise ValueError('prepared archive size mismatch')
    return prepared, proof


def run_commit(prepared, bundle):
    manifest = old._json(Path(prepared)/'manifest.json')
    if (not isinstance(manifest, dict) or manifest.get('stage') != 'prepared'
            or manifest.get('producer') != PREPARED_PRODUCER
            or manifest.get('context') != CONTEXT
            or manifest.get('files') != PREPARED_FILES
            or manifest.get('pin') != PREPARED_PIN
            or manifest.get('rules_id') != SOURCE_CONFIG['rules_id']):
        raise ValueError('prepared mature construction lineage mismatch')
    receipt = json.loads(manifest['source_receipt'])
    if (not isinstance(receipt, dict) or receipt.get('config') != SOURCE_CONFIG
            or receipt.get('workflow_sha') != SOURCE_WORKFLOW_SHA):
        raise ValueError('prepared mature source configuration mismatch')
    # This original helper authenticates every file and stream, commits on a
    # disposable copy, and retains the result before order restoration.
    with legacy.progress():
        return construction.commit_prepared(prepared, bundle, context=CONTEXT)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], text=True).strip()
    if sha != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != RUNTIME_SHA or tree != RUNTIME_TREE:
        raise ValueError('mature commit harness/runtime differs from green candidate')
    check_helpers()
    unique_launch()
    # Earlier mature commit consumed ~59.7 GiB beyond its staged inputs at
    # peak. Reserve the target copy and ~14 GiB margin as well as transport.
    if shutil.disk_usage('.').free < 100*1024**3:
        raise ValueError('need100GiB before downloading mature preparation')
    prepared, proof = download_prepared()
    if shutil.disk_usage('.').free < 75*1024**3:
        raise ValueError('need75GiB after extracting mature preparation')
    started, cpu = time.monotonic(), time.process_time()
    manifest = run_commit(prepared, ROOT/'committed')
    # Completed construction must remain uploadable if diagnostics fail.
    try:
        old._write_new(ROOT/'commit-summary.json', dict(stage='committed',
            runtime_sha=RUNTIME_SHA, execution_harness_sha=sha, context=CONTEXT,
            wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu,
            prepared_artifact=proof, files=manifest['files'], pin=manifest['pin'],
            prepared_manifest_sha256=manifest['prepared_manifest_sha256'],
            disk_free_bytes=shutil.disk_usage('.').free))
    except Exception:
        pass


if __name__ == '__main__': main()
