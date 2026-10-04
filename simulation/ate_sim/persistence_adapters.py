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
from .persistence_identity import iter_mutable_event_items
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
IDENTITY_LINKS = 'world_identity_links'
IDENTITY_LINK_SCHEMA = 1
IDENTITY_STORAGE_CURRENT = 'current-links/v1'
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
                expected_state = {
                    '_disk_prefix', '_disk_count', '_chunks', '_tail', '_count',
                    '_years', '_offsets', '_cache', '_last_year',
                }
                if set(vars(value)) != expected_state:
                    raise CodecError('unclassified EventLog state')
                # The existing P2 adapter remains an in-memory format. P3B disk
                # EventLogs require the later cold-session APIs and must not be
                # silently materialized through this legacy snapshot path.
                if value._disk_prefix is not None or value._disk_count != 0:
                    raise CodecError(
                        'disk-backed EventLog requires cold-session persistence'
                    )
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
            if cls is EventLog:
                last_year = years[-1] if years else None
                if (
                    count != value._count
                    or years != value._years
                    or offsets != value._offsets
                    or value._last_year != last_year
                ):
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


def _write_snapshot(world, path, *, rules_id, legacy_identity=False):
    """Atomically publish a full World snapshot without overwriting destination."""
    validate_schema()
    if type(world) is not World:
        raise CodecError('expected World from this package registry')
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
            descriptions[namespace] = (
                kind, size, len(item._chunks) if kind == 'EventLog' else 0
            )
    if legacy_identity:
        manifest = {
            'schema': SCHEMA,
            'collections': descriptions,
            'identity_links': links,
        }
        namespaces = tuple(descriptions) + (META,)
    else:
        manifest = {
            'schema': SCHEMA,
            'collections': descriptions,
            'identity_storage': IDENTITY_STORAGE_CURRENT,
        }
        for target, owner in links:
            changes.append(RecordChange(
                IDENTITY_LINKS, target, owner,
                record_schema=IDENTITY_LINK_SCHEMA,
            ))
        # The current-link namespace is an explicit authority even when empty.
        namespaces = tuple(descriptions) + (META, IDENTITY_LINKS)
    changes.append(RecordChange(META, 'manifest', manifest))
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ate-world-', dir=path.parent) as directory:
        temporary = Path(directory) / 'snapshot.sqlite'
        with TransactionalStore.create(
            temporary,
            simulation_schema=SCHEMA,
            rules_id=rules_id,
            codec=codec,
        ) as store:
            store.commit(0, changes, (), {
                'simulation_position': world.year,
                'seed': world.seed,
                'next_ids': {
                    k: getattr(world, k)
                    for k in ('next_person', 'next_household', 'next_settlement', 'next_event')
                },
                'namespaces': namespaces,
            })
            diagnostics = store.diagnostics()
        os.link(temporary, path)
        TransactionalStore._fsync_dir(path.parent)
    return diagnostics


def write_snapshot(world, path, *, rules_id):
    """Write the P2C current-link snapshot format (the opt-in snapshot default)."""
    return _write_snapshot(world, path, rules_id=rules_id, legacy_identity=False)


def _write_legacy_snapshot(world, path, *, rules_id):
    """Test/compatibility helper producing the genuine pre-P2C manifest shape."""
    return _write_snapshot(world, path, rules_id=rules_id, legacy_identity=True)


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


def _complete_identity_groups(
    value, path=(), groups=None, active=None, *, mutable_event_tail_only=False
):
    """Expand mutable occurrences in the selected identity projection."""
    if groups is None:
        groups = {}
    if active is None:
        active = set()
    cls = type(value)
    if value is None or cls in (bool, int, float, str, bytes) or cls is Layer:
        return groups
    if mutable_event_tail_only and cls in (FrozenDict, FrozenList):
        return groups
    if isinstance(value, EventLog):
        value._ensure_backend_readable()
        if value._disk_prefix is not None and not mutable_event_tail_only:
            raise StoreFormatError(
                'disk-backed EventLog identity traversal requires '
                'mutable_event_tail_only=True'
            )
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
                    getattr(value, name),
                    path + (('field', name),),
                    groups,
                    active,
                    mutable_event_tail_only=mutable_event_tail_only,
                )
        elif cls in (dict, RecordTable, FrozenDict):
            for key, child in value.items():
                _complete_identity_groups(
                    child,
                    path + (('key', key),),
                    groups,
                    active,
                    mutable_event_tail_only=mutable_event_tail_only,
                )
        elif cls is EventLog:
            items = (
                iter_mutable_event_items(value)
                if mutable_event_tail_only else enumerate(value)
            )
            for index, child in items:
                _complete_identity_groups(
                    child,
                    path + (('index', index),),
                    groups,
                    active,
                    mutable_event_tail_only=mutable_event_tail_only,
                )
        elif cls in (list, tuple, FrozenList):
            for index, child in enumerate(value):
                _complete_identity_groups(
                    child,
                    path + (('index', index),),
                    groups,
                    active,
                    mutable_event_tail_only=mutable_event_tail_only,
                )
        elif cls in (set, frozenset):
            return groups
    finally:
        active.remove(ident)
    return groups


def _verify_identity_graph(world, links, *, mutable_event_tail_only=False):
    """Verify every projected alias is explained by an explicit/ancestor link."""
    if type(links) is not list:
        raise StoreFormatError('invalid identity links')
    explicit = {}
    for link in links:
        if type(link) is not tuple or len(link) != 2:
            raise StoreFormatError('invalid identity link')
        target, owner = link
        if target in explicit and explicit[target] != owner:
            raise StoreIntegrityError('conflicting identity targets')
        explicit[target] = owner
        if _at_path(
            world, target,
            mutable_event_tail_only=mutable_event_tail_only,
        ) is not _at_path(
            world, owner,
            mutable_event_tail_only=mutable_event_tail_only,
        ):
            raise StoreIntegrityError('identity link was not restored')

    groups = _complete_identity_groups(
        world, mutable_event_tail_only=mutable_event_tail_only
    )
    for paths in groups.values():
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
            raise StoreIntegrityError(
                'restored alias group is not explained by identity links'
            )


def _identity_mode(manifest):
    if type(manifest) is not dict or manifest.get('schema') != SCHEMA:
        raise StoreFormatError('unsupported World adapter schema')
    keys = set(manifest)
    if keys == {'schema', 'collections', 'identity_links'}:
        if type(manifest['identity_links']) is not list:
            raise StoreFormatError('invalid legacy identity links')
        return 'legacy'
    if keys == {'schema', 'collections', 'identity_storage'}:
        if manifest['identity_storage'] != IDENTITY_STORAGE_CURRENT:
            raise StoreFormatError('unknown identity storage mode')
        return 'current'
    raise StoreFormatError('mixed/unsupported identity manifest')


def _read_manifest(store):
    """Read fixed manifest plus optional live collection-layout overlay."""
    metadata = {
        key: value
        for key, value, _ in store.read_records(
            META, expected_record_schema=RECORD_SCHEMA
        )
    }
    if set(metadata) not in ({'manifest'}, {'manifest', COLLECTION_LAYOUT}):
        raise StoreFormatError('unexpected snapshot metadata')
    manifest = metadata['manifest']
    _identity_mode(manifest)
    expected_paths = {
        root + '.' + name
        for root, names in ROOT_FIELDS.items()
        for name, kind in names.items()
        if kind != 'state'
    }
    if type(manifest['collections']) is not dict or set(manifest['collections']) != expected_paths:
        raise StoreFormatError('missing/unknown canonical collection roots')
    if COLLECTION_LAYOUT in metadata:
        layout = metadata[COLLECTION_LAYOUT]
        if type(layout) is not dict or set(layout) != expected_paths:
            raise StoreFormatError('missing/unknown canonical collection roots')
        manifest = dict(manifest, collections=layout)
    return manifest


def _read_cold_manifest(store):
    """Read the exact P3B cold manifest plus accepted collections overlay."""
    metadata = {
        key: value
        for key, value, _ in store.read_records(
            META, expected_record_schema=RECORD_SCHEMA
        )
    }
    if set(metadata) not in ({'manifest'}, {'manifest', COLLECTION_LAYOUT}):
        raise StoreFormatError('unexpected snapshot metadata')
    manifest = metadata['manifest']
    if type(manifest) is not dict or manifest.get('schema') != SCHEMA:
        raise StoreFormatError('unsupported World adapter schema')
    keys = set(manifest)
    cold_keys = {
        'schema', 'collections', 'identity_storage', 'event_storage'
    }
    if keys != cold_keys:
        legacy_current = {
            'schema', 'collections', 'identity_storage'
        }
        legacy_links = {'schema', 'collections', 'identity_links'}
        if keys in (legacy_current, legacy_links):
            raise StoreFormatError(
                'cold capture requires conversion to sealed-prefix-tail/v1'
            )
        raise StoreFormatError('mixed/unsupported cold World manifest')
    if manifest['identity_storage'] != IDENTITY_STORAGE_CURRENT:
        raise StoreFormatError('unknown identity storage mode')
    if manifest['event_storage'] != 'sealed-prefix-tail/v1':
        raise StoreFormatError('unknown cold event storage mode')

    expected_paths = {
        root + '.' + name
        for root, names in ROOT_FIELDS.items()
        for name, kind in names.items()
        if kind != 'state'
    }
    collections = manifest['collections']
    if type(collections) is not dict or set(collections) != expected_paths:
        raise StoreFormatError('missing/unknown canonical collection roots')
    if COLLECTION_LAYOUT in metadata:
        layout = metadata[COLLECTION_LAYOUT]
        if type(layout) is not dict or set(layout) != expected_paths:
            raise StoreFormatError('missing/unknown canonical collection roots')
        manifest = dict(manifest, collections=layout)
    return manifest


def _validate_identity_link(target, owner):
    if type(target) is not tuple or type(owner) is not tuple:
        raise StoreFormatError('identity paths require tuples')
    if not target or target == owner:
        raise StoreIntegrityError('duplicate/invalid identity target')
    for path in (target, owner):
        for component in path:
            if type(component) is not tuple or len(component) != 2:
                raise StoreFormatError('invalid identity path component')
            kind, _key = component
            if kind not in ('field', 'key', 'index'):
                raise StoreFormatError('invalid identity path component')


def _read_current_identity_links(store):
    rows = store.read_records(
        IDENTITY_LINKS, expected_record_schema=IDENTITY_LINK_SCHEMA
    )
    links = []
    seen = set()
    for target, owner, _schema in rows:
        _validate_identity_link(target, owner)
        if target in seen:
            raise StoreIntegrityError('duplicate identity target')
        seen.add(target)
        links.append((target, owner))
    return links


def _read_identity_links(store, manifest, namespaces):
    mode = _identity_mode(manifest)
    expected_paths = {
        root + '.' + name
        for root, names in ROOT_FIELDS.items()
        for name, kind in names.items()
        if kind != 'state'
    }
    base = expected_paths | {META}
    if mode == 'current':
        if namespaces != base | {IDENTITY_LINKS}:
            raise StoreFormatError('wrong namespace inventory for current identity storage')
        return mode, _read_current_identity_links(store)
    if IDENTITY_LINKS in namespaces or namespaces not in (
        base, base | {IDENTITY_DELTAS}
    ):
        raise StoreFormatError('wrong namespace inventory for legacy identity storage')
    delta_rows = (
        store.read_records(
            IDENTITY_DELTAS, expected_record_schema=IDENTITY_DELTA_SCHEMA
        )
        if IDENTITY_DELTAS in namespaces else []
    )
    links = _fold_identity_deltas(
        manifest['identity_links'], delta_rows,
        WorldCodec(identity_links_recorded=True),
    )
    for target, owner in links:
        _validate_identity_link(target, owner)
    return mode, links


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
            identity_mode, effective_links = _read_identity_links(
                store, manifest, namespaces
            )
            objects = {root: object.__new__(cls) for root, cls in ROOT_TYPES.items()}
            for root, obj in objects.items():
                for name, kind in ROOT_FIELDS[root].items():
                    namespace = root + '.' + name
                    value = objects[namespace] if kind == 'state' else _restore_collection(store, namespace, kind, descriptions[namespace])
                    object.__setattr__(obj, name, value)
            world = objects['world']
            if world.seed != head['seed'] or world.year != head['simulation_position'] or head['next_ids'] != {
                k: getattr(world, k) for k in ('next_person', 'next_household', 'next_settlement', 'next_event')
            }:
                raise StoreIntegrityError('World disagrees with committed head')
    _restore_identity(world, effective_links)
    if identity_mode == 'current' or IDENTITY_DELTAS in namespaces:
        _verify_identity_graph(world, effective_links)
    else:
        actual_links = []
        _audit(world, (), {}, set(), actual_links)
        if _identity_groups(actual_links) != _identity_groups(manifest['identity_links']):
            raise StoreIntegrityError('identity manifest does not match restored graph')
    return world


def convert_legacy_snapshot(source, destination, *, rules_id):
    """Full-cost, explicit no-overwrite conversion from legacy P2A/P2B to P2C."""
    source = Path(source)
    destination = Path(destination)
    codec = WorldCodec()
    with TransactionalStore.open(
        source, codec=codec, expected_simulation_schema=SCHEMA,
        expected_rules_id=rules_id,
    ) as store:
        with store.read_transaction():
            manifest = _read_manifest(store)
            if _identity_mode(manifest) != 'legacy':
                raise StoreFormatError('conversion source is not a legacy snapshot')
            # Validate the full source before reading it through the World adapter.
            store.verify_all()
    world = read_snapshot(source, rules_id=rules_id)
    return write_snapshot(world, destination, rules_id=rules_id)


def _at_path(world, path, *, mutable_event_tail_only=False):
    if type(path) is not tuple:
        raise StoreFormatError('identity paths require tuples')
    value = world
    for component in path:
        if type(component) is not tuple or len(component) != 2:
            raise StoreFormatError('invalid identity path component')
        kind, key = component

        if isinstance(value, EventLog):
            value._ensure_backend_readable()
            if value._disk_prefix is not None and not mutable_event_tail_only:
                raise StoreFormatError(
                    'disk-backed EventLog identity traversal requires '
                    'mutable_event_tail_only=True'
                )
            if mutable_event_tail_only:
                if kind != 'index' or type(key) is not int or key < 0:
                    raise StoreFormatError(
                        'identity path does not address canonical mutable EventLog tail'
                    )
                first = (
                    value._disk_count
                    + len(value._chunks) * value.chunk_size
                )
                if key < first:
                    raise StoreFormatError(
                        'identity path addresses sealed EventLog history'
                    )
                offset = key - first
                if offset < 0 or offset >= len(value._tail):
                    raise StoreFormatError(
                        'identity path does not address canonical state'
                    )
                event = value._tail[offset]
                if event.__dict__.get('_sealed', False) is True:
                    raise StoreFormatError(
                        'identity path addresses sealed EventLog history'
                    )
                value = event
                continue

        if (
            kind == 'field'
            and type(value) in RECORD_FIELDS
            and key in RECORD_FIELDS[type(value)]
        ):
            value = getattr(value, key)
        elif (
            kind == 'key'
            and type(value) in (dict, RecordTable, FrozenDict)
            and key in value
        ):
            value = value[key]
        elif (
            kind == 'index'
            and type(value) in (list, tuple, FrozenList, EventLog)
            and type(key) is int
            and key >= 0
        ):
            if isinstance(value, EventLog):
                if value._disk_prefix is not None:
                    raise StoreFormatError(
                        'disk-backed EventLog identity traversal requires '
                        'mutable_event_tail_only=True'
                    )
                if key >= len(value):
                    raise StoreFormatError(
                        'identity path does not address canonical state'
                    )
                value = value[key]
            elif key < len(value):
                value = value[key]
            else:
                raise StoreFormatError(
                    'identity path does not address canonical state'
                )
        else:
            raise StoreFormatError(
                'identity path does not address canonical state'
            )

    if isinstance(value, EventLog):
        value._ensure_backend_readable()
        if value._disk_prefix is not None and not mutable_event_tail_only:
            raise StoreFormatError(
                'disk-backed EventLog identity traversal requires '
                'mutable_event_tail_only=True'
            )
    return value


def _identity_assignment_boundary(
    world, target, *, mutable_event_tail_only=False
):
    if not target:
        raise StoreIntegrityError('duplicate/invalid identity target')
    parent = _at_path(
        world, target[:-1],
        mutable_event_tail_only=mutable_event_tail_only,
    )
    component = target[-1]
    if type(component) is not tuple or len(component) != 2:
        raise StoreFormatError('invalid identity path component')
    kind, key = component
    if (
        kind == 'field'
        and type(parent) in RECORD_FIELDS
        and key in RECORD_FIELDS[type(parent)]
        and not type(parent).__dataclass_params__.frozen
    ):
        return 'field'
    if (
        kind == 'key'
        and type(parent) in (dict, RecordTable)
        and key in parent
    ):
        return 'key'
    if (
        kind == 'index'
        and type(parent) is list
        and type(key) is int
        and key >= 0
        and key < len(parent)
    ):
        return 'list'
    if (
        kind == 'index'
        and isinstance(parent, EventLog)
        and mutable_event_tail_only
    ):
        # _at_path validates absolute range, sealedness and lifetime.
        _at_path(
            world, target,
            mutable_event_tail_only=True,
        )
        return 'eventlog'
    raise StoreFormatError('unsupported mutable identity boundary')


def _restore_identity(world, links, *, mutable_event_tail_only=False):
    if type(links) is not list:
        raise StoreFormatError('invalid identity links')
    comparisons = WorldCodec(identity_links_recorded=True)
    assignments = []
    targets = set()

    # Validate the complete batch, including assignment boundaries and exact
    # typed payload copies, before applying any relink.
    for link in links:
        if type(link) is not tuple or len(link) != 2:
            raise StoreFormatError('invalid identity link')
        target, owner = link
        if not target or target == owner or target in targets:
            raise StoreIntegrityError('duplicate/invalid identity target')
        targets.add(target)

        old = _at_path(
            world, target,
            mutable_event_tail_only=mutable_event_tail_only,
        )
        original = _at_path(
            world, owner,
            mutable_event_tail_only=mutable_event_tail_only,
        )
        boundary = _identity_assignment_boundary(
            world, target,
            mutable_event_tail_only=mutable_event_tail_only,
        )

        if isinstance(old, EventLog) or isinstance(original, EventLog):
            if old is not original:
                raise StoreIntegrityError(
                    'distinct EventLog aliases cannot be restored by value'
                )
        elif (
            type(old) is not type(original)
            or comparisons.encode(old) != comparisons.encode(original)
        ):
            raise StoreIntegrityError('aliased payload copies disagree')
        if boundary == 'eventlog':
            parent = _at_path(
                world, target[:-1], mutable_event_tail_only=True,
            )
            # Equal copies can still share an invalid ID for this position.
            # All tail-specific checks must precede every batch assignment.
            parent._validate_mutable_tail_relink(target[-1][1], original)
        assignments.append((target, owner, boundary))

    # Restore ancestors before descendants and re-resolve every owner after
    # earlier assignments. Validation above guarantees all boundaries/copies.
    assignments.sort(
        key=lambda item: (
            max(len(item[0]), len(item[1])),
            comparisons.encode((item[0], item[1])),
        )
    )
    for target, owner, _boundary in assignments:
        original = _at_path(
            world, owner,
            mutable_event_tail_only=mutable_event_tail_only,
        )
        parent = _at_path(
            world, target[:-1],
            mutable_event_tail_only=mutable_event_tail_only,
        )
        kind, key = target[-1]
        if (
            kind == 'field'
            and type(parent) in RECORD_FIELDS
            and not type(parent).__dataclass_params__.frozen
        ):
            object.__setattr__(parent, key, original)
        elif kind == 'key' and type(parent) in (dict, RecordTable):
            parent[key] = original
        elif kind == 'index' and type(parent) is list:
            parent[key] = original
        elif (
            kind == 'index'
            and isinstance(parent, EventLog)
            and mutable_event_tail_only
        ):
            parent._relink_mutable_tail(key, original)
        else:
            # This is unreachable without concurrent mutation; fail closed.
            raise StoreFormatError('unsupported mutable identity boundary')

