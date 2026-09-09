from ate_sim.advancement import AdvancementState
from ate_sim.magic_catalog import ESSENCES,ESSENCE_IDS

def path_with_one_skill():
 a=AdvancementState();a.absorb_essence(1,'fire',0,('farmer','neutral','farmer'));return a

def test_full_semantic_catalog_is_loaded():
 assert len(ESSENCES)==62
 assert ESSENCE_IDS[0]=='dark' and ESSENCE_IDS[-1]=='visage'
 for key in ESSENCE_IDS:
  e=ESSENCES[key];assert e['source_innate'] and e['semantic_core'] and e['suggested_domains'] and e['suggested_functions'] and e['guardrail']

def test_absorbing_essence_intrinsically_awakens_catalog_innate():
 a=AdvancementState();p,created=a.absorb_essence(1,'fire',0,('farmer','neutral','farmer'));assert p.capacity==5 and len(p.abilities)==1 and created[0].name=='Flame Bolt' and not created[0].special and a.rank(1)==1

def test_every_catalog_essence_can_be_absorbed():
 for i,e in enumerate(ESSENCE_IDS):
  a=AdvancementState();p,created=a.absorb_essence(i,e,0,('tester','neutral','tester'));assert len(created)==1 and created[0].name==ESSENCES[e]['source_innate']

def test_three_base_essences_form_person_shaped_confluence_and_innate():
 a=AdvancementState();created=[]
 for e in ('fire','water','wind'):p,new=a.absorb_essence(1,e,0,('guardian','good','smith'));created+=new
 assert len(p.base_essences)==3 and p.confluence and p.confluence_name and p.capacity==20 and len(p.abilities)==4 and len(created)==4
 assert p.abilities_for(p.confluence)[0].source=='confluence'

def test_confluence_changes_with_class_alignment_and_profession():
 a=AdvancementState();b=AdvancementState()
 for e in ('fire','water','wind'):pa,_=a.absorb_essence(1,e,0,('guardian','good','smith'));pb,_=b.absorb_essence(1,e,0,('scholar','neutral','scribe'))
 assert (pa.confluence,pa.confluence_name)!=(pb.confluence,pb.confluence_name)

def test_fifth_ability_of_each_set_is_special():
 a=AdvancementState();p,_=a.absorb_essence(1,'fire',0)
 for i in range(4):a.awaken_skill(1,'eyes',i+1,('worker',i),target_essence='fire')
 skills=p.abilities_for('fire');assert len(skills)==5 and [x.special for x in skills]==[False,False,False,False,True]
 assert 'Ascendant' in skills[-1].name

def test_stones_cannot_create_sixth_skill():
 a=AdvancementState();p,_=a.absorb_essence(1,'fire',0)
 for i in range(8):a.awaken_skill(1,'eyes',i+1,('worker',i),target_essence='fire')
 assert len(p.abilities_for('fire'))==5

def test_unknown_essence_and_stone_are_rejected():
 a=AdvancementState()
 try:a.absorb_essence(1,'not-real',0);assert False
 except ValueError:pass
 a.absorb_essence(1,'fire',0)
 try:a.awaken_skill(1,'not-real',1);assert False
 except ValueError:pass

def test_rank_requires_every_actually_awakened_skill():
 a=path_with_one_skill();a.awaken_skill(1,'eyes',1,('farmer',));first=a.path(1).abilities[0]
 for _ in range(200):a.practice(1,0,1.)
 assert first.rank>1 and a.rank(1)==1

def test_gold_to_diamond_requires_revelation_and_integration():
 a=path_with_one_skill();p=a.path(1);p.abilities[0].rank=4;p.abilities[0].level=9;p.abilities[0].progress=.99;a.practice(1,0,1.,reflection=0.);assert a.rank(1)==4;p.revelation=p.integrated=1.;a.practice(1,0,1.,reflection=1.);assert a.rank(1)==5

def test_monster_core_dependence_impedes_gold_revelation():
 a=path_with_one_skill();b=path_with_one_skill()
 for _ in range(100):b.practice(1,0,0.,core=1.)
 a.path(1).abilities[0].rank=b.path(1).abilities[0].rank=4
 for _ in range(100):a.practice(1,0,0.,reflection=1.);b.practice(1,0,0.,reflection=1.)
 assert a.path(1).revelation>b.path(1).revelation
