from __future__ import annotations
from .core_types import layer_ref
from .institutions import apply_for_society,full_essence_user,register_magic_user
from .magic_resources import _aspiration
from .currency import ranked_reward,value_of
from .magic_economy import spirit_economy_step,magical_services_step,apprenticeship_step

def society_career_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society');mag=world.institutions.institution_by_kind('magic_society')
 living=world.living_by_settlement();alive=sorted((p for people in living.values() for p in people),key=lambda x:x.id)
 recorded=set(world.institutions.recorded_people())
 for p in (x for x in alive if full_essence_user(world,x.id)):
  if p.id in recorded:continue
  b=world.institutions.branch_for('magic_society',p.settlement)
  if b is None:continue
  rr=rng.stream('magic_registry',world.year,p.id);member=mag is not None and p.id in mag.members
  if rr.random()<(.70 if member else .025):
   register_magic_user(world,p.id,'full' if member else ('essences' if rr.random()<.55 else 'identity'));recorded.add(p.id)
 for society,inst in (('adventure_society',adv),('magic_society',mag)):
  if inst is None:continue
  latest=world.institutions.latest_applications(society)
  for p in (x for x in alive if full_essence_user(world,x.id) and x.id not in inst.members):
   a=latest.get(p.id)
   if a is None or a.passed is None or a.passed:continue
   attempts=world.institutions.application_attempt_count(p.id,society)
   cooldown=min(96,3*(2**min(5,max(0,attempts-1))))
   if world.year-a.applied_year<cooldown:continue
   aspiration=_aspiration(world,p)
   if society=='adventure_society' and world.advancement.rank(p.id)<1:continue
   intent=aspiration.adventurer_aspiration if society=='adventure_society' else (p.curiosity>.55 or world.skills.get(p.id,'knowledge').level>1 or world.skills.get(p.id,'craft').level>1)
   if not intent:continue
   path=world.advancement.path(p.id);rank=world.advancement.rank(p.id);defense=world.skills.get(p.id,'defense').level;knowledge=world.skills.get(p.id,'knowledge').level
   threshold=.52 if society=='magic_society' else .60
   # Do not let failed applicants repeatedly buy lottery tickets when their
   # present capabilities cannot possibly clear one of the three assessments.
   physical_cap=min(1.,.25+.08*p.rank+.25*p.health+.20)
   magical_cap=min(1.,.25+.025*len(path.abilities)+.08*rank+.20)
   judgment_cap=min(1.,.30+.22*p.inhibition+.18*p.curiosity+.04*defense+.04*knowledge+.15)
   if min(physical_cap,magical_cap,judgment_cap)<threshold:continue
   rr=rng.stream('society_reapply',world.year,p.id+(0 if society=='adventure_society' else 1000000));persistence=min(1.,.45*aspiration.drive+.35*aspiration.preparation+.20*aspiration.urgency)
   if rr.random()<.18+.35*persistence:
    apply_for_society(world,p.id,society);world.emit('society_reapplication',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),society=society,previous_application=a.id,attempt=attempts+1,cooldown=cooldown)
 if adv is None:return
 # Reuse one living-population index across the three Society economy passes.
 spirit_economy_step(world,rng,living)
 apprenticeship_step(world,living)
 magical_services_step(world,rng,living)
 for n in world.institutions.active_notices():
  # Event-backed notices without a persistent world object are operational
  # opportunities, not immortal obligations. If nobody solved them while the
  # event was current, they age out of the live queue but remain in history.
  if n.kind!='ranked_magic_manifested' and world.year-n.year>=5:
   n.status='expired';n.assigned_to=None
   world.emit('adventure_notice_expired',Layer.SOCIETY,location=Ref('settlement',n.location),
              causes=(n.cause_event,),notice=n.id,notice_kind=n.kind,age=world.year-n.year)
   continue
  resolution=world.threat_ecology.resolutions.get(n.cause_event)
  if n.kind=='ranked_magic_manifested' and resolution is not None:
   event=world.events[resolution-1]
   actual=next((ref.id for ref in event.actors if ref.kind=='person'),None)
   # Once the underlying threat is gone, the notice cannot remain assigned
   # forever. Society members can still receive the normal verified reward;
   # an outside/dead resolver closes the obsolete notice without payment.
   if actual in adv.members and world.people.get(actual) is not None and world.people[actual].alive:
    n.assigned_to=actual;n.status='assigned'
   else:
    n.status='resolved';n.assigned_to=actual;n.resolved_event=resolution
    continue
  if n.status=='open':
   candidates=[world.people[pid] for pid in adv.members if pid in world.people and world.people[pid].alive and world.people[pid].settlement==n.location and world.people[pid].rank>=n.required_rank]
   if not candidates and n.required_rank>=3:
    candidates=[world.people[pid] for pid in adv.members if pid in world.people and world.people[pid].alive and world.advancement.rank(pid)>=n.required_rank and world.infrastructure.route_condition(world.people[pid].settlement,n.location)>0]
   if candidates:
    candidates.sort(key=lambda p:(p.rank,world.skills.get(p.id,'defense').level,p.health,-p.id),reverse=True);leader=candidates[0];rr=rng.stream('notice_accept',world.year,n.id)
    if rr.random()<.45:
     n.status='assigned';n.assigned_to=leader.id;world.emit('adventure_notice_accepted',Layer.SOCIETY,(Ref('person',leader.id),),Ref('settlement',n.location),causes=(n.cause_event,),notice=n.id)
  if n.status=='assigned' and n.assigned_to in world.people:
   p=world.people[n.assigned_to]
   if not p.alive:n.status='open';n.assigned_to=None;continue
   resolution=world.threat_ecology.resolutions.get(n.cause_event)
   if n.kind=='ranked_magic_manifested':
    if resolution is None:continue
    event=world.events[resolution-1]
    if not any(ref.kind=='person' and ref.id==p.id for ref in event.actors):continue
   rr=rng.stream('notice_resolve',world.year,n.id);rank=p.rank;cap=.22+.10*rank+.08*world.skills.get(p.id,'defense').level+.18*p.health
   if rr.random()<min(.85,cap):
    # Job difficulty sets the denomination. A known ranked threat must really
    # have been resolved by this claimant before the Society can pay.
    coins=ranked_reward(n.required_rank,1.,include_change=False)
    treasury=world.currency.treasuries.get(adv.id,{})
    if any(treasury.get(d,0)<v for d,v in coins.items()):continue
    world.currency.treasury_transfer(adv.id,p.id,coins)
    stipend=0.
    e=world.emit('adventure_notice_resolved',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',n.location),causes=(n.cause_event,) if resolution is None else (n.cause_event,resolution),notice=n.id,stipend=round(stipend,2),coin_reward=coins,treasury=adv.id,coin_value_lesser=value_of(coins),reward_rank=n.required_rank,responder_rank=rank)
    n.status='resolved';n.resolved_event=e.id
