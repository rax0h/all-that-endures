from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


def test_founder_expertise_has_event_provenance():
    w=generate_world(843000)
    seeded=[s for s in w.skills.skills.values() if s.provenance]
    assert seeded
    assert all(eid in w.event_ids for s in seeded for eid in s.provenance)


def test_expertise_accumulates_and_can_be_taught():
    w=generate_world(843000)
    before=sum(s.level for s in w.skills.skills.values())
    Simulation(w).run(80)
    after=sum(s.level for s in w.skills.skills.values())
    assert after>before
    taught=[e for e in w.events if e.kind=='skill_taught']
    assert taught
    assert any(t.kind=='apprenticeship' and t.item_kind=='skill' for t in w.transmission.records.values())


def test_infrastructure_has_lineage_and_decay_maintenance_history():
    w=generate_world(843000)
    initial=list(w.infrastructure.assets.values())
    assert initial
    assert all(("infrastructure",a.id) in w.lineage.nodes for a in initial)
    Simulation(w).run(300)
    roads=[a for a in w.infrastructure.assets.values() if a.kind=='road']
    assert roads
    assert all(0<=a.condition<=1 for a in w.infrastructure.assets.values())
    assert all(("infrastructure",a.id) in w.lineage.nodes for a in roads)


def test_agricultural_skill_affects_production_without_replacing_biology():
    w1=generate_world(843000);w2=generate_world(843000)
    for p in w2.people.values():
        if p.age>=18:w2.skills.get(p.id,'agriculture').level=1.0
    from ate_sim.engine import Simulation
    s1=Simulation(w1);s2=Simulation(w2)
    s1._weather();s2._weather();s1._production();s2._production()
    assert sum(s.food_stock for s in w2.settlements.values())>sum(s.food_stock for s in w1.settlements.values())
