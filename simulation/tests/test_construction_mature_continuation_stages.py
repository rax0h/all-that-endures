"""Production launch and transport guards reject before expensive execution."""
from dataclasses import replace
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from simulation.tests.test_continuation_receipts import artifact


def module():
    assert importlib.util.find_spec('simulation.construction_mature_continuation_stages'), 'mature stage runner missing'
    return importlib.import_module('simulation.construction_mature_continuation_stages')


@pytest.mark.parametrize('stage,before,expected',[
    ('save',True,3400),('save',False,2400),('audit',True,3000),('digest',False,2000),
    ('restore-values',True,3000),('accept-year',True,0),
])
def test_disk_reservation_covers_phase_peak_and_fails_one_byte_below(stage,before,expected):
    m=module();required=m.required_space(stage,1000,40,1200,before=before)
    assert required==expected+8*1024**3+64*1024**2
    m.check_space(required,free=required)
    with pytest.raises(ValueError,match='headroom'):m.check_space(required,free=required-1)


def test_mature_authority_keeps_original_checkpoint_producer_separate():
    m=module();a=m.mature_authority()
    assert a.checkpoint_runtime_sha=='bbc3cbf11becb58aa4b9483114559fd1296878f1'
    assert a.execution_runtime_sha=='2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a'
    assert a.source_config['milestones']==(1001,1002)
    assert a.source_config['bootstrap_year']==1000


@pytest.mark.parametrize('status',['queued','in_progress','waiting','requested','pending'])
def test_active_continuation_on_another_sha_blocks_launch(monkeypatch,status):
    m=module();current=dict(id=20,head_sha='c'*40,path=m.WORKFLOW,head_branch=m.BRANCH,status='in_progress')
    other=dict(id=19,head_sha='d'*40,path=m.original.WORKFLOW,head_branch=m.original.BRANCH,status=status)
    monkeypatch.setenv('GITHUB_RUN_ID','20');monkeypatch.setenv('GITHUB_SHA','c'*40);monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(m.artifacts,'_api',lambda path:current)
    monkeypatch.setattr(m.artifacts,'_pages',lambda path,key:[current,other])
    with pytest.raises(ValueError,match='active'):m.unique_launch()


def test_same_sha_duplicate_and_rerun_cannot_launch(monkeypatch):
    m=module();current=dict(id=20,head_sha='c'*40,path=m.WORKFLOW,head_branch=m.BRANCH,status='in_progress')
    prior=dict(current,id=19,status='completed',conclusion='failure')
    monkeypatch.setenv('GITHUB_RUN_ID','20');monkeypatch.setenv('GITHUB_SHA','c'*40);monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(m.artifacts,'_api',lambda path:current)
    monkeypatch.setattr(m.artifacts,'_pages',lambda path,key:[current,prior])
    with pytest.raises(ValueError,match='duplicate'):m.unique_launch()
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    with pytest.raises(ValueError,match='rerun'):m.unique_launch()


def test_invalid_stage_and_unpinned_proof_reject_before_any_download(tmp_path,monkeypatch):
    m=module();path=tmp_path/'launch.json'
    base=dict(schema=m.LAUNCH_SCHEMA,stage='save',year=1001,inputs={},candidate_database=None,proof=None)
    path.write_text(json.dumps(base))
    with pytest.raises(ValueError,match='proof'):m.load_launch(path,stage='save',year=1001)
    base['stage']='unknown';path.write_text(json.dumps(base))
    with pytest.raises(ValueError):m.load_launch(path,stage='unknown',year=1001)


def test_foreign_input_runtime_rejects_before_transport(tmp_path):
    m=module();a=m.mature_authority()
    proof=replace(artifact(m.r),name='continuation-small-proof',producer_job='proof-summary',workflow_path=m.PROOF_WORKFLOW,
        runtime_sha=a.execution_runtime_sha,runtime_tree=a.execution_runtime_tree)
    path=tmp_path/'launch.json';path.write_text(json.dumps(dict(schema=m.LAUNCH_SCHEMA,
        stage='audit',year=1001,inputs={'candidate':artifact(m.r).to_dict()},candidate_database=None,proof=proof.to_dict())))
    with pytest.raises(ValueError,match='runtime'):m.load_launch(path,stage='audit',year=1001)


def test_declared_database_size_constrains_extraction_before_copy(tmp_path,monkeypatch):
    m=module();seen=[];a=m.mature_authority();ref=artifact(m.r)
    def download(reference,destination,*,members,database_cap):
        seen.append(database_cap)
    monkeypatch.setattr(m,'download_ref',download)
    m.fetch_stage_inputs('audit',1001,root=tmp_path,authority=a,refs={'candidate':ref},database_cap=128)
    assert seen==[128]


def test_upload_rechecks_full_saved_database_allowance():
    m=module()
    assert m.upload_space('save',{'database':{'bytes':200}})==200+8*1024**3+64*1024**2
    assert m.upload_space('audit',{})==8*1024**3+64*1024**2


def test_proof_fingerprint_covers_the_actual_current_state_audit_helper(monkeypatch):
    m=module();repo=Path(__file__).resolve().parents[2]
    helper=str(Path(m.checkpoint.p5.current_audit.__code__.co_filename).resolve().relative_to(repo))
    before=m.implementation_hashes();actual=m.r.file_hash
    monkeypatch.setattr(m.r,'file_hash',lambda path:'0'*64 if str(path)==helper else actual(path))
    assert m.implementation_hashes()!=before


def test_failed_upload_producer_cannot_authenticate(monkeypatch):
    m=module();ref=artifact(m.r,name='saved1',identity=10)
    data=dict(id=10,name=ref.name,expired=False,size_in_bytes=100,digest='sha256:'+ref.archive_sha256,
        created_at='2026-10-17T00:01:00Z',workflow_run=dict(id=1,head_sha=ref.workflow_sha))
    run=dict(id=1,head_sha=ref.workflow_sha,path=ref.workflow_path,conclusion='failure')
    monkeypatch.setattr(m.artifacts,'_api',lambda path:data if '/artifacts/' in path else run)
    jobs=[dict(name=ref.producer_job,conclusion='failure',started_at='2026-10-17T00:00:00Z',completed_at='2026-10-17T00:02:00Z')]
    monkeypatch.setattr(m.artifacts,'_pages',lambda path,key:jobs)
    with pytest.raises(ValueError,match='producing job'):m.authenticate_ref(ref,max_archive_bytes=100)


@pytest.mark.parametrize('status',[1,124])
def test_workflow_preserves_failed_stage_exit_and_requires_upload(tmp_path,status):
    m=module();path=Path(__file__).resolve().parents[2]/m.WORKFLOW
    assert path.exists(),'mature stage workflow missing'
    w=yaml.safe_load(path.read_text());job=w['jobs']['mature-stage']
    assert job['timeout-minutes']==360
    step=next(s for s in job['steps'] if s.get('name')=='Execute one mature stage')
    script=step['run'];command='timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_continuation_stages'
    assert command in script
    # Keep the actual surrounding pipeline/exit handling; replace only expensive execution.
    lines=script.splitlines()
    lines=[f"bash -c 'exit {status}' 2>&1 | tee evidence/stage.log" if command in line else line for line in lines]
    result=subprocess.run(['bash','-c','\n'.join(lines)],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==status
    uploads=[s for s in job['steps'] if s.get('uses','').startswith('actions/upload-artifact')]
    required=next(s for s in uploads if s.get('name')=='Retain completed stage')
    assert required['with']['if-no-files-found']=='error' and not required.get('continue-on-error',False)
