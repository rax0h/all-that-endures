from unittest.mock import patch
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.core import World


def test_population_index_birth_death_resurrection_and_archive():
    world=generate_world(843000)
    assert tuple(p.id for p in world.current_people())==tuple(p.id for p in world.people.values() if p.alive)
    Simulation(world).run(10)
    assert tuple(p.id for p in world.current_people())==tuple(p.id for p in world.people.values() if p.alive)


def test_scope_clears_on_exception():
    world=generate_world(843000)
    try:
        with world.current_people_scope():
            raise RuntimeError('boom')
    except RuntimeError:
        pass
    assert '_current_people_cache' not in world.__dict__
    assert '_index_current_people' not in world.__dict__


def test_indexed_population_matches_archive_scan_simulation():
    indexed=Simulation(generate_world(843000)).run(100)
    with patch.object(World,'current_people',lambda w:tuple(p for p in w.people.values() if p.alive)):
        reference=Simulation(generate_world(843000)).run(100)
    # The research branch intentionally changes world history. Keep this
    # fixture branch-local while still proving the living-population index is
    # semantically identical to a full archive scan.
    assert indexed.digest()==reference.digest()=='ca69c2cda3ff92c1d5fb96fe073c3faeb8022e5d690ce2744fdf89ad7355d298'
