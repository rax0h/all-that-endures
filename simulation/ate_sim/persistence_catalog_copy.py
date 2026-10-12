"""Private checked-catalog bootstrap for the eventual complete World converter.

This step deliberately does not emit capability6 or make ordinary World open
select staged catalog authority. Remaining graph normalization/format contracts
must be completed before the final converter can advertise a complete format.
"""
from pathlib import Path
from dataclasses import is_dataclass
import tempfile
import uuid

from .incremental_store import (
    Membership, RecordChange, StoreFormatError, StoreIntegrityError,
    _counts_blob, _head_checksum,
)
from .persistence_adapters import WorldCodec, SCHEMA
from .persistence_lazy_store import (
    LazyRecordStore, VersionChange, IdentityOccurrenceChange,
    _namespace_checksum, _order_checksum, BOUNDED_AUTHORITY_FORMAT_VERSION,
)
from .persistence_lazy_families import IDENTITY_OWNER_FAMILIES, AUXILIARY_OWNER_FAMILIES
from .persistence_lazy_identity_catalog import (
    IdentityCatalog, initial_catalog_delta, CATALOG_NAMESPACE, OWNER_NAMESPACE,
    GROUP_NAMESPACE, LINK_NAMESPACE, OWNER_TREE_NAMESPACE, CATALOG_TAG,
)
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE, PAGE_NAMESPACE, ENTRY_NAMESPACE
from .persistence_lazy_sequence import (
    DESCRIPTOR_NAMESPACE as SEQUENCE_DESCRIPTOR, NODE_NAMESPACE, DIRECTORY_NAMESPACE,
    NAMESPACES as SEQUENCE_NAMESPACES, LazyOrderedSequence,
)
from .persistence_record_headers import NAMESPACE as RECORD_HEADERS
from .persistence_record_headers import record_reference
from .persistence_event_id_reference import event_id_reference, check_compact_authority
from .persistence_lazy_nested_history import reference
from .persistence_schema import RECORD_FIELDS
from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
from .persistence_history_types import verify_type_witnesses
from .persistence_session import (
    _preflight_conversion_paths, _publish_private_cold_file,
    EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
)


def _copy_phase(_phase, _private_path):
    """Private deterministic fault seam; no alternate publication protocol."""
    return None


def _owner_sources(store, pin):
    versions, ordinary = [], []
    for namespace in IDENTITY_OWNER_FAMILIES:
        if store._namespace_state_at(namespace, pin.captured_head) is not None:
            for key in store.iter_keys(pin, namespace):
                typed_key = store.codec.encode(key)
                row = store._visible_record_row(pin.captured_head, namespace, typed_key)
                if row is None:
                    raise StoreIntegrityError('catalog copy owner disappeared from captured namespace')
                value, schema, _start, _end, memberships = store._check_record_row(
                    namespace, typed_key, row, decode=True)
                adapter = AUXILIARY_OWNER_FAMILIES.get(namespace)
                # Only permanent sequence occurrence leaves own child bodies.
                if (adapter is not None and adapter.owner_kind == 'leaf'
                        and type(value) is tuple and value and value[0] == 'branch'):
                    continue
                versions.append(VersionChange(namespace, key, value,
                    record_schema=schema,
                    memberships=tuple(Membership(*m) for m in memberships)))
        else:
            ordinary.extend(RecordChange(namespace, key, value, record_schema=schema)
                for key, value, schema in store.read_records(namespace, expected_record_schema=1))
    return versions, ordinary


def _backing_rosters(store, pin, next_incarnation):
    kinds = {}
    for namespace in (DESCRIPTOR_NAMESPACE, SEQUENCE_DESCRIPTOR, RECORD_HEADERS):
        for key in store.iter_keys(pin, namespace):
            value = store.read_version(pin, namespace, key, expected_record_schema=1).value
            inc = key[0] if namespace == RECORD_HEADERS and type(key) is tuple else key
            kind = 'record' if namespace == RECORD_HEADERS else 'sequence' if namespace == SEQUENCE_DESCRIPTOR else value[0]
            if (type(inc) is not int or not 0 < inc < next_incarnation or inc in kinds):
                raise StoreIntegrityError('duplicate or unallocated backing in catalog copy')
            kinds[inc] = kind
    return tuple(VersionChange(DEPENDENCIES, inc, dependency_value(kind)) for inc, kind in kinds.items())


def _verify_catalog(store, pin):
    catalog = IdentityCatalog(store)
    descriptor = catalog._descriptor(pin)
    links, expected_nodes, live_owners = 0, set(), set()
    for incarnation in store.iter_keys(pin, GROUP_NAMESPACE):
        group = catalog.read_identity_group(pin, incarnation)
        links += len(group.links)
        for values in (group.occurrences, group.links):
            if hasattr(values, 'close'):
                values.close()
    for owner in store.iter_keys(pin, OWNER_NAMESPACE):
        checked = catalog.read_owner_identity(pin, owner)
        if hasattr(checked.occurrences, 'close'):
            checked.occurrences.close()
        header = catalog._owner(pin, owner)
        if header[1]:
            live_owners.add(store.codec.encode(owner))
        pending = [header[6:]] if header[6] is not None else []
        while pending:
            prefix, count, checksum = pending.pop()
            marker = store.codec.encode((*owner, prefix))
            if marker in expected_nodes:
                raise StoreIntegrityError('duplicate identity owner tree node')
            expected_nodes.add(marker)
            node = catalog._node(pin, owner, prefix, count, checksum)
            if node[0] == 'owner-branch/v1':
                pending.extend(child[1:] for child in node[2])
    if links != store.namespace_size(pin, LINK_NAMESPACE):
        raise StoreIntegrityError('identity link inventory is incomplete or extra')
    versions, ordinary = _owner_sources(store, pin)
    if live_owners != {store.codec.encode((v.namespace, v.key)) for v in (*versions, *ordinary)}:
        raise StoreIntegrityError('identity owner witness inventory is incomplete or extra')
    if expected_nodes != {store.codec.encode(key) for key in store.iter_keys(pin, OWNER_TREE_NAMESPACE)}:
        raise StoreIntegrityError('extra/missing identity owner tree authority')
    if descriptor[0] == CATALOG_TAG:
        from .persistence_lazy_identity_retired import RetiredIdentityRanges
        RetiredIdentityRanges(store, pin, header=descriptor[4]).scrub()
    verify_type_witnesses(store, pin)
    from .persistence_history_retirement import NAMESPACE as RETIREMENT, _job
    for incarnation in store.iter_keys(pin, SEQUENCE_DESCRIPTOR):
        if store.contains_lazy_key(pin, RETIREMENT, incarnation) and _job(store, pin, incarnation)[4]:
            # Checked retirement deliberately leaves an unreadable partial tree.
            continue
        LazyOrderedSequence(store, pin, incarnation, value_mode='native',
            checked_types=True, recursive=True).scrub()


def _check_backing_graph(codec, versions, dependencies):
    """Scrub the existing physical ownership relation during explicit full copy.

    The temporary traversal state is discarded before publication. No new
    persistent dependency graph, registry or ordinary-operation scan is added.
    """
    kinds = {change.key: change.value[1] for change in dependencies}
    expected = {PAGE_NAMESPACE: ('list', 'frozen-list'),
        ENTRY_NAMESPACE: ('map', 'set', 'frozen-map'),
        RECORD_HEADERS: ('record',)}
    expected.update((ns, ('sequence',)) for ns in SEQUENCE_NAMESPACES if ns != SEQUENCE_DESCRIPTOR)
    edges = {}
    for change in versions:
        adapter = AUXILIARY_OWNER_FAMILIES.get(change.namespace)
        if change.namespace not in expected or change.delete:
            continue
        if adapter is not None:
            adapter.validate_key(change.key)
        elif (type(change.key) is not tuple or len(change.key) != 2
                or type(change.key[0]) is not int or change.key[0] <= 0
                or (type(change.key[1]) is not bytes or len(change.key[1]) > 32
                    if change.namespace == DIRECTORY_NAMESPACE
                    else type(change.key[1]) is not int or change.key[1] <= 0)):
            raise StoreIntegrityError('invalid physical sequence projection key')
        parent = change.key[0]
        if kinds.get(parent) not in expected[change.namespace]:
            raise StoreIntegrityError('physical owner has missing or wrong-kind backing')
        if adapter is None:
            continue
        if change.namespace == NODE_NAMESPACE and type(change.value) is tuple and change.value and change.value[0] == 'branch':
            continue
        adapter.validate_source(change, 'lazy', codec)
        for _path, child in adapter.reference_placements(change.value):
            edges.setdefault(parent, set()).add(child)
    colors = {}
    for root in edges:
        pending = [(root, False)]
        while pending:
            incarnation, finished = pending.pop()
            if finished:
                colors[incarnation] = 2
                continue
            color = colors.get(incarnation, 0)
            if color == 2:
                continue
            if color == 1:
                raise StoreIntegrityError('cyclic copy backing ownership relation')
            colors[incarnation] = 1
            pending.append((incarnation, True))
            pending.extend((child, False) for child in edges.get(incarnation, ()))


def _check_reference_targets(values, dependencies, *, event_id_incarnations=()):
    """Explicit conversion scrub, including compact refs inside eager headers."""
    kinds = {change.key: change.value[1] for change in dependencies}
    used_facades = set()
    pending, seen = list(values), set()
    while pending:
        value = pending.pop()
        if event_id_reference(value):
            if value.incarnation not in event_id_incarnations:
                raise StoreIntegrityError('catalog copy Event-ID reference lacks owner-zero identity')
            if value.incarnation in kinds:
                raise StoreIntegrityError('Event-ID facade competes with a recursive backing incarnation')
            used_facades.add(value.incarnation)
            continue
        if reference(value) or record_reference(value):
            expected = value.kind if reference(value) else 'record'
            if kinds.get(value.incarnation) != expected:
                raise StoreIntegrityError('catalog copy reference has missing or wrong-kind backing')
            continue
        if id(value) in seen:
            continue
        seen.add(id(value))
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend(value)
        elif is_dataclass(value) and type(value) in RECORD_FIELDS:
            pending.extend(getattr(value, field) for field in RECORD_FIELDS[type(value)])
    return used_facades


def _empty_destination(store, source_head, segments, format_floor):
    """Initialize an unpublished mutable-empty copy beside the captured source.

    Immutable segment authority is copied unchanged. Current record authority
    is installed for the first time by the existing commit, never moved in place.
    """
    counts = {}
    for row in segments:
        counts[row[0]] = (0, counts.get(row[0], (0, 0))[1] + 1)
    values = (*source_head[:5], store.codec.encode(tuple(sorted(counts))),
              _counts_blob(store.codec, counts))
    store.db.execute('BEGIN IMMEDIATE')
    try:
        store.db.executemany('INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?)', segments)
        store.db.execute('DELETE FROM save_head')
        store.db.execute('INSERT INTO save_head VALUES (1,?,?,?,?,?,?,?,?)',
                         (*values, _head_checksum(*values)))
        store.db.execute("UPDATE store_metadata SET value=? WHERE key='format_version'", (str(format_floor),))
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise


def _restore_copy_ordinals(store, generation, orders, states):
    """Private full-copy construction preserves source ordering and high water.

    The writer is closed to World readers until publication. This is not an
    ordinary mutation or an old-pin metadata rewrite.
    """
    store.db.execute('BEGIN IMMEDIATE')
    try:
        for ns, key, ordinal in orders:
            changed = store.db.execute('UPDATE lazy_order_versions SET ordinal=?,row_checksum=? '
                'WHERE namespace=? AND typed_key=? AND valid_from=? AND valid_to IS NULL',
                (ordinal, _order_checksum(ns, key, ordinal, generation, None), ns, key, generation)).rowcount
            if changed != 1:
                raise StoreIntegrityError('private copy lost a current collection-order row')
        for ns, count, next_ordinal in states:
            row = store.db.execute('SELECT member_count FROM lazy_namespace_state '
                'WHERE namespace=? AND valid_from=? AND valid_to IS NULL', (ns, generation)).fetchone()
            if row != (count,):
                raise StoreIntegrityError('private copy namespace member count changed')
            store.db.execute('UPDATE lazy_namespace_state SET next_ordinal=?,row_checksum=? '
                'WHERE namespace=? AND valid_from=? AND valid_to IS NULL',
                (next_ordinal, _namespace_checksum(ns, count, next_ordinal, generation, None), ns, generation))
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise


def _copy_with_checked_catalog(source, destination, *, rules_id, promote_lists=(), normalize_events=False):
    """Explicit staging copy, never ordinary-open migration or complete format6."""
    from .persistence_history_copy_promotion import selection, capture_lists, transform_copy
    from .persistence_event_copy_normalization import capture_bodies, normalize_events as normalize_event_graph
    selected = selection(promote_lists)
    if type(normalize_events) is not bool:
        raise TypeError('normalize_events must be bool')
    source, destination = _preflight_conversion_paths(source, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    codec = WorldCodec(identity_links_recorded=True)
    with tempfile.TemporaryDirectory(prefix='.ate-catalog-copy-', dir=destination.parent) as directory:
        captured_path = Path(directory) / 'captured.sqlite'
        private = Path(directory) / 'destination.sqlite'
        copied = LazyRecordStore.copy_current_head(source, captured_path, codec=codec,
            expected_simulation_schema=SCHEMA, expected_rules_id=rules_id)
        _copy_phase('after_private_copy', private)
        with LazyRecordStore.open(captured_path, codec=codec, expected_simulation_schema=SCHEMA,
                                  expected_rules_id=rules_id) as store:
            pin = store.capture_pin()
            try:
                with store.read_snapshot(pin):
                    if store._namespace_state_at(CATALOG_NAMESPACE, pin.captured_head) is not None:
                        raise StoreFormatError('catalog bootstrap requires a genuine legacy source')
                    floor = int(store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
                    if floor != BOUNDED_AUTHORITY_FORMAT_VERSION:
                        raise StoreFormatError('catalog copy requires an explicit bounded-authority source')
                    verify_type_witnesses(store, pin)
                    versions, ordinary = _owner_sources(store, pin)
                    next_incarnation = store.read_identity_state(pin)
                    placements = tuple(IdentityOccurrenceChange(ns, codec.decode(key), codec.decode(path), inc)
                        for ns, key, path, inc in store.db.execute(
                            'SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
                            'FROM lazy_identity_occurrence_versions WHERE valid_from<=? '
                            'AND (valid_to IS NULL OR ?<valid_to)', (pin.captured_head, pin.captured_head)))
                    delta = initial_catalog_delta(codec, versions, placements,
                        ordinary_changes=ordinary, next_incarnation_id=next_incarnation,
                        generation=pin.captured_head + 1)
                    dependencies = _backing_rosters(store, pin, next_incarnation)
                    promoted = capture_lists(store, pin, selected)
                    captured_bodies = capture_bodies(store, pin, dependencies) if normalize_events else None
                    head, metadata = store._checked_head_row(), store.head_metadata()
                    segments = tuple(store.db.execute('SELECT * FROM segments'))
                    all_versions = []
                    states = []
                    for ns, count, high_water in store.db.execute('SELECT namespace,member_count,next_ordinal '
                            'FROM lazy_namespace_state WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                            (pin.captured_head, pin.captured_head)):
                        if ns == DEPENDENCIES:
                            continue
                        states.append((ns, count, high_water))
                        for key in store.iter_keys(pin, ns):
                            row = store._visible_record_row(pin.captured_head, ns, codec.encode(key))
                            value, schema, _a, _b, members = store._check_record_row(ns, codec.encode(key), row, decode=True)
                            all_versions.append(VersionChange(ns, key, value, record_schema=schema,
                                memberships=tuple(Membership(*m) for m in members)))
                        if count == 0:
                            all_versions.append(VersionChange(ns, ('empty-catalog-copy/v1',), delete=True))
                    orders = tuple((ns, key, ordinal) for ns, key, ordinal in store.db.execute(
                        'SELECT namespace,typed_key,ordinal FROM lazy_order_versions '
                        'WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
                        (pin.captured_head, pin.captured_head)) if ns != DEPENDENCIES)
                    ordinary_members = {}
                    for ns, key, name, index_value, ordinal in store.db.execute(
                            'SELECT namespace,record_key,index_name,index_value,ordinal FROM query_membership'):
                        ordinary_members.setdefault((ns, key), []).append(Membership(name, codec.decode(index_value), ordinal))
                    all_ordinary = tuple(RecordChange(ns, codec.decode(key), codec.decode(payload), record_schema=schema,
                        memberships=tuple(ordinary_members.get((ns, key), ())))
                        for ns, key, payload, schema in store.db.execute('SELECT namespace,typed_key,payload,record_schema FROM records')
                        if ns != LINK_NAMESPACE and (ns, codec.decode(key)) != (EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY))
                    _check_reference_targets((value.value for value in (*all_versions, *all_ordinary)), dependencies)
                    _check_backing_graph(codec, all_versions, dependencies)
            finally:
                store.release_pin(pin)
        with LazyRecordStore.create(private, codec=codec, simulation_schema=SCHEMA, rules_id=rules_id) as target:
            _empty_destination(target, head, segments, floor)
            token = uuid.uuid4().hex
            pin = target.capture_pin()
            try:
                if normalize_events:
                    (all_versions, all_ordinary, placements, dependencies, orders, states,
                     versions, ordinary, next_incarnation) = normalize_event_graph(target, pin,
                        all_versions, all_ordinary, placements, dependencies, orders, states,
                        next_incarnation, captured_bodies)
                if promoted:
                    (all_versions, all_ordinary, placements, dependencies, orders, states,
                     versions, ordinary) = transform_copy(target, pin, promoted, all_versions,
                        all_ordinary, placements, dependencies, orders, states)
                if promoted or normalize_events:
                    facade_ids = {p.incarnation_id for p in placements if
                        (p.owner_namespace, p.owner_key, p.occurrence_path) == ('world.event_ids', 0, ())}
                    _check_reference_targets((v.value for v in (*all_versions, *all_ordinary)), dependencies,
                        event_id_incarnations=facade_ids)
                    _check_backing_graph(codec, all_versions, dependencies)
                    delta = initial_catalog_delta(codec, versions, placements, ordinary_changes=ordinary,
                        next_incarnation_id=next_incarnation, generation=pin.captured_head + 1)
                _copy_phase('before_catalog_commit', private)
                committed = target.commit(pin, commit_token=token,
                    changes=all_ordinary + (RecordChange(EVENT_STORAGE,
                        COMMIT_DESCRIPTOR_KEY, (1, pin.captured_head + 1, token)),),
                    version_changes=tuple(all_versions) + delta.decode(codec)[0] + dependencies,
                    identity_changes=placements, next_incarnation_id=next_incarnation, new_segments=(),
                    required_format_version=floor, metadata=metadata)
                pin = committed.pin
                _copy_phase('after_catalog_commit', private)
                _restore_copy_ordinals(target, pin.captured_head, orders, states)
                target.verify_all()
                _verify_catalog(target, pin)
                generation, identity = target.generation, target.store_identity
                _copy_phase('after_catalog_validation', private)
            except BaseException:
                # The file is unpublished and will be removed. Do not mask the
                # original preparation/commit fault by releasing an unresolved pin.
                raise
            else:
                target.release_pin(pin)
        _copy_phase('before_publish', private)
        _publish_private_cold_file(private, destination)
    return {'source_generation': copied.generation, 'generation': generation,
            'store_identity': identity, 'source_preserved': True, 'complete_format': False}


def _copy_current_checked_catalog(source, destination, *, rules_id):
    """Copy already backed current authority without relabeling or format claims.

    Existing catalog commitments/retired intervals and physical rows remain
    unchanged. The destination's existing commit installs empty backing leases
    and its coherent cold commit descriptor after a source-preserving capture.
    """
    from .persistence_history_dependencies import _checked_value as checked_dependency
    source, destination = _preflight_conversion_paths(source, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    codec = WorldCodec(identity_links_recorded=True)
    with tempfile.TemporaryDirectory(prefix='.ate-checked-current-copy-', dir=destination.parent) as directory:
        private = Path(directory) / 'destination.sqlite'
        copied = LazyRecordStore.copy_current_head(source, private, codec=codec,
            expected_simulation_schema=SCHEMA, expected_rules_id=rules_id)
        _copy_phase('after_private_copy', private)
        with LazyRecordStore.open(private, codec=codec, expected_simulation_schema=SCHEMA,
                                  expected_rules_id=rules_id) as target:
            pin = target.capture_pin()
            try:
                with target.read_snapshot(pin):
                    if target._namespace_state_at(CATALOG_NAMESPACE, pin.captured_head) is None:
                        raise StoreFormatError('checked current copy requires an existing checked catalog')
                    floor = int(target.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
                    if floor != BOUNDED_AUTHORITY_FORMAT_VERSION:
                        raise StoreFormatError('checked current copy requires bounded-authority format5')
                    _verify_catalog(target, pin)
                    rosters = _backing_rosters(target, pin, target.read_identity_state(pin))
                    if set(target.iter_keys(pin, DEPENDENCIES)) != {r.key for r in rosters}:
                        raise StoreIntegrityError('checked copy dependency roster inventory is incomplete or extra')
                    for roster in rosters:
                        if checked_dependency(target, pin, roster.key)[1] != roster.value[1]:
                            raise StoreIntegrityError('checked copy dependency roster has wrong backing kind')
                    versions = []
                    namespaces = tuple(ns for (ns,) in target.db.execute(
                        'SELECT namespace FROM lazy_namespace_state WHERE valid_from<=? '
                        'AND (valid_to IS NULL OR ?<valid_to)', (pin.captured_head, pin.captured_head)))
                    for ns in namespaces:
                        for key in target.iter_keys(pin, ns):
                            row = target._visible_record_row(pin.captured_head, ns, codec.encode(key))
                            value, schema, _a, _b, members = target._check_record_row(ns, codec.encode(key), row, decode=True)
                            versions.append(VersionChange(ns, key, value, record_schema=schema,
                                memberships=tuple(Membership(*m) for m in members)))
                    ordinary = tuple(codec.decode(payload) for (payload,) in target.db.execute('SELECT payload FROM records'))
                    facade = IdentityCatalog(target).read_owner_identity(pin, ('world.event_ids', 0))
                    try:
                        facade_ids = {inc for path, inc in facade.occurrences if not path}
                    finally:
                        if hasattr(facade.occurrences, 'close'): facade.occurrences.close()
                    used_facades = _check_reference_targets((*ordinary, *(v.value for v in versions)), rosters,
                        event_id_incarnations=facade_ids)
                    if used_facades:
                        namespace = 'world.event_ids'
                        if target._namespace_state_at(namespace, pin.captured_head) is None:
                            envelope = target.read_record(namespace, 0, expected_record_schema=1)
                            if type(envelope) is not tuple or len(envelope) != 2:
                                raise StoreIntegrityError('Event-ID graph copy has an invalid root authority envelope')
                            authority = envelope[1]
                        else:
                            authority = target.read_version(pin, namespace, 0, expected_record_schema=1).value
                        check_compact_authority(authority)
                    _check_backing_graph(codec, versions, rosters)
                    metadata = target.head_metadata()
                token = uuid.uuid4().hex
                _copy_phase('before_catalog_commit', private)
                committed = target.commit(pin, commit_token=token,
                    changes=(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                        (1, pin.captured_head + 1, token)),),
                    version_changes=rosters, identity_changes=(), new_segments=(),
                    required_format_version=floor, metadata=metadata)
                pin = committed.pin
                _copy_phase('after_catalog_commit', private)
                target.verify_all()
                _verify_catalog(target, pin)
                generation, identity = target.generation, target.store_identity
                _copy_phase('after_catalog_validation', private)
            except BaseException:
                # The unpublished file is discarded, including ambiguous plans.
                raise
            else:
                target.release_pin(pin)
        _copy_phase('before_publish', private)
        _publish_private_cold_file(private, destination)
    return {'source_generation': copied.generation, 'generation': generation,
            'store_identity': identity, 'source_preserved': True, 'complete_format': False}
