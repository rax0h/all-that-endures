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
            # Births happen inside this scope; mutation is valid, but
            # a save/digest lifecycle operation cannot run mid-scope.
            seq.append(251)
            from ate_sim.incremental_store import StoreError
            with pytest.raises(StoreError):
                session.save()
        assert len(seq)==251


def test_r3_eager_household_scalar_edit_and_member_append_share_save(tmp_path):
    original, path = make(tmp_path, 1000)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        h = session.world.households[1]
        h.food += 7.5
        h.members.append(1001)
        original.households[1].food += 7.5
        original.households[1].members.append(1001)
        assert session.world.digest() == original.digest()
        prior = session.pin.captured_head
        assert session.save() == prior + 1
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.digest() == original.digest()
        assert reopened.world.households[1].food == original.households[1].food


def test_r3_materializing_detach_restores_real_list_and_checkpoint(tmp_path):
    from ate_sim import checkpoint
    original, path = make(tmp_path, 1000)
    session = open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    )
    detached = session.detach(materialize_history=True)
    assert type(detached.households[1].members) is list
    assert detached.digest() == original.digest()
    assert checkpoint.loads(checkpoint.dumps(detached)).digest() == original.digest()


def test_r3_stale_second_writer_cannot_publish_members(tmp_path):
    from ate_sim.incremental_store import StoreConflictError
    original, path = make(tmp_path, 1000)
    winner = open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    )
    loser = open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    )
    try:
        winner.world.households[1].members.append(1001)
        loser.world.households[1].members.append(2001)
        prior = winner.pin.captured_head
        assert winner.save() == prior + 1
        with pytest.raises(StoreConflictError):
            loser.save()
        assert loser.world.households[1].members[-1] == 2001
    finally:
        winner.close()
        loser.close()
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.households[1].members[-1] == 1001


def test_r3_new_household_publishes_compact_owner_and_pages(tmp_path):
    original, path = make(tmp_path, 1000)
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as session:
        added = Household(2, 1, [9, 9, 11])
        session.world.households[2] = added
        session.world.next_household = 3
        original.households[2] = Household(2, 1, [9, 9, 11])
        original.next_household = 3
        assert session.world.digest() == original.digest()
        prior = session.pin.captured_head
        assert session.save() == prior + 1
        assert list(session.world.households[2].members) == [9, 9, 11]
        assert session.world.digest() == original.digest()
    with open_lazy_world_session(
        path, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.digest() == original.digest()
        assert reopened.world.households[2].members == [9, 9, 11]


def test_r3_deleted_household_owner_retained_alias_is_detached(tmp_path):
    original, path = make(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as session:
        old_members = session.world.households[1].members
        del session.world.households[1]
        del original.households[1]
        # Stale aliases remain their own mutable values and cannot resurrect
        # deleted canonical household members.
        old_members.append(12345)
        before = session.pin.captured_head
        assert session.save() == before + 1
        assert session.world.digest() == original.digest()
        assert old_members[-1] == 12345
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as reopened:
        assert not reopened.world.households
        assert reopened.world.digest() == original.digest()


def test_r3_replaced_household_same_id_preserves_old_alias_detachment(tmp_path):
    original, path = make(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as session:
        old_members = session.world.households[1].members
        replacement = Household(1, 1, [42, 42, 7], food=25.0)
        session.world.households[1] = replacement
        original.households[1] = Household(1, 1, [42, 42, 7], food=25.0)
        old_members.append(99999)
        prior = session.pin.captured_head
        assert session.save() == prior + 1
        assert session.world.households[1].members == [42, 42, 7]
        assert old_members[-1] == 99999
        assert session.world.digest() == original.digest()
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as reopened:
        assert reopened.world.digest() == original.digest()
        assert reopened.world.households[1].members == [42, 42, 7]
