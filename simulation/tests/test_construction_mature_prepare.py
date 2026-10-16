"""Mature wiring must save sealed inputs before the original target commit."""
import importlib
import importlib.util
import json
from pathlib import Path
import pytest
from simulation.tests.test_construction_checkpoint import inputs
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_prepare'), 'mature preparation wiring missing'
    return importlib.import_module('simulation.construction_mature_prepare')


def test_mature_prepare_stops_before_commit_and_retains_replayable_inputs(tmp_path,monkeypatch):
    from ate_sim import persistence_catalog_copy as copy
    source,receipt=inputs(tmp_path);before=sha(source)
    original=copy.LazyRecordStore.commit
    def forbid(store,*args,**kwargs):
        assert store.path.name!='destination.sqlite','mature preparation reached target commit'
        return original(store,*args,**kwargs)
    monkeypatch.setattr(copy.LazyRecordStore,'commit',forbid)
    m=module();manifest=m.run_prepare(source,receipt,tmp_path/'prepared',rules_id=RULES,context=CONTEXT)
    assert manifest['stage']=='prepared' and sha(source)==before
    assert {p.name for p in (tmp_path/'prepared').iterdir()}=={'target.sqlite','spool.sqlite','manifest.json'}


@pytest.mark.parametrize('condition',['run-failed','foreign-commit','wrong-workflow','missing-job','restore-failed'])
def test_mature_proof_gate_rejects_unproven_candidate(tmp_path,monkeypatch,condition):
    m=module();monkeypatch.setattr(m,'ROOT',tmp_path)
    run={'conclusion':'failure' if condition=='run-failed' else 'success',
        'head_sha':'foreign' if condition=='foreign-commit' else m.PROOF_WORKFLOW_SHA,
        'path':'foreign.yml' if condition=='wrong-workflow' else m.PROOF_WORKFLOW}
    names=set(m.PROOF_JOBS)
    if condition=='missing-job':names.remove('full-suite')
    monkeypatch.setattr(m.artifacts,'_api',lambda *a:run)
    monkeypatch.setattr(m.artifacts,'_pages',lambda *a:[dict(name=n,conclusion='success') for n in names])
    def download(destination,**kwargs):
        destination.mkdir()
        (destination/'restore.json').write_text(json.dumps(dict(passed=False,year=2,retained_original_unchanged=True)))
    monkeypatch.setattr(m.artifacts,'download',download)
    with pytest.raises(ValueError):m.proof_gate()


def test_mature_proof_gate_requires_pinned_artifact_and_exact_success(tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'ROOT',tmp_path)
    monkeypatch.setattr(m.artifacts,'_api',lambda *a:dict(conclusion='success',head_sha=m.PROOF_WORKFLOW_SHA,path=m.PROOF_WORKFLOW))
    monkeypatch.setattr(m.artifacts,'_pages',lambda *a:[dict(name=n,conclusion='success') for n in m.PROOF_JOBS])
    def download(destination,**kwargs):
        assert kwargs['run_id']==38819525026 and kwargs['artifact_id']==12011234609
        assert kwargs['expected_digest']=='22315f21ac3cf810e4d326b6d9d62e010cc5a6c96c3bc897a6d511ab2b626ebe'
        destination.mkdir();(destination/'restore.json').write_text(json.dumps(dict(passed=True,year=2,retained_original_unchanged=True)))
    monkeypatch.setattr(m.artifacts,'download',download)
    m.proof_gate()


def test_mature_prepare_workflow_runs_only_one_stage_with_upload_headroom():
    import yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-prepare.yml'
    assert path.exists(),'mature preparation workflow missing'
    text=path.read_text();d=yaml.safe_load(text)
    assert set(d['jobs'])=={'mature-prepare'}
    job=d['jobs']['mature-prepare'];assert job['timeout-minutes']==360
    run=next(s for s in job['steps'] if s.get('name')=='Prepare and save mature construction inputs')
    assert '300m python -m simulation.construction_mature_prepare' in run['run']
    assert 'commit_prepared' not in text and 'restore_orders' not in text
    assert d['concurrency']['cancel-in-progress'] is False
    upload=next(s for s in job['steps'] if s.get('name')=='Retain prepared construction')
    assert upload['with']['path']=='evidence/prepared' and 'if' not in upload
    diagnostics=next(s for s in job['steps'] if s.get('name')=='Retain diagnostics')
    assert diagnostics['if']=='always()' and diagnostics['continue-on-error'] is True


@pytest.mark.parametrize('older',[False,True])
def test_duplicate_push_cannot_start_a_second_expensive_preparation(monkeypatch,older):
    m=module();monkeypatch.setenv('GITHUB_RUN_ID','23');monkeypatch.setenv('GITHUB_SHA','a'*40)
    run=dict(head_sha='a'*40,path=m.WORKFLOW,head_branch=m.BRANCH)
    monkeypatch.setattr(m.artifacts,'_api',lambda *a:run)
    rows=[dict(run,id=23)]
    if older:rows.append(dict(run,id=22,status='completed',conclusion='success'))
    monkeypatch.setattr(m.artifacts,'_pages',lambda *a:rows)
    if older:
        with pytest.raises(ValueError,match='duplicate'):m.unique_launch()
    else:m.unique_launch()


def test_rerunning_same_workflow_requires_inspection_before_reconstruction(monkeypatch):
    m=module();monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    monkeypatch.setenv('GITHUB_RUN_ID','23');monkeypatch.setenv('GITHUB_SHA','a'*40)
    run=dict(head_sha='a'*40,path=m.WORKFLOW,head_branch=m.BRANCH)
    monkeypatch.setattr(m.artifacts,'_api',lambda *a:run)
    monkeypatch.setattr(m.artifacts,'_pages',lambda *a:[dict(run,id=23)])
    with pytest.raises(ValueError,match='rerun'):m.unique_launch()


@pytest.mark.parametrize('failure',['summary','stdout'])
def test_post_boundary_diagnostics_cannot_strand_completed_preparation(tmp_path,monkeypatch,failure):
    from types import SimpleNamespace
    from simulation import construction_checkpoint as core
    m=module();root=tmp_path/'evidence';monkeypatch.setattr(m,'ROOT',root)
    source,receipt=inputs(tmp_path)
    monkeypatch.setenv('HARNESS_SHA','a'*40);monkeypatch.setenv('RUNTIME_SHA',m.RUNTIME_SHA)
    monkeypatch.setattr(m.subprocess,'check_output',lambda args,**kw:'a'*40 if args[-1]=='HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource,'setrlimit',lambda *a:None)
    monkeypatch.setattr(m.shutil,'disk_usage',lambda *a:SimpleNamespace(free=100*1024**3))
    monkeypatch.setattr(m,'unique_launch',lambda:None);monkeypatch.setattr(m,'proof_gate',lambda:None)
    def download(destination,**kwargs):
        destination.mkdir();return dict(archive_bytes=1339563957)
    monkeypatch.setattr(m.artifacts,'download',download)
    monkeypatch.setattr(m.legacy,'check_source',lambda *a:None)
    def prepare(*args,**kwargs):
        return core.prepare(source,receipt,root/'prepared',rules_id=RULES,context=kwargs['context'])
    monkeypatch.setattr(m,'run_prepare',prepare)
    original=m.old._write_new
    def write(path,data):
        if Path(path).name=='prepare-summary.json':raise OSError('diagnostic disk error')
        return original(path,data)
    if failure=='summary':monkeypatch.setattr(m.old,'_write_new',write)
    else:monkeypatch.setattr(m,'print',lambda *a,**k:(_ for _ in ()).throw(OSError('stdout failed')),raising=False)
    m.main()
    manifest=m.old._json(root/'prepared/manifest.json')
    assert core.validate_prepared(root/'prepared',context=manifest['context'])['stage']=='prepared'


@pytest.mark.parametrize('status',[0,7,124])
def test_log_capture_failure_preserves_preparation_exit_status(status):
    import subprocess,yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-prepare.yml'
    job=yaml.safe_load(path.read_text())['jobs']['mature-prepare']
    script=next(s['run'] for s in job['steps'] if s.get('name')=='Prepare and save mature construction inputs')
    script=script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_prepare',f"bash -c 'exit {status}'")
    script=script.replace('tee evidence/prepare.log',"bash -c 'cat >/dev/null; exit 42'")
    result=subprocess.run(['bash','-e','-o','pipefail','-c',script],capture_output=True,text=True)
    assert result.returncode==status
