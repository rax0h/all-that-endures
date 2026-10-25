"""Inactive complete direct projection/target join for registered raw owners.

No recursive closure, member extents, semantic transition certificate, complete
alias verification or native World admission follows from this result alone.
"""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,CodecError
from .persistence_proof_projection import read_owner_projection,_ProjectionCodec
from .persistence_proof_version import VersionCertificate,certificate_commitment
from .persistence_proof_occurrence import OwnerScope
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from . import persistence_proof_target as target

@dataclass(frozen=True)
class RawOwnerTargets:
    source:object
    references:tuple
    targets:tuple


def _read(store,pin,namespace,typed_key,content_pair,scope_pair,inventory_pair,*,max_bytes,max_source_bytes,max_metadata_bytes,max_references):
    for n,maximum in ((max_bytes,64*1024*1024),(max_source_bytes,64*1024*1024),(max_metadata_bytes,1048576),(max_references,128)):
        if type(n) is not int or not 1<=n<=maximum:raise StoreIntegrityError('invalid owner-target budget')
    if type(namespace) is not str or namespace not in AUXILIARY_OWNER_FAMILIES or type(typed_key) is not bytes or len(typed_key)>4096:raise StoreError('join requires registered bounded physical owner')
    target._require_closed_codec(store);target._pairs(store,pin,(content_pair,scope_pair,inventory_pair))
    if store.db.in_transaction:raise StoreError('owner-target join requires owned snapshot')
    with store.read_snapshot(pin,_preflight=lambda:target._preflight(store,max_metadata_bytes)):
        target.inventory._snapshot_checks(store,*inventory_pair)
        with target.content._snapshot(store,pin,*content_pair,max_metadata_bytes):pass
        owner=target.scope.read_scope_certificate(store,pin,*scope_pair,OwnerScope(namespace,typed_key),max_metadata_bytes=max_metadata_bytes)
        c=content_pair[0];version=VersionCertificate(c.store_identity,c.generation,c.codec_version,c.versions)
        projection=read_owner_projection(store,pin,version,certificate_commitment(version),*owner,max_bytes=min(max_bytes,max_source_bytes),max_references=max_references,max_metadata_bytes=max_metadata_bytes)
        sources=target._Sources(store,pin,content_pair,max_bytes,max_source_bytes,max_metadata_bytes,read_limit=128*max_references)
        sources.charge(len(namespace.encode())+len(typed_key))
        if projection.source is None:return RawOwnerTargets(None,(),())
        sources.charge(len(projection.source.payload)+len(projection.source.memberships))
        codec=_ProjectionCodec();value=codec.decode(projection.source.payload);adapter=AUXILIARY_OWNER_FAMILIES[namespace]
        refs=[];targets={}
        for path,inc in adapter.reference_placements(value):
            encoded=codec.encode(path);sources.charge(len(encoded)+8)
            reference=adapter.resolve_path(value,path);kind,actual=target._reference(reference)
            if actual!=inc:raise StoreIntegrityError('owner path/target incarnation disagreement')
            if inc in targets:
                if targets[inc].kind!=kind:raise StoreIntegrityError('owner has competing target kinds for one incarnation')
            else:targets[inc]=target._resolve_target(sources,scope_pair,reference,inventory_pair[0].head.next_incarnation_id)
            refs.append((encoded,inc))
        if len(refs)!=projection.reference_count:raise StoreIntegrityError('owner projection changed during join')
        return RawOwnerTargets(projection.source,tuple(sorted(refs)),tuple(targets[k] for k in sorted(targets)))


def read_owner_targets(store,pin,namespace,typed_key,content_authority,scope_authority,inventory_authority,*,max_bytes=4194304,max_source_bytes=1048576,max_metadata_bytes=1048576,max_references=128):
    try:return _read(store,pin,namespace,typed_key,content_authority,scope_authority,inventory_authority,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes,max_references=max_references)
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError,IndexError,AttributeError) as exc:raise StoreIntegrityError('invalid owner-target closure metadata') from exc
