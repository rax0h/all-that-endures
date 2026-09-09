from __future__ import annotations
from dataclasses import dataclass,field
RANKS=('ordinary','iron','bronze','silver','gold','diamond')
@dataclass
class AbilityProgress:
 rank:int=1; level:int=0; progress:float=0.
@dataclass
class EssencePath:
 abilities:list[AbilityProgress]=field(default_factory=lambda:[AbilityProgress() for _ in range(20)])
 core_fraction:float=0.; revelation:float=0.; integrated:float=0.
@dataclass
class AdvancementState:
 paths:dict[int,EssencePath]=field(default_factory=dict)
 def awaken(self,pid:int):return self.paths.setdefault(pid,EssencePath())
 def path(self,pid:int):return self.paths.get(pid)
 def rank(self,pid:int)->int:
  p=self.paths.get(pid)
  return 0 if p is None else min(a.rank for a in p.abilities)
 def practice(self,pid:int,ability:int,meaningful_use:float,reflection:float=0.,core:float=0.):
  p=self.awaken(pid);a=p.abilities[ability%20];r=a.rank
  # Natural advancement comes from meaningful use. Gold changes character: experience
  # still matters, but integration/revelation becomes the gate to Diamond.
  gain=max(0.,meaningful_use)*(1.,.55,.28,.12,.035,.0)[min(r,5)]
  if core>0:
   gain+=core*(.8,.65,.5,.3,.0,.0)[min(r,5)];p.core_fraction=min(1.,p.core_fraction+core*.01)
  if r==4:
   p.revelation=min(1.,p.revelation+max(0.,reflection)*.004*(1-.75*p.core_fraction))
   p.integrated=min(1.,p.integrated+max(0.,reflection)*.002)
  a.progress+=gain
  while a.progress>=1 and a.rank<5:
   a.progress-=1;a.level+=1
   if a.level>=10:
    if a.rank==4 and min(p.revelation,p.integrated)<.92:
     a.level=9;a.progress=.999;break
    a.rank+=1;a.level=0
  return a
