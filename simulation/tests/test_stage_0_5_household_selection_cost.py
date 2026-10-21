"""Select the short side without changing membership authority or ordering."""
from unittest.mock import patch

from ate_sim.core import World, Person, Household
from ate_sim.household_queries import living_household_members
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'smaller-side-household-selection'


def make(tmp_path, members, living):
    world = World(843000)
    for pid in range(1, living+1):
        world.people[pid] = Person(pid, 0, 1, 2)  # Person.household is not membership authority.
    world.people[living+1] = Person(living+1, 0, 1, 1, alive=False)
    world.households[1] = Household(1, 1, members=members)
    source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    return target


def test_short_household_does_not_probe_every_live_id(tmp_path):
    path = make(tmp_path, [3, 1, 3], 1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        members = session.world.households[1].members
        with patch.object(members, 'occurrences', wraps=members.occurrences) as calls:
            assert [p.id for p in living_household_members(session.world, 1)] == [3, 1, 3]
            assert calls.call_count == 0


def test_long_household_uses_live_candidates(tmp_path):
    path = make(tmp_path, [4]*10000+[3, 1, 3], 3)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        members = session.world.households[1].members
        with patch.object(type(members), '__iter__', side_effect=AssertionError('scanned cold history')):
            assert [p.id for p in living_household_members(session.world, 1)] == [3, 1, 3]


def test_numeric_duplicates_and_fresh_liveness(tmp_path):
    path = make(tmp_path, [True, 1.0, 2, 4], 3)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        world = session.world
        assert [p.id for p in living_household_members(world, 1)] == [1, 1, 2]
        world.people[2].alive = False
        world.people[4].alive = True
        assert [p.id for p in living_household_members(world, 1)] == [1, 1, 4]
        world.people[5] = Person(5, 0, 1, 2)
        world.households[1].members.append(5)
        assert [p.id for p in living_household_members(world, 1)] == [1, 1, 4, 5]
        world.households[1].members[:] = []
        assert living_household_members(world, 1) == []
