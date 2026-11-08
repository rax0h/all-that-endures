"""Bounded append-frontier replay against accepted read-only predecessor bytes.

The existing counted-sequence implementation produces an expected delta only.
It is never registered in the World or added to the publisher's participants.
"""
from types import SimpleNamespace
from contextlib import nullcontext

from .incremental_store import StoreIntegrityError, _framed_sha
from .persistence_proof_content import version_key
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_lazy_nested_history import immutable_value
from .persistence_history_types import NAMESPACE as TYPES
from . import persistence_lazy_sequence as sequence
from . import persistence_lazy_identity_catalog as catalog
from . import persistence_proof_publication as content
from . import persistence_proof_scope as scope
from . import persistence_proof_world as world

MAX_BACKINGS = 16
MAX_APPENDED = 128
MAX_READS = 512
MAX_BYTES = 4 * 1048576


class Unsupported(Exception):
    """No sequence authority is granted; retain the original checked path."""


def _leaf_entries(value):
    if (type(value) is not tuple or len(value) != 2 or value[0] != 'leaf'
            or type(value[1]) is not tuple or len(value[1]) > sequence.LEAF_SIZE
            or any(type(e) is not tuple or len(e) != 2 or type(e[0]) is not int or e[0] <= 0 for e in value[1])
            or len({e[0] for e in value[1]}) != len(value[1])):
        raise StoreIntegrityError('invalid sequence append leaf entries')
    return value[1]


class _Sources:
    """Only the read operations needed by the existing sequence algorithm."""
    def __init__(self, store, request, consumed):
        self.store, self.request, self.codec = store, request, store.codec
        self.consumed, self.rows = consumed, {}

    def _ensure_open(self):
        self.store._ensure_open()

    def _require_pin(self, pin):
        if pin != self.request.pin:
            raise StoreIntegrityError('sequence replay changed its predecessor pin')
        self.store._require_pin(pin)

    def read_snapshot(self, pin):
        self._require_pin(pin)
        # The manifest guard already owns BEGIN IMMEDIATE. Replay performs no
        # independent transaction; every raw read below joins accepted content.
        if not self.store.db.in_transaction:
            raise StoreIntegrityError('sequence replay requires its manifest transaction')
        return nullcontext(pin.captured_head)

    def source(self, namespace, typed):
        marker = namespace, typed
        if marker in self.rows:
            return self.rows[marker]
        if len(self.rows) >= MAX_READS:
            raise Unsupported()
        self.consumed += len(namespace.encode()) + len(typed)
        sizes = self.store._interval_rows('lazy_record_versions', 'length(payload)+length(memberships)',
            ('namespace', 'typed_key'), marker, self.request.pin.captured_head,
            'lazy_record_interval', limit=2)
        if len(sizes) > 1:
            raise StoreIntegrityError('overlapping sequence predecessor versions')
        if len(sizes) == 1:
            if type(sizes[0][0]) is not int:
                raise StoreIntegrityError('invalid sequence predecessor size')
            self.consumed += sizes[0][0]
        if self.consumed > MAX_BYTES:
            raise Unsupported()
        row = content._source_version(self.store, self.request.pin.captured_head,
                                      namespace, typed, max_bytes=MAX_BYTES)
        expected = None if row is None else content._version_value(namespace, typed, row, self.codec.version)
        if content._map(self.store).get(self.request.pairs[0][0].versions,
                                       version_key(namespace, typed)) != expected:
            raise StoreIntegrityError('sequence predecessor lacks accepted content')
        if row is not None and (row.record_schema != 1 or row.memberships != self.codec.encode(())):
            raise Unsupported()
        self.rows[marker] = row
        return row

    def read_version(self, pin, namespace, key, *, expected_record_schema):
        self._require_pin(pin)
        if expected_record_schema != 1 or namespace not in (*sequence.NAMESPACES, TYPES):
            raise StoreIntegrityError('sequence replay requested an undeclared source')
        row = self.source(namespace, self.codec.encode(key))
        if row is None:
            raise KeyError(key)
        value = self.codec.decode(row.payload)
        if namespace == sequence.NODE_NAMESPACE:
            if type(value) is not tuple or len(value) != 2 or value[0] not in ('leaf', 'branch'):
                raise StoreIntegrityError('invalid sequence predecessor node')
            if value[0] == 'leaf' and any(not immutable_value(v[1]) for v in _leaf_entries(value)):
                raise Unsupported()
        return SimpleNamespace(value=value)


def certified(request, namespace, typed):
    return (namespace, typed) in (request.sequence_rows or ())


def prepare(store, request, versions):
    request.sequence_rows = frozenset()
    request.sequence_roots = request.pairs[1][0].roots[5:6]
    if len(versions) > 512 or len(request.pairs[1][0].roots) not in (6,7):
        return
    try:
        result = _prepare(store, request, versions)
    except Unsupported:
        return
    if result is None:
        return
    facts, child_root, sequence_root, approved, new_rows, added = result
    request.tail_facts, request.tail_child_root = facts, child_root
    request.sequence_roots = (sequence_root,)
    request.sequence_rows = frozenset(approved)
    request.tail_new.update(new_rows)
    request.tail_added += added


def _prepare(store, request, versions):
    codec, sa = store.codec, request.pairs[1][0]
    by_key = {(i['namespace'], i['typed_key']): i for i in versions}
    descriptors = [i for i in versions if i['namespace'] == sequence.DESCRIPTOR_NAMESPACE]
    if not descriptors:
        return None
    if len(descriptors) > MAX_BACKINGS:
        raise Unsupported()
    consumed = sum(len(i['namespace'].encode()) + len(i['typed_key']) +
                   len(i['payload'] or b'') + len(i['memberships_blob']) for i in versions)
    if consumed > MAX_BYTES:
        raise Unsupported()
    sources = _Sources(store, request, consumed)
    approved, new_rows, changes, backing_changes = {}, {}, [], []
    appended_count = added = 0
    for item in descriptors:
        incarnation = codec.decode(item['typed_key'])
        if type(incarnation) is not int or not 0 < incarnation < 2**63:
            raise StoreIntegrityError('invalid existing sequence incarnation')
        if incarnation >= sa.next_incarnation_id:
            raise Unsupported()
        parent = sources.source(sequence.DESCRIPTOR_NAMESPACE, item['typed_key'])
        if parent is None or item['change'].delete:
            raise Unsupported()
        before, after = codec.decode(parent.payload), codec.decode(item['payload'])
        world.target._validate_descriptor('sequence', incarnation, after)
        world.target._validate_descriptor('sequence', incarnation, before)
        if (before[0] != after[0] or before[3] == 0 or after[3] <= before[3]
                or after[4]-before[4] != after[3]-before[3] or after[6] <= before[6]):
            raise Unsupported()
        count = after[3]-before[3]
        appended_count += count
        if appended_count > MAX_APPENDED:
            raise Unsupported()
        actual, values = {}, {}
        for marker, row in by_key.items():
            ns, typed = marker
            if ns not in (*sequence.NAMESPACES, TYPES):
                continue
            key = codec.decode(typed)
            if ns in (sequence.DESCRIPTOR_NAMESPACE, TYPES):
                if type(key) is not int or not 0 < key < 2**63:
                    raise StoreIntegrityError('invalid sequence descriptor/type key')
                owner = key
            else:
                locator = scope._child_locator if ns == sequence.NODE_NAMESPACE else scope._sequence_locator
                owner = locator(ns, typed)[0].incarnation_id
            if owner != incarnation:
                continue
            if (row['change'].delete or row['change'].reinsertion or row['change'].record_schema != 1
                    or row['memberships_blob'] != codec.encode(())):
                raise Unsupported()
            actual[marker] = row['payload']
            if ns == sequence.NODE_NAMESPACE:
                node = codec.decode(row['payload'])
                if type(node) is not tuple or len(node) != 2 or node[0] not in ('leaf', 'branch'):
                    raise StoreIntegrityError('invalid frozen sequence node')
                if node[0] == 'leaf':
                    for occurrence, value in _leaf_entries(node):
                        if occurrence >= before[4]:
                            if occurrence in values or not immutable_value(value):
                                raise Unsupported()
                            values[occurrence] = value
        if set(values) != set(range(before[4], after[4])):
            raise Unsupported()
        replay = sequence.LazyOrderedSequence(sources, request.pin, incarnation, checked_types=True)
        try:
            prior_counts = replay._member_types.counts
            values = tuple(values[i] for i in range(before[4], after[4]))
            from .persistence_history_types import member_counts
            counts = member_counts(values)
            # Preserve every possible incoming int/pair policy without walking
            # unchanged alias owners. Empty predecessors remain unsupported.
            if any(prior_counts[n] == before[3] and counts[n] != count for n in (0, 1)):
                raise Unsupported()
            replay.extend(values)
            replay._revision = after[6]
            frozen = replay.prepare_delta().decode(codec)[0]
            wanted = {(c.namespace, codec.encode(c.key)): codec.encode(c.value) for c in frozen}
            if wanted != actual:
                raise Unsupported()
        finally:
            replay._clear_cache()
        for c in frozen:
            marker = c.namespace, codec.encode(c.key)
            old = sources.source(*marker)
            approved[marker] = codec.encode(c.value)
            changes.append((marker, old))
            if old is None:
                new_rows[marker] = approved[marker]
                added += 1
            if c.namespace == sequence.NODE_NAMESPACE and c.value[0] == 'leaf':
                if scope._resolve(store, sa, scope.OwnerScope(c.namespace, marker[1])).count:
                    raise Unsupported()
                header_marker = catalog.OWNER_NAMESPACE, codec.encode((c.namespace, c.key))
                header = by_key.get(header_marker)
                old_header = sources.source(*header_marker)
                if old is None:
                    empty = (None, 0, _framed_sha(b'identity-owner-empty-v1'))
                    if old_header is not None:
                        h = codec.decode(old_header.payload)
                        if type(h) is not tuple or len(h) != 9 or h[:3] != ('identity-owner/v1', False, 'lazy') or h[4] != 1 or h[6:] != empty:
                            raise Unsupported()
                    expected = codec.encode(('identity-owner/v1', True, 'lazy', request.pin.captured_head+1,
                        1, _framed_sha(b'lazy-payload-v1', approved[marker]), *empty))
                    if header is None or header['payload'] != expected or header['change'].delete or header['change'].reinsertion or header['change'].record_schema != 1 or header['memberships_blob'] != codec.encode(()):
                        raise Unsupported()
                    new_rows[header_marker] = expected
                    added += old_header is None
        backing_changes.append((incarnation, parent.payload, item['payload']))
    OrderedSeekMap(store.db, b'').create_schema()
    facts = list(request.tail_facts or request.facts)
    child_root, sequence_root = request.tail_child_root, sa.roots[5]
    directories = {4: child_root, 5: sequence_root}
    roots = {}
    for (ns, typed), old in changes:
        for index, locator in ((4, scope._child_locator), (5, scope._sequence_locator)):
            located = locator(ns, typed)
            if located is None:
                continue
            selected, position = located
            domain = scope._seek_domain(store, selected)
            seek = OrderedSeekMap(store.db, domain)
            root = roots.get(selected, scope._resolve(store, sa, selected))
            expected = None if old is None else scope._child_member(domain, position)
            if seek.get(root, position) != expected:
                raise StoreIntegrityError('sequence predecessor child scope disagrees')
            root = seek.set(root, position, scope._child_member(domain, position))
            roots[selected] = root
            directories[index] = scope._map(store, index).set(directories[index], scope._scope_key(selected),
                scope._write_descriptor(store, selected, root))
    for incarnation, before, after in backing_changes:
        key, typed = incarnation.to_bytes(8, 'big'), codec.encode(incarnation)
        for index, label, wanted, replacement in (
            (0, b'backing-inventory', _digest(b'ate-world-backing/1', b'sequence', sequence.DESCRIPTOR_NAMESPACE.encode(), typed, world._structural_descriptor(codec, 'sequence', before)),
             _digest(b'ate-world-backing/1', b'sequence', sequence.DESCRIPTOR_NAMESPACE.encode(), typed, world._structural_descriptor(codec, 'sequence', after))),
            (4, b'backing-orders', _digest(b'ate-world-history-order/1', b'sequence', before), _digest(b'ate-world-history-order/1', b'sequence', after))):
            mapping = world._map(store, label)
            if mapping.get(facts[index], key) != wanted:
                raise StoreIntegrityError('sequence predecessor lacks semantic backing authority')
            facts[index] = mapping.set(facts[index], key, replacement)
    return tuple(facts), directories[4], directories[5], approved, new_rows, added
