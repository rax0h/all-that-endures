"""An unchanged-identity row factory must not hide a corrupted reachable root."""
from pathlib import Path
import json,tempfile
from guard_holes import fingerprint
from simulation.tests.test_stage_0_6_genesis_transaction import ready
from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_genesis_transaction import ProofGenesisTransaction
from ate_sim import persistence_proof_record as record
from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
from ate_sim.persistence_proof_publication import bootstrap_content_proofs
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
from ate_sim.persistence_proof_inventory import bootstrap_inventory
from ate_sim.persistence_proof_manifest_publish import bootstrap_world_manifest
from ate_sim.persistence_proof_store import ProofNodeStore

fingerprint()
with tempfile.TemporaryDirectory(prefix='ate-review-factory-') as directory:
    store,pin=ready(Path(directory));row=dict(probe='row_factory_hides_corrupt_reachable_record_root')
    with store,lazy._bounded_conversion_audits():
        try:
            with ProofGenesisTransaction(store,pin):
                ra=record.bootstrap_record_proofs(store,pin)
                sa=bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True,include_rank=True)
                ca=bootstrap_content_proofs(store,pin)
                da=bootstrap_collection_directory(store,pin)
                ia=bootstrap_inventory(store,pin)
                domain=record._map(store).map_domain;digest=ra[0].root.digest
                raw=store.db.execute('SELECT node_bytes FROM ate_proof_nodes WHERE map_domain=? AND digest=?',(domain,digest)).fetchone()[0]
                store.db.execute("UPDATE ate_proof_nodes SET node_bytes=X'00' WHERE map_domain=? AND digest=?",(domain,digest))
                spoofed=0
                def factory(cursor,values):
                    global spoofed
                    if values==(1,b'\0'):
                        spoofed+=1
                        return len(raw),raw
                    return values
                store.db.row_factory=factory
                bootstrap_world_manifest(store,pin,ca,sa,ia,ra,da)
            row.update(outcome='committed',spoofed_reads=spoofed)
        except BaseException as exc:row.update(outcome='rejected',error=type(exc).__name__+': '+str(exc))
        finally:store.db.row_factory=None
        if row['outcome']=='committed':
            try:ProofNodeStore(store.db).read(domain,digest);row['real_reachable_root']='accepted'
            except BaseException as exc:row['real_reachable_root']=type(exc).__name__+': '+str(exc)
    print(json.dumps(row),flush=True)
