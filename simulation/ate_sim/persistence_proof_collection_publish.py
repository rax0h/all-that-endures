"""Bounded per-namespace successor orders in the existing unified writer."""
from dataclasses import dataclass
import json
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_order import query_order_key
from .persistence_proof_collection import CollectionCertificate,certificate_commitment,domain,member,_state,_schema,_indexes
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight
from .persistence_proof_publication import commit_content_proof,resolve_content_commit,_map
from .persistence_proof_content import version_key
from .persistence_lazy_store import _order_checksum

_SCHEMA='CREATE TABLE ate_collection_generations(generation INTEGER NOT NULL,namespace TEXT NOT NULL,certificate BLOB NOT NULL,commitment BLOB NOT NULL,parent BLOB,writer TEXT NOT NULL,token BLOB NOT NULL,checksum BLOB NOT NULL,PRIMARY KEY(generation,namespace)) WITHOUT ROWID'

def _encode(c):return json.dumps([c.store_identity,c.generation,c.codec_version,c.namespace,c.declared,c.member_count,c.next_ordinal,c.root.digest.hex(),c.root.count],separators=(',',':'),ensure_ascii=False).encode()
def _row_hash(c,parent,writer,token):return _digest(b'ate-collection-row/1',certificate_commitment(c),parent or b'',writer.encode('ascii'),token)
def _schema_rows(db):
 _schema(db)
 row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name='ate_collection_generations' AND type='table'").fetchone()
 if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(_SCHEMA.lower().split()):raise StoreError('collection publication requires verified construction')

def _load(store,g,ns):
 row=store.db.execute("SELECT CASE WHEN typeof(certificate)='blob' AND length(certificate)<=16384 THEN certificate END,CASE WHEN typeof(commitment)='blob' AND length(commitment)=32 THEN commitment END,CASE WHEN typeof(parent)='blob' AND length(parent)=32 THEN parent END,typeof(parent),CASE WHEN typeof(writer)='text' AND length(CAST(writer AS BLOB))<=4096 THEN writer END,CASE WHEN typeof(token)='blob' AND length(token)<=65536 THEN token END,CASE WHEN typeof(checksum)='blob' AND length(checksum)=32 THEN checksum END FROM ate_collection_generations WHERE generation=? AND namespace=?",(g,ns)).fetchone()
 if row is None:raise StoreIntegrityError('missing collection generation authority')
 raw,expected,parent,pt,writer,token,checksum=row
 try:
  if type(raw) is not bytes or pt not in ('null','blob') or pt=='blob' and parent is None or type(writer) is not str or type(token) is not bytes:raise StoreIntegrityError('invalid collection row')
  v=json.loads(raw);c=CollectionCertificate(*v[:7],Root(bytes.fromhex(v[7]),v[8]))
  if len(v)!=9 or _encode(c)!=raw or c.generation!=g or c.namespace!=ns or c.store_identity!=store.store_identity or c.codec_version!=store.codec.version or certificate_commitment(c)!=expected or _row_hash(c,parent,writer,token)!=checksum:raise StoreIntegrityError('collection row authority disagreement')
 except (ValueError,TypeError,IndexError,UnicodeError,AttributeError,RecursionError,OverflowError) as e:raise StoreIntegrityError('invalid collection row encoding') from e
 return (c,expected),parent,writer,token

def _write(store,c,*,parent=None,writer='',token=b''):
 expected=certificate_commitment(c);store.db.execute('INSERT INTO ate_collection_generations VALUES(?,?,?,?,?,?,?,?)',(c.generation,c.namespace,_encode(c),expected,parent,writer,token,_row_hash(c,parent,writer,token)));return c,expected

def persist_bootstrap(store,c):
 store.db.execute(_SCHEMA.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1));_schema_rows(store.db)
 if store.db.execute('SELECT 1 FROM ate_collection_generations WHERE generation=? AND namespace=?',(c.generation,c.namespace)).fetchone():
  if _load(store,c.generation,c.namespace)[0]!=(c,certificate_commitment(c)):raise StoreIntegrityError('cannot repair divergent collection authority')
  return c,certificate_commitment(c)
 return _write(store,c)

@dataclass
class _Request:
 store:object
 pin:object
 pairs:tuple
 token:bytes
 epoch:int
 directory:object=None
 states:object=None
 successor:object=None

@dataclass(frozen=True)
class CollectionCommit:
 content:object
 collections:tuple

def _check(store,pin,r):
 if type(r) is not _Request or r.store is not store or r.pin!=pin:raise StoreIntegrityError('invalid private collection request')
 _require_closed_codec(store,allow_typed=True)
 if store.db.execute('PRAGMA data_version').fetchone()[0]!=r.epoch:raise StoreConflictError('external write invalidated collection parent')
 if len(r.token)>65536:raise StoreError('collection token exceeds path')

def _order(store,g,ns,key):
 columns="CASE WHEN typeof(ordinal)='integer' THEN ordinal END,CASE WHEN typeof(valid_from)='integer' THEN valid_from END,CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END"
 rows=store._interval_rows('lazy_order_versions',columns,('namespace','typed_key'),(ns,key),g,'lazy_order_interval',limit=2)
 if not rows:return None
 if len(rows)!=1:raise StoreIntegrityError('overlapping collection order source')
 ordinal,start,end,et,checksum=rows[0]
 if type(ordinal) is not int or not 0<=ordinal<2**63 or type(start) is not int or not 0<=start<=g or et not in ('null','integer') or et=='integer' and (type(end) is not int or end<=g or end<=start) or checksum!=_order_checksum(ns,key,ordinal,start,end):raise StoreIntegrityError('invalid collection order source')
 return ordinal

def _guard(store,r,prepared,content_parent,ordinary=(),segments=()):
 _check(store,r.pin,r)
 if r.directory is not None:
  from .persistence_proof_directory_publish import _guard as guard_directory
  guard_directory(store,r,prepared,ordinary,segments)
 _schema_rows(store.db);_indexes(store)
 parents={c.namespace:c for c,e in r.pairs};states={ns:[c.declared,c.member_count,c.next_ordinal] for ns,c in parents.items()}
 for c,e in r.pairs:
  if r.directory is None and _load(store,c.generation,c.namespace)[0]!=(c,e) or _state(store,c.generation,c.namespace)!=(c.declared,c.member_count,c.next_ordinal):raise StoreIntegrityError('collection accepted parent changed')
 store.db.execute('CREATE TEMP TABLE ate_collection_pub_delta(namespace TEXT,key BLOB,old_position BLOB,new_position BLOB,PRIMARY KEY(namespace,key)) WITHOUT ROWID')
 for item in prepared:
  ns,key=item['namespace'],item['typed_key'];change=item['change']
  if ns not in parents:raise StoreError('missing touched collection authority')
  if len(key)>4096:raise StoreError('collection key exceeds supported path')
  c=parents[ns];old=_order(store,c.generation,ns,key);m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version,ns))
  present=_map(store).get(content_parent.versions,version_key(ns,key)) is not None
  if present!=(old is not None):raise StoreIntegrityError('collection predecessor presence disagreement')
  old_pos=None if old is None else query_order_key(old,key)
  if old is not None and (old>=c.next_ordinal or m.get(c.root,old_pos)!=member(m.domain,key,old)):raise StoreIntegrityError('collection predecessor root disagreement')
  state=states[ns];state[0]=True
  if change.delete:
   new=None
   if old is not None:state[1]-=1
  else:
   if old is None or change.reinsertion:new=state[2];state[2]+=1
   else:new=old
   if old is None:state[1]+=1
  store.db.execute('INSERT INTO ate_collection_pub_delta VALUES(?,?,?,?)',(ns,key,old_pos,None if new is None else query_order_key(new,key)))
 r.states=states

def _stage(store,r,g,token):
 _check(store,r.pin,r);_schema_rows(store.db)
 if token!=r.token or g!=r.pin.captured_head+1 or not store.db.in_transaction:raise StoreIntegrityError('collection successor context disagreement')
 out=[]
 for c,e in r.pairs:
  if r.directory is None and _load(store,c.generation,c.namespace)[0]!=(c,e):raise StoreIntegrityError('collection parent row changed')
  state=tuple(r.states[c.namespace])
  if _state(store,g,c.namespace)!=state:raise StoreIntegrityError('actual collection successor counters disagree')
  m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version,c.namespace));m.create_schema();root=c.root
  rows=store.db.execute('SELECT key,old_position,new_position FROM ate_collection_pub_delta WHERE namespace=? ORDER BY key',(c.namespace,))
  try:
   for key,old,new in rows:
    ordinal=_order(store,g,c.namespace,key)
    if (None if ordinal is None else query_order_key(ordinal,key))!=new:raise StoreIntegrityError('actual collection successor position disagrees')
    if old!=new:
     if old is not None:root=m.set(root,old,None)
     if new is not None:
      if m.get(root,new) is not None:raise StoreIntegrityError('collection successor position collision')
      root=m.set(root,new,member(m.domain,key,ordinal))
  finally:rows.close()
  child=CollectionCertificate(c.store_identity,g,c.codec_version,c.namespace,*state,root);out.append(_write(store,child,parent=e,writer=r.pin.token,token=token))
 store.db.execute('DROP TABLE ate_collection_pub_delta');r.successor=tuple(out)
 if r.directory is not None:
  from .persistence_proof_directory_publish import _stage as stage_directory
  stage_directory(store,r,g,token)

def _pairs(store,pin,pairs,*,allow_empty=False):
 if type(pairs) is not tuple or not (0 if allow_empty else 1)<=len(pairs)<=128:raise StoreError('collection authority inventory exceeds bound')
 seen=set()
 for pair in pairs:
  if type(pair) is not tuple or len(pair)!=2:raise StoreIntegrityError('invalid collection authority pair')
  c,e=pair
  if type(e) is not bytes or len(e)!=32 or certificate_commitment(c)!=e:raise StoreIntegrityError('collection expected authority disagreement')
  if (c.store_identity,c.generation,c.codec_version)!=(store.store_identity,pin.captured_head,store.codec.version) or pin.store_identity!=store.store_identity:raise StoreConflictError('collection parent context disagreement')
  if c.namespace in seen:raise StoreIntegrityError('duplicate collection namespace')
  seen.add(c.namespace)

def commit_collections(store,pin,collections,certificate,expected,*,commit_token,_directory=None,**arguments):
 _require_closed_codec(store,allow_typed=True);_pairs(store,pin,collections,allow_empty=_directory is not None)
 if any(k.startswith('_') for k in arguments):raise StoreError('private collection arguments forbidden')
 if store.db.in_transaction:raise StoreError('collection save requires owned operation')
 with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
  _schema_rows(store.db)
  for c,e in collections:
   if _directory is None and _load(store,c.generation,c.namespace)[0]!=(c,e):raise StoreIntegrityError('collection parent source disagreement')
  epoch=store.db.execute('PRAGMA data_version').fetchone()[0]
 r=_Request(store,pin,collections,store.codec.encode(commit_token),epoch,directory=_directory)
 content=commit_content_proof(store,pin,certificate,expected,commit_token=commit_token,_collection_proof=r,**arguments)
 if content.commit.outcome=='committed':
  if r.successor is None:raise StoreIntegrityError('missing collection successor')
  return CollectionCommit(content,r.successor)
 return CollectionCommit(content,collections if content.commit.outcome=='not_committed' else ())

def resolve_collections(store,pin,collections,certificate,expected,*,commit_token,**arguments):
 _require_closed_codec(store,allow_typed=True);_pairs(store,pin,collections)
 if store.db.in_transaction:raise StoreError('collection recovery requires owned operation')
 _schema_rows(store.db);content=resolve_content_commit(store,pin,certificate,expected,commit_token=commit_token,**arguments);result=content.commit
 if result.outcome=='conflict':return CollectionCommit(content,())
 out=[]
 with store.read_snapshot(result.pin,_preflight=lambda:_closed_snapshot_preflight(store,1048576)):
  _schema_rows(store.db)
  for c,e in collections:
   pair,parent,writer,token=_load(store,result.generation,c.namespace)
   if result.outcome=='not_committed':
    if pair!=(c,e) or result.generation!=c.generation or result.pin!=pin:raise StoreIntegrityError('collection recovery parent disagreement')
   elif parent!=e or writer!=pin.token or token!=store.codec.encode(commit_token) or result.generation!=c.generation+1:raise StoreIntegrityError('collection recovery exact receipt disagreement')
   out.append(pair)
 return CollectionCommit(content,tuple(out))
