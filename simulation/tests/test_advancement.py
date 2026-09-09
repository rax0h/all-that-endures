from ate_sim.worldgen import generate_world
from ate_sim.advancement import AdvancementState

def test_founder_essence_users_have_twenty_abilities_and_iron_rank():
 w=generate_world(843000)
 assert w.advancement.paths
 for pid,path in w.advancement.paths.items():
  assert len(path.abilities)==20
  assert w.people[pid].rank==1
  assert w.advancement.rank(pid)==1

def test_rank_requires_whole_ability_set_not_one_power():
 a=AdvancementState();a.awaken(1)
 for _ in range(200):a.practice(1,0,1.0)
 assert a.rank(1)==1

def test_gold_to_diamond_requires_revelation_and_integration():
 a=AdvancementState();p=a.awaken(1)
 for ability in p.abilities:
  ability.rank=4;ability.level=9;ability.progress=.99
 for i in range(20):a.practice(1,i,1.0,reflection=0.)
 assert a.rank(1)==4
 p.revelation=p.integrated=1.0
 for i in range(20):a.practice(1,i,1.0,reflection=1.)
 assert a.rank(1)==5

def test_monster_core_dependence_impedes_gold_revelation():
 a=AdvancementState();b=AdvancementState();a.awaken(1);b.awaken(1)
 for _ in range(100):b.practice(1,0,0.,core=1.)
 for state in (a,b):
  for ability in state.path(1).abilities:ability.rank=4
 for _ in range(100):
  a.practice(1,0,0.,reflection=1.);b.practice(1,0,0.,reflection=1.)
 assert a.path(1).revelation>b.path(1).revelation
