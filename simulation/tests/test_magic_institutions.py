from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.magic_resources import absorb_essence_resource,use_awakening_stone
from ate_sim.institutions import ensure_core_societies,register_magic_user,institution_step
from ate_sim.semantic_dictionary import ESSENCES,AWAKENING_STONES
from ate_sim.core import Layer,Ref,RNG


def _adult(w):
 return next(p for p in w.people.values() if p.alive and p.age>=18 and not w.advancement.essence_user(p.id))


def test_essence_resource_must_exist_and_is_consumed_with_provenance():
 w=generate_world(843000);p=_adult(w)
 found=w.emit('test_essence_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='fire')
 r=w.magic_resources.create('essence','fire',ESSENCES['fire']['rarity'],w.year,p.settlement,'person',p.id,found.id)
 path,created=absorb_essence_resource(w,p.id,r.id)
 assert path.base_essences[-1]=='fire'
 assert len(created)==1 and created[0].name==ESSENCES['fire']['source_innate']
 assert r.consumed_by==p.id and r.consumed_event is not None
 absorbed=next(e for e in w.events if e.id==r.consumed_event)
 assert found.id in absorbed.causes and absorbed.data['resource']==r.id


def test_three_real_essence_resources_form_confluence_immediately():
 w=generate_world(843000);p=_adult(w);last=None
 for key in ('fire','water','wind'):
  found=w.emit('test_essence_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence=key)
  r=w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],w.year,p.settlement,'person',p.id,found.id)
  last,_=absorb_essence_resource(w,p.id,r.id)
  assert r.consumed_by==p.id
 assert last is not None
 assert last.base_essences==['fire','water','wind']
 assert last.confluence is not None
 assert len(last.essences)==4
 assert len(last.abilities)==4
 assert len(last.abilities_for(last.confluence))==1
 assert last.abilities_for(last.confluence)[0].source=='confluence'


def test_stone_is_real_property_and_fifth_slot_is_special():
 w=generate_world(843001);p=_adult(w)
 f=w.emit('test_essence_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='fire')
 er=w.magic_resources.create('essence','fire',ESSENCES['fire']['rarity'],w.year,p.settlement,'person',p.id,f.id)
 absorb_essence_resource(w,p.id,er.id)
 made=[]
 for i in range(4):
  sf=w.emit('test_stone_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),stone='Eyes')
  sr=w.magic_resources.create('awakening_stone','Eyes',AWAKENING_STONES['Eyes']['rarity'],w.year,p.settlement,'person',p.id,sf.id)
  made.append(use_awakening_stone(w,p.id,sr.id,'fire'))
  assert sr.consumed_by==p.id
 assert [a.special for a in w.advancement.path(p.id).abilities_for('fire')]==[False,False,False,False,True]
 assert made[-1].special


def test_completed_loadout_has_four_specials_and_exactly_one_aura():
 from ate_sim.advancement import AdvancementState
 a=AdvancementState();pid=1
 for essence in ('fire','water','wind'):
  path,_=a.absorb_essence(pid,essence,0,('guardian','good','smith','river-city'))
 for target in path.essences:
  while len(path.abilities_for(target))<5:a.awaken_skill(pid,'Eyes',1,('guardian','good','smith','river-city'),target_essence=target)
 assert len(path.abilities)==20
 assert sum(x.special for x in path.abilities)==4
 assert sum(x.aura for x in path.abilities)==1


def test_societies_have_causal_branches_notices_and_limited_registry_knowledge():
 w=generate_world(843000);ensure_core_societies(w)
 adventure=w.institutions.institution_by_kind('adventure_society');magic=w.institutions.institution_by_kind('magic_society')
 assert adventure and magic and adventure.origin_event and magic.origin_event
 assert all(w.institutions.branches[b].origin_event for b in adventure.branches+magic.branches)
 p=_adult(w)
 found=w.emit('test_hidden_essence',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='dark')
 r=w.magic_resources.create('essence','dark',ESSENCES['dark']['rarity'],w.year,p.settlement,'person',p.id,found.id);absorb_essence_resource(w,p.id,r.id)
 assert not w.institutions.records_for_person(p.id)
 identity=register_magic_user(w,p.id,'identity')
 assert identity.essence_ids==() and identity.abilities==()
 full=register_magic_user(w,p.id,'full')
 assert full.essence_ids and full.abilities
 threat=w.emit('monster_surge',Layer.REALITY,location=Ref('settlement',p.settlement),severity=.4)
 institution_step(w,RNG(w.seed))
 notice=next(n for n in w.institutions.notices.values() if n.cause_event==threat.id)
 assert notice.location==p.settlement and notice.status=='open'
