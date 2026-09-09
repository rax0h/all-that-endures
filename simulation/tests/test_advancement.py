from ate_sim.advancement import AdvancementState

def path_with_one_skill():
 a=AdvancementState();a.absorb_essence(1,'fire',0,('farmer',));a.awaken_skill(1,'feast',0,('farmer','drought'));return a

def test_essence_does_not_grant_twenty_skills():
 a=AdvancementState();p=a.absorb_essence(1,'fire',0)
 assert p.capacity==5 and p.abilities==[] and a.rank(1)==0
 a.awaken_skill(1,'feast',1,('farmer',))
 assert len(p.abilities)==1 and a.rank(1)==1

def test_three_base_essences_create_one_confluence_and_capacity_twenty():
 a=AdvancementState()
 for e in ('fire','water','wind'):a.absorb_essence(1,e,0,('patient','curious'))
 p=a.path(1);assert len(p.base_essences)==3 and p.confluence is not None and len(p.essences)==4 and p.capacity==20

def test_stones_only_awaken_actual_capacity():
 a=AdvancementState();a.absorb_essence(1,'fire',0)
 for i in range(12):a.awaken_skill(1,'stone-'+str(i),i,('worker',i))
 assert len(a.path(1).abilities)==5

def test_rank_requires_every_actually_awakened_skill():
 a=path_with_one_skill();a.awaken_skill(1,'eyes',1,('farmer',))
 first=a.path(1).abilities[0]
 for _ in range(200):a.practice(1,0,1.)
 assert first.rank>1 and a.rank(1)==1

def test_gold_to_diamond_requires_revelation_and_integration():
 a=path_with_one_skill();p=a.path(1);p.abilities[0].rank=4;p.abilities[0].level=9;p.abilities[0].progress=.99
 a.practice(1,0,1.,reflection=0.);assert a.rank(1)==4
 p.revelation=p.integrated=1.;a.practice(1,0,1.,reflection=1.);assert a.rank(1)==5

def test_monster_core_dependence_impedes_gold_revelation():
 a=path_with_one_skill();b=path_with_one_skill()
 for _ in range(100):b.practice(1,0,0.,core=1.)
 a.path(1).abilities[0].rank=b.path(1).abilities[0].rank=4
 for _ in range(100):a.practice(1,0,0.,reflection=1.);b.practice(1,0,0.,reflection=1.)
 assert a.path(1).revelation>b.path(1).revelation
