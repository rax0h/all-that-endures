from pathlib import Path
import json,sqlite3,tempfile
from guard_holes import fingerprint,construct
from simulation.tests.test_stage_0_6_genesis_transaction import ready
from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_genesis_transaction import ProofGenesisTransaction

fingerprint()
for operation in ('preexisting_blob','deserialize'):
    with tempfile.TemporaryDirectory(prefix='ate-review-handle-') as directory:
        root=Path(directory);store,pin=ready(root);row=dict(probe=operation)
        blob=None
        if operation=='preexisting_blob':
            rid=store.db.execute("SELECT rowid FROM store_metadata WHERE key='format_version'").fetchone()[0]
            blob=store.db.blobopen('store_metadata','value',rid,readonly=False)
            row['sqlite_in_transaction_before_enter']=store.db.in_transaction
        else:
            with sqlite3.connect(':memory:') as other:
                other.execute('CREATE TABLE replacement(x)')
                replacement=other.serialize()
        with store,lazy._bounded_conversion_audits():
            try:
                with ProofGenesisTransaction(store,pin):
                    construct(store,pin)
                    try:
                        if operation=='preexisting_blob':
                            blob.write(b'6');blob.close();blob=None
                        else:store.db.deserialize(replacement)
                        row['operation']='succeeded'
                    except BaseException as exc:row.update(operation='rejected',error=type(exc).__name__+': '+str(exc))
                row.update(outcome='committed',tables=[r[0] for r in store.db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name IN ('replacement','ate_generation_manifests')")])
                if operation=='preexisting_blob':row['format_version']=store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0]
            except BaseException as exc:row.update(outcome='rejected',exit_error=type(exc).__name__+': '+str(exc))
            finally:
                if blob is not None:blob.close()
        print(json.dumps(row),flush=True)
