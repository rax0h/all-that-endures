"""Catalog verification reuses a checked storage receipt and preserves predecessors."""
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulation import construction_checkpoint as construction
from simulation import complete_upgrade_checkpoint as old
from simulation.tests.test_construction_checkpoint import inputs, hashes
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_catalog'), 'mature catalog wiring missing'
    return importlib.import_module('simulation.construction_mature_catalog')


def fixture(tmp_path, monkeypatch):
    m = module(); source, receipt = inputs(tmp_path)
    prepared, committed, candidate = (tmp_path/name for name in ('prepared', 'committed', 'candidate'))
    construction.prepare(source, receipt, prepared, rules_id=RULES, context=CONTEXT)
    construction.commit_prepared(prepared, committed, context=CONTEXT)
    c = construction.restore_orders(prepared, committed, candidate, context=CONTEXT)
    storage = tmp_path/'storage.json'; old.verify_storage(candidate, storage, context=CONTEXT)
    monkeypatch.setattr(m, 'CONTEXT', CONTEXT)
    monkeypatch.setattr(m, 'CANDIDATE_MANIFEST_SHA', sha(candidate/'manifest.json'))
    monkeypatch.setattr(m, 'CANDIDATE_DATABASE', c['database'])
    monkeypatch.setattr(m, 'CANDIDATE_PIN', c['pin'])
    monkeypatch.setattr(m, 'SOURCE_GENERATION', c['source_generation'])
    monkeypatch.setattr(m, 'SOURCE_CONFIG', {'rules_id': RULES})
    monkeypatch.setattr(m, 'SOURCE_WORKFLOW_SHA', None)
    monkeypatch.setattr(m, 'STORAGE_RECEIPT_SHA', sha(storage))
    monkeypatch.setattr(m, 'STORAGE_RECEIPT_BYTES', storage.stat().st_size)
    return m, candidate, storage


def forbidden(*args, **kwargs): raise AssertionError('catalog verification repeated another stage')


def test_catalog_uses_original_verifier_and_exact_storage_receipt_without_repeating_work(tmp_path, monkeypatch):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    before = hashes(candidate), sha(storage)
    for name in ('prepare', 'commit_prepared', 'restore_orders', 'upgrade_lazy_snapshot'):
        monkeypatch.setattr(construction, name, forbidden)
    for name in ('verify_storage', 'publish', 'publish_p5', 'capture'):
        monkeypatch.setattr(old, name, forbidden)
    result = m.run_catalog(candidate, storage, tmp_path/'catalog.json')
    assert result == old._receipt(candidate, old._json(candidate/'manifest.json'), 'catalog-verified', storage)
    assert old._json(tmp_path/'catalog.json') == result
    assert (hashes(candidate), sha(storage)) == before
    with pytest.raises(FileExistsError): m.run_catalog(candidate, storage, tmp_path/'catalog.json')


@pytest.mark.parametrize('field', ['context', 'stage', 'database', 'pin', 'source_generation', 'source_receipt'])
def test_foreign_candidate_rejects_before_catalog_verifier(tmp_path, monkeypatch, field):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    path = candidate/'manifest.json'; value = old._json(path)
    value[field] = 'foreign'; path.write_text(json.dumps(value))
    monkeypatch.setattr(old, 'verify_catalog', forbidden)
    with pytest.raises(ValueError, match='lineage'):
        m.run_catalog(candidate, storage, tmp_path/'catalog.json')


@pytest.mark.parametrize('field', ['context', 'stage', 'database', 'manifest_sha256', 'previous_receipt_sha256'])
def test_refreshed_receipt_hash_cannot_excuse_wrong_original_authority(tmp_path, monkeypatch, field):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    value = old._json(storage); value[field] = 'foreign'; storage.write_text(json.dumps(value))
    monkeypatch.setattr(m, 'STORAGE_RECEIPT_SHA', sha(storage))
    monkeypatch.setattr(m, 'STORAGE_RECEIPT_BYTES', storage.stat().st_size)
    monkeypatch.setattr(old.copy, '_verify_catalog', forbidden)
    with pytest.raises(ValueError, match='receipt stage/lineage'):
        m.run_catalog(candidate, storage, tmp_path/'catalog.json')
    assert not (tmp_path/'catalog.json').exists()


def test_uninspected_storage_receipt_rejects_before_catalog_verification(tmp_path, monkeypatch):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    storage.write_text('{}')
    monkeypatch.setattr(old, 'verify_catalog', forbidden)
    with pytest.raises(ValueError, match='storage receipt'):
        m.run_catalog(candidate, storage, tmp_path/'catalog.json')


def test_catalog_interruption_and_receipt_failure_preserve_both_inputs(tmp_path, monkeypatch):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    before = hashes(candidate), sha(storage)
    def failed(*args): raise RuntimeError('interrupted catalog')
    with monkeypatch.context() as patch:
        patch.setattr(old.copy, '_verify_catalog', failed)
        with pytest.raises(RuntimeError, match='interrupted catalog'):
            m.run_catalog(candidate, storage, tmp_path/'catalog.json')
    assert not (tmp_path/'catalog.json').exists()
    assert (hashes(candidate), sha(storage)) == before
    def failed_write(*args): raise OSError('receipt write failure')
    with monkeypatch.context() as patch:
        patch.setattr(old, '_write_new', failed_write)
        with pytest.raises(OSError, match='receipt write failure'):
            m.run_catalog(candidate, storage, tmp_path/'catalog.json')
    assert not (tmp_path/'catalog.json').exists()
    assert (hashes(candidate), sha(storage)) == before


def test_diagnostic_output_failure_does_not_strand_catalog_receipt(tmp_path, monkeypatch):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    class Broken:
        def write(self, value): raise OSError('diagnostic output')
        def flush(self): raise OSError('diagnostic flush')
    with monkeypatch.context() as patch:
        patch.setattr(m.sys, 'stdout', Broken())
        result = m.run_catalog(candidate, storage, tmp_path/'catalog.json')
    assert result['stage'] == 'catalog-verified'


def test_changed_storage_prerequisite_during_verification_cannot_advance(tmp_path, monkeypatch):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    original = old.copy._verify_catalog
    def changed(*args):
        original(*args)
        storage.write_text('{}')
    monkeypatch.setattr(old.copy, '_verify_catalog', changed)
    with pytest.raises(ValueError, match='retained prerequisite'):
        m.run_catalog(candidate, storage, tmp_path/'catalog.json')


@pytest.mark.parametrize('condition', ['first', 'duplicate', 'rerun', 'workflow', 'branch', 'head'])
def test_catalog_launch_guard(monkeypatch, condition):
    m = module(); monkeypatch.setenv('GITHUB_RUN_ID', '23'); monkeypatch.setenv('GITHUB_SHA', 'a'*40)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2' if condition == 'rerun' else '1')
    current = dict(id=23, head_sha='a'*40, path=m.WORKFLOW, head_branch=m.BRANCH)
    if condition == 'workflow': current['path'] = 'foreign.yml'
    if condition == 'branch': current['head_branch'] = 'foreign'
    if condition == 'head': current['head_sha'] = 'b'*40
    rows = [current]
    if condition == 'duplicate': rows.append(dict(current, id=22))
    monkeypatch.setattr(m.artifacts, '_api', lambda *a: current)
    monkeypatch.setattr(m.artifacts, '_pages', lambda *a: rows)
    if condition == 'first': m.unique_launch()
    else:
        with pytest.raises(ValueError): m.unique_launch()


@pytest.mark.parametrize('wrong_size', [False, True])
def test_storage_transport_requires_exact_producer_and_small_receipt_archive(tmp_path, monkeypatch, wrong_size):
    m = module(); monkeypatch.setattr(m, 'ROOT', tmp_path)
    def download(destination, **kwargs):
        assert destination == tmp_path/'storage'
        assert kwargs == dict(run_id=38872643738,
            workflow_sha='4f1a7d7f0bd6c90704b5370f5e508669afe3b00f',
            workflow_path='.github/workflows/stage-0-5-mature-storage.yml',
            name='construction-mature-storage', job='mature-storage', members={'storage.json'},
            artifact_id=12037828504,
            expected_digest='7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4')
        return dict(archive_bytes=554-int(wrong_size))
    monkeypatch.setattr(m.artifacts, 'download', download)
    if wrong_size:
        with pytest.raises(ValueError, match='archive size'): m.download_storage()
    else:
        assert m.download_storage() == (tmp_path/'storage/storage.json', {'archive_bytes': 554})


def main_environment(m, monkeypatch):
    monkeypatch.setenv('HARNESS_SHA', 'd'*40); monkeypatch.setenv('RUNTIME_SHA', m.RUNTIME_SHA)
    monkeypatch.setattr(m.subprocess, 'check_output', lambda args, **kw:
        'd'*40 if args[-1] == 'HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource, 'setrlimit', lambda *a: None)
    monkeypatch.setattr(m, 'unique_launch', lambda: None); monkeypatch.setattr(m, 'check_helpers', lambda: None)


@pytest.mark.parametrize('where', ['before', 'after'])
def test_catalog_headroom_checked_before_verification(tmp_path, monkeypatch, where):
    m = module(); monkeypatch.setattr(m, 'ROOT', tmp_path/'evidence'); main_environment(m, monkeypatch)
    assert m.WORK_FREE_BYTES >= m.CANDIDATE_DATABASE['bytes']+8*1024**3
    assert m.START_FREE_BYTES >= m.WORK_FREE_BYTES+m.CANDIDATE_DATABASE['bytes']+4342414844+554
    values = iter([m.START_FREE_BYTES-int(where == 'before'), m.WORK_FREE_BYTES-1])
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=next(values)))
    def download():
        if where == 'before': pytest.fail('download before reserve')
        return tmp_path/'input', {}
    monkeypatch.setattr(m, 'download_candidate', download); monkeypatch.setattr(m, 'download_storage', download)
    monkeypatch.setattr(m, 'run_catalog', forbidden)
    with pytest.raises(ValueError, match='disk headroom'): m.main()


def test_post_receipt_summary_failure_cannot_suppress_catalog_upload(tmp_path, monkeypatch):
    m, candidate, storage = fixture(tmp_path, monkeypatch)
    root=tmp_path/'evidence'; monkeypatch.setattr(m, 'ROOT', root); main_environment(m, monkeypatch)
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=m.START_FREE_BYTES))
    monkeypatch.setattr(m, 'download_candidate', lambda: (candidate, {}))
    monkeypatch.setattr(m, 'download_storage', lambda: (storage, {}))
    original=old._write_new
    def failed(path, value):
        if Path(path).name=='catalog-summary.json': raise OSError('diagnostic summary')
        return original(path, value)
    monkeypatch.setattr(old, '_write_new', failed); m.main()
    assert old._json(root/'catalog/catalog.json')['stage']=='catalog-verified'


@pytest.mark.parametrize('status', [0, 7, 124])
def test_catalog_workflow_is_single_stage_with_mandatory_receipt_upload(status):
    import subprocess,yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-catalog.yml'
    assert path.exists(), 'mature catalog workflow missing'
    workflow=yaml.safe_load(path.read_text()); assert set(workflow['jobs'])=={'mature-catalog'}
    assert workflow['concurrency']['cancel-in-progress'] is False
    job=workflow['jobs']['mature-catalog']; assert job['timeout-minutes']==360
    script=next(s['run'] for s in job['steps'] if s.get('name')=='Verify retained mature catalog')
    assert '300m python -m simulation.construction_mature_catalog' in script
    assert 'construction_mature_storage' not in script and 'publish' not in script
    script=script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_catalog',f"bash -c 'exit {status}'")
    script=script.replace('tee evidence/catalog.log',"bash -c 'cat >/dev/null; exit 42'")
    result=subprocess.run(['bash','-e','-o','pipefail','-c',script],capture_output=True)
    assert result.returncode==status
    diagnostic=next(s for s in job['steps'] if s.get('name')=='Retain diagnostics')
    assert diagnostic['if']=='always()' and diagnostic['continue-on-error'] is True
    upload=next(s for s in job['steps'] if s.get('name')=='Retain catalog receipt')
    assert 'if' not in upload and upload['with']['path']=='evidence/catalog'
    assert upload['with']['name']=='construction-mature-catalog'
    assert upload['with']['if-no-files-found']=='error'
