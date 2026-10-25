"""Verified physical scope directories; no complete World/manifest capability.

Scope descriptors exclude generation/allocator so unchanged scopes remain
shared. The externally accepted directory certificate binds both. All writes
belong to the existing store transaction; bootstrap is explicit archive work.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from itertools import groupby
import sqlite3

from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_proof_content import _namespace,_integer
from .persistence_proof_nodes import Root,_digest,key_locator
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_batch import update_sorted
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_occurrence import OwnerScope,GroupScope,RawOccurrence,occurrence_domain,member_commitment as occurrence_member,group_order_key,_check_allocator,_require_indexes
from .persistence_proof_occurrence_seek import SeekOccurrenceCertificate,seek_domain as occurrence_seek_domain,certificate_commitment as occurrence_certificate_commitment
from .persistence_proof_query import QueryScope,query_domain,member_commitment as query_member
from .persistence_proof_query_seek import SeekQueryCertificate,seek_domain as query_seek_domain,certificate_commitment as query_certificate_commitment
from .persistence_proof_order import query_order_key
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight
from .persistence_sqlite_guard import require_persistent_sources

MAX_FIELD_BYTES=4096
_DESCRIPTOR_SCHEMA='CREATE TABLE ate_scope_descriptors(commitment BLOB PRIMARY KEY,root_digest BLOB NOT NULL,root_count INTEGER NOT NULL) WITHOUT ROWID'
_ROOT_SCHEMA='CREATE TABLE ate_scope_generations(generation INTEGER PRIMARY KEY,next_incarnation_id INTEGER NOT NULL,roots BLOB NOT NULL,certificate BLOB NOT NULL,parent_commitment BLOB,pin_token TEXT NOT NULL,commit_token BLOB NOT NULL,row_checksum BLOB NOT NULL)'
_NODE_SCHEMA='CREATE TABLE ate_proof_nodes (map_domain BLOB NOT NULL, digest BLOB NOT NULL CHECK(length(digest)=32), node_bytes BLOB NOT NULL CHECK(length(node_bytes)<=696), PRIMARY KEY(map_domain,digest)) WITHOUT ROWID'
_SEEK_SCHEMA='CREATE TABLE ate_ordered_seek_nodes(domain BLOB NOT NULL,digest BLOB NOT NULL,raw BLOB NOT NULL,PRIMARY KEY(domain,digest)) WITHOUT ROWID'


@dataclass(frozen=True)
class _QueryOwnerScope:
    namespace: str
    typed_key: bytes


@dataclass(frozen=True)
class ChildScope:
    incarnation_id: int


@dataclass(frozen=True)
class SequenceScope:
    incarnation_id: int


class ScopeProofBudgetError(StoreError):pass


@dataclass(frozen=True)
class ScopeDirectoryCertificate:
    store_identity: str
    generation: int
    codec_version: int
    next_incarnation_id: int
    roots: tuple


def _scope_key(scope):
    if type(scope) is OwnerScope:tag,parts=0,(_namespace(scope.namespace),scope.typed_key)
    elif type(scope) is GroupScope:tag,parts=1,(_integer(scope.incarnation_id,1),)
    elif type(scope) is ChildScope:tag,parts=4,(_integer(scope.incarnation_id,1),)
    elif type(scope) is SequenceScope:tag,parts=5,(_integer(scope.incarnation_id,1),)
    elif type(scope) is _QueryOwnerScope:tag,parts=3,(_namespace(scope.namespace),scope.typed_key)
    elif type(scope) is QueryScope:tag,parts=2,(_namespace(scope.namespace),_namespace(scope.index_name),scope.index_value)
    else:raise StoreIntegrityError('invalid directory scope')
    if any(type(p) is not bytes for p in parts):raise StoreIntegrityError('invalid directory scope bytes')
    if any(len(p)>MAX_FIELD_BYTES for p in parts):raise ScopeProofBudgetError('scope field exceeds explicit directory path')
    return bytes([tag])+b''.join(len(p).to_bytes(4,'big')+p for p in parts)


def _parse_scope(raw):
    if type(raw) is not bytes or not raw or raw[0]>5:raise StoreIntegrityError('invalid scope encoding')
    fields=[];offset=1
    for _ in range((2,1,3,2,1,1)[raw[0]]):
        if offset+4>len(raw):raise StoreIntegrityError('truncated scope encoding')
        size=int.from_bytes(raw[offset:offset+4],'big');offset+=4
        if size>MAX_FIELD_BYTES or offset+size>len(raw):raise StoreIntegrityError('invalid scope frame')
        fields.append(raw[offset:offset+size]);offset+=size
    if offset!=len(raw):raise StoreIntegrityError('surplus scope bytes')
    try:
        if raw[0] in (0,3):scope=(OwnerScope if raw[0]==0 else _QueryOwnerScope)(fields[0].decode('utf-8'),fields[1])
        elif raw[0] in (1,4,5):scope=({1:GroupScope,4:ChildScope,5:SequenceScope}[raw[0]])(int(fields[0]))
        else:scope=QueryScope(fields[0].decode('utf-8'),fields[1].decode('utf-8'),fields[2])
    except (ValueError,UnicodeError) as exc:raise StoreIntegrityError('invalid scope fields') from exc
    if _scope_key(scope)!=raw:raise StoreIntegrityError('noncanonical scope bytes')
    return scope


def directory_domain(store_identity,codec_version,kind):
    if type(kind) is not int or not 0<=kind<6:raise StoreIntegrityError('invalid directory kind')
    return _digest(b'ate-scope-directory-domain/1',_namespace(store_identity),_integer(codec_version,1),bytes([kind]))


def _map(store,kind):
    domain=directory_domain(store.store_identity,store.codec.version,kind);nodes=ProofNodeStore(store.db)
    return ProofMap(domain,lambda d:nodes.read(domain,d),lambda d,raw:nodes.write(domain,d,raw))


def _seek_domain(store,scope):
    if type(scope) is SequenceScope:return _digest(b'ate-sequence-locator-seek-domain/1',_namespace(store.store_identity),_integer(store.codec.version,1),_scope_key(scope))
    if type(scope) is ChildScope:return _digest(b'ate-child-locator-seek-domain/1',_namespace(store.store_identity),_integer(store.codec.version,1),_scope_key(scope))
    if type(scope) is _QueryOwnerScope:return _digest(b'ate-query-owner-seek-domain/1',_namespace(store.store_identity),_integer(store.codec.version,1),_scope_key(scope))
    return (query_seek_domain if type(scope) is QueryScope else occurrence_seek_domain)(store.store_identity,store.codec.version,scope)


def _roots_bytes(cert):return b''.join(r.digest+r.count.to_bytes(8,'big') for r in cert.roots)


def certificate_commitment(cert):
    if (type(cert) is not ScopeDirectoryCertificate or type(cert.generation) is not int or not 0<=cert.generation<2**63
            or type(cert.next_incarnation_id) is not int or not 1<=cert.next_incarnation_id<2**63
            or type(cert.roots) is not tuple or len(cert.roots) not in (4,5,6)):raise StoreIntegrityError('invalid scope directory certificate')
    for kind,root in enumerate(cert.roots):ProofMap(directory_domain(cert.store_identity,cert.codec_version,kind),None,None)._reference(root)
    return _digest({4:b'ate-scope-directory-certificate/1',5:b'ate-scope-directory-certificate/2',6:b'ate-scope-directory-certificate/3'}[len(cert.roots)],_namespace(cert.store_identity),_integer(cert.codec_version,1),
        cert.generation.to_bytes(8,'big'),cert.next_incarnation_id.to_bytes(8,'big'),_roots_bytes(cert))


def _authority(store,pin,cert,expected):
    if type(expected) is not bytes or len(expected)!=32 or certificate_commitment(cert)!=expected:raise StoreIntegrityError('scope directory authority disagreement')
    if (cert.store_identity!=store.store_identity or cert.store_identity!=pin.store_identity
            or cert.codec_version!=store.codec.version or cert.generation!=pin.captured_head):raise StoreConflictError('scope directory context disagreement')


def _schemas(db):
    require_persistent_sources(db)
    for sql in (_DESCRIPTOR_SCHEMA,_ROOT_SCHEMA,_NODE_SCHEMA,_SEEK_SCHEMA):
        name=sql.split('(')[0].split()[2]
        row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM sqlite_schema WHERE type='table' AND name=?",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(sql.lower().split()):raise StoreError('scope schemas require explicit verified construction')


def _descriptor(store,scope,root):
    OrderedSeekMap(None,_seek_domain(store,scope))._reference(root)
    return _digest(b'ate-scope-descriptor/1',_seek_domain(store,scope),_scope_key(scope),root.digest,root.count.to_bytes(8,'big'))


def _write_descriptor(store,scope,root):
    value=_descriptor(store,scope,root)
    cursor=store.db.execute('INSERT OR IGNORE INTO ate_scope_descriptors VALUES(?,?,?)',(value,root.digest,root.count))
    if not cursor.rowcount and store.db.execute('SELECT 1 FROM ate_scope_descriptors WHERE commitment=? AND root_digest=? AND root_count=?',(value,root.digest,root.count)).fetchone() is None:raise StoreIntegrityError('conflicting immutable scope descriptor')
    cursor.close();return value


def _resolve(store,cert,scope):
    encoded=_scope_key(scope);kind=encoded[0]
    if kind==4 and len(cert.roots)<5:raise StoreError('child inventory requires explicit verified construction')
    if kind==5 and len(cert.roots)!=6:raise StoreError('sequence inventory requires explicit verified construction')
    if kind==1 and scope.incarnation_id>=cert.next_incarnation_id:raise StoreIntegrityError('directory group exceeds allocator')
    wanted=_map(store,kind).get(cert.roots[kind],encoded)
    if wanted is None:return OrderedSeekMap(None,_seek_domain(store,scope)).empty
    row=store.db.execute("SELECT CASE WHEN typeof(root_digest)='blob' AND length(root_digest)=32 THEN root_digest END,CASE WHEN typeof(root_count)='integer' THEN root_count END FROM ate_scope_descriptors WHERE commitment=?",(wanted,)).fetchone()
    if row is None:raise StoreIntegrityError('missing scope descriptor')
    root=Root(*row)
    if not root.count or _descriptor(store,scope,root)!=wanted:raise StoreIntegrityError('scope descriptor disagrees with directory')
    return root


def _row_checksum(cert,parent,pin_token,token):
    return _digest(b'ate-scope-generation-row/1',certificate_commitment(cert),parent or b'',pin_token.encode('ascii'),token)


def _write_root(store,cert,*,parent=None,pin_token='',token=b''):
    expected=certificate_commitment(cert)
    store.db.execute('INSERT INTO ate_scope_generations VALUES(?,?,?,?,?,?,?,?)',(cert.generation,cert.next_incarnation_id,_roots_bytes(cert),expected,parent,pin_token,token,_row_checksum(cert,parent,pin_token,token)))
    return cert,expected


def _load_root(store,generation):
    row=store.db.execute("SELECT CASE WHEN typeof(next_incarnation_id)='integer' THEN next_incarnation_id END,CASE WHEN typeof(roots)='blob' AND length(roots) IN (160,200,240) THEN roots END,CASE WHEN typeof(certificate)='blob' AND length(certificate)=32 THEN certificate END,CASE WHEN typeof(parent_commitment)='blob' AND length(parent_commitment)=32 THEN parent_commitment END,typeof(parent_commitment),CASE WHEN typeof(pin_token)='text' AND length(CAST(pin_token AS BLOB))<=4096 THEN pin_token END,CASE WHEN typeof(commit_token)='blob' AND length(commit_token)<=65536 THEN commit_token END,CASE WHEN typeof(row_checksum)='blob' AND length(row_checksum)=32 THEN row_checksum END FROM ate_scope_generations WHERE generation=?",(generation,)).fetchone()
    if row is None:raise StoreIntegrityError('missing current/retained scope directory')
    allocator,roots,expected,parent,parent_type,writer,token,checksum=row
    if type(roots) is not bytes or parent_type not in ('null','blob') or parent_type=='blob' and parent is None or type(writer) is not str or type(token) is not bytes:raise StoreIntegrityError('invalid scope generation source')
    cert=ScopeDirectoryCertificate(store.store_identity,generation,store.codec.version,allocator,tuple(Root(roots[i:i+32],int.from_bytes(roots[i+32:i+40],'big')) for i in range(0,len(roots),40)))
    try:actual=_row_checksum(cert,parent,writer,token)
    except UnicodeError as exc:raise StoreIntegrityError('invalid scope writer token') from exc
    if certificate_commitment(cert)!=expected or actual!=checksum:raise StoreIntegrityError('scope generation row checksum disagreement')
    return (cert,expected),parent,writer,token


def _guard_construction(db):
    for table,texts,blobs,integers in (
        ('lazy_query_versions',('namespace','index_name'),('index_value','record_key'),('ordinal',)),
        ('lazy_identity_occurrence_versions',('owner_namespace',),('owner_key','occurrence_path'),('incarnation_id',))):
        valid=' AND '.join([f"typeof({f})='text' AND length(CAST({f} AS BLOB)) BETWEEN 1 AND {MAX_FIELD_BYTES} AND instr({f},char(0))=0" for f in texts]+[f"typeof({f})='blob' AND length({f})<={MAX_FIELD_BYTES}" for f in blobs]+[f"typeof({f})='integer' AND {f}>={'1' if f=='incarnation_id' else '0'}" for f in integers]+["typeof(valid_from)='integer' AND valid_from>=0","typeof(valid_to) IN ('null','integer')","typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64"])
        if db.execute('SELECT 1 FROM '+table+' WHERE NOT('+valid+') LIMIT 1').fetchone() is not None:raise ScopeProofBudgetError('invalid or oversized scope construction source metadata')


def bootstrap_scope_proofs(store,pin,*,max_metadata_bytes=1048576,include_children=False,include_sequence=False):
    _require_closed_codec(store,allow_typed=True)
    if type(include_children) is not bool or type(include_sequence) is not bool or include_sequence and not include_children:raise StoreIntegrityError('invalid child/sequence construction option')
    if type(max_metadata_bytes) is not int or not 1<=max_metadata_bytes<=64*1024*1024:raise StoreIntegrityError('invalid scope metadata budget')
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('scope construction requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        if include_children:
            from .persistence_proof_collection_directory import _source_schemas
            _source_schemas(store.db);_guard_child_keys(store)
            if include_sequence:_guard_sequence_keys(store)
        _closed_snapshot_preflight(store,max_metadata_bytes);generation=store._require_pin(pin)
        if generation!=int(store._checked_head_row()[0]):raise StoreConflictError('scope construction requires current pin')
        _guard_construction(store.db);store.verify_all()
        _require_indexes(store.db,include_order=False,intervals=('lazy_query_interval','lazy_query_owner_interval','lazy_identity_occurrence_interval','lazy_identity_state_interval'))
        allocator=store._identity_state_at(generation)[0];_check_allocator(store,generation,allocator)
        ProofNodeStore(store.db).create_schema();OrderedSeekMap(store.db,b'').create_schema()
        for sql in (_DESCRIPTOR_SCHEMA,_ROOT_SCHEMA):store.db.execute(sql.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1))
        _schemas(store.db)
        if store.db.execute('SELECT 1 FROM ate_scope_generations WHERE generation=?',(generation,)).fetchone() is not None:raise StoreIntegrityError('scope constructor cannot replace existing generation')
        store.db.execute('CREATE TEMP TABLE ate_scope_directory_delta(kind INTEGER,locator BLOB,key BLOB,value BLOB,PRIMARY KEY(kind,locator)) WITHOUT ROWID')
        if include_children:_construct_child_spool(store,generation)
        if include_sequence:_construct_sequence_spool(store,generation)
        roots=[]
        for kind in range(6 if include_sequence else 5 if include_children else 4):
            if kind<2:
                columns='owner_namespace,owner_key,occurrence_path,incarnation_id';table='lazy_identity_occurrence_versions'
                order='owner_namespace,owner_key,occurrence_path' if kind==0 else 'incarnation_id,owner_namespace,owner_key,occurrence_path'
                scope_for=(lambda r:OwnerScope(r[0],r[1])) if kind==0 else (lambda r:GroupScope(r[3]))
            elif kind in (4,5):
                columns='parent,position';table='ate_scope_child_spool' if kind==4 else 'ate_scope_sequence_spool';order='parent,position';scope_for=(lambda r:ChildScope(r[0])) if kind==4 else (lambda r:SequenceScope(r[0]))
            else:
                columns='namespace,index_name,index_value,record_key,ordinal';table='lazy_query_versions';order=columns
                # Query position ordering is ordinal then record_key within a scope.
                order='namespace,index_name,index_value,ordinal,record_key';scope_for=lambda r:QueryScope(*r[:3])
                if kind==3:order='namespace,record_key,index_name,index_value,ordinal';scope_for=lambda r:_QueryOwnerScope(r[0],r[3])
            cursor=(store.db.execute('SELECT parent,position FROM '+table+' ORDER BY parent,position') if kind in (4,5) else
                    store.db.execute('SELECT '+columns+' FROM '+table+' WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY '+order,(generation,generation)))
            directory=_map(store,kind)
            try:
                for scope,rows in groupby(cursor,scope_for):
                    encoded=_scope_key(scope);m=OrderedSeekMap(store.db,_seek_domain(store,scope))
                    domain=(query_domain if kind==2 else occurrence_domain)(store.store_identity,store.codec.version,scope) if kind<3 else None
                    def entries():
                        for row in rows:
                            if kind in (4,5):yield row[1],_child_member(m.domain,row[1])
                            elif kind==2:yield query_order_key(row[4],row[3]),query_member(domain,row[3],row[4])
                            elif kind==3:
                                query=QueryScope(*row[:3]);d=query_domain(store.store_identity,store.codec.version,query)
                                yield group_order_key(row[1],row[2],row[4].to_bytes(8,'big')),query_member(d,row[3],row[4])
                            else:
                                if not 0<row[3]<allocator:raise StoreIntegrityError('scope placement exceeds allocator')
                                yield row[2] if kind==0 else group_order_key(*row[:3]),occurrence_member(domain,RawOccurrence(*row))
                    root=m.build(entries());value=_write_descriptor(store,scope,root)
                    store.db.execute('INSERT INTO ate_scope_directory_delta VALUES(?,?,?,?)',(kind,key_locator(directory.map_domain,encoded),encoded,value))
            finally:cursor.close()
            delta=store.db.execute('SELECT key,value FROM ate_scope_directory_delta WHERE kind=? ORDER BY locator',(kind,))
            try:roots.append(update_sorted(directory,directory.empty,delta))
            finally:delta.close()
        store.db.execute('DROP TABLE ate_scope_directory_delta')
        if include_children:store.db.execute('DROP TABLE ate_scope_child_spool')
        if include_sequence:store.db.execute('DROP TABLE ate_scope_sequence_spool')
        result=_write_root(store,ScopeDirectoryCertificate(store.store_identity,generation,store.codec.version,allocator,tuple(roots)))
        store.db.commit();return result
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False


def read_scope_certificate(store,pin,certificate,expected,scope,*,max_metadata_bytes=1048576):
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,certificate,expected);_scope_key(scope)
    if type(scope) in (_QueryOwnerScope,ChildScope,SequenceScope):raise StoreError('internal scope requires its dedicated checked reader')
    if type(max_metadata_bytes) is not int or not 1<=max_metadata_bytes<=64*1024*1024:raise StoreIntegrityError('invalid directory metadata budget')
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):raise StoreError('scope reader cannot borrow arbitrary transaction')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,max_metadata_bytes)) as generation:
        head=int(store._checked_head_row()[0])
        if generation not in (head,head-1):raise StoreConflictError('scope pin outside retained generations')
        _schemas(store.db)
        if _load_root(store,generation)[0]!=(certificate,expected):raise StoreIntegrityError('scope accepted generation source disagreement')
        _require_indexes(store.db,include_order=False,intervals=('lazy_identity_state_interval',));_check_allocator(store,generation,certificate.next_incarnation_id)
        root=_resolve(store,certificate,scope)
        if type(scope) is QueryScope:
            cert=SeekQueryCertificate(store.store_identity,generation,store.codec.version,scope,root)
            return cert,query_certificate_commitment(cert)
        cert=SeekOccurrenceCertificate(store.store_identity,generation,store.codec.version,scope,certificate.next_incarnation_id,root)
        return cert,occurrence_certificate_commitment(cert)


@dataclass(frozen=True)
class ScopeProofCommit:
    commit: object
    certificate: ScopeDirectoryCertificate | None
    commitment: bytes | None
    record: object = None


@dataclass
class _ScopeProofRequest:
    store: object
    pin: object
    parent: ScopeDirectoryCertificate
    expected_parent: bytes
    encoded_token: bytes
    data_version: int
    successor: tuple | None = None


def _check_request(store,pin,request):
    from .persistence_sqlite_guard import GuardedConnection
    if type(request) is not _ScopeProofRequest or request.store is not store or request.pin!=pin:raise StoreIntegrityError('invalid private scope proof request')
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,request.parent,request.expected_parent)
    if type(store.db) is not GuardedConnection:raise StoreError('scope publication requires tracked SQL callback guard')
    if type(request.encoded_token) is not bytes or len(request.encoded_token)>65536:raise ScopeProofBudgetError('scope commit token exceeds metadata path')
    if store.db.execute('PRAGMA data_version').fetchone()[0]!=request.data_version:raise StoreConflictError('external write invalidated scope parent epoch')


def _interval_ok(start,end,generation):
    return type(start) is int and 0<=start<=generation and (end is None or type(end) is int and end>generation and end>start)


def _guard_scope_inputs(store,request,version_prepared,identity_prepared):
    """Guard before inherited reads, inside one caller-owned stable snapshot.

    Repeat after BEGIN IMMEDIATE: preparation and attempt registration must
    not create a gap in which unbounded predecessor bytes can be transferred.
    The inherited writer still checks all checksums and owner projections.
    """
    _check_request(store,request.pin,request);_closed_snapshot_preflight(store,1048576);_schemas(store.db)
    required=('lazy_query_owner_interval','lazy_identity_occurrence_interval','lazy_identity_state_interval',
        'lazy_record_interval','lazy_order_interval','lazy_namespace_interval')
    if any(i not in store._interval_indexes for i in required):raise StoreError('scope save cannot use legacy interval fallback')
    _require_indexes(store.db,include_order=False,intervals=required)
    generation=request.parent.generation;_check_allocator(store,generation,request.parent.next_incarnation_id)
    fixed=("typeof(valid_from)='integer' AND valid_from>=0 AND typeof(valid_to) IN ('null','integer') "
        "AND typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64")
    def probe(table,index,keys,args,valid):
        rows=store._interval_rows(table,'CASE WHEN '+valid+' THEN 1 ELSE 0 END',keys,args,generation,index,limit=2)
        if len(rows)>1 or any(row!=(1,) for row in rows):raise StoreIntegrityError('invalid or oversized affected scope predecessor')
    for item in version_prepared:
        ns,key=item['namespace'],item['typed_key'];_scope_key(OwnerScope(ns,key))
        probe('lazy_namespace_state','lazy_namespace_interval',('namespace',),(ns,),fixed+" AND typeof(member_count)='integer' AND member_count>=0 AND typeof(next_ordinal)='integer' AND next_ordinal>=0")
        probe('lazy_order_versions','lazy_order_interval',('namespace','typed_key'),(ns,key),fixed+" AND typeof(ordinal)='integer' AND ordinal>=0")
        probe('lazy_record_versions','lazy_record_interval',('namespace','typed_key'),(ns,key),fixed+
            " AND typeof(payload)='blob' AND typeof(memberships)='blob' AND length(payload)+length(memberships)<=67108864 "
            "AND typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 "
            "AND typeof(record_schema)='integer' AND record_schema>0 AND typeof(codec_version)='integer' AND codec_version="+str(store.codec.version))
        for _ in _query_source(store,generation,ns,key):pass
    for item in identity_prepared:
        ns,key,path=item['owner_namespace'],item['owner_key'],item['occurrence_path'];_scope_key(OwnerScope(ns,key))
        if type(path) is not bytes or len(path)>MAX_FIELD_BYTES:raise ScopeProofBudgetError('changed occurrence exceeds scope path')
        _identity_source(store,generation,ns,key,path,request.parent.next_incarnation_id)


@contextmanager
def _scope_parent_snapshot(store,request,version_prepared,identity_prepared):
    with store.read_snapshot(request.pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
        _guard_scope_inputs(store,request,version_prepared,identity_prepared)
        yield


def _query_source(store,generation,namespace,key):
    from .persistence_lazy_store import _query_checksum
    columns=("CASE WHEN typeof(index_name)='text' AND length(CAST(index_name AS BLOB)) BETWEEN 1 AND 4096 AND instr(index_name,char(0))=0 THEN index_name END,"
        "CASE WHEN typeof(index_value)='blob' AND length(index_value)<=4096 THEN index_value END,"
        "CASE WHEN typeof(ordinal)='integer' THEN ordinal END,CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")
    rows=store._interval_rows('lazy_query_versions',columns,('namespace','record_key'),(namespace,key),generation,'lazy_query_owner_interval',stream=True)
    try:
        for name,value,ordinal,start,end,end_type,checksum in rows:
            if (type(name) is not str or type(value) is not bytes or type(ordinal) is not int or not 0<=ordinal<2**63
                    or end_type not in ('null','integer') or end_type=='integer' and type(end) is not int or not _interval_ok(start,end,generation)
                    or checksum!=_query_checksum(namespace,name,value,key,ordinal,start,end)):raise StoreIntegrityError('invalid actual scope query source')
            yield name,value,ordinal
    finally:rows.close()


def _identity_source(store,generation,namespace,key,path,allocator):
    from .persistence_lazy_store import _identity_occurrence_checksum
    columns=("CASE WHEN typeof(incarnation_id)='integer' THEN incarnation_id END,CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")
    rows=store._interval_rows('lazy_identity_occurrence_versions',columns,('owner_namespace','owner_key','occurrence_path'),(namespace,key,path),generation,'lazy_identity_occurrence_interval',limit=2)
    if len(rows)>1:raise StoreIntegrityError('overlapping actual scope identity source')
    if not rows:return None
    inc,start,end,end_type,checksum=rows[0]
    if (type(inc) is not int or not 0<inc<allocator or end_type not in ('null','integer')
            or end_type=='integer' and type(end) is not int or not _interval_ok(start,end,generation)
            or checksum!=_identity_occurrence_checksum(namespace,key,path,inc,start,end)):raise StoreIntegrityError('invalid actual scope identity source')
    return inc


def _delta(store,scope,position,value,side):
    encoded=_scope_key(scope)
    store.db.execute('INSERT OR IGNORE INTO ate_scope_touched VALUES(?)',(encoded,))
    if type(position) is not bytes or type(value) is not bytes or len(value)!=32:raise StoreIntegrityError('invalid scope transition member')
    # side is internal and fixed; uniqueness rejects overlapping source rows.
    existing=store.db.execute('SELECT old,new FROM ate_scope_member_delta WHERE scope=? AND position=?',(encoded,position)).fetchone()
    if existing is not None and existing[0 if side=='old' else 1] is not None:raise StoreIntegrityError('duplicate scope transition member')
    store.db.execute('INSERT INTO ate_scope_member_delta(scope,position,'+side+') VALUES(?,?,?) ON CONFLICT(scope,position) DO UPDATE SET '+side+'=excluded.'+side,(encoded,position,value))


def _stage_queries(store,request,new_generation,prepared):
    for item in prepared:
        namespace,key=item['namespace'],item['typed_key'];_scope_key(OwnerScope(namespace,key))
        reverse=_QueryOwnerScope(namespace,key)
        store.db.execute('INSERT OR IGNORE INTO ate_scope_touched VALUES(?)',(_scope_key(reverse),))
        store.db.execute('DELETE FROM ate_scope_expected_members')
        if not item['change'].delete:
            for name,_,ordinal,encoded in item['memberships']:
                _scope_key(QueryScope(namespace,name,encoded));query_order_key(ordinal,key)
                store.db.execute('INSERT INTO ate_scope_expected_members VALUES(?,?,?,0)',(name,encoded,ordinal))
        for generation,side in ((request.parent.generation,'old'),(new_generation,'new')):
            for name,value,ordinal in _query_source(store,generation,namespace,key):
                if side=='new':
                    cursor=store.db.execute('UPDATE ate_scope_expected_members SET seen=seen+1 WHERE name=? AND value=? AND ordinal=?',(name,value,ordinal))
                    if cursor.rowcount!=1:raise StoreIntegrityError('actual new query is absent from prepared transition')
                    cursor.close()
                scope=QueryScope(namespace,name,value);domain=query_domain(store.store_identity,store.codec.version,scope)
                _delta(store,scope,query_order_key(ordinal,key),query_member(domain,key,ordinal),side)
                _delta(store,reverse,group_order_key(name,value,ordinal.to_bytes(8,'big')),query_member(domain,key,ordinal),side)
        if store.db.execute('SELECT 1 FROM ate_scope_expected_members WHERE seen!=1 LIMIT 1').fetchone() is not None:raise StoreIntegrityError('prepared query is missing or duplicated in actual successor')


def _stage_placements(store,request,new_generation,allocator,prepared):
    for item in prepared:
        ns,key,path=item['owner_namespace'],item['owner_key'],item['occurrence_path'];owner=OwnerScope(ns,key);_scope_key(owner)
        if type(path) is not bytes or len(path)>MAX_FIELD_BYTES:raise ScopeProofBudgetError('changed occurrence path exceeds explicit scope path')
        old=_identity_source(store,request.parent.generation,ns,key,path,request.parent.next_incarnation_id)
        parent=OrderedSeekMap(store.db,_seek_domain(store,owner))
        wanted_old=None if old is None else occurrence_member(occurrence_domain(store.store_identity,store.codec.version,owner),RawOccurrence(ns,key,path,old))
        if parent.get(_resolve(store,request.parent,owner),path)!=wanted_old:raise StoreIntegrityError('actual parent placement is missing or changed')
        new=_identity_source(store,new_generation,ns,key,path,allocator)
        wanted=None if item['change'].delete else item['change'].incarnation_id
        if new!=wanted:raise StoreIntegrityError('actual new placement disagrees with prepared transition')
        for inc,side in ((old,'old'),(new,'new')):
            if inc is None:continue
            row=RawOccurrence(ns,key,path,inc)
            for scope,position in ((owner,path),(GroupScope(inc),group_order_key(ns,key,path))):
                domain=occurrence_domain(store.store_identity,store.codec.version,scope)
                _delta(store,scope,position,occurrence_member(domain,row),side)


def _stage_scope_proof(store,request,new_generation,version_prepared,identity_prepared,encoded_token):
    _check_request(store,request.pin,request)
    if not store.db.in_transaction:raise StoreIntegrityError('scope publication requires existing writer transaction')
    if new_generation!=request.parent.generation+1 or encoded_token!=request.encoded_token:raise StoreConflictError('scope successor generation/token disagreement')
    if store.db.execute('SELECT generation,parent_generation FROM save_head WHERE singleton=1').fetchone()!=(new_generation,request.parent.generation):raise StoreIntegrityError('scope writer lost successor head')
    _schemas(store.db)
    if _load_root(store,request.parent.generation)[0]!=(request.parent,request.expected_parent):raise StoreIntegrityError('accepted scope parent changed')
    _require_indexes(store.db,include_order=False,intervals=('lazy_query_owner_interval','lazy_identity_occurrence_interval','lazy_identity_state_interval'))
    _check_allocator(store,request.parent.generation,request.parent.next_incarnation_id)
    # Probe fixed-size allocator metadata before any inherited transfer.
    rows=store._interval_rows('lazy_identity_state',"CASE WHEN typeof(next_incarnation_id)='integer' THEN next_incarnation_id END",(),(),new_generation,'lazy_identity_state_interval',limit=2)
    if len(rows)!=1 or type(rows[0][0]) is not int:raise StoreIntegrityError('invalid successor scope allocator')
    allocator=rows[0][0];_check_allocator(store,new_generation,allocator)
    if allocator<request.parent.next_incarnation_id:raise StoreIntegrityError('scope successor allocator moved backwards')
    OrderedSeekMap(store.db,b'').create_schema()
    store.db.execute('CREATE TEMP TABLE ate_scope_touched(scope BLOB PRIMARY KEY) WITHOUT ROWID')
    store.db.execute('CREATE TEMP TABLE ate_scope_member_delta(scope BLOB,position BLOB,old BLOB,new BLOB,PRIMARY KEY(scope,position)) WITHOUT ROWID')
    store.db.execute('CREATE TEMP TABLE ate_scope_expected_members(name TEXT,value BLOB,ordinal INTEGER,seen INTEGER,PRIMARY KEY(name,value,ordinal)) WITHOUT ROWID')
    store.db.execute('CREATE TEMP TABLE ate_scope_directory_delta(kind INTEGER,locator BLOB,key BLOB,value BLOB,PRIMARY KEY(kind,locator)) WITHOUT ROWID')
    if len(request.parent.roots)>=5:
        if 'lazy_record_interval' not in store._interval_indexes:raise StoreError('child inventory cannot use legacy interval fallback')
        _require_indexes(store.db,include_order=False,intervals=('lazy_record_interval',))
        _stage_children(store,request,new_generation,version_prepared)
        if len(request.parent.roots)==6:_stage_children(store,request,new_generation,version_prepared,locator_for=_sequence_locator)
    _stage_queries(store,request,new_generation,version_prepared);_stage_placements(store,request,new_generation,allocator,identity_prepared)
    cursor=store.db.execute('SELECT scope FROM ate_scope_touched ORDER BY scope')
    try:
        for (encoded,) in cursor:
            scope=_parse_scope(encoded);kind=encoded[0];m=OrderedSeekMap(store.db,_seek_domain(store,scope))
            parent=m.empty if kind==1 and scope.incarnation_id>=request.parent.next_incarnation_id else _resolve(store,request.parent,scope)
            if kind==3:
                old_rows=store.db.execute('SELECT position,old FROM ate_scope_member_delta WHERE scope=? AND old IS NOT NULL ORDER BY position',(encoded,))
                try:actual_old=m.build(old_rows)
                finally:old_rows.close()
                if actual_old!=parent:raise StoreIntegrityError('complete actual parent query set disagrees with accepted owner witness')
            root=parent
            rows=store.db.execute('SELECT position,old,new FROM ate_scope_member_delta WHERE scope=? ORDER BY position',(encoded,))
            try:
                for position,old,new in rows:
                    if m.get(parent,position)!=old:raise StoreIntegrityError('actual old scope member disagrees with accepted parent')
                    root=m.set(root,position,new)
            finally:rows.close()
            value=_write_descriptor(store,scope,root) if root.count else None;directory=_map(store,kind)
            store.db.execute('INSERT INTO ate_scope_directory_delta VALUES(?,?,?,?)',(kind,key_locator(directory.map_domain,encoded),encoded,value))
    finally:cursor.close()
    roots=[]
    for kind,parent in enumerate(request.parent.roots):
        m=_map(store,kind);rows=store.db.execute('SELECT key,value FROM ate_scope_directory_delta WHERE kind=? ORDER BY locator',(kind,))
        try:roots.append(update_sorted(m,parent,rows))
        finally:rows.close()
    for table in ('ate_scope_touched','ate_scope_member_delta','ate_scope_expected_members','ate_scope_directory_delta'):store.db.execute('DROP TABLE '+table)
    cert=ScopeDirectoryCertificate(store.store_identity,new_generation,store.codec.version,allocator,tuple(roots))
    request.successor=_write_root(store,cert,parent=request.expected_parent,pin_token=request.pin.token,token=encoded_token)


def commit_scope_proof(store,pin,certificate,expected,*,commit_token,record_authority=None,**arguments):
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,certificate,expected)
    if any(k in arguments for k in ('_scope_proof','_record_proof')):raise StoreError('private proof requests cannot be supplied by wrapper caller')
    if store.db.in_transaction:raise StoreError('scope save requires owned writer operation')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
        _schemas(store.db)
        if _load_root(store,certificate.generation)[0]!=(certificate,expected):raise StoreIntegrityError('scope parent source disagreement')
        _require_indexes(store.db,include_order=False,intervals=('lazy_identity_state_interval',));_check_allocator(store,certificate.generation,certificate.next_incarnation_id)
        data_version=store.db.execute('PRAGMA data_version').fetchone()[0]
    request=_ScopeProofRequest(store,pin,certificate,expected,store.codec.encode(commit_token),data_version);_check_request(store,pin,request)
    record=None
    if record_authority is None:result=store.commit(pin,commit_token=commit_token,_scope_proof=request,**arguments)
    else:
        from .persistence_proof_record import commit_record_proof
        if type(record_authority) is not tuple or len(record_authority)!=2:raise StoreIntegrityError('invalid combined record authority')
        record=commit_record_proof(store,pin,*record_authority,commit_token=commit_token,_scope_proof=request,**arguments);result=record.commit
    if result.outcome=='committed':
        if request.successor is None:raise StoreIntegrityError('missing scope publication result')
        return ScopeProofCommit(result,*request.successor,record)
    return ScopeProofCommit(result,certificate if result.outcome=='not_committed' else None,expected if result.outcome=='not_committed' else None,record)


def resolve_scope_commit(store,pin,certificate,expected,*,commit_token,record_authority=None):
    _require_closed_codec(store,allow_typed=True);_authority(store,pin,certificate,expected)
    if store.db.in_transaction:raise StoreError('scope recovery requires owned operation')
    encoded=store.codec.encode(commit_token);result=store.resolve_commit(pin,commit_token);record=None
    if record_authority is not None:
        from .persistence_proof_record import resolve_record_commit
        if type(record_authority) is not tuple or len(record_authority)!=2:raise StoreIntegrityError('invalid combined recovery authority')
        record=resolve_record_commit(store,pin,*record_authority,commit_token=commit_token)
        if record.commit!=result:raise StoreIntegrityError('combined proof recovery receipt disagreement')
    if result.outcome=='conflict':return ScopeProofCommit(result,None,None,record)
    if result.outcome=='not_committed' and (result.generation!=certificate.generation or result.pin!=pin):raise StoreConflictError('noncommitted scope recovery parent disagreement')
    with store.read_snapshot(result.pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
        _schemas(store.db);pair,parent,writer,token=_load_root(store,result.generation)
        if result.outcome=='not_committed':
            if pair!=(certificate,expected):raise StoreIntegrityError('resolved scope parent missing or changed')
        elif parent!=expected or writer!=pin.token or token!=encoded or result.generation!=certificate.generation+1:raise StoreIntegrityError('resolved scope disagrees with exact parent/token/receipt')
        return ScopeProofCommit(result,*pair,record)


# A locator-only inventory: content and semantic admission remain separate roots.
_CHILD_NAMES=('aux.lazy.nested.list_pages','aux.lazy.nested.entries','aux.lazy.sequence.nodes','aux.lazy.records.headers','aux.lazy.keys.nan_atoms')

def _child_locator(namespace,key):
    from .persistence_proof_projection import _ProjectionCodec
    from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    if namespace not in _CHILD_NAMES:return None
    if type(key) is not bytes or len(key)>4096:raise ScopeProofBudgetError('child key exceeds field budget')
    codec=_ProjectionCodec(metadata=True);value=codec.decode(key);AUXILIARY_OWNER_FAMILIES[namespace].validate_key(value)
    if codec.encode(value)!=key:raise StoreIntegrityError('noncanonical physical child key')
    if not value[0]<2**63:raise StoreIntegrityError('physical child parent exceeds identity range')
    scope=ChildScope(value[0]);_scope_key(scope)
    return scope,bytes([_CHILD_NAMES.index(namespace)])+key

def _child_member(domain,position):return _digest(b'ate-child-locator-member/1',domain,position)

def _guard_child_keys(store):
    names=','.join('?' for _ in _CHILD_NAMES)
    if store.db.execute("SELECT 1 FROM lazy_record_versions WHERE namespace IN ("+names+") AND (typeof(typed_key)!='blob' OR length(typed_key)>4096) LIMIT 1",_CHILD_NAMES).fetchone():raise ScopeProofBudgetError('invalid child inventory construction key')

def _construct_child_spool(store,g):
    store.db.execute('CREATE TEMP TABLE ate_scope_child_spool(parent INTEGER,position BLOB,PRIMARY KEY(parent,position)) WITHOUT ROWID')
    names=','.join('?' for _ in _CHILD_NAMES)
    rows=store.db.execute('SELECT namespace,typed_key FROM lazy_record_versions WHERE namespace IN ('+names+') AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(*_CHILD_NAMES,g,g))
    try:
        for ns,key in rows:
            scope,position=_child_locator(ns,key)
            store.db.execute('INSERT INTO ate_scope_child_spool VALUES(?,?)',(scope.incarnation_id,position))
    finally:rows.close()

def _child_present(store,g,namespace,key):
    rows=store._interval_rows('lazy_record_versions','1',('namespace','typed_key'),(namespace,key),g,'lazy_record_interval',limit=2)
    if len(rows)>1:raise StoreIntegrityError('overlapping physical child locator')
    return bool(rows)

def _stage_children(store,request,g,prepared,*,locator_for=_child_locator):
    for item in prepared:
        namespace,key=item['namespace'],item['typed_key'];locator=locator_for(namespace,key)
        if locator is None:continue
        scope,position=locator;d=_seek_domain(store,scope)
        old=_child_present(store,request.parent.generation,namespace,key);new=_child_present(store,g,namespace,key)
        if new==item['change'].delete:raise StoreIntegrityError('actual child successor disagrees with prepared source')
        m=OrderedSeekMap(store.db,d);wanted=_child_member(d,position) if old else None
        if m.get(_resolve(store,request.parent,scope),position)!=wanted:raise StoreIntegrityError('old physical child disagrees with accepted locator inventory')
        if old:_delta(store,scope,position,wanted,'old')
        if new:_delta(store,scope,position,_child_member(d,position),'new')


# Version3 adds a separate directory; version2 child-family tags never change.
_SEQUENCE_NAMES=('aux.lazy.sequence.parents','aux.lazy.sequence.occurrences','aux.lazy.sequence.members','aux.lazy.sequence.member_directory')

def _sequence_locator(namespace,key):
    from .persistence_proof_projection import _ProjectionCodec
    if namespace not in _SEQUENCE_NAMES:return None
    if type(key) is not bytes or len(key)>4096:raise ScopeProofBudgetError('sequence key exceeds field budget')
    codec=_ProjectionCodec(metadata=True);value=codec.decode(key)
    if (type(value) is not tuple or len(value)!=2 or type(value[0]) is not int or not 0<value[0]<2**63
            or (type(value[1]) is not bytes or len(value[1])>32 if namespace==_SEQUENCE_NAMES[3] else type(value[1]) is not int or value[1]<1)
            or codec.encode(value)!=key):raise StoreIntegrityError('invalid sequence physical key')
    scope=SequenceScope(value[0]);return scope,bytes([_SEQUENCE_NAMES.index(namespace)])+key

def _guard_sequence_keys(store):
    names=','.join('?' for _ in _SEQUENCE_NAMES)
    if store.db.execute("SELECT 1 FROM lazy_record_versions WHERE namespace IN ("+names+") AND (typeof(typed_key)!='blob' OR length(typed_key)>4096) LIMIT 1",_SEQUENCE_NAMES).fetchone():raise ScopeProofBudgetError('invalid sequence construction key')

def _construct_sequence_spool(store,g):
    store.db.execute('CREATE TEMP TABLE ate_scope_sequence_spool(parent INTEGER,position BLOB,PRIMARY KEY(parent,position)) WITHOUT ROWID')
    names=','.join('?' for _ in _SEQUENCE_NAMES)
    rows=store.db.execute('SELECT namespace,typed_key FROM lazy_record_versions WHERE namespace IN ('+names+') AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(*_SEQUENCE_NAMES,g,g))
    try:
        for ns,key in rows:
            scope,position=_sequence_locator(ns,key)
            store.db.execute('INSERT INTO ate_scope_sequence_spool VALUES(?,?)',(scope.incarnation_id,position))
    finally:rows.close()
