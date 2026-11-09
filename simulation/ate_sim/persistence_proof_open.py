"""Private bounded bootstrap/cleanup for explicit accepted-World opening."""
from pathlib import Path
import re
import sqlite3

from .incremental_store import StoreError, StoreFormatError, StoreIntegrityError, StoreConflictError
from .persistence_lazy_store import LazyRecordStore, GenerationPin, P1_DDL, P4_DDL, _pin_checksum
from .persistence_sqlite_guard import GuardedConnection, require_persistent_sources
from .persistence_proof_generation import decode_manifest, MAX_MANIFEST_BYTES
from .persistence_proof_projection import _require_closed_codec
from .persistence_proof_version import _guard_operational_metadata

MAX_METADATA_BYTES = 1048576
_META = {'store_uuid','format_version','codec_version','simulation_schema','rules_id','journal_mode','synchronous'}


class _OpeningResources:
    """Lexically owned resources, registered before durable/constructor handoff."""
    __slots__=('store','db','codec','identity','generation','pin','session')

    def __init__(self,store):
        manifest=getattr(store,'_opening_manifest',None)
        if manifest is None:raise StoreError('opening resources require accepted bootstrap')
        self.store,self.db,self.codec=store,store.db,store.codec
        self.identity,self.generation=manifest.store_identity,manifest.generation
        self.pin=self.session=None


def _check_resources(resources,store):
    if (type(resources) is not _OpeningResources or resources.store is not store
            or resources.db is not store.db or resources.codec is not store.codec
            or resources.identity!=store.store_identity):
        raise StoreError('invalid private proof opening resource owner')


def _remember_pin(resources,store,pin):
    _check_resources(resources,store)
    if (resources.pin is not None or type(pin) is not GenerationPin
            or pin.store_identity!=resources.identity or pin.captured_head!=resources.generation):
        raise StoreConflictError('proof opening cannot replace its owned capture')
    resources.pin=pin


def _remember_session(resources,session):
    _check_resources(resources,session.store)
    if resources.session is not None or session.pin!=resources.pin:
        raise StoreConflictError('proof opening cannot replace its owned session')
    resources.session=session


def _normalized(sql):
    return ''.join(sql.lower().split())


def _schema(db, name, wanted):
    row = db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=32768 THEN sql END "
        "FROM main.sqlite_schema WHERE type='table' AND name=?", (name,)).fetchone()
    if row is None or type(row[0]) is not str or _normalized(row[0]) != _normalized(wanted):
        raise StoreFormatError('proof opening requires verified metadata schemas')


def _raw_schemas(db):
    from .persistence_proof_manifest_publish import _SCHEMA
    for name in ('store_metadata','save_head','generation_pins','pin_receipts','pin_attempts'):
        for statement in (P1_DDL+'\n'+P4_DDL).split(';'):
            match = re.search(r'CREATE\s+TABLE\s+'+name+r'\s*\(',statement,re.I)
            if match is not None:
                _schema(db,name,statement[match.start():].strip())
                break
        else:
            raise StoreError('missing built-in opening schema')
    _schema(db,'ate_generation_manifests',_SCHEMA)


def guard_head(store):
    """Bound inherited head/lease fetches while the accepted head is provisional."""
    require_persistent_sources(store.db)
    _guard_operational_metadata(store,MAX_METADATA_BYTES)


def open_store(path, authority, *, rules_id):
    from .persistence_adapters import WorldCodec, SCHEMA
    from .persistence_proof_world_session import _WorldProofAuthority
    if type(authority) is not _WorldProofAuthority or not authority.proof_only or authority.store is not None:
        raise StoreError('invalid private proof opening capability')
    path = Path(path)
    if not path.exists():raise FileNotFoundError(path)
    db = sqlite3.connect(path,timeout=30.0,factory=GuardedConnection)
    try:
        LazyRecordStore._configure_open(db)
        db.execute('BEGIN IMMEDIATE')
        require_persistent_sources(db)
        _raw_schemas(db)
        rows = db.execute("SELECT CASE WHEN typeof(key)='text' AND length(CAST(key AS BLOB))<=128 THEN key END,"
            "CASE WHEN typeof(value)='text' AND length(CAST(value AS BLOB))<=4096 THEN value END "
            'FROM main.store_metadata LIMIT 8').fetchall()
        metadata = dict(rows)
        codec = WorldCodec(identity_links_recorded=True)
        if (len(rows)!=7 or set(metadata)!=_META or any(type(v) is not str for v in metadata.values())
                or metadata['format_version']!='7' or metadata['codec_version']!=str(codec.version)
                or metadata['simulation_schema']!=str(SCHEMA) or metadata['rules_id']!=str(rules_id)
                or metadata['journal_mode']!='delete' or metadata['synchronous']!='2'):
            raise StoreFormatError('proof opening fixed metadata or runtime context mismatch')
        identity = metadata['store_uuid']
        if not identity or not identity.isascii() or '\x00' in identity:
            raise StoreIntegrityError('invalid proof opening store identity')
        store = LazyRecordStore(path,db,codec,identity)
        store._active_read_transaction = True
        _require_closed_codec(store)
        generation = db.execute("SELECT singleton,CASE WHEN typeof(generation)='integer' AND generation>=0 THEN generation END "
            'FROM main.save_head LIMIT 2').fetchall()
        if len(generation)!=1 or generation[0][0]!=1 or type(generation[0][1]) is not int:
            raise StoreIntegrityError('invalid proof opening head selection')
        raw = db.execute("SELECT CASE WHEN typeof(commitment)='blob' AND length(commitment)=32 THEN commitment END,"
            "CASE WHEN typeof(manifest)='blob' AND length(manifest)<=? THEN manifest END "
            'FROM main.ate_generation_manifests WHERE generation=?',
            (MAX_MANIFEST_BYTES,generation[0][1])).fetchone()
        if raw is None or raw[0]!=authority.expected or type(raw[1]) is not bytes:
            raise StoreIntegrityError('missing or over-budget accepted opening manifest')
        value = decode_manifest(raw[1],authority.expected)
        if (value.store_identity!=identity or value.generation!=generation[0][1]
                or value.format_version!='7' or value.codec_version!=codec.version
                or value.simulation_schema!=str(SCHEMA) or value.rules_id!=str(rules_id)):
            raise StoreIntegrityError('accepted opening manifest context mismatch')
        authority.bind(store)
        store._world_proof_authority = authority
        authority.pair = value,authority.expected
        store._opening_manifest = value
        store._checked_head_row()
        # This preflight decodes fixed metadata only after the manifest join.
        from . import persistence_proof_manifest_publish as manifests
        manifests._schemas(store)
        db.commit()
        store._active_read_transaction = False
        return store
    except BaseException as exc:
        if db.in_transaction:db.rollback()
        db.close()
        if isinstance(exc,sqlite3.Error):raise StoreFormatError('invalid proof opening SQLite source') from exc
        raise


def context(authority):
    return (authority.store,authority.pair,authority.epoch,authority.read_pin,authority.read_components)


def check_context(authority, original, *, transaction, session=None):
    store = authority.store
    def bound():
        return (context(authority)==original and store._world_proof_authority is authority
            and store.db is original[2][0] and store.codec is original[2][1]
            and store.store_identity==original[1][0].store_identity
            and store.codec.version==original[1][0].codec_version
            and (session is None or session.store is store and session.pin==original[3]))
    if not bound():
        raise StoreConflictError('proof opening lost original admission context')
    _require_closed_codec(store)
    require_persistent_sources(store.db)
    if store.db.in_transaction is not transaction or authority._epoch()!=original[2]:
        raise StoreConflictError('proof opening snapshot or epoch changed during restoration')
    if not bound():raise StoreConflictError('proof opening changed handles during final checks')
    _require_closed_codec(store)


def abort_open(store, pin, prefix, session=None, *, owned_db=None, owned_codec=None):
    """Release only this opener's exact opaque lease, without reading a World head."""
    if owned_db is not None:store.db=owned_db
    if owned_codec is not None:store.codec=owned_codec
    if prefix is None and session is not None:prefix=getattr(session.world.events,'_disk_prefix',None)
    if prefix is not None:prefix.close()
    store._world_proof_authority = None
    try:
        if session is not None:
            try:session._registry.close()
            except Exception:pass
            session._active=False;session._state='closed'
        if store.db.in_transaction:store.db.rollback()
        if pin is not None:
            store.db.execute('BEGIN IMMEDIATE')
            require_persistent_sources(store.db)
            row=store.db.execute('SELECT store_uuid,generation,row_checksum FROM main.generation_pins WHERE token=?',(pin.token,)).fetchone()
            if row is not None:
                if row!=(pin.store_identity,pin.captured_head,_pin_checksum(pin.store_identity,pin.token,pin.captured_head)):
                    raise StoreConflictError('proof opening cleanup lost exact owned pin')
                for table in ('pin_receipts','pin_attempts'):
                    if store.db.execute('SELECT 1 FROM main.'+table+' WHERE pin_token=? LIMIT 1',(pin.token,)).fetchone():
                        raise StoreConflictError('proof opening cleanup cannot abandon publication state')
                store.db.execute('DELETE FROM main.generation_pins WHERE token=?',(pin.token,))
            store.db.commit()
    finally:
        if store.db.in_transaction:store.db.rollback()
        store.close()
