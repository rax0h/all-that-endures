"""Production version/event content; complete World authority remains gated.

The public writer composes ordinary and scoped proofs in the existing store
transaction. No format capability, alternate publisher or clean cache.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,_segment_checksum,_framed_sha
from .persistence_lazy_store import _version_checksum
from .persistence_proof_content import _namespace,_integer,version_key,version_commitment,segment_key,segment_commitment
from .persistence_proof_nodes import Root,_digest,key_locator
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_batch import update_sorted
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight
from .persistence_proof_version import VersionCertificate,RawVersion,version_domain,certificate_commitment as version_certificate_commitment,read_version_bytes
from .persistence_proof_occurrence import _require_indexes

MAX_BODY_BYTES=64*1024*1024
_ROOT_SCHEMA='CREATE TABLE ate_content_generations(generation INTEGER PRIMARY KEY,roots BLOB NOT NULL,certificate BLOB NOT NULL,parent_commitment BLOB,pin_token TEXT NOT NULL,commit_token BLOB NOT NULL,row_checksum BLOB NOT NULL)'
_NODE_SCHEMA='CREATE TABLE ate_proof_nodes (map_domain BLOB NOT NULL,digest BLOB NOT NULL CHECK(length(digest)=32),node_bytes BLOB NOT NULL CHECK(length(node_bytes)<=696),PRIMARY KEY(map_domain,digest)) WITHOUT ROWID'


class ContentProofBudgetError(StoreError):pass


@dataclass(frozen=True)
class ContentCertificate:
    store_identity: str
    generation: int
    codec_version: int
    versions: Root
    events: Root


@dataclass(frozen=True)
class RawEventSegment:
    payload: bytes
    first_id: bytes
    last_id: bytes
    element_count: int
    created_generation: int


def event_domain(store_identity,codec_version):return _digest(b'ate-event-content-domain/1',_namespace(store_identity),_integer(codec_version,1))


def _map(store,event=False):
    domain=(event_domain if event else version_domain)(store.store_identity,store.codec.version);nodes=ProofNodeStore(store.db)
    return ProofMap(domain,lambda d:nodes.read(domain,d),lambda d,raw:nodes.write(domain,d,raw))


def _root_bytes(cert):return b''.join(r.digest+r.count.to_bytes(8,'big') for r in (cert.versions,cert.events))


def certificate_commitment(cert):
    if type(cert) is not ContentCertificate or type(cert.generation) is not int or not 0<=cert.generation<2**63:raise StoreIntegrityError('invalid content publication certificate')
    for root,domain in ((cert.versions,version_domain(cert.store_identity,cert.codec_version)),(cert.events,event_domain(cert.store_identity,cert.codec_version))):ProofMap(domain,None,None)._reference(root)
    return _digest(b'ate-content-publication-certificate/1',_namespace(cert.store_identity),_integer(cert.codec_version,1),cert.generation.to_bytes(8,'big'),_root_bytes(cert))


def _authority(store,pin,cert,expected):
    if type(expected) is not bytes or len(expected)!=32 or certificate_commitment(cert)!=expected:raise StoreIntegrityError('content publication authority disagreement')
    if (cert.store_identity!=store.store_identity or cert.store_identity!=pin.store_identity or cert.codec_version!=store.codec.version or cert.generation!=pin.captured_head):raise StoreConflictError('content publication context disagreement')


def _schemas(db):
    for schema in ('sqlite_schema','sqlite_temp_schema'):
        if db.execute("SELECT 1 FROM "+schema+" WHERE type='trigger' LIMIT 1").fetchone() is not None:raise StoreError('content proof source cannot contain database triggers')
    for sql in (_ROOT_SCHEMA,_NODE_SCHEMA):
        name=sql.split('(')[0].split()[2]
        row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=8192 THEN sql END FROM sqlite_schema WHERE type='table' AND name=?",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(sql.lower().split()):raise StoreError('content schemas require explicit verified construction')


def _row_checksum(cert,parent,writer,token):return _digest(b'ate-content-generation-row/1',certificate_commitment(cert),parent or b'',writer.encode('ascii'),token)


def _write_root(store,cert,*,parent=None,writer='',token=b''):
    expected=certificate_commitment(cert)
    store.db.execute('INSERT INTO ate_content_generations VALUES(?,?,?,?,?,?,?)',(cert.generation,_root_bytes(cert),expected,parent,writer,token,_row_checksum(cert,parent,writer,token)))
    return cert,expected


def _load_root(store,generation):
    row=store.db.execute("SELECT CASE WHEN typeof(roots)='blob' AND length(roots)=80 THEN roots END,CASE WHEN typeof(certificate)='blob' AND length(certificate)=32 THEN certificate END,CASE WHEN typeof(parent_commitment)='blob' AND length(parent_commitment)=32 THEN parent_commitment END,typeof(parent_commitment),CASE WHEN typeof(pin_token)='text' AND length(CAST(pin_token AS BLOB))<=4096 THEN pin_token END,CASE WHEN typeof(commit_token)='blob' AND length(commit_token)<=65536 THEN commit_token END,CASE WHEN typeof(row_checksum)='blob' AND length(row_checksum)=32 THEN row_checksum END FROM ate_content_generations WHERE generation=?",(generation,)).fetchone()
    if row is None:raise StoreIntegrityError('missing current/retained content publication root')
    raw,expected,parent,parent_type,writer,token,checksum=row
    if type(raw) is not bytes or parent_type not in ('null','blob') or parent_type=='blob' and parent is None or type(writer) is not str or type(token) is not bytes:raise StoreIntegrityError('invalid content generation source')
    roots=tuple(Root(raw[i:i+32],int.from_bytes(raw[i+32:i+40],'big')) for i in (0,40))
    cert=ContentCertificate(store.store_identity,generation,store.codec.version,*roots)
    try:actual=_row_checksum(cert,parent,writer,token)
    except UnicodeError as exc:raise StoreIntegrityError('invalid content writer token') from exc
    if certificate_commitment(cert)!=expected or checksum!=actual:raise StoreIntegrityError('content generation row checksum disagreement')
    return (cert,expected),parent,writer,token


def _budgets(body,metadata):
    if type(body) is not int or not 1<=body<=MAX_BODY_BYTES or type(metadata) is not int or not 1<=metadata<=MAX_BODY_BYTES:raise StoreIntegrityError('invalid content source byte budgets')


@contextmanager
def _snapshot(store,pin,cert,expected,metadata):
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,cert,expected)
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):raise StoreError('content source cannot borrow arbitrary transaction')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,metadata)) as generation:
        head=int(store._checked_head_row()[0])
        if generation not in (head,head-1):raise StoreConflictError('content pin outside retained generations')
        _schemas(store.db)
        if _load_root(store,generation)[0]!=(cert,expected):raise StoreIntegrityError('accepted content source root disagreement')
        yield generation


def _version_value(namespace,key,row,codec):return version_commitment(namespace,key,valid_from=row.valid_from,codec_version=codec,record_schema=row.record_schema,memberships=row.memberships,payload=row.payload)


def _source_version(store,generation,namespace,key,*,max_bytes=MAX_BODY_BYTES):
    if 'lazy_record_interval' not in store._interval_indexes:raise StoreError('content cannot use legacy version fallback')
    _require_indexes(store.db,include_order=False,intervals=('lazy_record_interval',))
    body_ok="typeof(payload)='blob' AND typeof(memberships)='blob' AND length(payload)+length(memberships)<=?"
    # This internal path uses a validated literal budget, avoiding parameters
    # hidden inside the interval helper's fixed predicate values.
    body_ok=body_ok.replace('?',str(max_bytes))
    columns=("CASE WHEN typeof(valid_from)='integer' THEN valid_from END,CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        f"CASE WHEN {body_ok} THEN payload END,CASE WHEN {body_ok} THEN memberships END,"
        "CASE WHEN typeof(record_schema)='integer' THEN record_schema END,CASE WHEN typeof(codec_version)='integer' THEN codec_version END,"
        "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END,"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")
    rows=store._interval_rows('lazy_record_versions',columns,('namespace','typed_key'),(namespace,key),generation,'lazy_record_interval',limit=2)
    if len(rows)>1:raise StoreIntegrityError('overlapping content source versions')
    if not rows:return None
    start,end,end_type,payload,members,schema,codec,checksum,row_hash=rows[0]
    if (type(start) is not int or not 0<=start<=generation or end_type not in ('null','integer')
            or end_type=='integer' and (type(end) is not int or end<=generation or end<=start)
            or type(payload) is not bytes or type(members) is not bytes or type(schema) is not int or schema<1
            or codec!=store.codec.version or checksum!=_framed_sha(b'lazy-payload-v1',payload)
            or row_hash!=_version_checksum(namespace,key,schema,codec,start,end,members,payload)):raise StoreIntegrityError('invalid or oversized physical version content')
    store._payload_check_reads+=1;store._payload_check_bytes+=len(payload)
    return RawVersion(payload,members,schema,start,end)


def _event_value(namespace,ordinal,row,codec):return segment_commitment(namespace,ordinal,created_generation=row.created_generation,codec_version=codec,element_count=row.element_count,first_id=row.first_id,last_id=row.last_id,payload=row.payload)


def _source_event(store,generation,namespace,ordinal,body,metadata):
    row=store.db.execute("SELECT CASE WHEN typeof(payload)='blob' THEN length(payload) END,CASE WHEN typeof(payload)='blob' AND length(payload)<=? THEN payload END,CASE WHEN typeof(first_id)='blob' AND typeof(last_id)='blob' THEN length(first_id)+length(last_id) END,CASE WHEN typeof(first_id)='blob' AND typeof(last_id)='blob' AND length(first_id)+length(last_id)<=? THEN first_id END,CASE WHEN typeof(first_id)='blob' AND typeof(last_id)='blob' AND length(first_id)+length(last_id)<=? THEN last_id END,CASE WHEN typeof(codec_version)='integer' THEN codec_version END,CASE WHEN typeof(element_count)='integer' THEN element_count END,CASE WHEN typeof(created_generation)='integer' THEN created_generation END,CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END FROM segments WHERE namespace=? AND ordinal=?",(body,metadata,metadata,namespace,ordinal)).fetchone()
    if row is None:return None
    size,payload,id_size,first,last,codec,count,created,checksum=row
    if type(size) is not int or type(id_size) is not int:raise StoreIntegrityError('invalid event source storage classes')
    if size>body or id_size>metadata:raise ContentProofBudgetError('event source exceeds explicit body/ID budget')
    if (type(payload) is not bytes or type(first) is not bytes or type(last) is not bytes or codec!=store.codec.version
            or type(count) is not int or count<0 or type(created) is not int or not 0<=created<=generation
            or checksum!=_segment_checksum(namespace,ordinal,first,last,count,codec,created,payload)):raise StoreIntegrityError('event source bytes/checksum disagreement')
    store._payload_check_reads+=1;store._payload_check_bytes+=len(payload)
    return RawEventSegment(payload,first,last,count,created)


def _guard_construction(store,generation,body,metadata):
    fixed=("typeof(namespace)='text' AND length(CAST(namespace AS BLOB))>0 AND instr(namespace,char(0))=0 "
        "AND typeof(codec_version)='integer' AND codec_version="+str(store.codec.version))
    version=fixed+" AND typeof(typed_key)='blob' AND length(CAST(namespace AS BLOB))+length(typed_key)<="+str(metadata)+" AND typeof(payload)='blob' AND typeof(memberships)='blob' AND length(payload)+length(memberships)<="+str(body)+" AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 AND typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 AND typeof(record_schema)='integer' AND record_schema>0 AND typeof(valid_from)='integer' AND valid_from>=0 AND valid_from<="+str(generation)+" AND typeof(valid_to) IN ('null','integer')"
    event=fixed+" AND length(CAST(namespace AS BLOB))<="+str(metadata)+" AND typeof(ordinal)='integer' AND ordinal>=0 AND typeof(payload)='blob' AND length(payload)<="+str(body)+" AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 AND typeof(first_id)='blob' AND typeof(last_id)='blob' AND length(first_id)+length(last_id)<="+str(metadata)+" AND typeof(element_count)='integer' AND element_count>=0 AND typeof(created_generation)='integer' AND created_generation>=0 AND created_generation<="+str(generation)
    for table,valid in (('lazy_record_versions',version),('segments',event)):
        if store.db.execute('SELECT 1 FROM '+table+' WHERE NOT('+valid+') LIMIT 1').fetchone() is not None:raise ContentProofBudgetError('invalid or oversized construction content source')


def bootstrap_content_proofs(store,pin,*,max_body_bytes=MAX_BODY_BYTES,max_metadata_bytes=1048576):
    _require_closed_codec(store,allow_typed=True);_budgets(max_body_bytes,max_metadata_bytes)
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('content construction requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        _closed_snapshot_preflight(store,max_metadata_bytes);generation=store._require_pin(pin)
        if generation!=int(store._checked_head_row()[0]):raise StoreConflictError('content construction requires current pin')
        _guard_construction(store,generation,max_body_bytes,max_metadata_bytes);store.verify_all()
        ProofNodeStore(store.db).create_schema();store.db.execute(_ROOT_SCHEMA.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1));_schemas(store.db)
        if store.db.execute('SELECT 1 FROM ate_content_generations WHERE generation=?',(generation,)).fetchone() is not None:raise StoreIntegrityError('content constructor cannot replace existing generation')
        store.db.execute('CREATE TEMP TABLE ate_content_delta(kind INTEGER,locator BLOB,key BLOB,value BLOB,PRIMARY KEY(kind,locator)) WITHOUT ROWID')
        for event in (False,True):
            m=_map(store,event)
            if event:
                cursor=store.db.execute('SELECT namespace,ordinal FROM segments')
                def values():
                    for ns,ordinal in cursor:
                        row=_source_event(store,generation,ns,ordinal,max_body_bytes,max_metadata_bytes)
                        yield segment_key(ns,ordinal),_event_value(ns,ordinal,row,store.codec.version)
            else:
                cursor=store.db.execute('SELECT namespace,typed_key FROM lazy_record_versions WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(generation,generation))
                def values():
                    for ns,key in cursor:
                        row=_source_version(store,generation,ns,key,max_bytes=max_body_bytes)
                        yield version_key(ns,key),_version_value(ns,key,row,store.codec.version)
            try:
                for key,value in values():store.db.execute('INSERT INTO ate_content_delta VALUES(?,?,?,?)',(int(event),key_locator(m.map_domain,key),key,value))
            finally:cursor.close()
        roots=[]
        for event in (False,True):
            m=_map(store,event);cursor=store.db.execute('SELECT key,value FROM ate_content_delta WHERE kind=? ORDER BY locator',(int(event),))
            try:roots.append(update_sorted(m,m.empty,cursor))
            finally:cursor.close()
        store.db.execute('DROP TABLE ate_content_delta');result=_write_root(store,ContentCertificate(store.store_identity,generation,store.codec.version,*roots))
        store.db.commit();return result
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False


def version_certificate(store,pin,certificate,expected,*,max_metadata_bytes=1048576):
    _budgets(1048576,max_metadata_bytes)
    with _snapshot(store,pin,certificate,expected,max_metadata_bytes):
        cert=VersionCertificate(store.store_identity,certificate.generation,store.codec.version,certificate.versions)
        return cert,version_certificate_commitment(cert)


def read_version_content_bytes(store,pin,certificate,expected,namespace,typed_key,*,expected_record_schema,max_bytes=1048576,max_metadata_bytes=1048576):
    _budgets(max_bytes,max_metadata_bytes)
    if type(typed_key) is not bytes or len(_namespace(namespace))+len(typed_key)>max_metadata_bytes:raise ContentProofBudgetError('version locator exceeds explicit metadata path')
    with _snapshot(store,pin,certificate,expected,max_metadata_bytes):
        cert=VersionCertificate(store.store_identity,certificate.generation,store.codec.version,certificate.versions)
        return read_version_bytes(store,pin,cert,version_certificate_commitment(cert),namespace,typed_key,expected_record_schema=expected_record_schema,max_bytes=max_bytes,max_metadata_bytes=max_metadata_bytes)


def read_event_content_bytes(store,pin,certificate,expected,namespace,ordinal,*,max_bytes=1048576,max_metadata_bytes=1048576):
    _budgets(max_bytes,max_metadata_bytes)
    if type(ordinal) is not int or not 0<=ordinal<2**63 or len(_namespace(namespace))>max_metadata_bytes:raise StoreIntegrityError('invalid event locator')
    with _snapshot(store,pin,certificate,expected,max_metadata_bytes) as generation:
        wanted=_map(store,True).get(certificate.events,segment_key(namespace,ordinal))
        if wanted is None:return None
        row=_source_event(store,generation,namespace,ordinal,max_bytes,max_metadata_bytes)
        if row is None or _event_value(namespace,ordinal,row,store.codec.version)!=wanted:raise StoreIntegrityError('event source disagrees with accepted content root')
        return row


@dataclass(frozen=True)
class ContentProofCommit:
    commit: object
    certificate: ContentCertificate | None
    commitment: bytes | None
    scope: object


@dataclass
class _ContentProofRequest:
    store: object
    pin: object
    parent: ContentCertificate
    expected_parent: bytes
    encoded_token: bytes
    data_version: int
    successor: tuple | None = None


def _check_request(store,pin,request):
    from .persistence_sqlite_guard import GuardedConnection
    if type(request) is not _ContentProofRequest or request.store is not store or request.pin!=pin:raise StoreIntegrityError('invalid private content publication request')
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,request.parent,request.expected_parent)
    if type(store.db) is not GuardedConnection:raise StoreError('content publication requires tracked SQL callback guard')
    if type(request.encoded_token) is not bytes or len(request.encoded_token)>65536:raise ContentProofBudgetError('content commit token exceeds explicit metadata path')
    if store.db.execute('PRAGMA data_version').fetchone()[0]!=request.data_version:raise StoreConflictError('external write invalidated content parent epoch')


def _guard_content_parent(store,request,version_prepared,segment_prepared):
    """Authenticate actual old content within the existing locked writer TX."""
    _check_request(store,request.pin,request)
    if not store.db.in_transaction:raise StoreError('content parent check requires existing writer transaction')
    _schemas(store.db)
    if _load_root(store,request.parent.generation)[0]!=(request.parent,request.expected_parent):raise StoreIntegrityError('accepted content parent changed')
    m=_map(store)
    for item in version_prepared:
        ns,key=item['namespace'],item['typed_key']
        if len(_namespace(ns))+len(key)>1048576:raise ContentProofBudgetError('changed version locator exceeds metadata path')
        if not item['change'].delete and (type(item['payload']) is not bytes or type(item['memberships_blob']) is not bytes or len(item['payload'])+len(item['memberships_blob'])>MAX_BODY_BYTES):raise ContentProofBudgetError('prepared version exceeds content body path')
        wanted=m.get(request.parent.versions,version_key(ns,key));row=_source_version(store,request.parent.generation,ns,key)
        actual=None if row is None else _version_value(ns,key,row,store.codec.version)
        if wanted!=actual:raise StoreIntegrityError('actual predecessor version disagrees with accepted parent content')
    events=_map(store,True)
    for item in segment_prepared:
        ns=item['namespace'];segment=item['segment']
        if (len(_namespace(ns))>1048576 or len(item['first_id'])+len(item['last_id'])>1048576
                or len(item['payload'])>MAX_BODY_BYTES):raise ContentProofBudgetError('prepared event exceeds explicit content path')
        if events.get(request.parent.events,segment_key(ns,segment.ordinal)) is not None:raise StoreConflictError('event append already belongs to accepted parent')


def _stage_content_proof(store,request,new_generation,version_prepared,segment_prepared,encoded_token):
    _check_request(store,request.pin,request)
    if not store.db.in_transaction:raise StoreError('content publication requires existing writer transaction')
    if new_generation!=request.parent.generation+1 or encoded_token!=request.encoded_token:raise StoreConflictError('content successor generation/token disagreement')
    if store.db.execute('SELECT generation,parent_generation FROM save_head WHERE singleton=1').fetchone()!=(new_generation,request.parent.generation):raise StoreIntegrityError('content writer lost successor head')
    _schemas(store.db)
    if _load_root(store,request.parent.generation)[0]!=(request.parent,request.expected_parent):raise StoreIntegrityError('content parent root changed before publication')
    store.db.execute('CREATE TEMP TABLE ate_content_delta(kind INTEGER,locator BLOB,key BLOB,value BLOB,PRIMARY KEY(kind,locator)) WITHOUT ROWID')
    versions=_map(store);events=_map(store,True)
    for item in version_prepared:
        ns,key=item['namespace'],item['typed_key'];encoded=version_key(ns,key);row=_source_version(store,new_generation,ns,key)
        if item['change'].delete:
            if row is not None:raise StoreIntegrityError('actual version deletion disagrees with prepared transition')
            value=None
        else:
            if row is None or (row.payload,row.memberships,row.record_schema,row.valid_from,row.valid_to)!=(item['payload'],item['memberships_blob'],item['change'].record_schema,new_generation,None):raise StoreIntegrityError('actual successor version disagrees with prepared bytes')
            value=_version_value(ns,key,row,store.codec.version)
        store.db.execute('INSERT INTO ate_content_delta VALUES(?,?,?,?)',(0,key_locator(versions.map_domain,encoded),encoded,value))
    for item in segment_prepared:
        ns=item['namespace'];segment=item['segment'];ordinal=segment.ordinal
        row=_source_event(store,new_generation,ns,ordinal,MAX_BODY_BYTES,1048576)
        if row is None or (row.payload,row.first_id,row.last_id,row.element_count,row.created_generation)!=(item['payload'],item['first_id'],item['last_id'],segment.element_count,new_generation):raise StoreIntegrityError('actual event append disagrees with prepared bytes')
        encoded=segment_key(ns,ordinal);value=_event_value(ns,ordinal,row,store.codec.version)
        store.db.execute('INSERT INTO ate_content_delta VALUES(?,?,?,?)',(1,key_locator(events.map_domain,encoded),encoded,value))
    roots=[]
    for kind,m,parent in ((0,versions,request.parent.versions),(1,events,request.parent.events)):
        rows=store.db.execute('SELECT key,value FROM ate_content_delta WHERE kind=? ORDER BY locator',(kind,))
        try:roots.append(update_sorted(m,parent,rows))
        finally:rows.close()
    store.db.execute('DROP TABLE ate_content_delta')
    cert=ContentCertificate(store.store_identity,new_generation,store.codec.version,*roots)
    request.successor=_write_root(store,cert,parent=request.expected_parent,writer=request.pin.token,token=encoded_token)


def commit_content_proof(store,pin,certificate,expected,*,scope_authority,record_authority,commit_token,**arguments):
    from .persistence_proof_scope import commit_scope_proof
    if any(k in arguments for k in ('_content_proof','_scope_proof','_record_proof')):raise StoreError('private publication requests cannot be supplied by wrapper caller')
    if any(type(p) is not tuple or len(p)!=2 for p in (scope_authority,record_authority)):raise StoreIntegrityError('unified save requires exact record and scope authorities')
    if store.db.in_transaction:raise StoreError('content save requires owned writer operation')
    with _snapshot(store,pin,certificate,expected,1048576):data_version=store.db.execute('PRAGMA data_version').fetchone()[0]
    request=_ContentProofRequest(store,pin,certificate,expected,store.codec.encode(commit_token),data_version);_check_request(store,pin,request)
    scope=commit_scope_proof(store,pin,*scope_authority,record_authority=record_authority,commit_token=commit_token,_content_proof=request,**arguments)
    result=scope.commit
    if result.outcome=='committed':
        if request.successor is None:raise StoreIntegrityError('missing content publication result')
        return ContentProofCommit(result,*request.successor,scope)
    return ContentProofCommit(result,certificate if result.outcome=='not_committed' else None,expected if result.outcome=='not_committed' else None,scope)


def resolve_content_commit(store,pin,certificate,expected,*,scope_authority,record_authority,commit_token):
    from .persistence_proof_scope import resolve_scope_commit
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,certificate,expected)
    if any(type(p) is not tuple or len(p)!=2 for p in (scope_authority,record_authority)):raise StoreIntegrityError('unified recovery requires exact record and scope authorities')
    if store.db.in_transaction:raise StoreError('content recovery requires owned operation')
    encoded=store.codec.encode(commit_token)
    scope=resolve_scope_commit(store,pin,*scope_authority,record_authority=record_authority,commit_token=commit_token);result=scope.commit
    if result.outcome=='conflict':return ContentProofCommit(result,None,None,scope)
    if result.outcome=='not_committed' and (result.generation!=certificate.generation or result.pin!=pin):raise StoreConflictError('noncommitted content recovery parent disagreement')
    with store.read_snapshot(result.pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
        _schemas(store.db);pair,parent,writer,token=_load_root(store,result.generation)
        if result.outcome=='not_committed':
            if pair!=(certificate,expected):raise StoreIntegrityError('resolved content parent root missing or changed')
        elif parent!=expected or writer!=pin.token or token!=encoded or result.generation!=certificate.generation+1:raise StoreIntegrityError('resolved content disagrees with exact parent/token/receipt')
        return ContentProofCommit(result,*pair,scope)
