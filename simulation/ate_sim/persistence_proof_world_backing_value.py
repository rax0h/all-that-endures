"""Fixed-shape backing edits; accepted topology and member policies stay exact."""
from .incremental_store import StoreIntegrityError
from .persistence_proof_content import version_key
from . import persistence_proof_publication as content
from . import persistence_proof_world as world
from .persistence_history_types import member_counts


def _parent(store,request,namespace,inc):
    key=store.codec.encode(inc)
    row=content._source_version(store,request.pin.captured_head,namespace,key,max_bytes=4*1048576)
    if row is None:raise StoreIntegrityError('changed backing has no parent descriptor')
    wanted=content._version_value(namespace,key,row,store.codec.version)
    if content._map(store).get(request.pairs[0][0].versions,version_key(namespace,key))!=wanted:
        raise StoreIntegrityError('backing parent descriptor lacks accepted content')
    return store.codec.decode(row.payload)


def eligible(store,request,change,old):
    """Check only changed physical values; unsupported shape uses full audit."""
    from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE,ENTRY_NAMESPACE
    from .persistence_record_headers import NAMESPACE as RECORDS,checked_record_header
    from .core import Event
    ns=change.namespace;new=change.value;adapter=AUXILIARY_OWNER_FAMILIES.get(ns)
    if adapter is None or ns not in (PAGE_NAMESPACE,ENTRY_NAMESPACE,RECORDS):return False
    adapter.validate_source(change,'lazy',store.codec)
    if ns==RECORDS:
        before,values,state=checked_record_header(old);after,fields,next_state=checked_record_header(new)
        if before is not after or before is Event or store.codec.encode(state)!=store.codec.encode(next_state):return False
        world._check_field_values(store,None,after,fields)
        return True
    descriptor=_parent(store,request,DESCRIPTOR_NAMESPACE,change.key[0])
    if descriptor[0] not in ('list','map'):return False
    if ns==PAGE_NAMESPACE:
        return descriptor[0]=='list' and len(old)==len(new) and member_counts(old)==member_counts(new)
    # Complete membership, native key bytes and insertion ordinal stay exact.
    # Map type counters describe keys; the exact old key preserves that witness.
    return (descriptor[0]=='map' and old[0]==new[0] and type(old[0]) is type(new[0])
            and store.codec.encode(old[1])==store.codec.encode(new[1]))


def projection(store,namespace,value):
    from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    adapter=AUXILIARY_OWNER_FAMILIES[namespace]
    return tuple((path,inc,world.target._reference(adapter.resolve_path(value,path))[0],None)
                 for path,inc in adapter.reference_placements(value))
