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


@pytest.mark.parametrize("count", [1000, 10000])
def test_r1_retained_history_sidecars_and_reactivation_across_boundaries(
    tmp_path, count
):
    world = people_world(count, active=8)
    path = _converted(tmp_path, world, f"r1-history-{count}")
    with open_lazy_world_session(path, rules_id=RULES) as session:
        people = session.world.people
        assert not people._baseline_payload
        for person_id in range(1, count + 1):
            assert people[person_id].id == person_id

        def checked_bound():
            gc.collect()
            assert len(people._baseline_payload) <= 256
            assert len(people._baseline_presence) <= 256
            assert len(people._baseline_incarnation) <= 256
            assert len(people._baseline_ordinal) <= 256
            registry = session._registry
            assert len(registry._occurrences) <= 256
            assert len(registry._occurrences_by_owner) <= 256
            assert sum(map(len, people._baseline_payload.values())) <= 200000

        checked_bound()
        for person_id in range(1, count + 1):
            assert person_id in people
        for person_id in range(count + 1, count + 4001):
            assert person_id not in people
        checked_bound()

        for person_id in range(1, count + 1):
            assert people[person_id].id == person_id
        checked_bound()

        generation = session.pin.captured_head
        session.store.reset_diagnostics()
        assert session.save() == generation
        assert session.store.diagnostics().payload_writes == 0
        checked_bound()

        # An explicit full digest is an allowed proportional traversal, but
        # discarded clean historical metadata must not survive that boundary.
        before_digest = session.world.digest()
        assert before_digest == world.digest()
        checked_bound()

        people[1].wealth += 3.25
        assert session.save() == generation + 1
        checked_bound()
        after_digest = session.world.digest()
        assert after_digest != before_digest
        checked_bound()

    with open_lazy_world_session(path, rules_id=RULES) as reopened:
        assert reopened.world.people[1].wealth == world.people[1].wealth + 3.25
        assert reopened.world.digest() == after_digest


def test_r2_public_lifecycle_rejects_reentrancy_then_recovers(
    tmp_path, monkeypatch
):
    from ate_sim.history_archive import export_archive

    path = _converted(tmp_path, people_world(12), "r2-nested")
    with open_lazy_world_session(path, rules_id=RULES) as session:
        person = session.world.people[1]
        before = person.wealth
        calls = []
        original = core._digest_world_unchecked

        def adversarial(_world):
            calls.append("entered")
            for action in (
                lambda: setattr(person, "wealth", before + 1),
                lambda: session.close(),
                lambda: session.save(),
                lambda: session.detach(materialize_history=True),
                lambda: session.world.digest(),
            ):
                with pytest.raises(StoreError):
                    action()
            raise RuntimeError("digest fault")

        monkeypatch.setattr(core, "_digest_world_unchecked", adversarial)
        with pytest.raises(RuntimeError, match="digest fault"):
            session.world.digest()
        assert calls == ["entered"]
        assert person.wealth == before
        assert session._lifecycle_operation is None

        archive = tmp_path / "blocked-archive.sqlite"
        with session.world.current_people_scope():
            with pytest.raises(StoreError):
                export_archive(session.world, archive, digest="trusted")
        assert not archive.exists()

        monkeypatch.setattr(core, "_digest_world_unchecked", original)
        assert isinstance(session.world.digest(), str)
        assert session._lifecycle_operation is None


def test_r2_closed_store_public_digest_preflights_callback(
    tmp_path, monkeypatch
):
    path = _converted(tmp_path, people_world(12), "r2-closed-store")
    session = open_lazy_world_session(path, rules_id=RULES)
    try:
        called = []
        monkeypatch.setattr(
            core, "_digest_world_unchecked", lambda _world: called.append("ran")
        )
        session.store.close()
        with pytest.raises(StoreError, match="closed"):
            session.world.digest()
        assert not called
    finally:
        # Direct store closure is intentionally adversarial; the session no
        # longer owns a live underlying pin to release.
        session._active = False
