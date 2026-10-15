"""Bounded small-world CI proof of checkpoint transport, retry and exact restore.

The mature fixture is deliberately not enabled here. Rerun FAILED jobs, not all
jobs: completed producer artifacts are immutable dependencies in the same run.
"""
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import time
from contextlib import contextmanager
from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as checkpoint

WORKFLOW = '.github/workflows/stage-0-5-final-release-validation.yml'
PREFIX = 'checkpoint-small-'
ROOT = Path('evidence')
RULES = 'stage-0-5-checkpoint-small'


def get(stage, members, destination=None):
    return artifacts.download(destination or ROOT/stage,
        run_id=int(os.environ['GITHUB_RUN_ID']), workflow_sha=os.environ['GITHUB_SHA'],
        name=PREFIX+stage, job=stage, workflow_path=WORKFLOW, members=set(members))


def context():
    run_id=int(os.environ['GITHUB_RUN_ID'])
    rows=artifacts._pages(f'/actions/runs/{run_id}/artifacts','artifacts')
    matching=[a for a in rows if a.get('name')==PREFIX+'source']
    if len(matching)!=1: raise ValueError('missing or ambiguous source artifact')
    a=matching[0]
    digest=artifacts.authenticate(a, artifacts._api(f'/actions/runs/{run_id}'),
        artifacts._pages(f'/actions/runs/{run_id}/jobs?filter=all','jobs'),
        run_id=run_id, workflow_sha=os.environ['GITHUB_SHA'], name=PREFIX+'source',
        job='source', workflow_path=WORKFLOW)
    return {'runtime_sha':os.environ['RUNTIME_SHA'], 'harness_sha':os.environ['HARNESS_SHA'],
        'source_artifact':{'id':a['id'],'run_id':run_id,'archive_sha256':digest}}


@contextmanager
def catalog_progress():
    from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
    from simulation.tests.catalog_sequence_scrub_probe import verification_probe
    originals={}; started=time.monotonic()
    for name in ('read_identity_group','read_owner_identity'):
        original=getattr(IdentityCatalog,name); originals[name]=original
        count=[0]
        def measured(*args,_original=original,_name=name,_count=count,**kwargs):
            value=_original(*args,**kwargs); _count[0]+=1
            if _count[0] == 1 or _count[0] % 1000 == 0:
                print(json.dumps({'catalog_progress':_name,'checked':_count[0],
                    'seconds':time.monotonic()-started}),flush=True)
            return value
        setattr(IdentityCatalog,name,measured)
    try:
        with verification_probe(ROOT/'verification.jsonl'): yield
    finally:
        for name, original in originals.items(): setattr(IdentityCatalog,name,original)


def main(stage):
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    ROOT.mkdir(exist_ok=True)
    import subprocess
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=os.environ['HARNESS_SHA']:
        raise ValueError('harness checkout mismatch')
    runtime_tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()
    if runtime_tree!='c3229ed9ed46bd338bf31d76e7f037d0d77b87b6':
        raise ValueError('runtime differs from green full-suite/recovery source')
    import persistence_p5_long_validation as p5
    if stage=='source':
        result=p5.run(843000,[1,2],0,ROOT/'source',RULES,os.environ['RUNTIME_SHA'],
                      os.environ['GITHUB_SHA'],complete_format=True,stop_after='lazy')
        assert result['checkpoint_stage']=='lazy' and not result['passed']
        return
    if stage=='restore':
        get('continue', {'result.json','restore.sqlite'})
        result=json.loads((ROOT/'continue/result.json').read_text())
        expected=result['restore_artifact']
        path=ROOT/'continue/restore.sqlite'
        before=checkpoint.file_hash(path)
        assert before==expected['sha256']
        shutil.copyfile(path, ROOT/'private-restore.sqlite')
        from ate_sim.persistence_lazy import open_lazy_world_session
        with open_lazy_world_session(ROOT/'private-restore.sqlite',rules_id=RULES) as session:
            assert session.world.year==2
            assert session.world.digest()==result['control']['2']['digest']
        assert checkpoint.file_hash(path)==before
        (ROOT/'restore.json').write_text(json.dumps({'passed':True,'year':2,
            'digest':result['control']['2']['digest'],'retained_original_unchanged':True}))
        return
    if stage=='continue':
        get('publish', {'checkpoint.json','p5-long-complete.sqlite'}, ROOT/'p5')
        result=p5.run(843000,[1,2],0,ROOT/'p5',RULES,os.environ['RUNTIME_SHA'],
                      os.environ['GITHUB_SHA'],complete_format=True,resume_from='complete')
        assert result['passed'] and all(result['p4'][str(y)]['matches_control'] for y in (1,2))
        out=ROOT/'continue';out.mkdir()
        (out/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2))
        shutil.copyfile(result['restore_artifact']['path'],out/'restore.sqlite')
        return
    expected=context()
    bundle=ROOT/'candidate'
    if stage=='capture':
        get('source',{'checkpoint.json','p5-long-lazy.sqlite'})
        checkpoint.capture(ROOT/'source/p5-long-lazy.sqlite',ROOT/'source/checkpoint.json',
                           bundle,rules_id=RULES,context=expected)
        return
    get('capture',{'candidate.sqlite','manifest.json'},bundle)
    if stage=='storage':
        checkpoint.verify_storage(bundle,ROOT/'storage.json',context=expected)
        return
    get('storage',{'storage.json'})
    storage=ROOT/'storage/storage.json'
    if stage=='interrupt':
        from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
        before=checkpoint.file_hash(bundle/'candidate.sqlite')
        original=IdentityCatalog.read_identity_group
        class Interrupted(Exception): pass
        def interrupt(*args,**kwargs):
            value=original(*args,**kwargs)
            for values in (value.occurrences,value.links):
                if hasattr(values,'close'): values.close()
            raise Interrupted()
        IdentityCatalog.read_identity_group=interrupt
        try:
            try: checkpoint.verify_catalog(bundle,storage,ROOT/'must-not-exist.json',context=expected)
            except Interrupted: pass
            else: raise AssertionError('fault did not interrupt original catalog verifier')
        finally: IdentityCatalog.read_identity_group=original
        assert not (ROOT/'must-not-exist.json').exists()
        assert checkpoint.file_hash(bundle/'candidate.sqlite')==before
        (ROOT/'interrupted.json').write_text(json.dumps({'passed':True,'candidate_unchanged':True}))
    elif stage=='catalog':
        # This fresh runner consumes only the earlier candidate and storage receipt.
        with catalog_progress():
            checkpoint.verify_catalog(bundle,storage,ROOT/'catalog.json',context=expected)
    elif stage=='publish':
        get('catalog',{'catalog.json'})
        get('source',{'checkpoint.json','p5-long-lazy.sqlite'},ROOT/'p5')
        checkpoint.publish_p5(bundle,storage,ROOT/'catalog/catalog.json',ROOT/'p5',
            context=expected,workflow_sha=os.environ['GITHUB_SHA'])
    else: raise ValueError('unknown stage')


if __name__=='__main__': main(sys.argv[1])
