"""Inactive typed backing plus complete incoming physical group metadata.

Owner payload semantics, child extents, recursive closure, native identity
admission and World topology are separate prerequisites. No publication occurs.
"""
from dataclasses import dataclass

from .incremental_store import StoreError, StoreIntegrityError, CodecError
from .persistence_proof_occurrence import GroupScope, OwnerScope
from .persistence_proof_occurrence_seek import read_occurrence_seek_page
from .persistence_proof_query import QueryScope
from .persistence_proof_version import VersionCertificate, certificate_commitment
from .persistence_proof_identity_group import _read_normalized, GroupProofBudgetError, RawIdentityGroup
from . import persistence_proof_target as target


@dataclass(frozen=True)
class RawTargetGroup:
    target: target.RawReferenceTarget
    group: RawIdentityGroup


def _check(store, pin, reference, content_pair, scope_pair, inventory_pair, *,
          max_members, max_bytes, max_source_bytes, max_metadata_bytes):
    for value, maximum in ((max_members, 4096), (max_bytes, 64*1024*1024),
                           (max_source_bytes, 64*1024*1024), (max_metadata_bytes, 1048576)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise StoreIntegrityError('invalid target/group budget')
    target._require_closed_codec(store)
    _, incarnation = target._reference(reference)
    target._pairs(store, pin, (content_pair, scope_pair, inventory_pair))
    if store.db.in_transaction:
        raise StoreError('target/group join requires owned snapshot')

def _read_checked(store, pin, reference, content_pair, scope_pair, inventory_pair, *,
                  max_members, max_bytes, max_source_bytes, max_metadata_bytes, _sources=None):
    """Private composition seam; caller has validated arguments and owns snapshot."""
    if not getattr(store, '_checked_snapshot_depth', 0):
        raise StoreError('target/group composition requires checked snapshot')
    _, incarnation = target._reference(reference)
    target.inventory._snapshot_checks(store, *inventory_pair)
    # Bind the derived version certificate to the physically checked accepted
    # content root. Component hash presence alone is never source authority.
    with target.content._snapshot(store, pin, *content_pair, max_metadata_bytes):
        pass
    group_pair = target.scope.read_scope_certificate(
        store, pin, *scope_pair, GroupScope(incarnation), max_metadata_bytes=max_metadata_bytes)
    if group_pair[0].root.count > max_members:
        raise GroupProofBudgetError('complete incoming group exceeds member budget')
    if _sources is None:sources=target._Sources(store,pin,content_pair,max_bytes,max_source_bytes,max_metadata_bytes)
    else:
        sources=_sources
        if (type(sources) is not target._Sources or sources.store is not store or sources.pin!=pin
                or sources.pair!=content_pair or sources.per_source!=max_source_bytes or sources.metadata_limit!=max_metadata_bytes
                or sources.remaining!=max_bytes):raise StoreIntegrityError('shared target source context disagreement')
        sources.read_limit+=128
    backing = target._resolve_target(sources, scope_pair, reference, inventory_pair[0].head.next_incarnation_id)
    # Discover authority exclusively from authenticated group pages. SQL
    # DISTINCT over live owners would be an unauthenticated completeness claim.
    owners = {}; after = None; count = 0
    while True:
        page = read_occurrence_seek_page(store, pin, *group_pair, after=after,
                                        max_metadata_bytes=max_metadata_bytes)
        for row in page.rows:
            count += 1
            if count > max_members:
                raise GroupProofBudgetError('incoming group exceeds member budget')
            sources.charge(len(row.namespace.encode()) + len(row.typed_key) + len(row.path) + 8)
            marker = row.namespace, row.typed_key
            if marker not in owners:
                owners[marker] = target.scope.read_scope_certificate(
                    store, pin, *scope_pair, OwnerScope(*marker), max_metadata_bytes=max_metadata_bytes)
        if page.next_after is None:
            break
        after = page.next_after
    if count != group_pair[0].root.count:
        raise StoreIntegrityError('incomplete target group discovery')
    links_pair = target.scope.read_scope_certificate(
        store, pin, *scope_pair, QueryScope(target.catalog.LINK_NAMESPACE, 'incarnation', sources.codec.encode(incarnation)),
        max_metadata_bytes=max_metadata_bytes)
    if sources.remaining < 1:
        raise target.TargetProofBudgetError('target/group sources exceed aggregate budget')
    content = content_pair[0]
    version = VersionCertificate(content.store_identity, content.generation, content.codec_version, content.versions)
    # Group reads charge the shared parent so later incoming-body checks
    # receive the actual remaining budget, including repeated metadata reads.
    group = _read_normalized(
        store, pin, version, certificate_commitment(version), *group_pair, *links_pair,
        tuple(owners[k] for k in sorted(owners)), max_members=max_members, max_bytes=sources.remaining,
        max_source_bytes=max_source_bytes, max_metadata_bytes=max_metadata_bytes, _budget=sources)
    if group.retired or not group.occurrences or group.incarnation_id != backing.incarnation:
        raise StoreIntegrityError('target/group liveness disagreement')
    return RawTargetGroup(backing, group), sources


def _read(store, pin, reference, content_pair, scope_pair, inventory_pair, *,
          max_members, max_bytes, max_source_bytes, max_metadata_bytes):
    options = dict(max_members=max_members, max_bytes=max_bytes, max_source_bytes=max_source_bytes,
                   max_metadata_bytes=max_metadata_bytes)
    _check(store, pin, reference, content_pair, scope_pair, inventory_pair, **options)
    with store.read_snapshot(pin, _preflight=lambda: target._preflight(store, max_metadata_bytes)):
        return _read_checked(store, pin, reference, content_pair, scope_pair, inventory_pair, **options)[0]


def read_target_group(store, pin, reference, content_authority, scope_authority, inventory_authority, *,
                      max_members=4096, max_bytes=4194304, max_source_bytes=1048576, max_metadata_bytes=1048576):
    """Authenticate one live target and its complete incoming group, as raw data."""
    try:
        return _read(store, pin, reference, content_authority, scope_authority, inventory_authority,
                     max_members=max_members, max_bytes=max_bytes, max_source_bytes=max_source_bytes,
                     max_metadata_bytes=max_metadata_bytes)
    except (CodecError, ValueError, TypeError, UnicodeError, RecursionError, IndexError, AttributeError) as exc:
        raise StoreIntegrityError('invalid target/group metadata') from exc
