"""Opt-in, full World snapshots. No annual hooks or incremental-save claims.

Records are keyed by canonical collection path and original typed entity key.
Nested record values remain with their owner; metadata preserves collection kind,
entry order and empty roots. This is deliberately separate from checkpoint.py.
"""
from dataclasses import fields, is_dataclass
from pathlib import Path
import os
import pickle
import tempfile
import zlib

from .core import World, Event, Layer
from .event_log import EventLog, FrozenDict, FrozenList
from .record_index import RecordTable, IndexedRecord
from .incremental_store import (
    TypedCodec, CodecError, RecordChange, TransactionalStore,
    StoreFormatError, StoreIntegrityError,
)
from .persistence_schema import RECORD_FIELDS, ROOT_TYPES, ROOT_FIELDS
from . import advancement, social, communities, magic_resources, materials

SCHEMA = 'ate-world-p2a/1'
RECORD_SCHEMA = 1
META = 'world_snapshot'
IDENTITY_DELTAS = 'world_identity_deltas'
IDENTITY_DELTA_SCHEMA = 1
COLLECTION_LAYOUT = 'collections/v1'
# Explicitly reviewed rebuildable state. Unknown non-fields fail closed.
CACHES = {
    World: {'_living_cache'},
    social.SocialGraph: {'_relationships', '_partnership_index', '_partnership_count'},
    communities.CommunityState: {'_membership_index'},
    magic_resources.MagicResourceState: {'_query_inventory', '_query_selection', '_query_offer_books'},
    materials.MaterialEconomy: {'_selection_index', '_rank_heaps', '_selection_ids', '_whole_units'},
    advancement.AdvancementState: {'_rank_cache'},
}


def validate_schema():
    for cls, names in RECORD_FIELDS.items():
        if tuple(f.name for f in fields(cls)) != names:
            raise CodecError(f'unclassified fields in {cls.__name__}')
    for path, cls in ROOT_TYPES.items():
        if tuple(ROOT_FIELDS[path]) != RECORD_FIELDS[cls]:
            raise CodecError(f'incomplete root field coverage: {path}')


def _check_record(value):
    cls = type(value)
    if cls not in RECORD_FIELDS:
        raise CodecError(f'unregistered record type: {cls!r}')
    names = RECORD_FIELDS[cls]
    if tuple(f.name for f in fields(cls)) != names:
        raise CodecError(f'unclassified fields in {cls.__name__}')
    allowed = set(names) | CACHES.get(cls, set())
    if isinstance(value, IndexedRecord):
        allowed |= {'_index_table', '_index_key'}
    if cls is Event:
        allowed.add('_sealed')
    extra = set(vars(value)) - allowed
    if extra:
        raise CodecError(f'unclassified non-field state in {cls.__name__}: {sorted(extra)}')
    if any(name not in vars(value) for name in names):
        raise CodecError(f'missing stored fields in {cls.__name__}')


class WorldCodec(TypedCodec):
    """P1 codec with explicit frozen event types and closed ATE record schema."""
    def __init__(self, *, identity_links_recorded=False):
        super().__init__()
        self.identity_links_recorded = identity_links_recorded
        validate_schema()
        self.register_enum('core.Layer/v1', Layer)
        for cls in RECORD_FIELDS:
            # Relative names work for ate_sim and simulation.ate_sim imports;
            # stored names never cause dynamic imports.
            module = cls.__module__.split('.')[-1]
            self.register_record(f'{module}.{cls.__name__}/v1', cls)

    def _encode_value(self, value, active, seen_mutable):
        cls = type(value)
        # Only a full snapshot with an explicit identity manifest may encode
        # repeated values. P1 and standalone WorldCodec remain strict. Cycles
        # are still rejected through the shared active recursion set.
        if self.identity_links_recorded:
            seen_mutable = set()
        if is_dataclass(value):
            _check_record(value)
            if cls.__dataclass_params__.frozen:
                # Frozen value records (Ref) may repeat without mutable identity.
                seen_mutable = seen_mutable - {id(value)}
        if cls is Event:
            present = '_sealed' in vars(value)
            sealed = vars(value).get('_sealed', False)
            if type(sealed) is not bool:
                raise CodecError('invalid event sealed flag')
            return ['ate_event/v1', present, sealed,
                    super()._encode_value(value, active, seen_mutable)]
        if cls in (FrozenDict, FrozenList):
            self._enter(value, active, seen_mutable, mutable=False)
            try:
                if cls is FrozenDict:
                    content = [[self._encode_value(k, active, seen_mutable),
                                self._encode_value(v, active, seen_mutable)] for k, v in value.items()]
                else:
                    content = [self._encode_value(v, active, seen_mutable) for v in value]
                return ['ate_frozen_dict/v1' if cls is FrozenDict else 'ate_frozen_list/v1', content]
            finally:
                active.remove(id(value))
        return super()._encode_value(value, active, seen_mutable)

    def _decode_value(self, node):
        if isinstance(node, list) and node:
            if node[0] == 'ate_event/v1':
                if len(node) != 4 or type(node[1]) is not bool or type(node[2]) is not bool:
                    raise CodecError('invalid event envelope')
                value = super()._decode_value(node[3])
                if type(value) is not Event or (not node[1] and node[2]):
                    raise CodecError('invalid event envelope')
                if node[1]:
                    object.__setattr__(value, '_sealed', node[2])
                return value
            if node[0] in ('ate_frozen_dict/v1', 'ate_frozen_list/v1'):
                if len(node) != 2 or type(node[1]) is not list:
                    raise CodecError('invalid frozen container')
                if node[0] == 'ate_frozen_list/v1':
                    return FrozenList(self._decode_value(x) for x in node[1])
                pairs = node[1]
                if any(type(p) is not list or len(p) != 2 for p in pairs):
                    raise CodecError('invalid frozen mapping')
                value = FrozenDict((self._decode_value(k), self._decode_value(v)) for k, v in pairs)
                if len(value) != len(pairs):
                    raise CodecError('duplicate frozen mapping key')
                return value
        return super()._decode_value(node)


def _events(log):
    """Read cold bytes without modifying the source log's query cache."""
    for chunk in log._chunks:
        events = pickle.loads(zlib.decompress(chunk))
        if len(events) != log.chunk_size:
            raise CodecError('invalid cold event segment length')
        yield from events
    yield from log._tail


def _audit(value, path, seen, active, links):
    """Inventory mutable identity links; reject cycles and unclassified state.

    Keep references during this traversal so IDs of decoded cold events cannot
    be reused. This temporary O(history) audit belongs to full bootstrap only.
    """
    cls = type(value)
    if value is None or cls in (bool, int, float, str, bytes) or cls is Layer:
        return
    if id(value) in active:
        raise CodecError(f'cycle at {path}')
    record = is_dataclass(value)
    mutable = cls in (dict, list, set, RecordTable, EventLog) or (record and not cls.__dataclass_params__.frozen)
    if mutable and id(value) in seen:
        links.append((path, seen[id(value)][0]))
        return
    if mutable:
        seen[id(value)] = (path, value)
    active.add(id(value))
    try:
        if record:
            _check_record(value)
            for name in RECORD_FIELDS[cls]:
                _audit(getattr(value, name), path + (('field', name),), seen, active, links)
        elif cls in (dict, FrozenDict, RecordTable):
            if cls is RecordTable and set(vars(value)) - {'_indexes'}:
                raise CodecError(f'unclassified RecordTable state: {path}')
            for k, v in value.items():
                _audit(k, path + (('map_key', k),), seen, active, links)
                _audit(v, path + (('key', k),), seen, active, links)
        elif cls in (list, tuple, set, frozenset, FrozenList, EventLog):
            if cls is EventLog:
                if set(vars(value)) != {'_chunks', '_tail', '_count', '_years', '_offsets', '_cache'}:
                    raise CodecError('unclassified EventLog state')
                items = _events(value)
            else:
                items = value
            years, offsets, count = [], [], 0
            for i, v in enumerate(items):
                if cls is EventLog:
                    if type(v) is not Event or v.id != i + 1 or (years and v.year < years[-1]):
                        raise CodecError('invalid EventLog identity/order')
                    if not years or v.year != years[-1]:
                        years.append(v.year)
                        offsets.append(i)
                    if i < len(value._chunks) * value.chunk_size and not vars(v).get('_sealed', False):
                        raise CodecError('unsealed cold event')
                    count += 1
                _audit(v, path + (('index', i),), seen, active, links)
            if cls is EventLog and (count != value._count or years != value._years or offsets != value._offsets):
                raise CodecError('EventLog index disagrees with logical events')
        else:
            raise CodecError(f'unsupported type {cls!r} at {path}')
    finally:
        active.remove(id(value))


def _roots(world):
    for path, cls in ROOT_TYPES.items():
        value = world if path == 'world' else getattr(world, path.split('.')[1])
        if type(value) is not cls:
            raise CodecError(f'wrong state type at {path}')
        yield path, value


def _kind(value, expected):
    cls = type(value)
    choices = {'dict': (dict, RecordTable), 'list': (list,), 'set': (set,),
               'int': (int,), 'events': (list, EventLog)}
    if cls not in choices[expected]:
        raise CodecError(f'expected {expected}, found {cls.__name__}')
    return cls.__name__


def write_snapshot(world, path, *, rules_id):
    """Atomically publish a new full World snapshot. Never overwrite a save.

    Returns P1 payload counters. Bootstrap encodes every retained record; later
    incremental mutation tracking is deliberately not provided here.
    """
    validate_schema()
    if type(world) is not World:
        raise CodecError('expected World from this package registry')
    # Mid-step snapshots are unsupported: current/rank scopes belong to a step.
    if world.__dict__.get('_index_current_people') or world.advancement.__dict__.get('_rank_cache') is not None:
        raise CodecError('snapshot requires a completed simulation step')
    links = []
    _audit(world, (), {}, set(), links)
    codec = WorldCodec(identity_links_recorded=bool(links))
    descriptions = {}
    changes = []
    for root, value in _roots(world):
        for name, expected in ROOT_FIELDS[root].items():
            if expected == 'state':
                continue
            item = getattr(value, name)
            namespace = root + '.' + name
            kind = _kind(item, expected)
            if kind in ('dict', 'RecordTable'):
                entries = item.items()
            elif kind == 'set':
                entries = enumerate(sorted(item, key=codec.encode))
            elif kind == 'EventLog':
                entries = enumerate(_events(item))
            elif kind == 'list':
                entries = enumerate(item)
            else:
                entries = [(0, item)]
            size = 0
            for ordinal, (key, entry) in enumerate(entries):
                changes.append(RecordChange(namespace, key, (ordinal, entry)))
                size += 1
            descriptions[namespace] = (kind, size, len(item._chunks) if kind == 'EventLog' else 0)
    manifest = {'schema': SCHEMA, 'collections': descriptions, 'identity_links': links}
    changes.append(RecordChange(META, 'manifest', manifest))
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a completely committed World; no generation-zero World at path.
    with tempfile.TemporaryDirectory(prefix='.ate-world-', dir=path.parent) as directory:
        temporary = Path(directory) / 'snapshot.sqlite'
        with TransactionalStore.create(temporary, simulation_schema=SCHEMA, rules_id=rules_id, codec=codec) as store:
            store.commit(0, changes, (), {
                'simulation_position': world.year, 'seed': world.seed,
                'next_ids': {k: getattr(world, k) for k in ('next_person', 'next_household', 'next_settlement', 'next_event')},
                'namespaces': tuple(descriptions) + (META,),
            })
            diagnostics = store.diagnostics()
        os.link(temporary, path)  # atomic no-overwrite publication on the same filesystem
        TransactionalStore._fsync_dir(path.parent)
    return diagnostics


def _restore_collection(store, namespace, expected, description):
    if type(description) is not tuple or len(description) != 3:
        raise StoreFormatError(f'invalid collection description: {namespace}')
    kind, size, chunks = description
    allowed = {'dict': ('dict', 'RecordTable', 'dict-stable/v1', 'RecordTable-stable/v1'),
               'list': ('list',), 'set': ('set', 'set-stable/v1'),
               'events': ('list', 'EventLog'), 'int': ('int',)}[expected]
    if kind not in allowed or type(size) is not int or size < 0 or type(chunks) is not int or chunks < 0:
        raise StoreFormatError(f'invalid collection kind/count: {namespace}')
    if kind != 'EventLog' and chunks != 0:
        raise StoreFormatError('unexpected event segments')
    rows = store.read_records(namespace, expected_record_schema=RECORD_SCHEMA)
    if len(rows) != size:
        raise StoreIntegrityError(f'missing/extra collection rows: {namespace}')
    stable = kind in ('dict-stable/v1', 'RecordTable-stable/v1', 'set-stable/v1')
    base_kind = {'dict-stable/v1': 'dict', 'RecordTable-stable/v1': 'RecordTable',
                 'set-stable/v1': 'set'}.get(kind, kind)
    ordered = {}
    for key, envelope, _ in rows:
        if type(envelope) is not tuple or len(envelope) != 2:
            raise StoreFormatError('invalid entry envelope')
        ordinal, value = envelope
        if type(ordinal) is not int or ordinal < 0 or ordinal in ordered or (not stable and ordinal >= size):
            raise StoreIntegrityError(f'duplicate/missing ordinal: {namespace}')
        if base_kind not in ('dict', 'RecordTable') and (type(key) is not int or key != ordinal):
            raise StoreIntegrityError('sequence key disagrees with ordinal')
        ordered[ordinal] = (key, value)
    if stable:
        if len(ordered) != size:
            raise StoreIntegrityError(f'missing/extra stable ordinals: {namespace}')
        pairs = [ordered[i] for i in sorted(ordered)]
    else:
        pairs = [ordered[i] for i in range(size)]
    if base_kind in ('dict', 'RecordTable'):
        result = dict(pairs)
        if len(result) != size:
            raise StoreIntegrityError('duplicate decoded dictionary key')
        if base_kind == 'RecordTable':
            if any(not isinstance(v, IndexedRecord) for v in result.values()):
                raise StoreFormatError('RecordTable requires indexed records')
            result = RecordTable(result)
        return result
    values = [v for _, v in pairs]
    if base_kind == 'int':
        if size != 1 or type(values[0]) is not int:
            raise StoreFormatError('missing/invalid scalar')
        return values[0]
    if base_kind == 'set':
        result = set(values)
        if len(result) != size:
            raise StoreIntegrityError('duplicate set member')
        return result
    if base_kind == 'list':
        return values
    if chunks * EventLog.chunk_size > size:
        raise StoreIntegrityError('invalid sealed event prefix')
    log = EventLog(values)  # validates IDs/year order; does not reseal the tail
    for i in range(chunks):
        chunk = values[i * log.chunk_size:(i + 1) * log.chunk_size]
        if any(type(e) is not Event or not e.__dict__.get('_sealed', False) for e in chunk):
            raise StoreIntegrityError('unsealed event in cold prefix')
        log._chunks.append(zlib.compress(pickle.dumps(chunk, protocol=5), level=1))
    log._tail = values[chunks * log.chunk_size:]
    return log


def _identity_groups(links):
    """Canonical alias groups; link list order is not part of World identity."""
    if type(links) is not list:
        raise StoreFormatError('invalid identity links')
    groups = []
    by_path = {}
    for target, owner in links:
        group = by_path.get(owner)
        if group is None:
            group = {owner};groups.append(group);by_path[owner] = group
        other = by_path.get(target)
        if other is not None and other is not group:
            group.update(other)
            for path in other:by_path[path] = group
            groups.remove(other)
        group.add(target);by_path[target] = group
    codec = WorldCodec(identity_links_recorded=True)
    return sorted(
        (tuple(sorted((codec.encode(path) for path in group))) for group in groups),
        key=repr,
    )


def _fold_identity_deltas(base_links, rows, codec):
    """Apply append-only identity link deltas without rewriting the base manifest."""
    state = {codec.encode(link): link for link in base_links}
    # P1 enumeration has no authoritative order. Typed integer keys sort
    # lexically in SQLite (0, 1, 10, 2, ...), not by delta sequence number.
    if any(type(key) is not int or key < 0 for key, _patch, _schema in rows):
        raise StoreIntegrityError('invalid identity delta sequence key')
    expected = 0
    for key, patch, _schema in sorted(rows, key=lambda row: row[0]):
        if type(key) is not int or key != expected:
            raise StoreIntegrityError('identity delta sequence is not contiguous')
        expected += 1
        if type(patch) is not tuple or len(patch) != 3 or patch[0] != 'identity-delta/v1':
            raise StoreFormatError('invalid identity delta record')
        removes, adds = patch[1], patch[2]
        if type(removes) is not tuple or type(adds) is not tuple:
            raise StoreFormatError('invalid identity delta links')
        for link in removes:
            state.pop(codec.encode(link), None)
        for link in adds:
            state[codec.encode(link)] = link
    return list(state.values())


def _complete_identity_groups(value, path=(), groups=None, active=None):
    """Expand every acyclic mutable occurrence, including below shared parents."""
    if groups is None:
        groups = {}
    if active is None:
        active = set()
    cls = type(value)
    if value is None or cls in (bool, int, float, str, bytes) or cls is Layer:
        return groups
    ident = id(value)
    if ident in active:
        raise StoreIntegrityError('cycle in restored identity graph')
    record = is_dataclass(value)
    mutable = cls in (dict, list, set, RecordTable, EventLog) or (
        record and not cls.__dataclass_params__.frozen
    )
    if mutable:
        groups.setdefault(ident, []).append(path)
    active.add(ident)
    try:
        if record:
            for name in RECORD_FIELDS[cls]:
                _complete_identity_groups(
                    getattr(value, name), path + (('field', name),), groups, active
                )
        elif cls in (dict, RecordTable, FrozenDict):
            for key, child in value.items():
                _complete_identity_groups(
                    child, path + (('key', key),), groups, active
                )
        elif cls in (list, tuple, FrozenList, EventLog):
            for i, child in enumerate(value):
                _complete_identity_groups(
                    child, path + (('index', i),), groups, active
                )
        elif cls in (set, frozenset):
            return groups
    finally:
        active.remove(ident)
    return groups


def _verify_identity_graph(world, links):
    """Verify every restored alias is explained by an explicit or ancestor link."""
    explicit = {}
    for target, owner in links:
        if target in explicit and explicit[target] != owner:
            raise StoreIntegrityError('conflicting identity targets')
        explicit[target] = owner
        if _at_path(world, target) is not _at_path(world, owner):
            raise StoreIntegrityError('identity link was not restored')

    for paths in _complete_identity_groups(world).values():
        if len(paths) < 2:
            continue
        path_set = set(paths)
        parent = {path: path for path in paths}

        def find(path):
            while parent[path] != path:
                parent[path] = parent[parent[path]]
                path = parent[path]
            return path

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[b] = a

        for path in paths:
            for n in range(1, len(path) + 1):
                prefix = path[:n]
                owner_prefix = explicit.get(prefix)
                if owner_prefix is None:
                    continue
                other = owner_prefix + path[n:]
                if other in path_set:
                    union(path, other)
        if len({find(path) for path in paths}) != 1:
            raise StoreIntegrityError('restored alias group is not explained by identity links')


def _read_manifest(store):
    """Read fixed bootstrap identity and the optional bounded live layout.

    P2A snapshots contain only manifest. Incremental structural saves update
    collections/v1 independently so historical base links are never rewritten.
    Both records are read inside the caller's pinned transaction.
    """
    metadata = {key: value for key, value, _ in
                store.read_records(META, expected_record_schema=RECORD_SCHEMA)}
    if set(metadata) not in ({'manifest'}, {'manifest', COLLECTION_LAYOUT}):
        raise StoreFormatError('unexpected snapshot metadata')
    manifest = metadata['manifest']
    if type(manifest) is not dict or set(manifest) != {'schema', 'collections', 'identity_links'} or manifest['schema'] != SCHEMA:
        raise StoreFormatError('unsupported World adapter schema')
    expected_paths = {root + '.' + name for root, names in ROOT_FIELDS.items()
                      for name, kind in names.items() if kind != 'state'}
    if type(manifest['collections']) is not dict or set(manifest['collections']) != expected_paths:
        raise StoreFormatError('missing/unknown canonical collection roots')
    if COLLECTION_LAYOUT in metadata:
        layout = metadata[COLLECTION_LAYOUT]
        if type(layout) is not dict or set(layout) != expected_paths:
            raise StoreFormatError('missing/unknown canonical collection roots')
        manifest = dict(manifest, collections=layout)
    return manifest


def read_snapshot(path, *, rules_id):
    """Restore a detached World from one pinned generation, with a full scrub."""
    codec = WorldCodec()
    with TransactionalStore.open(path, codec=codec, expected_simulation_schema=SCHEMA,
                                 expected_rules_id=rules_id) as store:
        with store.read_transaction():
            counts = store.verify_all()
            if counts['segments']:
                raise StoreFormatError('P2A does not use store segments')
            manifest = _read_manifest(store)
            descriptions = manifest['collections']
            expected_paths = {root + '.' + name for root, names in ROOT_FIELDS.items()
                              for name, kind in names.items() if kind != 'state'}
            if type(descriptions) is not dict or set(descriptions) != expected_paths:
                raise StoreFormatError('missing/unknown canonical collection roots')
            head = store.head_metadata()
            namespaces = set(head['namespaces'])
            allowed_namespaces = expected_paths | {META}
            if namespaces not in (allowed_namespaces, allowed_namespaces | {IDENTITY_DELTAS}):
                raise StoreFormatError('wrong namespace inventory')
            objects = {root: object.__new__(cls) for root, cls in ROOT_TYPES.items()}
            for root, obj in objects.items():
                for name, kind in ROOT_FIELDS[root].items():
                    namespace = root + '.' + name
                    value = objects[namespace] if kind == 'state' else _restore_collection(store, namespace, kind, descriptions[namespace])
                    object.__setattr__(obj, name, value)
            identity_delta_rows = (
                store.read_records(IDENTITY_DELTAS, expected_record_schema=IDENTITY_DELTA_SCHEMA)
                if IDENTITY_DELTAS in namespaces else []
            )
            effective_links = _fold_identity_deltas(
                manifest['identity_links'], identity_delta_rows,
                WorldCodec(identity_links_recorded=True),
            )
            world = objects['world']
            if world.seed != head['seed'] or world.year != head['simulation_position'] or head['next_ids'] != {
                k: getattr(world, k) for k in ('next_person', 'next_household', 'next_settlement', 'next_event')
            }:
                raise StoreIntegrityError('World disagrees with committed head')
    _restore_identity(world, effective_links)
    if identity_delta_rows:
        _verify_identity_graph(world, effective_links)
    else:
        actual_links = []
        _audit(world, (), {}, set(), actual_links)
        if _identity_groups(actual_links) != _identity_groups(manifest['identity_links']):
            raise StoreIntegrityError('identity manifest does not match restored graph')
    return world


def _at_path(world, path):
    if type(path) is not tuple:
        raise StoreFormatError('identity paths require tuples')
    value = world
    for component in path:
        if type(component) is not tuple or len(component) != 2:
            raise StoreFormatError('invalid identity path component')
        kind, key = component
        if kind == 'field' and type(value) in RECORD_FIELDS and key in RECORD_FIELDS[type(value)]:
            value = getattr(value, key)
        elif kind == 'key' and type(value) in (dict, RecordTable, FrozenDict) and key in value:
            value = value[key]
        elif kind == 'index' and type(value) in (list, tuple, FrozenList, EventLog) and type(key) is int and 0 <= key < len(value):
            value = value[key]
        else:
            raise StoreFormatError('identity path does not address canonical state')
    return value


def _restore_identity(world, links):
    if type(links) is not list:
        raise StoreFormatError('invalid identity links')
    comparisons = WorldCodec(identity_links_recorded=True)
    assignments = []
    targets = set()
    for link in links:
        if type(link) is not tuple or len(link) != 2:
            raise StoreFormatError('invalid identity link')
        target, owner = link
        if not target or target == owner or target in targets:
            raise StoreIntegrityError('duplicate/invalid identity target')
        targets.add(target)
        old, original = _at_path(world, target), _at_path(world, owner)
        if type(old) is not type(original) or comparisons.encode(old) != comparisons.encode(original):
            raise StoreIntegrityError('aliased payload copies disagree')
        assignments.append((target, owner))
    # Compare every payload copy before relinking. Then restore ancestors before
    # descendants and re-resolve each owner path after ancestor assignments.
    assignments.sort(key=lambda pair: (max(len(pair[0]), len(pair[1])), comparisons.encode(pair)))
    for target, owner in assignments:
        original = _at_path(world, owner)
        parent = _at_path(world, target[:-1])
        kind, key = target[-1]
        if kind == 'field' and type(parent) in RECORD_FIELDS and not type(parent).__dataclass_params__.frozen:
            object.__setattr__(parent, key, original)
        elif kind == 'key' and type(parent) in (dict, RecordTable):
            parent[key] = original
        elif kind == 'index' and type(parent) is list:
            parent[key] = original
        else:
            raise StoreFormatError('unsupported mutable identity boundary')
