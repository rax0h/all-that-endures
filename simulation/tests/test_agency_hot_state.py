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

def test_relationship_reference_index_tracks_mutations_additions_and_checkpoint():
    import pickle
    from simulation.ate_sim.social import SocialGraph
    graph=SocialGraph()
    a=graph.get(1,2)
    assert list(graph.relationships_for(1))==[a]
    a.attachment=.8
    assert max(r.attachment for r in graph.relationships_for(1))==.8
    b=graph.record(1,3,1,attachment=.9)
    assert set(id(r) for r in graph.relationships_for(1))=={id(a),id(b)}
    graph.record(1,3,2,attachment=-.5)
    assert max(r.attachment for r in graph.relationships_for(1))==.8
    restored=pickle.loads(pickle.dumps(graph))
    restored.edges[(1,2)].attachment=.1
    assert max(r.attachment for r in restored.relationships_for(1))==.4

def test_relationship_reference_index_empty_endpoints_and_legacy_rebuild():
    from simulation.ate_sim.social import SocialGraph
    graph=SocialGraph()
    assert list(graph.relationships_for(1))==[]
    assert list(graph.relationships_for(2))==[]
    edge=graph.get(2,1)
    assert list(graph.relationships_for(1))==[edge]
    assert list(graph.relationships_for(2))==[edge]
    del graph._relationships  # Checkpoints created before this derived cache.
    assert list(graph.relationships_for(2))==[edge]
    assert list(graph.relationships_for(1))==[edge]
