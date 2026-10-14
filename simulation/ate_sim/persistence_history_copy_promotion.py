"""Explicit copy-only promotion, using the existing counted sequence builder."""
from collections import Counter
from itertools import chain
from dataclasses import is_dataclass, replace

from .incremental_store import StoreIntegrityError, StoreConflictError, _framed_sha
from .persistence_lazy_store import IdentityOccurrenceChange, VersionChange
from .persistence_lazy_nested_history import (
    HistoryReference, reference, LazyHistoryList, DESCRIPTOR_NAMESPACE, PAGE_NAMESPACE,
)
from .persistence_lazy_sequence import LazyOrderedSequence, NODE_NAMESPACE
from .persistence_history_types import NAMESPACE as TYPES
from .persistence_history_retirement import NAMESPACE as RETIREMENT
from .persistence_history_dependencies import dependency_value
from .persistence_lazy_families import IDENTITY_OWNER_FAMILIES, AUXILIARY_OWNER_FAMILIES
from .persistence_schema import RECORD_FIELDS
from .core import Event


def selection(values):
    values = tuple(values)
    if any(type(inc) is not int or inc < 1 for inc in values) or len(set(values)) != len(values):
        raise ValueError('copy promotion requires distinct positive incarnation IDs')
    return values


def capture_lists(store, pin, selected):
    output = {}
    for inc in selected:
        try:
            descriptor = store.read_version(pin, DESCRIPTOR_NAMESPACE, inc, expected_record_schema=1).value
        except KeyError as exc:
            raise StoreIntegrityError('selected copy promotion has no append backing') from exc
        if type(descriptor) is not tuple or not descriptor or descriptor[0] != 'list':
            raise StoreIntegrityError('selected copy promotion is not a mutable append list')
        if store.contains_lazy_key(pin, RETIREMENT, inc):
            raise StoreConflictError('retiring append backing cannot be promoted')
        history = LazyHistoryList(store, pin, inc, checked_types=True, recursive=True)
        output[inc] = tuple(history)
    return output


def _rewrite(value, selected, memo):
    if reference(value) and value.incarnation in selected:
        if value.kind != 'list':
            raise StoreIntegrityError('promotion reference contradicts selected backing kind')
        return HistoryReference('sequence', value.incarnation)
    ident = id(value)
    if ident in memo:
        return memo[ident]
    if type(value) is tuple:
        result = tuple(_rewrite(v, selected, memo) for v in value)
    elif isinstance(value, dict):
        result = type(value)()
        memo[ident] = result
        for key, child in value.items():
            dict.__setitem__(result, _rewrite(key, selected, memo), _rewrite(child, selected, memo))
    elif isinstance(value, list):
        result = type(value)()
        memo[ident] = result
        list.extend(result, (_rewrite(v, selected, memo) for v in value))
    elif type(value) in (set, frozenset):
        result = type(value)(_rewrite(v, selected, memo) for v in value)
    elif is_dataclass(value) and type(value) in RECORD_FIELDS:
        result = object.__new__(type(value))
        memo[ident] = result
        for field in RECORD_FIELDS[type(value)]:
            object.__setattr__(result, field, _rewrite(getattr(value, field), selected, memo))
        if type(value) is Event and '_sealed' in vars(value):
            object.__setattr__(result, '_sealed', vars(value)['_sealed'])
    else:
        return value
    memo[ident] = result
    return result


def transform_copy(target, pin, captured, versions, ordinary, placements, dependencies, orders, states, *, workspace=None):
    """Build only in an unpublished mutable-empty destination; never source I/O."""
    selected, memo = set(captured), {}
    added = []
    for inc, values in captured.items():
        builder = LazyOrderedSequence(target, pin, inc,
            initial_values=(_rewrite(v, selected, memo) for v in values),
            value_mode='native', checked_types=True, recursive=True)
        added.extend(builder.pending_changes())
    def removed(change):
        return ((change.namespace in (DESCRIPTOR_NAMESPACE, TYPES) and change.key in selected)
                or (change.namespace == PAGE_NAMESPACE and change.key[0] in selected))
    def rewrite(change):
        return replace(change, value=_rewrite(change.value, selected, memo),
            memberships=tuple(replace(m, value=_rewrite(m.value, selected, memo)) for m in change.memberships))
    versions = [rewrite(v) for v in versions if not removed(v)] + added
    ordinary = tuple(rewrite(v) for v in ordinary)
    placements = [p for p in placements if not (p.owner_namespace == PAGE_NAMESPACE and p.owner_key[0] in selected)]
    for change in added:
        if change.namespace == NODE_NAMESPACE and change.value[0] == 'leaf':
            for path, child in AUXILIARY_OWNER_FAMILIES[NODE_NAMESPACE].reference_placements(change.value):
                placements.append(IdentityOccurrenceChange(NODE_NAMESPACE, change.key, path, child))
    dependencies = tuple(replace(v, value=dependency_value('sequence')) if v.key in selected else v for v in dependencies)
    return reconcile_copy(target.codec, versions, ordinary, tuple(placements), dependencies, orders, states, workspace=workspace)


def reconcile_copy(codec, versions, ordinary, placements, dependencies, orders, states, *, workspace=None):
    """Reconcile explicit copied authority, using captured order high water."""
    if workspace is not None:
        return _reconcile_disk(workspace, versions, ordinary, placements, dependencies, orders, states)
    # Rebuild catalog input from actual resulting physical authority.
    owners = [v for v in versions if not v.delete and v.namespace in IDENTITY_OWNER_FAMILIES
              and not (v.namespace == NODE_NAMESPACE and v.value[0] == 'branch')]
    eager = tuple(v for v in ordinary if v.namespace in IDENTITY_OWNER_FAMILIES)
    # Retain surviving order positions; new rows start at the source high water.
    final = {(v.namespace, codec.encode(v.key)) for v in versions if not v.delete}
    source_orders = {(ns, key): ordinal for ns, key, ordinal in orders}
    counts = Counter(ns for ns, _key in final)
    highs = {ns: high for ns, _count, high in states}
    rewritten_orders = [(ns, key, ordinal) for (ns, key), ordinal in source_orders.items() if (ns, key) in final]
    for ns, key in sorted(final - source_orders.keys()):
        ordinal = highs.get(ns, 0)
        rewritten_orders.append((ns, key, ordinal))
        highs[ns] = ordinal + 1
    namespaces = set(highs) | set(counts)
    rewritten_states = [(ns, counts.get(ns, 0), highs.get(ns, 0)) for ns in sorted(namespaces)]
    declared = {v.namespace for v in versions}
    versions.extend(VersionChange(ns, ('empty-copy-promotion/v1',), delete=True)
        for ns in namespaces - declared)
    return versions, ordinary, tuple(placements), dependencies, rewritten_orders, rewritten_states, owners, eager


def _reconcile_disk(workspace, versions, ordinary, placements, dependencies, orders, states):
    """Completed normalized rows only: no replay enters source object identity."""
    codec, db = workspace.codec, workspace.db
    # A checked replay sequence captures this metadata once; SQL indexes provide
    # joins/sorting without a second Python dictionary of every source key.
    live = workspace.stage((v.namespace, codec.encode(v.key)) for v in versions if not v.delete)
    source_orders = workspace.stage(orders)
    db.execute('DROP TABLE IF EXISTS conversion_order_reconcile')
    db.execute('CREATE TABLE conversion_order_reconcile(namespace TEXT,typed_key BLOB,live INTEGER,source_ordinal INTEGER,source_position INTEGER,PRIMARY KEY(namespace,typed_key)) WITHOUT ROWID')
    expected_live = expected_index_count = expected_index_root = 0
    def row_hash(row):
        return int(_framed_sha(b'conversion-order-index/v1', codec.encode(row)), 16)
    for namespace, key in live:
        changed = db.execute('INSERT OR IGNORE INTO conversion_order_reconcile VALUES (?,?,1,NULL,NULL)', (namespace,key)).rowcount
        expected_live += changed
        if changed:
            expected_index_count += 1
            expected_index_root ^= row_hash((namespace,key,1,None,None))
    for position, (namespace, key, ordinal) in enumerate(source_orders):
        previous = db.execute('SELECT namespace,typed_key,live,source_ordinal,source_position '
            'FROM conversion_order_reconcile WHERE namespace=? AND typed_key=?',(namespace,key)).fetchone()
        if previous is None:
            expected_index_count += 1
            current = (namespace,key,0,ordinal,position)
        else:
            expected_index_root ^= row_hash(previous)
            current = (namespace,key,previous[2],ordinal,position if previous[4] is None else previous[4])
        expected_index_root ^= row_hash(current)
        db.execute('INSERT INTO conversion_order_reconcile VALUES (?,?,0,?,?) '
            'ON CONFLICT(namespace,typed_key) DO UPDATE SET source_ordinal=excluded.source_ordinal, '
            'source_position=coalesce(conversion_order_reconcile.source_position,excluded.source_position)',
            (namespace,key,ordinal,position))
    def validate_index():
        # Seal all join/sort metadata while consuming checked input. Positions
        # determine both survivor order and old/new classification; checking
        # only ordinals would silently accept an existing key as a new one.
        count = root = 0
        for row in db.execute('SELECT namespace,typed_key,live,source_ordinal,source_position FROM conversion_order_reconcile'):
            count += 1
            root ^= row_hash(row)
        if (count,root) != (expected_index_count,expected_index_root):
            raise StoreIntegrityError('reconciled order index count/root mismatch')
    validate_index()
    counts = dict(db.execute('SELECT namespace,count(*) FROM conversion_order_reconcile WHERE live=1 GROUP BY namespace'))
    highs = {ns: high for ns, _count, high in states}
    def rewritten_orders():
        yield from db.execute('SELECT namespace,typed_key,source_ordinal FROM conversion_order_reconcile '
            'WHERE live=1 AND source_position IS NOT NULL ORDER BY source_position')
        for ns,key in db.execute('SELECT namespace,typed_key FROM conversion_order_reconcile '
                'WHERE live=1 AND source_position IS NULL ORDER BY namespace,typed_key'):
            ordinal=highs.get(ns,0)
            yield ns,key,ordinal
            highs[ns]=ordinal+1
    rewritten = workspace.stage(rewritten_orders())
    # Authenticate against the sealed inventories, rather than trusting an
    # unsealed scratch index. The same index is only working join/sort data.
    validate_index()
    expected_count=sum(counts.values())
    if len(rewritten)!=expected_live or expected_count!=expected_live:
        raise StoreIntegrityError('reconciled order inventory count mismatch')
    namespaces=set(highs)|set(counts)
    rewritten_states=tuple((ns,counts.get(ns,0),highs.get(ns,0)) for ns in sorted(namespaces))
    declared={v.namespace for v in versions}
    final_versions=workspace.stage_versions(chain(versions,(VersionChange(ns,('empty-copy-promotion/v1',),delete=True)
        for ns in namespaces-declared)))
    final_ordinary=workspace.stage_ordinary(ordinary)
    final_placements=workspace.stage_identity(placements)
    final_dependencies=workspace.stage_versions(dependencies)
    owners=(v for v in final_versions if not v.delete and v.namespace in IDENTITY_OWNER_FAMILIES
            and not(v.namespace==NODE_NAMESPACE and v.value[0]=='branch'))
    eager=(v for v in final_ordinary if v.namespace in IDENTITY_OWNER_FAMILIES)
    return final_versions,final_ordinary,final_placements,final_dependencies,rewritten,rewritten_states,owners,eager
