"""Compose fresh native owners/backing forests with existing value/tail proofs.

Unsupported topology and over-budget alias rosters retain checked fallback.
This does not construct another identity authority.
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


class _BudgetExceeded(Exception):
    pass


def prepare(store, request, versions, ordinary, segments):
    from .persistence_proof_world_new_backings import Unsupported
    try:
        return _prepare(store, request, versions, ordinary, segments)
    except Unsupported:
        return None


def _prepare(store, request, versions, ordinary, segments):
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

    from .persistence_proof_world_new_backings import Forest
    forest = Forest(store, request, by_key, predecessor)
    owners, placements, incarnations, sources = [], [], set(forest.backings), []
    identities = {}
    catalog_rows, added = {}, 0
    declared = set()
    for item in versions:
        change = item['change']
        ns, typed = item['namespace'], item['typed_key']
        if change.reinsertion or change.record_schema != 1:
            return None
        within_budget, old = predecessor(ns, typed)
        if not within_budget:
            return None
        added += (not change.delete) - (old is not None)
        if ns in catalog.CATALOG_NAMESPACES:
            catalog_rows[(ns, typed)] = item
            continue
        if ns == DEPENDENCIES:
            # validate_lease_updates checked publisher ownership. Fresh forest
            # rows additionally bind the lease kind to their new descriptor.
            if (ns, typed) in forest.new_rows:
                continue
            if old is None or old.memberships != item['memberships_blob']:
                return None
            continue
        frozen = replace(change, key=codec.decode(typed),
                         value=None if change.delete else codec.decode(item['payload']),
                         memberships=tuple(Membership(*m) for m in codec.decode(item['memberships_blob'])))
        from .persistence_lazy_sequence import NODE_NAMESPACE
        branch = ns == NODE_NAMESPACE and type(frozen.value) is tuple and frozen.value and frozen.value[0] == 'branch'
        if ns in catalog.IDENTITY_OWNER_FAMILIES and not branch:
            sources.append(frozen)
        if old is not None or (ns, typed) in (request.tail_new or {}):
            # The complete remaining transition is checked by the existing
            # value/tail validator below, including deletions and witnesses.
            continue
        concrete = ns in world.AUXILIARY_OWNER_FAMILIES and (ns, typed) in forest.new_rows
        if (ns, typed) in forest.new_rows and not concrete:
            continue
        if change.delete or not concrete and (ns not in world.FAMILIES or world.FAMILIES[ns].collection_kind != 'dict'):
            return None
        # A family name alone does not authorize changing its representation.
        # Only an already declared native lazy collection can accept this slice.
        if not concrete and ns not in declared:
            parent = directory._lookup(store, da[0], ns)
            if parent is None or not parent[0].declared:
                return None
            declared.add(ns)
        projection = forest.project(frozen)
        forest.check(frozen, projection)
        if scope._resolve(store, sa[0], scope.OwnerScope(ns, typed)).count:
            raise StoreIntegrityError('fresh insertion has accepted predecessor placements')
        for path, inc, kind, fingerprint in projection:
            if inc is None:
                tree_key = (ns, frozen.key, catalog.path_hash(codec, path))
                leaf = by_key.get((catalog.OWNER_TREE_NAMESPACE, codec.encode(tree_key)))
                value = None if leaf is None or leaf['change'].delete else codec.decode(leaf['payload'])
                if (type(value) is not tuple or len(value) != 3 or value[:2] != ('owner-leaf/v1', path)
                        or type(value[2]) is not int):
                    return None
                inc = value[2]
            if fingerprint is not None:
                if inc < sa[0].next_incarnation_id:
                    return None
                incarnations.add(inc)
            identity = kind, fingerprint
            if inc in identities and identities[inc] != identity:
                raise StoreIntegrityError('fresh aliases disagree on kind or inline value')
            identities[inc] = identity
            placements.append(IdentityOccurrenceChange(ns, frozen.key, path, incarnation_id=inc))
        owners.append((frozen, projection))
    if (not owners or set(forest.backings) & {i for i, (_kind, fingerprint) in identities.items() if fingerprint is not None}
            or sorted(incarnations) != list(range(sa[0].next_incarnation_id,
                                                  sa[0].next_incarnation_id + len(incarnations)))
            or not set(forest.backings) <= set(identities)):
        return None
    forest.guard_alias_work(p.incarnation_id for p in placements)

    fresh = {(c.namespace, codec.encode(c.key)) for c, _p in owners}
    remaining = []
    for item in versions:
        ns, typed = item['namespace'], item['typed_key']
        if ns not in catalog.CATALOG_NAMESPACES:
            if (ns, typed) not in fresh and (ns, typed) not in forest.new_rows:
                remaining.append(item)
        elif ns == catalog.OWNER_NAMESPACE:
            owner = codec.decode(typed)
            if type(owner) is not tuple or len(owner) != 2 or type(owner[0]) is not str:
                raise StoreIntegrityError('invalid catalog owner key in mixed transition')
            if (owner[0], codec.encode(owner[1])) not in fresh:
                remaining.append(item)
    other_records = tuple(i for i in ordinary if (i['namespace'], i['typed_key']) !=
                          (META, codec.encode(COLLECTION_LAYOUT)))
    from .persistence_proof_world_value import validate_value_transition
    if not validate_value_transition(store, request, tuple(remaining), other_records, segments):
        return None

    counts = Counter(c.namespace for c, _p in owners if c.namespace in world.FAMILIES)
    saw_layout = False
    scalars = {r + '.' + f for r, fs in ROOT_FIELDS.items() for f, k in fs.items() if k == 'int'}
    ordinary_sources = []
    for item in ordinary:
        ns, key = item['namespace'], item['typed_key']
        c = item['change']
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
        elif ns in world.FAMILIES:
            # Existing value proof above requires its exact updated catalog
            # source witness even for a byte-identical ordinary owner rewrite.
            ordinary_sources.append(replace(c, key=codec.decode(item['typed_key']),
                                            value=codec.decode(item['payload'])))
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

    # Existing catalog logic may read unchanged owner-tree metadata while
    # checking fixed-shape backings. Every such dependency must be authenticated
    # and charged, not just catalog rows that happen to appear in the delta.
    class CheckedCatalog(catalog.IdentityCatalog):
        def _read(self, pin, namespace, key):
            within_budget, row = predecessor(namespace, codec.encode(key))
            if not within_budget:
                raise _BudgetExceeded()
            if row is None or row.record_schema != 1:
                raise StoreIntegrityError('missing required accepted catalog predecessor')
            return codec.decode(row.payload)

    class CatalogStore:
        # Retirement range helpers read the store directly rather than _read.
        # Keep those point dependencies under the same accepted byte authority.
        def __getattr__(self, name): return getattr(store, name)
        def __setattr__(self, name, value): setattr(store, name, value)
        def read_version(self, pin, namespace, key, **kwargs):
            within_budget, _row = predecessor(namespace, codec.encode(key))
            if not within_budget: raise _BudgetExceeded()
            return store.read_version(pin, namespace, key, **kwargs)
        def _roster(self, table, columns, keys, values, index, expected):
            nonlocal consumed
            rows = store._interval_rows(table, columns, keys, values, request.pin.captured_head,
                                        index, limit=expected+1, stream=True)
            result = []
            try:
                for row in rows:
                    if len(result) >= expected or any(v is None for v in row):
                        raise StoreIntegrityError('catalog physical alias roster exceeds accepted scope')
                    consumed += sum(len(v.encode()) if type(v) is str else len(v) for v in row)
                    if consumed > MAX_BYTES: raise _BudgetExceeded()
                    result.append(row)
            finally:
                rows.close()
            if len(result) != expected:
                raise StoreIntegrityError('catalog physical alias roster lacks accepted scope')
            return result
        def iter_identity_occurrences_for_incarnation(self, pin, incarnation):
            count = scope._resolve(store, sa[0], scope.GroupScope(incarnation)).count
            text = "CASE WHEN typeof(owner_namespace)='text' AND length(CAST(owner_namespace AS BLOB))<=4096 THEN owner_namespace END"
            blobs = ["CASE WHEN typeof("+name+")='blob' AND length("+name+")<=4096 THEN "+name+" END" for name in ('owner_key', 'occurrence_path')]
            self._roster('lazy_identity_occurrence_versions', ','.join((text, *blobs)),
                         ('incarnation_id',), (incarnation,), 'lazy_identity_incarnation_interval', count)
            return store.iter_identity_occurrences_for_incarnation(pin, incarnation)
        def identity_occurrences_for_incarnation(self, pin, incarnation):
            return tuple(self.iter_identity_occurrences_for_incarnation(pin, incarnation))
        def iter_query_memberships(self, pin, namespace, index_name, value):
            if namespace != catalog.LINK_NAMESPACE or index_name != 'incarnation':
                raise _BudgetExceeded()
            count = max(0, scope._resolve(store, sa[0], scope.GroupScope(value)).count-1)
            rows = self._roster('lazy_query_versions',
                "CASE WHEN typeof(record_key)='blob' AND length(record_key)<=4096 THEN record_key END",
                ('namespace', 'index_name', 'index_value'), (namespace, index_name, codec.encode(value)),
                'lazy_query_interval', count)
            for (key,) in rows:
                within_budget, _row = predecessor(namespace, key)
                if not within_budget: raise _BudgetExceeded()
            return store.iter_query_memberships(pin, namespace, index_name, value)
        def query_memberships(self, pin, namespace, index_name, value, **kwargs):
            rows = tuple(self.iter_query_memberships(pin, namespace, index_name, value))
            return rows[:kwargs['limit']] if 'limit' in kwargs else rows
    active = store._active_read_transaction
    store._active_read_transaction = True
    try:
        try:
            delta = CheckedCatalog(CatalogStore()).prepare_delta(
                request.pin, tuple(sources), tuple(placements), ordinary_changes=tuple(ordinary_sources),
                next_incarnation_id=sa[0].next_incarnation_id + len(incarnations))
        except _BudgetExceeded:
            return None
    finally:
        store._active_read_transaction = active
    wanted = {(c.namespace, codec.encode(c.key)): codec.encode((c.value, c.record_schema,
              c.delete, tuple((m.index_name, m.value, m.ordinal) for m in c.memberships), c.reinsertion))
              for c in delta.decode(codec)[0]}
    actual = {key: codec.encode((None if i['change'].delete else codec.decode(i['payload']), i['change'].record_schema, i['change'].delete,
               codec.decode(i['memberships_blob']), False)) for key, i in catalog_rows.items()}
    if actual != wanted:
        raise StoreIntegrityError('fresh insertion catalog differs from canonical transition')
    request.tail_facts, request.tail_child_root = forest.facts(request.tail_facts or request.facts, request.tail_child_root)
    return owners, placements, added, sa[0].next_incarnation_id + len(incarnations)


def stage(store, request, pin, ca, sa, ia):
    """Certify changed owner/group paths against the actual written roots."""
    owners, placements, added, allocator = request.insertions
    oldca, oldsa, oldia, _ra, _da = request.pairs
    codec = store.codec
    roots = list(oldsa[0].roots)
    facts = list(request.tail_facts or request.facts)
    by_path = {(p.owner_namespace, codec.encode(p.owner_key), codec.encode(p.occurrence_path)): p.incarnation_id for p in placements}
    groups = {}
    for change, projections in owners:
        ns, key = change.namespace, codec.encode(change.key)
        if ns in world.FAMILIES:
            world._check_queries(store, pin, change)
        owner = scope.OwnerScope(ns, key)
        if scope._map(store, 0).get(roots[0], scope._scope_key(owner)) is not None:
            raise StoreIntegrityError('fresh insertion scope is not absent in parent')
        seek = OrderedSeekMap(store.db, scope._seek_domain(store, owner)); owner_root = seek.empty
        for projected_path, _inc, kind, fingerprint in projections:
            path = codec.encode(projected_path)
            inc = by_path[ns, key, path]
            raw = scope.RawOccurrence(ns, key, path, inc)
            owner_root = seek.set(owner_root, path, scope.occurrence_member(
                scope.occurrence_domain(store.store_identity, codec.version, owner), raw))
            group = scope.GroupScope(inc)
            group_seek = OrderedSeekMap(store.db, scope._seek_domain(store, group))
            root = groups.get(inc)
            if root is None:
                root = group_seek.empty if inc >= oldsa[0].next_incarnation_id else scope._resolve(store, oldsa[0], group)
            position = scope.group_order_key(ns, key, path)
            if group_seek.get(root, position) is not None:
                raise StoreIntegrityError('fresh placement already exists in parent group')
            groups[inc] = group_seek.set(root, position, scope.occurrence_member(
                scope.occurrence_domain(store.store_identity, codec.version, group), raw))
            semantic = world._map(store, b'owner-projections')
            position = codec.encode((ns, key, path))
            if (semantic.get(facts[1], position) is not None or fingerprint is not None and
                    world._map(store, b'backing-inventory').get(facts[0], inc.to_bytes(8, 'big')) is not None):
                raise StoreIntegrityError('fresh identity has competing semantic authority')
            facts[1] = semantic.set(facts[1], position, _digest(b'ate-world-placement/1', inc.to_bytes(8, 'big'), kind.encode()))
        roots[0] = scope._map(store, 0).set(roots[0], scope._scope_key(owner),
                    scope._write_descriptor(store, owner, owner_root) if owner_root.count else None)
    for inc, root in groups.items():
        group = scope.GroupScope(inc)
        roots[1] = scope._map(store, 1).set(roots[1], scope._scope_key(group), scope._write_descriptor(store, group, root))
    if (sa[0].next_incarnation_id != allocator or sa[0].roots[:2] != tuple(roots[:2])
            or sa[0].roots[4] != request.tail_child_root or sa[0].roots[5:] != oldsa[0].roots[5:]
            or ca[0].versions.count != oldca[0].versions.count + added
            or ca[0].events != oldca[0].events
            or ia[0].head.namespace_inventory != oldia[0].head.namespace_inventory):
        raise StoreIntegrityError('insertion successor scope/inventory disagrees with exact transition')
    return tuple(facts)
