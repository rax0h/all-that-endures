"""Phase evidence must identify its input and retain open/dirty-save work."""
from dataclasses import asdict
from pathlib import Path
import copy
import functools
import sys

import pytest

from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.continuation_receipts import file_hash
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture, RULES


def runner():
    from simulation import profile_stage_0_5_performance
    return profile_stage_0_5_performance


def source_authority(path):
    with open_lazy_world_session(path, rules_id=RULES) as session:
        pin = asdict(session.pin)
        world = {'seed': session.world.seed, 'year': session.world.year}
    return {'schema': 'ate-performance-source/1',
            'database': {'sha256': file_hash(path), 'bytes': path.stat().st_size},
            'rules_id': RULES, 'pin': pin, 'world': world,
            'provenance': {'kind': 'local-test-fixture', 'description': '16 packed actions'}}


def test_phase_metrics_include_open_and_dirty_save(tmp_path):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    result = runner().run_phase(path, tmp_path/'result', phase='step-save', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'complete', result
    assert set(result['phases']) == {'open', 'step', 'save'}
    assert result['phases']['open']['io']['payload_reads'] > 0
    assert result['phases']['save']['io']['payload_writes'] > 0
    assert result['final']['year'] == authority['world']['year'] + 1
    assert result['final']['pin']['captured_head'] > authority['pin']['captured_head']
    assert result['phases']['step']['cpu_seconds'] >= 0
    assert 'process_peak_rss_bytes' in result['phases']['open']


def test_source_is_immutable(tmp_path):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    result = runner().run_phase(path, tmp_path/'result', phase='step-save', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'complete', result
    assert file_hash(path) == authority['database']['sha256']
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.year == authority['world']['year']
        assert asdict(session.pin)['captured_head'] == authority['pin']['captured_head']


@pytest.mark.parametrize('change', ['hash', 'world', 'pin'])
def test_wrong_authority_is_rejected(tmp_path, change):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    digest = authority['database']['sha256']
    if change == 'hash': authority['database']['sha256'] = '0'*64
    elif change == 'world': authority['world']['year'] += 1
    else: authority['pin']['captured_head'] += 1
    result = runner().run_phase(path, tmp_path/'result', phase='step-save', seconds=30,
        expected_sha256=digest, authority=authority)
    assert result['status'] == 'error'
    assert 'step' not in result['phases']
    assert file_hash(path) == digest


def test_hashing_is_streamed(tmp_path, monkeypatch):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    def forbidden(*args, **kwargs):
        raise AssertionError('whole-file read is forbidden')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    result = runner().run_phase(path, tmp_path/'result', phase='open', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'complete', result


def test_timeout_is_not_a_pass(tmp_path, monkeypatch):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    mod = runner()
    @functools.wraps(mod.open_lazy_world_session)
    def expired(*args, **kwargs):
        raise mod.BudgetExpired('test budget')
    monkeypatch.setattr(mod, 'open_lazy_world_session', expired)
    result = mod.run_phase(path, tmp_path/'result', phase='open', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'timeout'
    assert result['phases']['open']['status'] == 'timeout'


def test_comparison_rejects_different_sources(tmp_path):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    baseline = runner().run_phase(path, tmp_path/'result', phase='open', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    changed = copy.deepcopy(baseline)
    changed['source']['database']['sha256'] = '0'*64
    with pytest.raises(ValueError, match='source'):
        runner().compare_receipts(baseline, changed)
    changed = copy.deepcopy(baseline)
    changed['profiled'] = True
    with pytest.raises(ValueError, match='instrumentation'):
        runner().compare_receipts(baseline, changed)


def test_warm_steps_are_separately_measured(tmp_path):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    result = runner().run_phase(path, tmp_path/'result', phase='step-save', warm_steps=2, seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    assert result['status'] == 'complete', result
    assert result['warm_steps'] == 2
    assert set(result['phases']) == {'open', 'step', 'warm_step_1', 'warm_step_2', 'save'}
    assert result['final']['year'] == authority['world']['year'] + 3


@pytest.mark.parametrize('change', ['harness', 'warm_steps', 'phases'])
def test_comparison_rejects_different_measurement_workloads(tmp_path, change):
    path = fixture(tmp_path, 16)
    authority = source_authority(path)
    baseline = runner().run_phase(path, tmp_path/'result', phase='open', seconds=30,
        expected_sha256=authority['database']['sha256'], authority=authority)
    changed = copy.deepcopy(baseline)
    if change == 'harness': changed['harness_sha256'] = '0'*64
    elif change == 'warm_steps': changed['warm_steps'] = 2
    else: changed['phases']['extra'] = copy.deepcopy(changed['phases']['open'])
    with pytest.raises(ValueError): runner().compare_receipts(baseline, changed)


def test_provenance_follows_imported_runtime_not_harness_location(tmp_path, monkeypatch):
    mod = runner()
    monkeypatch.setattr(mod, '__file__', str(tmp_path/'foreign'/'harness.py'))
    identity = mod._runtime_identity()
    assert Path(identity['engine_path']) == Path(sys.modules[mod.Simulation.__module__].__file__).resolve()
    assert identity['committed_tree']
    assert Path(identity['root']) == Path(__file__).resolve().parents[2]


def test_provenance_rejects_mixed_import_roots(tmp_path, monkeypatch):
    mod = runner()
    module = sys.modules[mod.open_lazy_world_session.__module__]
    monkeypatch.setattr(module, '__file__', str(tmp_path/'ate_sim'/'persistence_lazy.py'))
    with pytest.raises(ValueError, match='runtime roots'):
        mod._runtime_identity()
