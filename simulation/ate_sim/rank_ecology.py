from __future__ import annotations
from .core_types import layer_ref
from .magic_resources import _aspiration

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
 """Return (candidates_mode, exposure, uses, purposeful_reflection).

 Full-time adventurers do not stop training after Bronze. Their annual tick represents a
 year of contracts, drills, sparring, expeditions and deliberate work on weak abilities.
 The curve intentionally steepens by rank: Iron->Bronze is commonly a few good years;
 Bronze->Silver is a longer professional career step; Silver->Gold takes sustained elite
 effort; Gold->Diamond is an exceptional multi-decade/century pursuit whose revelation
 gate must also be satisfied. This creates opportunity for Diamond without guaranteeing it.
 """
 rank=world.advancement.rank(p.id);complete=len(path.abilities)==20
 dedicated=complete and (member or asp.adventurer_aspiration)
 if not dedicated:return None
 ambition=max(0.,min(1.,.45*asp.drive+.30*asp.urgency+.25*p.curiosity))
 if rank==1:return ('all',5.4+1.8*strength+.8*asp.urgency,20,.18+.22*p.curiosity)
 if rank==2:return ('all',2.15+.75*strength+.55*ambition,20,.22+.28*p.curiosity)
 if rank==3:
  if not member and ambition<.52:return None
  return ('all',1.15+.45*strength+.45*ambition,20,.38+.35*p.curiosity)
 if rank==4:
  # Gold adventurers need both institutional/field continuity and exceptional personal
  # commitment. The Diamond gate is still enforced in AdvancementState.practice.
  if not member or ambition<.56:return None
  return ('all',1.05+.35*strength+.45*ambition,20,.72+.28*p.curiosity)
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
   # Deliberate rank training targets the weakest links first, but a full professional
   # year is broad enough to exercise the entire configuration.
   candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))
  elif member:
   candidates=[x for x in indexed if (x[1].rank,x[1].level,x[1].progress)<=weakest]
   if len(candidates)<4:candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))[:8]
   exposure=.32+.22*strength;uses=min(len(candidates),6)
  else:
   candidates=[x for x in indexed if x[1].function in relevant] or indexed
   exposure=.16+.20*strength;uses=min(len(candidates),4)
  rr=rng.stream('rank_ecology',world.year,p.id);rr.shuffle(candidates);before=world.advancement.rank(p.id)
  for i,a in candidates[:uses]:
   reflection=purposeful_reflection if purposeful_reflection is not None else ((.45+.55*p.curiosity) if action in ('learn','teach','socialize') else .10*p.curiosity)
   world.advancement.practice(p.id,i,exposure*(.8+.4*rr.random()),reflection)
  after=world.advancement.rank(p.id);p.rank=after
  if after>before:world.emit('rank_advanced',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),from_rank=before,to_rank=after,practice_context=action,dedicated_training=career is not None or member)
