from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.culture import cultural_step


class _ForcedInnovationRNG:
    """Deterministic test RNG: force the innovation branch without a 1000-year wait."""
    def stream(self,*args,**kwargs): return self
    def random(self): return 0.0
    def uniform(self,a,b): return (a+b)/2


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


def test_migration_can_found_traceable_diaspora():
    w=generate_world(843000)
    Simulation(w).run(300)
    diasporas=[c for c in w.communities.communities.values() if c.kind=="diaspora"]
    assert diasporas
    for c in diasporas:
        assert c.parent is not None
        node=w.lineage.nodes[("community",c.id)]
        assert ("community",c.parent) in node.parents
    assert any(t.kind=="diaspora_formation" for t in w.transmission.records.values())


def test_practice_variants_keep_parent_lineage_when_they_occur():
    # Test the invariant directly instead of hoping a rare random branch fires in 1000 years.
    w=generate_world(843000)
    sid=min(w.settlements)
    parent=next(p for p in w.culture.practices.values() if p.origin_settlement==sid)
    w.culture.adoption[(sid,parent.id)]=0.8
    before=set(w.culture.practices)
    w.year+=1
    cultural_step(w,w.culture,_ForcedInnovationRNG())
    variants=[p for p in w.culture.practices.values() if p.id not in before and p.parent is not None]
    assert variants
    for p in variants:
        node=w.lineage.nodes[("practice",p.id)]
        assert node.origin_event in w.event_ids
        assert ("practice",p.parent) in node.parents
        records=[t for t in w.transmission.records.values() if t.kind=="innovation" and t.item_kind=="practice" and t.item_id==p.id]
        assert records
        assert all(t.event_id in w.event_ids for t in records)
        assert all(t.source_kind=="practice" and t.source_id==p.parent for t in records)


def test_property_ownership_history_survives_transfer():
    w=generate_world(843000)
    prop=next(iter(w.economy.property.values()))
    original=prop.ownership[0]
    event=next(iter(w.events))
    w.economy.transfer(prop.id,"person",1,event.id,w.year)
    assert prop.ownership[0]==original
    assert prop.ownership[-1][1:3]==("person",1)
    assert len(prop.ownership)==2
