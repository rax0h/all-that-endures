"""Normal older-world updates must save and reopen against eager controls."""
import copy

from ate_sim.engine import Simulation
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.worldgen import generate_world


def test_year_60_world_continues_exactly_through_two_saved_years(tmp_path):
    rules = 'stage-0-5-aged-identity-save'
    world = generate_world(843000, width=6, height=6, settlements=1)
    Simulation(world).run(60)
    control = copy.deepcopy(world)
    expected = {}
    for year in (61, 62):
        Simulation(control).run(1)
        expected[year] = control.digest()
    cold, source, target = (tmp_path / name for name in ('cold.sqlite', 'lazy.sqlite', 'complete.sqlite'))
    write_cold_snapshot(world, cold, rules_id=rules)
    convert_cold_to_lazy(cold, source, rules_id=rules,
                         native_graph_buckets=True, counted_households=True)
    upgrade_lazy_snapshot(source, target, rules_id=rules)
    for year in (61, 62):
        with open_lazy_world_session(target, rules_id=rules) as session:
            before = session.pin.captured_head
            Simulation(session.world).run(1)
            assert session.world.year == year
            assert session.save() == before + 1
        with open_lazy_world_session(target, rules_id=rules) as session:
            assert session.world.year == year
            assert session.world.digest() == expected[year]
