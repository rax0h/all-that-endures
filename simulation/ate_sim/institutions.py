from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref

@dataclass
class Institution:
 id:int
 kind:str
 name:str
 founded_year:int
 origin_event:int|None
 branches:list[int]=field(default_factory=list)
 members:set[int]=field(default_factory=set)

@dataclass
class Branch:
 id:int
 institution:int
 settlement:int
 founded_year:int
 origin_event:int|None
 authority:float=.5
 records:set[int]=field(default_factory=set)
 notices:set[int]=field(default_factory=set)

@dataclass
class MagicUserRecord:
 id:int
 person:int
 branch:int
 year:int
 essence_ids:tuple[str,...]
 confluence_id:str|None
 confluence_name:str|None
 abilities:tuple[str,...]
 ability_names:tuple[str,...]
 disclosure:str
 source_event:int|None

@dataclass
class AdventureNotice:
 id:int
 branch:int
 year:int
 kind:str
 location:int
 cause_event:int
 status:str='open'
 assigned_to:int|None=None
 resolved_event:int|None=None

@dataclass
class SocietyApplication:
 id:int
 society:str
 person:int
 branch:int
 applied_year:int
 eligibility_verified:bool
 stage:str='screening'
 days_completed:int=0
 physical_score:float=0.
 magical_score:float=0.
 judgment_score:float=0.
 passed:bool|None=None
 origin_event:int|None=None
 resolved_event:int|None=None

@dataclass
class InstitutionState:
 institutions:dict[int,Institution]=field(default_factory=dict)
 branches:dict[int,Branch]=field(default_factory=dict)
 magic_records:dict[int,MagicUserRecord]=field(default_factory=dict)
 notices:dict[int,AdventureNotice]=field(default_factory=dict)
 applications:dict[int,SocietyApplication]=field(default_factory=dict)
 next_institution:int=1
 next_branch:int=1
 next_record:int=1
 next_notice:int=1
 next_application:int=1

 def create_institution(self,kind,name,year,origin_event=None):
  iid=self.next_institution;self.next_institution+=1;inst=Institution(iid,kind,name,year,origin_event);self.institutions[iid]=inst;return inst
 def create_branch(self,institution,settlement,year,origin_event=None,authority=.5):
  existing=[b for b in self.branches.values() if b.institution==institution and b.settlement==settlement]
  if existing:return existing[0]
  bid=self.next_branch;self.next_branch+=1;b=Branch(bid,institution,settlement,year,origin_event,authority);self.branches[bid]=b;self.institutions[institution].branches.append(bid);return b
 def institution_by_kind(self,kind):return next((i for i in self.institutions.values() if i.kind==kind),None)
 def branch_for(self,kind,settlement):
  inst=self.institution_by_kind(kind)
  if inst is None:return None
  return next((self.branches[bid] for bid in inst.branches if self.branches[bid].settlement==settlement),None)
 def register_magic_user(self,branch,person,path,year,source_event=None,disclosure='full'):
  if disclosure not in ('identity','essences','full'):raise ValueError('invalid disclosure level')
  essence_ids=tuple(path.essences) if disclosure in ('essences','full') else ();confluence_id=path.confluence if disclosure in ('essences','full') else None;confluence_name=path.confluence_name if disclosure in ('essences','full') else None;abilities=tuple(a.semantic_key for a in path.abilities) if disclosure=='full' else ();names=tuple(a.name for a in path.abilities) if disclosure=='full' else ()
  rid=self.next_record;self.next_record+=1;r=MagicUserRecord(rid,person,branch,year,essence_ids,confluence_id,confluence_name,abilities,names,disclosure,source_event);self.magic_records[rid]=r;self.branches[branch].records.add(rid);return r
 def records_for_person(self,pid):return sorted((r for r in self.magic_records.values() if r.person==pid),key=lambda r:(r.year,r.id))
 def post_notice(self,branch,year,kind,location,cause_event):
  for n in self.notices.values():
   if n.cause_event==cause_event:return n
  nid=self.next_notice;self.next_notice+=1;n=AdventureNotice(nid,branch,year,kind,location,cause_event);self.notices[nid]=n;self.branches[branch].notices.add(nid);return n
 def create_application(self,society,person,branch,year,eligible,origin_event=None):
  aid=self.next_application;self.next_application+=1;a=SocietyApplication(aid,society,person,branch,year,eligible,origin_event=origin_event);self.applications[aid]=a;return a

def full_essence_user(world,pid):
 path=world.advancement.path(pid);return path is not None and len(path.essences)==4 and path.confluence is not None

def society_eligible(world,pid,society):
 if society not in ('adventure_society','magic_society'):raise ValueError('unknown society')
 p=world.people.get(pid);return bool(p and p.alive and full_essence_user(world,pid))

def ensure_core_societies(world):
 if not world.settlements:return
 total=sum(1 for p in world.people.values() if p.alive)
 if total<20:return
 Layer,Ref=layer_ref();anchor=min(world.settlements)
 for kind,name in (('adventure_society','Adventure Society'),('magic_society','Magic Society')):
  inst=world.institutions.institution_by_kind(kind)
  if inst is None:
   e=world.emit('institution_founded',Layer.SOCIETY,location=Ref('settlement',anchor),institution_kind=kind,name=name);inst=world.institutions.create_institution(kind,name,world.year,e.id);world.lineage.register('institution',inst.id,origin_event=e.id,origin_year=world.year)
  for sid in sorted(world.settlements):
   residents=sum(1 for p in world.people.values() if p.alive and p.settlement==sid)
   if residents>=8 and world.institutions.branch_for(kind,sid) is None:
    be=world.emit('institution_branch_founded',Layer.SOCIETY,location=Ref('settlement',sid),causes=((inst.origin_event,) if inst.origin_event else ()),institution=inst.id,institution_kind=kind);b=world.institutions.create_branch(inst.id,sid,world.year,be.id,authority=min(.95,.35+residents/200));world.lineage.register('institution_branch',b.id,(('institution',inst.id),),be.id,world.year)

def register_magic_user(world,pid,disclosure='full'):
 p=world.people[pid];path=world.advancement.path(pid)
 if path is None:raise ValueError('person is not an essence user')
 branch=world.institutions.branch_for('magic_society',p.settlement)
 if branch is None:raise ValueError('no Magic Society branch in settlement')
 Layer,Ref=layer_ref();e=world.emit('magic_user_registered',Layer.KNOWLEDGE,(Ref('person',pid),),Ref('settlement',p.settlement),essences=tuple(path.essences) if disclosure!='identity' else (),confluence=path.confluence_name if disclosure!='identity' else None,disclosure=disclosure);rec=world.institutions.register_magic_user(branch.id,pid,path,world.year,e.id,disclosure);world.transmission.record(world.year,'institutional_record','magic_registration',rec.id,'person',pid,'institution_branch',branch.id,e.id,reliability=1.);return rec

def apply_for_society(world,pid,society):
 p=world.people[pid];branch=world.institutions.branch_for(society,p.settlement)
 if branch is None:raise ValueError('no local Society branch')
 eligible=society_eligible(world,pid,society);Layer,Ref=layer_ref();e=world.emit('society_application',Layer.SOCIETY,(Ref('person',pid),),Ref('settlement',p.settlement),society=society,eligible=eligible);a=world.institutions.create_application(society,pid,branch.id,world.year,eligible,e.id)
 if not eligible:
  a.stage='rejected_ineligible';a.passed=False;a.resolved_event=e.id
 return a

def _advance_application(world,a,rng):
 if a.passed is not None:return
 p=world.people.get(a.person)
 if p is None or not p.alive:a.stage='closed';a.passed=False;return
 path=world.advancement.path(a.person);rr=rng.stream('society_assessment',world.year,a.id);a.days_completed+=1
 # Multi-day assessment: screening/physical, magical control, then field judgment.
 if a.days_completed==1:
  a.stage='physical';a.physical_score=min(1.,.25+.08*p.rank+.25*p.health+.2*rr.random())
 elif a.days_completed==2:
  a.stage='magical';a.magical_score=min(1.,.25+.025*len(path.abilities)+.08*world.advancement.rank(p.id)+.2*rr.random())
 else:
  a.stage='field';agency=world.agency.people.get(p.id);judgment=(.35+.25*p.inhibition+.2*p.curiosity+.15*(agency.expertise if agency else 0.)+.15*rr.random());a.judgment_score=min(1.,judgment);threshold=.52 if a.society=='magic_society' else .60;a.passed=min(a.physical_score,a.magical_score,a.judgment_score)>=threshold;a.stage='passed' if a.passed else 'failed';Layer,Ref=layer_ref();e=world.emit('society_assessment_completed',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),(a.origin_event,),society=a.society,application=a.id,passed=a.passed,days=a.days_completed,physical=round(a.physical_score,3),magical=round(a.magical_score,3),judgment=round(a.judgment_score,3));a.resolved_event=e.id
  if a.passed:world.institutions.institution_by_kind(a.society).members.add(p.id)

def institution_step(world,rng):
 ensure_core_societies(world);Layer,Ref=layer_ref()
 for event in [e for e in world.events if e.year==world.year and e.kind in ('monster_surge','dangerous_magic','missing_person')]:
  if event.location is None or event.location.kind!='settlement':continue
  b=world.institutions.branch_for('adventure_society',event.location.id)
  if b is None:continue
  n=world.institutions.post_notice(b.id,world.year,event.kind,event.location.id,event.id)
  if not any(e.kind=='adventure_notice_posted' and e.data.get('notice')==n.id for e in world.events):world.emit('adventure_notice_posted',Layer.KNOWLEDGE,location=Ref('settlement',event.location.id),causes=(event.id,),notice=n.id,threat=event.kind)
 # Qualified full essence users may seek prestigious Society membership; partial users never enter this pipeline.
 applied={(a.person,a.society) for a in world.institutions.applications.values()}
 for p in sorted(world.people.values(),key=lambda p:p.id):
  if not p.alive or not full_essence_user(world,p.id):continue
  for society in ('adventure_society','magic_society'):
   inst=world.institutions.institution_by_kind(society)
   if inst is None or p.id in inst.members or (p.id,society) in applied:continue
   rr=rng.stream('society_apply',world.year,p.id+(1 if society=='adventure_society' else 1000000))
   if rr.random()<.035:apply_for_society(world,p.id,society)
 for a in sorted(world.institutions.applications.values(),key=lambda x:x.id):
  if a.passed is None:_advance_application(world,a,rng)
