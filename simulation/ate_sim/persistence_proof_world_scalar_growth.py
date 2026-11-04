"""Bounded append-only scalar map/set extents, without walking old entries."""
from dataclasses import replace

from .incremental_store import Membership, StoreIntegrityError, _framed_sha
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY, ENTRY_NAMESPACE as ENTRIES, immutable_value
from .persistence_history_types import NAMESPACE as TYPES, TAG, member_counts
from .persistence_proof_world_sequence import _Sources, Unsupported
from . import persistence_lazy_identity_catalog as catalog
from . import persistence_proof_scope as scope
from . import persistence_proof_world as world

MAX_BACKINGS = 16
MAX_APPENDED = 128
MAX_BYTES = 4 * 1048576


def certified(request, namespace, typed):
    return (namespace, typed) in (request.scalar_rows or ())


def prepare(store, request, versions):
    request.scalar_rows = frozenset()
    if len(versions) > 512:
        return
    try:
        result = _prepare(store, request, versions)
    except Unsupported:
        return
    if result is None:
        return
    facts, directory, approved, new_rows, added = result
    request.tail_facts, request.tail_child_root = facts, directory
    request.scalar_rows = frozenset(approved)
    request.tail_new.update(new_rows)
    request.tail_added += added


def _prepare(store, request, versions):
    codec, sa = store.codec, request.pairs[1][0]
    consumed = sum(len(i['namespace'].encode()) + len(i['typed_key']) +
                   len(i['payload'] or b'') + len(i['memberships_blob']) for i in versions)
    if consumed > MAX_BYTES:
        raise Unsupported()
    # Share the sequence proof's bounded authenticated predecessor reader.
    # No replay or raw read capability is used here.
    sources = _Sources(store, request, consumed)
    rows = {(i['namespace'], i['typed_key']): i for i in versions}
    approved, new_rows, backings = {}, {}, []
    appended = added = 0
    empty = (None, 0, _framed_sha(b'identity-owner-empty-v1'))
    def clean(i):
        return not i['change'].delete and not i['change'].reinsertion and i['change'].record_schema == 1
    for item in versions:
        if item['namespace'] != HISTORY or not clean(item):
            continue
        after = codec.decode(item['payload'])
        if type(after) is not tuple or not after or after[0] not in ('map', 'set'):
            continue
        inc = codec.decode(item['typed_key'])
        if type(inc) is not int or not 0 < inc < sa.next_incarnation_id:
            continue
        parent = sources.source(HISTORY, item['typed_key'])
        if parent is None:
            raise Unsupported()
        before = codec.decode(parent.payload)
        kind = after[0]
        world.target._validate_descriptor(kind, inc, before)
        world.target._validate_descriptor(kind, inc, after)
        if before[0] != kind or before[1] == 0 or after[1] <= before[1]:
            continue
        if item['memberships_blob'] != codec.encode(()) or after[1]-before[1] != after[2]-before[2]:
            raise Unsupported()
        appended += after[1]-before[1]
        if appended > MAX_APPENDED or len(backings) >= MAX_BACKINGS:
            raise Unsupported()
        entries, keys, ordinals = [], [], set()
        for candidate in versions:
            if candidate['namespace'] != ENTRIES:
                continue
            key = codec.decode(candidate['typed_key'])
            adapter = world.AUXILIARY_OWNER_FAMILIES[ENTRIES]
            adapter.validate_key(key)
            if key[0] != inc:
                continue
            if not clean(candidate):
                raise Unsupported()
            value = codec.decode(candidate['payload'])
            change = replace(candidate['change'], key=key, value=value,
                memberships=tuple(Membership(*m) for m in codec.decode(candidate['memberships_blob'])))
            adapter.validate_source(change, 'lazy', codec)
            if value[0] < before[2]:
                continue  # Existing map values remain under the value validator.
            if (not immutable_value(value[1]) or not immutable_value(value[2])
                    or kind == 'set' and value[2] is not None or value[0] in ordinals):
                raise Unsupported()
            marker = ENTRIES, candidate['typed_key']
            if sources.source(*marker) is not None:
                raise Unsupported()
            if scope._resolve(store, sa, scope.OwnerScope(*marker)).count:
                raise Unsupported()
            hkey = catalog.OWNER_NAMESPACE, codec.encode((ENTRIES, key))
            header, prior = rows.get(hkey), sources.source(*hkey)
            if prior is not None:
                old = codec.decode(prior.payload)
                if type(old) is not tuple or len(old) != 9 or old[:3] != ('identity-owner/v1', False, 'lazy') or old[4] != 1 or old[6:] != empty:
                    raise Unsupported()
            expected = codec.encode(('identity-owner/v1', True, 'lazy', request.pin.captured_head+1,
                1, _framed_sha(b'lazy-payload-v1', candidate['payload']), *empty))
            if header is None or not clean(header) or header['payload'] != expected or header['memberships_blob'] != codec.encode(()):
                raise Unsupported()
            approved[marker] = candidate['payload']
            new_rows[marker], new_rows[hkey] = candidate['payload'], expected
            added += 1 + (prior is None)
            entries.append(candidate); keys.append(value[1]); ordinals.add(value[0])
        if ordinals != set(range(before[2], after[2])) or len(entries) != after[1]-before[1]:
            raise Unsupported()
        prior_types = sources.source(TYPES, item['typed_key'])
        types = rows.get((TYPES, item['typed_key']))
        if prior_types is None or types is None or not clean(types) or types['memberships_blob'] != codec.encode(()):
            raise Unsupported()
        counts = codec.decode(prior_types.payload)
        if (type(counts) is not tuple or len(counts) != 3 or counts[:2] != (TAG, kind)
                or type(counts[2]) is not tuple or len(counts[2]) != 3
                or any(type(n) is not int or n < 0 for n in counts[2]) or sum(counts[2]) != before[1]):
            raise StoreIntegrityError('scalar growth predecessor type counts disagree')
        delta = member_counts(keys)
        if any(counts[2][n] == before[1] and delta[n] != len(keys) for n in (0, 1)):
            raise Unsupported()
        if types['payload'] != codec.encode((TAG, kind, tuple(a+b for a, b in zip(counts[2], delta)))):
            raise Unsupported()
        approved[HISTORY, item['typed_key']] = item['payload']
        approved[TYPES, item['typed_key']] = types['payload']
        backings.append((inc, kind, item['typed_key'], parent.payload, item['payload'], before[1], entries))
    if not backings:
        return None
    OrderedSeekMap(store.db, b'').create_schema()
    facts, directory = list(request.tail_facts or request.facts), request.tail_child_root
    for inc, kind, typed, before, after, size, entries in backings:
        selected = scope.ChildScope(inc)
        domain = scope._seek_domain(store, selected)
        seek, root = OrderedSeekMap(store.db, domain), scope._resolve(store, sa, selected)
        if root.count != size:
            raise StoreIntegrityError('scalar growth predecessor child extent disagrees')
        for entry in entries:
            _selected, position = scope._child_locator(ENTRIES, entry['typed_key'])
            if seek.get(root, position) is not None:
                raise StoreIntegrityError('scalar growth entry lacks accepted child absence')
            root = seek.set(root, position, scope._child_member(domain, position))
        directory = scope._map(store, 4).set(directory, scope._scope_key(selected), scope._write_descriptor(store, selected, root))
        for index, label, tag in ((0, b'backing-inventory', b'ate-world-backing/1'), (4, b'backing-orders', b'ate-world-history-order/1')):
            mapping, position = world._map(store, label), inc.to_bytes(8, 'big')
            def fact(payload):
                return (_digest(tag, kind.encode(), HISTORY.encode(), typed, payload) if index == 0
                        else _digest(tag, kind.encode(), payload))
            if mapping.get(facts[index], position) != fact(before):
                raise StoreIntegrityError('scalar growth lacks accepted semantic backing')
            facts[index] = mapping.set(facts[index], position, fact(after))
    return tuple(facts), directory, approved, new_rows, added
