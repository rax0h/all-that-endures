"""Commit-only wiring must consume retained preparation and stop before orders."""
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulation import construction_checkpoint as core
from simulation.tests.test_construction_checkpoint import inputs, hashes
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_commit'), 'mature commit wiring missing'
    return importlib.import_module('simulation.construction_mature_commit')


def fixture(tmp_path, monkeypatch):
    m = module()
    source, receipt = inputs(tmp_path)
    prepared = tmp_path/'prepared'
    manifest = core.prepare(source, receipt, prepared, rules_id=RULES, context=CONTEXT)
    monkeypatch.setattr(m, 'CONTEXT', CONTEXT)
    monkeypatch.setattr(m, 'PREPARED_PRODUCER', manifest['producer'])
    monkeypatch.setattr(m, 'PREPARED_FILES', manifest['files'])
    monkeypatch.setattr(m, 'PREPARED_PIN', manifest['pin'])
    monkeypatch.setattr(m, 'SOURCE_CONFIG', {'rules_id': RULES})
    monkeypatch.setattr(m, 'SOURCE_WORKFLOW_SHA', None)
    return m, source, prepared


def test_mature_commit_saves_original_commit_without_repeating_preparation_or_orders(tmp_path, monkeypatch):
    m, source, prepared = fixture(tmp_path, monkeypatch)
    before, original = hashes(prepared), sha(source)
    def forbidden(*args, **kwargs):
        raise AssertionError('commit repeated preparation or started ordering')
    monkeypatch.setattr(core, 'prepare', forbidden)
    monkeypatch.setattr(core.copy, '_restore_copy_ordinals', forbidden)
    result = m.run_commit(prepared, tmp_path/'committed')
    assert result['stage'] == 'committed'
    assert result['pin']['captured_head'] == result['source_generation'] + 1
    assert result['prepared_manifest_sha256'] == before['manifest.json']
    assert {p.name for p in (tmp_path/'committed').iterdir()} == {'target.sqlite', 'manifest.json'}
    assert hashes(prepared) == before and sha(source) == original


@pytest.mark.parametrize('field', ['producer', 'context', 'files', 'pin', 'rules_id', 'source_receipt'])
def test_foreign_preparation_is_rejected_before_expensive_commit(tmp_path, monkeypatch, field):
    m, _, prepared = fixture(tmp_path, monkeypatch)
    path = prepared/'manifest.json'
    value = json.loads(path.read_text())
    value[field] = '{}' if field == 'source_receipt' else 'foreign'
    path.write_text(json.dumps(value))
    def forbidden(*a, **kw):
        raise AssertionError('foreign preparation reached original commit')
    monkeypatch.setattr(core, 'commit_prepared', forbidden)
    with pytest.raises(ValueError):
        m.run_commit(prepared, tmp_path/'committed')
    assert not (tmp_path/'committed').exists()


@pytest.mark.parametrize('condition', ['duplicate', 'rerun', 'workflow'])
def test_duplicate_or_foreign_run_is_rejected_before_download(monkeypatch, condition):
    m = module()
    monkeypatch.setenv('GITHUB_RUN_ID', '23')
    monkeypatch.setenv('GITHUB_SHA', 'a'*40)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2' if condition == 'rerun' else '1')
    current = dict(id=23, head_sha='a'*40, path=m.WORKFLOW, head_branch=m.BRANCH)
    if condition == 'workflow': current['path'] = 'foreign.yml'
    monkeypatch.setattr(m.artifacts, '_api', lambda *a: current)
    rows = [current]
    if condition == 'duplicate': rows.append(dict(current, id=22))
    monkeypatch.setattr(m.artifacts, '_pages', lambda *a: rows)
    with pytest.raises(ValueError): m.unique_launch()


def test_download_uses_exact_prepared_artifact_and_validates_transfer(tmp_path, monkeypatch):
    m = module()
    monkeypatch.setattr(m, 'ROOT', tmp_path)
    def download(destination, **kwargs):
        assert kwargs == dict(run_id=38833265909,
            workflow_sha='c669c29a0c04544da451a35d2631cde9cc79d253',
            name='construction-mature-prepared', job='mature-prepare',
            workflow_path='.github/workflows/stage-0-5-mature-prepare.yml',
            members={'target.sqlite', 'spool.sqlite', 'manifest.json'}, artifact_id=12024550042,
            expected_digest='01db7a227f4a50a0bab347a211c09e2409880875de685cff1e32a01724322e06')
        destination.mkdir()
        return dict(archive_bytes=1)
    monkeypatch.setattr(m.artifacts, 'download', download)
    with pytest.raises(ValueError, match='archive size'): m.download_prepared()


def test_summary_failure_cannot_strand_completed_commit(tmp_path, monkeypatch):
    m, _, prepared = fixture(tmp_path, monkeypatch)
    root = tmp_path/'evidence'
    monkeypatch.setattr(m, 'ROOT', root)
    monkeypatch.setenv('HARNESS_SHA', 'd'*40)
    monkeypatch.setenv('RUNTIME_SHA', m.RUNTIME_SHA)
    monkeypatch.setattr(m.subprocess, 'check_output', lambda args, **kw:
        'd'*40 if args[-1] == 'HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource, 'setrlimit', lambda *a: None)
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=100*1024**3))
    monkeypatch.setattr(m, 'unique_launch', lambda: None)
    monkeypatch.setattr(m, 'check_helpers', lambda: None)
    monkeypatch.setattr(m, 'download_prepared', lambda: (prepared, {}))
    original = m.old._write_new
    def write(path, data):
        if Path(path).name == 'commit-summary.json': raise OSError('diagnostic disk error')
        return original(path, data)
    monkeypatch.setattr(m.old, '_write_new', write)
    m.main()
    assert json.loads((root/'committed/manifest.json').read_text())['stage'] == 'committed'


@pytest.mark.parametrize('before,after', [(99, 100), (103, 74)])
def test_measured_commit_disk_budget_is_required_before_replay(tmp_path, monkeypatch, before, after):
    m = module()
    monkeypatch.setattr(m, 'ROOT', tmp_path/'evidence')
    monkeypatch.setenv('HARNESS_SHA', 'd'*40)
    monkeypatch.setenv('RUNTIME_SHA', m.RUNTIME_SHA)
    monkeypatch.setattr(m.subprocess, 'check_output', lambda args, **kw:
        'd'*40 if args[-1] == 'HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource, 'setrlimit', lambda *a: None)
    monkeypatch.setattr(m, 'unique_launch', lambda: None)
    monkeypatch.setattr(m, 'check_helpers', lambda: None)
    values = iter([before, after])
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=next(values)*1024**3))
    monkeypatch.setattr(m, 'download_prepared', lambda: (tmp_path/'prepared', {}))
    def forbidden(*a, **kw):
        raise AssertionError('commit reached replay without measured disk headroom')
    monkeypatch.setattr(m, 'run_commit', forbidden)
    with pytest.raises(ValueError, match='GiB'): m.main()
    assert not (m.ROOT/'committed').exists()


@pytest.mark.parametrize('status', [0, 7, 124])
def test_commit_log_failure_does_not_override_command_status(status):
    import subprocess
    import yaml
    path = Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-commit.yml'
    assert path.exists(), 'mature commit workflow missing'
    workflow = yaml.safe_load(path.read_text())
    assert set(workflow['jobs']) == {'mature-commit'}
    job = workflow['jobs']['mature-commit']
    assert job['timeout-minutes'] == 360
    script = next(s['run'] for s in job['steps'] if s.get('name') == 'Commit retained mature preparation')
    script = script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_commit',
        f"bash -c 'exit {status}'")
    script = script.replace('tee evidence/commit.log', "bash -c 'cat >/dev/null; exit 42'")
    result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], capture_output=True)
    assert result.returncode == status
    upload = next(s for s in job['steps'] if s.get('name') == 'Retain committed construction')
    assert upload['with']['path'] == 'evidence/committed' and 'if' not in upload
    diagnostics = next(s for s in job['steps'] if s.get('name') == 'Retain diagnostics')
    assert diagnostics['continue-on-error'] is True and diagnostics['if'] == 'always()'
