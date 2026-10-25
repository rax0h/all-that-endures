"""Existing one-hop frozen certification, with accepted raw target authority.

This checks the selected snapshot's complete values, not transitive closure of
its dependencies. No native object restoration or caller hooks are involved.
"""
from .core import Ref
from .incremental_store import StoreError,StoreIntegrityError
from .persistence_frozen_snapshots import immutable_snapshot_value
from .persistence_nonreflexive_keys import nonreflexive_key_reference
from .persistence_lazy_nested_history import reference
from . import persistence_proof_target as targets


def check_frozen_members(s,scope_pair,backing,items,max_targets):
    values=(v for _,v in items) if backing.kind=='frozen-map' else iter(items)
    checked={};actual=True
    def eligible(ref):
        return nonreflexive_key_reference(ref) or reference(ref) and ref.kind in ('frozen-list','frozen-map')
    def resolve(ref):
        key=s.codec.encode(ref)
        if key not in checked:
            if len(checked)>=max_targets:raise StoreError('frozen certification exceeds target budget')
            s.charge(len(key));s.read_limit+=12
            checked[key]=targets._resolve_target(s,scope_pair,ref,scope_pair[0].next_incarnation_id)
        target=checked[key]
        return True if target.kind=='nan-key' else target.descriptor[3]
    def visit(item):
        if eligible(item):resolve(item)
        elif type(item) is Ref:visit(item.kind);visit(item.id)
        elif type(item) in (tuple,frozenset):
            for child in item:visit(child)
    for value in values:
        # Check every eligible dependency, including ones after a mutable value
        # inside a tuple/Ref/frozenset. The pure runtime predicate may short-circuit.
        visit(value)
        actual=immutable_snapshot_value(value,resolve) and actual
    if actual!=backing.descriptor[3]:raise StoreIntegrityError('frozen certification disagrees with complete backing values')
    return tuple(checked.values())
