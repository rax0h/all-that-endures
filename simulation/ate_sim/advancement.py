from __future__ import annotations
from dataclasses import dataclass,field
import hashlib
RANKS=('ordinary','iron','bronze','silver','gold','diamond');MAX_BASE_ESSENCES=3;SKILLS_PER_ESSENCE=5;MAX_SKILLS=20
@dataclass
class AbilityProgress:
 essence:str; source:str; semantic_key:str; awakened_year:int; origin_event:int|None=None; rank:int=1; level:int=0; progress:float=0.
@dataclass
class EssencePath:
 base_essences:list[str]=field(default_factory=list);confluence:str|None=None;abilities:list[AbilityProgress]=field(default_factory=list);core_fraction:float=0.;revelation:float=0.;integrated:float=0.
 @property
 def essences(self):return tuple(self.base_essences)+(() if self.confluence is None else (self.confluence,))
 @property
 def capacity(self):return len(self.essences)*SKILLS_PER_ESSENCE
 def abilities_for(self,essence):return [a for a in self.abilities if a.essence==essence]
@dataclass
class AdvancementState:
 paths:dict[int,EssencePath]=field(default_factory=dict)
 def path(self,pid):return self.paths.get(pid)
 def essence_user(self,pid):return pid in self.paths
 def _semantic_ability(self,p,essence,source,year,context,origin_event=None):
  if len(p.abilities_for(essence))>=SKILLS_PER_ESSENCE:return None
  raw='|'.join(p.essences)+'|'+essence+'|'+source+'|'+str(year)+'|'+'|'.join(map(str,context))+'|'+str(len(p.abilities));key=hashlib.blake2b(raw.encode(),digest_size=8).hexdigest();a=AbilityProgress(essence,source,'ability-'+key,year,origin_event);p.abilities.append(a);return a
 def absorb_essence(self,pid,essence,year,semantic_context=(),origin_event=None):
  p=self.paths.setdefault(pid,EssencePath())
  if essence in p.base_essences or len(p.base_essences)>=MAX_BASE_ESSENCES:return p,[]
  p.base_essences.append(essence);created=[self._semantic_ability(p,essence,'essence',year,semantic_context,origin_event)]
  if len(p.base_essences)==3 and p.confluence is None:
   p.confluence=self._confluence(p.base_essences,semantic_context);created.append(self._semantic_ability(p,p.confluence,'confluence',year,semantic_context,origin_event))
  return p,[a for a in created if a]
 def _confluence(self,essences,context):
  # ATE confluence semantics: the three base essences combine with who the person is.
  # Context is expected to include class/alignment/profession plus relevant lived state.
  raw='|'.join(sorted(essences))+'|'+'|'.join(map(str,context));return 'confluence-'+hashlib.blake2b(raw.encode(),digest_size=5).hexdigest()
 def awaken_skill(self,pid,stone,year,semantic_context=(),origin_event=None):
  p=self.paths.get(pid)
  if p is None:return None
  available=[e for e in p.essences if len(p.abilities_for(e))<SKILLS_PER_ESSENCE]
  if not available:return None
  raw='|'.join(p.essences)+'|'+stone+'|'+'|'.join(map(str,semantic_context))+'|'+str(len(p.abilities));key=hashlib.blake2b(raw.encode(),digest_size=8).hexdigest();essence=available[int(key[:8],16)%len(available)];return self._semantic_ability(p,essence,'stone:'+stone,year,semantic_context,origin_event)
 def rank(self,pid):
  p=self.paths.get(pid)
  if p is None or not p.abilities:return 0
  return min(a.rank for a in p.abilities)
 def practice(self,pid,ability,meaningful_use,reflection=0.,core=0.):
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
