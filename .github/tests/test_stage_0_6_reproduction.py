"""Reproduction names its source and public checkouts; no sibling defaults."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


PATH=Path(__file__).resolve().parents[2]/'docs/performance/stage-0-6-current/small-operation-profile/read-view-epoch/repeat-comparison/repeat.py'


def load():
    spec=importlib.util.spec_from_file_location('explicit_raw_reproduction',PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.fixture
def scenario(tmp_path,monkeypatch):
    module=load();root=tmp_path/'checkout';root.mkdir()
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
    git('init');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
    engine=root/'simulation/ate_sim/module.py';engine.parent.mkdir(parents=True);engine.write_text('value=1\n')
    driver=root/module.DRIVER;driver.parent.mkdir(parents=True);driver.write_text('raise AssertionError("dry run executed a child")\n')
    git('add','.');git('commit','-m','public fixture')
    head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD:simulation/ate_sim')
    source=tmp_path/'source.sqlite';source.write_bytes(b'closed fixture')
    authority=tmp_path/'input.json';authority.write_text(json.dumps(dict(database=dict(sha256=hashlib.sha256(source.read_bytes()).hexdigest()))))
    monkeypatch.setattr(module,'INPUT',authority)
    monkeypatch.setattr(module,'EXPECTED_TREES',dict(baseline=tree,candidate=tree))
    args=['repeat','--source',str(source),'--baseline-root',str(root),'--candidate-root',str(root),
        '--baseline-commit',head,'--candidate-commit',head,'--dry-run']
    monkeypatch.setattr(sys,'argv',args)
    return module,root,source,engine,driver,args


def test_explicit_reproduction_dry_run_records_exact_heads_and_observed_load(scenario,capsys):
    module,root,source,engine,driver,args=scenario
    module.main();value=json.loads(capsys.readouterr().out)
    assert value['heads']==dict(baseline=args[8],candidate=args[10])
    assert value['context']['cpu_totals'] and len(value['context']['load_average'])==3
    assert 'do not prove an idle' in value['context']['observation_limit']
    assert not (root/'output').exists()


@pytest.mark.parametrize('change',['head','engine','helper','source','output'])
def test_implicit_or_changed_input_cannot_start_trials(scenario,change):
    module,root,source,engine,driver,args=scenario
    if change=='head':args[8]='0'*40
    elif change=='engine':engine.write_text('changed\n')
    elif change=='helper':driver.write_text('changed helper\n')
    elif change=='source':source.write_bytes(b'changed')
    else:args.remove('--dry-run');args.extend(['--output',str(root/'output')])
    with pytest.raises(ValueError):module.main()
    assert not (root/'output').exists()


def test_missing_explicit_sources_is_argument_error_before_any_implicit_file_read(monkeypatch):
    monkeypatch.setattr(sys,'argv',['repeat','--dry-run'])
    with pytest.raises(SystemExit) as exc:load().main()
    assert exc.value.code==2


def test_missing_output_is_argument_error_before_preflight(scenario):
    module,root,source,engine,driver,args=scenario
    args.remove('--dry-run')
    source.unlink()  # Argument validation must precede even the source read.
    with pytest.raises(SystemExit) as exc:module.main()
    assert exc.value.code==2


def test_outer_termination_unwinds_and_restores_previous_handler(scenario,monkeypatch):
    import os,signal
    module,*_=scenario;previous=signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(module,'run',lambda args:os.kill(os.getpid(),signal.SIGTERM))
    with pytest.raises(SystemExit) as exc:module.main()
    assert exc.value.code==128+signal.SIGTERM
    assert signal.getsignal(signal.SIGTERM)==previous
