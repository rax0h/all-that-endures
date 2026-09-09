from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


def test_founders_have_community_and_lineage():
    w=generate_world(843000)
    assert w.communities.communities
    assert all(w.communities.memberships_for(p.id) for p in w.people.values())
    assert all(("person",p.id) in w.lineage.nodes for p in w.people.values())
    assert all(("property",pid) in w.lineage.nodes for pid in w.economy.property)


def test_birth_inherits_overlapping_community_history():
    w=generate_world(843000)
    initial=set(w.people)
    Simulation(w).run(80)
    born=[p for p in w.people.values() if p.id not in initial and p.parents]
    assert born
    child=born[0]
    assert ("person",child.id) in w.lineage.nodes
    assert set(w.lineage.nodes[("person",child.id)].parents)=={("person",x) for x in child.parents}
    assert w.communities.memberships_for(child.id)
    assert any(t.item_kind=="community_membership" and t.target_kind=="person" and t.target_id==child.id for t in w.transmission.records.values())


def test_practice_variants_keep_parent_lineage_when_they_occur():
    w=generate_world(843000)
    Simulation(w).run(1000)
    variants=[p for p in w.culture.practices.values() if p.parent is not None]
    assert variants
    for p in variants:
        node=w.lineage.nodes[("practice",p.id)]
        assert ("practice",p.parent) in node.parents
        assert any(t.kind=="innovation" and t.item_kind=="practice" and t.item_id==p.id for t in w.transmission.records.values())


def test_property_ownership_history_survives_transfer():
    w=generate_world(843000)
    prop=next(iter(w.economy.property.values()))
    original=prop.ownership[0]
    event=next(iter(w.events))
    w.economy.transfer(prop.id,"person",1,event.id,w.year)
    assert prop.ownership[0]==original
    assert prop.ownership[-1][1:3]==("person",1)
    assert len(prop.ownership)==2
