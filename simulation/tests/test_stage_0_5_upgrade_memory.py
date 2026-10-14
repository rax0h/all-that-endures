"""Conversion checks survive removal of the disposable catalog freeze."""
import hashlib
import importlib
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from ate_sim.persistence_adapters import WorldCodec
from simulation.tests.test_stage_0_5_final_catalog_copy import opened, sha, RULES, module
from simulation.tests.test_stage_0_5_final_legacy_event_copy import event_source


def catalog():
    return importlib.import_module('ate_sim.persistence_lazy_identity_catalog')


def test_complete_conversion_matches_pre_repair_authority_and_world(tmp_path):
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    from ate_sim.persistence_lazy import open_lazy_world_session
    source = event_source(tmp_path, share_history=True)
    before = sha(source)
    destination = tmp_path / 'complete.sqlite'
    upgrade_lazy_snapshot(source, destination, rules_id=RULES)
    assert sha(source) == before
    with opened(destination) as store:
        pin = store.capture_pin()
        h = hashlib.sha256()
        for namespace in catalog().CATALOG_NAMESPACES:
            for key in sorted(store.iter_keys(pin, namespace), key=store.codec.encode):
                value = store.read_version(pin, namespace, key, expected_record_schema=1).value
                h.update(store.codec.encode((namespace, key, value)))
        store.release_pin(pin)
        # Captured on the unmodified90a0550 converter at the same generation.
        assert h.hexdigest() == '5f74ee4b2cbe12a33326ac6212bdf0f758d652304e3fbd12cad3be97cdec65d4'
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        assert session.world.events[0].data['a'] is session.skills[1, 'craft'].provenance
        assert session.skills[1, 'craft'].provenance is session.skills[2, 'craft'].provenance
        assert session.detach(materialize_history=True).digest() == 'e72e6d203237ac5cac9f15d616e995b2af820e8e637349599624053694913e2b'


def test_validation_only_does_not_freeze_output_catalog(monkeypatch):
    codec = WorldCodec(identity_links_recorded=True)
    def forbidden(*args, **kwargs):
        raise AssertionError('unused catalog frozen')
    monkeypatch.setattr(catalog().ParticipantDelta, 'freeze', forbidden)
    owners = (VersionChange('world.people', 1, {'body': []}),)
    placements = (IdentityOccurrenceChange('world.people', 1, (), 1),)
    catalog().validate_initial_catalog_inputs(codec, owners, placements, next_incarnation_id=1000, generation=1)


@pytest.mark.parametrize('corruption', ['duplicate-owner', 'duplicate-path', 'missing-owner', 'unallocated',
    'physical-placement', 'auxiliary-body', 'hash-collision', 'removed-by-normalization'])
def test_invalid_source_rejects_before_normalization_and_preserves_source(tmp_path, monkeypatch, corruption):
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    source = event_source(tmp_path, share_history=True)
    before = sha(source)
    destination = tmp_path / 'invalid.sqlite'
    original = module()._owner_sources
    cat = catalog()
    if corruption in ('duplicate-path', 'missing-owner', 'unallocated', 'removed-by-normalization'):
        original_validate = getattr(cat, 'validate_initial_catalog_inputs', None)
        assert original_validate is not None, 'source validation-only API missing'
        def validate(codec, owners, placements, **kwargs):
            placements = list(placements)
            first = placements[0]
            if corruption == 'duplicate-path': placements.append(first)
            elif corruption == 'missing-owner': placements.append(replace(first, owner_key='missing'))
            elif corruption == 'unallocated': placements[0] = replace(first, incarnation_id=kwargs['next_incarnation_id'])
            else:
                # This descendant is removed when the Event body becomes a ref.
                p = next(p for p in placements if p.owner_namespace == 'world.events' and len(p.occurrence_path) > 1)
                placements.append(p)
            return original_validate(codec, owners, placements, **kwargs)
        monkeypatch.setattr(module(), 'validate_initial_catalog_inputs', validate)
    elif corruption == 'hash-collision':
        monkeypatch.setattr(cat, 'path_hash', lambda *args: bytes(32))
    else:
        def owners(store, pin):
            versions, ordinary = original(store, pin)
            if corruption == 'duplicate-owner': versions.append(versions[0])
            else:
                from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, HistoryReference
                if corruption == 'auxiliary-body':
                    i = next(i for i, v in enumerate(versions) if v.namespace == PAGE_NAMESPACE)
                    versions[i] = replace(versions[i], value={'invalid-body': 1})
                else:
                    # A valid physical body whose ref has no source placement.
                    versions.append(VersionChange(PAGE_NAMESPACE, (1, 999), (HistoryReference('list', 1),)))
            return versions, ordinary
        monkeypatch.setattr(module(), '_owner_sources', owners)
    with pytest.raises((ValueError, StoreIntegrityError)):
        upgrade_lazy_snapshot(source, destination, rules_id=RULES)
    assert not destination.exists() and sha(source) == before
    assert not list(tmp_path.glob('.ate-catalog-copy-*'))


def test_validation_only_fits_where_disposable_catalog_exhausts_address_space():
    import subprocess
    import sys
    import json
    code = '''
import json,resource,sys,time
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta,validate_initial_catalog_inputs
resource.setrlimit(resource.RLIMIT_AS,(110*1024**2,110*1024**2))
start=time.perf_counter()
try:
 owners=tuple(VersionChange('world.people',i,{'v':i}) for i in range(12000))
 placements=tuple(IdentityOccurrenceChange('world.people',i,(),i+1) for i in range(12000))
 build=initial_catalog_delta if sys.argv[1]=='old' else validate_initial_catalog_inputs
 result=build(WorldCodec(identity_links_recorded=True),owners,placements,next_incarnation_id=12001,generation=1)
 passed=True
except MemoryError:
 passed=False
print(json.dumps({'passed':passed,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'seconds':time.perf_counter()-start}))
'''
    rows = [json.loads(subprocess.check_output([sys.executable, '-c', code, mode], text=True))
            for mode in ('old', 'validate')]
    assert rows[0]['passed'] is False
    assert rows[1]['passed'] is True
    assert rows[1]['peak_rss_kib'] < rows[0]['peak_rss_kib']


def workspace_type():
    name = 'ate_sim.persistence_conversion_workspace'
    assert importlib.util.find_spec(name) is not None, 'conversion disk staging missing'
    return importlib.import_module(name).ConversionWorkspace


@pytest.mark.parametrize('shape', ['empty', 'owners', 'group', 'owner', 'retired'])
def test_staged_catalog_matches_reference_including_order_and_large_inventories(tmp_path, shape):
    codec = WorldCodec(identity_links_recorded=True)
    n = 257
    owners = tuple(VersionChange('world.people', i, {'v': i}) for i in range(n)) if shape in ('owners', 'group') else ()
    if shape == 'owner': owners = (VersionChange('world.people', 1, 'compact'),)
    if shape == 'owners': placements = tuple(IdentityOccurrenceChange('world.people', i, (), i + 1) for i in range(n))
    elif shape == 'group': placements = tuple(IdentityOccurrenceChange('world.people', i, (), 1) for i in range(n))
    elif shape == 'owner': placements = tuple(IdentityOccurrenceChange('world.people', 1, (('key', i),), i + 1) for i in range(n))
    else: placements = ()
    next_id = 1 if shape == 'empty' else n + 1
    expected = catalog().initial_catalog_delta(codec, owners, placements, next_incarnation_id=next_id, generation=1).decode(codec)[0]
    expected = [codec.encode((v.namespace, v.key, v.value, v.delete, v.record_schema,
                               tuple((m.index_name, m.value, m.ordinal) for m in v.memberships))) for v in expected]
    with workspace_type()(codec, directory=tmp_path, entry_limit=4, byte_limit=1024) as workspace:
        rows = catalog().stage_initial_catalog(workspace, owners, placements, next_incarnation_id=next_id, generation=1)
        for _ in range(2):
            actual = [codec.encode((v.namespace, v.key, v.value, v.delete, v.record_schema,
                                   tuple((m.index_name, m.value, m.ordinal) for m in v.memberships))) for v in rows]
            assert actual == expected
        assert len(rows) == len(expected)
        assert workspace.metrics['buffer_entries_high_water'] <= 4
        assert workspace.metrics['buffer_bytes_high_water'] <= 1024
        assert workspace.metrics['disk_bytes'] > 0
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('corruption', ['payload', 'missing', 'extra', 'reordered'])
def test_staged_replay_fails_closed_on_modified_row_count_or_order(tmp_path, corruption):
    codec = WorldCodec(identity_links_recorded=True)
    with workspace_type()(codec, directory=tmp_path, entry_limit=4, byte_limit=1024) as workspace:
        rows = workspace.stage_versions(VersionChange('world.people', i, [i]) for i in range(8))
        assert [v.key for v in rows] == list(range(8))
        db = workspace.db
        if corruption == 'payload': db.execute("UPDATE replay_rows SET payload=x'00' WHERE stream=? AND ordinal=0", (rows.stream,))
        elif corruption == 'missing': db.execute('DELETE FROM replay_rows WHERE stream=? AND ordinal=0', (rows.stream,))
        elif corruption == 'extra': db.execute('INSERT INTO replay_rows SELECT stream,99,payload,checksum FROM replay_rows WHERE stream=? AND ordinal=0', (rows.stream,))
        else:
            db.execute('UPDATE replay_rows SET ordinal=99 WHERE stream=? AND ordinal=0', (rows.stream,))
            db.execute('UPDATE replay_rows SET ordinal=0 WHERE stream=? AND ordinal=1', (rows.stream,))
            db.execute('UPDATE replay_rows SET ordinal=1 WHERE stream=? AND ordinal=99', (rows.stream,))
        with pytest.raises(StoreIntegrityError): list(rows)
    assert not list(tmp_path.iterdir())


def test_staging_freezes_mutable_values_and_cleans_up_exception(tmp_path):
    codec = WorldCodec(identity_links_recorded=True)
    with pytest.raises(OSError):
        with workspace_type()(codec, directory=tmp_path, entry_limit=4, byte_limit=1024) as workspace:
            value = [1]
            rows = workspace.stage_versions([VersionChange('world.people', 1, value)])
            value.append(2)
            assert rows[0].value == [1]
            assert rows[0].value is not rows[0].value
            raise OSError('after preparation')
    workspace.close()
    assert not list(tmp_path.iterdir())
