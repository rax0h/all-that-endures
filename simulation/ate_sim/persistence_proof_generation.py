"""Inactive generation bindings. External accepted authority is mandatory.

Hashing these data does not verify component roots, retain overwritten bodies,
publish a generation, or enable a World format capability.
"""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _receipt_checksum
from .persistence_proof_nodes import Root,_digest

MAX_MANIFEST_BYTES=2*1024*1024
ROOT_NAMES=('versions','records','topology','queries','orders','events','inventory')
_TAG=b'ATEG\x01'


class ManifestProofBudgetError(StoreError):
    """A separately budgeted manifest path is required."""


@dataclass(frozen=True)
class ManifestHead:
    simulation_position: bytes
    next_ids: bytes
    namespace_inventory: bytes
    namespace_counts: bytes
    seed: int | None
    next_incarnation_id: int


@dataclass(frozen=True)
class ManifestReceipt:
    pin_token: str
    encoded_commit_token: bytes
    checksum: str


@dataclass(frozen=True)
class GenerationManifest:
    store_identity: str
    generation: int
    parent_commitment: bytes | None
    format_version: str
    codec_version: int
    simulation_schema: str
    rules_id: str
    head: ManifestHead
    roots: tuple
    receipt: ManifestReceipt | None


def _uint(n,minimum=0):
    if type(n) is not int or not minimum<=n<2**63:raise StoreIntegrityError('invalid manifest integer')
    return n.to_bytes(8,'big')


def _blob(value,maximum=1024*1024):
    if type(value) is not bytes:raise StoreIntegrityError('invalid manifest bytes')
    if len(value)>maximum:raise ManifestProofBudgetError('manifest field exceeds explicit byte budget')
    return value


def _text(value):
    if type(value) is not str or not value or '\x00' in value:raise StoreIntegrityError('invalid manifest text')
    try:raw=value.encode('utf-8')
    except UnicodeError as exc:raise StoreIntegrityError('invalid manifest UTF8') from exc
    return _blob(raw,4096)


def _hash(value):
    if type(value) is not bytes or len(value)!=32:raise StoreIntegrityError('invalid manifest digest')
    return value


def encode_manifest(value):
    if type(value) is not GenerationManifest or type(value.head) is not ManifestHead:raise StoreIntegrityError('invalid manifest type')
    generation=_uint(value.generation);head=value.head
    if value.generation==0:
        if value.parent_commitment is not None or value.receipt is not None:raise StoreIntegrityError('genesis cannot have parent or receipt')
        parent=(2**64-1).to_bytes(8,'big');digest=b'';receipt=(b'',b'',b'')
    else:
        parent=_uint(value.generation-1);digest=_hash(value.parent_commitment);r=value.receipt
        if type(r) is not ManifestReceipt:raise StoreIntegrityError('missing exact manifest receipt')
        pin=_text(r.pin_token)
        try:pin.decode('ascii')
        except UnicodeError as exc:raise StoreIntegrityError('invalid manifest writer token') from exc
        token=_blob(r.encoded_commit_token,65536)
        if type(r.checksum) is not str or r.checksum!=_receipt_checksum(r.pin_token,token,value.generation,value.generation-1,'committed'):
            raise StoreIntegrityError('manifest receipt checksum disagreement')
        receipt=(pin,token,r.checksum.encode('ascii'))
    if head.seed is None:seed=b'\x00'
    elif type(head.seed) is int and -2**63<=head.seed<2**63:seed=b'\x01'+head.seed.to_bytes(8,'big',signed=True)
    else:raise StoreIntegrityError('invalid manifest seed')
    if type(value.roots) is not tuple or len(value.roots)!=len(ROOT_NAMES):raise StoreIntegrityError('incomplete named manifest roots')
    roots=[]
    for root in value.roots:
        if type(root) is not Root:raise StoreIntegrityError('invalid manifest root type')
        roots.append(_hash(root.digest)+_uint(root.count))
    fields=(_text(value.store_identity),generation,parent,digest,_text(value.format_version),_uint(value.codec_version,1),
        _text(value.simulation_schema),_text(value.rules_id),_uint(head.next_incarnation_id,1),seed,
        _blob(head.simulation_position),_blob(head.next_ids),_blob(head.namespace_inventory),_blob(head.namespace_counts),*roots,*receipt)
    size=len(_TAG)+sum(4+len(p) for p in fields)
    if size>MAX_MANIFEST_BYTES:raise ManifestProofBudgetError('manifest exceeds aggregate byte budget')
    return _TAG+b''.join(len(p).to_bytes(4,'big')+p for p in fields)


def manifest_commitment(value):return _digest(b'ate-generation-manifest/1',encode_manifest(value))


def decode_manifest(raw,expected):
    _hash(expected);_blob(raw,MAX_MANIFEST_BYTES)
    if _digest(b'ate-generation-manifest/1',raw)!=expected:raise StoreIntegrityError('manifest expected authority disagreement')
    try:
        if raw[:5]!=_TAG:raise StoreIntegrityError('unknown generation manifest encoding')
        fields=[];offset=5
        for _ in range(24):
            if offset+4>len(raw):raise StoreIntegrityError('truncated manifest frame')
            length=int.from_bytes(raw[offset:offset+4],'big');offset+=4
            if length>MAX_MANIFEST_BYTES or offset+length>len(raw):raise StoreIntegrityError('invalid manifest frame length')
            fields.append(raw[offset:offset+length]);offset+=length
        if offset!=len(raw):raise StoreIntegrityError('surplus manifest bytes')
        def integer(index):
            if len(fields[index])!=8:raise StoreIntegrityError('invalid manifest integer encoding')
            return int.from_bytes(fields[index],'big')
        generation=integer(1)
        if integer(2)!=(generation-1 if generation else 2**64-1):raise StoreIntegrityError('manifest parent generation disagreement')
        seed=fields[9]
        if seed==b'\x00':seed=None
        elif len(seed)==9 and seed[0]==1:seed=int.from_bytes(seed[1:],'big',signed=True)
        else:raise StoreIntegrityError('invalid manifest seed encoding')
        head=ManifestHead(*fields[10:14],seed,integer(8));roots=[]
        for field in fields[14:21]:
            if len(field)!=40:raise StoreIntegrityError('invalid manifest root encoding')
            roots.append(Root(field[:32],int.from_bytes(field[32:],'big')))
        if generation:receipt=ManifestReceipt(fields[21].decode('ascii'),fields[22],fields[23].decode('ascii'))
        else:
            if any(fields[21:]):raise StoreIntegrityError('genesis receipt bytes must be absent')
            receipt=None
        result=GenerationManifest(fields[0].decode('utf-8'),generation,fields[3] if generation else None,
            fields[4].decode('utf-8'),integer(5),fields[6].decode('utf-8'),fields[7].decode('utf-8'),head,tuple(roots),receipt)
        if encode_manifest(result)!=raw:raise StoreIntegrityError('noncanonical generation manifest')
        return result
    except (UnicodeError,ValueError,TypeError,IndexError,OverflowError) as exc:raise StoreIntegrityError('invalid generation manifest encoding') from exc


def _accepted(value,expected):
    if manifest_commitment(value)!=_hash(expected):raise StoreIntegrityError('generation manifest authority disagreement')


def validate_successor(parent,expected_parent,successor,expected_successor,encoded_commit_token):
    _accepted(parent,expected_parent);_accepted(successor,expected_successor);_blob(encoded_commit_token,65536)
    if (successor.generation!=parent.generation+1 or successor.parent_commitment!=expected_parent
            or (successor.store_identity,successor.format_version,successor.codec_version,successor.simulation_schema,successor.rules_id)!=
               (parent.store_identity,parent.format_version,parent.codec_version,parent.simulation_schema,parent.rules_id)
            or successor.head.next_incarnation_id<parent.head.next_incarnation_id
            or successor.receipt.encoded_commit_token!=encoded_commit_token):
        raise StoreConflictError('manifest successor parent/context/allocator/token disagreement')


def read_generation_manifest(store,pin,expected,*,max_bytes=MAX_MANIFEST_BYTES,max_metadata_bytes=1048576):
    """Read bound raw data, not a capability for arbitrary component roots."""
    from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight,ProjectionProofBudgetError
    from .persistence_proof_version import VersionProofBudgetError
    from .persistence_proof_occurrence import _check_allocator,_require_indexes
    _hash(expected)
    if (type(max_bytes) is not int or not 1<=max_bytes<=MAX_MANIFEST_BYTES or type(max_metadata_bytes) is not int
            or not 1<=max_metadata_bytes<=64*1024*1024):raise StoreIntegrityError('invalid manifest read budget')
    _require_closed_codec(store)
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('manifest cannot borrow arbitrary transaction')
    try:
        with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,max_metadata_bytes)) as generation:
            head=int(store._checked_head_row()[0])
            if generation not in (head,head-1):raise StoreConflictError('manifest pin outside retained generations')
            required=('lazy_identity_state_interval',)
            if any(i not in store._interval_indexes for i in required):raise StoreError('manifest cannot use legacy interval fallback')
            _require_indexes(store.db,include_order=False,intervals=required)
            schema=store.db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END "
                "FROM sqlite_schema WHERE type='table' AND name='ate_generation_manifests'").fetchone()
            wanted='CREATE TABLE ate_generation_manifests(generation INTEGER PRIMARY KEY,commitment BLOB NOT NULL,manifest BLOB NOT NULL)'
            if schema is None or type(schema[0]) is not str or ''.join(schema[0].lower().split())!=''.join(wanted.lower().split()):
                raise StoreError('manifest schema requires explicit verified construction')
            row=store.db.execute("SELECT CASE WHEN typeof(commitment)='blob' AND length(commitment)=32 THEN commitment END,"
                "CASE WHEN typeof(manifest)='blob' THEN length(manifest) END,"
                "CASE WHEN typeof(manifest)='blob' AND length(manifest)<=? THEN manifest END "
                'FROM ate_generation_manifests WHERE generation=?',(max_bytes,generation)).fetchone()
            if row is None or row[0]!=expected or type(row[1]) is not int:raise StoreIntegrityError('missing or invalid generation manifest source')
            if row[1]>max_bytes:raise ManifestProofBudgetError('manifest source exceeds explicit read budget')
            value=decode_manifest(row[2],expected)
            if value.store_identity!=store.store_identity or value.codec_version!=store.codec.version or value.generation!=generation:
                raise StoreConflictError('manifest source store/codec/generation disagreement')
            metadata=dict(store.db.execute("SELECT key,CASE WHEN typeof(value)='text' AND length(CAST(value AS BLOB))<=4096 THEN value END "
                "FROM store_metadata WHERE key IN ('store_uuid','format_version','codec_version','simulation_schema','rules_id')"))
            if metadata!=dict(store_uuid=value.store_identity,format_version=value.format_version,codec_version=str(value.codec_version),simulation_schema=value.simulation_schema,rules_id=value.rules_id):
                raise StoreIntegrityError('manifest fixed source context disagreement')
            _check_allocator(store,generation,value.head.next_incarnation_id)
            if generation==head:
                actual=store.db.execute('SELECT simulation_position,next_ids,namespace_inventory,namespace_counts,seed FROM save_head WHERE singleton=1').fetchone()
                h=value.head
                if actual!=(h.simulation_position,h.next_ids,h.namespace_inventory,h.namespace_counts,h.seed):
                    raise StoreIntegrityError('manifest exact current head disagreement')
                if value.receipt is not None:
                    r=value.receipt
                    actual=store.db.execute('SELECT commit_token,generation,parent_generation,outcome,row_checksum FROM pin_receipts WHERE pin_token=?',(r.pin_token,)).fetchone()
                    # Released writer receipts disappear. Externally accepted
                    # manifest bytes retain the exact committed receipt binding.
                    if actual is not None and actual!=(r.encoded_commit_token,generation,generation-1,'committed',r.checksum):
                        raise StoreIntegrityError('manifest existing writer receipt disagreement')
            return value
    except (VersionProofBudgetError,ProjectionProofBudgetError) as exc:raise ManifestProofBudgetError(str(exc)) from exc


@dataclass(frozen=True)
class RetainedRoots:
    manifests: tuple
    roots: tuple


def retained_roots(manifests,*,head,pins=(),unresolved=(),checkpoints=()):
    """Pure protected inventory. No collection, body retention or publication."""
    if any(type(v) is not tuple for v in (manifests,pins,unresolved,checkpoints)):
        raise StoreIntegrityError('invalid manifest protection inventory')
    if max(len(manifests),1+len(pins)+2*len(unresolved)+len(checkpoints))>256:
        raise ManifestProofBudgetError('manifest protection inventory exceeds explicit bound')
    known={};by_generation={}
    for pair in manifests:
        if type(pair) is not tuple or len(pair)!=2:raise StoreIntegrityError('invalid protected manifest pair')
        value,expected=pair;_accepted(value,expected)
        marker=(value.store_identity,value.generation)
        if marker in by_generation and by_generation[marker]!=expected:raise StoreIntegrityError('conflicting protected generation authority')
        by_generation[marker]=expected;known[expected]=value
    def get(digest):
        _hash(digest)
        if digest not in known:raise StoreIntegrityError('missing required protected manifest')
        return known[digest]
    current=get(head);required={head}
    def protect(digest):
        value=get(digest)
        if value.store_identity!=current.store_identity:raise StoreConflictError('foreign protected store')
        required.add(digest);return value
    for digest in pins:
        if protect(digest).generation not in (current.generation,current.generation-1):raise StoreConflictError('protected pin outside visibility window')
    for pair in unresolved:
        if type(pair) is not tuple or len(pair)!=2:raise StoreIntegrityError('invalid unresolved manifest pair')
        parent=protect(pair[0])
        if parent.generation not in (current.generation,current.generation-1):raise StoreConflictError('unresolved parent outside recovery window')
        if pair[1] is not None:
            child=protect(pair[1]);validate_successor(parent,pair[0],child,pair[1],child.receipt.encoded_commit_token if child.receipt else b'')
    for digest in checkpoints:
        if protect(digest).generation>current.generation:raise StoreConflictError('future protected checkpoint')
    if required!=set(known):raise StoreIntegrityError('unclassified protected manifest')
    roots={(v.store_identity,v.codec_version,name,root) for digest in required for v in (known[digest],) for name,root in zip(ROOT_NAMES,v.roots)}
    return RetainedRoots(tuple(sorted(required)),tuple(sorted(roots,key=lambda r:(r[0],r[1],r[2],r[3].digest,r[3].count))))
