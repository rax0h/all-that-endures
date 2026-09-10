from __future__ import annotations
from .core_types import layer_ref

ACTION_FUNCTIONS={
 'secure_food':{'creation','control','support','detection','recovery'},
 'prepare':{'enhancement','control','movement','detection','recovery'},
 'work':{'creation','enhancement','control','support','exchange','transformation'},
 'socialize':{'influence','support','detection','exchange'},
 'learn':{'detection','control','transformation','support'},
 'teach':{'influence','support','control','exchange'},
 'build':{'creation','enhancement','control','transformation'},
}

def rank_ecology_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society')
 members=set() if adv is None else adv.members
 latest={}
 for rec in reversed(world.agency.actions):
  if rec.year!=world.year:break
  latest.setdefault(rec.person,rec)
 for p in sorted((x for x in world.people.values() if x.alive),key=lambda x:x.id):
  path=world.advancement.path(p.id)
  if path is None or not path.abilities:continue
  rec=latest.get(p.id);action='work' if rec is None else rec.action;strength=.35 if rec is None else rec.strength;relevant=ACTION_FUNCTIONS.get(action,set())
  indexed=list(enumerate(path.abilities));weakest=min((a.rank,a.level,a.progress) for _,a in indexed)
  # Dedicated adventurers deliberately train weak links because personal rank is
  # constrained by the least-developed ability. Everyone else practices powers
  # that plausibly contributed to work and life that year.
  if p.id in members:
   candidates=[x for x in indexed if (x[1].rank,x[1].level,x[1].progress)<=weakest]
   if len(candidates)<4:candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))[:8]
   exposure=.32+.22*strength
  else:
   candidates=[x for x in indexed if x[1].function in relevant] or indexed
   exposure=.16+.20*strength
  rr=rng.stream('rank_ecology',world.year,p.id);rr.shuffle(candidates);uses=min(len(candidates),6 if p.id in members else 4);before=world.advancement.rank(p.id)
  for i,a in candidates[:uses]:
   reflection=(.45+.55*p.curiosity) if action in ('learn','teach','socialize') else .10*p.curiosity
   world.advancement.practice(p.id,i,exposure*(.8+.4*rr.random()),reflection)
  after=world.advancement.rank(p.id);p.rank=after
  if after>before:world.emit('rank_advanced',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),from_rank=before,to_rank=after,practice_context=action,dedicated_training=p.id in members)
