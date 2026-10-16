"""Save mature construction inputs only; commit/ordering require later jobs."""
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time
from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as old
from simulation import construction_checkpoint as construction
from simulation import checkpoint_mature_capture as legacy

ROOT=Path('evidence')
RUNTIME_SHA='bbc3cbf11becb58aa4b9483114559fd1296878f1'
RUNTIME_TREE='3c7c833dbec178dc513c21ddf1ccdaa6f79d430a'
WORKFLOW='.github/workflows/stage-0-5-mature-prepare.yml'
BRANCH='sol/stage-0-5-mature-prepared-inputs'
PROOF_WORKFLOW='.github/workflows/stage-0-5-construction-proof.yml'
PROOF_WORKFLOW_SHA='d8a2da54f6c83e2088b9ef107dfc5bdc2a919033'
PROOF_JOBS={'harness-tests','full-suite','source','recovery','prepare','interrupt',
    'commit','orders','storage','catalog','publish','continue','restore'}
GREEN_HELPERS={
    'simulation/construction_checkpoint.py':'57a14d227b0058c2fbce9e4d27fb0f29420e930753a86eca3364348f1f6c79c4',
    'simulation/complete_upgrade_checkpoint.py':'a4190fcf590c88b55d88756f5826517dd9fc1c61292c6a244ae3708d22e5b0ce',
    'simulation/checkpoint_artifacts.py':'553f872c182d246c40986be36438ada91117eee009822aa92b9fd0eeed92f7a6',
}


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT','1')!='1':
        raise ValueError('mature preparation rerun requires inspection before reconstruction')
    run_id=int(os.environ['GITHUB_RUN_ID'])
    current=artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha')!=os.environ['GITHUB_SHA'] or current.get('path')!=WORKFLOW
            or current.get('head_branch')!=BRANCH):
        raise ValueError('mature preparation executing workflow mismatch')
    runs=artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}','workflow_runs')
    matching=[r['id'] for r in runs if r.get('path')==WORKFLOW
        and r.get('head_sha')==current['head_sha'] and r.get('head_branch')==BRANCH]
    if not matching or min(matching)!=run_id:
        raise ValueError('duplicate mature preparation run; inspect the earlier run')


def proof_gate():
    run_id=38819525026
    run=artifacts._api(f'/actions/runs/{run_id}')
    jobs=artifacts._pages(f'/actions/runs/{run_id}/jobs','jobs')
    if (run.get('conclusion')!='success' or run.get('head_sha')!=PROOF_WORKFLOW_SHA
            or run.get('path')!=PROOF_WORKFLOW
            or {j['name'] for j in jobs if j.get('conclusion')=='success'}!=PROOF_JOBS):
        raise ValueError('construction proof/full-suite/recovery gates are not green')
    artifacts.download(ROOT/'proof',run_id=run_id,workflow_sha=PROOF_WORKFLOW_SHA,
        name='construction-small-restore',job='restore',workflow_path=PROOF_WORKFLOW,
        members={'restore.json'},artifact_id=12011234609,
        expected_digest='22315f21ac3cf810e4d326b6d9d62e010cc5a6c96c3bc897a6d511ab2b626ebe')
    result=old._json(ROOT/'proof/restore.json')
    if (result.get('passed') is not True or result.get('year')!=2
            or result.get('retained_original_unchanged') is not True):
        raise ValueError('pinned construction restore proof rejected')


def run_prepare(source,receipt,bundle,*,rules_id,context):
    with legacy.progress():
        return construction.prepare(source,receipt,bundle,rules_id=rules_id,context=context)


def main():
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()
    if sha!=os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA']!=RUNTIME_SHA or tree!=RUNTIME_TREE:
        raise ValueError('mature preparation harness/runtime differs from green candidate')
    for path,expected in GREEN_HELPERS.items():
        if old.file_hash(path)!=expected:raise ValueError('construction helper differs from green candidate')
    unique_launch();proof_gate()
    if shutil.disk_usage('.').free<55*1024**3:raise ValueError('need55GiB before mature source download')
    proof=artifacts.download(ROOT/'source',run_id=legacy.SOURCE_RUN,workflow_sha=legacy.SOURCE_WORKFLOW_SHA,
        name='late-lazy-checkpoint',job='late-lazy',workflow_path=legacy.WORKFLOW,
        members={'checkpoint.json','p5-long-lazy.sqlite'},artifact_id=legacy.SOURCE_ARTIFACT,
        expected_digest=legacy.SOURCE_DIGEST)
    if proof['archive_bytes']!=1339563957:raise ValueError('retained source archive size mismatch')
    legacy.check_source(ROOT/'source')
    if shutil.disk_usage('.').free<45*1024**3:raise ValueError('need45GiB after mature source extraction')
    context=dict(runtime_sha=RUNTIME_SHA,harness_sha=sha,
        source_artifact=dict(id=legacy.SOURCE_ARTIFACT,run_id=legacy.SOURCE_RUN,archive_sha256=legacy.SOURCE_DIGEST))
    started,cpu=time.monotonic(),time.process_time()
    manifest=run_prepare(ROOT/'source/p5-long-lazy.sqlite',ROOT/'source/checkpoint.json',
        ROOT/'prepared',rules_id=legacy.SOURCE_CONFIG['rules_id'],context=context)
    # The completed durable bundle is the critical result. No diagnostic write
    # or stdout operation after that boundary may suppress its mandatory upload.
    try:
        summary=dict(stage='prepared',runtime_sha=RUNTIME_SHA,harness_sha=sha,
            wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
            files=manifest['files'],streams=manifest['streams'],pin=manifest['pin'],
            source_artifact=proof,disk_free_bytes=shutil.disk_usage('.').free)
        old._write_new(ROOT/'prepare-summary.json',summary)
    except Exception:
        pass


if __name__=='__main__':main()
