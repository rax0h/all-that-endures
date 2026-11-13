"""Source-derived owner edits composed against accepted placement roots."""
from .incremental_store import StoreIntegrityError
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_proof_scope as scope
from . import persistence_proof_world as world


def accepted_placement(store, request, namespace, typed, path):
    owner = scope.OwnerScope(namespace, typed)
    inc = scope._identity_source(store, request.pin.captured_head, namespace, typed,
                                 path, request.pairs[1][0].next_incarnation_id)
    root = scope._resolve(store, request.pairs[1][0], owner)
    seek = OrderedSeekMap(store.db, scope._seek_domain(store, owner))
    wanted = None if inc is None else scope.occurrence_member(
        scope.occurrence_domain(store.store_identity, store.codec.version, owner),
        scope.RawOccurrence(namespace, typed, path, inc))
    if seek.get(root, path) != wanted:
        raise StoreIntegrityError('owner edit predecessor lacks accepted placement')
    return inc


def stage(store, request, pin, owners, placements, roots, facts):
    codec, sa = store.codec, request.pairs[1][0]
    by_path = {(p.owner_namespace, codec.encode(p.owner_key), codec.encode(p.occurrence_path)):
               p.incarnation_id for p in placements}
    previous = getattr(request, 'owner_previous', None) or {}
    groups = {}
    for change, projections in owners:
        ns, key = change.namespace, codec.encode(change.key)
        if ns in world.FAMILIES:
            world._check_queries(store, pin, change)
        owner = scope.OwnerScope(ns, key)
        seek = OrderedSeekMap(store.db, scope._seek_domain(store, owner))
        owner_root = scope._resolve(store, sa, owner)
        current = {p[0]: p for p in projections}
        removed = (getattr(request, 'owner_removed', None) or {}).get((ns, key), ())
        edits = (*projections, *removed)
        for projected_path, _inc, kind, fingerprint in edits:
            path = codec.encode(projected_path)
            inc = by_path[ns, key, path] if projected_path in current else None
            old = previous.get((ns, key, path))
            old_raw = None if old is None else scope.RawOccurrence(ns, key, path, old)
            expected = None if old is None else scope.occurrence_member(
                scope.occurrence_domain(store.store_identity, codec.version, owner), old_raw)
            if seek.get(owner_root, path) != expected:
                raise StoreIntegrityError('owner edit differs from accepted predecessor scope')
            raw = None if inc is None else scope.RawOccurrence(ns, key, path, inc)
            owner_root = seek.set(owner_root, path, None if raw is None else scope.occurrence_member(
                scope.occurrence_domain(store.store_identity, codec.version, owner), raw))
            position = scope.group_order_key(ns, key, path)
            for selected, value in ((old, None), (inc, raw)):
                if selected is None:
                    continue
                group = scope.GroupScope(selected)
                mapping = OrderedSeekMap(store.db, scope._seek_domain(store, group))
                root = groups.get(selected)
                if root is None:
                    root = mapping.empty if selected >= sa.next_incarnation_id else scope._resolve(store, sa, group)
                domain = scope.occurrence_domain(store.store_identity, codec.version, group)
                wanted = scope.occurrence_member(domain, old_raw) if value is None else None
                if mapping.get(root, position) != wanted:
                    raise StoreIntegrityError('owner edit predecessor group differs')
                groups[selected] = mapping.set(root, position,
                    None if value is None else scope.occurrence_member(domain, value))
            semantic = world._map(store, b'owner-projections')
            position = codec.encode((ns, key, path))
            wanted = None if old is None else _digest(b'ate-world-placement/1', old.to_bytes(8, 'big'), kind.encode())
            if (semantic.get(facts[1], position) != wanted or fingerprint is not None and
                    world._map(store, b'backing-inventory').get(facts[0], inc.to_bytes(8, 'big')) is not None):
                raise StoreIntegrityError('owner edit lacks exact semantic predecessor authority')
            facts[1] = semantic.set(facts[1], position, None if inc is None else
                _digest(b'ate-world-placement/1', inc.to_bytes(8, 'big'), kind.encode()))
        roots[0] = scope._map(store, 0).set(roots[0], scope._scope_key(owner),
            scope._write_descriptor(store, owner, owner_root) if owner_root.count else None)
    for inc, root in groups.items():
        group = scope.GroupScope(inc)
        roots[1] = scope._map(store, 1).set(roots[1], scope._scope_key(group),
            scope._write_descriptor(store, group, root) if root.count else None)


def scalar_replacement(store, request, change, before, by_key, forest):
    from . import persistence_lazy_identity_catalog as catalog
    from .persistence_proof_world_new_backings import Unsupported
    ns, key = change.namespace, store.codec.encode(change.key)
    if ns not in world.FAMILIES or world._record_class(ns) is None:
        return None
    leaf = by_key.get((catalog.OWNER_TREE_NAMESPACE,
        store.codec.encode((ns, change.key, catalog.path_hash(store.codec, ())))))
    if leaf is None:
        return None
    from itertools import islice
    old_projection = tuple(islice(world._project(store, ns, change.key, before, False, record_header=forest.header), 2))
    if len(old_projection) != 1:
        raise Unsupported()
    projection = forest.project(change, limit=1)
    if (len(old_projection) != 1 or len(projection) != 1 or old_projection[0][:2] != ((), None)
            or projection[0][:2] != ((), None) or old_projection[0][2] != projection[0][2]
            or old_projection[0][3] is None or projection[0][3] is None):
        raise Unsupported()
    owner = scope.OwnerScope(ns, key)
    if scope._resolve(store, request.pairs[1][0], owner).count != 1:
        raise Unsupported()
    old = accepted_placement(store, request, ns, key, store.codec.encode(()))
    if old is None:
        raise StoreIntegrityError('scalar replacement lacks its old root')
    return projection, old


def backing_replacement(store, request, change, before, forest, *, deleting=False):
    """Authenticate a complete small old owner before changing its references."""
    from .persistence_proof_world_backing_value import projection
    from .persistence_proof_world_new_backings import Unsupported
    from .persistence_record_headers import NAMESPACE as RECORDS, checked_record_header
    from .core import Event
    if not deleting:
        if change.namespace != RECORDS:
            return None
        cls, _values, seal = checked_record_header(before)
        after, _fields, next_seal = checked_record_header(change.value)
        if cls is not after or cls is Event or seal != next_seal:
            raise Unsupported()
    old = projection(store, change.namespace, before)
    new = () if deleting else forest.project(change)
    if not deleting and {p[0]: p[2] for p in old} != {p[0]: p[2] for p in new}:
        raise Unsupported()
    if not deleting and old == new:
        return None
    codec = store.codec
    owner = scope.OwnerScope(change.namespace, codec.encode(change.key))
    if scope._resolve(store, request.pairs[1][0], owner).count != len(old):
        raise StoreIntegrityError('changed backing owner lacks complete predecessor scope')
    previous = {}
    for path, inc, _kind, _fingerprint in old:
        actual = accepted_placement(store, request, change.namespace, owner.typed_key, codec.encode(path))
        if actual != inc:
            raise StoreIntegrityError('changed backing differs from accepted predecessor placement')
        previous[path] = inc
    if not deleting:
        fresh = [inc for path, inc, _kind, _fingerprint in new if previous[path] != inc]
        if any(inc not in forest.backings for inc in fresh):
            raise Unsupported()
        forest.closed_roots.update(fresh)
    return new, previous, old if deleting else ()
