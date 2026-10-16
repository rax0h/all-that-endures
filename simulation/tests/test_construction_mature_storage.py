"""Storage verification consumes the saved ordered candidate and emits one receipt."""
import importlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from ate_sim.incremental_store import StoreIntegrityError
from simulation import construction_checkpoint as construction
from simulation import complete_upgrade_checkpoint as old
from simulation.tests.test_construction_checkpoint import inputs, hashes
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_storage'), 'mature storage wiring missing'
    return importlib.import_module('simulation.construction_mature_storage')


def fixture(tmp_path, monkeypatch):
    m = module()
    source, receipt = inputs(tmp_path)
    prepared, committed, candidate = (tmp_path/name for name in ('prepared', 'committed', 'candidate'))
    construction.prepare(source, receipt, prepared, rules_id=RULES, context=CONTEXT)
    construction.commit_prepared(prepared, committed, context=CONTEXT)
    c = construction.restore_orders(prepared, committed, candidate, context=CONTEXT)
    monkeypatch.setattr(m, 'CONTEXT', CONTEXT)
    monkeypatch.setattr(m, 'CANDIDATE_MANIFEST_SHA', sha(candidate/'manifest.json'))
    monkeypatch.setattr(m, 'CANDIDATE_DATABASE', c['database'])
    monkeypatch.setattr(m, 'CANDIDATE_PIN', c['pin'])
    monkeypatch.setattr(m, 'SOURCE_GENERATION', c['source_generation'])
    monkeypatch.setattr(m, 'SOURCE_CONFIG', {'rules_id': RULES})
    monkeypatch.setattr(m, 'SOURCE_WORKFLOW_SHA', None)
    return m, candidate


def forbidden(*args, **kwargs):
    raise AssertionError('storage verification invoked another stage')


def test_storage_runs_original_verifier_preserves_candidate_and_emits_exact_receipt(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch)
    before = hashes(candidate)
    receipt = tmp_path/'storage.json'
    for name in ('prepare', 'commit_prepared', 'restore_orders', 'upgrade_lazy_snapshot'):
        monkeypatch.setattr(construction, name, forbidden)
    for name in ('verify_catalog', 'publish', 'publish_p5', 'capture'):
        monkeypatch.setattr(old, name, forbidden)
    result = m.run_storage(candidate, receipt)
    assert result == old._receipt(candidate, old._json(candidate/'manifest.json'), 'storage-verified')
    assert old._json(receipt) == result
    assert hashes(candidate) == before
    with pytest.raises(FileExistsError): m.run_storage(candidate, receipt)


@pytest.mark.parametrize('field', ['context', 'stage', 'database', 'pin', 'source_generation', 'source_receipt'])
def test_foreign_candidate_is_rejected_before_verification(tmp_path, monkeypatch, field):
    m, candidate = fixture(tmp_path, monkeypatch)
    path = candidate/'manifest.json'
    value = old._json(path); value[field] = 'foreign'; path.write_text(json.dumps(value))
    monkeypatch.setattr(old, 'verify_storage', forbidden)
    with pytest.raises(ValueError, match='lineage'):
        m.run_storage(candidate, tmp_path/'storage.json')
    assert not (tmp_path/'storage.json').exists()


def test_foreign_source_configuration_rejects_before_verification(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(m, 'SOURCE_CONFIG', {'rules_id': 'foreign'})
    monkeypatch.setattr(old, 'verify_storage', forbidden)
    with pytest.raises(ValueError, match='configuration'):
        m.run_storage(candidate, tmp_path/'storage.json')


def test_logical_corruption_cannot_be_excused_by_refreshed_transport_hashes(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch)
    database = candidate/'candidate.sqlite'
    with sqlite3.connect(database) as db:
        db.execute('UPDATE records SET payload=? WHERE rowid=(SELECT min(rowid) FROM records)', (b'invalid',))
    path = candidate/'manifest.json'; manifest = old._json(path)
    manifest['database']['sha256'] = sha(database)
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(m, 'CANDIDATE_DATABASE', manifest['database'])
    monkeypatch.setattr(m, 'CANDIDATE_MANIFEST_SHA', sha(path))
    before = hashes(candidate)
    with pytest.raises((StoreIntegrityError, ValueError)):
        m.run_storage(candidate, tmp_path/'storage.json')
    assert not (tmp_path/'storage.json').exists() and hashes(candidate) == before


def test_storage_interruption_never_emits_receipt_or_changes_candidate(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch); before = hashes(candidate)
    def failed(*a): raise RuntimeError('interrupted storage')
    monkeypatch.setattr(old.copy.LazyRecordStore, 'verify_all', failed)
    with pytest.raises(RuntimeError, match='interrupted storage'):
        m.run_storage(candidate, tmp_path/'storage.json')
    assert not (tmp_path/'storage.json').exists() and hashes(candidate) == before


def test_receipt_write_failure_preserves_candidate(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch); before = hashes(candidate)
    def failed(*a): raise OSError('receipt disk failure')
    monkeypatch.setattr(old, '_write_new', failed)
    with pytest.raises(OSError, match='receipt disk failure'):
        m.run_storage(candidate, tmp_path/'storage.json')
    assert not (tmp_path/'storage.json').exists() and hashes(candidate) == before


def test_broken_diagnostic_output_cannot_strand_a_completed_receipt(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch)
    class Broken:
        def write(self, text): raise OSError('diagnostic output failed')
        def flush(self): raise OSError('diagnostic flush failed')
    with monkeypatch.context() as patch:
        patch.setattr(m.sys, 'stdout', Broken())
        result = m.run_storage(candidate, tmp_path/'storage.json')
    assert result['stage'] == 'storage-verified'
    assert old._json(tmp_path/'storage.json') == result


@pytest.mark.parametrize('condition', ['duplicate', 'rerun', 'workflow', 'branch', 'head'])
def test_duplicate_or_foreign_storage_launch_is_rejected(monkeypatch, condition):
    m = module()
    monkeypatch.setenv('GITHUB_RUN_ID', '23'); monkeypatch.setenv('GITHUB_SHA', 'a'*40)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2' if condition == 'rerun' else '1')
    current = dict(id=23, head_sha='a'*40, path=m.WORKFLOW, head_branch=m.BRANCH)
    if condition == 'workflow': current['path'] = 'foreign.yml'
    if condition == 'branch': current['head_branch'] = 'foreign'
    if condition == 'head': current['head_sha'] = 'b'*40
    rows = [current]
    if condition == 'duplicate': rows.append(dict(current, id=22))
    monkeypatch.setattr(m.artifacts, '_api', lambda *a: current)
    monkeypatch.setattr(m.artifacts, '_pages', lambda *a: rows)
    with pytest.raises(ValueError): m.unique_launch()


@pytest.mark.parametrize('wrong_size', [False, True])
def test_candidate_download_requires_exact_transport_and_producer(tmp_path, monkeypatch, wrong_size):
    m = module(); monkeypatch.setattr(m, 'ROOT', tmp_path)
    def download(destination, **kwargs):
        assert destination == tmp_path/'candidate'
        assert kwargs == dict(run_id=38867766111,
            workflow_sha='8b8c108f032f1e6d58339cc436310402b40a10ce',
            workflow_path='.github/workflows/stage-0-5-mature-orders.yml',
            name='construction-mature-ordered', job='mature-orders',
            members={'candidate.sqlite', 'manifest.json'}, artifact_id=12032507300,
            expected_digest='b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4')
        return dict(archive_bytes=4342414844-int(wrong_size))
    monkeypatch.setattr(m.artifacts, 'download', download)
    if wrong_size:
        with pytest.raises(ValueError, match='archive size'): m.download_candidate()
    else:
        assert m.download_candidate() == (tmp_path/'candidate', {'archive_bytes': 4342414844})


def main_environment(m, monkeypatch):
    monkeypatch.setenv('HARNESS_SHA', 'd'*40); monkeypatch.setenv('RUNTIME_SHA', m.RUNTIME_SHA)
    monkeypatch.setattr(m.subprocess, 'check_output', lambda args, **kw:
        'd'*40 if args[-1] == 'HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource, 'setrlimit', lambda *a: None)
    monkeypatch.setattr(m, 'unique_launch', lambda: None)
    monkeypatch.setattr(m, 'check_helpers', lambda: None)


@pytest.mark.parametrize('where', ['before', 'after'])
def test_disk_reserve_checks_transfer_and_verifier_scratch_before_work(tmp_path, monkeypatch, where):
    m = module(); monkeypatch.setattr(m, 'ROOT', tmp_path/'evidence')
    main_environment(m, monkeypatch)
    assert m.WORK_FREE_BYTES >= m.CANDIDATE_DATABASE['bytes']+8*1024**3
    assert m.START_FREE_BYTES >= m.WORK_FREE_BYTES+m.CANDIDATE_DATABASE['bytes']+4342414844
    values = iter([m.START_FREE_BYTES-int(where == 'before'), m.WORK_FREE_BYTES-1])
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=next(values)))
    def download():
        if where == 'before': pytest.fail('download without required headroom')
        return tmp_path/'candidate', {}
    monkeypatch.setattr(m, 'download_candidate', download)
    monkeypatch.setattr(m, 'run_storage', forbidden)
    with pytest.raises(ValueError, match='disk headroom'): m.main()


def test_summary_failure_does_not_suppress_completed_storage_receipt(tmp_path, monkeypatch):
    m, candidate = fixture(tmp_path, monkeypatch)
    root = tmp_path/'evidence'; monkeypatch.setattr(m, 'ROOT', root)
    main_environment(m, monkeypatch)
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=m.START_FREE_BYTES))
    monkeypatch.setattr(m, 'download_candidate', lambda: (candidate, {}))
    write = old._write_new
    def failed(path, value):
        if Path(path).name == 'storage-summary.json': raise OSError('summary failure')
        return write(path, value)
    monkeypatch.setattr(old, '_write_new', failed)
    m.main()
    assert old._json(root/'storage/storage.json')['stage'] == 'storage-verified'


@pytest.mark.parametrize('status', [0, 7, 124])
def test_storage_workflow_runs_only_storage_and_preserves_exit_status(status):
    import subprocess
    import yaml
    path = Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-storage.yml'
    assert path.exists(), 'mature storage workflow missing'
    workflow = yaml.safe_load(path.read_text())
    assert set(workflow['jobs']) == {'mature-storage'}
    assert workflow['concurrency']['cancel-in-progress'] is False
    job = workflow['jobs']['mature-storage']; assert job['timeout-minutes'] == 360
    script = next(s['run'] for s in job['steps'] if s.get('name') == 'Verify retained mature storage')
    assert '300m python -m simulation.construction_mature_storage' in script
    assert 'mature_orders' not in script and 'verify_catalog' not in script
    script = script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_storage', f"bash -c 'exit {status}'")
    script = script.replace('tee evidence/storage.log', "bash -c 'cat >/dev/null; exit 42'")
    result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], capture_output=True)
    assert result.returncode == status
    diagnostics = next(s for s in job['steps'] if s.get('name') == 'Retain diagnostics')
    assert diagnostics['if'] == 'always()' and diagnostics['continue-on-error'] is True
    upload = next(s for s in job['steps'] if s.get('name') == 'Retain storage receipt')
    assert 'if' not in upload and upload['with']['path'] == 'evidence/storage'
    assert upload['with']['name'] == 'construction-mature-storage'
    assert upload['with']['if-no-files-found'] == 'error'
