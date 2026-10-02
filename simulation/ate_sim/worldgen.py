from .core import *
from .culture import seed_practices
from .species import habitat_suitability
from .semantic_dictionary import ESSENCE_IDS,ESSENCES,STONE_IDS,AWAKENING_STONES
from .divinity import seed_gods
from .institutions import ensure_core_societies
from .magic_progression import practice_ability,record_body_transition
import math

PEOPLES=('human','elf','celestine','leonid','smoulder','draconian','merfolk','runic')
ESSENCES_AVAILABLE=ESSENCE_IDS
FOUNDING_ADULT_MAGIC_PREVALENCE=.78
FOUNDING_RANKED_SHARE_OF_MAGIC_USERS=.45


def _local_peoples(rr,cell):
 weighted=[]
 for key in PEOPLES:
  weighted.append((habitat_suitability(key,cell.elevation,cell.moisture,cell.forest)*rr.uniform(.72,1.28),key))
 weighted.sort(reverse=True);count=rr.randint(1,4);local=[key for _,key in weighted[:count]]
 if count>1 and rr.random()<.28:local[-1]=rr.choice([key for _,key in weighted[count:] or weighted])
 return tuple(dict.fromkeys(local))


def _context(p,sid):
 return (p.species,'founder',p.occupation,round(p.curiosity,2),round(p.temperament,2),round(p.attachment,2),round(p.inhibition,2),sid)


def _observe_preexisting_essence(w,rr,p,sid,founded,essence=None):
 essence=essence or rr.choice(ESSENCES_AVAILABLE)
 observed=w.emit('preexisting_magic_resource_observed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(founded.id,),
     resource_kind='essence',key=essence,rarity=ESSENCES[essence]['rarity'],
     observation_boundary=True,preexisting=True,prior_provenance='outside observed timeline')
 resource=w.magic_resources.create('essence',essence,ESSENCES[essence]['rarity'],0,sid,'person',p.id,observed.id)
 absorbed=w.emit('essence_absorbed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(observed.id,),
     resource=resource.id,essence=essence,observation_boundary=True,preexisting=True)
 w.magic_resources.consume(resource.id,p.id,0,absorbed.id)
 path,created=w.advancement.absorb_essence(p.id,essence,0,_context(p,sid),absorbed.id)
 if any(a.source=='confluence' for a in created):
  formation=w.emit('confluence_formed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(absorbed.id,),
      base_essences=tuple(path.base_essences),confluence=path.confluence,observation_boundary=True,preexisting=True)
  w.emit('confluence_absorbed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(formation.id,),
      confluence=path.confluence,mechanism='touch',automatic_acceptance=True,observation_boundary=True,preexisting=True)
 for ability in created:
  w.emit('ability_awakened',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(absorbed.id,),
      essence=ability.essence,source=ability.source,ability=ability.semantic_key,name=ability.name,
      special=ability.special,aura=ability.aura,observation_boundary=True,preexisting=True)
 p.rank=w.advancement.rank(p.id)
 return path


def _seed_ranked_founder(w,rr,p,sid,founded,target_rank):
 """Observe a legal preexisting complete path, then reconstruct visible rank state."""
 path=w.advancement.path(p.id)
 if path is None:path=_observe_preexisting_essence(w,rr,p,sid,founded)
 while len(path.base_essences)<3:
  choices=[e for e in ESSENCES_AVAILABLE if e not in path.base_essences]
  path=_observe_preexisting_essence(w,rr,p,sid,founded,rr.choice(choices))
 while len(path.abilities)<20:
  stone=rr.choice(STONE_IDS)
  observed=w.emit('preexisting_magic_resource_observed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(founded.id,),
      resource_kind='awakening_stone',key=stone,rarity=AWAKENING_STONES[stone]['rarity'],
      observation_boundary=True,preexisting=True,prior_provenance='outside observed timeline')
  resource=w.magic_resources.create('awakening_stone',stone,AWAKENING_STONES[stone]['rarity'],0,sid,'person',p.id,observed.id)
  before=p.rank
  used=w.emit('awakening_stone_used',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(observed.id,),
      resource=resource.id,stone=stone,target_essence=None,observation_boundary=True,preexisting=True)
  ability=w.advancement.awaken_skill(p.id,stone,0,_context(p,sid),used.id)
  if ability is None:raise RuntimeError('founding ranked path could not awaken ability')
  w.magic_resources.consume(resource.id,p.id,0,used.id)
  awakened=w.emit('ability_awakened',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(used.id,),
      essence=ability.essence,source=ability.source,ability=ability.semantic_key,name=ability.name,
      special=ability.special,aura=ability.aura,observation_boundary=True,preexisting=True)
  record_body_transition(w,p,before,context='pre-observation magical career',causes=(awakened.id,))

 # Iron is already reached when the twentieth ability appears.  Bronze/Silver
 # are reconstructed with the normal progression machinery; no bypass exists.
 for target in range(2,max(1,target_rank)+1):
  before=p.rank
  for i in range(len(path.abilities)):
   practice_ability(w,p,i,22. if target==2 else 48.,.5,context='pre-observation magical career')
  record_body_transition(w,p,before,context='pre-observation magical career')
 return path


def _seed_essence_for_person(w,rr,p,sid,founded):
 _observe_preexisting_essence(w,rr,p,sid,founded)
 if rr.random()<.12:
  stone=rr.choice(STONE_IDS)
  observed=w.emit('preexisting_magic_resource_observed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),(founded.id,),
      resource_kind='awakening_stone',key=stone,rarity=AWAKENING_STONES[stone]['rarity'],
      observation_boundary=True,preexisting=True,prior_provenance='outside observed timeline')
  w.magic_resources.create('awakening_stone',stone,AWAKENING_STONES[stone]['rarity'],0,sid,'person',p.id,observed.id)


def _observe_society_reserve(w,r,adv,founding_events):
 """Observe a modest physical reserve already held at the boundary."""
 if adv is None:return
 for bid in adv.branches:
  branch=w.institutions.branches[bid];sid=branch.settlement;cause=founding_events[sid]
  rr=r.stream('founding_society_reserve',0,bid)
  for n in range(8):
   key=rr.choice(ESSENCE_IDS)
   e=w.emit('society_resource_reserve_observed',Layer.SOCIETY,(Ref('institution',adv.id),),Ref('settlement',sid),(cause.id,),
       resource_kind='essence',key=key,rarity=ESSENCES[key]['rarity'],branch=bid,
       observation_boundary=True,preexisting=True)
   w.magic_resources.create('essence',key,ESSENCES[key]['rarity'],0,sid,'institution',adv.id,e.id)
  for n in range(40):
   key=rr.choice(STONE_IDS)
   e=w.emit('society_resource_reserve_observed',Layer.SOCIETY,(Ref('institution',adv.id),),Ref('settlement',sid),(cause.id,),
       resource_kind='awakening_stone',key=key,rarity=AWAKENING_STONES[key]['rarity'],branch=bid,
       observation_boundary=True,preexisting=True)
   w.magic_resources.create('awakening_stone',key,AWAKENING_STONES[key]['rarity'],0,sid,'institution',adv.id,e.id)


def generate_world(seed:int,width=24,height=18,settlements=5):
 w=World(seed);seed_gods(w);r=RNG(seed);founding_events={}
 for y in range(height):
  for x in range(width):
   g=r.stream('terrain',0,y*width+x);nx=(x-(width-1)/2)/(width/2);ny=(y-(height-1)/2)/(height/2)
   continental=max(0,1-(nx*nx+ny*ny));elev=max(0,min(1,.12+.72*continental+g.uniform(-.16,.16)))
   moisture=max(0,min(1,.55+.25*math.sin(x*.43)+g.uniform(-.2,.2)-.18*elev))
   fertility=max(0,min(1,.15+.55*moisture+.25*(1-abs(elev-.42))))
   forest=max(0,min(1,moisture*.9+g.uniform(-.2,.15)));hazard=max(0,min(1,.12+.25*forest+g.uniform(0,.18)))
   w.cells[(x,y)]=Cell(x,y,elev,moisture,fertility,forest,hazard)

 candidates=sorted(w.cells.values(),key=lambda c:c.fertility-.25*c.hazard,reverse=True);chosen=[]
 for c in candidates:
  if c.elevation>=.2 and all((c.x-o.x)**2+(c.y-o.y)**2>18 for o in chosen):chosen.append(c)
  if len(chosen)>=settlements:break

 for c in chosen:
  sid=w.next_settlement;w.next_settlement+=1
  s=Settlement(sid,c.x,c.y,food_stock=130+80*c.fertility,defense=.08+.12*c.hazard,irrigation=.08+.2*c.fertility,prosperity=.2+.3*c.fertility)
  w.settlements[sid]=s;w.local[sid]=LocalState()
  field=w.ambient_magic.field(sid);field.level=min(.58,.28+.16*c.hazard+.10*c.fertility+.05*s.prosperity);field.peak=field.level
  rr=r.stream('founders',0,sid);local=_local_peoples(rr,c)
  founded=w.emit('settlement_founded',Layer.REALITY,location=Ref('settlement',sid),fertility=c.fertility,
      species=tuple(sorted(local)),observation_boundary=True,magical_civilization_preexists=True)
  founding_events[sid]=founded;w.lineage.register('settlement',sid,origin_event=founded.id,origin_year=0)
  community=w.communities.create('founder_network',0,sid,founded.id);w.lineage.register('community',community.id,origin_event=founded.id,origin_year=0)
  irrigation=w.infrastructure.create('irrigation',(sid,),max(.15,s.irrigation),40+120*s.irrigation,0,founded.id);w.lineage.register('infrastructure',irrigation.id,(('settlement',sid),),founded.id,0)

  for _ in range(rr.randint(5,9)):
   hid=w.next_household;w.next_household+=1
   h=Household(hid,sid,wealth=rr.uniform(15,90),food=rr.uniform(8,20),preparedness=rr.uniform(.05,.3),lineage=f'Line-{sid}-{hid}')
   w.households[hid]=h;s.households.append(hid);w.lineage.register('household',hid,(('community',community.id),),founded.id,0)
   sp0=rr.choice(local);prop=w.economy.create('homestead',sid,'household',hid,h.wealth*.7,0,founded.id);w.lineage.register('property',prop.id,(('household',hid),),founded.id,0)
   for _ in range(rr.randint(2,6)):
    pid=w.next_person;w.next_person+=1;age=rr.randint(0,45);sp=sp0 if rr.random()<.88 else rr.choice(local)
    p=Person(pid,-age,sid,hid,age=age,wealth=h.wealth/max(1,len(h.members)+1),temperament=rr.random(),attachment=rr.random(),curiosity=rr.random(),inhibition=rr.random(),species=sp)
    w.people[pid]=p;w.metaphysics.soul(pid);h.members.append(pid);w.communities.join(pid,community.id,1.0);w.lineage.register('person',pid,(('household',hid),),founded.id,-age)
    if age>=18:
     w.skills.practice(pid,'agriculture',rr.uniform(.8,3.2),founded.id);w.skills.practice(pid,'construction',rr.uniform(.2,1.4),founded.id)
     w.skills.practice(pid,'defense',rr.uniform(.1,1.2),founded.id);w.skills.practice(pid,'craft',rr.uniform(.1,1.0),founded.id)
     if rr.random()<FOUNDING_ADULT_MAGIC_PREVALENCE:_seed_essence_for_person(w,rr,p,sid,founded)

  for hid in s.households:
   members=w.households[hid].members
   for a,b in zip(members,members[1:]):w.social.record(a,b,founded.id,trust=.15,attachment=.15)

 seed_practices(w,w.culture)
 for pid,practice in w.culture.practices.items():w.lineage.register('practice',pid,origin_year=practice.origin_year)

 ensure_core_societies(w)
 adv=w.institutions.institution_by_kind('adventure_society');mag=w.institutions.institution_by_kind('magic_society')
 ranked_founders=[]
 for sid in sorted(w.settlements):
  users=[p for p in w.current_people() if p.age>=18 and p.settlement==sid and w.advancement.essence_user(p.id)]
  if not users:continue
  ranked_count=max(1,min(len(users),int(round(len(users)*FOUNDING_RANKED_SHARE_OF_MAGIC_USERS))))
  def career_score(p):
   experience=max(0,p.age-18);skill=min(1.,(w.skills.get(p.id,'agriculture').level+w.skills.get(p.id,'construction').level+w.skills.get(p.id,'defense').level)/5.)
   return (.42*min(1.,experience/20.)+.28*p.curiosity+.18*(1-p.inhibition)+.12*skill,p.id)
  for p in sorted(users,key=career_score,reverse=True)[:ranked_count]:
   score,_=career_score(p);experience=max(0,p.age-18)
   target=3 if experience>=10 and score>=.68 else (2 if experience>=4 and score>=.50 else 1)
   _seed_ranked_founder(w,r.stream('founding_ranked_career',0,p.id),p,sid,founding_events[sid],target)
   ranked_founders.append(p)

 # Existing institutions have existing practitioners. Membership is observed,
 # not retroactively earned during the year-zero tick.
 for p in ranked_founders:
  professional=.48*p.curiosity+.32*(1-p.inhibition)+.20*min(1.,w.skills.get(p.id,'defense').level)
  if adv is not None and professional>=.52:
   adv.members.add(p.id);p.occupation='adventurer'
   w.emit('society_membership_observed',Layer.SOCIETY,(Ref('person',p.id),Ref('institution',adv.id)),Ref('settlement',p.settlement),
       institution=adv.id,society='adventure_society',observation_boundary=True,preexisting=True)
  elif mag is not None and p.curiosity>=.52:
   mag.members.add(p.id)
   w.emit('society_membership_observed',Layer.SOCIETY,(Ref('person',p.id),Ref('institution',mag.id)),Ref('settlement',p.settlement),
       institution=mag.id,society='magic_society',observation_boundary=True,preexisting=True)

 if adv is not None:
  opening=max(120,60*len(adv.branches));w.currency.treasuries.setdefault(adv.id,{})['iron']=opening
  anchor=min(w.settlements)
  w.emit('society_treasury_observed',Layer.SOCIETY,(Ref('institution',adv.id),),Ref('settlement',anchor),
      institution=adv.id,opening_balance={'iron':opening},preexisting=True,observation_boundary=True)
  _observe_society_reserve(w,r,adv,founding_events)

 return w
