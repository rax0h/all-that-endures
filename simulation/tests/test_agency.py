from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.core import RNG


def test_scarcity_changes_person_motives():
    w=generate_world(843000);p=next(x for x in w.people.values() if x.age>=16)
    w.local[p.settlement].scarcity=0.;low=w.agency.assess(w,p).hunger
    w.local[p.settlement].scarcity=1.;high=w.agency.assess(w,p).hunger
    assert high>low


def test_agency_produces_actions_and_expertise():
    w=generate_world(843000);Simulation(w).run(5)
    assert w.agency.actions
    assert any(s.practice>0 for s in w.skills.skills.values())
    assert {a.action for a in w.agency.actions}.issubset({'secure_food','prepare','work','socialize','learn','teach','build'})


def test_agency_is_deterministic():
    a=generate_world(843000);b=generate_world(843000)
    Simulation(a).run(20);Simulation(b).run(20)
    assert a.digest()==b.digest()
