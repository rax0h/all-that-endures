from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref

RANK_NAMES=('mundane','iron','bronze','silver','gold','diamond','transcendent')

@dataclass
class MagicalThreat:
 id:int;kind:str;rank:int;location:int;created_year:int;ambient:float;status:str='active';origin_event:int|None=None

@dataclass
class ThreatEcologyState:
 threats:dict[int,MagicalThreat]=field(default_factory=dict);next_id:int=1
 def active(self,sid=None):
  return [t for t in self.threats.values() if t.status=='active' and (sid is None or t.location==sid)]

def supported_rank(ambient,hazard=0.):
 """Normal ecological ceiling. Exceptional rolls can still manifest one rank above it."""
 density=max(0.,ambient+.12*hazard)
 if density<.30:return 1
 if density<.55:return 2
 if density<.82:return 3
 if density<1.10:return 4
 return 5

def _rank_roll(rr,ceiling):
 # Rank is an ecological pyramid, not a uniform encounter table.
 weights=(0,.70,.20,.072,.024,.004)
 allowed=list(range(1,min(5,ceiling)+1))
 if ceiling<5 and rr.random()<.015:allowed.append(ceiling+1)
 total=sum(weights[r] for r in allowed);x=rr.random()*total
 for rank in allowed:
  x-=weights[rank]
  if x<=0:return rank
 return allowed[-1]

def effective_response_rank(world,p):
 """Preparation and a complete, coherent path can let an exceptional actor punch up one tier."""
 rank=world.advancement.rank(p.id) if world.advancement.essence_user(p.id) else 0
 path=world.advancement.path(p.id)
 complete=path is not None and len(path.abilities)>=20
 quality=.34*p.health+.26*p.curiosity+.20*(1-p.inhibition)+.20*min(1.,p.wealth/25.)
 return min(5,rank+(1 if complete and quality>=.72 else 0))

def threat_ecology_step(world,rng):
 Layer,Ref=layer_ref();state=world.threat_ecology
 for sid,s in sorted(world.settlements.items()):
  rr=rng.stream('ranked_threat_ecology',world.year,sid);field=world.ambient_magic.field(sid);cell=world.cells[(s.x,s.y)]
  ceiling=supported_rank(field.level,cell.hazard)
  # Manifestation pressure rises with ambient magic but Iron remains the common supernatural problem.
  chance=min(.20,.010+.030*field.level+.012*cell.hazard)
  if rr.random()<chance:
   rank=_rank_roll(rr,ceiling);kind='monster' if rr.random()<.72 else ('magic_item' if rr.random()<.58 else 'phenomenon')
   e=world.emit('ranked_magic_manifested',Layer.REALITY,location=Ref('settlement',sid),kind=kind,rank=rank,rank_name=RANK_NAMES[rank],ambient=round(field.level,3),ecological_ceiling=RANK_NAMES[ceiling])
   tid=state.next_id;state.next_id+=1;state.threats[tid]=MagicalThreat(tid,kind,rank,sid,world.year,field.level,origin_event=e.id)
  residents=[p for p in world.living_by_settlement()[sid] if p.age>=16]
  responders=sorted(residents,key=lambda p:(effective_response_rank(world,p),world.advancement.rank(p.id) if world.advancement.essence_user(p.id) else 0,p.health),reverse=True)
  for threat in sorted(state.active(sid),key=lambda t:(-t.rank,t.id))[:3]:
   if not responders:continue
   best=responders[0];effective=effective_response_rank(world,best);gap=threat.rank-effective
   if gap>1:continue
   base={-4:.99,-3:.98,-2:.96,-1:.91,0:.72,1:.22}.get(gap,.02)
   teamwork=min(.18,.025*sum(1 for p in responders[:8] if effective_response_rank(world,p)>=max(0,threat.rank-1)))
   if rr.random()<min(.98,base+teamwork):
    threat.status='resolved';e=world.emit('ranked_threat_resolved',Layer.SOCIETY,(Ref('person',best.id),),Ref('settlement',sid),((threat.origin_event,) if threat.origin_event else ()),threat=threat.id,kind=threat.kind,threat_rank=threat.rank,threat_rank_name=RANK_NAMES[threat.rank],responder_rank=world.advancement.rank(best.id) if world.advancement.essence_user(best.id) else 0,effective_rank=effective,punched_up=effective>=(threat.rank) and (world.advancement.rank(best.id) if world.advancement.essence_user(best.id) else 0)<threat.rank)
   elif gap>=0 and rr.random()<.08+.05*gap:
    world.emit('ranked_threat_escalated',Layer.REALITY,location=Ref('settlement',sid),causes=((threat.origin_event,) if threat.origin_event else ()),threat=threat.id,rank=threat.rank,rank_name=RANK_NAMES[threat.rank])
