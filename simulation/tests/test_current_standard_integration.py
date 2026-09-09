from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.core import Layer


def test_current_standard_runs_and_is_deterministic():
    a=generate_world(843000); b=generate_world(843000)
    Simulation(a).run(120); Simulation(b).run(120)
    assert a.digest()==b.digest()
    assert a.year==120
    assert all(e.layer in Layer for e in a.events)
    assert all(c in a.event_ids for e in a.events for c in e.causes)


def test_genealogy_property_culture_and_regions_are_live():
    w=generate_world(843001)
    initial_practices=len(w.culture.practices)
    Simulation(w).run(180)
    assert w.genealogy.parents
    assert w.economy.property
    assert len(w.culture.practices)>=initial_practices
    assert all(sid in w.local for sid in w.settlements)
    assert any(e.kind in {"trade_exchange","institution_founded","law_adopted","practice_innovated","household_migrated","household_split"} for e in w.events)


def test_species_is_not_culture_and_culture_is_not_a_person_field():
    w=generate_world(843002)
    assert all(not hasattr(p,"culture") for p in w.people.values())
    assert all(not hasattr(p,"morality") for p in w.people.values())
    assert len({p.species for p in w.people.values()})>1


def test_causal_references_reject_fabrication():
    w=generate_world(843003)
    try:
        w.emit("impossible",Layer.NARRATIVE,causes=(999999,))
    except ValueError:
        pass
    else:
        raise AssertionError("fabricated causal references must be rejected")
