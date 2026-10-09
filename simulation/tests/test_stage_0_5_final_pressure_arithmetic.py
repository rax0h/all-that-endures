"""Forced pressure preserves native ordered sum, occurrences and RNG calls."""
import math

import pytest

from ate_sim.core import World, Household, Settlement, Cell
from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-exact-pressure-arithmetic'


class ForcedHazard:
    def __init__(self):
        self.calls = []

    def stream(self, *key):
        rng = self
        class Stream:
            def random(self):
                rng.calls.append(key)
                return 0.
        return Stream()


def world_for(values, *, occurrences=None, shared=False):
    world = World(843000)
    for hid, value in enumerate(values, 1):
        world.households[hid] = Household(hid, 1, preparedness=value, alive=hid == 1)
    ids = list(range(1, len(values) + 1)) if occurrences is None else list(occurrences)
    world.cells[0, 0] = Cell(0, 0, 0., 0., 0., 0., 1000.)
    world.settlements[1] = Settlement(1, 0, 0, households=ids, defense=0., roads=0.)
    if shared:
        world.cells[1, 0] = Cell(1, 0, 0., 0., 0., 0., 1000.)
        world.settlements[2] = Settlement(2, 1, 0, households=ids, defense=0., roads=0.)
    return world


def pressure(world):
    sim = Simulation(world)
    rng = ForcedHazard()
    sim.rng = rng
    sim._pressure()
    return rng.calls


def event_values(world):
    return [(event.kind, event.data['preparedness'].hex(), event.data['severity'].hex())
            for event in world.events]


@pytest.mark.parametrize('values,occurrences', [
    ([1., 2.**-53, 2.**-107], None),
    ([1., 2.**-53], [1, 2, 2]),
    ([1., 2.**-53], None),
])
def test_forced_pressure_matches_eager_native_hex_and_rng_after_edit_and_reopen(tmp_path, values, occurrences):
    control = world_for(values, occurrences=occurrences)
    initial = world_for(values, occurrences=occurrences)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(initial, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    expected_mean = sum(initial.households[hid].preparedness for hid in initial.settlements[1].households) / len(initial.settlements[1].households)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert pressure(session.world) == pressure(control)
        assert event_values(session.world) == event_values(control)
        assert session.world.events[-1].data['preparedness'].hex() == (.25 * expected_mean).hex()
        # Repeated unsaved assignments cannot reuse an earlier numerator.
        for value in (2.**-52, 2.**-51):
            session.world.households[2].preparedness = value
            control.households[2].preparedness = value
            assert pressure(session.world) == pressure(control)
            assert event_values(session.world) == event_values(control)
        session.save()
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert event_values(session.world) == event_values(control)
        assert pressure(session.world) == pressure(control)
        assert event_values(session.world) == event_values(control)


def test_shared_occurrence_list_duplicates_and_replacement_keep_native_order(tmp_path):
    values = [1., 2.**-53]
    control = world_for(values, occurrences=[1, 2, 2], shared=True)
    initial = world_for(values, occurrences=[1, 2, 2], shared=True)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(initial, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert session.world.settlements[1].households is session.world.settlements[2].households
        for world in (control, session.world):
            world.settlements[1].households.insert(1, 1)
            world.settlements[2].households.remove(2)  # Native first-equal removal.
            world.households[2].preparedness = 2.**-52
        assert pressure(session.world) == pressure(control)
        assert event_values(session.world) == event_values(control)
        for world in (control, session.world):
            world.settlements[1].households = [2, 1, 2]
        assert pressure(session.world) == pressure(control)
        assert event_values(session.world) == event_values(control)
        session.save()
    with open_lazy_world_session(target, rules_id=RULES) as session:
        assert session.world.settlements[1].households is not session.world.settlements[2].households
        assert pressure(session.world) == pressure(control)
        assert event_values(session.world) == event_values(control)


def test_native_counterexamples_reject_fsum_page_subtotals_and_subtract_add():
    values = [1., 2.**-53, 2.**-107]
    assert sum(values).hex() == '0x1.0000000000000p+0'
    assert math.fsum(values).hex() == '0x1.0000000000001p+0'
    values = [1., 2.**-53, 2.**-53]
    assert sum(values).hex() == '0x1.0000000000001p+0'
    assert sum([sum(values[:2]), sum(values[2:])]).hex() == '0x1.0000000000000p+0'
    changed = sum([1., 2.**-53]) - 2.**-53 + 2.**-52
    assert changed.hex() == '0x1.0000000000000p+0'
    assert sum([1., 2.**-52]).hex() == '0x1.0000000000001p+0'
