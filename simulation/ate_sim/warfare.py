from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref
from .biology import combat_value,injury_resilience
from .mortality import kill

@dataclass
class Conflict:
 id:int; attacker:int; defender:int; started_year:int; cause:str; cause_event:int|None=None; status:str='war'; war_score:float=0.; battles:int=0; attacker_losses:int=0; defender_losses:int=0; ended_year:int|None=None; origin_event:int|None=None; peace_event:int|None=None
@dataclass
class WarfareState:
 conflicts:dict[int,Conflict]=field(default_factory=dict); tensions:dict[tuple[int,int],float]=field(default_factory=dict); next_conflict:int=1
 def active(self):return [c for c in self.conflicts.values() if c.status=='war']

def _pair(a,b):return (a,b) if a<b else (b,a)
def _residents(world,sid):return [p for p in world.people.values() if p.alive and p.age>=16 and p.settlement==sid]
def _strength(world,sid):
 people=_residents(world,sid);s=world.settlements[sid];members=world.institutions.institution_by_kind('adventure_society');member_ids=set() if members is None else members.members
 force=sum(combat_value(p)*(1.25 if p.id in member_ids else 1.) for p in people);return max(1.,force)*(0.55+0.45*s.defense)*(0.7+0.3*s.roads)

def _tension_step(world,rng):
 sids=sorted(world.settlements);Layer,Ref=layer_ref()
 for i,a in enumerate(sids):
  for b in sids[i+1:]:
   key=(a,b);sa,sb=world.settlements[a],world.settlements[b];qa,qb=world.local[a],world.local[b];route=world.trade_routes.get(key) or world.trade_routes.get((b,a));trade=0. if route is None else min(1.,route.strength+.002*route.exchanges)
   scarcity=max(qa.scarcity,qb.scarcity);prosperity_gap=abs(sa.prosperity-sb.prosperity);grievance=.35*(sa.memory.get('war',0)+sb.memory.get('war',0))+.15*(sa.memory.get('monster_surge',0)+sb.memory.get('monster_surge',0));target=.42*scarcity+.25*prosperity_gap+.18*grievance-.35*trade
   old=world.warfare.tensions.get(key,0.);world.warfare.tensions[key]=max(0.,min(1.,old*.965+max(0.,target)*.07))
   if any(c.status=='war' and {c.attacker,c.defender}=={a,b} for c in world.warfare.conflicts.values()):continue
   tension=world.warfare.tensions[key];rr=rng.stream('war_origin',world.year,a*100000+b)
   if tension<.58 or rr.random()>.025*tension:continue
   attacker=a if (qa.scarcity+.25*sa.prosperity)>(qb.scarcity+.25*sb.prosperity) else b;defender=b if attacker==a else a;cause='resource_pressure' if max(qa.scarcity,qb.scarcity)>.35 else ('trade_rivalry' if trade>.15 else 'political_rivalry')
   e=world.emit('war_declared',Layer.SOCIETY,location=Ref('settlement',attacker),attacker=attacker,defender=defender,cause=cause,tension=round(tension,3));cid=world.warfare.next_conflict;world.warfare.next_conflict+=1;world.warfare.conflicts[cid]=Conflict(cid,attacker,defender,world.year,cause,origin_event=e.id);sa.memory['war']=min(1.,sa.memory.get('war',0)+.2);sb.memory['war']=min(1.,sb.memory.get('war',0)+.2)

def _campaign(world,rng,c):
 Layer,Ref=layer_ref();a,d=c.attacker,c.defender;ar,dr=_residents(world,a),_residents(world,d)
 if not ar or not dr:c.status='ended';c.ended_year=world.year;return
 rr=rng.stream('war_campaign',world.year,c.id);astr,dstr=_strength(world,a),_strength(world,d);alog=.55+.45*world.settlements[a].roads;dlog=.65+.35*world.settlements[d].defense;attack=astr*alog*(.8+.4*rr.random());defense=dstr*dlog*(.8+.4*rr.random());ratio=attack/max(1.,defense);intensity=min(.22,.035+.045*abs(ratio-1)+.035*rr.random())
 battle=world.emit('battle',Layer.REALITY,location=Ref('settlement',d),causes=(() if c.origin_event is None else (c.origin_event,)),conflict=c.id,attacker=a,defender=d,attack_strength=round(attack,2),defense_strength=round(defense,2),intensity=round(intensity,3));c.battles+=1
 for side,people,pressure in ((a,ar,intensity/max(.65,ratio)),(d,dr,intensity*min(1.5,ratio))):
  for p in list(people):
   pr=rng.stream('battle_person',world.year,c.id*1000000+p.id)
   if pr.random()<pressure/max(.65,injury_resilience(p)):
    died=kill(world,p,'war',(battle.id,));c.attacker_losses+=bool(died and side==a);c.defender_losses+=bool(died and side==d)
 winner=1 if attack>defense else -1;c.war_score=max(-4.,min(4.,c.war_score+winner*(.3+.25*abs(ratio-1))));world.settlements[a].prosperity=max(0.,world.settlements[a].prosperity-intensity*.03);world.settlements[d].prosperity=max(0.,world.settlements[d].prosperity-intensity*.06)
 for p in ar+dr:
  if not p.alive:continue
  path=world.advancement.path(p.id)
  if path and path.abilities:
   for i,ab in enumerate(path.abilities):
    if ab.function in ('enhancement','control','movement','recovery','detection'):world.advancement.practice(p.id,i,.10+.15*intensity)
 if abs(c.war_score)>=2.2 or world.year-c.started_year>=12 or not _residents(world,a) or not _residents(world,d):
  c.status='ended';c.ended_year=world.year;e=world.emit('peace_settlement',Layer.SOCIETY,location=Ref('settlement',d),causes=(battle.id,),conflict=c.id,war_score=round(c.war_score,3),attacker_losses=c.attacker_losses,defender_losses=c.defender_losses);c.peace_event=e.id;world.warfare.tensions[_pair(a,d)]*=.35

def warfare_step(world,rng):
 _tension_step(world,rng)
 for c in sorted(world.warfare.active(),key=lambda x:x.id):_campaign(world,rng,c)
