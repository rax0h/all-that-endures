"""Institutional access to magic in a mature magical civilization.

Magic exists independently of aspiration.  This module models the ordinary
civilizational route from already-discovered resources to people: local Magic
Society stock, inter-settlement ordering, affordable purchase, and Adventure
Society sponsorship.  It deliberately does not create resources.
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
 # Magic is useful infrastructure, not a combat class.  These broad occupations
 # deliberately include ordinary productive lives as well as adventuring work.
 return person.occupation in {
  'adventurer','guard','hunter','soldier','farmer','labor','smith','crafter',
  'artisan','cook','chef','healer','builder','architect','merchant','scholar',
 }


def _candidate_resources(world,person,kind):
 path=world.advancement.path(person.id)
 owned=set(() if path is None else path.base_essences)
 local=[];remote=[]
 for r in world.magic_resources.resources.values():
  if r.consumed_year is not None or r.kind!=kind:continue
  if kind=='essence' and r.key in owned:continue
  # Institutional ordering can draw from settlement stock anywhere in the
  # connected civilization. Person-held property is not silently requisitioned.
  if r.owner_kind!='settlement':continue
  (local if r.location==person.settlement else remote).append(r)
 return sorted(local,key=lambda r:(_price(r),r.id))+sorted(remote,key=lambda r:(_price(r),r.id))


def _can_afford(world,person,price):
 return person.wealth>=price or can_pay_tier(world,person.id,'iron',ceil(price))


def _pay(world,person,price,institution):
 if person.wealth>=price:
  person.wealth-=price;return {},'ordinary_wealth'
 if can_pay_tier(world,person.id,'iron',ceil(price)):
  coins=world.currency.treasury_transfer(institution.id,person.id,{'iron':ceil(price)},deposit=True)
  return coins,'ranked_coin'
 return None,None


def _sponsored(world,person,aspiration):
 adventure=world.institutions.institution_by_kind('adventure_society')
 if adventure is None:return None
 # Adventuring/combat-track people can be provisioned before they are ranked;
 # requiring Iron first would make sponsorship circular.
 if aspiration.adventurer_aspiration or person.occupation in ('adventurer','guard','hunter','soldier'):
  return adventure
 return None


def _acquire(world,person,resource,aspiration,rr):
 Layer,Ref=layer_ref();magic=world.institutions.institution_by_kind('magic_society')
 if magic is None:return False
 price=_price(resource);sponsor=_sponsored(world,person,aspiration)
 sponsored=sponsor is not None and resource.rarity.lower() in ('common','uncommon')
 if not sponsored and not _can_afford(world,person,price):return False
 coins={};domain='sponsorship'
 if not sponsored:
  coins,domain=_pay(world,person,price,magic)
  if coins is None:return False
 remote=resource.location!=person.settlement
 e=world.emit('magic_resource_ordered' if remote else 'magic_resource_purchased',Layer.SOCIETY,
  (Ref('person',person.id),),Ref('settlement',person.settlement),
  ((resource.origin_event,) if resource.origin_event else ()),resource=resource.id,
  resource_kind=resource.kind,key=resource.key,rarity=resource.rarity,price=0 if sponsored else price,
  price_domain=domain,institution=(sponsor.id if sponsored else magic.id),
  sponsored=sponsored,source_settlement=resource.location,ordered=remote)
 world.magic_resources.transfer(resource.id,'person',person.id,e.id,person.settlement)
 aspiration.preparation=min(1.,aspiration.preparation+.12)
 return True


def institutional_magic_access_step(world,rng):
 """Move existing magical resources through mature institutions to people.

 This is access/circulation, not abundance: no resource is spawned here.  The
 75-80% figure is a calibration expectation, never a quota or forced assignment.
 """
 from .magic_resources import _aspiration,absorb_essence_resource,use_awakening_stone,_commit_to_full_path
 magic=world.institutions.institution_by_kind('magic_society')
 if magic is None:return
 adults=[p for p in world.current_people() if p.alive and p.age>=16]
 if not adults:return
 essence_users=sum(1 for p in adults if world.advancement.essence_user(p.id))
 prevalence=essence_users/len(adults)
 for p in sorted(adults,key=lambda x:x.id):
  rr=rng.stream('institutional_magic_access',world.year,p.id);a=_aspiration(world,p);path=world.advancement.path(p.id)
  # In a magical civilization ordinary productive people have a positive reason
  # to enter magic even when they are not combatants.  The prevalence signal only
  # raises opportunity salience below the mature-world floor; it never grants an
  # essence or overrides affordability/resource conservation.
  if a.desired_base_essences==0 and _professional_interest(p):
   chance=.12+.18*p.curiosity+.10*(1-p.inhibition)
   if prevalence<MAGIC_WORLD_ADOPTION_FLOOR:chance+=.20
   if rr.random()<chance:
    a.desired_base_essences=1;a.desired_abilities=max(a.desired_abilities,5);a.reason='profession/capability';a.urgency=max(a.urgency,.32)
  path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences)
  # A person who wants an essence first tries the institutional market/order
  # network. Common/uncommon stock is preferred naturally by price.
  if base<a.desired_base_essences:
   choices=_candidate_resources(world,p,'essence')
   if choices and _acquire(world,p,choices[0],a,rr):
    owned=world.magic_resources.inventory('person',p.id,'essence')
    candidates=[r for r in owned if path is None or r.key not in path.base_essences]
    if candidates:
     absorb_essence_resource(world,p.id,candidates[0].id);path=world.advancement.path(p.id);base=len(path.base_essences)
  # Adventurers who enter the path are explicitly completion-oriented. Other
  # professions may choose to deepen their path through the existing aspiration
  # model rather than being forced into combat-style completion.
  if path is not None and a.adventurer_aspiration:_commit_to_full_path(a)
  # Institutional stone access uses the same conserved stock/order network.
  if path is not None and len(path.abilities)<min(a.desired_abilities,path.capacity):
   choices=_candidate_resources(world,p,'awakening_stone')
   if choices and _acquire(world,p,choices[0],a,rr):
    stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
    if stones:use_awakening_stone(world,p.id,stones[0].id)
