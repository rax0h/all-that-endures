"""Explicit complete World format selection; no migration or second publisher."""
from .incremental_store import StoreFormatError, StoreIntegrityError

FORMAT_VERSION = 6
IDENTITY_STORAGE = 'checked-catalog/v1'
FEATURES = ('complete-world/v1', 'checked-identity-catalog/v2',
    'counted-household-settlement/v1', 'recursive-history-records/v1',
    'native-nan-atoms/v1', 'paged-event-id-exceptions/v1',
    'bounded-cache-maintenance/v1', 'hybrid-publication/v1')


def selected(manifest, floor):
    marked = manifest.get('identity_storage') == IDENTITY_STORAGE or 'complete_features' in manifest
    if floor >= FORMAT_VERSION or marked:
        if floor < FORMAT_VERSION:
            raise StoreFormatError('complete World markers require reader capability 6')
        if (set(manifest) != {'schema','collections','identity_storage','event_storage','complete_features'}
                or manifest.get('identity_storage') != IDENTITY_STORAGE
                or type(manifest.get('complete_features')) is not tuple
                or manifest['complete_features'] != FEATURES):
            raise StoreIntegrityError('complete World feature/identity authority is missing or incompatible')
        return True
    return False


def marked_manifest(manifest):
    return dict(manifest, identity_storage=IDENTITY_STORAGE, complete_features=FEATURES)


def check_open(store, pin, head, manifest):
    """Only fixed checked metadata; archived payload and global links stay cold."""
    from .persistence_lazy_identity_catalog import IdentityCatalog, LINK_NAMESPACE
    from .persistence_lazy import BUCKET_SPECS, BUCKET_KIND, SCALAR_RECORD_KINDS, SCALAR_NAMESPACES
    from .persistence_adapters import AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KIND
    floor=int(store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
    if floor>=7:
        from .persistence_proof_world_session import _WorldProofAuthority
        authority=getattr(store,'_world_proof_authority',None)
        if type(authority) is not _WorldProofAuthority:raise StoreFormatError('proof World admission requires explicit audited native integration')
        authority.admit(pin)
    return _check_fixed_contract(store,pin,head,manifest)


def _check_fixed_contract(store,pin,head,manifest):
    """Existing complete layout audit, also used by explicit proof construction."""
    from .persistence_lazy_identity_catalog import IdentityCatalog,LINK_NAMESPACE
    from .persistence_lazy import BUCKET_SPECS,BUCKET_KIND,SCALAR_RECORD_KINDS,SCALAR_NAMESPACES
    from .persistence_adapters import AGENCY_ACTIONS_NAMESPACE,PACKED_LIST_KIND
    floor=int(store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
    if not selected(manifest,floor):return None
    IdentityCatalog(store)._descriptor(pin)
    if store.db.execute('SELECT 1 FROM records WHERE namespace=? LIMIT 1',(LINK_NAMESPACE,)).fetchone():
        raise StoreIntegrityError('complete World contains competing ordinary identity links')
    size=store.namespace_size(pin,LINK_NAMESPACE)
    if head.namespace_counts.get(LINK_NAMESPACE,(0,0))!=(size,0):
        raise StoreIntegrityError('complete identity count disagrees with head')
    layout=manifest['collections']
    if (any(layout[ns][0] not in SCALAR_RECORD_KINDS for ns in SCALAR_NAMESPACES)
            or layout[AGENCY_ACTIONS_NAMESPACE][0]!=PACKED_LIST_KIND
            or layout['world.event_ids'][0] not in ('event-ids-range/v1','event-ids-exceptions/v1')
            or any(layout[ns][0]!=BUCKET_KIND for ns in BUCKET_SPECS)):
        raise StoreIntegrityError('complete World lacks mandatory compact root representations')
    return size


def upgrade_lazy_snapshot(source,destination,*,rules_id):
    """Source-preserving upgrade of a bounded legacy lazy World snapshot.

    Older formats first use their established explicit conversion path. This
    operation normalizes current graphs and installs markers in the same private
    copy transaction; it never changes the source or overwrites a destination.
    """
    from .persistence_catalog_copy import _copy_with_checked_catalog
    return _copy_with_checked_catalog(source,destination,rules_id=rules_id,
        normalize_events=True,normalize_advancement=True,complete_format=True)
