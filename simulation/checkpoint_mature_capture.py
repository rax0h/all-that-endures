"""Retain ONLY an unverified mature candidate using the green checkpoint harness."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import threading
import time
from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as checkpoint

SOURCE_RUN = 38508408370
SOURCE_ARTIFACT = 11870590333
SOURCE_WORKFLOW_SHA = '124c3215468a60862b7848086f00a8e768a6ed66'
SOURCE_DIGEST = '409cf0230ff1606b7eddd587a69c22076c11447eb6497e642e584c4fd3b74ef9'
WORKFLOW = '.github/workflows/stage-0-5-final-release-validation.yml'
SOURCE_CONFIG = dict(seed=843000, milestones=[1001,1002], bootstrap_year=1000,
    rules_id='stage-0-5-final-release', product_sha='2bc3c85389760ff12578857f7d2a849bc5cf9201',
    complete_format=True, initialization='mature', simulation_schema='ate-world-p2a/1')
RUNTIME_SHA = '24cc39974b0762e428e2a5a0d7581f7f92216310'
GREEN_HELPERS = {
    'simulation/complete_upgrade_checkpoint.py':'a4190fcf590c88b55d88756f5826517dd9fc1c61292c6a244ae3708d22e5b0ce',
    'simulation/checkpoint_artifacts.py':'553f872c182d246c40986be36438ada91117eee009822aa92b9fd0eeed92f7a6',
}
ROOT = Path('evidence')


def check_source(directory):
    directory=Path(directory)
    receipt=checkpoint._json(directory/'checkpoint.json')
    source=directory/'p5-long-lazy.sqlite'
    if (receipt.get('schema') != 1 or receipt.get('stage') != 'lazy'
            or receipt.get('workflow_sha') != SOURCE_WORKFLOW_SHA
            or receipt.get('config') != SOURCE_CONFIG
            or receipt.get('database') != {'name':source.name,'sha256':checkpoint.file_hash(source)}):
        raise ValueError('retained source configuration/provenance/database mismatch')
    return receipt


def proof_gate():
    run_id=38756130032
    workflow_sha='25a88883aff2c494481fee40ab0a29afed28a878'
    run=artifacts._api(f'/actions/runs/{run_id}')
    jobs=artifacts._pages(f'/actions/runs/{run_id}/jobs','jobs')
    expected={'harness-tests','source','capture','storage','interrupt','catalog','publish','continue','restore'}
    if (run.get('conclusion')!='success' or run.get('head_sha')!=workflow_sha
            or {j['name'] for j in jobs if j.get('conclusion')=='success'} != expected):
        raise ValueError('fresh-runner checkpoint proof is not green')
    artifacts.download(ROOT/'small-proof',run_id=run_id,workflow_sha=workflow_sha,
        name='checkpoint-small-restore',job='restore',workflow_path=WORKFLOW,
        members={'restore.json'},artifact_id=11983179741,
        expected_digest='240b92c2df78105f905c9ed018e23bbe30721d7eb68e4240a56e84dcb66b4667')
    result=checkpoint._json(ROOT/'small-proof/restore.json')
    if (result.get('passed') is not True or result.get('year')!=2
            or result.get('retained_original_unchanged') is not True):
        raise ValueError('fresh-runner restore proof rejected')


@contextmanager
def progress():
    from ate_sim import persistence_catalog_copy as copy
    started=time.monotonic()
    stop=threading.Event()
    def report(stage,**values):
        status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
        print(json.dumps({'stage':stage,'seconds':time.monotonic()-started,
            'rss':status.get('VmRSS','').strip(),'virtual_memory':status.get('VmSize','').strip(),
            'disk_free_bytes':shutil.disk_usage('.').free,**values}),flush=True)
    original_phase,original_restore=copy._copy_phase,copy._restore_copy_ordinals
    def phase(name,path):
        original_phase(name,path)
        report(name)
    def restore(*args,**kwargs):
        report('ordinal_restoration_started');start=time.monotonic()
        result=original_restore(*args,**kwargs)
        report('ordinal_restoration_finished',duration_seconds=time.monotonic()-start)
        return result
    def monitor():
        while not stop.wait(60):report('resource_heartbeat')
    copy._copy_phase,copy._restore_copy_ordinals=phase,restore
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        report('capture_started')
        yield
    finally:
        stop.set();thread.join(timeout=1)
        copy._copy_phase,copy._restore_copy_ordinals=original_phase,original_restore


def run_capture(source,receipt,bundle,*,rules_id,context):
    with progress():
        return checkpoint.capture(source,receipt,bundle,rules_id=rules_id,context=context)


def main():
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if sha!=os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA']!=RUNTIME_SHA:
        raise ValueError('executing harness/runtime mismatch')
    tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()
    if tree!='c3229ed9ed46bd338bf31d76e7f037d0d77b87b6':
        raise ValueError('runtime differs from green full suite and recovery')
    for path,expected in GREEN_HELPERS.items():
        if checkpoint.file_hash(path)!=expected:raise ValueError('checkpoint helper differs from green proof')
    proof_gate()
    if shutil.disk_usage('.').free < 55*1024**3:
        raise ValueError('need55GiB before downloading mature source')
    proof=artifacts.download(ROOT/'source',run_id=SOURCE_RUN,workflow_sha=SOURCE_WORKFLOW_SHA,
        name='late-lazy-checkpoint',job='late-lazy',workflow_path=WORKFLOW,
        members={'checkpoint.json','p5-long-lazy.sqlite'},artifact_id=SOURCE_ARTIFACT,
        expected_digest=SOURCE_DIGEST)
    if proof['archive_bytes']!=1339563957:raise ValueError('retained archive size mismatch')
    check_source(ROOT/'source')
    if shutil.disk_usage('.').free < 45*1024**3:
        raise ValueError('need45GiB after extracting mature source')
    context={'runtime_sha':RUNTIME_SHA,'harness_sha':sha,
        'source_artifact':{'id':SOURCE_ARTIFACT,'run_id':SOURCE_RUN,'archive_sha256':SOURCE_DIGEST}}
    started=time.monotonic()
    manifest=run_capture(ROOT/'source/p5-long-lazy.sqlite',ROOT/'source/checkpoint.json',
        ROOT/'candidate',rules_id=SOURCE_CONFIG['rules_id'],context=context)
    summary={'stage':'unverified','runtime_sha':RUNTIME_SHA,'harness_sha':sha,
        'source_artifact':proof,'construction_seconds':time.monotonic()-started,
        'database':manifest['database'],'pin':manifest['pin'],
        'disk_free_bytes':shutil.disk_usage('.').free,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    checkpoint._write_new(ROOT/'capture-summary.json',summary)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
