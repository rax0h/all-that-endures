import pytest

from ate_sim import Simulation, generate_world
from ate_sim.core import World, Event, Layer
from ate_sim.event_log import EventLog
from ate_sim.agency import ActionRecord, MotiveState
from ate_sim.advancement import AbilityProgress, EssencePath, Understanding
from ate_sim.checkpoint import dumps as checkpoint_dumps, loads as checkpoint_loads
from ate_sim.persistence_adapters import write_snapshot, read_snapshot
from ate_sim.persistence_tracking import bind_snapshot, TrackedDict
from ate_sim.incremental_store import StoreError, StoreIntegrityError

RULES = "stage-0.5-p2b-r1-r6"


def snap(tmp_path, world, name="world.sqlite"):
    path = tmp_path / name
    write_snapshot(world, path, rules_id=RULES)
    return path


def clone(world):
    return checkpoint_loads(checkpoint_dumps(world))


def test_r1_short_lived_insertions_keep_values_and_identity_distinct(tmp_path):
    world = World(401)
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        for i in range(80):
            world.currency.wallets[i] = {
                "iron": i,
                "nested": {"items": [i, i + 1]},
            }
        assert [world.currency.wallets[i]["iron"] for i in range(80)] == list(range(80))
        assert len({id(world.currency.wallets[i]) for i in range(80)}) == 80
        assert len({id(world.currency.wallets[i]["nested"]) for i in range(80)}) == 80
        assert len({id(world.currency.wallets[i]["nested"]["items"]) for i in range(80)}) == 80
        session.save()
    assert [world.currency.wallets[i]["iron"] for i in range(80)] == list(range(80))
    assert len({id(world.currency.wallets[i]) for i in range(80)}) == 80
    restored = read_snapshot(path, rules_id=RULES)
    assert [restored.currency.wallets[i]["iron"] for i in range(80)] == list(range(80))
    assert len({id(restored.currency.wallets[i]) for i in range(80)}) == 80
    assert len({id(restored.currency.wallets[i]["nested"]) for i in range(80)}) == 80
    assert len({id(restored.currency.wallets[i]["nested"]["items"]) for i in range(80)}) == 80


def test_r1_bound_world_matches_independent_unbound_control(tmp_path):
    base = Simulation(generate_world(843000, mature=True)).run(5)
    bound = clone(base)
    control = clone(base)
    path = snap(tmp_path, bound)
    with bind_snapshot(bound, path, rules_id=RULES) as session:
        Simulation(bound).run(1)
        session.save()
        bound_digest = bound.digest()
        bound_events = len(bound.events)
    Simulation(control).run(1)
    assert bound_digest == control.digest()
    assert bound_events == len(control.events) == 1467
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.digest() == control.digest()
    assert Simulation(restored).run(2).digest() == Simulation(control).run(2).digest()


def test_r2_rejected_root_replacement_keeps_old_value_tracked(tmp_path):
    world = World(402)
    world.currency.wallets = {1: {"iron": 3}, 2: {"iron": 5}}
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        retained = world.currency.wallets[2]
        with pytest.raises(StoreError, match="shared mutable"):
            world.currency.wallets[2] = world.currency.wallets[1]
        assert world.currency.wallets[2] is retained
        retained["iron"] = 9
        assert ("world.currency.wallets", 2) in session.dirty
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["iron"] == 3
    assert restored.currency.wallets[2]["iron"] == 9


def test_r2_rejected_nested_cycle_and_extended_slice_leave_tracking_intact(tmp_path):
    world = World(403)
    world.currency.wallets = {1: {"inner": {"value": 1}}}
    world.agency.actions = [
        ActionRecord(0, 1, "work", "wealth", .1),
        ActionRecord(0, 2, "work", "wealth", .2),
        ActionRecord(0, 3, "work", "wealth", .3),
    ]
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        inner = world.currency.wallets[1]["inner"]
        with pytest.raises(StoreError, match="cycles"):
            inner["cycle"] = world.currency.wallets[1]
        assert "cycle" not in inner
        inner["value"] = 7
        actions = world.agency.actions
        first = actions[0]
        with pytest.raises(ValueError):
            actions[::2] = [ActionRecord(1, 9, "learn", "curiosity", .9)]
        assert actions[0] is first and len(actions) == 3
        first.strength = .75
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["inner"]["value"] == 7
    assert restored.agency.actions[0].strength == .75
    assert len(restored.agency.actions) == 3


def test_r2_new_nested_dataclass_child_remains_tracked(tmp_path):
    world = World(404)
    ability = AbilityProgress("fire", "stone", "fire/control", "Control", "control", "combat", 0)
    world.advancement.paths = {1: EssencePath(["fire"], abilities=[ability])}
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        replacement = Understanding()
        ability = world.advancement.paths[1].abilities[0]
        ability.understanding = replacement
        ability.understanding.integration = 2.5
        assert ("world.advancement.paths", 1) in session.dirty
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.advancement.paths[1].abilities[0].understanding.integration == 2.5


def test_r3_shared_deep_descendant_propagates_every_owner(tmp_path):
    shared = {"value": 1}
    world = World(405)
    world.currency.wallets = {
        1: {"inner": shared},
        2: {"inner": shared},
    }
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        assert world.currency.wallets[1]["inner"] is world.currency.wallets[2]["inner"]
        world.currency.wallets[1]["inner"]["value"] = 2
        assert {
            ("world.currency.wallets", 1),
            ("world.currency.wallets", 2),
        }.issubset(session.dirty)
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["inner"] is restored.currency.wallets[2]["inner"]
    assert restored.currency.wallets[2]["inner"]["value"] == 2


def test_r3_shared_dataclass_and_same_owner_repeated_reference(tmp_path):
    motive = MotiveState(wealth=.4)
    repeated = {"value": 3}
    world = World(406)
    world.agency.motives = {1: motive, 2: motive}
    world.currency.wallets = {1: {"left": repeated, "right": repeated}}
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.agency.motives[1].wealth = .9
        world.currency.wallets[1]["left"]["value"] = 8
        assert ("world.agency.motives", 1) in session.dirty
        assert ("world.agency.motives", 2) in session.dirty
        assert ("world.currency.wallets", 1) in session.dirty
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.agency.motives[1] is restored.agency.motives[2]
    assert restored.agency.motives[2].wealth == .9
    assert restored.currency.wallets[1]["left"] is restored.currency.wallets[1]["right"]
    assert restored.currency.wallets[1]["right"]["value"] == 8


def test_r3_legal_new_nested_sharing_updates_identity_manifest(tmp_path):
    world = World(407)
    world.currency.wallets = {1: {"inner": {"value": 1}}, 2: {}}
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        shared = world.currency.wallets[1]["inner"]
        world.currency.wallets[2]["linked"] = shared
        assert world.currency.wallets[2]["linked"] is shared
        assert {
            ("world.currency.wallets", 1),
            ("world.currency.wallets", 2),
        }.issubset(session.dirty)
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["inner"] is restored.currency.wallets[2]["linked"]
    with bind_snapshot(restored, path, rules_id=RULES) as session:
        del restored.currency.wallets[2]["linked"]
        restored.currency.wallets[1]["inner"]["value"] = 4
        session.save()
    final = read_snapshot(path, rules_id=RULES)
    assert "linked" not in final.currency.wallets[2]
    assert final.currency.wallets[1]["inner"]["value"] == 4


@pytest.mark.parametrize("mode", ["value", "key", "order"])
def test_r4_mismatched_baseline_fails_cleanly(tmp_path, mode):
    world = World(408)
    world.currency.wallets = {1: {"iron": 3}, 2: {"iron": 5}}
    path = snap(tmp_path, world, f"{mode}.sqlite")
    if mode == "value":
        world.currency.wallets[2]["iron"] = 99
    elif mode == "key":
        world.currency.wallets = {1: {"iron": 3}, 3: {"iron": 5}}
    else:
        world.currency.wallets = {2: {"iron": 5}, 1: {"iron": 3}}
    original_wallets = world.currency.wallets
    with pytest.raises(StoreIntegrityError):
        bind_snapshot(world, path, rules_id=RULES)
    assert world.currency.wallets is original_wallets
    assert type(world.currency.wallets) is dict
    assert all(type(v) is dict for v in world.currency.wallets.values())


@pytest.mark.parametrize("mature", [False, True])
def test_r5_founder_and_mature_bound_runs_match_unbound_control(tmp_path, mature):
    base = generate_world(409 + int(mature), mature=mature)
    bound = clone(base)
    control = clone(base)
    path = snap(tmp_path, bound, f"start-{mature}.sqlite")
    with bind_snapshot(bound, path, rules_id=RULES) as session:
        Simulation(bound).run(1)
        session.save()
    Simulation(control).run(1)
    assert bound.digest() == control.digest()
    assert read_snapshot(path, rules_id=RULES).digest() == control.digest()


def test_r5_agency_action_tail_root_replacement_is_supported(tmp_path):
    world = World(411)
    world.agency.actions = [
        ActionRecord(i // 1000, i, "work", "wealth", .5)
        for i in range(50001)
    ]
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.agency.actions = world.agency.actions[-50000:]
        assert len(world.agency.actions) == 50000
        assert world.agency.actions[0].person == 1
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert len(restored.agency.actions) == 50000
    assert restored.agency.actions[0].person == 1
    assert restored.agency.actions[-1].person == 50000


def _event_world(count):
    world = World(500)
    world.year = 5
    events = [
        Event(i, 0, "history", Layer.REALITY)
        for i in range(1, count + 1)
    ]
    world.events = EventLog(events)
    world.event_ids = set(range(1, count + 1))
    world.next_event = count + 1
    return world


def test_r5_cold_event_sealing_matches_unbound_control(tmp_path):
    world = _event_world(EventLog.chunk_size)
    control = clone(world)
    path = snap(tmp_path, world)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.events.seal_before(4)
        assert len(world.events._chunks) == 1
        session.save()
    control.events.seal_before(4)
    assert world.digest() == control.digest()
    restored = read_snapshot(path, rules_id=RULES)
    assert restored.digest() == control.digest()
    assert len(restored.events._chunks) == 1


@pytest.mark.parametrize("count", [100, 1000, 5000])
def test_r6_event_emit_changed_member_work_is_constant(tmp_path, count):
    world = _event_world(count)
    path = snap(tmp_path, world, f"events-{count}.sqlite")
    with bind_snapshot(world, path, rules_id=RULES) as session:
        session.reset_changed_member_work()
        world.emit("new", Layer.REALITY)
        assert session.changed_member_work == 2
        assert ("world.events", count) in session.dirty
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert len(restored.events) == count + 1
    assert count + 1 in restored.event_ids


@pytest.mark.parametrize("count", [100, 1000, 5000])
def test_r6_dictionary_delete_changed_member_work_is_constant(tmp_path, count):
    world = World(600)
    world.currency.wallets = {i: {"iron": i} for i in range(count)}
    path = snap(tmp_path, world, f"dict-{count}.sqlite")
    key = count // 2
    with bind_snapshot(world, path, rules_id=RULES) as session:
        session.reset_changed_member_work()
        del world.currency.wallets[key]
        assert session.changed_member_work == 1
        assert session.deleted == {("world.currency.wallets", key)}
        session.save()
    restored = read_snapshot(path, rules_id=RULES)
    assert key not in restored.currency.wallets
    assert len(restored.currency.wallets) == count - 1
