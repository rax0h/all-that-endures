from ate_sim.persistence_lazy_nested_history import LazyHistoryList
import pytest

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.materials import MaterialLot, CraftedItem
from ate_sim.persistence_lazy import (
    LazyMaterialActiveIndexTable,
    LazyMaterialItemTable,
    LazyMaterialLotIndexTable,
    LazyMaterialLotTable,
    LazyTrackedIdList,
    LazyTrackedSet,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-material-tests"


def material_world(count, *, active=8, buckets=1):
    world = World(843000)
    for lot_id in range(1, count + 1):
        sid = 1 + ((lot_id - 1) % buckets)
        quantity = 10.0 + (lot_id % 3)
        lot = MaterialLot(
            lot_id,
            "ore" if lot_id % 2 else "timber",
            quantity,
            .25 + (lot_id % 11) / 20.0,
            sid,
            1,
            0,
            lot_id,
            "person",
            1,
            ("earth resonance",) if lot_id % 7 == 0 else (),
            0.0,
            [lot_id * 10] if lot_id % 13 == 0 else [],
            lot_id % 3,
        )
        if lot_id > active:
            lot.consumed = lot.quantity
        world.materials.lots[lot_id] = lot
        world.materials.lot_index.setdefault(sid, []).append(lot_id)
        if lot_id <= active:
            world.materials.active_lot_index.setdefault(sid, set()).add(
                lot_id
            )
    world.materials.next_lot = count + 1

    for item_id in range(1, min(5, count) + 1):
        world.materials.items[item_id] = CraftedItem(
            item_id,
            "metalwork",
            .5 + item_id / 20.0,
            "common",
            1,
            1,
            0,
            10000 + item_id,
            (item_id,),
            (),
            "person",
            1,
            0,
            False,
        )
    world.materials.next_item = min(5, count) + 1
    return world


def converted(tmp_path, count, *, active=8, buckets=1, name="materials"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        material_world(count, active=active, buckets=buckets),
        source,
        rules_id=RULES,
    )
    result = convert_cold_to_lazy(
        source, destination, rules_id=RULES
    )
    assert result["source_preserved"] is True
    assert result["material_lots"] == count
    return destination


def test_material_open_is_lazy_and_active_membership_needs_no_lot_bodies(tmp_path):
    destination = converted(tmp_path, 400, active=8)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.materials
        assert isinstance(state.lots, LazyMaterialLotTable)
        assert isinstance(state.items, LazyMaterialItemTable)
        assert isinstance(state.lot_index, LazyMaterialLotIndexTable)
        assert isinstance(
            state.active_lot_index, LazyMaterialActiveIndexTable
        )
        assert state.lots.diagnostics()["material_lot_payload_loads"] == 0
        assert state.items.diagnostics()["payload_loads"] == 0
        assert state.lot_index.diagnostics()["bucket_payload_loads"] == 0
        assert (
            state.active_lot_index.diagnostics()["bucket_payload_loads"]
            == 0
        )

        assert state.lots.active_ids(1) == tuple(range(1, 9))
        assert state.lots.diagnostics()["material_lot_payload_loads"] == 0

        available = state.available(1)
        assert tuple(lot.id for lot in available) == tuple(range(1, 9))
        assert state.lots.diagnostics()["material_lot_payload_loads"] == 8
        assert state.lot_index.diagnostics()["bucket_payload_loads"] == 0
        assert (
            state.active_lot_index.diagnostics()["bucket_payload_loads"]
            == 1
        )


def test_material_direct_mutation_save_reopen_and_noop(tmp_path):
    destination = converted(tmp_path, 20, active=6, name="edit")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.materials
        lot = state.lots[2]
        item = state.items[2]
        lot.owner_id = 77
        lot.quality += .125
        item.quality += .25
        item.owner_id = 88
        generation = session.save()

        before = session.store.diagnostics().payload_writes
        assert session.save() == generation
        assert session.store.diagnostics().payload_writes == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        lot = reopened.world.materials.lots[2]
        item = reopened.world.materials.items[2]
        assert lot.owner_id == 77
        assert lot.quality == pytest.approx(.35 + .125)
        assert item.owner_id == 88
        assert item.quality == pytest.approx(.6 + .25)


def test_retained_material_transfer_list_rehydrates_evicted_lot(tmp_path):
    destination = converted(tmp_path, 400, active=8, name="retained-transfer")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        lots = session.world.materials.lots
        lot = lots[1]
        transfers = lot.transfers
        assert isinstance(transfers, LazyHistoryList)
        for key in range(2, 401):
            lots[key]
        assert not dict.__contains__(lots, 1)

        transfers.append(991)
        assert dict.__contains__(lots, 1)
        assert lots[1] is lot
        assert lots[1].transfers is transfers
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.materials.lots[1].transfers == [991]


def test_create_consume_and_membership_publish_together(tmp_path):
    destination = converted(tmp_path, 4, active=4, name="create-consume")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.materials
        created = state.create_lot(
            "ore", 5.0, .9, 1, 1, 2, 9001, ("glow",), 2
        )
        assert created.id == 5
        assert state.lots.active_ids(1) == (1, 2, 3, 4, 5)
        assert state.lots.active_rank_ids(1, 2) == (2, 5)

        state.consume(created, created.quantity)
        assert 5 not in state.active_lot_index[1]
        assert state.lots.active_ids(1) == (1, 2, 3, 4)
        assert state.lots.active_rank_ids(1, 2) == (2,)
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        state = reopened.world.materials
        assert state.lots[5].consumed == pytest.approx(5.0)
        assert 5 not in state.active_lot_index[1]
        assert state.lots.active_ids(1) == (1, 2, 3, 4)


def test_retained_material_index_buckets_survive_eviction_and_save(tmp_path):
    destination = converted(
        tmp_path, 320, active=320, buckets=320, name="index-retained"
    )
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.materials
        lot_bucket = state.lot_index[1]
        active_bucket = state.active_lot_index[1]
        assert isinstance(lot_bucket, LazyTrackedIdList)
        assert isinstance(active_bucket, LazyTrackedSet)

        for sid in range(2, 321):
            state.lot_index[sid]
            state.active_lot_index[sid]
        assert not dict.__contains__(state.lot_index, 1)
        assert not dict.__contains__(state.active_lot_index, 1)

        lot_bucket.append(999001)
        active_bucket.add(999002)
        assert dict.__contains__(state.lot_index, 1)
        assert dict.__contains__(state.active_lot_index, 1)
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.materials.lot_index[1] == [1, 999001]
        assert reopened.world.materials.active_lot_index[1] == {
            1, 999002
        }


def test_material_delete_reinsert_preserves_order_and_incarnation(tmp_path):
    destination = converted(tmp_path, 5, active=5, name="reinsert")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        lots = session.world.materials.lots
        lot = lots[1]
        before = session.store.read_identity_occurrence(
            session.pin, "world.materials.lots", 1, ()
        ).incarnation_id
        del lots[1]
        lots[1] = lot
        assert tuple(lots) == (2, 3, 4, 5, 1)
        session.save()
        after = session.store.read_identity_occurrence(
            session.pin, "world.materials.lots", 1, ()
        ).incarnation_id
        assert after == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert tuple(reopened.world.materials.lots) == (2, 3, 4, 5, 1)


def test_material_selection_helpers_remain_ordered_and_do_not_touch_lot_index(
    tmp_path,
):
    destination = converted(tmp_path, 60, active=12, name="selection")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.materials
        best = state.best_available(1)
        expected = min(
            state.available(1), key=state._selection_key
        )
        assert best.id == expected.id
        assert state.magical_available_count(1) == sum(
            bool(lot.magical_properties) for lot in state.available(1)
        )
        assert tuple(state.selection_ids(1)) == tuple(range(1, 13))
        assert state.crafting_capacity(1, 100) > 0
        assert state.lot_index.diagnostics()["bucket_payload_loads"] == 0


@pytest.mark.parametrize("count", [1000, 10000])
def test_material_cold_history_does_not_increase_ordinary_open_loads(
    tmp_path, count
):
    destination = converted(
        tmp_path, count, active=8, name=f"scale-{count}"
    )
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.materials
        assert len(state.lots) == count
        assert state.lots.diagnostics()["material_lot_payload_loads"] == 0
        assert state.items.diagnostics()["payload_loads"] == 0
        assert state.lot_index.diagnostics()["bucket_payload_loads"] == 0
        assert (
            state.active_lot_index.diagnostics()["bucket_payload_loads"]
            == 0
        )

        assert state.lots.active_ids(1) == tuple(range(1, 9))
        assert state.lots.diagnostics()["material_lot_payload_loads"] == 0


def test_material_save_precommit_failure_resolves_old_and_retries(tmp_path):
    destination = converted(tmp_path, 30, active=8, name="failure")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        start = session.pin.captured_head
        lot = session.world.materials.lots[3]
        lot.quality += .2

        def fail(phase):
            if phase == "during_version_writes":
                raise OSError("material publication failed")

        session.store._phase_hook = fail
        with pytest.raises(OSError, match="material publication failed"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"

        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start
        assert session.diagnostics()["state"] == "active"
        assert session.save() == start + 1

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.materials.lots[3].quality == pytest.approx(
            .4 + .2
        )


def test_materializing_detach_returns_plain_portable_material_containers(
    tmp_path,
):
    destination = converted(tmp_path, 300, active=8, name="detach")
    session = open_lazy_world_session(destination, rules_id=RULES)
    retained = session.world.materials.lots[1]
    transfers = retained.transfers
    for key in range(2, 301):
        session.world.materials.lots[key]
    transfers.append(7001)

    detached = session.detach(materialize_history=True)
    assert type(detached.materials.lots) is dict
    assert type(detached.materials.items) is dict
    assert type(detached.materials.lot_index) is dict
    assert type(detached.materials.active_lot_index) is dict
    assert detached.materials.lots[1] is retained
    assert type(detached.materials.lots[1].transfers) is list
    assert detached.materials.lots[1].transfers == [7001]
    assert type(detached.materials.lot_index[1]) is list
    assert type(detached.materials.active_lot_index[1]) is set

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert type(restored.materials.lots[1].transfers) is list
