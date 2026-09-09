from __future__ import annotations
from dataclasses import dataclass,field

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
class InstitutionState:
 institutions:dict[int,Institution]=field(default_factory=dict)
 branches:dict[int,Branch]=field(default_factory=dict)
 magic_records:dict[int,MagicUserRecord]=field(default_factory=dict)
 notices:dict[int,AdventureNotice]=field(default_factory=dict)
 next_institution:int=1
 next_branch:int=1
 next_record:int=1
 next_notice:int=1

 def create_institution(self,kind,name,year,origin_event=None):
  iid=self.next_institution;self.next_institution+=1
  inst=Institution(iid,kind,name,year,origin_event);self.institutions[iid]=inst;return inst

 def create_branch(self,institution,settlement,year,origin_event=None,authority=.5):
  existing=[b for b in self.branches.values() if b.institution==institution and b.settlement==settlement]
  if existing:return existing[0]
  bid=self.next_branch;self.next_branch+=1
  b=Branch(bid,institution,settlement,year,origin_event,authority);self.branches[bid]=b;self.institutions[institution].branches.append(bid);return b

 def institution_by_kind(self,kind):
  return next((i for i in self.institutions.values() if i.kind==kind),None)

 def branch_for(self,kind,settlement):
  inst=self.institution_by_kind(kind)
  if inst is None:return None
  return next((self.branches[bid] for bid in inst.branches if self.branches[bid].settlement==settlement),None)

 def register_magic_user(self,branch,person,path,year,source_event=None,disclosure='full'):
  if disclosure not in ('identity','essences','full'):raise ValueError('invalid disclosure level')
  essence_ids=tuple(path.essences) if disclosure in ('essences','full') else ()
  confluence_id=path.confluence if disclosure in ('essences','full') else None
  confluence_name=path.confluence_name if disclosure in ('essences','full') else None
  abilities=tuple(a.semantic_key for a in path.abilities) if disclosure=='full' else ()
  names=tuple(a.name for a in path.abilities) if disclosure=='full' else ()
  rid=self.next_record;self.next_record+=1
  r=MagicUserRecord(rid,person,branch,year,essence_ids,confluence_id,confluence_name,abilities,names,disclosure,source_event)
  self.magic_records[rid]=r;self.branches[branch].records.add(rid);return r

 def records_for_person(self,pid):
  return sorted((r for r in self.magic_records.values() if r.person==pid),key=lambda r:(r.year,r.id))

 def post_notice(self,branch,year,kind,location,cause_event):
  for n in self.notices.values():
   if n.cause_event==cause_event:return n
  nid=self.next_notice;self.next_notice+=1
  n=AdventureNotice(nid,branch,year,kind,location,cause_event);self.notices[nid]=n;self.branches[branch].notices.add(nid);return n


def ensure_core_societies(world):
 if not world.settlements:return
 total=sum(1 for p in world.people.values() if p.alive)
 if total<20:return
 anchor=min(world.settlements)
 for kind,name in (('adventure_society','Adventure Society'),('magic_society','Magic Society')):
  inst=world.institutions.institution_by_kind(kind)
  if inst is None:
   e=world.emit('institution_founded',world.Layer.SOCIETY if hasattr(world,'Layer') else None,location=None) if False else None
   inst=world.institutions.create_institution(kind,name,world.year,None)
  for sid in sorted(world.settlements):
   residents=sum(1 for p in world.people.values() if p.alive and p.settlement==sid)
   if residents>=8 and world.institutions.branch_for(kind,sid) is None:
    world.institutions.create_branch(inst.id,sid,world.year,None,authority=min(.95,.35+residents/200))


def institution_step(world,rng):
 ensure_core_societies(world)
 # Adventure Society turns actual current-year threat events into persistent notices.
 for event in [e for e in world.events if e.year==world.year and e.kind in ('monster_surge','dangerous_magic','missing_person')]:
  if event.location is None or event.location.kind!='settlement':continue
  b=world.institutions.branch_for('adventure_society',event.location.id)
  if b is not None:world.institutions.post_notice(b.id,world.year,event.kind,event.location.id,event.id)
