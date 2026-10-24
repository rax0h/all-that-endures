"""Explicit retained ordinary content. No World admission or format activation.

Full bootstrap is archive work. Raw reads require external accepted authority;
content does not establish query membership, identity or complete World state.
"""
from dataclasses import dataclass
import sqlite3
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,_record_checksum
from .persistence_proof_content import _namespace,_integer,record_key,record_commitment
from .persistence_proof_nodes import Root,_digest,key_locator
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_batch import update_sorted
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight,ProjectionProofBudgetError
from .persistence_proof_version import VersionProofBudgetError

MAX_BODY_BYTES=64*1024*1024
_BODY_SCHEMA=('CREATE TABLE ate_retained_records(commitment BLOB PRIMARY KEY,namespace TEXT NOT NULL,typed_key BLOB NOT NULL,'
    'payload BLOB NOT NULL,payload_checksum TEXT NOT NULL,codec_version INTEGER NOT NULL,record_schema INTEGER NOT NULL,'
    'last_changed_generation INTEGER NOT NULL) WITHOUT ROWID')
_ROOT_SCHEMA=('CREATE TABLE ate_record_roots(generation INTEGER PRIMARY KEY,root_digest BLOB NOT NULL,root_count INTEGER NOT NULL,'
    'certificate BLOB NOT NULL,parent_commitment BLOB,pin_token TEXT NOT NULL,commit_token BLOB NOT NULL,row_checksum BLOB NOT NULL)')
_NODE_SCHEMA=('CREATE TABLE ate_proof_nodes (map_domain BLOB NOT NULL,digest BLOB NOT NULL CHECK(length(digest)=32),'
    'node_bytes BLOB NOT NULL CHECK(length(node_bytes)<=696),PRIMARY KEY(map_domain,digest)) WITHOUT ROWID')


class RecordProofBudgetError(StoreError):
    """A separately budgeted checked ordinary-content path is required."""


@dataclass(frozen=True)
class RecordCertificate:
    store_identity: str
    generation: int
    codec_version: int
    root: Root


@dataclass(frozen=True)
class RawRecord:
    payload: bytes
    record_schema: int
    last_changed_generation: int


def record_domain(store_identity,codec_version):
    return _digest(b'ate-record-proof-domain/1',_namespace(store_identity),_integer(codec_version,1))


def certificate_commitment(certificate):
    if (type(certificate) is not RecordCertificate or type(certificate.generation) is not int
            or not 0<=certificate.generation<2**63):raise StoreIntegrityError('invalid record certificate')
    domain=record_domain(certificate.store_identity,certificate.codec_version)
    ProofMap(domain,None,None)._reference(certificate.root)
    return _digest(b'ate-record-certificate/1',domain,certificate.generation.to_bytes(8,'big'),
        certificate.root.digest,certificate.root.count.to_bytes(8,'big'))


def _authority(store,pin,cert,expected):
    if type(expected) is not bytes or len(expected)!=32 or certificate_commitment(cert)!=expected:
        raise StoreIntegrityError('record certificate authority disagreement')
    if (cert.store_identity!=store.store_identity or cert.store_identity!=pin.store_identity
            or cert.generation!=pin.captured_head or cert.codec_version!=store.codec.version):
        raise StoreConflictError('record proof store/codec/pin disagreement')


def _schemas(db):
    for name,expected in (('ate_retained_records',_BODY_SCHEMA),('ate_record_roots',_ROOT_SCHEMA),('ate_proof_nodes',_NODE_SCHEMA)):
        row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=8192 THEN sql END "
            "FROM sqlite_schema WHERE type='table' AND name=?",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(expected.lower().split()):
            raise StoreError('record proof schema requires explicit verified construction')


def _map(store):
    domain=record_domain(store.store_identity,store.codec.version);nodes=ProofNodeStore(store.db)
    return ProofMap(domain,lambda d:nodes.read(domain,d),lambda d,raw:nodes.write(domain,d,raw))


def _root_checksum(cert,parent,pin_token,commit_token):
    return _digest(b'ate-record-root-row/1',record_domain(cert.store_identity,cert.codec_version),
        cert.generation.to_bytes(8,'big'),cert.root.digest,cert.root.count.to_bytes(8,'big'),
        certificate_commitment(cert),parent or b'',pin_token.encode('ascii'),commit_token)


def _write_root(store,cert,*,parent=None,pin_token='',commit_token=b''):
    expected=certificate_commitment(cert)
    store.db.execute('INSERT INTO ate_record_roots VALUES(?,?,?,?,?,?,?,?)',(cert.generation,cert.root.digest,cert.root.count,
        expected,parent,pin_token,commit_token,_root_checksum(cert,parent,pin_token,commit_token)))
    return cert,expected


def _load_root(store,generation):
    row=store.db.execute("SELECT CASE WHEN typeof(root_digest)='blob' AND length(root_digest)=32 THEN root_digest END,"
        "CASE WHEN typeof(root_count)='integer' THEN root_count END,"
        "CASE WHEN typeof(certificate)='blob' AND length(certificate)=32 THEN certificate END,"
        "CASE WHEN typeof(parent_commitment)='blob' AND length(parent_commitment)=32 THEN parent_commitment END,typeof(parent_commitment),"
        "CASE WHEN typeof(pin_token)='text' AND length(CAST(pin_token AS BLOB))<=4096 THEN pin_token END,"
        "CASE WHEN typeof(commit_token)='blob' AND length(commit_token)<=65536 THEN commit_token END,"
        "CASE WHEN typeof(row_checksum)='blob' AND length(row_checksum)=32 THEN row_checksum END "
        'FROM ate_record_roots WHERE generation=?',(generation,)).fetchone()
    if row is None:raise StoreIntegrityError('missing current/retained ordinary proof root')
    digest,count,expected,parent,parent_type,pin_token,token,checksum=row
    if parent_type not in ('null','blob') or parent_type=='blob' and parent is None or type(pin_token) is not str or type(token) is not bytes:
        raise StoreIntegrityError('invalid record root metadata')
    cert=RecordCertificate(store.store_identity,generation,store.codec.version,Root(digest,count))
    if certificate_commitment(cert)!=expected:raise StoreIntegrityError('record root certificate disagreement')
    try:actual=_root_checksum(cert,parent,pin_token,token)
    except UnicodeError as exc:raise StoreIntegrityError('invalid record root writer token') from exc
    if checksum!=actual:raise StoreIntegrityError('record root row checksum disagreement')
    return (cert,expected),parent,pin_token,token


def _retain_body(store,namespace,key,payload,checksum,codec,schema,revision):
    if (type(payload) is not bytes or len(payload)>MAX_BODY_BYTES):raise RecordProofBudgetError('ordinary body exceeds retained path budget')
    if checksum!=_record_checksum(namespace,key,schema,codec,revision,payload):raise StoreIntegrityError('ordinary source checksum disagreement')
    wanted=record_commitment(namespace,key,last_changed_generation=revision,codec_version=codec,record_schema=schema,payload=payload)
    values=(wanted,namespace,key,payload,checksum,codec,schema,revision)
    cursor=store.db.execute('INSERT OR IGNORE INTO ate_retained_records VALUES(?,?,?,?,?,?,?,?)',values)
    if not cursor.rowcount:
        # Compare in SQLite: a conflicting corrupted body must not be copied
        # into Python before its declared length has been bounded.
        row=store.db.execute('SELECT 1 FROM ate_retained_records WHERE commitment=? AND namespace=? AND typed_key=? '
            'AND payload=? AND payload_checksum=? AND codec_version=? AND record_schema=? AND last_changed_generation=?',values).fetchone()
        if row is None:raise StoreIntegrityError('conflicting immutable ordinary body')
    cursor.close();return wanted


def bootstrap_record_proofs(store,pin,*,max_body_bytes=MAX_BODY_BYTES,max_metadata_bytes=1048576):
    """Explicit full audited construction, never called by ordinary open/save."""
    _require_closed_codec(store,allow_typed=True)
    if type(max_body_bytes) is not int or not 1<=max_body_bytes<=MAX_BODY_BYTES:raise StoreIntegrityError('invalid record construction body budget')
    if type(max_metadata_bytes) is not int or not 1<=max_metadata_bytes<=64*1024*1024:raise StoreIntegrityError('invalid record construction metadata budget')
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('record bootstrap requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        _closed_snapshot_preflight(store,max_metadata_bytes);generation=store._require_pin(pin)
        if generation!=int(store._checked_head_row()[0]):raise StoreConflictError('record bootstrap requires current generation')
        # Do not let the inherited full audit transfer unsupported bodies first.
        valid=("typeof(namespace)='text' AND length(CAST(namespace AS BLOB))>0 AND instr(namespace,char(0))=0 "
            "AND typeof(typed_key)='blob' AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 "
            "AND typeof(codec_version)='integer' AND codec_version="+str(store.codec.version)+
            " AND typeof(record_schema)='integer' AND record_schema>0 AND typeof(last_changed_generation)='integer' "
            "AND last_changed_generation>=0 AND last_changed_generation<="+str(generation))
        locator="CASE WHEN typeof(namespace)='text' AND typeof(typed_key)='blob' THEN length(CAST(namespace AS BLOB))+length(typed_key) END"
        probe=store.db.execute('SELECT '+valid+",CASE WHEN typeof(payload)='blob' THEN length(payload) END,"+locator+
            ' FROM records WHERE NOT('+valid+") OR typeof(payload)!='blob' OR length(payload)>? OR "+locator+'>? LIMIT 1',
            (max_body_bytes,max_metadata_bytes)).fetchone()
        if probe is not None:
            if probe[0]!=1 or type(probe[1]) is not int:raise StoreIntegrityError('invalid ordinary construction source metadata/body')
            raise RecordProofBudgetError('ordinary source exceeds construction body/locator budget')
        store.verify_all()
        nodes=ProofNodeStore(store.db);nodes.create_schema()
        for sql in (_BODY_SCHEMA,_ROOT_SCHEMA):store.db.execute(sql.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1))
        _schemas(store.db);m=_map(store)
        store.db.execute('CREATE TEMP TABLE ate_record_delta(locator BLOB PRIMARY KEY,key BLOB,value BLOB) WITHOUT ROWID')
        cursor=store.db.execute('SELECT namespace,typed_key,payload,payload_checksum,codec_version,record_schema,last_changed_generation FROM records')
        try:
            for ns,key,payload,checksum,codec,schema,revision in cursor:
                if type(revision) is not int or not 0<=revision<=generation:raise StoreIntegrityError('ordinary source revision exceeds construction generation')
                value=_retain_body(store,ns,key,payload,checksum,codec,schema,revision);encoded=record_key(ns,key)
                store.db.execute('INSERT INTO ate_record_delta VALUES(?,?,?)',(key_locator(m.map_domain,encoded),encoded,value))
        finally:cursor.close()
        delta=store.db.execute('SELECT key,value FROM ate_record_delta ORDER BY locator')
        try:root=update_sorted(m,m.empty,delta)
        finally:delta.close()
        store.db.execute('DROP TABLE ate_record_delta')
        result=_write_root(store,RecordCertificate(store.store_identity,generation,store.codec.version,root))
        store.db.commit();return result
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False


def read_record_proof_bytes(store,pin,certificate,expected,namespace,typed_key,*,expected_record_schema,max_bytes=1048576,max_metadata_bytes=1048576):
    _authority(store,pin,certificate,expected);_require_closed_codec(store,allow_typed=True)
    ns=_namespace(namespace)
    if (type(typed_key) is not bytes or type(expected_record_schema) is not int or expected_record_schema<1
            or type(max_bytes) is not int or not 1<=max_bytes<=MAX_BODY_BYTES or type(max_metadata_bytes) is not int
            or not 1<=max_metadata_bytes<=64*1024*1024):raise StoreIntegrityError('invalid retained record read arguments')
    if len(ns)+len(typed_key)>max_metadata_bytes:raise RecordProofBudgetError('record locator exceeds metadata budget')
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('retained record cannot borrow arbitrary transaction')
    try:
        with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,max_metadata_bytes)) as generation:
            head=int(store._checked_head_row()[0])
            if generation not in (head,head-1):raise StoreConflictError('record pin outside retained generation window')
            _schemas(store.db)
            if _load_root(store,generation)[0]!=(certificate,expected):raise StoreIntegrityError('record source root disagreement')
            wanted=_map(store).get(certificate.root,record_key(namespace,typed_key))
            if wanted is None:return None
            row=store.db.execute("SELECT CASE WHEN typeof(payload)='blob' THEN length(payload) END,"
                "CASE WHEN typeof(payload)='blob' AND length(payload)<=? THEN payload END,"
                "typeof(namespace)='text' AND typeof(typed_key)='blob' AND namespace=? AND typed_key=?,"
                "CASE WHEN typeof(record_schema)='integer' THEN record_schema END,"
                "CASE WHEN typeof(codec_version)='integer' THEN codec_version END,"
                "CASE WHEN typeof(last_changed_generation)='integer' THEN last_changed_generation END,"
                "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END "
                'FROM ate_retained_records WHERE commitment=?',(max_bytes,namespace,typed_key,wanted)).fetchone()
            if row is None or type(row[0]) is not int:raise StoreIntegrityError('missing or invalid retained ordinary body')
            size,payload,locator,schema,codec,revision,checksum=row
            if size>max_bytes:raise RecordProofBudgetError('retained ordinary body exceeds explicit read budget')
            if (type(payload) is not bytes or len(payload)!=size or locator!=1 or schema!=expected_record_schema
                    or codec!=certificate.codec_version or type(revision) is not int or not 0<=revision<=generation
                    or checksum!=_record_checksum(namespace,typed_key,schema,codec,revision,payload)
                    or record_commitment(namespace,typed_key,last_changed_generation=revision,codec_version=codec,record_schema=schema,payload=payload)!=wanted):
                raise StoreIntegrityError('retained ordinary bytes/root disagreement')
            store._payload_check_reads+=1;store._payload_check_bytes+=size
            return RawRecord(payload,schema,revision)
    except (VersionProofBudgetError,ProjectionProofBudgetError) as exc:raise RecordProofBudgetError(str(exc)) from exc


@dataclass(frozen=True)
class RecordProofCommit:
    commit: object
    certificate: RecordCertificate | None
    commitment: bytes | None


@dataclass
class _RecordProofRequest:
    store: object
    pin: object
    parent: RecordCertificate
    expected_parent: bytes
    encoded_token: bytes
    data_version: int
    successor: tuple | None = None


def _check_request(store,pin,request):
    if type(request) is not _RecordProofRequest or request.store is not store or request.pin!=pin:
        raise StoreIntegrityError('invalid private ordinary proof request')
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,request.parent,request.expected_parent)
    from .persistence_sqlite_guard import GuardedConnection
    if type(store.db) is not GuardedConnection:raise StoreError('ordinary proof save requires tracked SQL callback capability')
    if type(request.encoded_token) is not bytes or len(request.encoded_token)>65536:
        raise RecordProofBudgetError('ordinary proof commit token exceeds metadata path')
    if store.db.execute('PRAGMA data_version').fetchone()[0]!=request.data_version:
        raise StoreConflictError('external write invalidated ordinary proof parent operation')


def _checked_phase_hook(store,phase):
    """Proof-aware fault hooks may raise/read, never inject unlisted SQL writes."""
    db=store.db;was_transaction=db.in_transaction
    before=(db.total_changes,db.execute('PRAGMA schema_version').fetchone()[0])
    try:
        try:
            with db.readonly_callback():store._phase_hook(phase)
        except sqlite3.DatabaseError as exc:raise StoreIntegrityError('proof-aware fault hook attempted unsupported SQL') from exc
        after=(db.total_changes,db.execute('PRAGMA schema_version').fetchone()[0])
        if after!=before:raise StoreIntegrityError('proof-aware phase hook changed physical source')
    except BaseException:
        if not was_transaction and db.in_transaction:db.rollback()
        raise


def _stage_record_proof(store,request,new_generation,prepared,encoded_token):
    if type(request) is not _RecordProofRequest or request.store is not store or not store.db.in_transaction:
        raise StoreIntegrityError('ordinary proof publication requires existing writer transaction')
    if new_generation!=request.parent.generation+1 or encoded_token!=request.encoded_token:
        raise StoreConflictError('ordinary proof successor generation/token disagreement')
    if store.db.execute('PRAGMA data_version').fetchone()[0]!=request.data_version:
        raise StoreConflictError('external write invalidated ordinary proof publication')
    if store.db.execute('SELECT generation,parent_generation FROM save_head WHERE singleton=1').fetchone()!=(new_generation,request.parent.generation):
        raise StoreIntegrityError('ordinary proof writer transaction lost its successor head')
    _schemas(store.db)
    if _load_root(store,request.parent.generation)[0]!=(request.parent,request.expected_parent):
        raise StoreIntegrityError('ordinary proof accepted parent changed')
    m=_map(store)
    store.db.execute('CREATE TEMP TABLE ate_record_delta(locator BLOB PRIMARY KEY,key BLOB,value BLOB) WITHOUT ROWID')
    for item in prepared:
        change=item['change'];namespace=item['namespace'];key=item['typed_key'];payload=item['payload']
        encoded=record_key(namespace,key)
        if change.delete:
            if store.db.execute('SELECT 1 FROM records WHERE namespace=? AND typed_key=?',(namespace,key)).fetchone() is not None:
                raise StoreIntegrityError('ordinary proof delete disagrees with written source')
            wanted=None
        else:
            if type(payload) is not bytes or len(payload)>MAX_BODY_BYTES:raise RecordProofBudgetError('changed ordinary body exceeds retained path')
            row=store.db.execute("SELECT CASE WHEN typeof(payload)='blob' AND length(payload)<=? THEN payload END,"
                "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END,"
                "CASE WHEN typeof(codec_version)='integer' THEN codec_version END,"
                "CASE WHEN typeof(record_schema)='integer' THEN record_schema END,"
                "CASE WHEN typeof(last_changed_generation)='integer' THEN last_changed_generation END "
                "FROM records WHERE namespace=? AND typed_key=?",
                (len(payload),namespace,key)).fetchone()
            checksum=_record_checksum(namespace,key,change.record_schema,store.codec.version,new_generation,payload)
            if row!=(payload,checksum,store.codec.version,change.record_schema,new_generation):
                raise StoreIntegrityError('ordinary proof prepared bytes disagree with actual written row')
            store._payload_check_reads+=1;store._payload_check_bytes+=len(payload)
            wanted=_retain_body(store,namespace,key,payload,checksum,store.codec.version,change.record_schema,new_generation)
        store.db.execute('INSERT INTO ate_record_delta VALUES(?,?,?)',(key_locator(m.map_domain,encoded),encoded,wanted))
    delta=store.db.execute('SELECT key,value FROM ate_record_delta ORDER BY locator')
    try:root=update_sorted(m,request.parent.root,delta)
    finally:delta.close()
    store.db.execute('DROP TABLE ate_record_delta')
    certificate=RecordCertificate(store.store_identity,new_generation,store.codec.version,root)
    request.successor=_write_root(store,certificate,parent=request.expected_parent,pin_token=request.pin.token,commit_token=encoded_token)


def commit_record_proof(store,pin,certificate,expected,*,commit_token,**arguments):
    """Opt-in ordinary content root in the existing complete data transaction."""
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,certificate,expected)
    if '_record_proof' in arguments:raise StoreError('private proof request cannot be supplied by wrapper caller')
    if store.db.in_transaction:raise StoreError('proof-aware save requires owned writer operation')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
        _schemas(store.db)
        if _load_root(store,certificate.generation)[0]!=(certificate,expected):raise StoreIntegrityError('ordinary proof parent source disagreement')
        data_version=store.db.execute('PRAGMA data_version').fetchone()[0]
    request=_RecordProofRequest(store,pin,certificate,expected,store.codec.encode(commit_token),data_version)
    _check_request(store,pin,request)
    result=store.commit(pin,commit_token=commit_token,_record_proof=request,**arguments)
    if result.outcome=='committed':
        if request.successor is None:raise StoreIntegrityError('missing ordinary proof publication result')
        return RecordProofCommit(result,*request.successor)
    return RecordProofCommit(result,certificate if result.outcome=='not_committed' else None,expected if result.outcome=='not_committed' else None)


def resolve_record_commit(store,pin,certificate,expected,*,commit_token):
    """Resolve the existing exact attempt; never replay ordinary changes."""
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,certificate,expected)
    if store.db.in_transaction:raise StoreError('ordinary proof recovery requires owned operation')
    encoded=store.codec.encode(commit_token);result=store.resolve_commit(pin,commit_token)
    if result.outcome!='committed':
        if result.outcome=='not_committed' and (result.generation!=certificate.generation or result.pin!=pin):
            raise StoreConflictError('resolved noncommitted attempt does not match supplied ordinary parent')
        if result.outcome=='not_committed':
            with store.read_snapshot(result.pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
                _schemas(store.db)
                if _load_root(store,result.generation)[0]!=(certificate,expected):
                    raise StoreIntegrityError('resolved noncommitted ordinary parent root is missing or changed')
        return RecordProofCommit(result,certificate if result.outcome=='not_committed' else None,expected if result.outcome=='not_committed' else None)
    with store.read_snapshot(result.pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
        _schemas(store.db);pair,parent,writer,token=_load_root(store,result.generation)
        if (parent!=expected or writer!=pin.token or token!=encoded or result.generation!=certificate.generation+1):
            raise StoreIntegrityError('resolved ordinary proof disagrees with exact parent/token/receipt')
        return RecordProofCommit(result,*pair)
