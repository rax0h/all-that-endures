from __future__ import annotations
from .core_types import layer_ref
from .institutions import apply_for_society,full_essence_user,register_magic_user
from .magic_resources import _aspiration
from .currency import ranked_reward,value_of
from .magic_economy import spirit_economy_step,magical_services_step,apprenticeship_step,treasury_liquidity_step

def society_career_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society');mag=world.institutions.institution_by_kind('magic_society')
 living=world.living_by_settlement();alive=list(world.current_people())
 full_users=[p for p in alive if full_essence_user(world,p.id)]
 recorded=world.institutions.recorded_people()

 # Registry growth reads the current population, never the historical record archive.
 for p in full_users:
  if p.id in recorded:continue
  b=world.institutions.branch_for('magic_society',p.settlement)
  if b is None:continue
  rr=rng.stream('magic_registry',world.year,p.id);member=mag is not None and p.id in mag.members
  if rr.random()<(.70 if member else .025):
   register_magic_user(world,p.id,'full' if member else ('essences' if rr.random()<.55 else 'identity'));recorded.add(p.id)

 # Failed applications can be retried after a real cooldown without rescanning
 # every application ever filed.
 for society,inst in (('adventure_society',adv),('magic_society',mag)):
  if inst is None:continue
  for p in full_users:
   if p.id in inst.members:continue
   a=world.institutions.latest_application(p.id,society)
   if a is None or a.passed is None or a.passed or world.year-a.applied_year<3:continue
   aspiration=_aspiration(world,p)
   intent=(aspiration.adventurer_aspiration and world.advancement.rank(p.id)>=1) if society=='adventure_society' else (p.curiosity>.55 or world.skills.get(p.id,'knowledge').level>1 or world.skills.get(p.id,'craft').level>1)
   if not intent:continue
   rr=rng.stream('society_reapply',world.year,p.id+(0 if society=='adventure_society' else 1000000));persistence=min(1.,.45*aspiration.drive+.35*aspiration.preparation+.20*aspiration.urgency)
   if rr.random()<.18+.35*persistence:
    apply_for_society(world,p.id,society);world.emit('society_reapplication',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),society=society,previous_application=a.id)

 if adv is None:return

 # Money, institutional reproduction and services are separate processes.
 spirit_economy_step(world,rng)
 treasury_liquidity_step(world,adv.id,alive)
 apprenticeship_step(world)
 magical_services_step(world,rng)

 living_members=[p for p in alive if p.id in adv.members]
 members_by_settlement={sid:[] for sid in world.settlements}
 for p in living_members:members_by_settlement[p.settlement].append(p)

 for n in sorted(world.institutions.active_notices(),key=lambda x:x.id):
  resolution=world.threat_ecology.resolutions.get(n.cause_event)
  if n.status!='resolved' and n.kind=='ranked_magic_manifested' and resolution is not None:
   event=world.event(resolution)
   actual=None if event is None else next((ref.id for ref in event.actors if ref.kind=='person'),None)
   if actual in adv.members and actual in world.people and world.people[actual].alive:
    n.assigned_to=actual;n.status='assigned'

  if n.status=='open':
   candidates=[p for p in members_by_settlement.get(n.location,()) if world.advancement.rank(p.id)>=n.required_rank]
   if not candidates and n.required_rank>=3:
    candidates=[p for p in living_members if world.advancement.rank(p.id)>=n.required_rank and world.infrastructure.route_condition(p.settlement,n.location)>0]
   if candidates:
    candidates.sort(key=lambda p:(world.advancement.rank(p.id),world.skills.get(p.id,'defense').level,p.health,-p.id),reverse=True);leader=candidates[0];rr=rng.stream('notice_accept',world.year,n.id)
    if rr.random()<.45:
     n.status='assigned';n.assigned_to=leader.id;world.emit('adventure_notice_accepted',Layer.SOCIETY,(Ref('person',leader.id),),Ref('settlement',n.location),causes=(n.cause_event,),notice=n.id)

  if n.status=='assigned' and n.assigned_to in world.people:
   p=world.people[n.assigned_to]
   if not p.alive:n.status='open';n.assigned_to=None;continue
   resolution=world.threat_ecology.resolutions.get(n.cause_event)
   if n.kind=='ranked_magic_manifested':
    if resolution is None:continue
    event=world.event(resolution)
    if event is None or not any(ref.kind=='person' and ref.id==p.id for ref in event.actors):continue
   rr=rng.stream('notice_resolve',world.year,n.id);rank=world.advancement.rank(p.id);cap=.22+.10*rank+.08*world.skills.get(p.id,'defense').level+.18*p.health
   if rr.random()<min(.85,cap):
    coins=ranked_reward(n.required_rank,1.,include_change=False);treasury=world.currency.treasuries.get(adv.id,{})
    if any(treasury.get(d,0)<v for d,v in coins.items()):continue
    world.currency.treasury_transfer(adv.id,p.id,coins)
    e=world.emit('adventure_notice_resolved',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',n.location),causes=(n.cause_event,) if resolution is None else (n.cause_event,resolution),notice=n.id,stipend=0.,coin_reward=coins,treasury=adv.id,coin_value_lesser=value_of(coins),reward_rank=n.required_rank,responder_rank=rank)
    n.status='resolved';n.resolved_event=e.id
