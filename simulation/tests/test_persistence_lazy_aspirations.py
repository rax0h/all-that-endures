import pytest

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.incremental_store import StoreError
from ate_sim.magic_resources import MagicAspiration
from ate_sim.persistence_lazy import (
    ASPIRATION_NAMESPACE,
    LazyAspirationTable,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-aspiration-tests"


def aspiration(value=0.5, *, reason="curiosity"):
    return MagicAspiration(
        value,
        3,
        20,
        reason,
        0,
        urgency=0.4,
    )


def aspiration_world(count):
    world = World(843000)
    for pid in range(1, count + 1):
        world.magic_resources.aspirations[pid] = aspiration(
            (pid % 10) / 10
        )
    return world


def converted(tmp_path, count, name="aspirations"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        aspiration_world(count), source, rules_id=RULES
    )
    convert_cold_to_lazy(source, destination, rules_id=RULES)
    return destination


def test_aspirations_open_zero_payloads_point_read_one_and_order(tmp_path):
    destination = converted(tmp_path, 400)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.aspirations
        assert isinstance(table, LazyAspirationTable)
        assert table.diagnostics()["aspiration_payload_loads"] == 0
        assert len(table) == 400
        assert table.diagnostics()["aspiration_payload_loads"] == 0
        assert table[300].reason == "curiosity"
        assert table.diagnostics()["aspiration_payload_loads"] == 1
        assert tuple(table) == tuple(range(1, 401))


def test_aspiration_edit_noop_save_and_reopen(tmp_path):
    destination = converted(tmp_path, 20, "edit")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        item = session.world.magic_resources.aspirations[7]
        item.preparation = 0.75
        generation = session.save()
        assert generation == session.pin.captured_head
        before = session.store.diagnostics().payload_writes
        assert session.save() == generation
        assert session.store.diagnostics().payload_writes == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        item = reopened.world.magic_resources.aspirations[7]
        assert item.preparation == 0.75


def test_retained_aspiration_survives_cache_pressure_and_mutates(tmp_path):
    destination = converted(tmp_path, 400, "pressure")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.aspirations
        retained = table[1]
        for key in range(2, 401):
            table[key]
        assert not dict.__contains__(table, 1)
        retained.search_years = 9
        assert dict.__contains__(table, 1)
        assert table[1] is retained
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.magic_resources.aspirations[1].search_years == 9


def test_aspiration_structural_order_delete_reinsert_and_replacement(tmp_path):
    destination = converted(tmp_path, 4, "structural")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.aspirations
        old = table[2]
        del table[2]
        table[2] = old
        table[5] = aspiration(0.9, reason="new")
        assert tuple(table) == (1, 3, 4, 2, 5)
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        table = reopened.world.magic_resources.aspirations
        assert tuple(table) == (1, 3, 4, 2, 5)
        replacement = aspiration(table[1].drive, reason=table[1].reason)
        old = table[1]
        table[1] = replacement
        assert table[1] is replacement
        assert old is not replacement
        session_generation = reopened.save()
        assert session_generation == reopened.pin.captured_head


def test_cross_boundary_aspiration_alias_mutates_without_payload_load(tmp_path):
    world = aspiration_world(4)
    shared = world.magic_resources.aspirations[1]
    world.currency.wallets[99] = {"aspiration": shared}
    source = tmp_path / "cross-cold.sqlite"
    destination = tmp_path / "cross-lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, destination, rules_id=RULES)

    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.aspirations
        eager_alias = session.world.currency.wallets[99]["aspiration"]
        assert table.diagnostics()["aspiration_payload_loads"] == 0
        eager_alias.preparation = 0.88
        assert table.diagnostics()["aspiration_payload_loads"] == 0
        assert table[1] is eager_alias
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        lazy = reopened.world.magic_resources.aspirations[1]
        eager = reopened.world.currency.wallets[99]["aspiration"]
        assert lazy is eager
        assert lazy.preparation == 0.88


def test_lazy_detach_materializes_complete_aspiration_mapping(tmp_path):
    destination = converted(tmp_path, 400, "detach")
    session = open_lazy_world_session(destination, rules_id=RULES)
    table = session.world.magic_resources.aspirations
    retained = table[1]
    retained.preparation = 0.91

    detached = session.detach(materialize_history=True)
    assert type(detached.magic_resources.aspirations) is dict
    assert len(detached.magic_resources.aspirations) == 400
    assert detached.magic_resources.aspirations[1] is retained
    assert retained.preparation == 0.91

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    session.close()


@pytest.mark.parametrize("count", [1000, 10000])
def test_aspiration_open_cost_does_not_decode_aspiration_history(tmp_path, count):
    destination = converted(tmp_path, count, f"scale-{count}")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        table = session.world.magic_resources.aspirations
        assert len(table) == count
        assert table.diagnostics()["aspiration_payload_loads"] == 0
