from copy import deepcopy
from simulation.ate_sim import Simulation, generate_world
from simulation.ate_sim.core import RNG
from simulation.ate_sim.agency import agency_step
from simulation.tests.reference_agency import legacy_agency_step

def test_living_adjacency_matches_full_relationship_archive():
    world = Simulation(generate_world(843000)).run(20)
    people = [p for p in world.people.values() if p.alive and p.age >= 16]
    a,b = people[:2]
    world.social.get(a.id,b.id).attachment = .95
    b.alive = False  # The living person's attachment to the deceased still matters.
    indexed = deepcopy(world)
    legacy_agency_step(world,RNG(world.seed))
    agency_step(indexed,RNG(indexed.seed))
    assert world.digest() == indexed.digest()

def test_agency_does_not_scan_global_relationships():
    world = generate_world(17)
    for n in range(10000):
        world.social.get(100000+n,200000+n)
    class NoValues(dict):
        def values(self): raise AssertionError("global relationship scan")
    world.social.edges = NoValues(world.social.edges)
    agency_step(world,RNG(world.seed))
