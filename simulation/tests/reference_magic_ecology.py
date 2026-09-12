"""Frozen market loop from 216c2660 for differential stabilization tests."""
from simulation.ate_sim.magic_resources import (
 _recover_dead_owner_resources, _discover, _wants, _aspiration,
 _commit_to_full_path, _make_resource, absorb_essence_resource,
 use_awakening_stone, _transfer_to_seeker,
)
from simulation.ate_sim.core_types import layer_ref

def legacy_magic_ecology_step(world,rng):
 Layer,Ref=layer_ref();_recover_dead_owner_resources(world);adults_by_settlement={sid:[] for sid in world.settlements}
 for p in world.people.values():
  if p.alive and p.age>=16:adults_by_settlement[p.settlement].append(p)
 for sid in adults_by_settlement:adults_by_settlement[sid].sort(key=lambda p:p.id)
 for sid,people in sorted(adults_by_settlement.items()):
  c=world.cells[(world.settlements[sid].x,world.settlements[sid].y)];rr=rng.stream('magic_discovery',world.year,sid);ambient=world.ambient_magic.field(sid).level
  chance=min(.16,.010+.00004*len(people)+.025*c.hazard+.008*c.forest+.04*max(0.,ambient-.5))
  if rr.random()<chance:_discover(world,rr,sid,people)
  for r in list(world.magic_resources.inventory('settlement',sid)):
   seekers=[p for p in people if _wants(world,p,r)]
   if seekers:
    q=max(seekers,key=lambda p:(_aspiration(world,p).urgency,_aspiration(world,p).drive,_aspiration(world,p).preparation,p.wealth,-p.id));price=(7 if r.kind=='essence' else 3)
    if q.wealth>=price:
     q.wealth-=price;e=world.emit('magic_resource_purchased',Layer.SOCIETY,(Ref('person',q.id),),Ref('settlement',sid),((r.origin_event,) if r.origin_event else ()),resource=r.id,key=r.key,price=price);world.magic_resources.transfer(r.id,'person',q.id,e.id,sid)
 adults=[p for sid in sorted(adults_by_settlement) for p in adults_by_settlement[sid]]
 for p in adults:
  rr=rng.stream('magic_use',world.year,p.id);a=_aspiration(world,p);path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences)
  if path is not None and not a.completion_goal and (a.adventurer_aspiration or a.drive>=.34):_commit_to_full_path(a)
  if a.desired_base_essences>base:
   a.search_years+=1;a.preparation=min(1.,a.preparation+.0025*(.5+a.drive+.5*a.urgency));sought=None
   if rr.random()<.015*(.4+a.drive+.4*a.urgency):sought=world.emit('magic_resource_sought',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),reason=a.reason,drive=round(a.drive,3),urgency=round(a.urgency,3),preparation=round(a.preparation,3),search_years=a.search_years,completion_goal=a.completion_goal)
   search_chance=min(.012,.00035+.0018*a.drive+.0020*a.preparation+.0018*a.urgency+.00008*min(30,a.search_years))
   if rr.random()<search_chance:_make_resource(world,rr,p.settlement,p,'essence',None if sought is None else sought.id,'aspirant search')
  essences=world.magic_resources.inventory('person',p.id,'essence')
  if essences and base<a.desired_base_essences and rr.random()<.15+.34*a.drive+.18*a.urgency:
   candidates=[r for r in essences if path is None or r.key not in path.base_essences]
   if candidates:
    take=a.compromise_tolerance if base>0 else max(.35,a.compromise_tolerance)
    if rr.random()<take:absorb_essence_resource(world,p.id,candidates[int(rr.random()*len(candidates))%len(candidates)].id);path=world.advancement.path(p.id);base=len(path.base_essences)
  stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
  if path is not None and stones and len(path.abilities)<min(a.desired_abilities,path.capacity) and rr.random()<.15+.34*a.drive+.18*a.urgency:
   if rr.random()<max(.12,1-a.stone_selectiveness):use_awakening_stone(world,p.id,stones[int(rr.random()*len(stones))%len(stones)].id)
  held=world.magic_resources.inventory('person',p.id)
  if held:
   surplus=[r for r in held if not _wants(world,p,r)]
   if surplus and rr.random()<.20:
    local=adults_by_settlement[p.settlement];pressure=0.
    for r in surplus:
     seekers=[q for q in local if q.id!=p.id and _wants(world,q,r)]
     if seekers:pressure=max(pressure,max((_aspiration(world,q).drive+.5*_aspiration(world,q).urgency)*(.35+.65*_aspiration(world,q).preparation) for q in seekers))
    conditional=(.04+.16*min(1.,pressure))/.20
    if rr.random()<conditional:_transfer_to_seeker(world,surplus[int(rr.random()*len(surplus))%len(surplus)],p,local,rr)
