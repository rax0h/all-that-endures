from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref

@dataclass
class Institution:
 id:int;kind:str;name:str;founded_year:int;origin_event:int|None;branches:list[int]=field(default_factory=list);members:set[int]=field(default_factory=set)
@dataclass
class Branch:
 id:int;institution:int;settlement:int;founded_year:int;origin_event:int|None;authority:float=.5;records:set[int]=field(default_factory=set);notices:set[int]=field(default_factory=set)
@dataclass
class MagicUserRecord:
 id:int;person:int;branch:int;year:int;essence_ids:tuple[str,...];confluence_id:str|None;confluence_name:str|None;abilities:tuple[str,...];ability_names:tuple[str,...];disclosure:str;source_event:int|None
@dataclass
class AdventureNotice:
 id:int;branch:int;year:int;kind:str;location:int;cause_event:int;status:str='open';assigned_to:int|None=None;resolved_event:int|None=None;required_rank:int=1
@dataclass
class SocietyApplication:
 id:int;society:str;person:int;branch:int;applied_year:int;eligibility_verified:bool;stage:str='screening';days_completed:int=0;physical_score:float=0.;magical_score:float=0.;judgment_score:float=0.;passed:bool|None=None;origin_event:int|None=None;resolved_event:int|None=None
@dataclass
class InstitutionState:
 institutions:dict[int,Institution]=field(default_factory=dict);branches:dict[int,Branch]=field(default_factory=dict);magic_records:dict[int,MagicUserRecord]=field(default_factory=dict);notices:dict[int,AdventureNotice]=field(default_factory=dict);applications:dict[int,SocietyApplication]=field(default_factory=dict);next_institution:int=1;next_branch:int=1;next_record:int=1;next_notice:int=1;next_application:int=1
 def create_institution(self,kind,name,year,origin_event=None):
  iid=self.next_institution;self.next_institution+=1;i=Institution(iid,kind,name,year,origin_event);self.institutions[iid]=i
  if hasattr(self,'_kind_index'):self._kind_index[kind]=i;self._kind_index_count=len(self.institutions)
  return i
 def create_branch(self,institution,settlement,year,origin_event=None,authority=.5):
  old=next((b for b in self.branches.values() if b.institution==institution and b.settlement==settlement),None)
  if old:return old
  bid=self.next_branch;self.next_branch+=1;b=Branch(bid,institution,settlement,year,origin_event,authority);self.branches[bid]=b;self.institutions[institution].branches.append(bid);return b
 def institution_by_kind(self,kind):
  if not hasattr(self,'_kind_index') or getattr(self,'_kind_index_count',-1)!=len(self.institutions):
   self._kind_index={i.kind:i for i in self.institutions.values()};self._kind_index_count=len(self.institutions)
  return self._kind_index.get(kind)
 def branch_for(self,kind,settlement):
  i=self.institution_by_kind(kind)
  return None if i is None else next((self.branches[bid] for bid in i.branches if self.branches[bid].settlement==settlement),None)
 def register_magic_user(self,branch,person,path,year,source_event=None,disclosure='full'):
  if disclosure not in ('identity','essences','full'):raise ValueError('invalid disclosure level')
  ess=tuple(path.essences) if disclosure!='identity' else ();cid=path.confluence if disclosure!='identity' else None;cname=path.confluence_name if disclosure!='identity' else None;abilities=tuple(a.semantic_key for a in path.abilities) if disclosure=='full' else ();names=tuple(a.name for a in path.abilities) if disclosure=='full' else ();rid=self.next_record;self.next_record+=1;r=MagicUserRecord(rid,person,branch,year,ess,cid,cname,abilities,names,disclosure,source_event);self.magic_records[rid]=r;self.branches[branch].records.add(rid)
  if hasattr(self,'_recorded_people'):self._recorded_people.add(person)
  return r
 def recorded_people(self):
  if not hasattr(self,'_recorded_people') or getattr(self,'_record_count',-1)!=len(self.magic_records):
   self._recorded_people={r.person for r in self.magic_records.values()};self._record_count=len(self.magic_records)
  return self._recorded_people
 def records_for_person(self,pid):return sorted((r for r in self.magic_records.values() if r.person==pid),key=lambda r:(r.year,r.id))
 def _ensure_notice_indexes(self):
  if not hasattr(self,'_notice_by_cause') or getattr(self,'_notice_index_count',-1)!=len(self.notices):
   self._notice_by_cause={n.cause_event:n for n in self.notices.values()}
   self._active_notice_ids={n.id for n in self.notices.values() if n.status not in ('resolved','expired')}
   self._notice_index_count=len(self.notices)
 def post_notice(self,branch,year,kind,location,cause_event):
  self._ensure_notice_indexes();old=self._notice_by_cause.get(cause_event)
  if old:return old
  nid=self.next_notice;self.next_notice+=1;n=AdventureNotice(nid,branch,year,kind,location,cause_event);self.notices[nid]=n;self.branches[branch].notices.add(nid)
  self._notice_by_cause[cause_event]=n;self._active_notice_ids.add(nid);self._notice_index_count=len(self.notices)
  return n
 def active_notices(self,branch=None):
  self._ensure_notice_indexes()
  # Status mutates in career resolution code. Keep only the live operational
  # queue; the full notice dictionary remains the immutable historical archive.
  self._active_notice_ids={nid for nid in self._active_notice_ids if self.notices[nid].status not in ('resolved','expired')}
  ids=sorted(self._active_notice_ids)
  if branch is not None:ids=[nid for nid in ids if self.notices[nid].branch==branch]
  return [self.notices[nid] for nid in ids]
 def active_notice_count(self,branch=None):
  return len(self.active_notices(branch))
 def create_application(self,society,person,branch,year,eligible,origin_event=None):
  aid=self.next_application;self.next_application+=1;a=SocietyApplication(aid,society,person,branch,year,eligible,origin_event=origin_event);self.applications[aid]=a
  if hasattr(self,'_application_pairs'):self._application_pairs.add((person,society));self._application_count=len(self.applications)
  if hasattr(self,'_latest_applications'):self._latest_applications[(society,person)]=a;self._latest_application_count=len(self.applications)
  if hasattr(self,'_pending_application_ids'):self._pending_application_ids.add(aid);self._pending_application_count=len(self.applications)
  if hasattr(self,'_application_attempts'):
   key=(society,person);self._application_attempts[key]=self._application_attempts.get(key,0)+1;self._application_attempt_count=len(self.applications)
  return a
 def application_attempt_count(self,person,society):
  if not hasattr(self,'_application_attempts') or getattr(self,'_application_attempt_count',-1)!=len(self.applications):
   self._application_attempts={}
   for a in self.applications.values():
    key=(a.society,a.person);self._application_attempts[key]=self._application_attempts.get(key,0)+1
   self._application_attempt_count=len(self.applications)
  return self._application_attempts.get((society,person),0)
 def application_pairs(self):
  if not hasattr(self,'_application_pairs') or getattr(self,'_application_count',-1)!=len(self.applications):
   self._application_pairs={(a.person,a.society) for a in self.applications.values()};self._application_count=len(self.applications)
  return self._application_pairs
 def latest_applications(self,society):
  if not hasattr(self,'_latest_applications') or getattr(self,'_latest_application_count',-1)!=len(self.applications):
   self._latest_applications={}
   for a in self.applications.values():self._latest_applications[(a.society,a.person)]=a
   self._latest_application_count=len(self.applications)
  return {person:a for (kind,person),a in self._latest_applications.items() if kind==society}
 def pending_applications(self):
  # Pending applications are a tiny hot subset of the historical archive.
  # Rebuild only for old/directly-mutated state; normal creation/resolution
  # keeps this derived index current.
  if not hasattr(self,'_pending_application_ids') or getattr(self,'_pending_application_count',-1)!=len(self.applications):
   self._pending_application_ids={aid for aid,a in self.applications.items() if a.passed is None}
   self._pending_application_count=len(self.applications)
  else:
   self._pending_application_ids={aid for aid in self._pending_application_ids if self.applications[aid].passed is None}
  return [self.applications[aid] for aid in sorted(self._pending_application_ids)]

def full_essence_user(world,pid):
 p=world.advancement.path(pid);return p is not None and p.confluence is not None and len(p.essences)==4

def society_eligible(world,pid,society):
 if society not in ('adventure_society','magic_society'):raise ValueError('unknown society')
 p=world.people.get(pid);return bool(p and p.alive and full_essence_user(world,pid))

def ensure_core_societies(world):
 if not world.settlements:return
 populations={sid:0 for sid in world.settlements}
 for p in world.current_people():
  if p.alive:populations[p.settlement]+=1
 if sum(populations.values())<20:return
 Layer,Ref=layer_ref();anchor=min(world.settlements)
 for kind,name in (('adventure_society','Adventure Society'),('magic_society','Magic Society')):
  inst=world.institutions.institution_by_kind(kind)
  if inst is None:
   e=world.emit('institution_founded',Layer.SOCIETY,location=Ref('settlement',anchor),institution_kind=kind,name=name);inst=world.institutions.create_institution(kind,name,world.year,e.id);world.lineage.register('institution',inst.id,origin_event=e.id,origin_year=world.year)
  for sid in sorted(world.settlements):
   residents=populations[sid]
   if residents>=8 and world.institutions.branch_for(kind,sid) is None:
    causes=(inst.origin_event,) if inst.origin_event else ();e=world.emit('institution_branch_founded',Layer.SOCIETY,location=Ref('settlement',sid),causes=causes,institution=inst.id,institution_kind=kind);b=world.institutions.create_branch(inst.id,sid,world.year,e.id,min(.95,.35+residents/200));world.lineage.register('institution_branch',b.id,(('institution',inst.id),),e.id,world.year)

def register_magic_user(world,pid,disclosure='full'):
 p=world.people[pid];path=world.advancement.path(pid)
 if path is None:raise ValueError('person is not an essence user')
 b=world.institutions.branch_for('magic_society',p.settlement)
 if b is None:raise ValueError('no Magic Society branch in settlement')
 Layer,Ref=layer_ref();e=world.emit('magic_user_registered',Layer.KNOWLEDGE,(Ref('person',pid),),Ref('settlement',p.settlement),essences=tuple(path.essences) if disclosure!='identity' else (),confluence=path.confluence_name if disclosure!='identity' else None,disclosure=disclosure);r=world.institutions.register_magic_user(b.id,pid,path,world.year,e.id,disclosure);world.transmission.record(world.year,'institutional_record','magic_registration',r.id,'person',pid,'institution_branch',b.id,e.id,reliability=1.);return r

def apply_for_society(world,pid,society):
 p=world.people[pid];b=world.institutions.branch_for(society,p.settlement)
 if b is None:raise ValueError('no local Society branch')
 eligible=society_eligible(world,pid,society);Layer,Ref=layer_ref();e=world.emit('society_application',Layer.SOCIETY,(Ref('person',pid),),Ref('settlement',p.settlement),society=society,eligible=eligible);a=world.institutions.create_application(society,pid,b.id,world.year,eligible,e.id)
 if not eligible:a.stage='rejected_ineligible';a.passed=False;a.resolved_event=e.id
 return a

def _advance_application(world,a,rng):
 if a.passed is not None:return
 p=world.people.get(a.person)
 if p is None or not p.alive:
  a.stage='closed';a.passed=False
  if hasattr(world.institutions,'_pending_application_ids'):world.institutions._pending_application_ids.discard(a.id)
  return
 path=world.advancement.path(p.id);rr=rng.stream('society_assessment',world.year,a.id);a.days_completed+=1
 if a.days_completed==1:a.stage='physical';a.physical_score=min(1.,.25+.08*p.rank+.25*p.health+.2*rr.random());return
 if a.days_completed==2:a.stage='magical';a.magical_score=min(1.,.25+.025*len(path.abilities)+.08*world.advancement.rank(p.id)+.2*rr.random());return
 defense=world.skills.get(p.id,'defense').level;knowledge=world.skills.get(p.id,'knowledge').level;a.stage='field';a.judgment_score=min(1.,.30+.22*p.inhibition+.18*p.curiosity+.04*defense+.04*knowledge+.15*rr.random());threshold=.52 if a.society=='magic_society' else .60;a.passed=min(a.physical_score,a.magical_score,a.judgment_score)>=threshold;a.stage='passed' if a.passed else 'failed';Layer,Ref=layer_ref();causes=(a.origin_event,) if a.origin_event else ();e=world.emit('society_assessment_completed',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),causes,society=a.society,application=a.id,passed=a.passed,days=a.days_completed,physical=round(a.physical_score,3),magical=round(a.magical_score,3),judgment=round(a.judgment_score,3));a.resolved_event=e.id
 if hasattr(world.institutions,'_pending_application_ids'):world.institutions._pending_application_ids.discard(a.id)
 if a.passed:world.institutions.institution_by_kind(a.society).members.add(p.id)

def institution_step(world,rng):
 ensure_core_societies(world);Layer,Ref=layer_ref()
 # Magical civilization runs after institutions, so review the prior year as well. Notice
 # creation is idempotent by cause_event; a newly created notice is identifiable by its year.
 for e in [x for x in world.events_between(max(0,world.year-1),world.year) if x.kind in ('monster_surge','dangerous_magic','missing_person','ranked_magic_manifested','magical_expedition_returned_empty')]:
  if e.location is None or e.location.kind!='settlement':continue
  b=world.institutions.branch_for('adventure_society',e.location.id)
  if b is None:continue
  n=world.institutions.post_notice(b.id,world.year,e.kind,e.location.id,e.id)
  n.required_rank=max(1,min(5,int(e.data.get('rank',1+int(4*e.data.get('severity',0.))))))
  if n.year==world.year:world.emit('adventure_notice_posted',Layer.KNOWLEDGE,location=Ref('settlement',e.location.id),causes=(e.id,),notice=n.id,threat=e.kind)
 applied=world.institutions.application_pairs()
 for p in sorted(world.current_people(),key=lambda x:x.id):
  if not p.alive or not full_essence_user(world,p.id):continue
  for society in ('adventure_society','magic_society'):
   i=world.institutions.institution_by_kind(society)
   if i is None or p.id in i.members or (p.id,society) in applied:continue
   rr=rng.stream('society_apply',world.year,p.id+(1 if society=='adventure_society' else 1000000))
   if rr.random()<.035:apply_for_society(world,p.id,society)
 for a in world.institutions.pending_applications():
  _advance_application(world,a,rng)
