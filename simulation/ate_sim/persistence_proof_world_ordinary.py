"""Authenticated unsealed event and packed action append shapes only."""
from collections import Counter
from dataclasses import dataclass, replace

from .incremental_store import StoreIntegrityError
from .persistence_proof_content import _integer
from .persistence_proof_nodes import _digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_world_new_backings import Unsupported
from .persistence_proof_world_owner_edits import accepted_placement
from . import persistence_proof_world as world
from . import persistence_proof_scope as scope

MAX_EVENTS = 128
MAX_ACTIONS = 4096


@dataclass
class OrdinaryPlan:
    owners: list
    handled: set
    handled_sources: set
    counts: Counter


def prepare(store, request, ordinary, read, forest):
    from .persistence_adapters import AGENCY_ACTIONS_NAMESPACE as ACTIONS, PACKED_LIST_KEY, PACKED_LIST_PAYLOAD
    from .persistence_session import EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, _decode_tail_descriptor, _validate_suffix_event
    from .persistence_event_ids import RANGE_TAG
    codec, sa = store.codec, request.pairs[1][0]
    rows = {(i['namespace'], i['typed_key']): i for i in ordinary}
    plan = OrdinaryPlan([], set(), set(), Counter())
    facts = list(request.tail_facts or request.facts)
    reserved = 0

    def remaining():
        from .persistence_proof_world_new_backings import MAX_PROJECTIONS
        return MAX_PROJECTIONS - forest.projections - reserved

    def append_owner(change, projection):
        nonlocal reserved
        reserved += len(projection)
        plan.owners.append((change, projection))

    def source(item):
        if item['change'].delete or item['change'].record_schema != 1 or item['memberships']:
            raise Unsupported()
        return replace(item['change'], key=codec.decode(item['typed_key']), value=codec.decode(item['payload']))

    def control(ns, key):
        marker = ns, codec.encode(key)
        item = rows.get(marker)
        if item is None:
            raise Unsupported()
        change = source(item)
        old = read(*marker)
        if old is None:
            raise StoreIntegrityError('ordinary append control lacks accepted predecessor')
        plan.handled.add(marker)
        return codec.decode(old), change.value, old, item['payload']

    actions = rows.get((ACTIONS, codec.encode(PACKED_LIST_KEY)))
    if actions is not None:
        change = source(actions)
        old = read(ACTIONS, actions['typed_key'])
        if old is None:
            raise Unsupported()
        before, after = codec.decode(old), change.value
        if old != actions['payload']:
            if (type(before) is not tuple or len(before) != 2 or type(before[0]) is not int
                    or before[0] != 0 or type(after) is not tuple or len(after) != 2 or after[0] != 0
                    or type(after[0]) is not int):
                raise Unsupported()
            a, b = before[1], after[1]
            if (type(a) is not tuple or len(a) != 2 or a[0] != PACKED_LIST_PAYLOAD or type(a[1]) is not tuple
                    or type(b) is not tuple or len(b) != 2 or b[0] != PACKED_LIST_PAYLOAD or type(b[1]) is not tuple
                    or not len(a[1]) < len(b[1]) <= MAX_ACTIONS or codec.encode(a[1]) != codec.encode(b[1][:len(a[1])])):
                raise Unsupported()
            owner = scope.OwnerScope(ACTIONS, actions['typed_key'])
            if scope._resolve(store, sa, owner).count != len(a[1]):
                raise Unsupported()
            def suffix():
                for i in range(len(a[1]), len(b[1])):
                    # Project only this new action, retaining its absolute path
                    # in the packed owner. The old prefix has accepted authority.
                    for path, inc, kind, fingerprint in world._project(store, ACTIONS, i,
                            (i, b[1][i]), True, record_header=forest.header):
                        yield (('index', i),)+path, inc, kind, fingerprint
            projected = forest.collect(suffix(), limit=remaining())
            if len(projected) != len(b[1])-len(a[1]) or any(p[0] != (('index', i),) or p[1] is not None or p[3] is None for i, p in enumerate(projected, len(a[1]))):
                raise Unsupported()
            append_owner(change, projected)
            marker = ACTIONS, actions['typed_key']
            plan.handled.add(marker); plan.handled_sources.add(marker)
            plan.counts[ACTIONS] += len(b[1])-len(a[1])

    events = []
    for item in ordinary:
        if item['namespace'] != 'world.events':
            continue
        change = source(item)
        if read('world.events', item['typed_key']) is not None:
            # Editing an existing event, even in a new event's batch, is not
            # an append certificate. Keep the checked structural path.
            raise Unsupported()
        events.append((change, item))
    if events:
        if len(events) > MAX_EVENTS:
            raise Unsupported()
        before, after, _old_tail, _tail = control(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY)
        old_tail, tail = _decode_tail_descriptor(before), _decode_tail_descriptor(after)
        if ((old_tail.disk_events, old_tail.sealed_events) != (tail.disk_events, tail.sealed_events)
                or tail.total_events != old_tail.total_events + len(events)):
            raise Unsupported()
        indices = [c.key for c, _ in events]
        if any(type(k) is not int for k in indices) or set(indices) != set(range(old_tail.total_events, tail.total_events)):
            raise StoreIntegrityError('ordinary event append is not contiguous')
        last_year = old_tail.last_event_year
        for change, item in sorted(events, key=lambda pair: pair[0].key):
            if (type(change.value) is not tuple or len(change.value) != 2 or type(change.value[0]) is not int
                    or change.value[0] != change.key):
                raise StoreIntegrityError('ordinary event append envelope disagrees')
            event = _validate_suffix_event(change.value[1], change.key)
            if any(not 1 <= cause < event.id for cause in event.causes):
                raise StoreIntegrityError('ordinary event append has an invalid cause')
            if getattr(event, '_sealed', False) is not False:
                raise Unsupported()
            if last_year is not None and event.year < last_year:
                raise StoreIntegrityError('ordinary event append chronology violation')
            last_year = event.year
            append_owner(change, forest.project(change, ordinary=True, limit=remaining()))
            marker = 'world.events', item['typed_key']
            plan.handled.add(marker); plan.handled_sources.add(marker)
        if tail.last_event_year != last_year:
            raise StoreIntegrityError('ordinary event append last year disagreement')
        before, after, old_ids, new_ids = control('world.event_ids', 0)
        if (codec.encode(before) != codec.encode((0, (RANGE_TAG, old_tail.total_events)))
                or codec.encode(after) != codec.encode((0, (RANGE_TAG, tail.total_events)))):
            raise Unsupported()
        owner = scope.OwnerScope('world.event_ids', codec.encode(0))
        if scope._resolve(store, sa, owner).count != 1:
            raise Unsupported()
        inc = accepted_placement(store, request, owner.namespace, owner.typed_key, codec.encode(()))
        if inc is None:
            raise StoreIntegrityError('ordinary Event-ID facade lacks its root')
        position = inc.to_bytes(8, 'big')
        for index, label, wanted, replacement in (
            (0, b'backing-inventory', _digest(b'ate-world-backing/1', b'event-ids', b'world.event_ids', codec.encode(0), old_ids),
             _digest(b'ate-world-backing/1', b'event-ids', b'world.event_ids', codec.encode(0), new_ids)),
            (4, b'backing-orders', _digest(b'ate-world-history-order/1', b'event-ids', old_ids),
             _digest(b'ate-world-history-order/1', b'event-ids', new_ids))):
            mapping = world._map(store, label)
            if mapping.get(facts[index], position) != wanted:
                raise StoreIntegrityError('ordinary Event-ID facade lacks accepted backing authority')
            facts[index] = mapping.set(facts[index], position, replacement)
        before, after, _old, _new = control('world.next_event', 0)
        if codec.encode(before) != codec.encode((0, old_tail.total_events+1)) or codec.encode(after) != codec.encode((0, tail.total_events+1)):
            raise StoreIntegrityError('ordinary event append next ID disagreement')
        plan.handled_sources.add(('world.event_ids', codec.encode(0)))
        plan.counts.update({'world.events':len(events), 'world.event_ids':len(events)})
        domain = _digest(b'ate-world-ordinary-order-domain/1', store.store_identity.encode(), _integer(codec.version, 1))
        seek = OrderedSeekMap(store.db, domain)
        seek.create_schema()
        root = facts[3]
        for change, item in events:
            ns = change.namespace.encode()
            position = len(ns).to_bytes(4, 'big') + ns + change.key.to_bytes(8, 'big') + item['typed_key']
            if seek.get(root, position) is not None:
                raise StoreIntegrityError('ordinary event append lacks accepted order absence')
            root = seek.set(root, position, _digest(b'ate-world-ordinary-order-member/1', position))
        facts[3] = root
    request.tail_facts = tuple(facts)
    return plan
