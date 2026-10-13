"""Explicit complete-format publication selects checked ordinary open."""
import pytest
from unittest.mock import patch
from ate_sim.core import Settlement
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_nested_history import ENTRY_NAMESPACE, PAGE_NAMESPACE
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, RULES, sha, opened


def upgraded(tmp_path):
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    def configure(world):
        world.settlements[1]=Settlement(1,0,0,memory={'war':.25})
    source=legacy_lazy(tmp_path,configure=configure);before=sha(source)
    target=tmp_path/'complete.sqlite'
    result=upgrade_lazy_snapshot(source,target,rules_id=RULES)
    assert sha(source)==before and result['complete_format'] is True
    return target


def test_complete_upgrade_opens_checked_runtime_without_legacy_scan(tmp_path,monkeypatch):
    from ate_sim.persistence_lazy_store import LazyRecordStore
    path=upgraded(tmp_path)
    read=LazyRecordStore.read_version
    def bounded(store,pin,namespace,key,**kwargs):
        if namespace in (ENTRY_NAMESPACE,PAGE_NAMESPACE):pytest.fail('ordinary open read historical child payload')
        return read(store,pin,namespace,key,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(LazyRecordStore,'read_version',bounded)
        with patch('ate_sim.persistence_lazy._read_current_identity_links',side_effect=AssertionError('legacy identity scan')):
            s=open_lazy_world_session(path,rules_id=RULES)
    with s:
        assert s._identity_coordinator is not None
        child=s.skills[1,'craft'].provenance
        assert child is s.skills[2,'craft'].provenance
        child.append(99);s.save()
        assert int(s.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])==6
    with open_lazy_world_session(path,rules_id=RULES) as s:
        assert s._identity_coordinator is not None and s.skills[1,'craft'].provenance[-1]==99


def test_genuine_legacy_reader_does_not_activate_partial_catalog_on_open(tmp_path):
    from simulation.tests.test_stage_0_5_final_catalog_copy import module
    source=legacy_lazy(tmp_path);target=tmp_path/'staged.sqlite'
    module()._copy_with_checked_catalog(source,target,rules_id=RULES,normalize_events=True)
    with open_lazy_world_session(source,rules_id=RULES) as s:assert s._identity_coordinator is None
    # A private partial catalog is not a complete published World and must not
    # be inferred as such merely from its presence.
    from ate_sim.incremental_store import StoreError
    with pytest.raises(StoreError):open_lazy_world_session(target,rules_id=RULES)


def rewrite_manifest(path,change):
    from ate_sim.incremental_store import RecordChange
    from ate_sim.persistence_adapters import META
    from ate_sim.persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
    with opened(path) as store:
        pin=store.capture_pin();manifest=dict(store.read_record(META,'manifest'));change(manifest)
        token='c'*32
        result=store.commit(pin,commit_token=token,version_changes=(),identity_changes=(),
            changes=(RecordChange(META,'manifest',manifest),RecordChange(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY,
                (1,pin.captured_head+1,token))),new_segments=(),metadata=store.head_metadata())
        store.release_pin(result.pin)


@pytest.mark.parametrize('corruption',['marker_without_floor','floor_without_marker','missing_feature','unknown_feature',
    'missing_catalog','missing_catalog_namespace','mixed_ordinary_links'])
def test_complete_open_rejects_missing_or_competing_authority(tmp_path,corruption):
    from ate_sim.incremental_store import StoreFormatError,StoreIntegrityError
    from ate_sim.persistence_lazy_identity_catalog import CATALOG_NAMESPACE
    path=upgraded(tmp_path)
    if corruption in ('floor_without_marker','missing_feature','unknown_feature'):
        def change(manifest):
            if corruption=='floor_without_marker':
                manifest.pop('complete_features');manifest['identity_storage']='current-links/v1'
            elif corruption=='missing_feature':manifest['complete_features']=manifest['complete_features'][:-1]
            else:manifest['complete_features']+=('unknown/v1',)
        rewrite_manifest(path,change)
    else:
        with opened(path) as store:
            if corruption=='marker_without_floor':store.db.execute("UPDATE store_metadata SET value='5' WHERE key='format_version'")
            elif corruption=='missing_catalog':store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?',(CATALOG_NAMESPACE,))
            elif corruption=='missing_catalog_namespace':store.db.execute('DELETE FROM lazy_namespace_state WHERE namespace=?',(CATALOG_NAMESPACE,))
            else:
                # Raw competing ordinary authority must be rejected before its
                # payload can be interpreted, even if its checksum is invalid.
                store.db.execute("INSERT INTO records VALUES ('world_identity_links',x'00',x'00','bad',1,1,0)")
            store.db.commit()
    with pytest.raises((StoreFormatError,StoreIntegrityError)):open_lazy_world_session(path,rules_id=RULES)


@pytest.mark.parametrize('phase',['after_private_copy','before_catalog_commit','after_catalog_commit',
    'after_catalog_validation','before_publish'])
def test_complete_upgrade_fault_never_publishes_partial_file(tmp_path,monkeypatch,phase):
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    from simulation.tests.test_stage_0_5_final_catalog_copy import module
    source=legacy_lazy(tmp_path);before=sha(source);target=tmp_path/'complete.sqlite'
    def fail(at,_path):
        if at==phase:raise OSError(phase)
    monkeypatch.setattr(module(),'_copy_phase',fail)
    with pytest.raises(OSError,match=phase):upgrade_lazy_snapshot(source,target,rules_id=RULES)
    assert sha(source)==before and not target.exists()


def test_complete_upgrade_does_not_overwrite_racing_destination(tmp_path,monkeypatch):
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    from simulation.tests.test_stage_0_5_final_catalog_copy import module
    source=legacy_lazy(tmp_path);before=sha(source);target=tmp_path/'complete.sqlite'
    def race(at,_path):
        if at=='before_publish':target.write_bytes(b'competing destination')
    monkeypatch.setattr(module(),'_copy_phase',race)
    with pytest.raises(FileExistsError):upgrade_lazy_snapshot(source,target,rules_id=RULES)
    assert sha(source)==before and target.read_bytes()==b'competing destination'


def test_complete_current_copy_preserves_markers_and_checked_runtime(tmp_path):
    from simulation.tests.test_stage_0_5_final_catalog_copy import module
    source=upgraded(tmp_path);before=sha(source);target=tmp_path/'current-copy.sqlite'
    result=module()._copy_current_checked_catalog(source,target,rules_id=RULES)
    assert sha(source)==before and result['complete_format'] is True
    with open_lazy_world_session(target,rules_id=RULES) as s:
        assert s._identity_coordinator is not None
        assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance


def test_complete_point_edit_and_noop_have_fixed_history_work(tmp_path,record_property):
    from dataclasses import asdict
    from ate_sim.core import Person,Household
    from ate_sim.household_queries import living_household_members
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    measured=[]
    for size in (1000,10000):
        folder=tmp_path/str(size);folder.mkdir()
        def configure(world):
            for pid in range(1,9):world.people[pid]=Person(pid,0,1,1)
            world.households[1]=Household(1,1,members=list(range(1,9)))
            world.settlements[1]=Settlement(1,0,0,households=[1],memory={'war':0.})
            world.next_person=9;world.next_household=2;world.next_settlement=2
        source=legacy_lazy(folder,size=size,configure=configure)
        target=folder/'complete.sqlite';upgrade_lazy_snapshot(source,target,rules_id=RULES)
        with open_lazy_world_session(target,rules_id=RULES) as s:
            assert [p.id for p in living_household_members(s.world,1)]==list(range(1,9))
            child=s.skills[1,'craft'].provenance
            s._registry.live_bindings=lambda:pytest.fail('ordinary edit/save scanned all registry objects')
            s.store.reset_diagnostics()
            child[0]=size;s.save()
            measured.append(asdict(s.store.diagnostics()))
            assert child is s.skills[2,'craft'].provenance and len(child)==size
            s.store.reset_diagnostics();read=s.store.read_version
            def no_archive(*_args,**_kwargs):pytest.fail('no-op save read versioned archive payload')
            s.store.read_version=no_archive
            try:s.save()
            finally:s.store.read_version=read
            assert s.store.diagnostics().payload_writes==0
        with open_lazy_world_session(target,rules_id=RULES) as s:
            assert s.skills[1,'craft'].provenance[0]==size
            assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
    record_property('h1k_h10k_complete_point_io',measured)
    for name in ('payload_reads','payload_writes','metadata_rows'):
        assert measured[0][name]==measured[1][name]
    for name in ('payload_read_bytes','payload_write_bytes'):
        assert abs(measured[0][name]-measured[1][name])<=1024


def test_full_complete_copy_rejects_inconsistent_exception_semantics(tmp_path):
    from ate_sim.persistence_event_ids import EventIdSet
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
    from simulation.tests.test_stage_0_5_final_catalog_copy import module
    def configure(world):world.event_ids=EventIdSet.from_range_descriptor(10)
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'complete.sqlite'
    upgrade_lazy_snapshot(source,target,rules_id=RULES)
    with open_lazy_world_session(target,rules_id=RULES) as s:
        ids=s.world.event_ids;ids.remove(2);s.save()
        ids._exact.removed[0]=0;s.save()
        assert len(ids)==9
        with pytest.raises(StoreIntegrityError,match='exception'):set(ids)
    before=sha(target);destination=tmp_path/'rejected-copy.sqlite'
    with pytest.raises(StoreIntegrityError,match='exception'):
        module()._copy_current_checked_catalog(target,destination,rules_id=RULES)
    assert sha(target)==before and not destination.exists()
