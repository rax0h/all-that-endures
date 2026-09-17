from __future__ import annotations
from .core_types import layer_ref
from .magic_progression import practice_ability,record_body_transition
from .magic_resources import _aspiration
from .mastery_training import mastery_training_step

ACTION_FUNCTIONS={
 'secure_food':{'creation','control','support','detection','recovery'},
 'prepare':{'enhancement','control','movement','detection','recovery'},
 'work':{'creation','enhancement','control','support','exchange','transformation'},
 'socialize':{'influence','support','detection','exchange'},
 'learn':{'detection','control','transformation','support'},
 'teach':{'influence','support','control','exchange'},
 'build':{'creation','enhancement','control','transformation'},
}

def _career_training(world,p,path,asp,member,strength):
 """Deliberate whole-path training for people actually pursuing rank mastery.

 A complete path makes a person Iron; it does not put them on an automatic
 conveyor to Diamond. Bronze is sustained use, Silver a serious career, Gold
 elite deliberate mastery, and Diamond exceptional long-lived integration.
 The gates are causal effort/evidence requirements rather than population caps.
 """
 rank=world.advancement.rank(p.id);complete=len(path.abilities)==20
 if not complete:return None
 ambition=max(0.,min(1.,.45*asp.drive+.30*asp.urgency+.25*p.curiosity))
 combat=asp.adventurer_aspiration or p.occupation in ('adventurer','guard','hunter','soldier')
 professional=member or combat
 if rank==1:
  if not professional and ambition<.58:return None
  return ('all',2.15+.70*strength+.45*ambition,12,.14+.18*p.curiosity)
 if rank==2:
  if not professional or ambition<.42:return None
  return ('all',1.05+.38*strength+.32*ambition,10,.22+.24*p.curiosity)
 if rank==3:
  # Gold should exist in a millennium world, but only among established Society
  # members with sustained above-normal commitment and real transfer evidence.
  if not member or ambition<.55:return None
  return ('all',.72+.24*strength+.28*ambition,10,.46+.32*p.curiosity)
 if rank==4:
  # Diamond remains a historical-person result: an exceptional Gold must keep
  # training broadly for years and independently satisfy the stricter two-proof
  # revelation/integration gate in AdvancementState.
  if not member or ambition<.72 or p.curiosity<.60:return None
  return ('all',.16+.06*strength+.08*ambition,4,.80+.18*p.curiosity)
 return None

def rank_ecology_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society')
 members=set() if adv is None else adv.members
 latest={}
 for rec in reversed(world.agency.actions):
  if rec.year!=world.year:break
  latest.setdefault(rec.person,rec)
 for p in sorted((x for x in world.current_people() if x.alive),key=lambda x:x.id):
  path=world.advancement.path(p.id)
  if path is None or not path.abilities:continue
  rec=latest.get(p.id);action='work' if rec is None else rec.action;strength=.35 if rec is None else rec.strength;relevant=ACTION_FUNCTIONS.get(action,set())
  indexed=list(enumerate(path.abilities));weakest=min((a.rank,a.level,a.progress) for _,a in indexed);asp=_aspiration(world,p);member=p.id in members
  career=_career_training(world,p,path,asp,member,strength)
  purposeful_reflection=None
  if career is not None:
   _,exposure,uses,purposeful_reflection=career
   candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))
  elif member:
   candidates=[x for x in indexed if (x[1].rank,x[1].level,x[1].progress)<=weakest]
   if len(candidates)<4:candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))[:8]
   exposure=.24+.16*strength;uses=min(len(candidates),5)
  else:
   candidates=[x for x in indexed if x[1].function in relevant] or indexed
   exposure=.11+.14*strength;uses=min(len(candidates),3)
  rr=rng.stream('rank_ecology',world.year,p.id);rr.shuffle(candidates);before=world.advancement.rank(p.id)
  for i,a in candidates[:uses]:
   reflection=purposeful_reflection if purposeful_reflection is not None else ((.45+.55*p.curiosity) if action in ('learn','teach','socialize') else .10*p.curiosity)
   practice_ability(world,p,i,exposure*(.8+.4*rr.random()),reflection,context=action)
  # Understanding trials are relevant only to Silver/Gold advancement. Keeping
  # them out of the Iron/Bronze hot path preserves the millennium performance gate.
  body_rank=world.advancement.rank(p.id)
  if len(path.abilities)==20 and body_rank>=3 and (member or action in ('work','learn','teach','build','prepare')):
   mastery_training_step(world,p,path,rng.stream('mastery_training',world.year,p.id))
  after=world.advancement.rank(p.id);p.rank=after
  record_body_transition(world,p,before,context=action)
