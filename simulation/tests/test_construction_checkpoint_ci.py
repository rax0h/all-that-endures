"""Fresh-runner construction proof cannot start mature construction."""
import importlib.util
import json
from pathlib import Path
import pytest


def runner():
    assert importlib.util.find_spec('simulation.construction_checkpoint_ci'), 'construction CI runner missing'
    return __import__('simulation.construction_checkpoint_ci',fromlist=['*'])


def test_transport_checks_exact_stage_members_and_manifest_producer(tmp_path, monkeypatch):
    m=runner(); monkeypatch.setattr(m,'ROOT',tmp_path)
    monkeypatch.setenv('GITHUB_RUN_ID','23'); monkeypatch.setenv('GITHUB_SHA','a'*40)
    def download(destination,**kwargs):
        assert kwargs['job']=='prepare'
        assert kwargs['members']=={'target.sqlite','spool.sqlite','manifest.json'}
        destination.mkdir()
        (destination/'manifest.json').write_text(json.dumps({'producer':dict(mode='ci',run_id=23,job='foreign',workflow_sha='a'*40)}))
    monkeypatch.setattr(m.artifacts,'download',download)
    with pytest.raises(ValueError,match='producer'):m.get('prepare')


def test_shared_fixture_contains_counted_rosters_and_shared_nested_identity():
    from ate_sim.worldgen import generate_world
    m=runner();world=m.fixture_world(generate_world,843000,mature=False)
    first,second=sorted(world.people)[:2]
    assert world.skills.skills[first,'craft'].provenance is world.skills.skills[second,'craft'].provenance
    assert any(h.members for h in world.households.values())


def test_workflow_proves_interrupted_construction_before_continuation():
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-construction-proof.yml'
    assert path.exists(),'construction proof workflow missing'
    text=path.read_text()
    import yaml
    data=yaml.safe_load(text)
    jobs=data['jobs']
    for stage,previous in [('prepare','source'),('interrupt','prepare'),('commit','interrupt'),
        ('orders','commit'),('storage','orders'),('catalog','storage'),('publish','catalog'),
        ('continue','publish'),('restore','continue')]:
        assert previous in jobs[stage]['needs']
        assert jobs[stage]['timeout-minutes']==20
        steps=jobs[stage]['steps']
        diagnostics=next(i for i,s in enumerate(steps) if s.get('name')=='Retain diagnostics')
        upload=next(i for i,s in enumerate(steps) if s.get('name')=='Retain completed stage')
        assert diagnostics<upload
        assert steps[diagnostics]['continue-on-error'] is True
        assert 'if' not in steps[upload]
    assert {'full-suite','recovery'}<=jobs.keys()
    source_upload=next(s for s in jobs['source']['steps'] if s.get('name')=='Retain completed stage')
    assert set(source_upload['with']['path'].splitlines())=={
        'evidence/source/checkpoint.json','evidence/source/p5-long-lazy.sqlite','evidence/source/fixture.json'}
    assert '300m' not in text and 'checkpoint_mature_capture' not in text
    assert 'sol/stage-0-5-construction-proof' in text


def test_stage_progress_records_cpu_disk_and_output_inventory(tmp_path,monkeypatch,capsys):
    m=runner();monkeypatch.setattr(m,'ROOT',tmp_path)
    monkeypatch.setenv('GITHUB_JOB','local')
    with m.measure('probe'):
        (tmp_path/'example.txt').write_text('example')
    row=json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert row['stage']=='probe_finished' and row['wall_seconds']>=0 and row['cpu_seconds']>=0
    assert row['disk_free_bytes']>0 and row['peak_rss_kib']>0


def test_metrics_use_executed_process_highwater_not_inherited_rusage(monkeypatch,capsys):
    from types import SimpleNamespace
    m=runner()
    monkeypatch.setattr(m.resource,'getrusage',lambda _:SimpleNamespace(ru_maxrss=10**9,ru_oublock=0))
    original=Path.read_text
    def read(path,*args,**kwargs):
        if str(path)=='/proc/self/status':return 'VmHWM:\t12345 kB\nVmPeak:\t45678 kB\n'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    with m.measure('probe'):pass
    row=json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert row['peak_rss_kib']==12345 and row['peak_virtual_kib']==45678
