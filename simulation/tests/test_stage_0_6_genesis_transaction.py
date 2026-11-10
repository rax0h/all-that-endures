from unittest.mock import patch
import sqlite3
import pytest
from ate_sim import persistence_lazy_store as lazy
from ate_sim.incremental_store import StoreError
from simulation.tests.test_stage_0_5_final_catalog_copy import opened
from simulation.tests.test_stage_0_5_final_complete_format import upgraded


def ready(tmp_path):
    from ate_sim.persistence_proof_world_copy import _rebase_private_snapshot
    store=opened(upgraded(tmp_path))
    _rebase_private_snapshot(store)
    store.db.execute("UPDATE store_metadata SET value='7' WHERE key='format_version'")
    store.db.commit()
    return store,store.capture_pin()


def bundle():
    from ate_sim.persistence_genesis_transaction import ProofGenesisTransaction
    return ProofGenesisTransaction


def construct(store,pin):
    from ate_sim.persistence_proof_record import bootstrap_record_proofs
    from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
    from ate_sim.persistence_proof_publication import bootstrap_content_proofs
    from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
    from ate_sim.persistence_proof_inventory import bootstrap_inventory
    from ate_sim.persistence_proof_manifest_publish import bootstrap_world_manifest
    ra=bootstrap_record_proofs(store,pin)
    sa=bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True,include_rank=True)
    ca=bootstrap_content_proofs(store,pin)
    da=bootstrap_collection_directory(store,pin)
    ia=bootstrap_inventory(store,pin)
    return bootstrap_world_manifest(store,pin,ca,sa,ia,ra,da)


def test_one_owned_transaction_reuses_source_audit_and_commits_all_roots(tmp_path):
    from ate_sim.persistence_proof_record import bootstrap_record_proofs
    from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
    from ate_sim.persistence_proof_publication import bootstrap_content_proofs
    from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
    from ate_sim.persistence_proof_inventory import bootstrap_inventory
    from ate_sim.persistence_proof_manifest_publish import bootstrap_world_manifest
    from ate_sim.persistence_proof_generation import read_generation_manifest
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits(),patch.object(store,'_verify_all_in_snapshot',wraps=store._verify_all_in_snapshot) as audits:
        with bundle()(store,pin) as owned:
            ra=bootstrap_record_proofs(store,pin)
            sa=bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True,include_rank=True)
            ca=bootstrap_content_proofs(store,pin)
            da=bootstrap_collection_directory(store,pin)
            ia=bootstrap_inventory(store,pin)
            manifest,expected=bootstrap_world_manifest(store,pin,ca,sa,ia,ra,da)
            assert store.db.in_transaction
            assert audits.call_count==1 and owned.audit_reuses>=5
        assert owned.physical_checks==1 and not store.db.in_transaction
        assert read_generation_manifest(store,pin,expected)==manifest


@pytest.mark.parametrize('sql',[
    'DELETE FROM records', 'UPDATE save_head SET generation=0',
    "UPDATE store_metadata SET value='6' WHERE key='format_version'",
    'DELETE FROM generation_pins','DELETE FROM lazy_identity_occurrence_versions',
    'CREATE TEMP TABLE records(x)','DROP TABLE records','ALTER TABLE records ADD COLUMN bad',
    'COMMIT','ROLLBACK','PRAGMA writable_schema=ON',
])
def test_caught_source_or_transaction_escape_poison_entire_build(tmp_path,sql):
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits():
        with pytest.raises(StoreError):
            with bundle()(store,pin):
                store.verify_all()
                try:store.db.execute(sql)
                except sqlite3.DatabaseError:pass
        assert not store.db.in_transaction
        assert store.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_record_roots'").fetchone() is None
        store.verify_all()


def test_public_bootstrap_still_rejects_borrowed_transaction(tmp_path):
    from ate_sim.persistence_proof_record import bootstrap_record_proofs
    store,pin=ready(tmp_path)
    with store:
        store.db.execute('BEGIN')
        with pytest.raises(StoreError):bootstrap_record_proofs(store,pin)
        store.db.rollback()


def test_catalog_scope_owns_and_blocks_writes_without_repeating_head_checks(tmp_path):
    from ate_sim.persistence_genesis_transaction import catalog_snapshot
    from ate_sim.persistence_lazy_identity_catalog import CATALOG_NAMESPACE
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits(),patch.object(store,'_checked_operational_rows',wraps=store._checked_operational_rows) as checks:
        with catalog_snapshot(store,pin):
            for _ in range(100):store.read_version(pin,CATALOG_NAMESPACE,0,expected_record_schema=1)
        assert checks.call_count==1
        assert getattr(store,'_validation_scope',None) is None
        with pytest.raises(StoreError):
            with catalog_snapshot(store,pin):
                try:store.db.execute('DELETE FROM records')
                except sqlite3.DatabaseError:pass


def test_incomplete_bundle_rolls_back_even_with_a_valid_source_audit(tmp_path):
    from ate_sim.persistence_proof_record import bootstrap_record_proofs
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits():
        with pytest.raises(StoreError,match='World audit'):
            with bundle()(store,pin):bootstrap_record_proofs(store,pin)
        assert store.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_record_roots'").fetchone() is None


def test_external_writer_cannot_change_frozen_source(tmp_path):
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits():
        with pytest.raises(StoreError,match='World audit'):
            with bundle()(store,pin):
                store.verify_all()
                with sqlite3.connect(store.path,timeout=0) as external:
                    with pytest.raises(sqlite3.OperationalError,match='locked'):
                        external.execute('DELETE FROM records')


@pytest.mark.parametrize('change',['codec','phase','authorizer','callback'])
def test_changed_custody_or_callback_write_cannot_keep_certificate(tmp_path,change):
    store,pin=ready(tmp_path)
    codec,phase=store.codec,store._phase_hook
    with store,lazy._bounded_conversion_audits():
        try:
            with pytest.raises(StoreError):
                with bundle()(store,pin) as owned:
                    store.verify_all()
                    if change=='codec':store.codec=type(store.codec)(identity_links_recorded=True)
                    elif change=='phase':store._phase_hook=lambda _:None
                    elif change=='authorizer':
                        try:store.db.set_authorizer(None)
                        except StoreError:pass
                    else:
                        def callback():
                            try:store.db.execute('DELETE FROM ate_proof_nodes')
                            except (sqlite3.DatabaseError,StoreError):pass
                            return 1
                        # Registration itself is forbidden while the capability is active.
                        try:store.db.create_function('unsafe',0,callback)
                        except StoreError:pass
                    owned.verify_sources()
        finally:store.codec=codec;store._phase_hook=phase
        assert not store.db.in_transaction


@pytest.mark.parametrize('damage',['expired','kind','duplicates'])
def test_folded_roster_reset_preserves_validation_and_source(tmp_path,damage):
    import hashlib
    from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
    from ate_sim.persistence_history_dependencies import NAMESPACE,TAG,_checked_value
    from ate_sim.persistence_lazy_store import VersionChange
    from simulation.tests.test_stage_0_5_final_catalog_copy import RULES
    from simulation.tests.test_stage_0_5_proof_world import coherent_edit
    source=upgraded(tmp_path)
    with opened(source) as store:
        pin=store.capture_pin();key=next(store.iter_keys(pin,NAMESPACE));old=_checked_value(store,pin,key)
        value=(TAG,('map' if old[1]!='map' else 'list') if damage=='kind' else old[1],
               ('expired','expired') if damage=='duplicates' else ('expired',))
        pin=coherent_edit(store,pin,version_changes=(VersionChange(NAMESPACE,key,value),))
        store.release_pin(pin)
    before=hashlib.sha256(source.read_bytes()).digest();dest=tmp_path/'proof.sqlite'
    if damage!='expired':
        with pytest.raises(StoreError):copy_world_with_proofs(source,dest,rules_id=RULES,rank_proofs=True)
        assert not dest.exists()
    else:
        result=copy_world_with_proofs(source,dest,rules_id=RULES,rank_proofs=True)
        assert result.manifest.generation==0
        with opened(dest) as store:
            pin=store.capture_pin()
            for incarnation in store.iter_keys(pin,NAMESPACE):assert _checked_value(store,pin,incarnation)[2]==()
    assert hashlib.sha256(source.read_bytes()).digest()==before


def test_source_certificate_does_not_accept_corrupt_new_proof_nodes(tmp_path,monkeypatch):
    from ate_sim import persistence_proof_world_copy as copy_api,persistence_proof_record as records
    from simulation.tests.test_stage_0_5_final_catalog_copy import RULES
    source=upgraded(tmp_path);dest=tmp_path/'proof.sqlite';captured={}
    original=records.bootstrap_record_proofs
    def remember(store,*a,**k):
        captured['store']=store
        return original(store,*a,**k)
    def corrupt(phase):
        if phase=='bootstrap.World_manifest':
            captured['store'].db.execute("UPDATE ate_proof_nodes SET node_bytes=X'00'")
    monkeypatch.setattr(records,'bootstrap_record_proofs',remember)
    monkeypatch.setattr(copy_api,'_genesis_phase',corrupt)
    with pytest.raises(StoreError):copy_api.copy_world_with_proofs(source,dest,rules_id=RULES,rank_proofs=True)
    assert not dest.exists() and not tuple(tmp_path.glob('.ate-proof-genesis-*'))


@pytest.mark.parametrize('sql',['SAVEPOINT before_build','ROLLBACK TO before_build','RELEASE before_build'])
def test_savepoint_control_is_not_permitted_after_world_seal(tmp_path,sql):
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits():
        with pytest.raises(StoreError):
            with bundle()(store,pin) as owned:
                construct(store,pin)
                try:store.db.execute(sql)
                except sqlite3.DatabaseError:pass
                assert owned.denied
        assert not store.db.in_transaction
        assert store.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_generation_manifests'").fetchone() is None


@pytest.mark.parametrize('at',['begin','schema','commit'])
def test_sql_callbacks_stay_readonly_from_setup_through_commit(tmp_path,at):
    store,pin=ready(tmp_path);attempts=[]
    def trace(sql):
        matches=(sql=='BEGIN IMMEDIATE' if at=='begin' else
            sql.startswith('CREATE TABLE IF NOT EXISTS ate_proof_nodes') if at=='schema' else sql=='COMMIT')
        if matches and not attempts:
            attempts.append(getattr(store.db,'_native_write_guard',None) is not None)
            try:store.db.execute("UPDATE store_metadata SET value='6' WHERE key='format_version'")
            except (StoreError,sqlite3.DatabaseError):pass
    with store,lazy._bounded_conversion_audits():
        store.db.set_trace_callback(trace)
        try:
            with pytest.raises((StoreError,sqlite3.DatabaseError)):
                with bundle()(store,pin):construct(store,pin)
        finally:store.db.set_trace_callback(None)
        assert attempts==[True] and not store.db.in_transaction
        assert store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()==('7',)
        assert store.db.execute("SELECT 1 FROM sqlite_schema WHERE name='ate_generation_manifests'").fetchone() is None


@pytest.mark.parametrize('field',['row','text','cursor'])
def test_result_factories_are_frozen_for_source_and_proof_checks(tmp_path,field):
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits():
        with pytest.raises(StoreError):
            with bundle()(store,pin) as owned:
                owned.verify_sources()
                try:
                    if field=='row':store.db.row_factory=lambda c,r:r
                    elif field=='text':store.db.text_factory=bytes
                    else:store.db.cursor().row_factory=lambda c,r:r
                except StoreError:pass
                assert owned.denied
        assert not store.db.in_transaction


def test_source_audit_certificate_cannot_be_transferred_to_another_store(tmp_path):
    for name in ('a','b'):(tmp_path/name).mkdir()
    a,pin=ready(tmp_path/'a');b,_=ready(tmp_path/'b')
    with a,b,lazy._bounded_conversion_audits():
        b.db.execute("UPDATE lazy_record_versions SET payload=X'00'");b.db.commit()
        with pytest.raises(StoreError,match='World audit'):
            with bundle()(a,pin) as owned:
                owned.verify_sources();b._genesis_transaction=owned
                try:
                    with pytest.raises(StoreError,match='certificate'):b.verify_all()
                finally:b._genesis_transaction=None
        with pytest.raises(StoreError):b.verify_all()


@pytest.mark.parametrize('method',['blob','deserialize'])
def test_non_sql_database_mutation_cannot_borrow_source_certificate(tmp_path,method):
    store,pin=ready(tmp_path)
    image=store.db.serialize() if method=='deserialize' else None
    row=store.db.execute("SELECT rowid FROM store_metadata WHERE key='format_version'").fetchone()[0]
    with store,lazy._bounded_conversion_audits():
        with pytest.raises(StoreError):
            with bundle()(store,pin) as owned:
                owned.verify_sources()
                try:
                    if method=='blob':store.db.blobopen('store_metadata','value',row).write(b'6')
                    else:store.db.deserialize(image)
                except StoreError:pass
                assert owned.denied
        assert store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()==('7',)


def test_existing_writable_blob_must_close_before_source_custody(tmp_path):
    store,pin=ready(tmp_path)
    with store,lazy._bounded_conversion_audits():
        row=store.db.execute("SELECT rowid FROM store_metadata WHERE key='format_version'").fetchone()[0]
        with store.db.blobopen('store_metadata','value',row) as blob:
            assert len(blob)==1 and blob.read()==b'7'
            with pytest.raises(StoreError,match='BLOB'):
                with bundle()(store,pin):pass
        assert not store.db._writable_blobs and not store.db.in_transaction


def test_deferred_transfer_still_rejects_staged_damage_before_rebase(tmp_path,monkeypatch):
    from ate_sim import persistence_proof_world_copy as copy_api
    from simulation.tests.test_stage_0_5_final_catalog_copy import RULES,sha
    source=upgraded(tmp_path);before=sha(source);destination=tmp_path/'proof.sqlite'
    original=copy_api._rebase_private_snapshot
    observed=[]
    def damaged(store,**kwargs):
        # Damage the private transfer after its canonical read but before any
        # row rewrite could replace the bad checksum with a fresh one.
        store.db.execute("UPDATE records SET payload_checksum='bad'")
        store.db.commit()
        observed.append('damaged')
        original(store,**kwargs)
    monkeypatch.setattr(copy_api,'_rebase_private_snapshot',damaged)
    with pytest.raises(StoreError):
        copy_api.copy_world_with_proofs(source,destination,rules_id=RULES,rank_proofs=True)
    assert observed==['damaged'] and sha(source)==before
    assert not destination.exists() and not tuple(tmp_path.glob('.ate-proof-genesis-*'))


@pytest.mark.parametrize('option',[True,1,None])
def test_deferred_transfer_cannot_be_requested_outside_private_construction(tmp_path,option):
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    from simulation.tests.test_stage_0_5_final_catalog_copy import RULES
    with pytest.raises(StoreError,match='private proof construction'):
        lazy.LazyRecordStore.copy_current_head(tmp_path/'missing.sqlite',tmp_path/'copy.sqlite',
            codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,
            expected_rules_id=RULES,_defer_target_audit=option)


def test_default_transfer_keeps_full_destination_audit(tmp_path,monkeypatch):
    from ate_sim.persistence_adapters import WorldCodec,SCHEMA
    from simulation.tests.test_stage_0_5_final_catalog_copy import RULES,sha
    source=upgraded(tmp_path);before=sha(source);destination=tmp_path/'copy.sqlite'
    original=lazy.LazyRecordStore._verify_all_in_snapshot;paths=[]
    def observe(store):
        paths.append(store.path)
        return original(store)
    monkeypatch.setattr(lazy.LazyRecordStore,'_verify_all_in_snapshot',observe)
    lazy.LazyRecordStore.copy_current_head(source,destination,
        codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=RULES)
    assert len(paths)==2 and paths[0]==source and paths[1]!=source
    assert destination.exists() and sha(source)==before
