"""Small hosted recovery proof. Never execute against a mature checkpoint."""
import json
import os
from pathlib import Path
import subprocess
import sys
from simulation import stage_0_6_genesis_checkpoint as c

CHILD='''
import os
from unittest.mock import patch
from ate_sim import persistence_proof_world_copy as genesis
real=genesis._rebase_private_snapshot
def interrupted(*args,**kwargs):
    def phase(name):
        if name=='rebase.ordinary_complete':os._exit(77)
    with patch.object(genesis,'_genesis_phase',phase):return real(*args,**kwargs)
genesis._rebase_private_snapshot=interrupted
from simulation.stage_0_6_genesis_resume import main
main()
'''


def main():
    if os.environ.get('MODE')!='smoke' or os.environ.get('GITHUB_JOB')!='rebase':raise ValueError('recovery drill is smoke-only')
    parent_run=int(os.environ['PARENT_RUN']);parent_id=int(os.environ['PARENT_ID'])
    if min(parent_run,parent_id)<=0:raise ValueError('missing real checkpoint reference')
    work=Path('recovery-work');work.mkdir(exist_ok=False)
    command=[sys.executable,'-c',CHILD,'run-stage','--stage','rebase','--mode','smoke',
        '--parent-run',str(parent_run),'--parent-artifact',str(parent_id),'--workspace',str(work)]
    with (work/'worker.log').open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    if result.returncode!=77:raise AssertionError('worker did not reach the intended mid-transaction crash: '+str(result.returncode))
    retained=c.load(work/'input-metadata',require_remote=True)
    if retained['stage']!='catalog' or retained['context']['mode']!='smoke':raise AssertionError('drill used wrong source')
    c.verify_database(work/'input-data/candidate.sqlite',retained['database'])
    if (work/'out').exists():raise AssertionError('crashed worker published a completed checkpoint')
    proof=dict(status='passed',worker_exit=77,interrupted_stage='rebase',retained_stage='catalog',
        receipt_sha256=c.receipt_hash(retained),database_sha256=retained['database']['sha256'],
        next_action='ordinary rebase step restores the same immutable parent in a fresh process')
    (work/'recovery.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
