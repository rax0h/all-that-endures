"""Stage 0.5 architect-closeout red probes; do not weaken invariants."""
import gc
import sys
import pytest

from ate_sim.core import Household
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.history_archive import export_archive
from simulation.tests.test_persistence_lazy_people import RULES, people_world
import ate_sim.core as core


def opened_fixture(tmp_path, count=300, *, household=False):
    world = people_world(count, active=8)
    if household:
        world.households[1] = Household(1, 1, list(range(1, count + 1)))
        world.next_household = 2
    cold = tmp_path / "cold.sqlite"
    lazy = tmp_path / "lazy.sqlite"
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, lazy, rules_id=RULES)
    return lazy


@pytest.mark.parametrize("count", [300, 900])
def test_r1_clean_traversal_releases_payload_and_runtime_placement(tmp_path, count):
    path = opened_fixture(tmp_path, count)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        people = session.world.people
        for key in range(1, count + 1):
            people[key]
        gc.collect()
        before = {
            "count": count, "resident": people.diagnostics()["resident_people"],
            "baselines": len(people._baseline_payload),
            "baseline_bytes": sum(map(len, people._baseline_payload.values())),
            "presence": len(people._baseline_presence),
            "incarnation": len(people._baseline_incarnation),
            "occurrences": session._registry.diagnostics()["occurrences"],
        }
        print("R1", before)
        assert before["resident"] <= 256
        assert before["baselines"] <= 256
        assert before["presence"] <= 256
        assert before["incarnation"] <= 256
        assert before["occurrences"] <= 256


def test_r2_public_digest_mutation_guard_and_scope_preflight(tmp_path, monkeypatch):
    path = opened_fixture(tmp_path, 25)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        person = session.world.people[1]
        before = person.wealth
        calls = []
        def callback(_world):
            calls.append("digest")
            with pytest.raises(StoreError):
                person.wealth += 10
            return "guarded"
        monkeypatch.setattr(core, "_digest_world_unchecked", callback)
        assert session.world.digest() == "guarded"
        assert person.wealth == before
        with session.world.current_people_scope():
            with pytest.raises(StoreError, match="current_people_scope"):
                session.world.digest()
        assert calls == ["digest"]
        assert session._lifecycle_operation is None
        person.wealth += 1


def test_r2_public_archive_scope_rejects_before_publication(tmp_path):
    path = opened_fixture(tmp_path, 25)
    target = tmp_path / "rejected-history.sqlite"
    with open_lazy_world_session(path, rules_id=RULES) as session:
        with session.world.current_people_scope():
            with pytest.raises(StoreError, match="current_people_scope"):
                export_archive(session.world, target, digest="already-computed")
        assert not target.exists()


@pytest.mark.parametrize("count", [1000, 10000])
def test_r3_fixed_household_open_does_not_materialize_whole_member_history(tmp_path, count):
    path = opened_fixture(tmp_path, count, household=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        members = session.world.households[1].members
        observed = {
            "historical": count, "length": len(members),
            "member_container_bytes": sys.getsizeof(members),
            "people_decoded": session.world.people.diagnostics()["person_payload_loads"],
        }
        print("R3", observed)
        assert len(members) == count
        assert list(members[:3]) == [1, 2, 3]
        assert observed["people_decoded"] == 0
        assert observed["member_container_bytes"] < 6000
