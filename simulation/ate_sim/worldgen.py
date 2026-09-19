from .core import *
from .culture import seed_practices
from .species import habitat_suitability
from .semantic_dictionary import ESSENCE_IDS,ESSENCES,STONE_IDS,AWAKENING_STONES
from .divinity import seed_gods
from .institutions import ensure_core_societies
import math
PEOPLES=('human','elf','celestine','leonid','smoulder','draconian','merfolk','runic');ESSENCES_AVAILABLE=ESSENCE_IDS
FOUNDING_ADULT_MAGIC_PREVALENCE=.78

def _local_peoples(rr,cell):
 weighted=[]
 for key in PEOPLES:weighted.append((habitat_suitability(key,cell.elevation,cell.moisture,cell.forest)*rr.uniform(.72,1.28),key))
 weighted.sort(reverse=True);count=rr.randint(1,4);local=[key for _,key in weighted[:count]]
 if count>1 and rr.random()<.28:local[-1]=rr.choice([key for _,key in weighted[count:] or weighted])
 return tuple(dict.fromkeys(local))

def _context(p,sid):return (p.species,'founder',p.occupation,round(p.curiosity,2),round(p.temperament,2),round(p.attachment,2),round(p.inhibition,2),sid)

def _observe_preexisting_essence(w,rr,p,sid,founded,essence=None):
 essence=essence or rr.choice([e for e in ESSENCES_AVAILABLE if w.advancement.path(p.id) is None or e not in w.advancement.path(p.id).base_essences])
 found=w.emit('essence_resource_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(founded.id,),essence=essence,provenance='pre-simulation magical civilization',preexisting=True,observation_boundary=True)
 resource=w.magic_resources.create('essence',essence,ESSENCES[essence]['rarity'],0,sid,'person',p.id,found.id)
 absorbed=w.emit('essence_absorbed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(found.id,),resource=resource.id,essence=essence,preexisting=True,observation_boundary=True)
 w.magic_resources.consume(resource.id,p.id,0,absorbed.id);path,created=w.advancement.absorb_essence(p.id,essence,0,_context(p,sid),absorbed.id)
 if any(a.source=='confluence' for a in created):
  formed=w.emit('confluence_formed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(absorbed.id,),base_essences=tuple(path.base_essences),confluence=path.confluence,preexisting=True,observation_boundary=True)
  w.emit('confluence_absorbed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(formed.id,),confluence=path.confluence,mechanism='touch',automatic_acceptance=True,preexisting=True,observation_boundary=True)
 for a in created:
  w.emit('ability_awakened',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(absorbed.id,),essence=a.essence,source=a.source,ability=a.semantic_key,name=a.name,special=a.special,aura=a.aura,preexisting=True,observation_boundary=True)
 p.rank=w.advancement.rank(p.id)
 return path

def _observe_preexisting_stone_use(w,rr,p,sid,founded,target_essence):
 skey=rr.choice(STONE_IDS)
 found=w.emit('awakening_stone_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(founded.id,),stone=skey,provenance='pre-simulation magical civilization',preexisting=True,observation_boundary=True)
 resource=w.magic_resources.create('awakening_stone',skey,AWAKENING_STONES[skey]['rarity'],0,sid,'person',p.id,found.id)
 used=w.emit('awakening_stone_used',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(found.id,),resource=resource.id,stone=skey,target_essence=target_essence,preexisting=True,observation_boundary=True)
 ability=w.advancement.awaken_skill(p.id,skey,0,_context(p,sid),used.id,target_essence)
 if ability is None:raise RuntimeError('preexisting path could not awaken ability')
 w.magic_resources.consume(resource.id,p.id,0,used.id)
 w.emit('ability_awakened',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(used.id,),essence=ability.essence,source=ability.source,ability=ability.semantic_key,name=ability.name,special=ability.special,aura=ability.aura,preexisting=True,observation_boundary=True)
 return ability

def _complete_preexisting_path(w,rr,p,sid,founded,target_rank):
 path=w.advancement.path(p.id)
 if path is None:path=_observe_preexisting_essence(w,rr,p,sid,founded)
 while len(path.base_essences)<3:
  choices=[e for e in ESSENCES_AVAILABLE if e not in path.base_essences]
  path=_observe_preexisting_essence(w,rr,p,sid,founded,rr.choice(choices))
 while len(path.abilities)<20:
  target=min(path.essences,key=lambda e:(len(path.abilities_for(e)),path.essences.index(e)))
  _observe_preexisting_stone_use(w,rr,p,sid,founded,target)
 if not w.advancement.completed_path(p.id):raise RuntimeError('preexisting completed path violates 20/20 invariant')
 target_rank=max(1,min(3,int(target_rank)))
 for ability in path.abilities:
  ability.rank=target_rank;ability.level=0;ability.progress=0.
 p.rank=target_rank
 observed=w.emit('preexisting_rank_observed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),
                 tuple(a.origin_event for a in path.abilities if a.origin_event is not None),
                 body_rank=target_rank,ability_ranks=tuple(a.rank for a in path.abilities),
                 abilities=tuple(a.semantic_key for a in path.abilities),essences=path.essences,
                 preexisting=True,observation_boundary=True,basis='pre-observation magical career')
 for ability in path.abilities:ability.milestone_event=observed.id
 return path

def _founder_career_score(w,p):
 experience=max(0,p.age-18)
 skill=min(1.,(w.skills.get(p.id,'agriculture').level+w.skills.get(p.id,'construction').level)/4.)
 return .42*min(1.,experience/22.)+.28*p.curiosity+.18*(1-p.inhibition)+.12*skill

def _seed_mature_magical_civilization(w,r,founding_events):
 # Complete some real inherited careers. This is a year-zero cross-section, not
 # a target-maintenance rule; all later participation and rank are live outcomes.
 for sid in sorted(w.settlements):
  users=[p for p in w.current_people() if p.age>=18 and p.settlement==sid and w.advancement.essence_user(p.id)]
  completed=[]
  for p in users:
   rr=r.stream('founding_magic_career',0,p.id);experience=max(0,p.age-18);score=_founder_career_score(w,p)
   chance=min(.74,.14+.014*experience+.24*p.curiosity+.10*(1-p.inhibition))
   if rr.random()>=chance:continue
   if experience>=12 and score>=.66 and rr.random()<.62:target=3
   elif experience>=4 and score>=.43:target=2
   else:target=1
   _complete_preexisting_path(w,rr,p,sid,founding_events[sid],target);completed.append(p)
  # A mature branch must begin with at least one qualified practitioner locally.
  # This is initial institutional continuity, never a later population floor.
  if users and not completed:
   p=max(users,key=lambda x:(_founder_career_score(w,x),x.age,-x.id))
   _complete_preexisting_path(w,r.stream('founding_magic_continuity',0,p.id),p,sid,founding_events[sid],1)

 ensure_core_societies(w,preexisting=True)
 adv=w.institutions.institution_by_kind('adventure_society');mag=w.institutions.institution_by_kind('magic_society')
 for sid in sorted(w.settlements):
  complete=[p for p in w.current_people() if p.age>=18 and p.settlement==sid and w.advancement.completed_path(p.id)]
  if not complete:continue
  magic_branch=w.institutions.branch_for('magic_society',sid);adv_branch=w.institutions.branch_for('adventure_society',sid)
  # Existing magical records are institutional knowledge at the observation boundary.
  for p in complete:
   if magic_branch is not None:
    e=w.emit('magic_user_registration_observed',Layer.KNOWLEDGE,(Ref('person',p.id),),Ref('settlement',sid),essences=tuple(w.advancement.path(p.id).essences),disclosure='full',preexisting=True,observation_boundary=True)
    record=w.institutions.register_magic_user(magic_branch.id,p.id,w.advancement.path(p.id),0,e.id,'full')
    w.transmission.record(0,'institutional_record','magic_registration',record.id,'person',p.id,'institution_branch',magic_branch.id,e.id,reliability=1.)
  magic_members=sorted((p for p in complete if p.curiosity>=.48),key=lambda p:(p.curiosity,p.rank,-p.id),reverse=True)
  if not magic_members:magic_members=[max(complete,key=lambda p:(p.curiosity,p.rank,-p.id))]
  adventure_members=sorted((p for p in complete if .55*(1-p.inhibition)+.30*p.curiosity+.15*min(1.,w.skills.get(p.id,'defense').level)>=.52),key=lambda p:(p.rank,1-p.inhibition,p.curiosity,-p.id),reverse=True)
  if not adventure_members:adventure_members=[max(complete,key=lambda p:(p.rank,1-p.inhibition,p.curiosity,-p.id))]
  for inst,branch,members in ((mag,magic_branch,magic_members),(adv,adv_branch,adventure_members)):
   if inst is None or branch is None:continue
   for p in members:
    if p.id in inst.members:continue
    inst.members.add(p.id)
    w.emit('society_membership_observed',Layer.SOCIETY,(Ref('person',p.id),Ref('institution',inst.id)),Ref('settlement',sid),
           institution=inst.id,institution_kind=inst.kind,branch=branch.id,preexisting=True,observation_boundary=True)

def _seed_essence_for_person(w,rr,p,sid,founded):
 _observe_preexisting_essence(w,rr,p,sid,founded)
 if rr.random()<.12:
  skey=rr.choice(STONE_IDS);sf=w.emit('awakening_stone_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(founded.id,),stone=skey,provenance='pre-simulation magical civilization',preexisting=True,observation_boundary=True);w.magic_resources.create('awakening_stone',skey,AWAKENING_STONES[skey]['rarity'],0,sid,'person',p.id,sf.id)

def generate_world(seed:int,width=24,height=18,settlements=5):
 w=World(seed);seed_gods(w);r=RNG(seed);founding_events={}
 for y in range(height):
  for x in range(width):
   g=r.stream('terrain',0,y*width+x);nx=(x-(width-1)/2)/(width/2);ny=(y-(height-1)/2)/(height/2);continental=max(0,1-(nx*nx+ny*ny));elev=max(0,min(1,.12+.72*continental+g.uniform(-.16,.16)));moisture=max(0,min(1,.55+.25*math.sin(x*.43)+g.uniform(-.2,.2)-.18*elev));fertility=max(0,min(1,.15+.55*moisture+.25*(1-abs(elev-.42))));forest=max(0,min(1,moisture*.9+g.uniform(-.2,.15)));hazard=max(0,min(1,.12+.25*forest+g.uniform(0,.18)));w.cells[(x,y)]=Cell(x,y,elev,moisture,fertility,forest,hazard)
 candidates=sorted(w.cells.values(),key=lambda c:c.fertility-.25*c.hazard,reverse=True);chosen=[]
 for c in candidates:
  if c.elevation>=.2 and all((c.x-o.x)**2+(c.y-o.y)**2>18 for o in chosen):chosen.append(c)
  if len(chosen)>=settlements:break
 for c in chosen:
  sid=w.next_settlement;w.next_settlement+=1;s=Settlement(sid,c.x,c.y,food_stock=130+80*c.fertility,defense=.08+.12*c.hazard,irrigation=.08+.2*c.fertility,prosperity=.2+.3*c.fertility);w.settlements[sid]=s;w.local[sid]=LocalState();field=w.ambient_magic.field(sid);field.level=min(.58,.28+.16*c.hazard+.10*c.fertility+.05*s.prosperity);field.peak=field.level;rr=r.stream('founders',0,sid);local=_local_peoples(rr,c);founded=w.emit('settlement_founded',Layer.REALITY,location=Ref('settlement',sid),fertility=c.fertility,species=tuple(sorted(local)),preexisting=True,observation_boundary=True,magical_civilization_preexists=True);founding_events[sid]=founded;w.lineage.register('settlement',sid,origin_event=founded.id,origin_year=0);community=w.communities.create('founder_network',0,sid,founded.id);w.lineage.register('community',community.id,origin_event=founded.id,origin_year=0);irrigation=w.infrastructure.create('irrigation',(sid,),max(.15,s.irrigation),40+120*s.irrigation,0,founded.id);w.lineage.register('infrastructure',irrigation.id,(('settlement',sid),),founded.id,0)
  for _ in range(rr.randint(5,9)):
   hid=w.next_household;w.next_household+=1;h=Household(hid,sid,wealth=rr.uniform(15,90),food=rr.uniform(8,20),preparedness=rr.uniform(.05,.3),lineage=f'Line-{sid}-{hid}');w.households[hid]=h;s.households.append(hid);w.lineage.register('household',hid,(('community',community.id),),founded.id,0);sp0=rr.choice(local);prop=w.economy.create('homestead',sid,'household',hid,h.wealth*.7,0,founded.id);w.lineage.register('property',prop.id,(('household',hid),),founded.id,0)
   for _ in range(rr.randint(2,6)):
    pid=w.next_person;w.next_person+=1;age=rr.randint(0,45);sp=sp0 if rr.random()<.88 else rr.choice(local);p=Person(pid,-age,sid,hid,age=age,wealth=h.wealth/max(1,len(h.members)+1),temperament=rr.random(),attachment=rr.random(),curiosity=rr.random(),inhibition=rr.random(),species=sp);w.people[pid]=p;w.metaphysics.soul(pid);h.members.append(pid);w.communities.join(pid,community.id,1.0);w.lineage.register('person',pid,(('household',hid),),founded.id,-age)
    if age>=18:
     w.skills.practice(pid,'agriculture',rr.uniform(.8,3.2),founded.id);w.skills.practice(pid,'construction',rr.uniform(.2,1.4),founded.id)
     if rr.random()<FOUNDING_ADULT_MAGIC_PREVALENCE:_seed_essence_for_person(w,rr,p,sid,founded)
  for h in s.households:
   hm=w.households[h].members
   for a,b in zip(hm,hm[1:]):w.social.record(a,b,founded.id,trust=.15,attachment=.15)
 seed_practices(w,w.culture)
 for pid,practice in w.culture.practices.items():w.lineage.register('practice',pid,origin_year=practice.origin_year)
 _seed_mature_magical_civilization(w,r,founding_events)
 return w
