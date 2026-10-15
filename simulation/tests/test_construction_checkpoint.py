"""Construction stages retain work before commit and before order restoration."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import pytest
from ate_sim import persistence_catalog_copy as copy
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation import complete_upgrade_checkpoint as old
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, RULES, sha
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT


def api():
    assert importlib.util.find_spec('simulation.construction_checkpoint'), 'construction checkpoint implementation missing'
    return importlib.import_module('simulation.construction_checkpoint')


def inputs(tmp_path):
    from ate_sim.core import Household, Event, Layer
    def configure(world):
        world.households[1] = Household(1, 1, members=[1, 2, 1, 3])
        shared = world.skills.skills[1, 'craft'].provenance
        world.events.extend((Event(1, 0, 'probe', Layer.SOCIETY, data={'shared': shared}),
                             Event(2, 0, 'probe', Layer.SOCIETY, data={'shared': shared})))
        world.event_ids.update((1, 2)); world.next_event = 3
    source = legacy_lazy(tmp_path, size=8, configure=configure)
    receipt = tmp_path/'source.json'
    receipt.write_text(json.dumps({'schema': 1, 'stage': 'lazy', 'config': {'rules_id': RULES},
        'database': {'name': source.name, 'sha256': sha(source)}}))
    return source, receipt


def prepared(tmp_path):
    source, receipt = inputs(tmp_path)
    bundle = tmp_path/'prepared'
    api().prepare(source, receipt, bundle, rules_id=RULES, context=CONTEXT)
    return source, receipt, bundle


def hashes(bundle):
    return {p.name: sha(p) for p in bundle.iterdir()}


def test_preparation_survives_cleanup_without_committing(tmp_path, monkeypatch):
    source, receipt = inputs(tmp_path); before = sha(source)
    original = copy.LazyRecordStore.commit
    def forbid_target(store, *args, **kwargs):
        assert store.path.name != 'destination.sqlite', 'preparation reached target commit'
        return original(store, *args, **kwargs)
    monkeypatch.setattr(copy.LazyRecordStore, 'commit', forbid_target)
    bundle = tmp_path/'prepared'
    api().prepare(source, receipt, bundle, rules_id=RULES, context=CONTEXT)
    manifest = api().validate_prepared(bundle, context=CONTEXT)
    assert manifest['stage'] == 'prepared'
    assert set(manifest['streams']) == {'ordinary','versions','catalog','dependencies','identity','orders','states'}
    assert set(hashes(bundle)) == {'target.sqlite','spool.sqlite','manifest.json'}
    assert sha(source) == before
    assert not list(tmp_path.glob('.ate-catalog-copy-*'))
    assert not list(tmp_path.glob('.construction-*'))
    # Retained files are closed and independently usable after converter cleanup.
    with sqlite3.connect(bundle/'spool.sqlite') as db:
        for descriptor in manifest['streams'].values():
            assert db.execute('SELECT count(*) FROM replay_rows WHERE stream=?', (descriptor['stream'],)).fetchone()[0] == descriptor['count']


@pytest.mark.parametrize('field,value', [('stage','committed'),('source_generation',True),
    ('pin',None),('streams',{}),('commit','not-hex'),('producer',{})])
def test_prepared_manifest_rejects_malformed_authority(tmp_path, field, value):
    _, _, bundle = prepared(tmp_path)
    path = bundle/'manifest.json'; m = old._json(path); m[field] = value
    path.write_text(json.dumps(m))
    with pytest.raises((ValueError, StoreIntegrityError, TypeError)):
        api().validate_prepared(bundle, context=CONTEXT)


@pytest.mark.parametrize('corruption',['payload','missing','extra','count','adapter','seal'])
def test_corrupt_stream_cannot_advance_even_with_refreshed_file_hash(tmp_path, corruption):
    _, _, bundle = prepared(tmp_path)
    manifest = old._json(bundle/'manifest.json'); desc = manifest['streams']['versions']
    with sqlite3.connect(bundle/'spool.sqlite') as db:
        if corruption == 'payload': db.execute("UPDATE replay_rows SET payload=x'00' WHERE stream=? AND ordinal=0", (desc['stream'],))
        elif corruption == 'missing': db.execute('DELETE FROM replay_rows WHERE stream=? AND ordinal=0', (desc['stream'],))
        elif corruption == 'extra': db.execute('INSERT INTO replay_rows SELECT stream,999999,payload,checksum FROM replay_rows WHERE stream=? AND ordinal=0', (desc['stream'],))
    if corruption == 'count': desc['count'] = True
    elif corruption == 'adapter': desc['adapter'] = 'identity'
    elif corruption == 'seal': desc['seal'] = '0'*64
    manifest['files']['spool.sqlite'] = {'sha256': sha(bundle/'spool.sqlite'), 'bytes': (bundle/'spool.sqlite').stat().st_size}
    (bundle/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises((ValueError, StoreIntegrityError)):
        api().commit_prepared(bundle, tmp_path/'committed', context=CONTEXT)
    assert not (tmp_path/'committed').exists()


def test_commit_and_orders_produce_equivalent_existing_candidate(tmp_path, monkeypatch):
    source, receipt, prep = prepared(tmp_path); h = api(); before = hashes(prep)
    original = upgrade_lazy_snapshot
    # No later stage may reconstruct preparation.
    monkeypatch.setattr(h, 'upgrade_lazy_snapshot', lambda *a, **k: pytest.fail('repeated preparation'))
    committed, candidate = tmp_path/'committed', tmp_path/'candidate'
    h.commit_prepared(prep, committed, context=CONTEXT)
    committed_before = hashes(committed)
    h.restore_orders(prep, committed, candidate, context=CONTEXT)
    assert hashes(prep) == before and hashes(committed) == committed_before
    old.validate(candidate, context=CONTEXT)
    storage, catalog = tmp_path/'storage.json', tmp_path/'catalog.json'
    old.verify_storage(candidate, storage, context=CONTEXT)
    old.verify_catalog(candidate, storage, catalog, context=CONTEXT)
    destination = tmp_path/'complete.sqlite'
    old.publish(candidate, storage, catalog, destination, context=CONTEXT)
    normal = tmp_path/'normal.sqlite'; original(source, normal, rules_id=RULES)
    with open_lazy_world_session(destination, rules_id=RULES) as a, open_lazy_world_session(normal, rules_id=RULES) as b:
        assert a.detach(materialize_history=True).digest() == b.detach(materialize_history=True).digest()
        assert a.world.events[0].data['shared'] is a.skills[1, 'craft'].provenance
        assert a.skills[1, 'craft'].provenance is a.skills[2, 'craft'].provenance
    for operation, args in [(h.commit_prepared,(prep,committed)), (h.restore_orders,(prep,committed,candidate))]:
        with pytest.raises(FileExistsError): operation(*args, context=CONTEXT)


@pytest.mark.parametrize('phase',['before_transaction','during_version_writes','after_commit'])
def test_commit_interruption_preserves_preparation_and_retry_skips_it(tmp_path, monkeypatch, phase):
    _, _, prep = prepared(tmp_path); before = hashes(prep); h = api()
    original_open = h.old._open
    def opening(*args):
        store = original_open(*args)
        if '.construction-' in str(store.path):
            def fault(at):
                if at == phase: raise RuntimeError('interrupted commit')
            store._phase_hook = fault
        return store
    with monkeypatch.context() as patch:
        patch.setattr(h.old, '_open', opening)
        with pytest.raises(RuntimeError, match='interrupted commit'):
            h.commit_prepared(prep, tmp_path/'committed', context=CONTEXT)
    assert hashes(prep) == before and not (tmp_path/'committed').exists()
    monkeypatch.setattr(h, 'upgrade_lazy_snapshot', lambda *a, **k: pytest.fail('repeated preparation'))
    h.commit_prepared(prep, tmp_path/'committed', context=CONTEXT)


def test_order_interruption_preserves_both_earlier_stages(tmp_path, monkeypatch):
    _, _, prep = prepared(tmp_path); h = api(); committed = tmp_path/'committed'
    h.commit_prepared(prep, committed, context=CONTEXT)
    before = hashes(prep), hashes(committed)
    original = copy._restore_copy_ordinals
    def fault(*args):
        original(*args)
        raise RuntimeError('interrupted orders')
    with monkeypatch.context() as patch:
        patch.setattr(copy,'_restore_copy_ordinals',fault)
        with pytest.raises(RuntimeError): h.restore_orders(prep,committed,tmp_path/'candidate',context=CONTEXT)
    assert (hashes(prep), hashes(committed)) == before
    assert not (tmp_path/'candidate').exists()
    monkeypatch.setattr(h,'commit_prepared',lambda *a,**k:pytest.fail('repeated commit'))
    h.restore_orders(prep,committed,tmp_path/'candidate',context=CONTEXT)


def test_foreign_preparation_cannot_supply_order_inputs(tmp_path):
    _, _, prep = prepared(tmp_path); h = api(); committed = tmp_path/'committed'
    h.commit_prepared(prep, committed, context=CONTEXT)
    otherdir = tmp_path/'other'; otherdir.mkdir()
    _, _, other = prepared(otherdir)
    with pytest.raises(ValueError): h.restore_orders(other,committed,tmp_path/'candidate',context=CONTEXT)


@pytest.mark.parametrize('stream',['orders','states'])
def test_invalid_order_commitment_rejects_before_commit_attempt(tmp_path,monkeypatch,stream):
    _,_,prep=prepared(tmp_path);h=api()
    path=prep/'manifest.json';manifest=old._json(path)
    manifest['streams'][stream]['seal']='0'*64;path.write_text(json.dumps(manifest))
    attempted=[]
    original=copy.LazyRecordStore.commit
    def observe(*args,**kwargs):
        attempted.append(True);return original(*args,**kwargs)
    monkeypatch.setattr(copy.LazyRecordStore,'commit',observe)
    with pytest.raises(StoreIntegrityError):h.commit_prepared(prep,tmp_path/'committed',context=CONTEXT)
    assert not attempted and not (tmp_path/'committed').exists()


def test_receipt_failure_keeps_source_and_previous_stages(tmp_path, monkeypatch):
    source, _, prep = prepared(tmp_path); h = api(); before = sha(source), hashes(prep)
    with monkeypatch.context() as patch:
        patch.setattr(old,'_write_new',lambda *a: (_ for _ in ()).throw(OSError('disk full')))
        with pytest.raises(OSError): h.commit_prepared(prep,tmp_path/'committed',context=CONTEXT)
    assert (sha(source), hashes(prep)) == before
    assert not (tmp_path/'committed').exists()


def test_cli_runs_each_construction_stage_in_a_fresh_process(tmp_path):
    import os, subprocess, sys
    source, receipt = inputs(tmp_path); context = tmp_path/'context.json'
    context.write_text(json.dumps(CONTEXT)); prep, committed, candidate = [tmp_path/name for name in ('prepared','committed','candidate')]
    for stage,args in [('prepare',['--source',source,'--source-receipt',receipt,'--rules-id',RULES,'--bundle',prep]),
        ('commit',['--prepared',prep,'--bundle',committed]),
        ('orders',['--prepared',prep,'--committed',committed,'--bundle',candidate])]:
        p = subprocess.run([sys.executable,'-m','simulation.construction_checkpoint',stage,'--context',str(context),*map(str,args)],
            env=dict(os.environ,PYTHONPATH='.:simulation'),capture_output=True,text=True)
        assert p.returncode == 0, p.stdout+p.stderr
    old.validate(candidate,context=CONTEXT)
