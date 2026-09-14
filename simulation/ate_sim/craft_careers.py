from __future__ import annotations
from .core_types import layer_ref
from .materials import _craft_once

def craft_career_step(world,rng):
 Layer,Ref=layer_ref()
 for sid,people in sorted(world.living_by_settlement().items()):
  adults=[p for p in people if p.age>=16]
  if not adults:continue
  masters=[p for p in adults if world.skills.get(p.id,'craft').level>=2.5 and world.advancement.rank(p.id)>0]
  apprentices=[p for p in adults if .5<=world.skills.get(p.id,'craft').level<2.5 and p.curiosity>.45]
  # Apprenticeships arise only where a real magical master exists.
  for a in apprentices[:min(3,len(masters))]:
   if not masters:break
   rr=rng.stream('craft_apprentice',world.year,a.id);m=masters[int(rr.random()*len(masters))%len(masters)]
   if rr.random()<.22:
    world.skills.practice(a.id,'craft',.35+.25*m.curiosity);a.occupation='craft apprentice';e=world.emit('craft_apprenticeship',Layer.SOCIETY,(Ref('person',m.id),Ref('person',a.id)),Ref('settlement',sid),master=m.id,apprentice=a.id)
    world.social.record(m.id,a.id,e.id,trust=.05,attachment=.04,obligation=.08)
  # Masters with real material supply produce repeat work. This increases low-rank
  # magical goods through careers and commissions, not through an item spawn bonus.
  for m in masters:
   if not world.materials.has_available(sid):continue
   rr=rng.stream('craft_career',world.year,m.id);demand=.18+.25*world.settlements[sid].prosperity+.15*world.local[sid].scarcity
   magic_branch=world.institutions.branch_for('magic_society',sid)
   if magic_branch is not None:demand+=.18
   attempts=1+(1 if rr.random()<min(.75,demand) else 0)
   made=0
   for n in range(attempts):
    cr=rng.stream('career_commission',world.year,m.id*10+n)
    if _craft_once(world,sid,m,cr,Layer,Ref):made+=1
   if made:
    m.occupation='magical craftsperson';world.emit('craft_career_work',Layer.SOCIETY,(Ref('person',m.id),),Ref('settlement',sid),items=made,magic_society=magic_branch is not None)
