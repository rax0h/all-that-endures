from ate_sim.advancement import AdvancementState


def ready_understanding(skill, rank=3):
 skill.understanding.applications={'a':{},'b':{}}
 skill.understanding.transfers=[{'difficulty':5},{'difficulty':5}]
 skill.understanding.integration=5.


def path_with_one_skill():
 a=AdvancementState();a.absorb_essence(1,'fire',0);return a


def full_path():
 a=AdvancementState()
 for essence in ('fire','water','wind'):a.absorb_essence(1,essence,0)
 for essence in a.path(1).essences:
  for _ in range(4):a.awaken_skill(1,'eyes',1,target_essence=essence)
 return a


def test_iron_requires_four_essences_and_all_twenty_abilities():
 a=AdvancementState()
 for essence in ('fire','water'):
  a.absorb_essence(1,essence,0)
  assert a.rank(1)==0
 a.absorb_essence(1,'wind',0)
 assert len(a.path(1).abilities)==4 and a.rank(1)==0
 for essence in a.path(1).essences:
  for _ in range(4):a.awaken_skill(1,'eyes',1,target_essence=essence)
 assert len(a.path(1).abilities)==20 and a.rank(1)==1


def test_single_ability_cannot_carry_incomplete_body_to_diamond():
 a=path_with_one_skill()
 for _ in range(1000):a.practice(1,0,100.,reflection=100.)
 skill=a.path(1).abilities[0]
 assert (skill.rank,skill.level,skill.progress)==(2,0,0.)
 assert a.rank(1)==0


def test_all_twenty_abilities_gate_each_body_transition_and_ceiling():
 a=full_path();path=a.path(1)
 for target in range(2,6):
  for skill in path.abilities:ready_understanding(skill)
  # Gold additionally requires earned whole-path integration. This test isolates
  # the all-twenty structural gate, so explicitly satisfy that separate contract.
  if target==4:
   path.integration.reflected={skill.semantic_key:1. for skill in path.abilities}
   path.integration.essence_groups=set(path.essences)
   path.integration.contemplation=12.
  # Diamond structural testing isolates the separate no-core/revelation contract.
  if target==5:path.core_fraction=0.
  for i in range(19):
   a.practice(1,i,100000.)
   assert a.rank(1)==target-1
   skill=path.abilities[i]
   assert (skill.rank,skill.level,skill.progress)==(target,0,0.)
   a.practice(1,i,100000.)
   assert (skill.rank,skill.level,skill.progress)==(target,0,0.)
  a.practice(1,19,100000.)
  assert a.rank(1)==target


def test_gold_requires_whole_path_integration_beyond_twenty_silver_abilities():
 a=full_path();path=a.path(1)
 for skill in path.abilities:skill.rank=3;skill.level=9;skill.progress=.999;ready_understanding(skill)
 for i in range(20):a.practice(1,i,100000.)
 assert a.rank(1)==3
 assert all(skill.rank==3 for skill in path.abilities)
 assert 'path_integration' in a.blockers(1)
 path.integration.reflected={skill.semantic_key:1. for skill in path.abilities}
 path.integration.essence_groups=set(path.essences);path.integration.contemplation=12.
 for i in range(20):a.practice(1,i,100000.)
 assert a.rank(1)==4


def test_twenty_abilities_with_wrong_group_distribution_do_not_qualify():
 a=full_path()
 for skill in a.path(1).abilities:skill.rank=2
 a.path(1).abilities[-1].essence='fire'
 assert a.rank(1)==0
