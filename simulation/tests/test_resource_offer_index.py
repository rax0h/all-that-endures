from copy import deepcopy
from unittest.mock import patch

from ate_sim.checkpoint import dumps, loads
from ate_sim.core import Layer, Ref
from ate_sim.magic_economy import _trainee_resources
from ate_sim.magic_resources import (
    MagicAspiration,
    _circulation_stock,
    absorb_essence_resource,
    resource_price,
)
from ate_sim.resource_offers import ordered_resource_offers
from ate_sim import resource_offers
from test_society_cohorts import Willing, resource, trainee_world


def legacy_offers(world, sid, people):
    offers = world.magic_resources.inventory("settlement", sid)
    for holder in people:
        if holder.alive and holder.age >= 16:
            offers.extend(_circulation_stock(world, holder)[2])
    return {
        kind: sorted(
            (r for r in offers if r.kind == kind),
            key=lambda r: (resource_price(r), r.id),
        )
        for kind in ("essence", "awakening_stone")
    }


def ids(offers):
    return {kind: [r.id for r in values] for kind, values in offers.items()}


def indexed_world():
    w, p, society, branch, asset = trainee_world()
    people = [q for q in w.people.values() if q.alive and q.settlement == p.settlement]
    seller = next(q for q in people if q.id != p.id and q.age >= 16)
    w.magic_resources.aspirations[seller.id] = MagicAspiration(
        1, 3, 20, "seller", 0, completion_goal=True
    )
    for key in ("fire", "water", "wind"):
        resource(w, p, "essence", key, "settlement", p.settlement)
    resource(w, p, "essence", "life", owner_id=seller.id)
    for n in range(12):
        r = resource(w, p, "awakening_stone", "eyes", owner_id=seller.id)
        if n % 3 == 0:
            r.rarity = "Rare"
    return w, p, seller, people


def test_incremental_offers_match_legacy_through_inventory_and_demand_changes():
    base, p, seller, people = indexed_world()
    control = deepcopy(base)
    indexed = deepcopy(base)
    control_people = [control.people[q.id] for q in people]
    indexed_people = [indexed.people[q.id] for q in people]

    assert ids(ordered_resource_offers(indexed, p.settlement, indexed_people)) == ids(
        legacy_offers(control, p.settlement, control_people)
    )

    # Exercise both ownership directions while the old source is still cached.
    person_rid = next(
        r.id for r in indexed.magic_resources.inventory("person", seller.id)
        if r.kind == "awakening_stone"
    )
    settlement_rid = next(
        r.id for r in indexed.magic_resources.inventory("settlement", p.settlement)
        if r.kind == "essence"
    )
    for world in (control, indexed):
        q = world.people[seller.id]
        e = world.emit(
            "test_resource_transfer",
            Layer.SOCIETY,
            location=Ref("settlement", q.settlement),
        )
        world.magic_resources.transfer(
            person_rid, "settlement", q.settlement, e.id, q.settlement
        )
        e = world.emit(
            "test_resource_transfer",
            Layer.SOCIETY,
            location=Ref("settlement", q.settlement),
        )
        world.magic_resources.transfer(
            settlement_rid, "person", q.id, e.id, q.settlement
        )
    assert ids(ordered_resource_offers(indexed, p.settlement, indexed_people)) == ids(
        legacy_offers(control, p.settlement, control_people)
    )

    # An unchanged second query must not reconstruct holder circulation.
    expected = ids(ordered_resource_offers(indexed, p.settlement, indexed_people))
    with patch.object(
        resource_offers,
        "_circulation_stock",
        side_effect=AssertionError("reconstructed unchanged holder offers"),
    ):
        assert ids(ordered_resource_offers(indexed, p.settlement, indexed_people)) == expected

    # Ownership mutation invalidates only the affected inventory token.
    for world in (control, indexed):
        q = world.people[seller.id]
        e = world.emit(
            "test_resource_origin",
            Layer.REALITY,
            location=Ref("settlement", q.settlement),
        )
        world.magic_resources.create(
            "awakening_stone", "eyes", "Common", world.year, q.settlement,
            "person", q.id, e.id,
        )
    assert ids(ordered_resource_offers(indexed, p.settlement, indexed_people)) == ids(
        legacy_offers(control, p.settlement, control_people)
    )

    # Compatibility mutation changes surplus membership without changing
    # ownership; the holder signature must still refresh the index.
    control.magic_resources.aspirations[seller.id].desired_base_essences = 0
    indexed.magic_resources.aspirations[seller.id].desired_base_essences = 0
    assert ids(ordered_resource_offers(indexed, p.settlement, indexed_people)) == ids(
        legacy_offers(control, p.settlement, control_people)
    )


def test_offer_index_is_derived_and_rebuilds_after_checkpoint():
    w, p, seller, people = indexed_world()
    before = ids(ordered_resource_offers(w, p.settlement, people))
    assert hasattr(w.magic_resources, "_query_offer_books")
    restored = loads(dumps(w))
    assert not hasattr(restored.magic_resources, "_query_offer_books")
    restored_people = [restored.people[q.id] for q in people]
    assert ids(ordered_resource_offers(restored, p.settlement, restored_people)) == before


def test_indexed_trainee_procurement_matches_legacy_snapshot_and_outcome():
    w, p, seller, people = indexed_world()
    # Put the trainee on a real partial path so both essences and stones matter.
    for world in (w,):
        for key in ("fire", "water", "wind"):
            held = resource(world, world.people[p.id], "essence", key)
            absorb_essence_resource(world, p.id, held.id)
    legacy = deepcopy(w)
    indexed = deepcopy(w)
    legacy_people = [legacy.people[q.id] for q in people]
    indexed_people = [indexed.people[q.id] for q in people]
    legacy_p = legacy.people[p.id]
    indexed_p = indexed.people[p.id]
    legacy.currency.credit(legacy_p.id, {"iron": 80})
    indexed.currency.credit(indexed_p.id, {"iron": 80})

    supply = legacy_offers(legacy, legacy_p.settlement, legacy_people)
    _trainee_resources(legacy, legacy_p, legacy_people, supply, Willing())
    _trainee_resources(indexed, indexed_p, indexed_people, {}, Willing())

    assert legacy.digest() == indexed.digest()
