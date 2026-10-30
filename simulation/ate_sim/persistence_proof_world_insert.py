"""Bounded fresh scalar-owner insertion using the existing catalog and proofs.

Existing-owner edits, aliases, nested backings and retirement stay on their
existing checked paths. This does not construct another identity authority.
"""
from collections import Counter
from dataclasses import replace

from .incremental_store import StoreIntegrityError, Membership
from .persistence_lazy_store import IdentityOccurrenceChange
from .persistence_proof_content import version_key, record_key, record_commitment
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_lazy_identity_catalog as catalog
from . import persistence_proof_scope as scope
from . import persistence_proof_world as world
from . import persistence_proof_publication as content
from . import persistence_proof_record as records
from . import persistence_proof_collection_directory as directory

MAX_ROWS = 512
MAX_BYTES = 4 * 1048576


def prepare(store, request, versions, ordinary, segments):
    """Authenticate the exact finite insertion, or retain checked fallback."""
    from .persistence_adapters import META, COLLECTION_LAYOUT
    from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES
    from .persistence_schema import ROOT_FIELDS
    from .persistence_session import EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY
    from .incremental_store import _record_checksum

    if segments or not versions or len(versions) + len(ordinary) > MAX_ROWS:
        return None
    consumed = sum(len(i['payload'] or b'') + len(i.get('memberships_blob', b'')) + len(i['typed_key'])
                   for i in (*versions, *ordinary))
    if consumed > MAX_BYTES:
        return None
    codec = store.codec
    ca, sa, _ia, ra, da = request.pairs
    by_key = {(i['namespace'], i['typed_key']): i for i in versions}
    predecessors = {}

    def predecessor(ns, typed):
        nonlocal consumed
        if (ns, typed) in predecessors:
            return True, predecessors[ns, typed]
        sizes = store._interval_rows('lazy_record_versions', 'length(payload)+length(memberships)',
            ('namespace', 'typed_key'), (ns, typed), request.pin.captured_head, 'lazy_record_interval', limit=2)
        if len(sizes) == 1:
            consumed += sizes[0][0]
            if consumed > MAX_BYTES:
                return False, None
        old = content._source_version(store, request.pin.captured_head, ns, typed, max_bytes=MAX_BYTES)
        expected = None if old is None else content._version_value(ns, typed, old, codec.version)
        if content._map(store).get(ca[0].versions, version_key(ns, typed)) != expected:
            raise StoreIntegrityError('insertion predecessor lacks accepted content')
        predecessors[ns, typed] = old
        return True, old

    owners, placements, incarnations = [], [], []
    catalog_rows, added = {}, 0
    declared = set()
    for item in versions:
        change = item['change']
        ns, typed = item['namespace'], item['typed_key']
        if change.delete or change.reinsertion or change.record_schema != 1:
            return None
        within_budget, old = predecessor(ns, typed)
        if not within_budget:
            return None
        added += old is None
        if ns in catalog.CATALOG_NAMESPACES:
            catalog_rows[(ns, typed)] = item
            continue
        if ns == DEPENDENCIES:
            # validate_lease_updates already checked ownership and canonical
            # values; insertion does not introduce a backing or its lease row.
            if old is None or old.memberships != item['memberships_blob']:
                return None
            continue
        if ns not in world.FAMILIES or world.FAMILIES[ns].collection_kind != 'dict' or old is not None:
            return None
        # A family name alone does not authorize changing its representation.
        # Only an already declared native lazy collection can accept this slice.
        if ns not in declared:
            parent = directory._lookup(store, da[0], ns)
            if parent is None or not parent[0].declared:
                return None
            declared.add(ns)
        frozen = replace(change, key=codec.decode(typed), value=codec.decode(item['payload']),
                         memberships=tuple(Membership(*m) for m in codec.decode(item['memberships_blob'])))
        projection = tuple(world._project(store, ns, frozen.key, frozen.value, False))
        if len(projection) > 1 or projection and (
                projection[0][0] != () or projection[0][1] is not None
                or not projection[0][2].startswith('record:') or projection[0][3] is None):
            return None
        if scope._resolve(store, sa[0], scope.OwnerScope(ns, typed)).count:
            raise StoreIntegrityError('fresh insertion has accepted predecessor placements')
        if projection:
            tree_key = (ns, frozen.key, catalog.path_hash(codec, ()))
            leaf = by_key.get((catalog.OWNER_TREE_NAMESPACE, codec.encode(tree_key)))
            value = None if leaf is None else codec.decode(leaf['payload'])
            if (type(value) is not tuple or len(value) != 3 or value[:2] != ('owner-leaf/v1', ())
                    or type(value[2]) is not int):
                return None
            inc = value[2]
            if inc < sa[0].next_incarnation_id:
                return None
            incarnations.append(inc)
            placements.append(IdentityOccurrenceChange(ns, frozen.key, (), incarnation_id=inc))
        owners.append((frozen, projection))
    if not owners or sorted(incarnations) != list(range(sa[0].next_incarnation_id,
                                                       sa[0].next_incarnation_id + len(incarnations))):
        return None

    # Regenerate catalog witnesses with the existing causal primitive. This
    # reads only the global descriptor and the fresh owners/groups just proved
    # absent; it never discovers unrelated owners or historical bodies.
    for key, item in catalog_rows.items():
        if key[0] != catalog.CATALOG_NAMESPACE and content._map(store).get(ca[0].versions, version_key(*key)) is not None:
            return None
    # prepare_delta reads both singleton headers even when no identity is
    # allocated. Authenticate and budget these dependencies before transfer.
    for ns in (catalog.CATALOG_NAMESPACE, catalog.RETIRED_NAMESPACE):
        within_budget, _old = predecessor(ns, codec.encode(0))
        if not within_budget:
            return None
    active = store._active_read_transaction
    store._active_read_transaction = True
    try:
        delta = catalog.IdentityCatalog(store).prepare_delta(
            request.pin, tuple(c for c, _p in owners), tuple(placements),
            next_incarnation_id=sa[0].next_incarnation_id + len(incarnations))
    finally:
        store._active_read_transaction = active
    wanted = {(c.namespace, codec.encode(c.key)): codec.encode((c.value, c.record_schema,
              c.delete, tuple((m.index_name, m.value, m.ordinal) for m in c.memberships), c.reinsertion))
              for c in delta.decode(codec)[0]}
    actual = {key: codec.encode((codec.decode(i['payload']), i['change'].record_schema, False,
               codec.decode(i['memberships_blob']), False)) for key, i in catalog_rows.items()}
    if actual != wanted:
        raise StoreIntegrityError('fresh insertion catalog differs from canonical transition')

    counts = Counter(c.namespace for c, _p in owners)
    saw_layout = False
    scalars = {r + '.' + f for r, fs in ROOT_FIELDS.items() for f, k in fs.items() if k == 'int'}
    for item in ordinary:
        ns, key = item['namespace'], item['typed_key']
        c = item['change']
        # Even identical ordinary owner bytes acquire a new revision/checksum.
        # Their catalog source witness must advance, which this insertion-only
        # slice deliberately does not authorize.
        if ns in world.FAMILIES:
            return None
        if c.delete or c.record_schema != 1 or item['memberships']:
            return None
        row = store.db.execute('SELECT CASE WHEN typeof(payload)=\'blob\' AND length(payload)<=? THEN payload END,'
                               'payload_checksum,codec_version,record_schema,last_changed_generation '
                               'FROM records WHERE namespace=? AND typed_key=?', (MAX_BYTES-consumed, ns, key)).fetchone()
        new_layout = row is None and ns == META and c.key == COLLECTION_LAYOUT
        if new_layout:
            if records._map(store).get(ra[0].root, record_key(ns, key)) is not None:
                raise StoreIntegrityError('new layout lacks accepted absence')
            # The first layout overlay inherits the authenticated original
            # manifest; later overlays inherit the previous layout record.
            key = codec.encode('manifest')
            row = store.db.execute('SELECT CASE WHEN typeof(payload)=\'blob\' AND length(payload)<=? THEN payload END,'
                                   'payload_checksum,codec_version,record_schema,last_changed_generation '
                                   'FROM records WHERE namespace=? AND typed_key=?', (MAX_BYTES-consumed, ns, key)).fetchone()
        if row is None or type(row[0]) is not bytes:
            return None
        payload, checksum, version, schema, revision = row
        consumed += len(payload)
        if (checksum != _record_checksum(ns, key, schema, version, revision, payload)
                or records._map(store).get(ra[0].root, record_key(ns, key)) != record_commitment(
                    ns, key, last_changed_generation=revision, codec_version=version, record_schema=schema, payload=payload)):
            raise StoreIntegrityError('insertion ordinary predecessor lacks accepted content')
        if ns == META and c.key == COLLECTION_LAYOUT:
            before = codec.decode(payload)['collections'] if new_layout else codec.decode(payload)
            expected = dict(before)
            for family, count in counts.items():
                kind, size, chunks = expected[family]
                expected[family] = (kind, size + count, chunks)
            if codec.encode(expected) != item['payload']:
                raise StoreIntegrityError('insertion layout does not match new owners')
            saw_layout = True
        elif ns == EVENT_STORAGE and c.key == COMMIT_DESCRIPTOR_KEY:
            if item['payload'] != codec.encode((1, request.pin.captured_head + 1, codec.decode(request.token))):
                raise StoreIntegrityError('insertion commit descriptor disagreement')
        elif ns in scalars and ns != 'world.next_event':
            value = codec.decode(item['payload'])
            if (codec.decode(key) != 0 or type(value) is not tuple or len(value) != 2
                    or type(value[0]) is not int or value[0] != 0 or type(value[1]) is not int):
                return None
        elif item['payload'] != payload:
            return None
    if not saw_layout:
        return None
    return owners, placements, added, sa[0].next_incarnation_id + len(incarnations)


def stage(store, request, pin, ca, sa, ia):
    """Certify changed owner/group paths against the actual written roots."""
    owners, placements, added, allocator = request.insertions
    oldca, oldsa, oldia, _ra, _da = request.pairs
    codec = store.codec
    roots = list(oldsa[0].roots)
    facts = list(request.facts)
    by_owner = {(p.owner_namespace, codec.encode(p.owner_key)): p.incarnation_id for p in placements}
    for change, projections in owners:
        ns, key = change.namespace, codec.encode(change.key)
        world._check_queries(store, pin, change)
        if not projections:
            continue
        inc = by_owner[ns, key]
        path = codec.encode(())
        raw = scope.RawOccurrence(ns, key, path, inc)
        for kind, selected, position in ((0, scope.OwnerScope(ns, key), path),
                                         (1, scope.GroupScope(inc), scope.group_order_key(ns, key, path))):
            mapping = scope._map(store, kind)
            if mapping.get(roots[kind], scope._scope_key(selected)) is not None:
                raise StoreIntegrityError('fresh insertion scope is not absent in parent')
            seek = OrderedSeekMap(store.db, scope._seek_domain(store, selected))
            root = seek.set(seek.empty, position, scope.occurrence_member(
                scope.occurrence_domain(store.store_identity, codec.version, selected), raw))
            roots[kind] = mapping.set(roots[kind], scope._scope_key(selected),
                                      scope._write_descriptor(store, selected, root))
        semantic = world._map(store, b'owner-projections')
        position = codec.encode((ns, key, path))
        if semantic.get(facts[1], position) is not None or world._map(store, b'backing-inventory').get(facts[0], inc.to_bytes(8, 'big')) is not None:
            raise StoreIntegrityError('fresh inline identity has competing semantic authority')
        facts[1] = semantic.set(facts[1], position, _digest(
            b'ate-world-placement/1', inc.to_bytes(8, 'big'), projections[0][2].encode()))
    if (sa[0].next_incarnation_id != allocator or sa[0].roots[:2] != tuple(roots[:2])
            or sa[0].roots[4:] != oldsa[0].roots[4:]
            or ca[0].versions.count != oldca[0].versions.count + added
            or ca[0].events != oldca[0].events
            or ia[0].head.namespace_inventory != oldia[0].head.namespace_inventory):
        raise StoreIntegrityError('insertion successor scope/inventory disagrees with exact transition')
    return tuple(facts)
