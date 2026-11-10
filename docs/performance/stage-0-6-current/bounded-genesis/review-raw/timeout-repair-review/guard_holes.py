"""Independent guard/atomicity controls; no product edits or hosted work."""
from pathlib import Path
import hashlib,json,platform,sqlite3,sys,tempfile
from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_genesis_transaction import ProofGenesisTransaction
from simulation.tests.test_stage_0_6_genesis_transaction import ready

OUT=Path(__file__).parent
def fingerprint():
    import _sqlite3
    expected=json.loads(Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
    h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    db=sqlite3.connect(':memory:');libs=sorted({r.split()[-1] for r in Path('/proc/self/maps').read_text().splitlines() if '/libsqlite3.so.' in r})
    actual=dict(resolved_executable=str(Path(sys.executable).resolve()),executable_sha256=h(Path(sys.executable).resolve()),python=sys.version,compiler=platform.python_compiler(),sqlite=sqlite3.sqlite_version,sqlite_source_id=db.execute('select sqlite_source_id()').fetchone()[0],sqlite_compile_options=[r[0] for r in db.execute('pragma compile_options')],sqlite_extension_path=_sqlite3.__file__,sqlite_extension_sha256=h(_sqlite3.__file__),loaded_sqlite_libraries=[dict(path=p,sha256=h(p)) for p in libs]);db.close()
    diff={k:dict(expected=expected[k],actual=v) for k,v in actual.items() if expected[k]!=v}
    (OUT/'fingerprint.json').write_text(json.dumps(dict(actual=actual,differences=diff),indent=2)+'\n')
    assert not diff,diff

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

def savepoint_after_seal():
    with tempfile.TemporaryDirectory(prefix='ate-review-savepoint-') as directory:
        store,pin=ready(Path(directory))
        row=dict(probe='rollback_to_pre_manifest_savepoint')
        with store,lazy._bounded_conversion_audits():
            try:
                with ProofGenesisTransaction(store,pin) as owned:
                    store.db.execute('SAVEPOINT before_build')
                    construct(store,pin)
                    row['sealed_before_rollback']=owned.sealed
                    row['manifest_rows_before']=store.db.execute('SELECT count(*) FROM ate_generation_manifests').fetchone()[0]
                    store.db.execute('ROLLBACK TO before_build')
                    store.db.execute('RELEASE before_build')
                    row['manifest_rows_after_rollback']=store.db.execute('SELECT count(*) FROM ate_generation_manifests').fetchone()[0]
                row.update(outcome='committed',manifest_rows_after_commit=store.db.execute('SELECT count(*) FROM ate_generation_manifests').fetchone()[0],physical_checks=owned.physical_checks)
            except BaseException as exc:row.update(outcome='rejected',error_type=type(exc).__name__,error=str(exc))
        print(json.dumps(row),flush=True)

def trace_write_at_commit():
    with tempfile.TemporaryDirectory(prefix='ate-review-commit-trace-') as directory:
        store,pin=ready(Path(directory));armed=False;attempts=[]
        def trace(sql):
            if armed and sql.strip().upper()=='COMMIT':
                attempt=dict(guard_active=getattr(store.db,'_native_write_guard',None) is not None)
                try:
                    store.db.execute("UPDATE store_metadata SET value='6' WHERE key='format_version'")
                    attempt['source_write']='succeeded'
                except BaseException as exc:attempt.update(source_write='rejected',error=type(exc).__name__+': '+str(exc))
                attempts.append(attempt)
        row=dict(probe='trace_callback_source_write_at_commit')
        with store,lazy._bounded_conversion_audits():
            store.db.set_trace_callback(trace)
            try:
                with ProofGenesisTransaction(store,pin) as owned:
                    construct(store,pin)
                    armed=True
                row.update(outcome='committed',format_version=store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0],manifest_rows=store.db.execute('SELECT count(*) FROM ate_generation_manifests').fetchone()[0])
            except BaseException as exc:row.update(outcome='rejected',error_type=type(exc).__name__,error=str(exc))
            finally:
                armed=False;store.db.set_trace_callback(None)
        row['callback_attempts']=attempts
        print(json.dumps(row),flush=True)

def trace_write_during_setup():
    with tempfile.TemporaryDirectory(prefix='ate-review-setup-trace-') as directory:
        store,pin=ready(Path(directory));attempts=[]
        def trace(sql):
            if not attempts and sql.startswith('CREATE TABLE IF NOT EXISTS ate_proof_nodes'):
                attempt=dict(guard_active=getattr(store.db,'_native_write_guard',None) is not None)
                attempts.append(attempt)
                try:
                    store.db.execute("UPDATE store_metadata SET value='tampered-in-setup' WHERE key='rules_id'")
                    attempt['source_write']='succeeded'
                except BaseException as exc:attempt.update(source_write='rejected',error=type(exc).__name__+': '+str(exc))
        row=dict(probe='trace_callback_source_write_during_schema_setup')
        with store,lazy._bounded_conversion_audits():
            store.db.set_trace_callback(trace)
            try:
                with ProofGenesisTransaction(store,pin):
                    manifest,_=construct(store,pin)
                row.update(outcome='committed',rules_id=store.db.execute("SELECT value FROM store_metadata WHERE key='rules_id'").fetchone()[0],manifest_rules_id=manifest.rules_id)
            except BaseException as exc:row.update(outcome='rejected',error_type=type(exc).__name__,error=str(exc))
            finally:store.db.set_trace_callback(None)
        row['callback_attempts']=attempts
        print(json.dumps(row),flush=True)

def foreign_store_certificate():
    with tempfile.TemporaryDirectory(prefix='ate-review-foreign-') as directory:
        a=Path(directory)/'a';b=Path(directory)/'b';a.mkdir();b.mkdir()
        store,pin=ready(a);foreign,foreign_pin=ready(b)
        foreign.db.execute("UPDATE lazy_record_versions SET payload=X'00'");foreign.db.commit()
        row=dict(probe='foreign_store_verify_all_certificate')
        with store,foreign,lazy._bounded_conversion_audits():
            try:
                with ProofGenesisTransaction(store,pin) as owned:
                    owned.verify_sources()
                    foreign._genesis_transaction=owned
                    try:
                        report=foreign.verify_all()
                        row.update(foreign_audit='accepted',report_generation=report['generation'])
                    except BaseException as exc:row.update(foreign_audit='rejected',error_type=type(exc).__name__,error=str(exc))
                    finally:foreign._genesis_transaction=None
            except BaseException as exc:row['incomplete_bundle_exit']=type(exc).__name__
            try:foreign.verify_all()
            except BaseException as exc:row['real_foreign_audit']=type(exc).__name__+': '+str(exc)
        print(json.dumps(row),flush=True)

def blob_source_write():
    with tempfile.TemporaryDirectory(prefix='ate-review-blob-') as directory:
        store,pin=ready(Path(directory));row=dict(probe='incremental_blob_source_write')
        with store,lazy._bounded_conversion_audits():
            try:
                with ProofGenesisTransaction(store,pin):
                    construct(store,pin)
                    rid=store.db.execute("SELECT rowid FROM store_metadata WHERE key='format_version'").fetchone()[0]
                    try:
                        with store.db.blobopen('store_metadata','value',rid,readonly=False) as blob:blob.write(b'6')
                        row['source_write']='succeeded'
                    except BaseException as exc:row.update(source_write='rejected',error_type=type(exc).__name__,error=str(exc))
                row.update(outcome='committed',format_version=store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
            except BaseException as exc:row.update(outcome='rejected',exit_error=type(exc).__name__+': '+str(exc))
        print(json.dumps(row),flush=True)

if __name__=='__main__':
    fingerprint()
    savepoint_after_seal()
    trace_write_at_commit()
    trace_write_during_setup()
    foreign_store_certificate()
    blob_source_write()
