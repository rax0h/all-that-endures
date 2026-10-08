"""Experimental opt-in integration gate for paged household membership.

These must pass before R3 can be promoted into PR #14.
"""
import pytest

from ate_sim.core import Household
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from simulation.tests.test_persistence_lazy_people import people_world, RULES


def make(tmp_path, count):
    world = people_world(count, active=8)
    world.households[1] = Household(1, 1, list(range(1, count+1)))
    world.next_household = 2
    source = tmp_path / "cold.sqlite"
    target = tmp_path / "paged.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    result = convert_cold_to_lazy(
        source, target, rules_id=RULES, paged_household_members=True
    )
    assert result["source_preserved"]
    return world, target


@pytest.mark.parametrize("count", [1000, 10000])
def test_r3_world_open_digest_append_atomic_save_reopen(tmp_path, count):
    original, path = make(tmp_path, count)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        seq = session.world.households[1].members
        assert len(seq) == count
        assert seq[:3] == [1, 2, 3]
        assert seq[-1] == count
        assert session.world.people.diagnostics()["person_payload_loads"] == 0
        assert seq.diagnostics()["resident_cached_pages"] <= 4
        assert session.world.digest() == original.digest()
        seq.append(count+1)
        original.households[1].members.append(count+1)
        assert session.world.digest() == original.digest()
        session.store.reset_diagnostics()
        generation = session.pin.captured_head
        assert session.save() == generation + 1
        d=session.store.diagnostics()
        print("PAGED WORLD",count,d.payload_writes,d.payload_write_bytes)
        assert d.payload_writes < 20
        assert session.world.digest() == original.digest()

    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.digest() == original.digest()
        assert reopened.world.households[1].members[-1] == count+1


def test_r3_mutation_scope_and_noop_saves(tmp_path):
    world, path = make(tmp_path, 250)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        seq=session.world.households[1].members
        generation=session.pin.captured_head
        session.store.reset_diagnostics()
        assert session.save() == generation
        assert session.store.diagnostics().payload_writes == 0
        with session.world.current_people_scope():
            from ate_sim.incremental_store import StoreError
            with pytest.raises(StoreError):
                seq.append(251)
        assert len(seq)==250
