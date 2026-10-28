from pathlib import Path
import importlib,time
import pytest
from simulation.tests.test_stage_0_5_performance_runner import source_authority
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture


def mod():return importlib.import_module('simulation.stage_0_6_mature_benchmark')


def test_actual_small_checkpoint_has_separate_phases_and_immutable_source(tmp_path):
 s=fixture(tmp_path,16);a=source_authority(s)
 value=mod().run(s,tmp_path/'measurement',authority=a,budgets={'open':30,'first_step':30,'save':30,'warm_step':30})
 assert value['status']=='complete',value
 assert {'database_open','state_restore','open_total','first_step','save','warm_step','source_verification','copy_verification','saved_file_hash'}<=set(value['phases'])
 assert value['phases']['database_open']['wall_seconds']>0
 assert value['phases']['state_restore']['wall_seconds']>0
 assert value['source_unchanged'] and value['saved']['year']==a['world']['year']+1
 assert value['final']['year']==a['world']['year']+2
 assert value['phases']['save']['io']['payload_writes']>0
 assert value['phases']['open_total']['io']['payload_reads']>0
 assert value['runtime']['committed_tree'] and value['machine']['sqlite']
 from ate_sim.persistence_lazy import open_lazy_world_session
 with open_lazy_world_session(tmp_path/'measurement/operational.sqlite',rules_id=a['rules_id']) as checked:digest=checked.world.digest()
 fresh=mod().verify(tmp_path/'measurement/operational.sqlite',tmp_path/'fresh.json',seconds=30,expected_sha256=mod().r.file_hash(tmp_path/'measurement/operational.sqlite'),expected_bytes=value['saved_database']['bytes'],rules_id=a['rules_id'],expected_year=a['world']['year']+1,expected_seed=a['world']['seed'],expected_generation=a['pin']['captured_head']+1,expected_store_identity=a['pin']['store_identity'],expected_digest=digest)
 assert fresh['status']=='complete',fresh
 assert {'fresh_open_total','fresh_database_open','fresh_state_restore','logical_digest','verification_total'}<=set(fresh['phases'])


def test_phase_timeout_is_censored_and_published(tmp_path):
 recorder=mod().Recorder(tmp_path,{'slow':.01})
 with pytest.raises(mod().base.BudgetExpired):recorder.measure('slow',lambda:time.sleep(.1))
 assert recorder.phases['slow']['status']=='timeout'
 assert (tmp_path/'phase-progress-slow.json').is_file()

@pytest.mark.parametrize('field',['hash','size','pin','world'])
def test_wrong_source_authority_cannot_reach_step(tmp_path,field):
 s=fixture(tmp_path,16);a=source_authority(s)
 if field=='hash':a['database']['sha256']='0'*64
 elif field=='size':a['database']['bytes']+=1
 elif field=='pin':a['pin']['captured_head']+=1
 else:a['world']['year']+=1
 result=mod().run(s,tmp_path/'bad',authority=a,budgets={'open':30,'first_step':30,'save':30,'warm_step':30})
 assert result['status']=='error' and 'first_step' not in result['phases']


def test_runtime_fence_rejects_wrong_tree(tmp_path):
 with pytest.raises(ValueError):mod().check_source(Path.cwd(),{'runtime_tree':'0'*40,'green_commit':'b3030921dfa7b2d6d9685c7c360534928331f805','fingerprints':{}},'0'*40)


def test_summary_keeps_missing_targets_and_timeouts_explicit(tmp_path):
 from simulation.stage_0_6_benchmark_launch import summarize
 from simulation import continuation_receipts as r
 root=tmp_path;current=root/'evidence/current';current.mkdir(parents=True)
 r.publish_receipt(current/'result.json',dict(status='timeout',runtime={'head':'test','committed_tree':'test'},phases={'open_total':{'status':'complete','wall_seconds':12},'first_step':{'status':'timeout','wall_seconds':30}}))
 assert not summarize(root,{'historical_seconds':{'open_total':313.270},'targets_seconds':{'open_total':10}})
 rows=r.load_receipt(root/'evidence/comparison.json')['rows'];assert rows[0]['result']=='fail'
 assert rows[1]['status']=='timeout' and rows[1]['result']=='not measured' and rows[1]['target_seconds'] is None
 assert (root/'evidence/summary.md').is_file()


def test_restore_timeout_remains_censored(tmp_path,monkeypatch):
 from simulation import stage_0_5_mature_step_save as old
 s=fixture(tmp_path,16);a=source_authority(s)
 def slow(*args,**kw):time.sleep(.2)
 monkeypatch.setattr(old,'open_lazy_world_session',slow)
 value=mod().verify(s,tmp_path/'timeout.json',seconds=.02,expected_sha256=a['database']['sha256'],expected_bytes=a['database']['bytes'],rules_id=a['rules_id'],expected_year=a['world']['year'],expected_seed=a['world']['seed'],expected_generation=a['pin']['captured_head'],expected_store_identity=a['pin']['store_identity'],expected_digest='0'*64)
 assert value['status']=='timeout' and value['censored']
 assert value['phases']['fresh_open_total']['status']=='timeout'
 assert value['phases']['verification_total']['status']=='timeout'
 assert value['phases']['verification_total']['censored']


def test_exact_workflow_measure_and_verify_launchers_on_small_fixture(tmp_path):
 import json,os,shutil,subprocess,yaml
 from ate_sim.engine import Simulation
 from ate_sim.persistence_lazy import open_lazy_world_session
 from simulation import continuation_receipts as r
 repo=Path(__file__).resolve().parents[2];s=fixture(tmp_path,16);a=source_authority(s)
 root=tmp_path/'workspace';(root/'source').mkdir(parents=True);(root/'evidence').mkdir();shutil.copyfile(s,root/'source/candidate.sqlite')
 control=tmp_path/'control.sqlite';shutil.copyfile(s,control)
 with open_lazy_world_session(control,rules_id=a['rules_id']) as session:
  Simulation(session.world).run(1);expected=session.world.digest()
 config=json.loads((repo/'simulation/stage_0_6_benchmark_launch.json').read_text());config.update(database=dict(name='candidate.sqlite',**a['database']),world=a['world'],pin={k:a['pin'][k] for k in ('store_identity','captured_head')},expected_saved_digest=expected,budgets={'open':30,'first_step':30,'save':30,'warm_step':30},verification_budget_seconds=60)
 path=tmp_path/'smoke-config.json';path.write_text(json.dumps(config));r.publish_receipt(root/'evidence/source-authority.json',a)
 workflow=yaml.safe_load((repo/'.github/workflows/stage-0-6-current-mature-performance.yml').read_text());env=dict(os.environ,GITHUB_WORKSPACE=str(root),GITHUB_SHA=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),PYTHONPATH='.:simulation')
 for name in ('measure','restore'):
  command=next(step['run'] for step in workflow['jobs']['measure']['steps'] if step.get('id')==name).replace('simulation/stage_0_6_benchmark_launch.json',str(path))
  run=subprocess.run(['bash','-e','-o','pipefail','-c',command],cwd=repo,env=env,capture_output=True,text=True,timeout=90)
  assert run.returncode==0,(run.stdout,run.stderr)
 assert r.load_receipt(root/'evidence/fresh-restore.json')['status']=='complete'
 assert r.file_hash(root/'source/candidate.sqlite')==a['database']['sha256']


def test_workflow_checkout_contains_the_pinned_green_ancestor(tmp_path,monkeypatch):
 import hashlib,subprocess,yaml
 def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
 seed=tmp_path/'origin';seed.mkdir();git(seed,'init');git(seed,'config','user.email','fixture@example.invalid');git(seed,'config','user.name','Fixture')
 runtime=seed/'simulation/ate_sim';runtime.mkdir(parents=True);(runtime/'module.py').write_text('value=1\n');git(seed,'add','.');git(seed,'commit','-m','green');green=git(seed,'rev-parse','HEAD')
 (seed/'harness.py').write_text('fixture harness\n');git(seed,'add','.');git(seed,'commit','-m','benchmark');head=git(seed,'rev-parse','HEAD')
 workflow=yaml.safe_load((Path.cwd()/'.github/workflows/stage-0-6-current-mature-performance.yml').read_text());checkout=workflow['jobs']['measure']['steps'][0];depth=checkout.get('with',{}).get('fetch-depth',1)
 clone=tmp_path/'checkout';command=['git','clone','--quiet']+(['--depth',str(depth)] if depth else [])+[seed.as_uri(),str(clone)];subprocess.run(command,check=True)
 monkeypatch.setattr(mod().base,'_runtime_identity',lambda:{'root':str(clone),'head':head})
 config={'green_commit':green,'runtime_tree':git(seed,'rev-parse','HEAD:simulation/ate_sim'),'fingerprints':{'harness.py':hashlib.sha256((seed/'harness.py').read_bytes()).hexdigest()}}
 assert mod().check_source(clone,config,head)['head']==head

@pytest.mark.parametrize('bad',['hash','size','sidecar'])
def test_failed_preopen_verification_retains_final_diagnostic_receipt(tmp_path,bad):
 s=fixture(tmp_path,16);a=source_authority(s)
 if bad=='sidecar':Path(str(s)+'-journal').write_bytes(b'not a closed checkpoint')
 value=mod().verify(s,tmp_path/'failed-restore.json',seconds=30,expected_sha256='0'*64 if bad=='hash' else a['database']['sha256'],expected_bytes=a['database']['bytes']+(1 if bad=='size' else 0),rules_id=a['rules_id'],expected_year=a['world']['year'],expected_seed=a['world']['seed'],expected_generation=a['pin']['captured_head'],expected_store_identity=a['pin']['store_identity'],expected_digest='0'*64)
 assert value['status']=='error' and (tmp_path/'failed-restore.json').is_file()
 assert value['phases']['verification_total']['status']=='error'


def test_temporary_key_high_water_is_not_reported_as_a_counter_delta(tmp_path):
 from dataclasses import fields
 from types import SimpleNamespace
 from ate_sim.persistence_lazy_store import LazyStoreDiagnostics
 values={f.name:0 for f in fields(LazyStoreDiagnostics)};values['temporary_keys_peak']=100
 recorder=mod().Recorder(tmp_path,{})
 recorder.store=SimpleNamespace(diagnostics=lambda:LazyStoreDiagnostics(**values))
 recorder.measure('higher',lambda:values.update(temporary_keys_peak=120))
 recorder.measure('unchanged',lambda:None)
 assert 'temporary_keys_peak' not in recorder.phases['higher']['io']
 assert recorder.phases['higher']['io_high_water']['temporary_keys_peak']=={'before':100,'after':120}
 assert recorder.phases['unchanged']['io_high_water']['temporary_keys_peak']=={'before':120,'after':120}


def test_shell_timeout_retains_started_phase_and_censored_command_receipt(tmp_path):
 import os,subprocess
 root=tmp_path;output=root/'evidence/current';output.mkdir(parents=True)
 code="from pathlib import Path; import time; from simulation.stage_0_6_mature_benchmark import Recorder; r=Recorder(Path("+repr(str(output))+"),{}); r.measure('database_copy',lambda:time.sleep(30))"
 env=dict(os.environ,PYTHONPATH='.:simulation')
 stopped=subprocess.run(['timeout','--signal=TERM','--kill-after=.2s','2s','python','-c',code],env=env,capture_output=True,text=True)
 assert stopped.returncode in (124,137),stopped.stderr
 value=importlib.import_module('simulation.stage_0_6_benchmark_launch').record_command_exit(root,'measure',stopped.returncode)
 assert value['censored'] and value['status']=='timeout'
 assert (output/'phase-start-database_copy.json').is_file()
 assert (output/'result.json').is_file()


def test_only_one_stage06_measurement_workflow_and_no_automatic_launch():
 import yaml
 root=Path(__file__).resolve().parents[2]
 paths=sorted((root/'.github/workflows').glob('stage-0-6-*.yml'))
 assert [p.name for p in paths]==['stage-0-6-current-mature-performance.yml']
 workflow=yaml.safe_load(paths[0].read_text())
 assert set(workflow['on'])=={'workflow_dispatch'}
 assert workflow['concurrency']['cancel-in-progress'] is False
