"""Bounded fresh-runner proof; this module never starts mature construction."""
from contextlib import contextmanager
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
from simulation import construction_checkpoint as construction

ROOT=Path('evidence')
WORKFLOW='.github/workflows/stage-0-5-construction-proof.yml'
PREFIX='construction-small-'
RULES='stage-0-5-construction-proof'
MEMBERS={
    'source':{'checkpoint.json','p5-long-lazy.sqlite','fixture.json'},
    'prepare':{'target.sqlite','spool.sqlite','manifest.json'},
    'interrupt':{'interrupted.json'}, 'commit':{'target.sqlite','manifest.json'},
    'orders':{'candidate.sqlite','manifest.json'}, 'storage':{'storage.json'},
    'catalog':{'catalog.json'}, 'publish':{'checkpoint.json','p5-long-complete.sqlite'},
    'continue':{'result.json','restore.sqlite'}, 'restore':{'restore.json'},
}


def get(stage):
    destination=ROOT/stage
    artifacts.download(destination,run_id=int(os.environ['GITHUB_RUN_ID']),
        workflow_sha=os.environ['GITHUB_SHA'],name=PREFIX+stage,job=stage,
        workflow_path=WORKFLOW,members=MEMBERS[stage])
    if stage in ('prepare','commit'):
        producer=old._json(destination/'manifest.json').get('producer')
        expected=dict(mode='ci',run_id=int(os.environ['GITHUB_RUN_ID']),job=stage,
            workflow_sha=os.environ['GITHUB_SHA'])
        if producer!=expected:raise ValueError('construction manifest producer mismatch')
    return destination


def context():
    run_id=int(os.environ['GITHUB_RUN_ID'])
    rows=artifacts._pages(f'/actions/runs/{run_id}/artifacts','artifacts')
    matches=[a for a in rows if a.get('name')==PREFIX+'source']
    if len(matches)!=1:raise ValueError('missing or ambiguous proof source')
    a=matches[0]
    digest=artifacts.authenticate(a,artifacts._api(f'/actions/runs/{run_id}'),
        artifacts._pages(f'/actions/runs/{run_id}/jobs?filter=all','jobs'),
        run_id=run_id,workflow_sha=os.environ['GITHUB_SHA'],name=PREFIX+'source',job='source',workflow_path=WORKFLOW)
    return dict(runtime_sha=os.environ['RUNTIME_SHA'],harness_sha=os.environ['HARNESS_SHA'],
        source_artifact=dict(id=a['id'],run_id=run_id,archive_sha256=digest))


@contextmanager
def measure(stage):
    started,cpu=time.monotonic(),time.process_time()
    before=resource.getrusage(resource.RUSAGE_SELF);ok=False
    print(json.dumps(dict(stage=stage+'_started')),flush=True)
    try:
        yield
        ok=True
    finally:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
        print(json.dumps(dict(stage=stage+'_finished',outcome='success' if ok else 'failure',
            wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
            disk_free_bytes=shutil.disk_usage('.').free,
            peak_rss_kib=int(status['VmHWM'].split()[0]),peak_virtual_kib=int(status['VmPeak'].split()[0]),
            filesystem_output_blocks=usage.ru_oublock-before.ru_oublock)),flush=True)


def fixture_world(generate,seed,**kwargs):
    from ate_sim.skills import SkillHistory
    world=generate(seed,**kwargs); shared=list(range(32))
    for person in sorted(world.people)[:2]:
        world.skills.skills[person,'craft']=SkillHistory(person,'craft',provenance=shared)
    return world


def _unchanged(directory, expected):
    return {p.name:old.file_hash(p) for p in directory.iterdir()}==expected


def execute(stage):
    import persistence_p5_long_validation as p5
    ROOT.mkdir(exist_ok=True)
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if head!=os.environ['HARNESS_SHA'] or head!=os.environ['RUNTIME_SHA']:
        raise ValueError('construction proof checkout/runtime mismatch')
    if stage=='source':
        original=p5.generate_world
        p5.generate_world=lambda seed,**kw:fixture_world(original,seed,**kw)
        try:
            p5.run(843000,[1,2],0,ROOT/'source',RULES,head,os.environ['GITHUB_SHA'],
                complete_format=True,stop_after='lazy')
        finally:p5.generate_world=original
        with old._open(ROOT/'source/p5-long-lazy.sqlite',RULES) as store:
            count=store.db.execute("SELECT count(*) FROM lazy_record_versions WHERE namespace=? AND valid_to IS NULL",
                ('aux.lazy.sequence.descriptors',)).fetchone()[0]
            if not count:raise AssertionError('proof source lacks counted histories')
        old._write_new(ROOT/'source/fixture.json',dict(counted_histories=count,shared_nested_history=True))
        return
    if stage=='restore':
        previous=get('continue'); result=old._json(previous/'result.json')
        retained=previous/'restore.sqlite'; before=old.file_hash(retained)
        if before!=result['restore_artifact']['sha256']:raise ValueError('restore artifact digest mismatch')
        private=ROOT/'private-restore.sqlite';shutil.copyfile(retained,private)
        from ate_sim.persistence_lazy import open_lazy_world_session
        with open_lazy_world_session(private,rules_id=RULES) as session:
            if session.world.year!=2 or session.world.digest()!=result['control']['2']['digest']:
                raise AssertionError('downloaded restored World differs from independent control')
        if old.file_hash(retained)!=before:raise AssertionError('restore changed immutable input')
        (ROOT/'restore').mkdir()
        old._write_new(ROOT/'restore/restore.json',dict(passed=True,year=2,retained_original_unchanged=True))
        return
    if stage=='continue':
        previous=get('publish')
        result=p5.run(843000,[1,2],0,previous,RULES,head,os.environ['GITHUB_SHA'],
            complete_format=True,resume_from='complete')
        if not result['passed'] or not all(result['p4'][str(y)]['matches_control'] for y in (1,2)):
            raise AssertionError('continuation differs from independent control')
        (ROOT/'continue').mkdir()
        old._write_new(ROOT/'continue/result.json',result)
        shutil.copyfile(result['restore_artifact']['path'],ROOT/'continue/restore.sqlite')
        return
    expected=context()
    if stage=='prepare':
        source=get('source')
        m=construction.prepare(source/'p5-long-lazy.sqlite',source/'checkpoint.json',ROOT/'prepare',
            rules_id=RULES,context=expected)
        print(json.dumps(dict(prepared_files=m['files'],stream_rows={k:v['count'] for k,v in m['streams'].items()})),flush=True)
        return
    if stage in ('interrupt','commit','orders'):
        prepared=get('prepare')
        if stage=='interrupt':
            before={p.name:old.file_hash(p) for p in prepared.iterdir()}
            original=old._open
            class Interrupted(Exception):pass
            def opening(*args):
                store=original(*args)
                if '.construction-' in str(store.path):
                    def fault(phase):
                        if phase=='during_version_writes':raise Interrupted()
                    store._phase_hook=fault
                return store
            old._open=opening
            try:
                try:construction.commit_prepared(prepared,ROOT/'must-not-exist',context=expected)
                except Interrupted:pass
                else:raise AssertionError('real construction commit was not interrupted')
            finally:old._open=original
            if (ROOT/'must-not-exist').exists() or not _unchanged(prepared,before):
                raise AssertionError('interrupted construction damaged retained preparation')
            (ROOT/'interrupt').mkdir()
            old._write_new(ROOT/'interrupt/interrupted.json',dict(passed=True,
                prepared_manifest_sha256=old.file_hash(prepared/'manifest.json'),prepared_unchanged=True))
        elif stage=='commit':
            interrupted=old._json(get('interrupt')/'interrupted.json')
            if interrupted!=dict(passed=True,prepared_manifest_sha256=old.file_hash(prepared/'manifest.json'),prepared_unchanged=True):
                raise ValueError('interruption proof/preparation mismatch')
            construction.commit_prepared(prepared,ROOT/'commit',context=expected)
        else:
            committed=get('commit')
            construction.restore_orders(prepared,committed,ROOT/'orders',context=expected)
        return
    candidate=get('orders')
    if stage=='storage':
        (ROOT/'storage').mkdir()
        old.verify_storage(candidate,ROOT/'storage/storage.json',context=expected)
        return
    storage=get('storage')/'storage.json'
    if stage=='catalog':
        (ROOT/'catalog').mkdir()
        old.verify_catalog(candidate,storage,ROOT/'catalog/catalog.json',context=expected)
    elif stage=='publish':
        catalog=get('catalog')/'catalog.json';source=get('source')
        old.publish_p5(candidate,storage,catalog,source,context=expected,workflow_sha=os.environ['GITHUB_SHA'])
        (ROOT/'publish').mkdir()
        for name in MEMBERS['publish']:shutil.copyfile(source/name,ROOT/'publish'/name)
    else:raise ValueError('unknown construction proof stage')


def main(stage):
    with measure(stage):execute(stage)


if __name__=='__main__':main(sys.argv[1])
