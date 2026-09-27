"""Incremental ordered magical-resource offers for hot Society queries.

This is derived query state only.  It is attached to MagicResourceState under a
_query_ name, so checkpoints omit it and restore from authoritative ownership,
resource and advancement state.

The legacy Society broker assembled local public stock plus every adult holder's
surplus, then sorted each kind by (price, resource id).  This index preserves
that exact snapshot and ordering while refreshing only inventories or holder
compatibility states that changed.
"""
from bisect import bisect_left, insort

from .magic_resources import _aspiration, _circulation_stock, resource_price


_EMPTY = object()
_KINDS = ("essence", "awakening_stone")


def _inventory_token(resources, key):
    cache = getattr(resources, "_query_inventory", {})
    kinds = cache.get(key)
    if kinds is not None and None in kinds:
        return kinds[None]
    if key not in resources.owner_index:
        return _EMPTY
    return None


def _holder_signature(world, person):
    aspiration = _aspiration(world, person)
    path = world.advancement.path(person.id)
    path_state = None if path is None else (
        tuple(path.base_essences), len(path.abilities), path.capacity
    )
    return (
        person.alive,
        person.age >= 16,
        person.settlement,
        aspiration.desired_base_essences,
        aspiration.desired_abilities,
        path_state,
    )


def _entry(resource):
    return (
        resource.kind,
        resource_price(resource),
        resource.id,
        resource.owner_kind,
        resource.owner_id,
    )


class _OfferBook:
    def __init__(self):
        self.rows = {kind: [] for kind in _KINDS}
        self.members = {kind: {} for kind in _KINDS}

    def _remove_row(self, kind, row):
        rows = self.rows[kind]
        pos = bisect_left(rows, row)
        if pos >= len(rows) or rows[pos] != row:
            raise AssertionError("resource offer index lost ordered membership")
        rows.pop(pos)

    def add(self, entries):
        for kind, price, rid, owner_kind, owner_id in entries:
            if kind not in self.rows:
                continue
            row = (price, rid)
            current = self.members[kind].get(rid)
            source = (owner_kind, owner_id)
            if current is not None:
                current_row, current_source = current
                if current_row == row and current_source == source:
                    continue
                # Ownership may have changed before the stale owner's cache is
                # refreshed. Replace the derived row with current authority;
                # the stale source is then unable to remove this membership.
                self._remove_row(kind, current_row)
            insort(self.rows[kind], row)
            self.members[kind][rid] = (row, source)

    def remove(self, entries):
        for kind, _price, rid, owner_kind, owner_id in entries:
            if kind not in self.rows:
                continue
            current = self.members[kind].get(rid)
            if current is None:
                continue
            row, source = current
            if source != (owner_kind, owner_id):
                continue
            self.members[kind].pop(rid)
            self._remove_row(kind, row)

    def snapshot(self, resources):
        return {
            kind: [resources.resources[rid] for _price, rid in self.rows[kind]]
            for kind in _KINDS
        }


class _ResourceOfferIndex:
    def __init__(self):
        self.books = {}
        self.settlements = {}
        self.people = {}
        self.owners_by_settlement = {}

    def _book(self, sid):
        return self.books.setdefault(sid, _OfferBook())

    def _drop_person(self, pid):
        cached = self.people.pop(pid, None)
        if cached is None:
            return
        sid, _token, _signature, entries = cached
        self._book(sid).remove(entries)
        owners = self.owners_by_settlement.get(sid)
        if owners is not None:
            owners.discard(pid)
            if not owners:
                self.owners_by_settlement.pop(sid, None)

    def _refresh_settlement(self, world, sid):
        resources = world.magic_resources
        key = ("settlement", sid)
        token = _inventory_token(resources, key)
        cached = self.settlements.get(sid)
        if cached is not None and token is cached[0]:
            return
        if cached is not None:
            self._book(sid).remove(cached[1])
        inventory = resources.inventory("settlement", sid)
        token = _inventory_token(resources, key)
        entries = tuple(_entry(resource) for resource in inventory if resource.kind in _KINDS)
        self._book(sid).add(entries)
        self.settlements[sid] = (token, entries)

    def _refresh_person(self, world, sid, person):
        resources = world.magic_resources
        key = ("person", person.id)
        token = _inventory_token(resources, key)
        signature = _holder_signature(world, person)
        cached = self.people.get(person.id)
        if (
            cached is not None
            and cached[0] == sid
            and token is cached[1]
            and signature == cached[2]
        ):
            return
        self._drop_person(person.id)
        # Use the established circulation selector so offer compatibility is
        # exactly the same as the pre-index broker.
        surplus = _circulation_stock(world, person)[2]
        token = _inventory_token(resources, key)
        entries = tuple(_entry(resource) for resource in surplus if resource.kind in _KINDS)
        self._book(sid).add(entries)
        self.people[person.id] = (sid, token, signature, entries)
        self.owners_by_settlement.setdefault(sid, set()).add(person.id)

    def offers(self, world, sid, people):
        self._refresh_settlement(world, sid)
        adults = {p.id for p in people if p.alive and p.age >= 16}
        for pid in tuple(self.owners_by_settlement.get(sid, ())):
            if pid not in adults:
                self._drop_person(pid)
        # Preserve legacy aspiration/circulation initialization order by walking
        # the caller's people sequence rather than the set above.
        for person in people:
            if person.alive and person.age >= 16:
                self._refresh_person(world, sid, person)
        return self._book(sid).snapshot(world.magic_resources)


def ordered_resource_offers(world, sid, people):
    resources = world.magic_resources
    index = getattr(resources, "_query_offer_books", None)
    if index is None:
        index = resources._query_offer_books = _ResourceOfferIndex()
    return index.offers(world, sid, people)
