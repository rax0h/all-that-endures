from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref
from .currency import denomination_for_rank
from .magic_progression import record_application

RANK_NAMES=('mundane','iron','bronze','silver','gold','diamond','transcendent')
@dataclass
class MagicalThreat:
 id:int;kind:str;rank:int;location:int;created_year:int;ambient:float;status:str='active';origin_event:int|None=None;form:str='unshaped manifestation';environment_tags:tuple[str,...]=()
@dataclass
class ThreatEcologyState:
 threats:dict[int,MagicalThreat]=field(default_factory=dict);next_id:int=1;resolutions:dict[int,int]=field(default_factory=dict)
 def active(self,sid=None):return [t for t in self.threats.values() if t.status=='active' and (sid is None or t.location==sid)]
def supported_rank(ambient,hazard=0.):
 density=max(0.,ambient+.12*hazard)
 if density<.30:return 1
 if density<.55:return 2
 if density<.82:return 3
 if density<1.10:return 4
 return 5
def _rank_roll(rr,ceiling):
 weights=(0,.70,.20,.072,.024,.004);allowed=list(range(1,min(5,ceiling)+1))
 if ceiling<5 and rr.random()<.015:allowed.append(ceiling+1)
 total=sum(weights[r] for r in allowed);x=rr.random()*total
 for rank in allowed:
  x-=weights[rank]
  if x<=0:return rank
 return allowed[-1]
def environment_tags(world,sid):
 s=world.settlements[sid];c=world.cells[(s.x,s.y)];q=world.local[sid];tags=[]
 if c.forest>=.55:tags+=['forest','wood','plant','growth','beast','insect','fungus']
 elif c.forest>=.25:tags+=['scrub','plant','beast']
 if c.fertility>=.58:tags+=['fertile','growth','life','soil']
 if c.elevation>=.62:tags+=['mountain','stone','ore','crystal','wind']
 elif c.elevation<=.22:tags+=['lowland','plain']
 if c.moisture>=.62 or q.rain>=.68:tags+=['wet','water','rain','river']
 if q.flood>.04:tags+=['flood','mud','water']
 if c.moisture<=.28 or q.drought>.10:tags+=['dry','dust','sun','fire']
 if c.hazard>=.62:tags+=['hazard','predation','poison','death']
 if s.memory.get('monster_surge',0)>.12:tags+=['monster-scarred','fear','death']
 if s.prosperity>=.55:tags+=['settled','craft','trade','waste']
 return tuple(dict.fromkeys(tags))
def _monster_form(tags,rr):
 pools=[]
 if 'forest' in tags:pools+=['bark-hided prowler','root-burrowing mauler','spore-backed hunter','antlered thorn beast']
 if 'mountain' in tags:pools+=['shale-plated crawler','ore-jawed burrower','crystal-spined hunter']
 if 'wet' in tags or 'flood' in tags:pools+=['silt-bodied ambusher','reed-limbed lurker','mire-swollen predator']
 if 'dry' in tags:pools+=['dust-skinned stalker','glass-scaled scavenger','sun-baked burrower']
 if 'hazard' in tags:pools+=['venom-veined predator','carrion-fed horror']
 if 'settled' in tags:pools+=['refuse-fed vermin mass','smoke-stained scavenger','drain-nesting crawler']
 return (pools or ['feral ambient construct','terrain-shaped predator'])[int(rr.random()*len(pools or ['feral ambient construct','terrain-shaped predator']))%len(pools or ['feral ambient construct','terrain-shaped predator'])]
def _manifestation_form(kind,tags,rr):
 if kind=='monster':return _monster_form(tags,rr)
 if kind=='magic_item':
  material='wood' if 'wood' in tags else ('stone' if 'stone' in tags else ('crystal' if 'crystal' in tags else 'local matter'));return f'naturally condensed {material} focus'
 return f'{tags[0] if tags else "ambient"} magical phenomenon'
def effective_response_rank(world,p):
 rank=world.advancement.rank(p.id) if world.advancement.essence_user(p.id) else 0;path=world.advancement.path(p.id);complete=path is not None and len(path.abilities)>=20;quality=.34*p.health+.26*p.curiosity+.20*(1-p.inhibition)+.20*min(1.,p.wealth/25.);return min(5,rank+(1 if complete and quality>=.72 else 0))
def threat_ecology_step(world,rng):
 Layer,Ref=layer_ref();state=world.threat_ecology;living=world.living_by_settlement();dispatched={}
 for notice in world.institutions.notices.values():
  if notice.kind=='ranked_magic_manifested' and notice.status=='assigned' and notice.assigned_to is not None:
   person=world.people.get(notice.assigned_to)
   if person and person.alive and person.settlement!=notice.location and world.infrastructure.route_condition(person.settlement,notice.location)>0:dispatched[notice.cause_event]=person
 for sid,s in sorted(world.settlements.items()):
  rr=rng.stream('ranked_threat_ecology',world.year,sid);field=world.ambient_magic.field(sid);cell=world.cells[(s.x,s.y)];tags=environment_tags(world,sid);ceiling=supported_rank(field.level,cell.hazard);chance=min(.20,.010+.030*field.level+.012*cell.hazard)
  if rr.random()<chance:
   rank=_rank_roll(rr,ceiling);manifestation_kind='monster' if rr.random()<.72 else ('magic_item' if rr.random()<.58 else 'phenomenon');form=_manifestation_form(manifestation_kind,tags,rr);e=world.emit('ranked_magic_manifested',Layer.REALITY,location=Ref('settlement',sid),manifestation_kind=manifestation_kind,form=form,environment_tags=tags,manifestation_basis='ambient magic expressing local conditions',rank=rank,rank_name=RANK_NAMES[rank],ambient=round(field.level,3),ecological_ceiling=RANK_NAMES[ceiling]);tid=state.next_id;state.next_id+=1;state.threats[tid]=MagicalThreat(tid,manifestation_kind,rank,sid,world.year,field.level,origin_event=e.id,form=form,environment_tags=tags)
  residents=[p for p in living.get(sid,()) if p.age>=16];responders=sorted(residents,key=lambda p:(effective_response_rank(world,p),world.advancement.rank(p.id) if world.advancement.essence_user(p.id) else 0,p.health),reverse=True)
  for threat in sorted(state.active(sid),key=lambda t:(-t.rank,t.id))[:3]:
   visitor=dispatched.get(threat.origin_event);candidates=responders if visitor is None else sorted((*responders,visitor),key=lambda p:(effective_response_rank(world,p),p.rank,p.health),reverse=True)
   if not candidates:continue
   best=candidates[0];effective=effective_response_rank(world,best);gap=threat.rank-effective;actual=world.advancement.rank(best.id);difference=threat.rank-actual
   if gap>0 or difference>1:continue
   path=world.advancement.path(best.id);applicable=[a for a in path.abilities if a.function in ('attack','destruction','damage','control','movement','defense','enhancement','detection','support','sense','technique','precision','reaction','suppression','affliction','deception','concealment','redirection','timing','detection-denial','disruption','drain','pressure','multitasking','persistence','manipulation')] if path else [];used=sorted(applicable,key=lambda a:(len(a.understanding.applications),a.level,a.semantic_key))[:3];base={-4:.99,-3:.98,-2:.96,-1:.91,0:.72,1:.22}.get(gap,.02);teamwork=min(.18,.025*sum(1 for p in responders[:8] if effective_response_rank(world,p)>=max(0,threat.rank-1)));constraints=sum(bool(set(threat.environment_tags)&set(axis)) for axis in (('wet','flood'),('forest','scrub'),('hazard','poison'),('settled','waste')));complexity=min(5,max(threat.rank,1+constraints))
   if best.settlement!=sid:world.emit('ranked_response_journey',Layer.REALITY,(Ref('person',best.id),),Ref('settlement',sid),(threat.origin_event,),origin_settlement=best.settlement,destination=sid,threat=threat.id,mechanism='Society dispatch over an existing road; temporary journey')
   if rr.random()<min(.98,base+teamwork+.005*sum(a.level for a in used)-.025*constraints):
    threat.status='resolved';resolution=world.emit('ranked_threat_resolved',Layer.SOCIETY,(Ref('person',best.id),),Ref('settlement',sid),((threat.origin_event,) if threat.origin_event else ()),challenge_complexity=complexity,used_abilities=tuple(a.semantic_key for a in used),threat=threat.id,manifestation_kind=threat.kind,form=threat.form,threat_rank=threat.rank,threat_rank_name=RANK_NAMES[threat.rank],responder_rank=actual,effective_rank=effective,punched_up=effective>=threat.rank and actual<threat.rank)
    for ability in used:record_application(world,best,ability,resolution,constraint=f'{threat.kind}:{threat.form}:{sid}',difficulty=complexity,outcome=1.)
    if threat.origin_event is not None:state.resolutions[threat.origin_event]=resolution.id
    if threat.kind=='monster':
     harvested=world.emit('monster_remains_harvested',Layer.REALITY,(Ref('person',best.id),),Ref('settlement',sid),(resolution.id,),threat=threat.id,material_rank=threat.rank,valuation_denomination=denomination_for_rank(threat.rank),mechanism='physical_harvest',quantity=1.);world.materials.create_lot('monster_remains',1.,.5+.05*threat.rank,sid,best.id,world.year,harvested.id,(threat.form,),threat.rank)
     core=world.emit('monster_core_harvested',Layer.REALITY,(Ref('person',best.id),),Ref('settlement',sid),(resolution.id,),threat=threat.id,core_rank=threat.rank,core_rank_name=RANK_NAMES[threat.rank],mechanism='physical_monster_core',quantity=1.);world.materials.create_lot('monster_core',1.,1.,sid,best.id,world.year,core.id,(f'{RANK_NAMES[threat.rank]} core',),threat.rank)
   elif gap>=0 and rr.random()<.08+.05*gap:world.emit('ranked_threat_escalated',Layer.REALITY,location=Ref('settlement',sid),causes=((threat.origin_event,) if threat.origin_event else ()),threat=threat.id,form=threat.form,rank=threat.rank,rank_name=RANK_NAMES[threat.rank])