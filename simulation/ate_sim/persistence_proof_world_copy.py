"""Explicit source-preserving proof genesis copy; never an in-place migration."""
from dataclasses import dataclass
from pathlib import Path
import tempfile
from .incremental_store import StoreError,StoreIntegrityError,_record_checksum,_segment_checksum,_head_checksum,_framed_sha
from .persistence_lazy_store import LazyRecordStore
from .persistence_adapters import WorldCodec,SCHEMA
from . import persistence_lazy_store as lazy
from . import persistence_lazy_identity_catalog as catalog

@dataclass(frozen=True)
class WorldManifestCopy:
    manifest:object
    commitment:bytes


def _rebase_private_snapshot(store):
    """A new unpublished identity has no predecessor proof generation.

    Keep logical history and ordinal/allocator state. Only storage revisions,
    source binding checksums, leases and session publication metadata change.
    """
    from .persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
    if store.db.in_transaction:raise StoreError('private genesis rebase requires owned construction')
    g=store.generation;db=store.db;codec=store.codec
    if db.execute('SELECT 1 FROM generation_pins LIMIT 1').fetchone():raise StoreError('private genesis cannot carry live publisher leases')
    store.verify_all();db.execute('BEGIN IMMEDIATE')
    try:
        # Normalize current source revisions before rewriting owner witnesses.
        for table in ('lazy_record_versions','lazy_order_versions','lazy_query_versions','lazy_namespace_state','lazy_identity_occurrence_versions','lazy_identity_state'):
            db.execute('DELETE FROM '+table+' WHERE NOT(valid_from<=? AND (valid_to IS NULL OR ?<valid_to))',(g,g))
        for ns,key,payload,version,schema in db.execute('SELECT namespace,typed_key,payload,codec_version,record_schema FROM records').fetchall():
            if ns==EVENT_STORAGE and key==codec.encode(COMMIT_DESCRIPTOR_KEY):payload=codec.encode((1,0,'0'*32))
            checksum=_record_checksum(ns,key,schema,version,0,payload)
            db.execute('UPDATE records SET payload=?,payload_checksum=?,last_changed_generation=0 WHERE namespace=? AND typed_key=?',(payload,checksum,ns,key))
        db.execute('UPDATE query_membership SET generation=0')
        for ns,ordinal,payload,first,last,count,version in db.execute('SELECT namespace,ordinal,payload,first_id,last_id,element_count,codec_version FROM segments').fetchall():
            db.execute('UPDATE segments SET created_generation=0,payload_checksum=? WHERE namespace=? AND ordinal=?',(_segment_checksum(ns,ordinal,first,last,count,version,0,payload),ns,ordinal))
        for ns,key,payload,version,schema,members in db.execute('SELECT namespace,typed_key,payload,codec_version,record_schema,memberships FROM lazy_record_versions').fetchall():
            if ns==catalog.OWNER_NAMESPACE:
                h=list(codec.decode(payload));h[3]=0
                if h[2]=='ordinary':
                    owner_ns,owner_key=codec.decode(key);row=db.execute('SELECT payload_checksum FROM records WHERE namespace=? AND typed_key=?',(owner_ns,codec.encode(owner_key))).fetchone()
                    if h[1] and row is None:raise StoreIntegrityError('private genesis owner source missing')
                    if row is not None:h[5]=row[0]
                payload=codec.encode(tuple(h))
            if ns==catalog.GROUP_NAMESPACE:
                members=codec.encode(tuple((name,value,0 if name=='retired' else ordinal) for name,value,ordinal in codec.decode(members)))
            db.execute('UPDATE lazy_record_versions SET payload=?,payload_checksum=?,memberships=?,valid_from=0,valid_to=NULL,row_checksum=? WHERE namespace=? AND typed_key=?',
                (payload,_framed_sha(b'lazy-payload-v1',payload),members,lazy._version_checksum(ns,key,schema,version,0,None,members,payload),ns,key))
        layouts=(
            ('lazy_order_versions',('namespace','typed_key','ordinal'),lazy._order_checksum),
            ('lazy_query_versions',('namespace','index_name','index_value','record_key','ordinal'),lazy._query_checksum),
            ('lazy_namespace_state',('namespace','member_count','next_ordinal'),lazy._namespace_checksum),
            ('lazy_identity_occurrence_versions',('owner_namespace','owner_key','occurrence_path','incarnation_id'),lazy._identity_occurrence_checksum),
            ('lazy_identity_state',('next_incarnation_id',),lazy._identity_state_checksum))
        for table,fields,checksum in layouts:
            rows=db.execute('SELECT '+','.join(fields)+' FROM '+table).fetchall()
            db.execute('DELETE FROM '+table)
            for row in rows:
                if table=='lazy_query_versions' and row[:2]==(catalog.GROUP_NAMESPACE,'retired'):
                    row=(*row[:-1],0)
                names=(*fields,'valid_from','valid_to','row_checksum');values=(*row,0,None,checksum(*row,0,None))
                db.execute('INSERT INTO '+table+'('+','.join(names)+') VALUES('+','.join('?' for _ in names)+')',values)
        for table in ('save_receipts','pin_receipts','pin_attempts'):db.execute('DELETE FROM '+table)
        row=store._checked_head_row();values=(0,None,*row[2:7])
        db.execute('UPDATE save_head SET generation=0,parent_generation=NULL,head_checksum=?',(_head_checksum(*values),))
        db.commit();store.verify_all()
    except BaseException:
        if db.in_transaction:db.rollback()
        raise


def copy_world_with_proofs(source,destination,*,rules_id):
    from .persistence_session import _preflight_conversion_paths,_publish_private_cold_file
    from .persistence_complete_format import upgrade_lazy_snapshot
    from .persistence_proof_record import bootstrap_record_proofs
    from .persistence_proof_scope import bootstrap_scope_proofs
    from .persistence_proof_publication import bootstrap_content_proofs
    from .persistence_proof_inventory import bootstrap_inventory
    from .persistence_proof_collection_directory import bootstrap_collection_directory
    from .persistence_proof_manifest_publish import bootstrap_world_manifest
    source,destination=_preflight_conversion_paths(source,destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ate-proof-genesis-',dir=destination.parent) as scratch:
        private=Path(scratch)/'world.sqlite'
        with LazyRecordStore.open(source,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=rules_id) as original:
            floor=int(original.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
        if floor==6:
            from .persistence_catalog_copy import _copy_current_checked_catalog
            _copy_current_checked_catalog(source,private,rules_id=rules_id)
        elif floor<6:upgrade_lazy_snapshot(source,private,rules_id=rules_id)
        else:raise StoreError('proof copy source requires old checked reader authority')
        from .persistence_lazy import open_lazy_world_session
        from .core import _digest_world_unchecked
        with open_lazy_world_session(private,rules_id=rules_id) as session:before=_digest_world_unchecked(session.world)
        with LazyRecordStore.open(private,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=rules_id) as store:_rebase_private_snapshot(store)
        with open_lazy_world_session(private,rules_id=rules_id) as session:
            if _digest_world_unchecked(session.world)!=before:raise StoreIntegrityError('proof genesis changed the canonical World digest')
        with LazyRecordStore.open(private,codec=WorldCodec(identity_links_recorded=True),expected_simulation_schema=SCHEMA,expected_rules_id=rules_id) as store:
            store.db.execute("UPDATE store_metadata SET value='7' WHERE key='format_version'");store.db.commit()
            pin=store.capture_pin()
            try:
                ra=bootstrap_record_proofs(store,pin);sa=bootstrap_scope_proofs(store,pin,include_children=True,include_sequence=True)
                ca=bootstrap_content_proofs(store,pin);da=bootstrap_collection_directory(store,pin);ia=bootstrap_inventory(store,pin)
                manifest,expected=bootstrap_world_manifest(store,pin,ca,sa,ia,ra,da)
            finally:store.release_pin(pin)
        _publish_private_cold_file(private,destination)
    return WorldManifestCopy(manifest,expected)
