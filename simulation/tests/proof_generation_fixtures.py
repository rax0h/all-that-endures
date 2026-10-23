"""Synthetic root slots exercise bindings, NOT complete World authority."""
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange
from ate_sim.persistence_proof_nodes import Root
from ate_sim.persistence_proof_generation import GenerationManifest,ManifestHead,ManifestReceipt,encode_manifest,manifest_commitment

SCHEMA='CREATE TABLE ate_generation_manifests(generation INTEGER PRIMARY KEY,commitment BLOB NOT NULL,manifest BLOB NOT NULL)'


def metadata(n=1):return dict(simulation_position=n,seed=7,next_ids={},namespaces=('archive',))


def install(store,pin,parent=None):
    g=pin.captured_head
    pos,ids,ns,counts,seed=store.db.execute('SELECT simulation_position,next_ids,namespace_inventory,namespace_counts,seed FROM save_head').fetchone()
    state=store._identity_state_at(g)[0];rows=dict(store.db.execute('SELECT key,value FROM store_metadata'))
    row=store.db.execute('SELECT pin_token,commit_token,row_checksum FROM pin_receipts WHERE generation=?',(g,)).fetchone()
    receipt=None if not g else ManifestReceipt(*row)
    value=GenerationManifest(store.store_identity,g,parent,rows['format_version'],store.codec.version,rows['simulation_schema'],rows['rules_id'],
        ManifestHead(pos,ids,ns,counts,seed,state),tuple(Root(bytes([i+1])*32,i) for i in range(7)),receipt)
    expected=manifest_commitment(value)
    store.db.execute(SCHEMA.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS'))
    store.db.execute('INSERT INTO ate_generation_manifests VALUES(?,?,?)',(g,expected,encode_manifest(value)));store.db.commit()
    return value,expected


def make_generation_store(path):
    store=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='manifest-test');pin=store.capture_pin()
    genesis=install(store,pin)
    pin=store.commit(pin,commit_token='seed',version_changes=(VersionChange('archive',i,b'x'*128) for i in range(1000)),
        changes=(),new_segments=(),metadata=metadata(),next_incarnation_id=4).pin
    return store,pin,install(store,pin,genesis[1])
