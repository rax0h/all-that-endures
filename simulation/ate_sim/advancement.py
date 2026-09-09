from __future__ import annotations
from dataclasses import dataclass,field
import hashlib,re
from .semantic_dictionary import ESSENCES,AWAKENING_STONES,stone as stone_semantics
RANKS=('ordinary','iron','bronze','silver','gold','diamond');MAX_BASE_ESSENCES=3;SKILLS_PER_ESSENCE=5;MAX_SKILLS=20
@dataclass
class AbilityProgress:
 essence:str; source:str; semantic_key:str; name:str; function:str; domain:str; awakened_year:int; origin_event:int|None=None; special:bool=False; aura:bool=False; rank:int=1; level:int=0; progress:float=0.
@dataclass
class EssencePath:
 base_essences:list[str]=field(default_factory=list);confluence:str|None=None;confluence_name:str|None=None;confluence_concepts:tuple[str,...]=();abilities:list[AbilityProgress]=field(default_factory=list);core_fraction:float=0.;revelation:float=0.;integrated:float=0.
 @property
 def essences(self):return tuple(self.base_essences)+(() if self.confluence is None else (self.confluence,))
 @property
 def capacity(self):return len(self.essences)*SKILLS_PER_ESSENCE
 def abilities_for(self,e):return [a for a in self.abilities if a.essence==e]
@dataclass
class AdvancementState:
 paths:dict[int,EssencePath]=field(default_factory=dict)
 def path(self,pid):return self.paths.get(pid)
 def essence_user(self,pid):return pid in self.paths
 def _pick(self,v,k,o=0):return v[(int(k[o:o+8],16) if len(k)>=o+8 else int(k[:8],16))%len(v)] if v else 'manifestation'
 def _tokens(self,context):
  out=[]
  for value in context:out.extend(x for x in re.split(r'[^a-z0-9]+',str(value).lower()) if x)
  return tuple(dict.fromkeys(out))
 def _stone(self,key):
  data=stone_semantics(key)
  if data is None:raise ValueError(f'unknown awakening stone: {key}')
  return data
 def _semantic_ability(self,p,essence,source,year,context,origin_event=None):
  slot=len(p.abilities_for(essence))+1
  if slot>SKILLS_PER_ESSENCE:return None
  raw='|'.join(p.essences)+'|'+essence+'|'+source+'|'+str(year)+'|'+'|'.join(map(str,context))+'|'+str(slot);key=hashlib.blake2b(raw.encode(),digest_size=16).hexdigest();special=slot==5
  if essence in ESSENCES:
   sem=ESSENCES[essence];fn=self._pick(sem.get('suggested_functions',[]),key);domain=self._pick(sem.get('suggested_domains',[]),key,8)
   if source=='essence':name=sem['source_innate']
   else:
    stone_key=source.split(':',1)[1];sd=self._stone(stone_key);stone_core=[x.strip() for x in sd.get('core','manifestation').split(',') if x.strip()];stone_adj=[x.strip() for x in sd.get('adjacent','').split(',') if x.strip()];essence_words=sem.get('semantic_core',[])+sem.get('semantic_adjacent',[]);concept=self._pick(stone_core+stone_adj,key,16);aspect=self._pick(essence_words,key,24);name=f'{concept.title()} of {aspect.title()}' + (' Ascendant' if special else '')
  else:
   fn=self._pick(('transformation','enhancement','control','support','movement','recovery','detection','creation','influence','exchange'),key);domain=self._pick(p.confluence_concepts or self._tokens(context) or ('identity',),key,8);aspect=self._pick(p.confluence_concepts or ('synthesis',),key,16);name=f"{p.confluence_name or 'Confluence'}: {aspect.title()}" + (' Ascendant' if special else '')
  a=AbilityProgress(essence,source,'ability-'+key,name,fn,domain,year,origin_event,special);p.abilities.append(a);self._ensure_aura(p,context);return a
 def _ensure_aura(self,p,context):
  for a in p.abilities:a.aura=False
  if len(p.abilities)!=MAX_SKILLS:return
  raw='aura|'+'|'.join(p.essences)+'|'+'|'.join(map(str,context));key=hashlib.blake2b(raw.encode(),digest_size=8).hexdigest();preferred=[i for i,a in enumerate(p.abilities) if a.function in ('support','control','influence','detection','enhancement')]
  choices=preferred or list(range(len(p.abilities)));p.abilities[choices[int(key[:8],16)%len(choices)]].aura=True
 def absorb_essence(self,pid,essence,year,semantic_context=(),origin_event=None):
  essence=essence.lower()
  if essence not in ESSENCES:raise ValueError(f'unknown essence: {essence}')
  p=self.paths.setdefault(pid,EssencePath())
  if essence in p.base_essences or len(p.base_essences)>=MAX_BASE_ESSENCES:return p,[]
  p.base_essences.append(essence);created=[self._semantic_ability(p,essence,'essence',year,semantic_context,origin_event)]
  if len(p.base_essences)==MAX_BASE_ESSENCES and p.confluence is None:
   p.confluence,p.confluence_name,p.confluence_concepts=self._confluence(p.base_essences,semantic_context);created.append(self._semantic_ability(p,p.confluence,'confluence',year,semantic_context,origin_event))
  return p,[a for a in created if a]
 def _confluence(self,essences,context):
  sem=[ESSENCES[e] for e in essences];cores=[x for s in sem for x in s.get('semantic_core',[])];adj=[x for s in sem for x in s.get('semantic_adjacent',[])];functions=[x for s in sem for x in s.get('suggested_functions',[])];tokens=self._tokens(context);raw='|'.join(sorted(essences))+'|'+'|'.join(map(str,context));key=hashlib.blake2b(raw.encode(),digest_size=16).hexdigest();concepts=[]
  for i,s in enumerate(sem):concepts.append(self._pick(s.get('semantic_core',[]),key,(i*8)%24))
  if tokens:concepts.append(self._pick(tokens,key,8))
  concepts.append(self._pick(functions,key,16));concepts=tuple(dict.fromkeys(concepts))
  role=(self._pick(tokens,key,0).title() if tokens else 'Path');higher=self._pick(cores+adj,key,24).title();name=f'{higher} {role}';return 'confluence-'+key[:12],name,concepts
 def awaken_skill(self,pid,stone,year,semantic_context=(),origin_event=None,target_essence=None):
  p=self.paths.get(pid)
  if p is None:return None
  sd=self._stone(stone);stone_name=next(name for name,data in AWAKENING_STONES.items() if data is sd)
  available=[e for e in p.essences if len(p.abilities_for(e))<SKILLS_PER_ESSENCE]
  if target_essence is not None:
   if target_essence not in available:return None
   essence=target_essence
  else:
   raw='|'.join(p.essences)+'|'+stone_name+'|'+'|'.join(map(str,semantic_context))+'|'+str(len(p.abilities));key=hashlib.blake2b(raw.encode(),digest_size=8).hexdigest();essence=available[int(key[:8],16)%len(available)] if available else None
  return None if essence is None else self._semantic_ability(p,essence,'stone:'+stone_name,year,semantic_context,origin_event)
 def rank(self,pid):
  p=self.paths.get(pid);return 0 if p is None or not p.abilities else min(a.rank for a in p.abilities)
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
