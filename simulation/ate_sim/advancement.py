from __future__ import annotations
from dataclasses import dataclass,field
import hashlib
RANKS=('ordinary','iron','bronze','silver','gold','diamond')
MAX_BASE_ESSENCES=3;MAX_ESSENCES=4;SKILLS_PER_ESSENCE=5;MAX_SKILLS=20
@dataclass
class AbilityProgress:
 essence:str; stone:str; semantic_key:str; awakened_year:int; origin_event:int|None=None; rank:int=1; level:int=0; progress:float=0.
@dataclass
class EssencePath:
 base_essences:list[str]=field(default_factory=list);confluence:str|None=None;abilities:list[AbilityProgress]=field(default_factory=list);core_fraction:float=0.;revelation:float=0.;integrated:float=0.
 @property
 def essences(self):return tuple(self.base_essences)+(() if self.confluence is None else (self.confluence,))
 @property
 def capacity(self):return len(self.essences)*SKILLS_PER_ESSENCE
@dataclass
class AdvancementState:
 paths:dict[int,EssencePath]=field(default_factory=dict)
 def path(self,pid:int):return self.paths.get(pid)
 def essence_user(self,pid:int):return pid in self.paths
 def absorb_essence(self,pid:int,essence:str,year:int,semantic_context=()):
  p=self.paths.setdefault(pid,EssencePath())
  if essence in p.base_essences or len(p.base_essences)>=MAX_BASE_ESSENCES:return p
  p.base_essences.append(essence)
  if len(p.base_essences)==3 and p.confluence is None:p.confluence=self._confluence(p.base_essences,semantic_context)
  return p
 def _confluence(self,essences,context):
  # Deterministic semantic synthesis: combination is primary; lived/context variables break
  # otherwise equivalent combinations. Names are stable identifiers until the semantic
  # dictionary's richer confluence vocabulary is wired into this resolver.
  raw='|'.join(sorted(essences))+'|'+'|'.join(map(str,context));h=hashlib.blake2b(raw.encode(),digest_size=5).hexdigest();return 'confluence-'+h
 def awaken_skill(self,pid:int,stone:str,year:int,semantic_context=(),origin_event=None):
  p=self.paths.get(pid)
  if p is None or len(p.abilities)>=p.capacity:return None
  # Stone + actual essence configuration + person/life context determine the result.
  raw='|'.join(p.essences)+'|'+stone+'|'+'|'.join(map(str,semantic_context))+'|'+str(len(p.abilities));key=hashlib.blake2b(raw.encode(),digest_size=8).hexdigest()
  # Distribute awakenings across essences with remaining capacity; no unowned essence can
  # receive an ability and no essence can exceed five.
  counts={e:0 for e in p.essences}
  for a in p.abilities:counts[a.essence]+=1
  available=[e for e in p.essences if counts[e]<SKILLS_PER_ESSENCE];essence=available[int(key[:8],16)%len(available)]
  a=AbilityProgress(essence,stone,'ability-'+key,year,origin_event);p.abilities.append(a);return a
 def rank(self,pid:int)->int:
  p=self.paths.get(pid)
  if p is None or not p.abilities:return 0
  return min(a.rank for a in p.abilities)
 def practice(self,pid:int,ability:int,meaningful_use:float,reflection:float=0.,core:float=0.):
  p=self.paths.get(pid)
  if p is None or not p.abilities:return None
  a=p.abilities[ability%len(p.abilities)];r=a.rank;gain=max(0.,meaningful_use)*(1.,.55,.28,.12,.035,.0)[min(r,5)]
  if core>0:gain+=core*(.8,.65,.5,.3,.0,.0)[min(r,5)];p.core_fraction=min(1.,p.core_fraction+core*.01)
  if r==4:p.revelation=min(1.,p.revelation+max(0.,reflection)*.004*(1-.75*p.core_fraction));p.integrated=min(1.,p.integrated+max(0.,reflection)*.002)
  a.progress+=gain
  while a.progress>=1 and a.rank<5:
   a.progress-=1;a.level+=1
   if a.level>=10:
    if a.rank==4 and min(p.revelation,p.integrated)<.92:a.level=9;a.progress=.999;break
    a.rank+=1;a.level=0
  return a
