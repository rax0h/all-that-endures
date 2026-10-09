"""Living-member access must not materialize dead household history.

Candidate enumeration is bounded by current people and checked member
occurrences. The returned order and multiplicity must remain exactly native.
"""
import pytest

from ate_sim.civilization import _household_living
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_paged_household_world import make
from simulation.tests.test_persistence_lazy_people import RULES


@pytest.mark.parametrize("history", [1000, 10000])
def test_living_member_selection_is_bounded_by_current_people(tmp_path, history):
    original, path = make(tmp_path, history)
    expected = [p.id for p in _household_living(original, 1)]
    assert expected
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        world = session.world
        members = world.households[1].members
        current = tuple(world.current_people())
        assert len(current) == len(expected)
        assert world.people.diagnostics()["person_payload_loads"] <= len(current)
        session.store.reset_diagnostics()
        assert members.matching_member_ids(p.id for p in current) == expected
        assert [p.id for p in _household_living(world, 1)] == expected
        stats = session.store.diagnostics()
        assert stats.payload_read_bytes < 32000
        assert members.diagnostics()["resident_cached_pages"] <= 4
        assert world.people.diagnostics()["person_payload_loads"] <= len(current)


def test_dirty_pages_duplicate_positions_and_reopen_preserve_native_order(tmp_path):
    original, path = make(tmp_path, 260)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        world = session.world
        members = world.households[1].members
        # Duplicate an actual living ID and overwrite another live slot
        # with a historical member. Appends are still current dirty pages.
        living = [p.id for p in world.current_people()]
        assert len(living) >= 2
        members[1] = living[0]
        original.households[1].members[1] = living[0]
        members[7] = 260
        original.households[1].members[7] = 260
        members.append(living[1])
        original.households[1].members.append(living[1])
        expected = [p.id for p in _household_living(original, 1)]
        assert members.matching_member_ids(living) == expected
        assert [p.id for p in _household_living(world, 1)] == expected
        session.save()
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert [p.id for p in _household_living(reopened.world, 1)] == expected


def test_unpaged_eager_world_retains_native_living_selection(tmp_path):
    original, _path = make(tmp_path, 130)
    expected = [
        original.people[pid] for pid in original.households[1].members
        if original.people[pid].alive
    ]
    assert _household_living(original, 1) == expected
