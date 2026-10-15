"""Validation harness tests: retained candidates never certify themselves."""
import importlib
import json
from pathlib import Path
import pytest
from ate_sim import persistence_catalog_copy as copy
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, RULES, sha

CONTEXT = {'runtime_sha': 'a'*40, 'harness_sha': 'b'*40,
           'source_artifact': {'id': 17, 'run_id': 23, 'archive_sha256': 'c'*64}}


def harness():
    assert importlib.util.find_spec('simulation.complete_upgrade_checkpoint'), 'checkpoint harness missing'
    return importlib.import_module('simulation.complete_upgrade_checkpoint')


def inputs(tmp_path):
    source = legacy_lazy(tmp_path, size=8)
    receipt = tmp_path/'source.json'
    receipt.write_text(json.dumps({'schema': 1, 'stage': 'lazy', 'config': {'rules_id': RULES},
        'database': {'name': source.name, 'sha256': sha(source)}}))
    return source, receipt


def captured(tmp_path):
    source, receipt = inputs(tmp_path)
    bundle = tmp_path/'candidate'
    harness().capture(source, receipt, bundle, rules_id=RULES, context=CONTEXT)
    return source, receipt, bundle


def test_capture_stops_after_ordinals_before_any_full_verification(tmp_path, monkeypatch):
    source, receipt = inputs(tmp_path)
    before = sha(source)
    original = copy._restore_copy_ordinals
    restored = []
    def ordinals(*args):
        result = original(*args)
        restored.append(True)
        return result
    monkeypatch.setattr(copy, '_restore_copy_ordinals', ordinals)
    verify = copy.LazyRecordStore.verify_all
    def checked_verify(store):
        assert not restored, 'capture ran target verifier after ordinals'
        return verify(store)
    monkeypatch.setattr(copy.LazyRecordStore, 'verify_all', checked_verify)
    harness().capture(source, receipt, tmp_path/'candidate', rules_id=RULES, context=CONTEXT)
    assert restored == [True]
    assert sha(source) == before
    assert sorted(p.name for p in (tmp_path/'candidate').iterdir()) == ['candidate.sqlite', 'manifest.json']
    assert not (tmp_path/'complete.sqlite').exists()
    harness().validate(tmp_path/'candidate', context=CONTEXT)


def test_stages_preserve_retained_bytes_and_publish_equivalent_aliases(tmp_path):
    source, receipt, bundle = captured(tmp_path)
    h = harness()
    before = sha(bundle/'candidate.sqlite')
    storage, catalog = tmp_path/'storage.json', tmp_path/'catalog.json'
    h.verify_storage(bundle, storage, context=CONTEXT)
    h.verify_catalog(bundle, storage, catalog, context=CONTEXT)
    assert sha(bundle/'candidate.sqlite') == before
    dest, ordinary = tmp_path/'complete.sqlite', tmp_path/'ordinary.sqlite'
    h.publish(bundle, storage, catalog, dest, context=CONTEXT)
    upgrade_lazy_snapshot(source, ordinary, rules_id=RULES)
    with open_lazy_world_session(dest, rules_id=RULES) as staged, open_lazy_world_session(ordinary, rules_id=RULES) as normal:
        a, b = staged.detach(materialize_history=True), normal.detach(materialize_history=True)
        assert a.digest() == b.digest()
        assert a.skills.skills[1, 'craft'].provenance is a.skills.skills[2, 'craft'].provenance
    assert sha(bundle/'candidate.sqlite') == before
    with pytest.raises(FileExistsError):
        h.publish(bundle, storage, catalog, dest, context=CONTEXT)


def test_storage_failure_keeps_candidate_and_does_not_emit_receipt(tmp_path, monkeypatch):
    _, _, bundle = captured(tmp_path)
    before = sha(bundle/'candidate.sqlite')
    def fail(*a): raise RuntimeError('interrupted')
    monkeypatch.setattr(copy.LazyRecordStore, 'verify_all', fail)
    with pytest.raises(RuntimeError, match='interrupted'):
        harness().verify_storage(bundle, tmp_path/'storage.json', context=CONTEXT)
    assert not (tmp_path/'storage.json').exists()
    assert sha(bundle/'candidate.sqlite') == before


@pytest.mark.parametrize('field', ['runtime_sha', 'harness_sha', 'source_artifact'])
def test_foreign_lineage_rejected(tmp_path, field):
    _, _, bundle = captured(tmp_path)
    wrong = dict(CONTEXT, **{field: 'foreign'})
    with pytest.raises(ValueError):
        harness().verify_storage(bundle, tmp_path/'storage.json', context=wrong)


def test_database_corruption_rejected_before_receipt(tmp_path):
    _, _, bundle = captured(tmp_path)
    with (bundle/'candidate.sqlite').open('ab') as f: f.write(b'corruption')
    with pytest.raises(ValueError, match='database'):
        harness().verify_storage(bundle, tmp_path/'storage.json', context=CONTEXT)


def test_receipts_cannot_be_swapped_or_skipped(tmp_path):
    _, _, bundle = captured(tmp_path)
    h = harness()
    storage = tmp_path/'storage.json'
    h.verify_storage(bundle, storage, context=CONTEXT)
    with pytest.raises(ValueError):
        h.publish(bundle, storage, storage, tmp_path/'complete.sqlite', context=CONTEXT)
    data = json.loads(storage.read_text()); data['manifest_sha256'] = '0'*64
    storage.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        h.verify_catalog(bundle, storage, tmp_path/'catalog.json', context=CONTEXT)


@pytest.mark.parametrize('field,value', [('pin', None), ('source_generation', -1),
    ('rules_id', ''), ('source_receipt_sha256', '0'*64)])
def test_malformed_manifest_rejected(tmp_path, field, value):
    _, _, bundle = captured(tmp_path)
    path = bundle/'manifest.json'
    data = json.loads(path.read_text()); data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError): harness().validate(bundle, context=CONTEXT)


def test_catalog_interruption_can_resume_without_repeating_storage(tmp_path, monkeypatch):
    _, _, bundle = captured(tmp_path)
    h = harness(); storage, catalog = tmp_path/'storage.json', tmp_path/'catalog.json'
    h.verify_storage(bundle, storage, context=CONTEXT)
    original = copy._verify_catalog
    def fail(*a): raise RuntimeError('interrupted catalog')
    monkeypatch.setattr(copy, '_verify_catalog', fail)
    with pytest.raises(RuntimeError): h.verify_catalog(bundle, storage, catalog, context=CONTEXT)
    assert storage.exists() and not catalog.exists()
    monkeypatch.setattr(copy, '_verify_catalog', original)
    monkeypatch.setattr(copy.LazyRecordStore, 'verify_all', lambda *a: pytest.fail('repeated storage'))
    h.verify_catalog(bundle, storage, catalog, context=CONTEXT)
    h.publish(bundle, storage, catalog, tmp_path/'complete.sqlite', context=CONTEXT)


def test_capture_ordinal_failure_never_emits_bundle(tmp_path, monkeypatch):
    source, receipt = inputs(tmp_path); before = sha(source)
    def fail(*a): raise RuntimeError('ordinal fault')
    monkeypatch.setattr(copy, '_restore_copy_ordinals', fail)
    with pytest.raises(RuntimeError):
        harness().capture(source, receipt, tmp_path/'candidate', rules_id=RULES, context=CONTEXT)
    assert not (tmp_path/'candidate').exists() and sha(source) == before


def test_fresh_process_cli_stages(tmp_path):
    import os, subprocess, sys
    source, receipt = inputs(tmp_path)
    context = tmp_path/'context.json'; context.write_text(json.dumps(CONTEXT))
    bundle = tmp_path/'candidate'; storage = tmp_path/'storage.json'; catalog = tmp_path/'catalog.json'
    def run(stage, *args):
        result = subprocess.run([sys.executable, '-m', 'simulation.complete_upgrade_checkpoint', stage,
            '--context', str(context), '--bundle', str(bundle), *map(str, args)],
            env=dict(os.environ, PYTHONPATH='.:simulation'), capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    run('capture', '--source', source, '--source-receipt', receipt, '--rules-id', RULES)
    assert bundle.exists(), 'CLI must actually execute capture'
    run('storage', '--receipt', storage)
    run('catalog', '--storage-receipt', storage, '--receipt', catalog)
    run('publish', '--storage-receipt', storage, '--catalog-receipt', catalog,
        '--destination', tmp_path/'complete.sqlite')
    with open_lazy_world_session(tmp_path/'complete.sqlite', rules_id=RULES) as session:
        assert session.detach(materialize_history=True).skills.skills[1, 'craft'].provenance == list(range(8))


def test_p5_bridge_emits_normal_receipt_and_exact_continuation(tmp_path, monkeypatch):
    import persistence_p5_long_validation as p5
    from ate_sim import persistence_complete_format as complete
    h = harness(); workdir = tmp_path/'p5'
    config = dict(rules_id=RULES, product_sha='original-source', workflow_sha='source-workflow', complete_format=True)
    p5.run(843000, [1, 2], 0, workdir, **config, stop_after='lazy')
    bundle, storage, catalog = tmp_path/'candidate', tmp_path/'storage.json', tmp_path/'catalog.json'
    h.capture(workdir/'p5-long-lazy.sqlite', workdir/'checkpoint.json', bundle, rules_id=RULES, context=CONTEXT)
    h.verify_storage(bundle, storage, context=CONTEXT)
    h.verify_catalog(bundle, storage, catalog, context=CONTEXT)
    monkeypatch.setattr(complete, 'upgrade_lazy_snapshot', lambda *a, **kw: pytest.fail('repeated conversion'))
    h.publish_p5(bundle, storage, catalog, workdir, context=CONTEXT, workflow_sha='harness-workflow')
    receipt = json.loads((workdir/'checkpoint.json').read_text())
    assert receipt['stage'] == 'complete' and receipt['config']['product_sha'] == CONTEXT['runtime_sha']
    assert receipt['source_checkpoint']['product_sha'] == 'original-source'
    result = p5.run(843000, [1, 2], 0, workdir, RULES, CONTEXT['runtime_sha'], 'harness-workflow',
                    complete_format=True, resume_from='complete')
    assert result['passed']
    assert all(result['p4'][str(y)]['matches_control'] for y in (1, 2))
    assert result['restore_artifact']['year'] == 2


@pytest.mark.parametrize('stage', ['storage', 'catalog'])
def test_receipt_write_failure_preserves_prior_evidence(tmp_path, monkeypatch, stage):
    _, _, bundle = captured(tmp_path); h = harness()
    storage, catalog = tmp_path/'storage.json', tmp_path/'catalog.json'
    if stage == 'catalog': h.verify_storage(bundle, storage, context=CONTEXT)
    before = sha(bundle/'candidate.sqlite')
    def fail(*a): raise OSError('receipt disk failure')
    monkeypatch.setattr(h, '_write_new', fail)
    with pytest.raises(OSError):
        if stage == 'storage': h.verify_storage(bundle, storage, context=CONTEXT)
        else: h.verify_catalog(bundle, storage, catalog, context=CONTEXT)
    assert sha(bundle/'candidate.sqlite') == before
    assert storage.exists() == (stage == 'catalog')
    assert not catalog.exists()


def test_publish_race_and_fault_preserve_candidate_and_receipts(tmp_path, monkeypatch):
    _, _, bundle = captured(tmp_path); h = harness()
    storage, catalog = tmp_path/'storage.json', tmp_path/'catalog.json'
    h.verify_storage(bundle, storage, context=CONTEXT); h.verify_catalog(bundle, storage, catalog, context=CONTEXT)
    hashes = [sha(p) for p in (bundle/'candidate.sqlite', storage, catalog)]
    destination = tmp_path/'complete.sqlite'
    original = h._publish_private_cold_file
    def race(private, dest):
        dest.write_bytes(b'other writer')
        original(private, dest)
    monkeypatch.setattr(h, '_publish_private_cold_file', race)
    with pytest.raises(FileExistsError): h.publish(bundle, storage, catalog, destination, context=CONTEXT)
    assert destination.read_bytes() == b'other writer'
    assert [sha(p) for p in (bundle/'candidate.sqlite', storage, catalog)] == hashes


def test_original_verifier_rejects_corrupt_payload_even_with_updated_transport_hash(tmp_path):
    import sqlite3
    _, _, bundle = captured(tmp_path); h = harness()
    database = bundle/'candidate.sqlite'
    with sqlite3.connect(database) as db:
        db.execute("UPDATE records SET payload=? WHERE rowid=(SELECT min(rowid) FROM records)", (b'invalid',))
    path = bundle/'manifest.json'; manifest=json.loads(path.read_text())
    manifest['database']['sha256']=sha(database); manifest['database']['bytes']=database.stat().st_size
    path.write_text(json.dumps(manifest))
    from ate_sim.incremental_store import StoreIntegrityError
    with pytest.raises(StoreIntegrityError): h.verify_storage(bundle, tmp_path/'storage.json', context=CONTEXT)
    assert not (tmp_path/'storage.json').exists()
