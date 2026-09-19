from simulation.ate_sim import *

def test_determinism():
    a=Simulation(generate_world(42)).run(100); b=Simulation(generate_world(42)).run(100); assert a.digest()==b.digest()
def test_seed_divergence():
    assert Simulation(generate_world(42)).run(50).digest()!=Simulation(generate_world(43)).run(50).digest()
def test_causal_integrity():
    w=Simulation(generate_world(7)).run(200); ids={e.id for e in w.events}; assert all(c in ids and c<e.id for e in w.events for c in e.causes)
def test_persistent_identity():
    w=generate_world(9); ids=set(w.people); Simulation(w).run(100); assert ids.issubset(w.people)


def test_longevity_event_pruning_preserves_ids_recent_payloads_and_protected_evidence():
    w=World(1)
    protected=w.emit('protected',Layer.REALITY)
    w.year=1;old=w.emit('old',Layer.REALITY)
    w.year=20;recent=w.emit('recent',Layer.REALITY)
    assert w.prune_event_payloads_before_year(10,{protected.id})==2
    assert w.event(protected.id) is protected
    assert w.event(old.id) is None
    assert w.event(recent.id) is recent
    assert [e.id for e in w.events_between(20,20)]==[recent.id]
    derived=w.emit('derived',Layer.REALITY,causes=(old.id,))
    assert derived.causes==(old.id,)
