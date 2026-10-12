"""Normalize captured legacy Event payloads; only existing commit publishes.

Transient build maps contain copied references/bytes, not live canonical World
objects. Existing source labels identify mutable bodies; frozen values allocate
new destination IDs because legacy snapshots have no mutable identity labels.
"""
from dataclasses import replace
import math

from .core import Event, Ref
from .event_log import FrozenDict, FrozenList
from .incremental_store import StoreIntegrityError, StoreFormatError
from .persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from .persistence_lazy_nested_history import (
    HISTORY_CLASSES, HistoryReference, reference, immutable_value,
    DESCRIPTOR_NAMESPACE, ENTRY_NAMESPACE, PAGE_NAMESPACE,
)
from .persistence_history_types import NAMESPACE as TYPES
from .persistence_history_retirement import NAMESPACE as RETIREMENT
from .persistence_record_headers import (
    RecordReference, record_reference, record_header, checked_record_header, NAMESPACE as RECORD_HEADERS,
)
from .persistence_record_runtime import mutable_record
from .persistence_schema import RECORD_FIELDS
from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES, dependency_value
from .persistence_lazy_families import FAMILIES, AUXILIARY_OWNER_FAMILIES
from .persistence_history_copy_promotion import reconcile_copy
from .persistence_event_ids import AUTHORITY_REFERENCE
from .persistence_event_id_reference import EventIdReference, event_id_reference, check_compact_authority
from .persistence_adapters import (AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY,
    PACKED_LIST_KIND, PACKED_LIST_PAYLOAD, META, COLLECTION_LAYOUT)
from .incremental_store import RecordChange

from .persistence_nonreflexive_keys import (
    NonreflexiveKeyReference, nonreflexive_key_reference, nonreflexive_key_header,
    NAMESPACE as NAN_HEADERS, storage_equality_key, stored_immutable_key,
)


class _StoredCopyKeys:
    """Project already checked stored keys in the private full-copy builder."""
    @staticmethod
    def project_key(value, *, allocate=False, canonical=True):
        if not stored_immutable_key(value):
            raise StoreIntegrityError('copy key is outside the closed immutable schema')
        return storage_equality_key(value) if canonical else value


CURRENCY_ROOTS = ('world.currency.wallets', 'world.currency.treasuries')


def capture_bodies(store, pin, dependencies):
    """Explicit full-copy comparison material; never ordinary open/admission."""
    bodies, frozen = {}, {}
    for dep in dependencies:
        inc, kind = dep.key, dep.value[1]
        if kind == 'nan-key':
            bodies[inc] = store.codec.encode(store.read_version(pin, NAN_HEADERS, (inc, 0), expected_record_schema=1).value)
            frozen[inc] = True
            continue
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
                     orders, states, next_incarnation, captured, *, normalize_advancement=False):
    codec = target.codec
    bodies, frozen = captured
    known = {d.key: d.value[1] for d in dependencies}
    labels = {(codec.encode((p.owner_namespace, p.owner_key)), codec.encode(p.occurrence_path)): p.incarnation_id
        for p in placements}
    selected, built, signatures, active, added = {}, {}, {}, set(), []
    readonly_ids = {}
    atom_ids = {}
    cuts = {}
    facade_inc = labels.get((codec.encode(('world.event_ids', 0)), codec.encode(())))
    facade_rows = [(c.key, c.value[1]) for c in ordinary if c.namespace == 'world.event_ids' and not c.delete]
    facade_rows += [(c.key, c.value) for c in versions if c.namespace == 'world.event_ids' and not c.delete]
    facade_checked = False

    def check_facade_authority():
        nonlocal facade_checked
        if facade_checked:
            return
        if len(facade_rows) != 1 or facade_rows[0][0] != 0:
            raise StoreIntegrityError('Event-ID graph copy lacks its single captured root authority')
        check_compact_authority(facade_rows[0][1])
        facade_checked = True

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

    def encode_atom(source, owner, path):
        nonlocal next_incarnation
        # Genuine legacy has no float identity labels. Pin each decoded value
        # position to its nearest checked mutable ancestor so aliases of that
        # same container agree, without inventing key/value float sharing.
        anchor = ('owner', codec.encode(owner), codec.encode(path))
        for length in range(len(path), -1, -1):
            ancestor = labels.get(marker(owner, path[:length]))
            if ancestor is not None:
                anchor = ('ancestor', ancestor, codec.encode(path[length:]))
                break
        header = nonreflexive_key_header(source)
        if anchor not in atom_ids:
            inc = next_incarnation
            next_incarnation += 1
            atom_ids[anchor] = inc
            added.append(VersionChange(NAN_HEADERS, (inc, 0), header))
            built[inc] = dependency_value('nan-key')
            signatures[inc] = codec.encode(header)
            frozen[inc] = True
        inc = atom_ids[anchor]
        if signatures[inc] != codec.encode(header):
            raise StoreIntegrityError('legacy aliases disagree with captured NaN bits')
        return NonreflexiveKeyReference(inc)

    def encode_immutable(source, owner, path):
        if type(source) is float and math.isnan(source):
            return encode_atom(source, owner, path)
        if type(source) is tuple:
            return tuple(encode_immutable(v, owner, path + (('index', n),)) for n, v in enumerate(source))
        if type(source) is frozenset:
            # Set iteration order is not an identity authority. Canonical byte
            # order, including repeated equal-bit NaNs, gives each value slot.
            values = sorted(source, key=codec.encode)
            return frozenset(encode_immutable(v, owner, path + (('set-slot', n),)) for n, v in enumerate(values))
        if type(source) is Ref:
            return Ref(encode_immutable(source.kind, owner, path + (('field', 'kind'),)),
                       encode_immutable(source.id, owner, path + (('field', 'id'),)))
        return source

    def encode(source, owner, path, *, atom_path=None):
        if reference(source) or record_reference(source) or event_id_reference(source) or nonreflexive_key_reference(source):
            return source
        if type(source) is tuple:
            if source == AUTHORITY_REFERENCE and marker(owner, path) in labels:
                inc = labels[marker(owner, path)]
                if inc != facade_inc:
                    raise StoreIntegrityError('legacy Event-ID alias disagrees with owner-zero identity')
                check_facade_authority()
                selected[inc] = EventIdReference(inc)
                cuts.setdefault(codec.encode(owner), set()).add(path)
                return selected[inc]
            return tuple(encode(v, owner, path + (('index', n),),
                                atom_path=atom_path + (('index', n),) if atom_path is not None else None)
                         for n, v in enumerate(source))
        if immutable_value(source):
            return encode_immutable(source, owner, path if atom_path is None else atom_path)
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
                for ordinal, (key, child) in enumerate(source.items()):
                    if not immutable_value(key):
                        raise StoreFormatError('legacy Event map has an unsupported key')
                    stored_key = encode_immutable(key, owner, path + (('map-key', (ordinal, codec.encode(key))),))
                    atom_path = path + (('map-value', ordinal),) if immutable_value(child) else None
                    payload[stored_key] = encode(child, owner, path + (('key', key),), atom_path=atom_path)
                signature = codec.encode(tuple(payload.items()))
            elif kind == 'set':
                if any(not immutable_value(v) for v in source):
                    raise StoreFormatError('legacy Event set has an unsupported member')
                payload = frozenset(encode_immutable(v, owner, path + (('set-slot', n),))
                                    for n, v in enumerate(sorted(source, key=codec.encode)))
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
                if kind in ('map', 'set', 'frozen-map'):
                    arguments['key_runtime'] = _StoredCopyKeys()
                if kind.startswith('frozen-'):
                    arguments['reference_is_immutable'] = lambda child: frozen.get(child.incarnation, False)
                builder = HISTORY_CLASSES[kind](target, pin, inc, **arguments)
                changes = builder.pending_changes()
                if kind.startswith('frozen-'):
                    frozen[inc] = builder._deep_immutable
            added.extend(changes)
            built[inc] = dependency_value(kind)
        return ref

    # Earlier typed histories may still contain literal NaNs. Project their
    # physical slots during this explicit full copy, retaining parent IDs and
    # member ordinals. Rekeyed scalar entries keep their collection-order row.
    atom_rows, owner_moves = [], {}
    rewritten_backings = []
    for change in versions:
        if change.delete or change.namespace not in (PAGE_NAMESPACE, ENTRY_NAMESPACE, RECORD_HEADERS):
            rewritten_backings.append(change)
            continue
        owner = change.namespace, change.key
        if change.namespace == PAGE_NAMESPACE:
            value = tuple(encode_immutable(v, owner, (('index', n),)) for n, v in enumerate(change.value))
            key = change.key
        elif change.namespace == ENTRY_NAMESPACE:
            ordinal, original_key, child = change.value
            stored_key = encode_immutable(original_key, owner, (('index', 1),))
            value = (ordinal, stored_key, encode_immutable(child, owner, (('index', 2),)))
            key = change.key[0], storage_equality_key(stored_key)
        else:
            cls, values, state = checked_record_header(change.value)
            value = (change.value[0], change.value[1], tuple(
                encode_immutable(v, owner, (('field', field),))
                for field, v in zip(RECORD_FIELDS[cls], values)), state)
            key = change.key
        replacement = replace(change, key=key, value=value)
        rewritten_backings.append(replacement)
        if codec.encode((key, value)) != codec.encode((change.key, change.value)):
            atom_rows.append(replacement)
            owner_moves[codec.encode(owner)] = (change.namespace, key)
    versions = rewritten_backings
    if owner_moves:
        placements = tuple(replace(p, owner_key=owner_moves[codec.encode((p.owner_namespace, p.owner_key))][1])
                           if codec.encode((p.owner_namespace, p.owner_key)) in owner_moves else p for p in placements)
        orders = tuple((ns, codec.encode(owner_moves[codec.encode((ns, codec.decode(key)))][1]), ordinal)
                       if codec.encode((ns, codec.decode(key))) in owner_moves else (ns, key, ordinal)
                       for ns, key, ordinal in orders)

    # These concrete root tables now accept the same checked map headers. Seed
    # their graphs even without an Event alias; explicit copy closes the whole
    # currency bucket rather than leaving a resident legacy subtree behind.
    for change in (*versions, *ordinary):
        if change.namespace in CURRENCY_ROOTS and not change.delete:
            value = change.value[1] if isinstance(change, RecordChange) else change.value
            encode(value, (change.namespace, change.key), ())
        if normalize_advancement and change.namespace == 'world.advancement.paths' and not change.delete:
            from .advancement import EssencePath
            value = change.value[1] if isinstance(change, RecordChange) else change.value
            if type(value) is not EssencePath:
                raise StoreIntegrityError('advancement normalization requires a captured native EssencePath')
            encode(value, (change.namespace, change.key), ())
    # Source Event envelopes are current ordinary record authority.
    for change in ordinary:
        if change.namespace == 'world.events' and not change.delete:
            if type(change.value) is not tuple or len(change.value) != 2 or type(change.value[1]) is not Event:
                raise StoreIntegrityError('legacy Event source envelope is invalid')
            encode(change.value[1].data, (change.namespace, change.key), (('field', 'data'),))

    def rewrite(source, owner, path=(), *, root=False):
        inc = labels.get(marker(owner, path))
        if owner == ('world.event_ids', 0):
            return source  # Preserve the one real compact value authority.
        if type(source) is tuple and source == AUTHORITY_REFERENCE and inc == facade_inc:
            return source  # Existing concrete family adapters keep compatibility markers.
        if root and normalize_advancement and owner[0] == 'world.advancement.paths':
            return encode(source, owner, path)
        if root and inc in selected and mutable_record(source):
            # Concrete native family records remain physical bodies. Validate
            # their fields against the recursively backed alias before publish,
            # without removing that family's own direct child placements.
            encode(source, owner, path)
            cuts[codec.encode(owner)].discard(path)
        if root and inc in selected and not mutable_record(source) and not reference(source):
            if owner[0] not in CURRENCY_ROOTS or selected[inc].kind != 'map':
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
    # Earlier conversion could leave an unused set snapshot under the facade's
    # same incarnation. The native World root is its value authority. Remove
    # that destination-only legacy snapshot when no stored set edge consumes it;
    # never publish two concrete bodies for the newly typed facade reference.
    removed_facade_set = False
    if facade_inc in selected and facade_inc in known:
        if known[facade_inc] != 'set':
            raise StoreIntegrityError('Event-ID facade competes with another backing kind')
        pending = [c.value for c in (*versions, *ordinary) if not c.delete]
        while pending:
            value = pending.pop()
            if reference(value) and value.incarnation == facade_inc:
                raise StoreFormatError('legacy Event-ID set backing still has typed owners requiring their root adapter')
            if type(value) is dict:
                pending.extend(value.values())
            elif type(value) in (list, tuple, set, frozenset):
                pending.extend(value)
            elif mutable_record(value):
                pending.extend(getattr(value, field) for field in RECORD_FIELDS[type(value)])
        if any(c.namespace == RETIREMENT and c.key == facade_inc and not c.delete for c in versions):
            raise StoreFormatError('legacy Event-ID set backing has unresolved retirement authority')
        versions = [c for c in versions if not (
            (c.namespace in (DESCRIPTOR_NAMESPACE, TYPES) and c.key == facade_inc)
            or (c.namespace == ENTRY_NAMESPACE and c.key[0] == facade_inc))]
        dependencies = tuple(c for c in dependencies if c.key != facade_inc)
        removed_facade_set = True
    retained = []
    for p in placements:
        if removed_facade_set and p.owner_namespace == ENTRY_NAMESPACE and p.owner_key[0] == facade_inc:
            continue
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
    retained_markers = {marker((p.owner_namespace, p.owner_key), p.occurrence_path): p.incarnation_id for p in retained}
    for change in (*added, *atom_rows):
        adapter = AUXILIARY_OWNER_FAMILIES.get(change.namespace)
        if adapter is not None:
            for path, child in adapter.reference_placements(change.value):
                placement_marker = marker((change.namespace, change.key), path)
                if placement_marker in retained_markers:
                    if retained_markers[placement_marker] != child:
                        raise StoreIntegrityError('copied atom slot conflicts with its source placement')
                    continue
                retained.append(IdentityOccurrenceChange(change.namespace, change.key, path, child))
                retained_markers[placement_marker] = child
    dependencies = dependencies + tuple(VersionChange(DEPENDENCIES, inc, value) for inc, value in built.items())
    return (*reconcile_copy(codec, versions, ordinary, tuple(retained), dependencies, orders, states), next_incarnation)
