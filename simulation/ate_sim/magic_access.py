"""Institutional access to magic in a mature magical civilization.

Magic exists independently of aspiration. This module models the ordinary
civilizational route from already-discovered resources to people: local Magic
Society stock, inter-settlement ordering, affordable purchase, brokerage of
surplus private stock, and Adventure Society sponsorship. It never creates
magical resources.
"""
from __future__ import annotations
from math import ceil
from .core_types import layer_ref
from .currency import can_pay_tier

RARITY_PRICE={
 'Common':3.,'Uncommon':6.,'Rare':18.,'Epic':45.,'Legendary':120.,
 'common':3.,'uncommon':6.,'rare':18.,'epic':45.,'legendary':120.,
}
MAGIC_WORLD_ADOPTION_FLOOR=.75
MAGIC_WORLD_ADOPTION_EXPECTED=.80


def _price(resource):
 return RARITY_PRICE.get(resource.rarity,8.)*(1.0 if resource.kind=='essence' else .55)


def _professional_interest(person):
 return person.occupation in {
  'adventurer','guard','hunter','soldier','farmer','labor','smith','crafter',
  'artisan','cook','chef','healer','builder','architect','merchant','scholar',
 }


def _broker_stock(world,adults):
 """Snapshot resources legitimately available to the Society brokerage network.

 Settlement stock is public market inventory. Person-held stock is offered only
 when its owner does not currently want it, so institutions move existing
 surplus rather than requisitioning private property.
 """
 from .magic_resources import _wants
 stock=[]
 for r in world.magic_resources.resources.values():
  if r.consumed_year is not None:continue
  if r.owner_kind=='settlement':stock.append(r);continue
  if r.owner_kind!='person':continue
  owner=world.people.get(r.owner_id)
  if owner is None or not owner.alive:continue
  if not _wants(world,owner,r):stock.append(r)
 return stock


def _candidate_resources(world,person,kind,stock):
 from .magic_resources import _wants
 path=world.advancement.path(person.id);owned=set(() if path is None else path.base_essences)
 local=[];remote=[]
 for r in stock:
  if r.consumed_year is not None or r.kind!=kind:continue
  if kind=='essence' and r.key in owned:continue
  if r.owner_kind=='person':
   if r.owner_id==person.id:continue
   owner=world.people.get(r.owner_id)
   if owner is None or not owner.alive or _wants(world,owner,r):continue
  elif r.owner_kind!='settlement':continue
  (local if r.location==person.settlement else remote).append(r)
 return sorted(local,key=lambda r:(_price(r),r.id))+sorted(remote,key=lambda r:(_price(r),r.id))


def _can_afford(world,person,price):
 return person.wealth>=price or can_pay_tier(world,person.id,'iron',ceil(price))


def _pay(world,person,price,institution,seller=None):
 if person.wealth>=price:
  person.wealth-=price
  if seller is not None:seller.wealth+=price
  return {},'ordinary_wealth'
 if can_pay_tier(world,person.id,'iron',ceil(price)):
  if seller is not None:
   coins=world.currency.transfer(person.id,seller.id,{'iron':ceil(price)})
  else:
   coins=world.currency.treasury_transfer(institution.id,person.id,{'iron':ceil(price)},deposit=True)
  return coins,'ranked_coin'
 return None,None


def _sponsored(world,person,aspiration):
 adventure=world.institutions.institution_by_kind('adventure_society')
 if adventure is None:return None
 if aspiration.adventurer_aspiration or person.occupation in ('adventurer','guard','hunter','soldier'):
  return adventure
 return None


def _acquire(world,person,resource,aspiration,rr):
 Layer,Ref=layer_ref();magic=world.institutions.institution_by_kind('magic_society')
 if magic is None:return False
 price=_price(resource);seller=None
 if resource.owner_kind=='person':
  seller=world.people.get(resource.owner_id)
  if seller is None or not seller.alive:return False
 sponsor=_sponsored(world,person,aspiration)
 # Sponsorship can issue Society stock. Privately owned resources remain paid
 # exchanges so brokerage never silently confiscates somebody else's property.
 sponsored=seller is None and sponsor is not None and resource.rarity.lower() in ('common','uncommon')
 if not sponsored and not _can_afford(world,person,price):return False
 coins={};domain='sponsorship'
 if not sponsored:
  coins,domain=_pay(world,person,price,magic,seller)
  if coins is None:return False
 remote=resource.location!=person.settlement
 actors=[Ref('person',person.id)]
 if seller is not None:actors.append(Ref('person',seller.id))
 e=world.emit('magic_resource_ordered' if remote else 'magic_resource_purchased',Layer.SOCIETY,
  tuple(actors),Ref('settlement',person.settlement),
  ((resource.origin_event,) if resource.origin_event else ()),resource=resource.id,
  resource_kind=resource.kind,key=resource.key,rarity=resource.rarity,price=0 if sponsored else price,
  price_domain=domain,institution=(sponsor.id if sponsored else magic.id),
  sponsored=sponsored,brokered_private_stock=seller is not None,
  source_settlement=resource.location,ordered=remote)
 world.magic_resources.transfer(resource.id,'person',person.id,e.id,person.settlement)
 aspiration.preparation=min(1.,aspiration.preparation+.12)
 return True


def _use_owned_essence(world,p,a):
 """Institutional counseling closes the old gap where a person could already
 own a wanted essence yet wait on the legacy annual-use RNG before absorbing it."""
 from .magic_resources import absorb_essence_resource
 path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences)
 if base>=a.desired_base_essences:return path,base
 owned=world.magic_resources.inventory('person',p.id,'essence')
 candidates=[r for r in owned if path is None or r.key not in path.base_essences]
 if candidates:
  candidates.sort(key=lambda r:(_price(r),r.id));absorb_essence_resource(world,p.id,candidates[0].id)
  path=world.advancement.path(p.id);base=len(path.base_essences)
 return path,base


def institutional_magic_access_step(world,rng):
 """Move existing magical resources through mature institutions to people."""
 from .magic_resources import _aspiration,use_awakening_stone,_commit_to_full_path
 magic=world.institutions.institution_by_kind('magic_society')
 if magic is None:return
 adults=[p for p in world.current_people() if p.alive and p.age>=16]
 if not adults:return
 essence_users=sum(1 for p in adults if world.advancement.essence_user(p.id));prevalence=essence_users/len(adults)
 # Build one annual brokerage snapshot instead of rescanning the full historical
 # resource table separately for every seeker.
 stock=_broker_stock(world,adults)
 for p in sorted(adults,key=lambda x:x.id):
  rr=rng.stream('institutional_magic_access',world.year,p.id);a=_aspiration(world,p);path=world.advancement.path(p.id)
  if a.desired_base_essences==0 and _professional_interest(p):
   chance=.12+.18*p.curiosity+.10*(1-p.inhibition)
   if prevalence<MAGIC_WORLD_ADOPTION_FLOOR:chance+=.20
   if rr.random()<chance:
    a.desired_base_essences=1;a.desired_abilities=max(a.desired_abilities,5);a.reason='profession/capability';a.urgency=max(a.urgency,.32)
  # First use resources the person already owns; then ask the Society network.
  path,base=_use_owned_essence(world,p,a)
  if base<a.desired_base_essences:
   choices=_candidate_resources(world,p,'essence',stock)
   if choices and _acquire(world,p,choices[0],a,rr):path,base=_use_owned_essence(world,p,a)
  if path is not None and a.adventurer_aspiration:_commit_to_full_path(a)
  # Re-evaluate after commitment because sponsorship may need to provision the
  # second and third base essences on subsequent annual steps.
  if path is not None and len(path.abilities)<min(a.desired_abilities,path.capacity):
   stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
   if stones:
    stones.sort(key=lambda r:(_price(r),r.id));use_awakening_stone(world,p.id,stones[0].id)
   else:
    choices=_candidate_resources(world,p,'awakening_stone',stock)
    if choices and _acquire(world,p,choices[0],a,rr):
     stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
     if stones:use_awakening_stone(world,p.id,stones[0].id)
