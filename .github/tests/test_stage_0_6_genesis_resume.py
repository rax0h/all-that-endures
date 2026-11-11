import copy
import importlib
import importlib.util
import pytest


def api():
    name='simulation.stage_0_6_genesis_resume'
    assert importlib.util.find_spec(name) is not None,'safe checkpoint resume/green reuse launcher is missing'
    return importlib.import_module(name)


def green():
    m=api()
    run=dict(id=m.GREEN_RUN,head_sha=m.GREEN_SHA,head_branch='sol/durable-proof-map',
        path='.github/workflows/stage-0-5-proof-map-validation.yml',event='push',run_attempt=1,
        status='completed',conclusion='failure')
    jobs=[dict(id=m.GREEN_JOBS[name],name=name,head_sha=m.GREEN_SHA,status='completed',conclusion='success') for name in ('proof-map','full-suite')]
    sources={name:dict(head=m.GREEN_SHA,runtime_tree=m.RUNTIME,python='3.12.16',sqlite='3.45.1') for name in ('proof-map','full-suite')}
    return run,jobs,sources


def test_green_prerequisites_are_reusable_despite_later_mature_timeout():
    m=api();r,j,s=green()
    assert m.validate_green(r,j,s,current_runtime=m.RUNTIME)['green_commit']==m.GREEN_SHA


@pytest.mark.parametrize('damage',['runtime','source_head','job_failed','job_skipped','duplicate','run_head','workflow'])
def test_green_reuse_rejects_untested_or_different_engine(damage):
    m=api();r,j,s=green();runtime=m.RUNTIME
    if damage=='runtime':runtime='f'*40
    elif damage=='source_head':s['proof-map']['head']='f'*40
    elif damage=='job_failed':j[0]['conclusion']='failure'
    elif damage=='job_skipped':j[0]['status']='skipped'
    elif damage=='duplicate':j.append(copy.deepcopy(j[0]))
    elif damage=='run_head':r['head_sha']='f'*40
    else:r['path']='other.yml'
    with pytest.raises(ValueError):m.validate_green(r,j,s,current_runtime=runtime)


def test_new_workflow_keeps_expensive_stages_protected_and_old_monolith_untouched():
    from pathlib import Path
    import yaml
    from simulation import stage_0_6_genesis_checkpoint as c
    path=Path(c.WORKFLOW)
    assert path.is_file(),'resumable workflow is missing'
    w=yaml.safe_load(path.read_text());jobs=w['jobs']
    previous='gate'
    for stage in c.STAGES:
        key=c.JOB[stage];job=jobs[key]
        assert set(job['needs'])=={'gate',previous}
        assert 'always()' in job['if']
        if previous!='gate':assert "'failure'" in job['if'] and "'cancelled'" in job['if']
        upload=[s for s in job['steps'] if s.get('id')=='metadata']
        assert len(upload)==1 and upload[0].get('if','success()')!='always()'
        previous=key
    assert 'full-suite' not in jobs and 'proof-map' not in jobs
    raw=path.read_text()
    assert 'simulation/stage_0_6_proof_genesis_request.json' not in raw
    assert 'simulation/ate_sim/**' not in raw and 'simulation/tests/**' not in raw


def test_hosted_software_change_fails_before_reusing_engine_validation():
    m=api()
    assert hasattr(m,'check_software'),'hosted interpreter/SQLite tuple must be checked before engine work'
    m.check_software(dict(python='3.12.16',sqlite='3.45.1',signature='a'*64))
    with pytest.raises(ValueError):m.check_software(dict(python='3.13.5',sqlite='3.46.1',signature='b'*64))


def test_hosted_smoke_kills_a_worker_before_resuming_verified_catalog():
    from pathlib import Path
    import yaml
    m=api();path=Path('.github/tests/run_genesis_recovery_drill.py')
    assert path.is_file(),'real hosted crash/recovery drill is missing'
    assert str(path) in m.CRITICAL
    w=yaml.safe_load(Path('.github/workflows/stage-0-6-resumable-proof-genesis.yml').read_text())
    drill=[s for s in w['jobs']['rebase']['steps'] if s.get('id')=='recovery-drill']
    assert len(drill)==1 and "'smoke'" in drill[0]['if'] and str(path) in drill[0]['run']


def acceptance_receipt(mode='mature'):
    from simulation import stage_0_6_genesis_checkpoint as c
    from test_stage_0_6_genesis_checkpoint import context,descriptor,producer
    ctx=context();ctx['mode']=mode;db=descriptor();row=c.record('source',ctx,db,producer(),data_ref={'kind':'local'})
    for stage in c.STAGES:
        metrics={}
        if stage=='rebase':db={**db,'generation':0,'sha256':'1'*64}
        if stage=='proofs':db={**db,'format':7,'sha256':'2'*64}
        if stage=='measure':
            db={**db,'generation':1,'year':1002,'sha256':'3'*64}
            metrics=dict(benchmark=dict(phases={name:dict(status='complete',wall_seconds=seconds) for name,seconds in dict(open=1,first_step=1,save=1,warm_step=.5).items()},targets_seconds=dict(open=10,save=2,warm_step=1),targets_met=dict(open=True,save=True,warm_step=True),saved_commitment='4'*64))
        if stage=='fresh_restore':metrics=dict(restored=dict(year=1002,seed=843000,generation=1,digest=ctx['expected_saved_digest'],world_audits=0))
        row=c.record(stage,ctx,db,producer(stage),parent=row,data_ref={'kind':'local'},
            baseline_digest='f'*64 if stage=='source_digest' else None,proof_commitment='4'*64 if stage in ('proofs','measure','fresh_restore') else None,metrics=metrics)
    return row


def test_acceptance_checks_actual_measurements_and_fresh_state():
    m=api();assert hasattr(m,'evaluate_acceptance'),'acceptance must validate full measured/fresh evidence'
    assert m.evaluate_acceptance(acceptance_receipt(),'mature')['acceptance']=='mature-targets-met'


@pytest.mark.parametrize('damage',['flag_only','timeout','digest','audits','year','fake_boolean'])
def test_incomplete_or_false_target_claim_cannot_complete_stage06(damage):
    m=api();assert hasattr(m,'evaluate_acceptance'),'strict acceptance is missing'
    row=acceptance_receipt();bench=row['parent']['receipt']['metrics']['benchmark']
    if damage=='flag_only':bench['phases']['save']['wall_seconds']=100
    elif damage=='timeout':bench['phases']['save']['status']='timeout'
    elif damage=='digest':row['metrics']['restored']['digest']='0'*64
    elif damage=='audits':row['metrics']['restored']['world_audits']=1
    elif damage=='year':row['metrics']['restored']['year']=1003
    else:bench['targets_met']['save']=1
    # Recompute the parent binding so the check reaches evidence semantics.
    from simulation import stage_0_6_genesis_checkpoint as c
    row['parent']['sha256']=c.receipt_hash(row['parent']['receipt'])
    with pytest.raises(ValueError):m.evaluate_acceptance(row,'mature')


def test_original_green_jobs_survive_a_later_failed_rerun_attempt():
    m=api();r,j,s=green();r['run_attempt']=2
    assert m.validate_green(r,j,s,current_runtime=m.RUNTIME)['green_commit']==m.GREEN_SHA


def test_green_source_receipt_software_must_match_hosted_tuple():
    m=api();r,j,s=green();s['proof-map']['sqlite']='3.53.1'
    with pytest.raises(ValueError):m.validate_green(r,j,s,current_runtime=m.RUNTIME)


def test_code_fence_includes_imported_helpers_and_authority_data_only(tmp_path):
    m=api();assert hasattr(m,'dependency_paths'),'resume code fence must cover imported helper semantics'
    d=tmp_path/'simulation';d.mkdir()
    (d/'driver.py').write_text("from simulation import helper\nREQUEST='simulation/stage_0_6_genesis_resume_request.json'\n")
    (d/'helper.py').write_text("CONFIG='simulation/authority.json'\n")
    (d/'authority.json').write_text('{}')
    (d/'unrelated.py').write_text('pass')
    (d/'stage_0_6_genesis_resume_request.json').write_text('{}')
    result=m.dependency_paths(tmp_path,['simulation/driver.py'])
    assert result=={'simulation/driver.py','simulation/helper.py','simulation/authority.json'}


def test_missed_mature_targets_stop_before_expensive_fresh_verification():
    m=api();assert hasattr(m,'check_measured_targets'),'known target failure must stop before the deep final digest'
    value=acceptance_receipt()['parent']['receipt']
    value['metrics']['benchmark']['phases']['save']['wall_seconds']=20
    value['metrics']['benchmark']['targets_met']['save']=False
    with pytest.raises(ValueError,match='targets not met'):m.check_measured_targets(value,'mature')


def test_smoke_checks_functional_recovery_without_claiming_mature_speed():
    m=api();assert hasattr(m,'check_measured_targets'),'measurement preflight is missing'
    value=acceptance_receipt('smoke')['parent']['receipt']
    value['metrics']['benchmark']['phases']['save']['wall_seconds']=20
    value['metrics']['benchmark']['targets_met']['save']=False
    assert m.check_measured_targets(value,'smoke')['save'] is False


def test_source_digest_restart_keeps_the_selected_sources_original_run():
    from pathlib import Path
    import yaml
    w=yaml.safe_load(Path('.github/workflows/stage-0-6-resumable-proof-genesis.yml').read_text())
    worker=next(s for s in w['jobs']['source-digest']['steps'] if s.get('id')=='run')
    assert worker['env']['PARENT_RUN']=='${{ needs.gate.outputs.run_id }}', 'an earlier-run source artifact must not be relabeled with the new run id'


def test_diagnostic_upload_failure_cannot_invalidate_committed_checkpoints():
    from pathlib import Path
    import yaml
    w=yaml.safe_load(Path('.github/workflows/stage-0-6-resumable-proof-genesis.yml').read_text())
    for job in w['jobs'].values():
        for step in job['steps']:
            if step.get('id')=='evidence':assert step.get('continue-on-error') is True,'diagnostics must not turn a published checkpoint producer red'
            elif step.get('id') in ('data','seal','metadata','run','decide'):assert step.get('continue-on-error') is not True


def test_receipt_attempt_is_bound_to_authenticated_artifact_name():
    m=api();assert hasattr(m,'match_receipt_reference'),'receipt attempt must be bound to artifact identity'
    from test_stage_0_6_genesis_checkpoint import source
    value=source();producer=value['producer']
    ref=dict(run_id=producer['run_id'],head_sha=producer['head_sha'],job=producer['job'],name='checkpoint-smoke-source-'+producer['head_sha']+'-1')
    m.match_receipt_reference(value,ref,mode='smoke',stage='source')
    value['producer']['attempt']=2
    with pytest.raises(ValueError):m.match_receipt_reference(value,ref,mode='smoke',stage='source')
