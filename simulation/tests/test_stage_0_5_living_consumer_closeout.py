"""Ordinary death and household-deactivation consumers avoid cold dead-member scans.

The canonical historical sequence remains ordered and complete. Only living
candidates are selected, with duplicates preserved for observable grief events.
"""
import pytest

from ate_sim import Simulation
from ate_sim.mortality import kill
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_paged_household_world import make
from simulation.tests.test_persistence_lazy_people import RULES


def _page_bound(session, history, active=8):
    # The number of decoded Person payloads and sequence pages is independent
    # of the dead historical tail length.
    loads = session.world.people.diagnostics()["person_payload_loads"]
    seq = session.world.households[1].members
    assert loads <= active
    assert seq.diagnostics()["resident_cached_pages"] <= 4
    stats = session.store.diagnostics()
    assert stats.payload_read_bytes < 50000


@pytest.mark.parametrize("history", [1000, 10000])
def test_mortality_survivors_and_inheritance_match_eager_without_dead_loads(
    tmp_path, history,
):
    expected, path = make(tmp_path, history)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        eager_death = kill(expected, expected.people[1], "natural")
        lazy_death = kill(session.world, session.world.people[1], "natural")
        assert eager_death is not None and lazy_death is not None
        assert session.world.people[1].alive is False
        _page_bound(session, history)
        assert session.world.digest() == expected.digest()
        before = session.pin.captured_head
        assert session.save() == before + 1
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.digest() == expected.digest()


@pytest.mark.parametrize("history", [1000, 10000])
def test_engine_death_matches_eager_without_dead_member_reads(tmp_path, history):
    expected, path = make(tmp_path, history)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        Simulation(expected)._die(expected.people[1], "natural")
        Simulation(session.world)._die(session.world.people[1], "natural")
        _page_bound(session, history)
        assert session.world.digest() == expected.digest()


@pytest.mark.parametrize("history", [1000, 10000])
def test_demography_deactivates_households_without_scanning_dead_members(
    tmp_path, history,
):
    expected, path = make(tmp_path, history)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        for pid in range(1, 9):
            expected.people[pid].alive = False
            session.world.people[pid].alive = False
        # No surviving people; _demography checks household occupancy,
        # but may not load any additional historical Person records.
        Simulation(expected)._demography()
        Simulation(session.world)._demography()
        assert expected.households[1].alive is False
        assert session.world.households[1].alive is False
        _page_bound(session, history)
        assert session.world.digest() == expected.digest()
        assert session.save() == session.pin.captured_head + 1
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.digest() == expected.digest()


def test_duplicate_live_member_occurrences_keep_order_and_effects(tmp_path):
    expected, path = make(tmp_path, 1000)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        # Exact native sequence semantics: duplicate live references result
        # in repeated bereavement handling, not set-style deduplication.
        for world in (expected, session.world):
            world.households[1].members.append(2)
            world.households[1].members.append(3)
        kill(expected, expected.people[1], "natural")
        kill(session.world, session.world.people[1], "natural")
        assert session.world.digest() == expected.digest()
        bereaved = [e.actors[0].id for e in expected.events
                    if e.kind == "bereavement"]
        assert bereaved.count(2) == 2
        assert bereaved.count(3) == 2
        _page_bound(session, 1000)
