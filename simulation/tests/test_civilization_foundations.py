from ate_sim.culture import CulturalState, seed_practices, cultural_step
from ate_sim.social import SocialGraph
from ate_sim.genealogy import Genealogy
from ate_sim.economy import Economy
from ate_sim.knowledge import KnowledgeState
from ate_sim.worldgen import generate_world
from ate_sim.core import RNG

def test_culture_is_history_not_species_personality():
    w=generate_world(843000); c=CulturalState(); seed_practices(w,c)
    assert c.practices and all(not hasattr(p,'personality') for p in c.practices.values())
    before=len(c.practices); cultural_step(w,c,RNG(w.seed)); assert len(c.practices)>=before

def test_relationships_keep_shared_history():
    g=SocialGraph(); r=g.record(1,2,99,trust=.1,attachment=.2); assert 99 in r.shared_history and r.trust>.5

def test_genealogy_is_explicit():
    g=Genealogy(); g.birth(3,(1,2)); g.birth(4,(3,)); assert g.ancestors(4)=={1,2,3}

def test_property_provenance_survives_transfer():
    e=Economy(); p=e.create('workshop',1,'household',1,100,0,7); e.transfer(p.id,'person',2,12); assert p.provenance==[7,12]

def test_knowledge_separates_belief_from_truth():
    k=KnowledgeState(); cid=k.claim('river','is cursed',False,4); k.beliefs[(1,cid)]=.9; k.teach(1,2,cid,.8); assert k.claims[cid].truth is False and k.beliefs[(2,cid)]>0
