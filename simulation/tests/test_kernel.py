from simulation.ate_sim import *

def test_determinism():
    a=Simulation(generate_world(42)).run(100); b=Simulation(generate_world(42)).run(100); assert a.digest()==b.digest()
def test_seed_divergence():
    assert Simulation(generate_world(42)).run(50).digest()!=Simulation(generate_world(43)).run(50).digest()
def test_causal_integrity():
    w=Simulation(generate_world(7)).run(200); ids={e.id for e in w.events}; assert all(c in ids and c<e.id for e in w.events for c in e.causes)
def test_persistent_identity():
    w=generate_world(9); ids=set(w.people); Simulation(w).run(100); assert ids.issubset(w.people)
