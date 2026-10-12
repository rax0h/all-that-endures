"""Normalize captured legacy Event payloads; only existing commit publishes.

Transient build maps contain copied references/bytes, not live canonical World
objects. Existing source labels identify mutable bodies; frozen values allocate
new destination IDs because legacy snapshots have no mutable identity labels.
"""
from dataclasses import replace

from .core import Event
from .event_log import FrozenDict, FrozenList
from .incremental_store import StoreIntegrityError, StoreFormatError
from .persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from .persistence_lazy_nested_history import (
    HISTORY_CLASSES, HistoryReference, reference, immutable_value,
)
from .persistence_record_headers import (
    RecordReference, record_reference, record_header, NAMESPACE as RECORD_HEADERS,
)
from .persistence_record_runtime import mutable_record
from .persistence_schema import RECORD_FIELDS
from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
from .persistence_lazy_families import FAMILIES, AUXILIARY_OWNER_FAMILIES
from .persistence_history_copy_promotion import reconcile_copy
from .persistence_event_ids import AUTHORITY_REFERENCE
from .persistence_adapters import (AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY,
    PACKED_LIST_KIND, PACKED_LIST_PAYLOAD, META, COLLECTION_LAYOUT)
from .incremental_store import RecordChange


def capture_bodies(store, pin, dependencies):
    """Explicit full-copy comparison material; never ordinary open/admission."""
    bodies, frozen = {}, {}
    for dep in dependencies:
        inc, kind = dep.key, dep.value[1]
        if kind == 'record':
            bodies[inc] = store.codec.encode(store.read_version(pin, RECORD_HEADERS, (inc, 0), expected_record_schema=1).value)
            continue
        history = HISTORY_CLASSES[kind](store, pin, inc, checked_types=True, recursive=True)
        payload = tuple(history.items()) if history._kind == 'map' else frozenset(history) if kind == 'set' else tuple(history)
        bodies[inc] = store.codec.encode(payload)
        if kind.startswith('frozen-'):
            frozen[inc] = history._deep_immutable
    return bodies, frozen


def normalize_events(target, pin, versions, ordinary, placements, dependencies,
                     orders, states, next_incarnation, captured):
    codec = target.codec
    bodies, frozen = captured
    known = {d.key: d.value[1] for d in dependencies}
    labels = {(codec.encode((p.owner_namespace, p.owner_key)), codec.encode(p.occurrence_path)): p.incarnation_id
        for p in placements}
    selected, built, signatures, active, added = {}, {}, {}, set(), []
    readonly_ids = {}
    cuts = {}

    def marker(owner, path):
        return codec.encode(owner), codec.encode(path)

    def identity(source, owner, path):
        nonlocal next_incarnation
        if type(source) in (FrozenDict, FrozenList):
            # Separate decoded owner rows have separate Python snapshot bodies.
            # A checked mutable ancestor still supplies one durable identity for
            # its readonly field path across all of those source aliases.
            ident = ('body', id(source))
            for length in range(len(path) - 1, -1, -1):
                ancestor = labels.get(marker(owner, path[:length]))
                if ancestor is not None:
                    ident = ('ancestor', ancestor, codec.encode(path[length:]))
                    break
            if ident not in readonly_ids:
                readonly_ids[ident] = next_incarnation
                next_incarnation += 1
            return readonly_ids[ident]
        inc = labels.get(marker(owner, path))
        if inc is None:
            raise StoreIntegrityError('legacy Event mutable value has no checked source label')
        return inc

    def encode(source, owner, path):
        if reference(source) or record_reference(source):
            return source
        if type(source) is tuple:
            if source == AUTHORITY_REFERENCE and marker(owner, path) in labels:
                raise StoreFormatError('Event-ID root alias needs its special copy authority')
            return tuple(encode(v, owner, path + (('index', n),)) for n, v in enumerate(source))
        if immutable_value(source):
            return source
        cls = type(source)
        if cls not in (dict, list, set, FrozenDict, FrozenList) and not mutable_record(source):
            raise StoreFormatError('legacy Event payload has an undeclared graph value')
        inc = identity(source, owner, path)
        kind = 'record' if mutable_record(source) else {
            dict: 'map', list: 'list', set: 'set', FrozenDict: 'frozen-map', FrozenList: 'frozen-list'}[cls]
        if known.get(inc) == 'sequence' and kind == 'list':
            kind = 'sequence'
        if inc in known and known[inc] != kind:
            raise StoreIntegrityError('legacy Event source label has a different backing kind')
        ref = RecordReference(inc) if kind == 'record' else HistoryReference(kind, inc)
        selected[inc] = ref
        cuts.setdefault(codec.encode(owner), set()).add(path)
        if inc in active:
            raise StoreIntegrityError('cyclic legacy Event payload')
        active.add(inc)
        try:
            if kind == 'record':
                payload = record_header(source, values=tuple(encode(getattr(source, f), owner,
                    path + (('field', f),)) for f in RECORD_FIELDS[cls]))
                signature = codec.encode(payload)
            elif kind in ('map', 'frozen-map'):
                payload = {}
                for key, child in source.items():
                    if not immutable_value(key):
                        raise StoreFormatError('legacy Event map has an unsupported key')
                    payload[key] = encode(child, owner, path + (('key', key),))
                signature = codec.encode(tuple(payload.items()))
            elif kind == 'set':
                payload = frozenset(source)
                if any(not immutable_value(v) for v in payload):
                    raise StoreFormatError('legacy Event set has an unsupported member')
                signature = codec.encode(payload)
            else:
                payload = tuple(encode(v, owner, path + (('index', n),)) for n, v in enumerate(source))
                signature = codec.encode(payload)
        finally:
            active.remove(inc)
        expected = bodies.get(inc, signatures.get(inc))
        if expected is not None and expected != signature:
            raise StoreIntegrityError('legacy Event aliases disagree with captured backing values')
        signatures[inc] = signature
        if inc not in known and inc not in built:
            if kind == 'record':
                changes = (VersionChange(RECORD_HEADERS, (inc, 0), payload),)
            else:
                arguments = dict(initial_values=payload, checked_types=True, recursive=True)
                if kind.startswith('frozen-'):
                    arguments['reference_is_immutable'] = lambda child: frozen.get(child.incarnation, False)
                builder = HISTORY_CLASSES[kind](target, pin, inc, **arguments)
                changes = builder.pending_changes()
                if kind.startswith('frozen-'):
                    frozen[inc] = builder._deep_immutable
            added.extend(changes)
            built[inc] = dependency_value(kind)
        return ref

    # Source Event envelopes are current ordinary record authority.
    for change in ordinary:
        if change.namespace == 'world.events' and not change.delete:
            if type(change.value) is not tuple or len(change.value) != 2 or type(change.value[1]) is not Event:
                raise StoreIntegrityError('legacy Event source envelope is invalid')
            encode(change.value[1].data, (change.namespace, change.key), (('field', 'data'),))

    def rewrite(source, owner, path=(), *, root=False):
        inc = labels.get(marker(owner, path))
        if root and inc in selected and mutable_record(source):
            # Concrete native family records remain physical bodies. Validate
            # their fields against the recursively backed alias before publish,
            # without removing that family's own direct child placements.
            encode(source, owner, path)
            cuts[codec.encode(owner)].discard(path)
        if root and inc in selected and not mutable_record(source) and not reference(source):
            raise StoreFormatError('raw Event alias to concrete family container needs its root adapter')
        if inc in selected and not (root and mutable_record(source)):
            return encode(source, owner, path)
        if type(source) in (FrozenDict, FrozenList):
            return encode(source, owner, path)
        if reference(source) or record_reference(source) or immutable_value(source):
            return source
        if type(source) is tuple:
            return tuple(rewrite(v, owner, path + (('index', n),)) for n, v in enumerate(source))
        if type(source) is dict:
            if root and inc in selected:
                raise StoreFormatError('raw Event alias to concrete family container needs its root adapter')
            return {k: rewrite(v, owner, path + (('key', k),)) for k, v in source.items()}
        if type(source) is list:
            return [rewrite(v, owner, path + (('index', n),)) for n, v in enumerate(source)]
        if mutable_record(source):
            result = object.__new__(type(source))
            for field in RECORD_FIELDS[type(source)]:
                child = getattr(source, field)
                stored = encode(child, owner, path + (('field', field),)) if type(source) is Event and field == 'data' else rewrite(
                    child, owner, path + (('field', field),))
                object.__setattr__(result, field, stored)
            if type(source) is Event and '_sealed' in vars(source):
                object.__setattr__(result, '_sealed', vars(source)['_sealed'])
            return result
        return source

    rewritten = []
    for change in ordinary:
        if change.namespace in FAMILIES and not change.delete:
            ordinal, value = change.value
            change = replace(change, value=(ordinal, rewrite(value, (change.namespace, change.key), root=True)))
        rewritten.append(change)
    ordinary = tuple(rewritten)
    versions = [replace(v, value=rewrite(v.value, (v.namespace, v.key), root=True))
        if v.namespace in FAMILIES and not v.delete else v for v in versions] + added
    retained = []
    for p in placements:
        paths = cuts.get(codec.encode((p.owner_namespace, p.owner_key)), ())
        if not any(len(prefix) < len(p.occurrence_path) and p.occurrence_path[:len(prefix)] == prefix for prefix in paths):
            retained.append(p)
    # Newly allocated readonly Event data has no legacy occurrence row.
    for owner_marker, paths in cuts.items():
        owner = codec.decode(owner_marker)
        for path in paths:
            if any(len(parent) < len(path) and path[:len(parent)] == parent for parent in paths):
                continue
            if marker(owner, path) not in labels:
                # The normalized header now holds the checked reference.
                from .persistence_lazy import _relative_get
                source = next(c.value[1] for c in ordinary if (c.namespace, c.key) == owner)
                ref = _relative_get(source, path)
                retained.append(IdentityOccurrenceChange(*owner, path, ref.incarnation))
    # Checked action routing owns one accepted packed physical source. Convert
    # only the copied current body; legacy logical positions retain their IDs.
    actions = [c for c in ordinary if c.namespace == AGENCY_ACTIONS_NAMESPACE and not c.delete]
    if actions and not any(c.key == PACKED_LIST_KEY for c in actions):
        if any(type(c.key) is not int or c.memberships for c in actions):
            raise StoreFormatError('legacy action packing requires unindexed logical positions')
        ranked = sorted(actions, key=lambda c: c.value[0])
        if [c.key for c in ranked] != list(range(len(ranked))):
            raise StoreIntegrityError('legacy action positions disagree with current order')
        values = tuple(c.value[1] for c in ranked)
        ordinary = tuple(c for c in ordinary if c.namespace != AGENCY_ACTIONS_NAMESPACE) + (
            RecordChange(AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY, (0, (PACKED_LIST_PAYLOAD, values))),)
        retained = [replace(p, owner_key=PACKED_LIST_KEY,
            occurrence_path=(('index', p.owner_key),) + p.occurrence_path)
            if p.owner_namespace == AGENCY_ACTIONS_NAMESPACE else p for p in retained]
    # Empty roots also need the accepted packed layout for subsequent edits.
    if not actions:
        ordinary += (RecordChange(AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY, (0, (PACKED_LIST_PAYLOAD, ()))),)
    rewritten_metadata = []
    for change in ordinary:
        if change.namespace == META and change.key in ('manifest', COLLECTION_LAYOUT):
            layout = dict(change.value['collections'] if change.key == 'manifest' else change.value)
            packed = next(c for c in ordinary if c.namespace == AGENCY_ACTIONS_NAMESPACE and c.key == PACKED_LIST_KEY)
            layout[AGENCY_ACTIONS_NAMESPACE] = (PACKED_LIST_KIND, len(packed.value[1][1]), 0)
            change = replace(change, value=dict(change.value, collections=layout) if change.key == 'manifest' else layout)
        rewritten_metadata.append(change)
    ordinary = tuple(rewritten_metadata)
    for change in added:
        adapter = AUXILIARY_OWNER_FAMILIES.get(change.namespace)
        if adapter is not None:
            retained.extend(IdentityOccurrenceChange(change.namespace, change.key, path, child)
                for path, child in adapter.reference_placements(change.value))
    dependencies = dependencies + tuple(VersionChange(DEPENDENCIES, inc, value) for inc, value in built.items())
    return (*reconcile_copy(codec, versions, ordinary, tuple(retained), dependencies, orders, states), next_incarnation)
