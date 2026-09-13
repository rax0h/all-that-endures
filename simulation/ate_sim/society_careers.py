from __future__ import annotations
from .core_types import layer_ref
from .institutions import apply_for_society,full_essence_user,register_magic_user
from .magic_resources import _aspiration
from .currency import ranked_reward,value_of

def society_career_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society');mag=world.institutions.institution_by_kind('magic_society')
 recorded={r.person for r in world.institutions.magic_records.values()}
 for p in sorted((x for x in world.current_people() if x.alive and full_essence_user(world,x.id)),key=lambda x:x.id):
  if p.id in recorded:continue
  b=world.institutions.branch_for('magic_society',p.settlement)
  if b is None:continue
  rr=rng.stream('magic_registry',world.year,p.id);member=mag is not None and p.id in mag.members
  if rr.random()<(.70 if member else .025):
   register_magic_user(world,p.id,'full' if member else ('essences' if rr.random()<.55 else 'identity'));recorded.add(p.id)
 for society,inst in (('adventure_society',adv),('magic_society',mag)):
  if inst is None:continue
  latest={}
  for a in world.institutions.applications.values():
   if a.society==society and (a.person not in latest or a.id>latest[a.person].id):latest[a.person]=a
  for p in sorted((x for x in world.current_people() if x.alive and full_essence_user(world,x.id) and x.id not in inst.members),key=lambda x:x.id):
   a=latest.get(p.id)
   if a is None or a.passed is None or a.passed or world.year-a.applied_year<3:continue
   aspiration=_aspiration(world,p);intent=aspiration.adventurer_aspiration if society=='adventure_society' else (p.curiosity>.55 or world.skills.get(p.id,'knowledge').level>1 or world.skills.get(p.id,'craft').level>1)
   if not intent:continue
   rr=rng.stream('society_reapply',world.year,p.id+(0 if society=='adventure_society' else 1000000));persistence=min(1.,.45*aspiration.drive+.35*aspiration.preparation+.20*aspiration.urgency)
   if rr.random()<.18+.35*persistence:
    apply_for_society(world,p.id,society);world.emit('society_reapplication',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),society=society,previous_application=a.id)
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
   rr=rng.stream('notice_resolve',world.year,n.id);rank=world.advancement.rank(p.id);cap=.22+.10*rank+.08*world.skills.get(p.id,'defense').level+.18*p.health
   if rr.random()<min(.85,cap):
    # The Society pays at the adventurer's operative rank. The exact job amount varies with
    # difficulty/capability, but denomination exchange values are invariant and higher ranks
    # receive higher-rank magical coinage rather than enormous piles of low-rank currency.
    coins=ranked_reward(rank,.75+cap);world.currency.credit(p.id,coins)
    stipend=1.+2.*cap;p.wealth+=stipend
    e=world.emit('adventure_notice_resolved',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',n.location),causes=(n.cause_event,),notice=n.id,stipend=round(stipend,2),coin_reward=coins,coin_value_lesser=value_of(coins),reward_rank=rank)
    n.status='resolved';n.resolved_event=e.id
