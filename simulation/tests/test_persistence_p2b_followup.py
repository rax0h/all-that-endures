import pytest

from ate_sim import Simulation, generate_world
from ate_sim.checkpoint import dumps as checkpoint_dumps, loads as checkpoint_loads
from ate_sim.core import Event, Layer, World
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_adapters import read_snapshot, write_snapshot
from ate_sim.persistence_tracking import bind_snapshot

RULES = "stage-0.5-p2b-followup"


def snap(tmp_path, world, name):
    path = tmp_path / name
    write_snapshot(world, path, rules_id=RULES)
    return path


def clone(world):
    return checkpoint_loads(checkpoint_dumps(world))


def event_world(count):
    world = World(700)
    world.year = 5
    world.events = EventLog(
        Event(i, 0, "history", Layer.REALITY) for i in range(1, count + 1)
    )
    world.event_ids = set(range(1, count + 1))
    world.next_event = count + 1
    return world


def test_f1_new_same_owner_dict_alias_restores_identity(tmp_path):
    world = World(701)
    world.currency.wallets = {1: {"left": {"value": 1}}}
    path = snap(tmp_path, world, "same-owner-dict.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        wallet = world.currency.wallets[1]
        wallet["right"] = wallet["left"]
        assert wallet["right"] is wallet["left"]
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["right"] is restored.currency.wallets[1]["left"]
    restored.currency.wallets[1]["left"]["value"] = 8
    assert restored.currency.wallets[1]["right"]["value"] == 8


def test_f1_new_same_owner_list_alias_and_edge_removal_preserve_identity(tmp_path):
    world = World(702)
    shared = {"value": 2}
    world.genealogy.children = {1: [shared]}
    path = snap(tmp_path, world, "same-owner-list.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        items = world.genealogy.children[1]
        items.append(items[0])
        assert items[0] is items[1]
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.genealogy.children[1][0] is restored.genealogy.children[1][1]

    with bind_snapshot(restored, path, rules_id=RULES) as session:
        items = restored.genealogy.children[1]
        del items[0]
        items[0]["value"] = 9
        session.save()
    final = read_snapshot(path, rules_id=RULES)
    assert len(final.genealogy.children[1]) == 1
    assert final.genealogy.children[1][0]["value"] == 9


def test_f1_new_same_owner_nested_dataclass_alias_restores_identity(tmp_path):
    from ate_sim.agency import MotiveState

    world = World(703)
    world.agency.motives = {1: MotiveState()}
    world.currency.wallets = {1: {"box": {"value": 1}}}
    path = snap(tmp_path, world, "same-owner-dataclass.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        motive = world.agency.motives[1]
        # Put one existing mutable child into two fields of a new nested mapping
        # reachable from the same record owner.
        shared = world.currency.wallets[1]["box"]
        world.currency.wallets[1]["pair"] = {"a": shared, "b": shared}
        motive.wealth = .25
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    pair = restored.currency.wallets[1]["pair"]
    assert pair["a"] is pair["b"] is restored.currency.wallets[1]["box"]


@pytest.mark.parametrize("kind", ["dict", "list", "set"])
@pytest.mark.parametrize("same_owner_key", [True, False])
def test_f2_cross_session_tracked_containers_reject_before_mutation(
    tmp_path, kind, same_owner_key
):
    a = World(710)
    b = World(711)
    a.currency.wallets = {1: {"inner": {"value": 1}}, 2: {}}
    b.currency.wallets = {1: {"inner": {"value": 1}}, 2: {}}
    a.genealogy.children = {1: [1, 2]}
    b.genealogy.children = {1: [1, 2]}
    a.social.adjacency = {1: {2, 3}}
    b.social.adjacency = {1: {2, 3}}
    pa = snap(tmp_path, a, f"a-{kind}-{same_owner_key}.sqlite")
    pb = snap(tmp_path, b, f"b-{kind}-{same_owner_key}.sqlite")

    with bind_snapshot(a, pa, rules_id=RULES) as sa, bind_snapshot(b, pb, rules_id=RULES) as sb:
        target = 1 if same_owner_key else 2
        if kind == "dict":
            foreign = b.currency.wallets[1]["inner"]
        elif kind == "list":
            foreign = b.genealogy.children[1]
        else:
            foreign = b.social.adjacency[1]

        a_before = a.digest()
        b_before = b.digest()
        da, db = sa.dirty, sb.dirty
        with pytest.raises(StoreError, match="cross-session"):
            a.currency.wallets[target]["foreign"] = foreign
        assert "foreign" not in a.currency.wallets[target]
        assert a.digest() == a_before
        assert b.digest() == b_before
        assert sa.dirty == da
        assert sb.dirty == db

        # Both sessions remain usable and independently tracked afterward.
        a.currency.wallets[target]["local"] = {"value": 4}
        b.currency.wallets[1]["inner"]["value"] = 7
        assert ("world.currency.wallets", target) in sa.dirty
        assert ("world.currency.wallets", 1) in sb.dirty
        sa.save()
        sb.save()

    ra = read_snapshot(pa, rules_id=RULES)
    rb = read_snapshot(pb, rules_id=RULES)
    assert ra.currency.wallets[target]["local"]["value"] == 4
    assert "foreign" not in ra.currency.wallets[target]
    assert rb.currency.wallets[1]["inner"]["value"] == 7


def test_f2_cross_session_nested_incoming_value_rejects_atomically(tmp_path):
    a = World(712)
    b = World(713)
    a.currency.wallets = {1: {}}
    b.genealogy.children = {1: [1, 2]}
    pa = snap(tmp_path, a, "a-nested.sqlite")
    pb = snap(tmp_path, b, "b-nested.sqlite")
    with bind_snapshot(a, pa, rules_id=RULES) as sa, bind_snapshot(b, pb, rules_id=RULES) as sb:
        incoming = {"level": {"foreign": b.genealogy.children[1]}}
        with pytest.raises(StoreError, match="cross-session"):
            a.currency.wallets[1]["nested"] = incoming
        assert "nested" not in a.currency.wallets[1]
        assert not sa.dirty
        assert not sb.dirty


@pytest.mark.parametrize("count", [100, 1000, 5000])
def test_f3_unshared_wallet_delete_save_never_iterates_event_history(
    tmp_path, monkeypatch, count
):
    world = event_world(count)
    world.currency.wallets = {1: {"iron": 1}, 2: {"iron": 2}}
    path = snap(tmp_path, world, f"delete-{count}.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        visited = {"events": 0}
        original = EventLog.__iter__

        def counted(log):
            for event in original(log):
                visited["events"] += 1
                yield event

        monkeypatch.setattr(EventLog, "__iter__", counted)
        del world.currency.wallets[1]
        session.save()
        assert visited["events"] == 0
    restored = read_snapshot(path, rules_id=RULES)
    assert 1 not in restored.currency.wallets
    assert len(restored.events) == count


@pytest.mark.parametrize("count", [100, 1000, 5000])
def test_f3_alias_anchor_removal_save_avoids_unrelated_history(
    tmp_path, monkeypatch, count
):
    world = event_world(count)
    shared = {"value": 1}
    world.currency.wallets = {1: {"inner": shared}, 2: {"inner": shared}}
    path = snap(tmp_path, world, f"anchor-{count}.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        visited = {"events": 0}
        original = EventLog.__iter__

        def counted(log):
            for event in original(log):
                visited["events"] += 1
                yield event

        monkeypatch.setattr(EventLog, "__iter__", counted)
        del world.currency.wallets[1]
        world.currency.wallets[2]["inner"]["value"] = 6
        session.save()
        assert visited["events"] == 0
    restored = read_snapshot(path, rules_id=RULES)
    assert 1 not in restored.currency.wallets
    assert restored.currency.wallets[2]["inner"]["value"] == 6


def test_followup_bound_unbound_restored_continuation_control(tmp_path):
    base = Simulation(generate_world(843000, mature=True)).run(5)
    bound = clone(base)
    control = clone(base)
    path = snap(tmp_path, bound, "control.sqlite")

    with bind_snapshot(bound, path, rules_id=RULES) as session:
        Simulation(bound).run(1)
        session.save()
    Simulation(control).run(1)

    restored = read_snapshot(path, rules_id=RULES)
    assert bound.digest() == control.digest() == restored.digest()
    independent = clone(control)
    expected = Simulation(independent).run(2).digest()
    assert Simulation(bound).run(2).digest() == expected
    assert Simulation(control).run(2).digest() == expected
    restored = read_snapshot(path, rules_id=RULES)
    assert Simulation(restored).run(2).digest() == expected
