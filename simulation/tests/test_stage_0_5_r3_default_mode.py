"""R3 default bounded storage with explicit legacy P4 compatibility."""
import sys

import pytest

from ate_sim.core import Household
from ate_sim.incremental_store import StoreFormatError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from simulation.tests.test_persistence_lazy_people import RULES, people_world


def _source(tmp_path, count=1000):
    world = people_world(count, active=8)
    world.households[1] = Household(1, 1, list(range(1, count + 1)))
    world.next_household = 2
    source = tmp_path / "cold.sqlite"
    write_cold_snapshot(world, source, rules_id=RULES)
    return world, source


def test_default_conversion_and_open_use_checked_bounded_pages(tmp_path):
    world, source = _source(tmp_path)
    target = tmp_path / "default.sqlite"
    assert convert_cold_to_lazy(source, target, rules_id=RULES)["source_preserved"]
    with open_lazy_world_session(target, rules_id=RULES) as session:
        members = session.world.households[1].members
        assert members == world.households[1].members
        assert sys.getsizeof(members) < 1024
        assert members.diagnostics()["resident_cached_pages"] <= 4
        assert session.world.digest() == world.digest()
        members.append(1001)
        world.households[1].members.append(1001)
        session.save()
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert session.world.digest() == world.digest()
        assert session.world.households[1].members[-1] == 1001
        with pytest.raises(StoreFormatError):
            open_lazy_world_session(target, rules_id=RULES, paged_household_members=False)


def test_unpaged_legacy_store_opens_by_default_and_explicitly(tmp_path):
    world, source = _source(tmp_path, 20)
    legacy = tmp_path / "legacy.sqlite"
    convert_cold_to_lazy(source, legacy, rules_id=RULES, paged_household_members=False)
    for requested_mode in (None, False):
        with open_lazy_world_session(
            legacy, rules_id=RULES, paged_household_members=requested_mode
        ) as session:
            assert type(session.world.households[1].members) is list
            assert session.world.digest() == world.digest()
    with pytest.raises(StoreFormatError):
        open_lazy_world_session(legacy, rules_id=RULES, paged_household_members=True)
