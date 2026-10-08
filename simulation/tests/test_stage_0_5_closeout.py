"""Stage 0.5 final architect closeout: reproductions before repair."""
from __future__ import annotations

import gc
import sys

import pytest

from ate_sim.core import Household
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from simulation.tests.test_persistence_lazy_people import RULES, people_world
import ate_sim.core as core


def _converted(tmp_path, world, suffix):
    cold = tmp_path / (suffix + "-cold.sqlite")
    lazy = tmp_path / (suffix + "-lazy.sqlite")
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, lazy, rules_id=RULES)
    return lazy


@pytest.mark.parametrize("count", [300, 900])
def test_r1_clean_history_releases_baselines_and_occurrences(tmp_path, count):
    path = _converted(tmp_path, people_world(count, active=8), f"r1-{count}")
    with open_lazy_world_session(path, rules_id=RULES) as session:
        people = session.world.people
        for person_id in range(1, count + 1):
            assert people[person_id].id == person_id
        gc.collect()
        assert len(people._baseline_payload) <= people._clean_limit
        assert len(people._baseline_presence) <= people._clean_limit
        assert len(people._baseline_incarnation) <= people._clean_limit
        assert len(session._registry._occurrences) <= people._clean_limit


def test_r2_public_digest_rejects_mutation_before_callback(tmp_path, monkeypatch):
    path = _converted(tmp_path, people_world(20), "r2-digest")
    with open_lazy_world_session(path, rules_id=RULES) as session:
        person = session.world.people[1]
        before = person.wealth
        calls = []

        def forbidden(_world):
            calls.append("called")
            person.wealth = before + 1
            return "unprotected"

        monkeypatch.setattr(core, "_digest_world_unchecked", forbidden)
        with pytest.raises(StoreError):
            session.world.digest()
        assert person.wealth == before
        assert calls == ["called"]


def test_r2_scope_rejects_digest_before_callback(tmp_path, monkeypatch):
    path = _converted(tmp_path, people_world(20), "r2-scope")
    with open_lazy_world_session(path, rules_id=RULES) as session:
        calls = []
        monkeypatch.setattr(core, "_digest_world_unchecked", lambda _world: calls.append(1))
        with session.world.current_people_scope():
            with pytest.raises(StoreError):
                session.world.digest()
        assert not calls


@pytest.mark.parametrize("count", [1000])
def test_r3_household_history_not_loaded_as_full_eager_list(tmp_path, count):
    world = people_world(count, active=8)
    world.households[1] = Household(1, 1, list(range(1, count + 1)))
    world.next_household = 2
    path = _converted(tmp_path, world, f"r3-{count}")
    with open_lazy_world_session(path, rules_id=RULES) as session:
        members = session.world.households[1].members
        assert len(members) == count
        assert members[0] == 1 and members[-1] == count
        assert sys.getsizeof(members) < 1024
