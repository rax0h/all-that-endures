"""No-op and one-owner saves must not read every historical household label.

The full household graph is currently bound on open, but ordinary post-open
save metadata cost must be independent of the number of unchanged households.
"""
import pytest

from ate_sim.core import Household
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from simulation.tests.test_persistence_lazy_people import people_world, RULES


def create_world(tmp_path, households):
    world = people_world(0)
    for hid in range(1, households + 1):
        world.households[hid] = Household(hid, 1, [1] if hid == 1 else [])
    world.next_household = households + 1
    source = tmp_path / "touched-save-cold.sqlite"
    target = tmp_path / "touched-save-lazy.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    result = convert_cold_to_lazy(
        source, target, rules_id=RULES, paged_household_members=True
    )
    assert result["source_preserved"]
    return world, target


@pytest.mark.parametrize("households", [100, 1000])
def test_noop_save_checks_no_historical_member_identity_inventory(
    tmp_path, households,
):
    _world, target = create_world(tmp_path, households)
    with open_lazy_world_session(
        target, rules_id=RULES, paged_household_members=True
    ) as session:
        previous = session.pin.captured_head
        session.store.reset_diagnostics()
        assert session.save() == previous
        stats = session.store.diagnostics()
        print("NOOP", households, stats.metadata_rows, stats.payload_reads)
        assert stats.metadata_rows <= 180
        assert stats.payload_writes == 0


@pytest.mark.parametrize("households", [100, 1000])
def test_one_scalar_owner_save_does_not_refresh_all_member_labels(
    tmp_path, households,
):
    original, target = create_world(tmp_path, households)
    with open_lazy_world_session(
        target, rules_id=RULES, paged_household_members=True
    ) as session:
        unchanged_members = session.world.households[1].members
        assert unchanged_members[0] == 1
        session.world.households[households].food += 2.0
        original.households[households].food += 2.0
        previous = session.pin.captured_head
        session.store.reset_diagnostics()
        assert session.save() == previous + 1
        stats = session.store.diagnostics()
        print("ONE_OWNER", households, stats.metadata_rows, stats.payload_reads)
        assert stats.metadata_rows <= 220
        # An untouched retained page proxy must follow the committed pin.
        assert unchanged_members[0] == 1
        assert session.world.digest() == original.digest()
    with open_lazy_world_session(
        target, rules_id=RULES, paged_household_members=True
    ) as reopened:
        assert reopened.world.digest() == original.digest()
