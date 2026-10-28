"""Small real checkpoints exercise benchmark timing and failure boundaries."""
import importlib.util
from pathlib import Path
import signal
import time

import pytest

from simulation import continuation_receipts as r
from simulation import stage_0_5_mature_step_save as runner
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture, RULES
from simulation.tests.test_stage_0_5_performance_runner import source_authority


def test_preparation_is_receipted_outside_operation_budget(tmp_path, monkeypatch):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    verify = runner.base._verify_authority
    def slow_verify(*args):
        time.sleep(.15)
        return verify(*args)
    monkeypatch.setattr(runner.base, '_verify_authority', slow_verify)
    result = runner.run(path, tmp_path/'run', seconds=.1,
        preparation_seconds=5, phase_seconds=5,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'complete', result
    assert result['preparation']['status'] == 'complete'
    assert result['preparation']['wall_seconds'] >= .15
    assert set(result['preparation']['phases']) == {'source_authentication', 'copy', 'copy_hash'}
    assert (tmp_path/'run/preparation.json').is_file()


def test_phase_timeout_retains_closed_saved_checkpoint(tmp_path, monkeypatch):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    original = runner.Simulation.run
    calls = 0
    def warm_timeout(self, years):
        nonlocal calls
        calls += 1
        if calls == 2:
            time.sleep(2)
        return original(self, years)
    monkeypatch.setattr(runner.Simulation, 'run', warm_timeout)
    result = runner.run(path, tmp_path/'run', seconds=30,
        preparation_seconds=5, phase_seconds=.4,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'timeout', result
    assert result['phases']['warm_step']['status'] == 'timeout'
    assert result['saved_database']['sha256'] == r.file_hash(tmp_path/'run/operational.sqlite')
    assert result['source_unchanged']
    with runner.open_lazy_world_session(tmp_path/'run/operational.sqlite', rules_id=RULES) as session:
        assert session.world.year == authority['world']['year'] + 1


def test_preparation_error_still_publishes_result(tmp_path):
    result = runner.run(tmp_path/'missing', tmp_path/'run', seconds=1,
        expected_sha256='0'*64, authority={})
    assert result['status'] == 'error'
    assert r.load_receipt(tmp_path/'run/result.json')['status'] == 'error'


def test_restore_timeout_publishes_censored_open(tmp_path, monkeypatch):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    def slow_open(*args, **kwargs):
        time.sleep(2)
    monkeypatch.setattr(runner, 'open_lazy_world_session', slow_open)
    result = runner.verify_checkpoint(path, tmp_path/'restore.json',
        expected_sha256=r.file_hash(path), expected_bytes=path.stat().st_size,
        rules_id=RULES, expected_year=authority['world']['year'],
        expected_seed=authority['world']['seed'],
        expected_generation=authority['pin']['captured_head'],
        expected_store_identity=authority['pin']['store_identity'],
        expected_digest='unused', seconds=.1)
    assert result['status'] == 'timeout'
    assert result['phases']['fresh_open']['status'] == 'timeout'
    assert r.load_receipt(tmp_path/'restore.json')['status'] == 'timeout'


def test_restore_times_open_separately_from_digest(tmp_path):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    with runner.open_lazy_world_session(path, rules_id=RULES) as session:
        digest = session.world.digest()
    result = runner.verify_checkpoint(path, tmp_path/'restore.json',
        expected_sha256=r.file_hash(path), expected_bytes=path.stat().st_size,
        rules_id=RULES, expected_year=authority['world']['year'],
        expected_seed=authority['world']['seed'],
        expected_generation=authority['pin']['captured_head'],
        expected_store_identity=authority['pin']['store_identity'],
        expected_digest=digest, seconds=10)
    assert result['status'] == 'complete', result
    assert result['phases']['fresh_open']['wall_seconds'] > 0
    assert result['phases']['digest']['wall_seconds'] > 0


def test_gate_reports_timeout_before_missing_restore(tmp_path):
    r.publish_receipt(tmp_path/'result.json', {'status': 'timeout'})
    with pytest.raises(ValueError, match='timing lane.*timeout'):
        runner.require_complete(tmp_path)


def test_smoke_selects_current_workflow_command():
    script = Path(__file__).resolve().parents[2]/'.github/tests/check_mature_step_save_launch.py'
    spec = importlib.util.spec_from_file_location('launch_check', script)
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    workflow = script.parents[1]/'workflows/stage-0-6-current-mature-performance.yml'
    command = check.launch_command(workflow)
    assert 'simulation.stage_0_5_mature_step_save run' in command
    assert '--phase-seconds' in command


def test_caller_alarm_is_not_replaced(tmp_path):
    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        with pytest.raises(ValueError, match='active caller alarm'):
            runner.run(tmp_path/'missing', tmp_path/'run', seconds=1,
                expected_sha256='0'*64, authority={})
        assert signal.getitimer(signal.ITIMER_REAL)[0] > 50
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
