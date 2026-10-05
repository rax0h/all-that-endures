import pytest

from ate_sim import checkpoint

from ate_sim.core import World
from ate_sim.magic_resources import MagicResource
from ate_sim.persistence_lazy import (
    LazyResourceTable,
    LazyTrackedList,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-resource-tests"


def resource_world(count):
    world = World(843000)
    for rid in range(1, count + 1):
        resource = MagicResource(
            rid,
            "essence",
            "fire",
            "common",
            1,
            "person",
            rid,
            0,
            None,
        )
        world.magic_resources.resources[rid] = resource
        world.magic_resources.owner_index[("person", rid)] = {rid}
    world.magic_resources.next_id = count + 1
    return world


def converted(tmp_path, count, name="resources"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        resource_world(count), source, rules_id=RULES
    )
    convert_cold_to_lazy(source, destination, rules_id=RULES)
    return destination


def test_resources_open_zero_payloads_point_read_one_and_owner_query(tmp_path):
    destination = converted(tmp_path, 400)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.resources
        assert isinstance(table, LazyResourceTable)
        assert table.diagnostics()["resource_payload_loads"] == 0
        assert len(table) == 400
        assert table.owner_ids("person", 300) == (300,)
        # Membership lookup does not need the resource body.
        assert table.diagnostics()["resource_payload_loads"] == 0
        item = table[300]
        assert isinstance(item.transfers, LazyTrackedList)
        assert table.diagnostics()["resource_payload_loads"] == 1


def test_retained_transfer_list_rehydrates_evicted_resource_and_saves(tmp_path):
    destination = converted(tmp_path, 400, "retained-child")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.resources
        resource = table[1]
        transfers = resource.transfers
        for key in range(2, 401):
            table[key]
        assert not dict.__contains__(table, 1)

        transfers.append(991)
        assert dict.__contains__(table, 1)
        assert table[1].transfers is transfers
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.magic_resources.resources[1].transfers == [991]


def test_resource_transfer_consume_membership_and_reopen(tmp_path):
    destination = converted(tmp_path, 4, "transfer-consume")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.magic_resources
        table = state.resources
        assert table.owner_ids("person", 1) == (1,)

        state.transfer(1, "person", 2, 101, location=2)
        assert table.owner_ids("person", 1) == ()
        assert table.owner_ids("person", 2) == (1, 2)
        assert state.owner_index.get(("person", 1), set()) == set()
        assert state.owner_index[("person", 2)] == {1, 2}
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        state = reopened.world.magic_resources
        item = state.resources[1]
        assert item.owner_id == 2
        assert item.location == 2
        assert item.transfers == [101]
        assert state.resources.owner_ids("person", 2) == (1, 2)

        state.consume(1, 2, 5, 102)
        assert state.resources.owner_ids("person", 2) == (2,)
        assert state.owner_index[("person", 2)] == {2}
        reopened.save()

    with open_lazy_world_session(destination, rules_id=RULES) as final:
        item = final.world.magic_resources.resources[1]
        assert item.consumed_year == 5
        assert item.consumed_by == 2
        assert item.consumed_event == 102
        assert final.world.magic_resources.resources.owner_ids(
            "person", 2
        ) == (2,)


def test_resource_create_and_noop_save(tmp_path):
    destination = converted(tmp_path, 2, "create")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.magic_resources
        created = state.create(
            "awakening_stone",
            "might",
            "common",
            3,
            location=1,
            owner_kind="person",
            owner_id=9,
            origin_event=77,
        )
        assert created.id == 3
        assert state.resources.owner_ids("person", 9) == (3,)
        generation = session.save()
        before = session.store.diagnostics().payload_writes
        assert session.save() == generation
        assert session.store.diagnostics().payload_writes == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        item = reopened.world.magic_resources.resources[3]
        assert item.kind == "awakening_stone"
        assert item.owner_id == 9


@pytest.mark.parametrize("count", [1000, 10000])
def test_resource_open_cost_does_not_decode_resource_history(tmp_path, count):
    destination = converted(tmp_path, count, f"scale-{count}")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.resources
        assert len(table) == count
        assert table.diagnostics()["resource_payload_loads"] == 0


def test_resource_materializing_detach_is_portable(tmp_path):
    destination = converted(tmp_path, 300, "detach")
    session = open_lazy_world_session(destination, rules_id=RULES)
    retained = session.world.magic_resources.resources[1]
    transfers = retained.transfers
    transfers.append(7001)
    for key in range(2, 301):
        session.world.magic_resources.resources[key]
    assert not dict.__contains__(
        session.world.magic_resources.resources, 1
    )

    detached = session.detach(materialize_history=True)
    resources = detached.magic_resources.resources
    assert type(resources) is dict
    assert len(resources) == 300
    assert resources[1] is retained
    assert type(resources[1].transfers) is list
    assert resources[1].transfers == [7001]

    data = checkpoint.dumps(detached)
    restored = checkpoint.loads(data)
    assert restored.digest() == detached.digest()
    assert type(restored.magic_resources.resources[1].transfers) is list
