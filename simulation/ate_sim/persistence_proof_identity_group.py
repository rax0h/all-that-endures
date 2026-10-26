"""Inactive complete raw group join under externally accepted proof roots.

This authenticates fetched catalog metadata and selected placement intervals,
never owner bodies, target existence, complete World topology or publication.
"""
from dataclasses import dataclass
from types import SimpleNamespace
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,StoreFormatError,CodecError
from . import persistence_lazy_identity_catalog as catalog
from .persistence_lazy_identity_retired import RetiredIdentityRanges,checked_header
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_proof_occurrence import OwnerScope,GroupScope,occurrence_domain,member_commitment,_require_indexes,REQUIRED_INTERVALS,OccurrenceProofBudgetError
from .persistence_proof_occurrence_seek import certificate_commitment as occurrence_commitment,seek_domain as owner_domain,read_occurrence_seek_page
from .persistence_proof_query import QueryScope
from .persistence_proof_query_seek import certificate_commitment as query_commitment,read_query_seek_page,QuerySeekBudgetError
from .persistence_proof_version import certificate_commitment as version_commitment,read_version_bytes,VersionProofBudgetError
from .persistence_proof_projection import _ProjectionCodec,_authority,_require_closed_codec,_closed_snapshot_preflight,ProjectionProofBudgetError
from .persistence_proof_seek import OrderedSeekMap


class GroupProofBudgetError(StoreError):
    """The complete affected group requires a larger checked source path."""


@dataclass(frozen=True)
class RawIdentityGroup:
    incarnation_id: int
    occurrences: tuple
    links: tuple
    anchor: bytes | None
    retired: bool


def _context(store,pin,cert):
    if (cert.store_identity!=store.store_identity or cert.store_identity!=pin.store_identity
            or cert.codec_version!=store.codec.version or cert.generation!=pin.captured_head):
        raise StoreConflictError('group proof store/codec/pin disagreement')


class _Sources:
    def __init__(self,store,pin,certificate,expected,codec,max_bytes,source_limit,metadata_limit,*,budget=None):
        self.store,self.pin,self.certificate,self.expected,self.codec=store,pin,certificate,expected,codec
        self.remaining,self.source_limit,self.metadata_limit=max_bytes,source_limit,metadata_limit
        self.budget=budget

    def charge(self,size):
        self.remaining-=size
        if self.remaining<0:raise GroupProofBudgetError('complete group exceeds aggregate byte budget')
        if self.budget is not None:self.budget.charge(size)

    def value(self,namespace,key,*,absent=False):
        typed=self.codec.encode(key);self.charge(len(namespace.encode('utf-8'))+len(typed))
        if self.budget is not None and getattr(self.budget,'dependencies',None) is not None:self.budget.dependencies.add((0,namespace,typed))
        if self.remaining<1:raise GroupProofBudgetError('group source exceeds aggregate byte budget')
        source=read_version_bytes(self.store,self.pin,self.certificate,self.expected,namespace,typed,
            expected_record_schema=1,max_bytes=min(self.source_limit,self.remaining),max_metadata_bytes=self.metadata_limit)
        if source is None:
            if absent:return None
            raise StoreIntegrityError('missing required group metadata')
        self.charge(len(source.payload)+len(source.memberships))
        value=self.codec.decode(source.payload);memberships=self.codec.decode(source.memberships)
        if (type(memberships) is not tuple or any(type(row) is not tuple or len(row)!=3
                or type(row[0]) is not str or type(row[2]) is not int or row[2]<0 for row in memberships)):
            raise StoreIntegrityError('invalid group source memberships')
        return value,memberships

    def metadata(self,namespace,key):
        value,memberships=self.value(namespace,key)
        if memberships:raise StoreIntegrityError('unexpected catalog metadata memberships')
        return value


class _RetiredSource:
    """Reuse the existing range verifier with only proof-checked raw sources."""
    def __init__(self,sources):self.sources,self.codec=sources,sources.codec
    def _require_pin(self,pin):return self.sources.store._require_pin(pin)
    def read_snapshot(self,pin):return self.sources.store.read_snapshot(pin)
    def read_version(self,pin,namespace,key,*,expected_record_schema):
        if pin!=self.sources.pin or expected_record_schema!=1:raise StoreIntegrityError('invalid retirement source context')
        return SimpleNamespace(value=self.sources.metadata(namespace,key))


def _owner_header(sources,owner,certificate,generation,head):
    header=sources.metadata(catalog.OWNER_NAMESPACE,owner)
    if (type(header) is not tuple or len(header)!=9 or header[0]!='identity-owner/v1'
            or type(header[1]) is not bool or not header[1] or header[2] not in ('lazy','ordinary')
            or type(header[3]) is not int or not 0<=header[3]<=generation
            or type(header[4]) is not int or header[4]<1 or type(header[5]) is not str or len(header[5])!=64
            or type(header[6]) is not bytes or len(header[6])>32
            or type(header[7]) is not int or header[7]<1 or header[7]!=certificate.root.count
            or type(header[8]) is not str or len(header[8])!=64):
        raise StoreIntegrityError('invalid group owner witness')
    adapter=AUXILIARY_OWNER_FAMILIES.get(owner[0])
    if adapter is not None:
        adapter.validate_key(owner[1])
        if owner[1][0]>=certificate.next_incarnation_id or header[2]!='lazy' or header[4]!=adapter.record_schema:
            raise StoreIntegrityError('group physical owner schema/allocator disagreement')
    store=sources.store;typed=sources.codec.encode(owner[1]);rows=None
    common=("CASE WHEN typeof(record_schema)='integer' THEN record_schema END,"
        "CASE WHEN typeof(payload_checksum)='text' AND length(CAST(payload_checksum AS BLOB))=64 THEN payload_checksum END,"
        "CASE WHEN typeof(codec_version)='integer' THEN codec_version END,typeof(payload)")
    if header[2]=='lazy':
        columns=("CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
            "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"+common)
        rows=store._interval_rows('lazy_record_versions',columns,('namespace','typed_key'),(owner[0],typed),generation,'lazy_record_interval',limit=2)
        if len(rows)!=1:raise StoreIntegrityError('group owner source missing or overlapping')
        start,end,end_type,schema,checksum,codec,body_type=rows[0]
        if (type(start) is not int or not 0<=start<=generation or end_type not in ('null','integer')
                or end_type=='integer' and (type(end) is not int or end<=generation or end<=start)):
            raise StoreIntegrityError('invalid selected owner source interval')
    elif generation==head:
        rows=store.db.execute("SELECT CASE WHEN typeof(last_changed_generation)='integer' THEN last_changed_generation END,"+
            common+' FROM records WHERE namespace=? AND typed_key=?',(owner[0],typed)).fetchall()
        if len(rows)!=1:raise StoreIntegrityError('missing current ordinary owner source')
        start,schema,checksum,codec,body_type=rows[0]
    # A historical ordinary header proves metadata only. Its overwritten body
    # remains unavailable and must never be admitted through this raw join.
    if rows is not None:
        store._metadata_rows+=len(rows)
        if (start,schema,checksum)!=(header[3],header[4],header[5]) or codec!=store.codec.version or body_type!='blob':
            raise StoreIntegrityError('group owner/header source commitment disagreement')
    return header


def _owner_point(sources,owner,path,inc,header):
    wanted=catalog.path_hash(sources.codec,path);prefix,count,checksum=header[6:]
    while True:
        node=sources.metadata(catalog.OWNER_TREE_NAMESPACE,(*owner,prefix))
        if catalog.node_commit(sources.codec,node)!=(count,checksum):raise StoreIntegrityError('group owner radix count/digest disagreement')
        if node[0]=='owner-leaf/v1':
            if catalog.path_hash(sources.codec,node[1])!=prefix or prefix!=wanted or node[2]!=inc:
                raise StoreIntegrityError('group owner radix exact placement disagreement')
            return
        if node[1]!=prefix or not wanted.startswith(prefix):raise StoreIntegrityError('group owner radix branch locator disagreement')
        child=next((c for c in node[2] if c[0]==wanted[len(prefix)]),None)
        if child is None:raise StoreIntegrityError('missing group owner radix path')
        _,prefix,count,checksum=child


def _read(store,pin,version_certificate,expected_version,group_certificate,expected_group,link_certificate,expected_links,
          owner_certificates,*,max_members,max_bytes,max_source_bytes,max_metadata_bytes,_budget=None):
    for cert,expected,commitment in ((version_certificate,expected_version,version_commitment),
            (group_certificate,expected_group,occurrence_commitment),(link_certificate,expected_links,query_commitment)):
        _authority(cert,expected,commitment);_context(store,pin,cert)
    if (type(max_members) is not int or not 1<=max_members<=4096 or any(type(n) is not int or not 1<=n<=64*1024*1024
            for n in (max_bytes,max_source_bytes,max_metadata_bytes))):raise StoreIntegrityError('invalid complete group budget')
    if type(group_certificate.scope) is not GroupScope:raise StoreIntegrityError('group proof requires a group scope')
    inc=group_certificate.scope.incarnation_id;allocator=group_certificate.next_incarnation_id
    _require_closed_codec(store);codec=_ProjectionCodec(metadata=True)
    if link_certificate.scope!=QueryScope(catalog.LINK_NAMESPACE,'incarnation',codec.encode(inc)):
        raise StoreIntegrityError('wrong group link query scope')
    if type(owner_certificates) is not tuple:raise StoreIntegrityError('invalid owner authority bundle')
    if group_certificate.root.count>max_members or len(owner_certificates)>max_members:raise GroupProofBudgetError('complete group exceeds member budget')
    owners={}
    sources=_Sources(store,pin,version_certificate,expected_version,codec,max_bytes,max_source_bytes,max_metadata_bytes,budget=_budget)
    for pair in owner_certificates:
        if type(pair) is not tuple or len(pair)!=2:raise StoreIntegrityError('invalid owner authority pair')
        cert,expected=pair;_authority(cert,expected,occurrence_commitment);_context(store,pin,cert)
        if type(cert.scope) is not OwnerScope or cert.next_incarnation_id!=allocator:raise StoreIntegrityError('group owner authority scope/allocator disagreement')
        marker=(cert.scope.namespace,cert.scope.typed_key)
        sources.charge(len(marker[0].encode('utf-8'))+len(marker[1])+64)
        if marker in owners:raise StoreIntegrityError('duplicate group owner authority')
        owners[marker]=cert
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('group proof cannot borrow arbitrary transaction')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,max_metadata_bytes)) as generation:
        required=REQUIRED_INTERVALS+('lazy_record_interval','lazy_query_interval')
        if any(name not in store._interval_indexes for name in required):raise StoreError('group cannot use legacy interval fallback')
        _require_indexes(store.db,include_order=False,intervals=required);head=int(store._checked_head_row()[0])
        rows=[];after=None
        while True:
            page=read_occurrence_seek_page(store,pin,group_certificate,expected_group,after=after,max_metadata_bytes=max_metadata_bytes)
            for row in page.rows:
                sources.charge(len(row.namespace.encode('utf-8'))+len(row.typed_key)+len(row.path)+8);rows.append(row)
            if page.next_after is None:break
            after=page.next_after
        descriptor=sources.metadata(catalog.CATALOG_NAMESPACE,0);retired_header=sources.metadata(catalog.RETIRED_NAMESPACE,0)
        checked_header(retired_header)
        if (type(descriptor) is not tuple or len(descriptor)!=5 or descriptor[0]!=catalog.CATALOG_TAG or descriptor[1]!=catalog.FEATURES
                or type(descriptor[2]) is not int or descriptor[2]!=allocator or type(descriptor[3]) is not int or descriptor[3]<0
                or codec.encode(checked_header(descriptor[4]))!=codec.encode(retired_header)
                or descriptor[3]+(retired_header[2][6] if retired_header[2] else 0)!=allocator-1
                or retired_header[2] is not None and retired_header[2][5]>=allocator):
            raise StoreIntegrityError('group catalog allocator/retirement disagreement')
        retired=RetiredIdentityRanges(_RetiredSource(sources),pin,header=retired_header).contains(inc)
        found=sources.value(catalog.GROUP_NAMESPACE,inc,absent=True)
        if found is None:
            if not retired or rows or owners or link_certificate.root.count:raise StoreIntegrityError('unproved absent group')
            return RawIdentityGroup(inc,(),(),None,True)
        if retired:raise StoreIntegrityError('group has both surviving header and retirement range')
        header,memberships=found
        if (type(header) is not tuple or len(header)!=7 or header[:2]!=('identity-group/v1','mutable')
                or type(header[2]) is not int or header[2]!=len(rows) or type(header[4]) is not int
                or header[4]!=max(0,len(rows)-1)):
            raise StoreIntegrityError('group header schema/count disagreement')
        if rows:
            if memberships:raise StoreIntegrityError('live group has retired membership')
        elif (len(memberships)!=1 or memberships[0][0]!='retired' or memberships[0][1] is not True
                or not 0<=memberships[0][2]<=generation):raise StoreIntegrityError('empty group lacks exact retirement eligibility')
        occurrences=[];paths=[];used=set();headers={}
        for row in rows:
            marker=row.namespace,row.typed_key;cert=owners.get(marker)
            if cert is None:raise StoreIntegrityError('missing exact group owner authority')
            m=OrderedSeekMap(store.db,owner_domain(cert.store_identity,cert.codec_version,cert.scope))
            if m.get(cert.root,row.path)!=member_commitment(occurrence_domain(cert.store_identity,cert.codec_version,cert.scope),row):
                raise StoreIntegrityError('group/owner root placement disagreement')
            key,path=codec.decode(row.typed_key),codec.decode(row.path)
            if codec.encode(key)!=row.typed_key or codec.encode(path)!=row.path:raise StoreIntegrityError('noncanonical group key/path')
            absolute=catalog.placement_path(row.namespace,key,path);encoded=codec.encode(absolute);sources.charge(len(encoded))
            occurrences.append((row.namespace,key,path));paths.append((encoded,absolute));used.add(marker)
            owner=(row.namespace,key)
            if marker not in headers:headers[marker]=_owner_header(sources,owner,cert,generation,head)
            _owner_point(sources,owner,path,inc,headers[marker])
        if used!=set(owners):raise StoreIntegrityError('unused group owner authority')
        paths.sort(key=lambda p:p[0])
        if any(a[0]==b[0] for a,b in zip(paths,paths[1:])):raise StoreIntegrityError('duplicate canonical group placement')
        anchor=paths[0][1] if paths else None;links=tuple((p[1],anchor) for p in paths[1:])
        if (header[3]!=catalog.digest(codec,b'identity-group-occurrences-v1',occurrences) or codec.encode(header[6])!=codec.encode(anchor)
                or header[5]!=catalog.digest(codec,b'identity-group-links-v1',links) or link_certificate.root.count!=len(links)):
            raise StoreIntegrityError('group occurrence/link count/digest/anchor disagreement')
        offset=0;after=None
        while True:
            page=read_query_seek_page(store,pin,link_certificate,expected_links,after=after,max_metadata_bytes=max_metadata_bytes)
            for key,ordinal in page.positions:
                if offset>=len(links) or ordinal!=offset or key!=codec.encode(links[offset][0]):raise StoreIntegrityError('group canonical link projection disagreement')
                value,member=sources.value(catalog.LINK_NAMESPACE,links[offset][0])
                if (codec.encode(value)!=codec.encode(('identity-link/v1',inc,anchor))
                        or codec.encode(member)!=codec.encode((('incarnation',inc,ordinal),))):
                    raise StoreIntegrityError('group link source/membership disagreement')
                offset+=1
            if page.next_after is None:break
            after=page.next_after
        if offset!=len(links):raise StoreIntegrityError('incomplete group links')
        return RawIdentityGroup(inc,tuple(rows),tuple((p[0],paths[0][0]) for p in paths[1:]),paths[0][0] if paths else None,False)


def _read_normalized(store,pin,version_certificate,expected_version,group_certificate,expected_group,link_certificate,expected_links,
        owner_certificates,*,max_members=4096,max_bytes=2097152,max_source_bytes=1048576,max_metadata_bytes=1048576,_budget=None):
    try:return _read(store,pin,version_certificate,expected_version,group_certificate,expected_group,link_certificate,expected_links,
        owner_certificates,max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes,_budget=_budget)
    except (VersionProofBudgetError,OccurrenceProofBudgetError,ProjectionProofBudgetError,QuerySeekBudgetError) as exc:raise GroupProofBudgetError(str(exc)) from exc
    except (CodecError,StoreFormatError,ValueError,TypeError,UnicodeError,RecursionError,IndexError) as exc:raise StoreIntegrityError('invalid group proof metadata/schema') from exc


def read_identity_group_proof(store,pin,version_certificate,expected_version,group_certificate,expected_group,link_certificate,expected_links,
        owner_certificates,*,max_members=4096,max_bytes=2097152,max_source_bytes=1048576,max_metadata_bytes=1048576):
    return _read_normalized(store,pin,version_certificate,expected_version,group_certificate,expected_group,link_certificate,expected_links,
        owner_certificates,max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)
