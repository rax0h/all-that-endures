"""Bounded compact/exceptional Event-ID extents, preserving exact values."""
from .incremental_store import StoreIntegrityError
from .persistence_event_ids import RANGE_TAG
from .persistence_history_types import member_counts
from .persistence_proof_extent_inventory import physical_locators
from . import persistence_proof_target as targets


def read_event_extent(backing,s,scope_pair,budget,max_certification_targets):
    from .persistence_proof_child_extents import RawBackingExtent,_physical
    d=backing.descriptor;end=d[1];budget.take_values(end)
    locators=physical_locators(s,scope_pair,backing.incarnation,budget,require_sequence=True)
    if locators:raise StoreIntegrityError('Event-ID facade has competing physical child backing')
    if d[0]==RANGE_TAG:
        values=tuple(range(1,end+1));return RawBackingExtent(backing,values,(end,0,0),())
    components=[]
    for reference in d[2:4]:
        s.read_limit+=12
        target=targets._resolve_target(s,scope_pair,reference,scope_pair[0].next_incarnation_id)
        components.append(_physical(target,s,scope_pair,budget,max_certification_targets))
    removed,added=(c.members for c in components)
    if len(components[0].target.descriptor)!=9:raise StoreIntegrityError('Event-ID removed sequence requires native value mode')
    previous=0
    for value in removed:
        if type(value) is not int or not previous<value<=end:raise StoreIntegrityError('Event-ID removed values are not strictly ordered within prefix')
        previous=value
    holes=set(removed)
    for value in added:
        # Preserve bool/float representatives while checking integer equality in
        # constant time; float membership in a Python range may iterate it.
        integral=type(value) in (bool,int) or type(value) is float and value.is_integer()
        if integral and 1<=value<=end and int(value) not in holes:raise StoreIntegrityError('Event-ID additions overlap surviving prefix')
    if end-len(removed)+len(added)!=d[4]:raise StoreIntegrityError('Event-ID exception count disagrees')
    values=tuple(v for v in range(1,end+1) if v not in holes)+added
    if len(values)!=d[4]:raise StoreIntegrityError('Event-ID materialized length disagrees')
    return RawBackingExtent(backing,values,member_counts(values),(),components=tuple(components))
