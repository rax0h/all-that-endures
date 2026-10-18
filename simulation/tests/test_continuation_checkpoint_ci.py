"""The shared stage dispatcher and real ZIP boundary preserve protocol authority."""
import base64
from dataclasses import replace
import json
import importlib
import importlib.util
import hashlib
import os
import subprocess
import sys
import yaml
from pathlib import Path
import zipfile

import pytest

from simulation import continuation_receipts as r
from simulation.tests.test_construction_mature_continuation_stages import module
from simulation.tests.test_continuation_checkpoint import publication,forbidden
from simulation.tests.test_continuation_verifiers import saved_template
from simulation.tests.test_continuation_acceptance import verified_template
from simulation.tests.test_continuation_receipts import artifact,producer
from simulation.tests.test_continuation_restore import continuation_template


def test_receipt_only_dispatch_can_approve_without_download_or_world_open(tmp_path,verified_template,monkeypatch):
    m=module();source,a,saved,candidate,audit,digest,audit_ref,digest_ref=verified_template
    paths={}
    for label,row in (('audit',audit),('digest',digest)):
        paths[label]=tmp_path/label;paths[label].mkdir()
        r.publish_receipt(paths[label]/(label+'.json'),row)
    monkeypatch.setattr(m.checkpoint,'open_lazy_world_session',forbidden)
    result=m.execute_stage('accept-year',1,authority=a,inputs=paths,
        refs=dict(candidate=candidate,audit=audit_ref,digest=digest_ref),
        producer=producer('accept-year','accept1'),output=tmp_path/'output')
    assert result['stage']=='year-verified'
    assert (tmp_path/'output/year-verified.json').exists()


def test_launch_accepts_only_the_separate_completed_proof_summary(tmp_path):
    m=module();a=m.mature_authority()
    proof=replace(artifact(r),name='continuation-small-proof',producer_job='proof-summary',workflow_path=m.PROOF_WORKFLOW,
        runtime_sha=a.execution_runtime_sha,runtime_tree=a.execution_runtime_tree)
    path=tmp_path/'launch.json';path.write_text(json.dumps(dict(schema=m.LAUNCH_SCHEMA,
        stage='save',year=1001,inputs={},candidate_database=None,proof=proof.to_dict())))
    config,refs,actual=m.load_launch(path,stage='save',year=1001)
    assert actual==proof and refs=={}


def test_dispatch_rejects_wrong_actual_milestone_before_world_open(tmp_path,continuation_template,monkeypatch):
    m=module();saved,a,candidate,continued=continuation_template
    monkeypatch.setattr(m.checkpoint,'open_lazy_world_session',forbidden)
    with pytest.raises(ValueError):m.execute_stage('audit',1,authority=a,inputs={'candidate':saved},refs={'candidate':candidate},
        producer=producer('audit','audit1'),output=tmp_path/'wrong')


def test_restore_composition_cannot_replace_expected_original_authority(tmp_path,continuation_template):
    m=module();saved,a,candidate,continued=continuation_template
    values=m.checkpoint.restore_values(saved,tmp_path/'values/restore-values.json',authority=a,candidate=candidate,
        continuation=continued,producer=producer('restore-values','values'))
    digest=m.checkpoint.restore_digest(saved,tmp_path/'digest/restore-digest.json',authority=a,candidate=candidate,
        continuation=continued,producer=producer('restore-digest','restore-digest'))
    r.publish_receipt(tmp_path/'continuation/continuation-verified.json',continued)
    refs=dict(candidate=candidate,values=replace(candidate,artifact_id=31,name='values',producer_job='values'),
        digest=replace(candidate,artifact_id=32,name='restore-digest',producer_job='restore-digest'),
        continuation=replace(candidate,artifact_id=30,name='continued',producer_job='continued'))
    paths={key:tmp_path/key for key in ('values','digest','continuation')}
    wrong=replace(a,checkpoint_sha256='0'*64)
    with pytest.raises(ValueError):m.execute_stage('accept-restore',2,authority=wrong,inputs=paths,refs=refs,
        producer=producer('accept-restore','restored'),output=tmp_path/'wrong')
    assert not (tmp_path/'wrong/restore-verified.json').exists()


def test_serial_extract_limit_rejects_before_output_and_restores_original_callable(tmp_path):
    m=module();archive=tmp_path/'artifact.zip'
    with zipfile.ZipFile(archive,'w') as stream:
        stream.writestr('candidate.sqlite',b'x'*201)
        stream.writestr('checkpoint.json','{}');stream.writestr('save.json','{}')
    original=m.artifacts.extract
    with pytest.raises(ValueError,match='extraction bound'):
        with m.bounded_extraction(200):
            m.artifacts.extract(archive,tmp_path/'out',r.SAVED_MEMBERS)
    assert m.artifacts.extract is original and not (tmp_path/'out').exists()


def test_archive_cap_rejects_before_network(monkeypatch):
    m=module();ref=artifact(r)
    monkeypatch.setattr(m.artifacts,'_api',forbidden)
    with pytest.raises(ValueError,match='cap'):m.authenticate_ref(ref,max_archive_bytes=ref.archive_bytes-1)


@pytest.mark.parametrize('foreign_tree',[False,True])
def test_authentication_uses_successful_producer_and_checked_source_pins(monkeypatch,foreign_tree):
    m=module();ref=artifact(r);m._SOURCE_IDENTITIES.clear()
    metadata=dict(id=ref.artifact_id,name=ref.name,expired=False,size_in_bytes=ref.archive_bytes,
        digest='sha256:'+ref.archive_sha256,created_at='2026-10-17T00:01:00Z',
        workflow_run=dict(id=ref.run_id,head_sha=ref.workflow_sha))
    run=dict(id=ref.run_id,head_sha=ref.workflow_sha,path=ref.workflow_path,conclusion='failure')
    workflow=dict(env=dict(HARNESS_SHA=ref.harness_sha,RUNTIME_SHA=ref.runtime_sha))
    def api(path):
        if path.startswith('/actions/artifacts/'):return metadata
        if path.startswith('/actions/runs/'):return run
        if path.startswith('/contents/'):return dict(encoding='base64',content=base64.b64encode(json.dumps(workflow).encode()).decode())
        if path.startswith('/git/trees/'):return dict(truncated=False,tree=[dict(path='simulation/ate_sim',type='tree',sha='9'*40 if foreign_tree else ref.runtime_tree)])
        raise AssertionError(path)
    monkeypatch.setattr(m.artifacts,'_api',api)
    monkeypatch.setattr(m.artifacts,'_pages',lambda path,key:[dict(name=ref.producer_job,conclusion='success',
        started_at='2026-10-17T00:00:00Z',completed_at='2026-10-17T00:02:00Z')])
    if foreign_tree:
        with pytest.raises(ValueError,match='subtree'):m.authenticate_ref(ref,max_archive_bytes=ref.archive_bytes)
    else:
        assert m.authenticate_ref(ref,max_archive_bytes=ref.archive_bytes)['id']==ref.artifact_id


def ci_module():
    assert importlib.util.find_spec('simulation.continuation_checkpoint_ci'), 'fresh-runner proof entry point missing'
    return importlib.import_module('simulation.continuation_checkpoint_ci')


def test_ci_rejects_a_mature_role_before_source_or_network(monkeypatch):
    m=ci_module();monkeypatch.setattr(m.runner,'check_source',forbidden)
    with pytest.raises(SystemExit) as error:m.main(['--job','mature'])
    assert error.value.code==2


def test_ci_source_has_populated_controls_for_only_two_bounded_years(tmp_path,monkeypatch):
    m=ci_module();monkeypatch.setenv('RUNTIME_SHA','b'*40);monkeypatch.setenv('HARNESS_SHA','e'*40);monkeypatch.setenv('GITHUB_SHA','c'*40)
    source=m.build_source(tmp_path/'source')
    assert {p.name for p in source.iterdir()}=={'checkpoint.json','p5-long-complete.sqlite','fixture.json'}
    row=r.load_receipt(source/'checkpoint.json')
    assert row['config']['milestones']==[1,2] and row['config']['bootstrap_year']==0
    assert row['state']['controls']['1']['audit']['snapshot']['magic_access']['treasuries']


def test_proof_workflow_orders_retry_and_captures_real_command_failure(tmp_path):
    m=module();path=Path(__file__).resolve().parents[2]/m.PROOF_WORKFLOW
    assert path.exists(),'separate-runner proof workflow missing'
    workflow=yaml.safe_load(path.read_text());jobs=workflow['jobs']
    assert jobs['audit1']['needs']==['interrupt-audit1']
    assert jobs['save2']['needs']==['accept1']
    assert set(jobs['proof-summary']['needs'])=={'restored','full-suite'}
    step=next(s for s in jobs['audit1']['steps'] if s.get('name')=='Execute bounded stage')
    lines=["bash -c 'exit 1' 2>&1 | tee evidence/audit1.log" if 'python -m simulation.continuation_checkpoint_ci' in line else line
        for line in step['run'].splitlines()]
    result=subprocess.run(['bash','-c','\n'.join(lines)],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==1
    assert workflow['env']['HARNESS_SHA']=='${{ github.sha }}'


def test_real_zip_transport_two_year_pipeline_uses_fresh_processes(tmp_path):
    probe=Path(__file__).with_name('continuation_transport_probe.py')
    assert probe.exists(),'fresh-process transport probe missing'
    repo=Path(__file__).resolve().parents[2]
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    workflow=(repo/module().PROOF_WORKFLOW).read_text()
    state=dict(head=head,workflow=workflow,artifacts=[],jobs=[],archives={})
    roles=['source','save1','interrupt-audit1','audit1','digest1','accept1','save2',
        'audit2','digest2','accept2','continued','restore-values','restore-digest','restored','proof-summary']
    env=dict(os.environ,PYTHONPATH='simulation:.',GH_TOKEN='bounded-test-token',HARNESS_SHA=head,
        GITHUB_SHA=head,RUNTIME_SHA='2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a',GITHUB_RUN_ID='500',GITHUB_RUN_ATTEMPT='1')
    for index,role in enumerate(roles):
        path=tmp_path/'network.json';path.write_text(json.dumps(state))
        result=subprocess.run([sys.executable,str(probe),str(path),role,str(tmp_path/role)],
            cwd=repo,env=env,capture_output=True,text=True,timeout=120)
        assert result.returncode==0,role+'\n'+result.stdout[-4000:]+'\n'+result.stderr
        output=tmp_path/role/role/'output'
        assert output.is_dir(),role
        archive=tmp_path/(role+'.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as stream:
            for file in output.iterdir():stream.write(file,file.name)
        identity=1000+index
        name='continuation-small-'+('proof' if role=='proof-summary' else role)
        state['artifacts'].append(dict(id=identity,name=name,expired=False,size_in_bytes=archive.stat().st_size,
            digest='sha256:'+hashlib.sha256(archive.read_bytes()).hexdigest(),created_at='2026-10-18T12:00:00Z',
            workflow_run=dict(id=500,head_sha=head)))
        state['jobs'].append(dict(name=role,conclusion='success',started_at='2026-10-18T00:00:00Z',completed_at='2026-10-18T23:59:59Z'))
        state['archives'][str(identity)]=str(archive)
    final=r.load_receipt(tmp_path/'restored/restored/output/restore-verified.json')
    assert final['binding']['year']==2 and final['stage_0_5_accepted'] is False
    assert final['values']['observation']['snapshot']['magic_access']['treasuries']
    features=r.load_receipt(tmp_path/'restore-values/restore-values/fixture-check.json')
    assert features['year']==2 and features['shared_nested_identity'] is True and features['counted_histories']>0
