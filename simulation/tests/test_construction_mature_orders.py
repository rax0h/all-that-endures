"""Ordering reuses the exact durable inputs and stops at an unverified candidate."""
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from simulation import construction_checkpoint as core
from simulation import complete_upgrade_checkpoint as old
from simulation.tests.test_construction_checkpoint import inputs, hashes
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_orders'), 'mature ordering wiring missing'
    return importlib.import_module('simulation.construction_mature_orders')


def fixture(tmp_path, monkeypatch):
    m = module()
    source, receipt = inputs(tmp_path)
    prepared, committed = tmp_path/'prepared', tmp_path/'committed'
    p = core.prepare(source, receipt, prepared, rules_id=RULES, context=CONTEXT)
    c = core.commit_prepared(prepared, committed, context=CONTEXT)
    monkeypatch.setattr(m, 'CONTEXT', CONTEXT)
    monkeypatch.setattr(m, 'PREPARED_MANIFEST_SHA', sha(prepared/'manifest.json'))
    monkeypatch.setattr(m, 'PREPARED_PRODUCER', p['producer'])
    monkeypatch.setattr(m, 'COMMITTED_PRODUCER', c['producer'])
    monkeypatch.setattr(m, 'PREPARED_FILES', p['files'])
    monkeypatch.setattr(m, 'PREPARED_PIN', p['pin'])
    monkeypatch.setattr(m, 'COMMITTED_FILES', c['files'])
    monkeypatch.setattr(m, 'COMMITTED_PIN', c['pin'])
    monkeypatch.setattr(m, 'SOURCE_CONFIG', {'rules_id': RULES})
    monkeypatch.setattr(m, 'SOURCE_WORKFLOW_SHA', None)
    return m, source, prepared, committed


def forbid(*args, **kwargs):
    raise AssertionError('ordering repeated an earlier stage or started acceptance')


def test_ordering_reuses_both_saved_inputs_and_retains_exact_world_and_aliases(tmp_path, monkeypatch):
    from ate_sim.persistence_lazy import open_lazy_world_session
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot

    m, source, prepared, committed = fixture(tmp_path, monkeypatch)
    before = hashes(prepared), hashes(committed), sha(source)
    candidate = tmp_path/'candidate'
    with monkeypatch.context() as patch:
        for name in ('prepare', 'commit_prepared', 'upgrade_lazy_snapshot'):
            patch.setattr(core, name, forbid)
        for name in ('verify_storage', 'verify_catalog', 'publish', 'publish_p5'):
            patch.setattr(old, name, forbid)
        result = m.run_orders(prepared, committed, candidate)
    assert result['stage'] == 'unverified'
    assert {p.name for p in candidate.iterdir()} == {'candidate.sqlite', 'manifest.json'}
    assert (hashes(prepared), hashes(committed), sha(source)) == before
    old.validate(candidate, context=CONTEXT)
    normal = tmp_path/'normal.sqlite'
    upgrade_lazy_snapshot(source, normal, rules_id=RULES)
    with open_lazy_world_session(candidate/'candidate.sqlite', rules_id=RULES) as a, \
            open_lazy_world_session(normal, rules_id=RULES) as b:
        assert a.detach(materialize_history=True).digest() == b.detach(materialize_history=True).digest()
        assert a.world.events[0].data['shared'] is a.skills[1, 'craft'].provenance
        assert a.skills[1, 'craft'].provenance is a.skills[2, 'craft'].provenance
    with pytest.raises(FileExistsError):
        m.run_orders(prepared, committed, candidate)


@pytest.mark.parametrize('which,field', [
    ('prepared','producer'), ('prepared','context'), ('prepared','files'),
    ('prepared','pin'), ('prepared','source_receipt'), ('prepared','streams'),
    ('committed','producer'), ('committed','context'), ('committed','files'),
    ('committed','pin'), ('committed','prepared_manifest_sha256'),
    ('committed','source_receipt'), ('committed','source_generation'),
])
def test_foreign_manifest_is_rejected_before_original_ordering(tmp_path, monkeypatch, which, field):
    m, _, prepared, committed = fixture(tmp_path, monkeypatch)
    path = (prepared if which == 'prepared' else committed)/'manifest.json'
    value = old._json(path)
    value[field] = 'foreign'
    path.write_text(json.dumps(value))
    monkeypatch.setattr(core, 'restore_orders', forbid)
    with pytest.raises(ValueError, match='lineage|configuration'):
        m.run_orders(prepared, committed, tmp_path/'candidate')
    assert not (tmp_path/'candidate').exists()


def test_configuration_mismatch_rejects_even_with_refreshed_expected_manifest_hash(tmp_path, monkeypatch):
    m, _, prepared, committed = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(m, 'SOURCE_CONFIG', {'rules_id': 'foreign'})
    monkeypatch.setattr(core, 'restore_orders', forbid)
    with pytest.raises(ValueError, match='configuration'):
        m.run_orders(prepared, committed, tmp_path/'candidate')


@pytest.mark.parametrize('condition', ['duplicate', 'rerun', 'workflow', 'branch', 'head'])
def test_duplicate_or_foreign_launch_is_rejected(monkeypatch, condition):
    m = module()
    monkeypatch.setenv('GITHUB_RUN_ID', '23')
    monkeypatch.setenv('GITHUB_SHA', 'a'*40)
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


def test_first_unique_launch_is_allowed(monkeypatch):
    m = module()
    monkeypatch.setenv('GITHUB_RUN_ID', '23')
    monkeypatch.setenv('GITHUB_SHA', 'a'*40)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    current = dict(id=23, head_sha='a'*40, path=m.WORKFLOW, head_branch=m.BRANCH)
    monkeypatch.setattr(m.artifacts, '_api', lambda *a: current)
    monkeypatch.setattr(m.artifacts, '_pages', lambda *a: [current])
    m.unique_launch()


@pytest.mark.parametrize('wrong_size', [False, True])
def test_download_pins_exact_commit_transport_and_producer(tmp_path, monkeypatch, wrong_size):
    m = module()
    monkeypatch.setattr(m, 'ROOT', tmp_path)
    def download(destination, **kwargs):
        assert destination == tmp_path/'committed'
        assert kwargs == dict(run_id=38851921152,
            workflow_sha='0acb45ef35748f7eda3f8d212c5c33c5d408be8f',
            workflow_path='.github/workflows/stage-0-5-mature-commit.yml',
            name='construction-mature-committed', job='mature-commit',
            members={'target.sqlite', 'manifest.json'}, artifact_id=12030703178,
            expected_digest='ec5dbeb0224a7bae109771b59da2bdca6eca451ebf67f1f5102fc77b91506077')
        destination.mkdir()
        return dict(archive_bytes=4332758248-int(wrong_size))
    monkeypatch.setattr(m.artifacts, 'download', download)
    if wrong_size:
        with pytest.raises(ValueError, match='archive size'): m.download_committed()
    else:
        assert m.download_committed() == (tmp_path/'committed', {'archive_bytes': 4332758248})


def main_environment(m, monkeypatch):
    monkeypatch.setenv('HARNESS_SHA', 'd'*40)
    monkeypatch.setenv('RUNTIME_SHA', m.RUNTIME_SHA)
    monkeypatch.setattr(m.subprocess, 'check_output', lambda args, **kw:
        'd'*40 if args[-1] == 'HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource, 'setrlimit', lambda *a: None)
    monkeypatch.setattr(m, 'unique_launch', lambda: None)
    monkeypatch.setattr(m, 'check_helpers', lambda: None)


@pytest.mark.parametrize('where', ['before', 'after'])
def test_disk_budget_reserves_copy_full_rollback_journal_and_margin(tmp_path, monkeypatch, where):
    m = module()
    monkeypatch.setattr(m, 'ROOT', tmp_path/'evidence')
    main_environment(m, monkeypatch)
    assert m.ORDER_FREE_BYTES >= 2*m.COMMITTED_FILES['target.sqlite']['bytes']+8*1024**3
    assert m.START_FREE_BYTES >= m.ORDER_FREE_BYTES+sum(v['bytes'] for v in m.PREPARED_FILES.values())+m.COMMITTED_FILES['target.sqlite']['bytes']+4332758248
    values = iter([m.START_FREE_BYTES-int(where == 'before'), m.ORDER_FREE_BYTES-1])
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=next(values)))
    def download():
        if where == 'before': pytest.fail('download started without transfer headroom')
        return tmp_path/'input', {}
    monkeypatch.setattr(m, 'download_prepared', download)
    monkeypatch.setattr(m, 'download_committed', download)
    monkeypatch.setattr(m, 'run_orders', forbid)
    with pytest.raises(ValueError, match='disk headroom'): m.main()


def test_post_order_diagnostic_failure_preserves_completed_bundle(tmp_path, monkeypatch):
    m, _, prepared, committed = fixture(tmp_path, monkeypatch)
    root = tmp_path/'evidence'
    monkeypatch.setattr(m, 'ROOT', root)
    main_environment(m, monkeypatch)
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=m.START_FREE_BYTES))
    monkeypatch.setattr(m, 'download_prepared', lambda: (prepared, {}))
    monkeypatch.setattr(m, 'download_committed', lambda: (committed, {}))
    write = old._write_new
    def failed(path, data):
        if Path(path).name == 'orders-summary.json': raise OSError('diagnostic failed')
        return write(path, data)
    monkeypatch.setattr(old, '_write_new', failed)
    m.main()
    assert old.validate(root/'candidate', context=CONTEXT)['stage'] == 'unverified'


@pytest.mark.parametrize('status', [0, 7, 124])
def test_one_stage_workflow_preserves_exit_status_and_mandatory_upload(status):
    import subprocess
    import yaml
    path = Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-orders.yml'
    assert path.exists(), 'mature ordering workflow missing'
    workflow = yaml.safe_load(path.read_text())
    assert set(workflow['jobs']) == {'mature-orders'}
    assert workflow['concurrency']['cancel-in-progress'] is False
    assert workflow['permissions'] == {'contents': 'read', 'actions': 'read'}
    job = workflow['jobs']['mature-orders']
    assert job['timeout-minutes'] == 360
    step = next(s for s in job['steps'] if s.get('name') == 'Restore retained mature ordering')
    script = step['run']
    assert '300m python -m simulation.construction_mature_orders' in script
    assert 'construction_mature_commit' not in script and 'construction_mature_prepare' not in script
    assert 'verify_storage' not in script and 'verify_catalog' not in script
    script = script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_orders', f"bash -c 'exit {status}'")
    script = script.replace('tee evidence/orders.log', "bash -c 'cat >/dev/null; exit 42'")
    result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], capture_output=True)
    assert result.returncode == status
    diagnostics = next(s for s in job['steps'] if s.get('name') == 'Retain diagnostics')
    assert diagnostics['if'] == 'always()' and diagnostics['continue-on-error'] is True
    upload = next(s for s in job['steps'] if s.get('name') == 'Retain ordered candidate')
    assert upload['with']['path'] == 'evidence/candidate' and 'if' not in upload
    assert upload['with']['if-no-files-found'] == 'error'
    assert upload['with']['name'] == 'construction-mature-ordered'
