"""Reports must contain detached JSON values for populated persisted treasuries."""
import json

import pytest

from ate_sim.core import World
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_lazy_nested_history import LazyHistoryMap
from ate_sim.persistence_session import write_cold_snapshot
from persistence_p5_long_validation import _audit
from run_long_history import snapshot


RULES = "long-report-treasuries"


def populated_world():
    world = World(843000)
    world.currency.treasuries[1] = {"iron": 7}
    world.currency.treasuries[2] = {"lesser": 5, "bronze": 2}
    world.currency.minted.update(iron=7, lesser=5, bronze=2)
    return world


def normalized_audit(world):
    result = _audit(world)
    result.pop("audit_seconds")
    return result


@pytest.mark.parametrize("complete", [False, True], ids=["legacy", "complete"])
def test_populated_treasury_audit_matches_eager_before_save_after_save_and_reopen(tmp_path, complete):
    world = populated_world()
    expected = normalized_audit(world)
    cold, lazy, upgraded = (tmp_path / name for name in ("cold.sqlite", "lazy.sqlite", "complete.sqlite"))
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, lazy, rules_id=RULES, native_graph_buckets=complete)
    if complete:
        upgrade_lazy_snapshot(lazy, upgraded, rules_id=RULES)
    target = upgraded if complete else lazy
    with open_lazy_world_session(target, rules_id=RULES) as session:
        if complete:
            assert type(session.world.currency.treasuries[1]) is LazyHistoryMap
        assert normalized_audit(session.world) == expected
        # Mutate the actual lazy currency graph while maintaining conservation.
        session.world.currency.treasuries[1]["iron"] += 3
        session.world.currency.minted["iron"] += 3
        world.currency.treasuries[1]["iron"] += 3
        world.currency.minted["iron"] += 3
        expected = normalized_audit(world)
        generation = session.save()
        assert normalized_audit(session.world) == expected
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert session.pin.captured_head == generation
        assert normalized_audit(session.world) == expected


def test_snapshot_treasuries_are_detached_values():
    world = populated_world()
    report = snapshot(world)
    expected = {1: {"iron": 7}, 2: {"lesser": 5, "bronze": 2}}
    world.currency.treasuries[1]["iron"] = 99
    world.currency.treasuries[3] = {"gold": 1}
    assert report["magic_access"]["treasuries"] == expected
    assert json.loads(json.dumps(report))["magic_access"]["treasuries"] == {
        str(key): value for key, value in expected.items()
    }
