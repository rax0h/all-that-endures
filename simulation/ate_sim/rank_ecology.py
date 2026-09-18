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

def _martial_school_context(world,rng,living,adventure_members):
 """Maintain a sparse network of lineage-rooted specialist training schools.

 Schools are historical communities, not rank factories. Silver+ Society veterans
 can found them, family members inherit them through the normal community system,
 and a bounded number of complete-path students can be accepted. Their only direct
 progression effect is access to better deliberate practice from living mentors.
 """
 schools=[c for c in world.communities.communities.values() if c.active and c.kind=='martial_school']
 by_sid={}
 for p in living:by_sid.setdefault(p.settlement,[]).append(p)

 if world.year%5==0:
  existing_by_sid={}
  for school in schools:existing_by_sid.setdefault(school.origin_settlement,[]).append(school)
  Layer,Ref=layer_ref()
  for sid,people in sorted(by_sid.items()):
   local=list(existing_by_sid.get(sid,()))
   max_schools=max(1,min(3,1+len(people)//220))
   if len(local)>=max_schools:continue
   founders=[p for p in people if p.id in adventure_members and p.rank>=3 and p.age>=24]
   founders.sort(key=lambda p:(p.rank,world.skills.get(p.id,'defense').level,p.curiosity,-p.id),reverse=True)
   for founder in founders:
    if len(local)>=max_schools:break
    if any(world.communities.memberships.get((founder.id,s.id),0.)>=.2 for s in local):continue
    family=[x for x in people if x.id!=founder.id and x.household==founder.household]
    family_practitioners=sum(world.advancement.essence_user(x.id) for x in family)
    cid=world.communities.next_community
    e=world.emit('martial_school_founded',Layer.SOCIETY,(Ref('person',founder.id),),Ref('settlement',sid),
                 school=cid,founder_rank=founder.rank,
                 household=founder.household,family_practitioners=family_practitioners,
                 basis='accomplished adventuring tradition and specialist instruction')
    school=world.communities.create('martial_school',world.year,sid,e.id)
    world.lineage.register('community',school.id,(('person',founder.id),),e.id,world.year)
    world.communities.join(founder.id,school.id,1.)
    for kin in family:world.communities.join(kin.id,school.id,.78 if world.advancement.essence_user(kin.id) else .58)
    local.append(school);schools.append(school)

 if not schools:return {}
 school_ids={s.id for s in schools}
 members_by_school={sid:[] for sid in school_ids}
 already_school=set()
 # Never scan the historical membership archive here. It contains every dead
 # ancestor and grows for the entire millennium. Query the existing per-person
 # membership index for the bounded living population instead.
 for person in living:
  for cid,strength in world.communities.memberships_for(person.id,.18).items():
   if cid not in school_ids:continue
   school=world.communities.communities[cid]
   if person.settlement!=school.origin_settlement:continue
   members_by_school[cid].append((person,strength));already_school.add(person.id)

 # Schools occasionally accept outsiders, but instruction remains scarce and
 # teacher-limited. This creates a real route through Bronze/Silver without a
 # population target or a global advancement multiplier.
 if world.year%3==0:
  Layer,Ref=layer_ref()
  for school in sorted(schools,key=lambda s:s.id):
   members=members_by_school.get(school.id,[])
   teachers=[p for p,_ in members if p.rank>=3]
   if not teachers:continue
   teacher=max(teachers,key=lambda p:(p.rank,world.skills.get(p.id,'defense').level,-p.id))
   mentor_rank=teacher.rank
   active_students=sum(1 for p,_ in members if 1<=p.rank<=3)
   seats=max(0,min(10,2+2*mentor_rank)-active_students)
   if seats<=0:continue
   candidates=[]
   for p in by_sid.get(school.origin_settlement,()):
    if p.id in already_school or p.age<16:continue
    path=world.advancement.path(p.id);rank=p.rank
    if path is None or len(path.abilities)!=20 or rank not in (1,2,3):continue
    a=_aspiration(world,p)
    defense=world.skills.get(p.id,'defense').level
    if not (a.adventurer_aspiration or defense>=.65 or p.curiosity>=.62):continue
    score=.35*min(1.,defense/2.)+.25*p.curiosity+.20*a.drive+.20*a.preparation
    candidates.append((score,p))
   candidates.sort(key=lambda x:(x[0],-x[1].id),reverse=True)
   for _,student in candidates[:seats]:
    world.communities.join(student.id,school.id,.62);already_school.add(student.id)
    e=world.emit('martial_school_student_accepted',Layer.SOCIETY,
                 (Ref('person',teacher.id),Ref('person',student.id)),Ref('settlement',school.origin_settlement),
                 ((school.origin_event,) if school.origin_event else ()),school=school.id,
                 teacher_rank=mentor_rank,student_rank=student.rank)
    world.social.record(teacher.id,student.id,e.id,trust=.025,obligation=.02)
    members_by_school[school.id].append((student,.62))

 mentor_for_person={}
 for school in schools:
  members=members_by_school.get(school.id,[])
  mentor=max((p.rank for p,_ in members),default=0)
  if mentor<3:continue
  for p,strength in members:
   if strength>=.18:mentor_for_person[p.id]=max(mentor_for_person.get(p.id,0),mentor)
 return mentor_for_person

def _career_training(world,p,path,asp,member,strength,school_rank=0):
 """Return (candidates_mode, exposure, uses, purposeful_reflection).

 Iron is the broad professional base. Bronze and Silver take sustained careers;
 specialist schools improve the lower/middle climb when accomplished mentors
 actually exist. Gold requires elite continuity, and Diamond remains an
 exceptional lifetime culmination rather than the default fate of a survivor.
 """
 rank=p.rank;complete=len(path.abilities)==20
 dedicated=complete and (member or asp.adventurer_aspiration or school_rank>=3)
 if not dedicated:return None
 ambition=max(0.,min(1.,.45*asp.drive+.30*asp.urgency+.25*p.curiosity))
 if rank==1:
  school_boost=.45 if school_rank>=3 else 0.
  return ('all',4*(1.20+.40*strength+.20*asp.urgency+school_boost),5,.18+.22*p.curiosity)
 if rank==2:
  school_boost=.32 if school_rank>=3 else 0.
  return ('all',4*(.82+.28*strength+.24*ambition+school_boost),5,.24+.28*p.curiosity)
 if rank==3:
  elite_school=school_rank>=4
  if not elite_school and not member and ambition<.68:return None
  return ('all',4*(.48+.18*strength+.20*ambition+(.18 if elite_school else 0.)),5,.42+.35*p.curiosity)
 if rank==4:
  # Gold-to-Diamond must remain possible without a Diamond teacher, but only for
  # unusually committed practitioners; a Diamond mentor is a genuine advantage.
  diamond_school=school_rank>=5
  if not member or (not diamond_school and ambition<.82):return None
  return ('all',4*(.38+.12*strength+.15*ambition+(.10 if diamond_school else 0.)),5,.78+.22*p.curiosity)
 return None

def rank_ecology_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society')
 members=set() if adv is None else adv.members
 living=sorted(world.current_people(),key=lambda x:x.id)
 school_rank=_martial_school_context(world,rng,living,members)
 latest={}
 for rec in reversed(world.agency.actions):
  if rec.year!=world.year:break
  latest.setdefault(rec.person,rec)
 for p in living:
  path=world.advancement.path(p.id)
  if path is None or not path.abilities:continue
  rec=latest.get(p.id);action='work' if rec is None else rec.action;strength=.35 if rec is None else rec.strength;relevant=ACTION_FUNCTIONS.get(action,set())
  indexed=list(enumerate(path.abilities));weakest=min((a.rank,a.level,a.progress) for _,a in indexed);asp=_aspiration(world,p);member=p.id in members
  career=_career_training(world,p,path,asp,member,strength,school_rank.get(p.id,0))
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
  rr=rng.stream('rank_ecology',world.year,p.id)
  # Full-time training is represented as a rotating weakest-quarter block:
  # five abilities receive four years' worth of exposure at once. Over a cycle
  # this is the same annual training budget, but avoids 20 hot-path calls for
  # every ranked professional every simulated year.
  if career is None:rr.shuffle(candidates)
  before=p.rank
  for i,a in candidates[:uses]:
   reflection=purposeful_reflection if purposeful_reflection is not None else ((.45+.55*p.curiosity) if action in ('learn','teach','socialize') else .10*p.curiosity)
   practice_ability(world,p,i,exposure*(.8+.4*rr.random()),reflection,context=action,body_rank=before)
  if len(path.abilities)==20 and (member or action in ('work','learn','teach','build','prepare')):
   mastery_training_step(world,p,path,rng.stream('mastery_training',world.year,p.id))
  record_body_transition(world,p,before,context=action)
