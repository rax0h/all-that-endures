from __future__ import annotations
from .core_types import layer_ref
from .institutions import apply_for_society,full_essence_user,register_magic_user
from .magic_resources import _aspiration

def society_career_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society');mag=world.institutions.institution_by_kind('magic_society')
 # Registration is a record, not membership. Full users with a local Magic Society
 # branch may disclose independently; members are strongly likely to maintain a record.
 recorded={r.person for r in world.institutions.magic_records.values()}
 for p in sorted((x for x in world.people.values() if x.alive and full_essence_user(world,x.id)),key=lambda x:x.id):
  if p.id in recorded:continue
  b=world.institutions.branch_for('magic_society',p.settlement)
  if b is None:continue
  rr=rng.stream('magic_registry',world.year,p.id);member=mag is not None and p.id in mag.members
  if rr.random()<(.70 if member else .025):
   register_magic_user(world,p.id,'full' if member else ('essences' if rr.random()<.55 else 'identity'));recorded.add(p.id)
 # Failed candidates can improve and reapply after a real cooldown instead of being
 # permanently excluded by their first attempt.
 for society,inst in (('adventure_society',adv),('magic_society',mag)):
  if inst is None:continue
  latest={}
  for a in world.institutions.applications.values():
   if a.society==society and (a.person not in latest or a.id>latest[a.person].id):latest[a.person]=a
  for p in sorted((x for x in world.people.values() if x.alive and full_essence_user(world,x.id) and x.id not in inst.members),key=lambda x:x.id):
   a=latest.get(p.id)
   if a is None or a.passed is None or a.passed or world.year-a.applied_year<3:continue
   aspiration=_aspiration(world,p);intent=aspiration.adventurer_aspiration if society=='adventure_society' else (p.curiosity>.55 or world.skills.get(p.id,'knowledge').level>1 or world.skills.get(p.id,'craft').level>1)
   if not intent:continue
   rr=rng.stream('society_reapply',world.year,p.id+(0 if society=='adventure_society' else 1000000))
   if rr.random()<.18+.35*aspiration.persistence:
    apply_for_society(world,p.id,society);world.emit('society_reapplication',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),society=society,previous_application=a.id)
 # Adventure notices become actual work. Members accept local contracts, resolve
 # them through capability/readiness, and receive traceable rewards.
 if adv is None:return
 for n in sorted(world.institutions.notices.values(),key=lambda x:x.id):
  if n.status=='open':
   candidates=[world.people[pid] for pid in adv.members if pid in world.people and world.people[pid].alive and world.people[pid].settlement==n.location]
   if candidates:
    candidates.sort(key=lambda p:(world.advancement.rank(p.id),world.skills.get(p.id,'defense').level,p.health,-p.id),reverse=True);leader=candidates[0];rr=rng.stream('notice_accept',world.year,n.id)
    if rr.random()<.45:
     n.status='assigned';n.assigned_to=leader.id;world.emit('adventure_notice_accepted',Layer.SOCIETY,(Ref('person',leader.id),),Ref('settlement',n.location),causes=(n.cause_event,),notice=n.id)
  if n.status=='assigned' and n.assigned_to in world.people:
   p=world.people[n.assigned_to]
   if not p.alive:n.status='open';n.assigned_to=None;continue
   rr=rng.stream('notice_resolve',world.year,n.id);cap=.22+.10*world.advancement.rank(p.id)+.08*world.skills.get(p.id,'defense').level+.18*p.health
   if rr.random()<min(.85,cap):
    reward=2.+4.*cap;p.wealth+=reward;e=world.emit('adventure_notice_resolved',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',n.location),causes=(n.cause_event,),notice=n.id,reward=round(reward,2));n.status='resolved';n.resolved_event=e.id
