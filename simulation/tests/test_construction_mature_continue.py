"""Exact continuation must reuse saved controls and preserve all retained inputs."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from simulation import complete_upgrade_checkpoint as old
from simulation.tests.test_construction_checkpoint import hashes
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_continue'), 'mature continuation wiring missing'
    return importlib.import_module('simulation.construction_mature_continue')


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    import persistence_p5_long_validation as p5
    from simulation.construction_checkpoint_ci import fixture_world
    root=tmp_path_factory.mktemp('continuation-fixture'); source=root/'source'
    original=p5.generate_world
    p5.generate_world=lambda seed, **kw: fixture_world(original, seed, width=6, height=6, settlements=1, **kw)
    try:
        p5.run(843000,[1,2],0,source,RULES,'c'*40,'d'*40,complete_format=True,stop_after='lazy')
    finally: p5.generate_world=original
    candidate=root/'candidate'; storage=root/'storage.json'; catalog=root/'catalog.json'
    manifest=old.capture(source/'p5-long-lazy.sqlite',source/'checkpoint.json',candidate,rules_id=RULES,context=CONTEXT)
    old.verify_storage(candidate,storage,context=CONTEXT)
    old.verify_catalog(candidate,storage,catalog,context=CONTEXT)
    prior=old._json(source/'checkpoint.json')
    old.publish_p5(candidate,storage,catalog,source,context=CONTEXT,workflow_sha='e'*40)
    published=root/'published'; published.mkdir()
    for name in ('checkpoint.json','p5-long-complete.sqlite'): shutil.copyfile(source/name,published/name)
    return root, manifest, prior


def fixture(tmp_path, monkeypatch, template):
    m=module(); root, manifest, prior=template
    published=tmp_path/'published'; shutil.copytree(root/'published',published)
    diagnostics=tmp_path/'diagnostics'; diagnostics.mkdir()
    for name in ('storage.json','catalog.json'): shutil.copyfile(root/name,tmp_path/name)
    receipt=old._json(published/'checkpoint.json')
    files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in published.iterdir()}
    summary=dict(stage='complete-published',context=CONTEXT,runtime_sha=CONTEXT['runtime_sha'],
        execution_workflow_sha='e'*40,execution_harness_sha='f'*40,files=files,receipt=receipt,
        inputs=copy.deepcopy(m.PUBLISH_INPUTS))
    old._write_new(diagnostics/'publish-summary.json',summary)
    (diagnostics/'publish.log').write_text('saved publication')
    (diagnostics/'disk-start.txt').write_text('117GiB')
    for key,value in dict(CONTEXT=CONTEXT,RUNTIME_SHA=CONTEXT['runtime_sha'],
        SOURCE_CONFIG=prior['config'],PUBLISHED_WORKFLOW_SHA='e'*40,PUBLISHED_HARNESS_SHA='f'*40,
        PUBLISHED_FILES=files,SUMMARY_SHA=sha(diagnostics/'publish-summary.json'),
        SUMMARY_BYTES=(diagnostics/'publish-summary.json').stat().st_size,
        SOURCE_CHECKPOINT=receipt['source_checkpoint'],CANDIDATE_PIN=manifest['pin'],
        SOURCE_GENERATION=manifest['source_generation'],CANDIDATE_DATABASE=manifest['database'],
        CANDIDATE_MANIFEST_SHA=sha(root/'candidate/manifest.json'),
        STORAGE_RECEIPT_SHA=sha(tmp_path/'storage.json'),STORAGE_RECEIPT_BYTES=(tmp_path/'storage.json').stat().st_size,
        CATALOG_RECEIPT_SHA=sha(tmp_path/'catalog.json'),CATALOG_RECEIPT_BYTES=(tmp_path/'catalog.json').stat().st_size).items():
        monkeypatch.setattr(m,key,value)
    return m,published,diagnostics,tmp_path/'storage.json',tmp_path/'catalog.json'


def forbidden(*args, **kwargs): raise AssertionError('continuation repeated successful earlier work')


def run(args, output): return args[0].run_continue(*args[1:],output,workflow_sha='9'*40)


def test_real_continuation_proves_exact_both_milestones_and_retained_restore(tmp_path,monkeypatch,template):
    import persistence_p5_long_validation as p5
    from ate_sim.persistence_lazy import open_lazy_world_session
    from ate_sim import persistence_complete_format as complete
    from simulation import construction_checkpoint as construction
    args=fixture(tmp_path,monkeypatch,template); m,published,diagnostics,storage,catalog=args
    before=hashes(published),hashes(diagnostics),sha(storage),sha(catalog)
    for name in ('capture','verify_storage','verify_catalog','publish_p5'): monkeypatch.setattr(old,name,forbidden)
    for name in ('prepare','commit_prepared','restore_orders'): monkeypatch.setattr(construction,name,forbidden)
    monkeypatch.setattr(complete,'upgrade_lazy_snapshot',forbidden)
    monkeypatch.setattr(p5,'generate_world',forbidden); monkeypatch.setattr(p5,'_control',forbidden)
    output=tmp_path/'continued'; result=run(args,output)
    assert set(hashes(output))=={'checkpoint.json','result.json','restore.sqlite'}
    assert result==old._json(output/'result.json') and result['passed'] is True
    receipt=old._json(published/'checkpoint.json')
    assert result['control']==receipt['state']['controls']
    assert result['workflow_sha']=='9'*40 and result['product_sha']==m.EXECUTION_RUNTIME_SHA
    assert result['source_checkpoint']['receipt_sha256']==sha(published/'checkpoint.json')
    for year in ('1','2'):
        assert result['p4'][year]['matches_control'] is True
        assert result['p4'][year]['reopen_digest']==receipt['state']['controls'][year]['digest']
    assert result['restore_artifact']['path']=='restore.sqlite' and result['restore_artifact']['year']==2
    assert result['restore_artifact']['sha256']==sha(output/'restore.sqlite')
    assert (output/'checkpoint.json').read_bytes()==(published/'checkpoint.json').read_bytes()
    assert (hashes(published),hashes(diagnostics),sha(storage),sha(catalog))==before
    retained=hashes(output); disposable=tmp_path/'restored.sqlite'; shutil.copyfile(output/'restore.sqlite',disposable)
    with open_lazy_world_session(disposable,rules_id=RULES) as session:
        assert session.world.year==2 and session.world.digest()==result['control']['2']['digest']
        assert p5._counters(session.world)==result['control']['2']['counters']
        assert session.world.skills.skills[1,'craft'].provenance is session.world.skills.skills[2,'craft'].provenance
    assert hashes(output)==retained
    with pytest.raises(FileExistsError): run(args,output)


@pytest.mark.parametrize('which',['database','checkpoint','summary','storage','catalog'])
def test_uninspected_bytes_reject_before_continuation(tmp_path,monkeypatch,template,which):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args
    path=dict(database=p/'p5-long-complete.sqlite',checkpoint=p/'checkpoint.json',
        summary=d/'publish-summary.json',storage=s,catalog=c)[which]
    with path.open('ab') as stream: stream.write(b'foreign')
    monkeypatch.setattr(m.p5,'run',forbidden)
    with pytest.raises(ValueError): run(args,tmp_path/'continued')
    assert not (tmp_path/'continued').exists()


@pytest.mark.parametrize('field',['schema','stage','config','workflow_sha','source_checkpoint','state','database'])
def test_refreshed_checkpoint_hash_cannot_excuse_foreign_normal_authority(tmp_path,monkeypatch,template,field):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args
    value=old._json(p/'checkpoint.json'); value[field]=True if field=='schema' else 'foreign'
    (p/'checkpoint.json').write_text(json.dumps(value))
    monkeypatch.setattr(m,'PUBLISHED_FILES',dict(m.PUBLISHED_FILES,**{'checkpoint.json':dict(bytes=(p/'checkpoint.json').stat().st_size,sha256=sha(p/'checkpoint.json'))}))
    monkeypatch.setattr(m.p5,'run',forbidden)
    with pytest.raises(ValueError): run(args,tmp_path/'continued')


@pytest.mark.parametrize('which',['storage','catalog'])
def test_refreshed_verifier_receipt_hash_does_not_excuse_wrong_chain(tmp_path,monkeypatch,template,which):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args
    path=s if which=='storage' else c; value=old._json(path); value['previous_receipt_sha256']='foreign'
    path.write_text(json.dumps(value)); monkeypatch.setattr(m,which.upper()+'_RECEIPT_SHA',sha(path))
    monkeypatch.setattr(m,which.upper()+'_RECEIPT_BYTES',path.stat().st_size)
    monkeypatch.setattr(m.p5,'run',forbidden)
    with pytest.raises(ValueError): run(args,tmp_path/'continued')


@pytest.mark.parametrize('field',['passed','control','source_checkpoint','workflow_sha','milestone','restore_digest'])
def test_wrong_continuation_result_cannot_be_retained(tmp_path,monkeypatch,template,field):
    args=fixture(tmp_path,monkeypatch,template); m=args[0]; original=m.p5.run
    def changed(*a,**kw):
        result=original(*a,**kw)
        if field=='milestone': result['p4']['2']['matches_control']=False
        elif field=='restore_digest': result['restore_artifact']['sha256']='0'*64
        else: result[field]=False if field=='passed' else 'foreign'
        return result
    monkeypatch.setattr(m.p5,'run',changed)
    with pytest.raises(ValueError): run(args,tmp_path/'continued')
    assert not (tmp_path/'continued').exists()


@pytest.mark.parametrize('fault',['interrupted','receipt_write','oversized','publication_race'])
def test_failed_continuation_preserves_all_retained_inputs(tmp_path,monkeypatch,template,fault):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args
    before=hashes(p),hashes(d),sha(s),sha(c)
    if fault=='interrupted':
        def fail(*a,**kw): raise RuntimeError('interrupted')
        monkeypatch.setattr(m.p5.Simulation,'run',fail)
    elif fault=='receipt_write':
        def fail(*a,**kw): raise OSError('receipt write')
        monkeypatch.setattr(old,'_write_new',fail)
    elif fault=='oversized': monkeypatch.setattr(m,'OUTPUT_MAX_BYTES',1)
    else:
        original=m.os.link
        def fail(source,destination):
            if Path(destination).name=='restore.sqlite': raise FileExistsError('publication race')
            return original(source,destination)
        monkeypatch.setattr(m.os,'link',fail)
    with pytest.raises((RuntimeError,OSError,ValueError)): run(args,tmp_path/'continued')
    assert not (tmp_path/'continued').exists()
    assert (hashes(p),hashes(d),sha(s),sha(c))==before


def test_changed_prerequisite_during_continuation_cannot_advance(tmp_path,monkeypatch,template):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args; original=m.p5.run
    def changed(*a,**kw):
        result=original(*a,**kw); s.write_text('{}'); return result
    monkeypatch.setattr(m.p5,'run',changed)
    with pytest.raises(ValueError,match='retained prerequisite'): run(args,tmp_path/'continued')
    assert not (tmp_path/'continued').exists()


def test_broken_stdout_does_not_strand_completed_continuation(tmp_path,monkeypatch,template):
    args=fixture(tmp_path,monkeypatch,template)
    class Broken:
        def write(self,value): raise OSError('diagnostic stdout')
        def flush(self): raise OSError('diagnostic stdout')
    with monkeypatch.context() as patch:
        patch.setattr(args[0].sys,'stdout',Broken()); result=run(args,tmp_path/'continued')
    assert result['passed'] is True


@pytest.mark.parametrize('condition',['first','duplicate','rerun','workflow','branch','head'])
def test_continue_launch_guard(monkeypatch,condition):
    m=module(); monkeypatch.setenv('GITHUB_RUN_ID','23'); monkeypatch.setenv('GITHUB_SHA','a'*40)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2' if condition=='rerun' else '1')
    current=dict(id=23,head_sha='a'*40,path=m.WORKFLOW,head_branch=m.BRANCH)
    if condition=='workflow': current['path']='foreign.yml'
    if condition=='branch': current['head_branch']='foreign'
    if condition=='head': current['head_sha']='b'*40
    rows=[current]+([dict(current,id=22)] if condition=='duplicate' else [])
    monkeypatch.setattr(m.artifacts,'_api',lambda *a:current)
    monkeypatch.setattr(m.artifacts,'_pages',lambda *a:rows)
    if condition=='first': m.unique_launch()
    else:
        with pytest.raises(ValueError): m.unique_launch()


@pytest.mark.parametrize('wrong_size',[False,True])
def test_download_pins_exact_published_diagnostics_and_receipt_producers(tmp_path,monkeypatch,wrong_size):
    m=module(); monkeypatch.setattr(m,'ROOT',tmp_path)
    expected=dict(published=(38907665230,12049884660,'construction-mature-published','mature-publish',
        '5fe99ca2faf0c0668ff73032fe9cc33fd1d6e9a9','.github/workflows/stage-0-5-mature-publish.yml',
        '5ea709166d2bba7f7a22d614fed604f471973ae9ff757979a4148ff197c43382',3910109453,{'checkpoint.json','p5-long-complete.sqlite'}),
        diagnostics=(38907665230,12050152952,'construction-mature-publish-diagnostics','mature-publish',
        '5fe99ca2faf0c0668ff73032fe9cc33fd1d6e9a9','.github/workflows/stage-0-5-mature-publish.yml',
        '58e4d2584cdbcaffa8ee31e9173473c46d07d60b202e4d8d0e319ac2da597823',19421,{'publish-summary.json','publish.log','disk-start.txt'}),
        storage=(38872643738,12037828504,'construction-mature-storage','mature-storage',
        '4f1a7d7f0bd6c90704b5370f5e508669afe3b00f','.github/workflows/stage-0-5-mature-storage.yml',
        '7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4',554,{'storage.json'}),
        catalog=(38884880079,12043567528,'construction-mature-catalog','mature-catalog',
        'ee5000a156ebcf1fcec4a893da1a06958feb0ed5','.github/workflows/stage-0-5-mature-catalog.yml',
        '854c941a708c3aa7abd8a85836369c4a209e089496d6b82906afe30f9a9b1bbd',585,{'catalog.json'}))
    seen=[]
    def download(destination,**kw):
        label=Path(destination).name; r=expected[label]; seen.append(label)
        assert kw==dict(run_id=r[0],artifact_id=r[1],name=r[2],job=r[3],workflow_sha=r[4],
            workflow_path=r[5],expected_digest=r[6],members=r[8])
        return dict(artifact_id=r[1],archive_bytes=r[7]-int(wrong_size))
    monkeypatch.setattr(m.artifacts,'download',download)
    if wrong_size:
        with pytest.raises(ValueError,match='archive size'): m.download_inputs()
    else:
        directories,proofs=m.download_inputs(); assert set(seen)==set(directories)==set(proofs)==set(expected)


def main_environment(m,monkeypatch):
    monkeypatch.setenv('HARNESS_SHA','f'*40); monkeypatch.setenv('RUNTIME_SHA',m.EXECUTION_RUNTIME_SHA)
    monkeypatch.setenv('GITHUB_SHA','9'*40)
    monkeypatch.setattr(m.subprocess,'check_output',lambda args,**kw:'f'*40 if args[-1]=='HEAD' else m.EXECUTION_RUNTIME_TREE)
    monkeypatch.setattr(m.resource,'setrlimit',lambda *a:None)
    monkeypatch.setattr(m,'check_helpers',lambda:None); monkeypatch.setattr(m,'unique_launch',lambda:None)


def test_fixed_runtime_preserves_original_checkpoint_and_control_provenance(tmp_path,monkeypatch,template):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args
    monkeypatch.setattr(m,'EXECUTION_RUNTIME_SHA','8'*40,raising=False)
    before=hashes(p),hashes(d),sha(s),sha(c)
    original=m.p5.run
    def checked(*a,**kw):
        assert a[5]=='8'*40
        assert kw.get('checkpoint_product_sha')==m.RUNTIME_SHA
        return original(*a,**kw)
    monkeypatch.setattr(m.p5,'run',checked)
    result=run(args,tmp_path/'continued')
    assert result['product_sha']=='8'*40
    assert result['checkpoint_product_sha']==m.RUNTIME_SHA
    assert result['source_checkpoint']['product_sha']==m.RUNTIME_SHA
    assert result['control']==old._json(p/'checkpoint.json')['state']['controls']
    assert (hashes(p),hashes(d),sha(s),sha(c))==before


@pytest.mark.parametrize('where',['before','after'])
def test_headroom_rejects_before_any_continuation_mutation(tmp_path,monkeypatch,where):
    m=module(); monkeypatch.setattr(m,'ROOT',tmp_path/'evidence'); main_environment(m,monkeypatch)
    assert m.START_FREE_BYTES>=118550874381 and m.WORK_FREE_BYTES>=84972371968
    values=iter([m.START_FREE_BYTES-int(where=='before'),m.WORK_FREE_BYTES-1])
    monkeypatch.setattr(m.shutil,'disk_usage',lambda *a:SimpleNamespace(free=next(values)))
    def download():
        if where=='before': pytest.fail('downloads before headroom')
        return {n:tmp_path/n for n in ('published','diagnostics','storage','catalog')},{}
    monkeypatch.setattr(m,'download_inputs',download); monkeypatch.setattr(m,'run_continue',forbidden)
    with pytest.raises(ValueError,match='disk headroom'): m.main()


def test_post_boundary_summary_failure_cannot_suppress_output(tmp_path,monkeypatch,template):
    args=fixture(tmp_path,monkeypatch,template); m,p,d,s,c=args
    for path in (s,c):
        directory=tmp_path/path.stem; directory.mkdir(); shutil.copyfile(path,directory/path.name)
    root=tmp_path/'evidence'; monkeypatch.setattr(m,'ROOT',root); main_environment(m,monkeypatch)
    monkeypatch.setattr(m.shutil,'disk_usage',lambda *a:SimpleNamespace(free=m.START_FREE_BYTES))
    monkeypatch.setattr(m,'download_inputs',lambda: (dict(published=p,diagnostics=d,storage=tmp_path/'storage',catalog=tmp_path/'catalog'),{}))
    original=old._write_new
    def failed(path,value):
        if Path(path).name=='continue-summary.json': raise OSError('diagnostic summary')
        return original(path,value)
    monkeypatch.setattr(old,'_write_new',failed); m.main()
    assert old._json(root/'continued/result.json')['passed'] is True


@pytest.mark.parametrize('status',[0,7,124])
def test_workflow_continuation_only_preserves_real_command_exit_and_mandatory_upload(status):
    import subprocess,yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-continue.yml'
    assert path.exists(), 'mature continuation workflow missing'
    workflow=yaml.safe_load(path.read_text()); assert set(workflow['jobs'])=={'mature-continue'}
    assert workflow['concurrency']['cancel-in-progress'] is False
    job=workflow['jobs']['mature-continue']; assert job['timeout-minutes']==360
    script=next(s['run'] for s in job['steps'] if s.get('name')=='Continue exact mature checkpoint')
    assert '300m python -m simulation.construction_mature_continue' in script
    script=script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_continue',f"bash -c 'exit {status}'")
    script=script.replace('tee evidence/continue.log',"bash -c 'cat >/dev/null; exit 42'")
    assert subprocess.run(['bash','-e','-o','pipefail','-c',script],capture_output=True).returncode==status
    diagnostic=next(s for s in job['steps'] if s.get('name')=='Retain diagnostics')
    assert diagnostic['if']=='always()' and diagnostic['continue-on-error'] is True
    upload=next(s for s in job['steps'] if s.get('name')=='Retain continued checkpoint')
    assert 'if' not in upload and upload['with']['path']=='evidence/continued'
    assert upload['with']['name']=='construction-mature-continued' and upload['with']['if-no-files-found']=='error'


def test_disposable_cleanup_preserves_python_and_actions_runtime(tmp_path):
    import subprocess,yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-continue.yml'
    assert path.exists(), 'mature continuation workflow missing'
    w=yaml.safe_load(path.read_text()); script=next(s['run'] for s in w['jobs']['mature-continue']['steps']
        if s.get('name')=='Reserve disk on this disposable runner')
    locations={'/usr/share/dotnet':'dotnet','/usr/local/lib/android':'android','/opt/ghc':'ghc',
        '/usr/share/swift':'swift','/usr/local/.ghcup':'ghcup','/usr/local/share/powershell':'powershell','/opt/hostedtoolcache':'toolcache'}
    for original,label in locations.items():
        (tmp_path/label).mkdir(); script=script.replace(original,str(tmp_path/label))
    for name in ('Python','CodeQL','node'): (tmp_path/'toolcache'/name).mkdir()
    actions=tmp_path/'actions-runtime'; actions.write_bytes(b'preserved')
    script=script.replace('sudo ',''); docker="docker() { test \"$*\" = 'image prune -af'; touch docker-pruned; }\n"
    subprocess.run(['bash','-e','-o','pipefail','-c',docker+script],cwd=tmp_path,check=True,capture_output=True)
    assert {p.name for p in (tmp_path/'toolcache').iterdir()}=={'Python'}
    assert actions.read_bytes()==b'preserved' and (tmp_path/'docker-pruned').exists()
    assert all(not (tmp_path/label).exists() for label in locations.values() if label!='toolcache')
