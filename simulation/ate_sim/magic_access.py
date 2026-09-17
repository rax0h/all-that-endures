"""Institutional distribution of already-existing magic.

ATE is a magical world, not a mundane world with an optional magic career.
Existing magical ecology creates material pressure; institutions turn the world's
existing stock into ordinary access.  Pressure changes urgency and action, never
conjures inventory or weakens canonical 20/20 progression.
"""
from __future__ import annotations
from math import ceil
from .core_types import layer_ref
from .currency import can_pay_tier

RARITY_PRICE={'Common':1.,'Uncommon':2.,'Rare':8.,'Epic':24.,'Legendary':80.,
 'common':1.,'uncommon':2.,'rare':8.,'epic':24.,'legendary':80.}
MAGIC_WORLD_ADOPTION_FLOOR=.75
MAGIC_WORLD_ADOPTION_EXPECTED=.80


def _price(r):return RARITY_PRICE.get(r.rarity,4.)*(1. if r.kind=='essence' else .55)

def _professional_interest(p):return p.occupation in {'adventurer','guard','hunter','soldier','farmer','labor','smith','crafter','artisan','cook','chef','healer','builder','architect','merchant','scholar'}


def _threat_pressure(world):
 """Settlement pressure from objective, unresolved magical manifestations.

 Rank and persistence matter.  A safe settlement can remain culturally relaxed;
 repeated unresolved manifestations make magical capability materially urgent.
 This is computed once per annual access step so it does not add a person x threat
 hot-path scan.
 """
 pressure={sid:0. for sid in world.settlements}
 state=getattr(world,'threat_ecology',None)
 if state is None:return pressure
 for threat in state.threats.values():
  if threat.status!='active' or threat.location not in pressure:continue
  age=max(0,world.year-threat.created_year)
  kind=.10 if threat.kind=='monster' else (.06 if threat.kind=='phenomenon' else .035)
  pressure[threat.location]+=kind+.045*max(1,threat.rank)+.012*min(10,age)
 return {sid:min(1.,value) for sid,value in pressure.items()}


def _broker_stock(world):
 """Return market stock plus a frozen map of legitimately offered private surplus."""
 from .magic_resources import _wants
 stock=[];private={}
 for r in world.magic_resources.resources.values():
  if r.consumed_year is not None:continue
  if r.owner_kind=='settlement':stock.append(r);continue
  if r.owner_kind!='person':continue
  owner=world.people.get(r.owner_id)
  if owner is not None and owner.alive and not _wants(world,owner,r):
   stock.append(r);private[r.id]=r.owner_id
 stock.sort(key=lambda r:(_price(r),r.id))
 return stock,private


def _candidates(world,p,kind,stock,private):
 path=world.advancement.path(p.id);owned=set(() if path is None else path.base_essences)
 local=[];remote=[]
 for r in stock:
  if r.consumed_year is not None or r.kind!=kind:continue
  if kind=='essence' and r.key in owned:continue
  if r.owner_kind=='person':
   if private.get(r.id)!=r.owner_id or r.owner_id==p.id:continue
  elif r.owner_kind!='settlement':continue
  (local if r.location==p.settlement else remote).append(r)
 return local+remote


def _can_afford(world,p,price):return p.wealth>=price or can_pay_tier(world,p.id,'iron',ceil(price))

def _pay(world,p,price,institution,seller=None):
 if p.wealth>=price:
  p.wealth-=price
  if seller is not None:seller.wealth+=price
  return {},'ordinary_wealth'
 if can_pay_tier(world,p.id,'iron',ceil(price)):
  coins=world.currency.transfer(p.id,seller.id,{'iron':ceil(price)}) if seller is not None else world.currency.treasury_transfer(institution.id,p.id,{'iron':ceil(price)},deposit=True)
  return coins,'ranked_coin'
 return None,None


def _sponsor(world,p,a,pressure=0.):
 adv=world.institutions.institution_by_kind('adventure_society')
 if adv is None:return None
 combat=a.adventurer_aspiration or p.occupation in ('adventurer','guard','hunter','soldier')
 # Under real magical danger the Society also equips ordinary residents whose
 # livelihood/settlement needs capability. This is civil defense, not a combat
 # class conversion, and only applies to affordable common/uncommon stock.
 civil_defense=pressure>=.45 and (a.completion_goal or _professional_interest(p))
 return adv if combat or civil_defense else None


def _acquire(world,p,r,a,pressure=0.):
 Layer,Ref=layer_ref();magic=world.institutions.institution_by_kind('magic_society')
 if magic is None:return False
 price=_price(r);seller=world.people.get(r.owner_id) if r.owner_kind=='person' else None
 if r.owner_kind=='person' and (seller is None or not seller.alive):return False
 sponsor=_sponsor(world,p,a,pressure);sponsored=seller is None and sponsor is not None and r.rarity.lower() in ('common','uncommon')
 if not sponsored and not _can_afford(world,p,price):return False
 domain='sponsorship'
 if not sponsored:
  coins,domain=_pay(world,p,price,magic,seller)
  if coins is None:return False
 remote=r.location!=p.settlement;actors=[Ref('person',p.id)]
 if seller is not None:actors.append(Ref('person',seller.id))
 e=world.emit('magic_resource_ordered' if remote else 'magic_resource_purchased',Layer.SOCIETY,tuple(actors),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key,rarity=r.rarity,price=0 if sponsored else price,price_domain=domain,institution=(sponsor.id if sponsored else magic.id),sponsored=sponsored,brokered_private_stock=seller is not None,source_settlement=r.location,ordered=remote,threat_pressure=round(pressure,3))
 world.magic_resources.transfer(r.id,'person',p.id,e.id,p.settlement);a.preparation=min(1.,a.preparation+.12);return True


def _use_owned_essence(world,p,a):
 from .magic_resources import absorb_essence_resource
 path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences)
 if base>=a.desired_base_essences:return path,base
 owned=world.magic_resources.inventory('person',p.id,'essence');c=[r for r in owned if path is None or r.key not in path.base_essences]
 if c:
  c.sort(key=lambda r:(_price(r),r.id));absorb_essence_resource(world,p.id,c[0].id);path=world.advancement.path(p.id);base=len(path.base_essences)
 return path,base


def institutional_magic_access_step(world,rng):
 from .magic_resources import _aspiration,use_awakening_stone,_commit_to_full_path
 if world.institutions.institution_by_kind('magic_society') is None:return
 adults=[p for p in world.current_people() if p.alive and p.age>=16]
 if not adults:return
 prevalence=sum(1 for p in adults if world.advancement.essence_user(p.id))/len(adults)
 pressure_by_settlement=_threat_pressure(world)
 stock,private=_broker_stock(world)
 for p in sorted(adults,key=lambda x:x.id):
  rr=rng.stream('institutional_magic_access',world.year,p.id);a=_aspiration(world,p);path=world.advancement.path(p.id);pressure=pressure_by_settlement.get(p.settlement,0.)
  # Objective danger changes behavior. It does not create desire from nothing:
  # professional/capability interest and existing aspiration are converted into
  # urgency, preparation and concrete acquisition when the world bears down.
  if pressure>0:
   a.urgency=max(a.urgency,min(1.,.28+.72*pressure))
   a.preparation=min(1.,a.preparation+.04*pressure)
   if a.desired_base_essences==0 and (_professional_interest(p) or pressure>=.65):
    a.desired_base_essences=1;a.desired_abilities=max(a.desired_abilities,5);a.reason='magical-world pressure';a.urgency=max(a.urgency,.45)
  if a.desired_base_essences==0 and _professional_interest(p):
   chance=.12+.18*p.curiosity+.10*(1-p.inhibition)+(.20 if prevalence<MAGIC_WORLD_ADOPTION_FLOOR else 0)+.30*pressure
   if rr.random()<min(.95,chance):a.desired_base_essences=1;a.desired_abilities=max(a.desired_abilities,5);a.reason='profession/capability';a.urgency=max(a.urgency,.32)
  # Committed people do not indefinitely procrastinate in a dangerous magical
  # world. Pressure makes them less selective about an available viable path.
  if a.completion_goal and pressure>=.25:
   a.desired_base_essences=3;a.desired_abilities=20
   a.compromise_tolerance=max(a.compromise_tolerance,.72+.25*pressure)
   a.stone_selectiveness=min(a.stone_selectiveness,.35-.20*min(1.,pressure))
  path,base=_use_owned_essence(world,p,a)
  while base<a.desired_base_essences:
   choices=_candidates(world,p,'essence',stock,private)
   if not choices or not _acquire(world,p,choices[0],a,pressure):break
   path,newbase=_use_owned_essence(world,p,a)
   if newbase<=base:break
   base=newbase
  if path is not None and a.adventurer_aspiration:_commit_to_full_path(a)
  if path is not None and len(path.abilities)<min(a.desired_abilities,path.capacity):
   stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
   if not stones:
    choices=_candidates(world,p,'awakening_stone',stock,private)
    if choices and _acquire(world,p,choices[0],a,pressure):stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
   if stones:
    stones.sort(key=lambda r:(_price(r),r.id));use_awakening_stone(world,p.id,stones[0].id)
