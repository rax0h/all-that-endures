"""Persistent magical-goods circulation for mature settlements.

This module moves existing resources only. Local dealers buy unwanted goods into
settlement inventory, people browse that literal persistent stock and purchase
what they can use, and bounded travelling merchants redistribute unsold stock
along established trade routes. A failed sale never consumes the opportunity.
"""
from heapq import heapify, heappop
from math import ceil
from .core_types import layer_ref
from .currency import can_pay_tier
from .magic_resources import _wants, _aspiration, _demand_key


def _adults_by_settlement(world):
 out={sid:[] for sid in world.settlements}
 for p in world.current_people():
  if p.alive and p.age>=16:out[p.settlement].append(p)
 for people in out.values():people.sort(key=lambda p:p.id)
 return out


def _dealer_intake(world,adults):
 """Put person-held surplus into persistent local shop stock.

Ordinary wealth is the existing non-ranked civilian economy, not conserved
ranked coin. Dealers pay a modest wholesale price; retail spread represents
storage, brokerage and transport. At most one item/person/year enters stock,
so this is bounded by living adults rather than resources x people.
 """
 Layer,Ref=layer_ref()
 for sid,people in sorted(adults.items()):
  for p in people:
   held=world.magic_resources.inventory('person',p.id)
   if not held:continue
   surplus=[r for r in held if not _wants(world,p,r)]
   if not surplus:continue
   r=min(surplus,key=lambda x:x.id)
   wholesale=4.0 if r.kind=='essence' else 1.5
   if 'Rare' in r.rarity or 'Epic' in r.rarity:wholesale*=1.35
   if 'Legendary' in r.rarity:wholesale*=1.8
   p.wealth+=wholesale
   e=world.emit('magic_resource_listed',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',sid),
                ((r.origin_event,) if r.origin_event else ()),resource=r.id,
                resource_kind=r.kind,key=r.key,rarity=r.rarity,
                channel='local essence dealer',wholesale_price=round(wholesale,2),
                price_domain='ordinary_wealth')
   world.magic_resources.transfer(r.id,'settlement',sid,e.id,sid)


def _retail_price(resource):
 return 7 if resource.kind=='essence' else 3


def _retail_browse(world,adults):
 """Let people shop persistent local inventory instead of being market-matched.

A settlement's inventory is literal shelf stock. An adult with unmet magical
needs can inspect the goods actually present and buy one affordable, usable item
per year. Priority, aspiration score and preparation never reserve stock or
decide who is allowed to shop. Those states determine what the person wants;
money and actual shelf availability determine whether a purchase occurs.

Shelf lookup is indexed by kind/key so runtime depends on shoppers and distinct
goods, not centuries of accumulated copies. Since all retail essences share one
price and all stones share one price, browsing preserves the same choice rule:
cheapest usable kind first, then oldest resource id.
 """
 Layer,Ref=layer_ref()
 institution=world.institutions.institution_by_kind('adventure_society')
 for sid,people in sorted(adults.items()):
  stock=world.magic_resources.inventory('settlement',sid)
  if not stock:continue
  essence_by_key={};stone_heap=[]
  for r in stock:
   if r.kind=='essence':essence_by_key.setdefault(r.key,[]).append(r.id)
   else:stone_heap.append(r.id)
  for heap in essence_by_key.values():heapify(heap)
  heapify(stone_heap)
  # One current shelf-front id per distinct essence identity. A buyer scans only
  # these distinct fronts, never accumulated copies. This also avoids mutating a
  # shared heap merely to skip identities the current buyer already absorbed.
  essence_front={key:heap[0] for key,heap in essence_by_key.items() if heap}
  for p in people:
   held=world.magic_resources.inventory('person',p.id)
   if any(_wants(world,p,r) for r in held):continue
   a=_aspiration(world,p);path=world.advancement.path(p.id)
   base=0 if path is None else len(path.base_essences)
   abilities=0 if path is None else len(path.abilities)
   wants_essence=base<a.desired_base_essences
   wants_stone=path is not None and abilities<a.desired_abilities and abilities<path.capacity
   choice=None
   # Stones are cheaper than essences, matching the prior min(price,id) rule.
   if wants_stone and stone_heap and (p.wealth>=3 or can_pay_tier(world,p.id,'iron',3)):
    rid=stone_heap[0];choice=(3,rid,'stone',None)
   if choice is None and wants_essence and essence_front and (p.wealth>=7 or can_pay_tier(world,p.id,'iron',7)):
    owned=set() if path is None else set(path.base_essences)
    candidates=((rid,key) for key,rid in essence_front.items() if key not in owned)
    candidate=min(candidates,default=None)
    if candidate is not None:
     rid,key=candidate;choice=(7,rid,'essence',key)
   if choice is None:continue
   price,rid,kind,key=choice;r=world.magic_resources.resources[rid];coins={}
   if p.wealth>=price:p.wealth-=price
   elif institution is not None and can_pay_tier(world,p.id,'iron',ceil(price)):
    coins=world.currency.treasury_transfer(institution.id,p.id,{'iron':ceil(price)},deposit=True)
   else:continue
   e=world.emit('magic_resource_purchased',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',sid),
                ((r.origin_event,) if r.origin_event else ()),resource=r.id,key=r.key,
                price=price,coin_deposit=coins,
                institution=None if institution is None else institution.id,
                price_domain='ranked_coin' if coins else 'ordinary_wealth',
                channel='local essence dealer',mechanism='browsed shelf stock')
   world.magic_resources.transfer(r.id,'person',p.id,e.id,sid)
   if kind=='stone':heappop(stone_heap)
   else:
    heap=essence_by_key[key];removed=heappop(heap);assert removed==rid
    if heap:essence_front[key]=heap[0]
    else:essence_front.pop(key,None)


def _route_neighbors(world,sid):
 neighbors=[]
 for route in world.trade_routes.values():
  if route.a==sid:neighbors.append((route.strength,route.b,route))
  elif route.b==sid:neighbors.append((route.strength,route.a,route))
 return sorted(neighbors,key=lambda x:(-x[0],x[1]))


def _demand_score(world,people,r):
 score=0.0
 for p in people:
  if _wants(world,p,r):
   a=_aspiration(world,p);score+=.25+a.drive+.5*a.urgency+.25*a.preparation
 return score


def _travelling_merchants(world,adults):
 """Move persistent shop stock toward demand through real trade routes.

Demand is memoized by settlement and resource demand identity for this merchant
pass. Persistent inventory can grow for centuries; rescanning every local adult
for every copy of the same essence made the old pass scale with accumulated
stock rather than with the bounded set of distinct goods actually considered.
 """
 if world.year%3:return
 Layer,Ref=layer_ref()
 stock={sid:list(world.magic_resources.inventory('settlement',sid)) for sid in world.settlements}
 demand_cache={}
 def score(sid,r):
  key=(sid,_demand_key(r))
  if key not in demand_cache:demand_cache[key]=_demand_score(world,adults[sid],r)
  return demand_cache[key]
 for sid in sorted(world.settlements):
  inventory=stock[sid]
  if len(inventory)<=4:continue
  neighbors=_route_neighbors(world,sid)
  if not neighbors:continue
  moved=0
  # At most two goods move from a settlement in a merchant year. We may inspect
  # persistent stock to find them, but repeated goods reuse cached demand.
  for r in inventory:
   if moved>=2:break
   local_score=score(sid,r)
   choices=[]
   for strength,dst,route in neighbors:
    dst_score=score(dst,r)
    if dst_score>local_score:choices.append((dst_score,strength,-dst,dst,route))
   if not choices:continue
   _,_,_,dst,route=max(choices)
   e=world.emit('magic_resource_merchant_moved',Layer.SOCIETY,location=Ref('settlement',dst),
                causes=((r.origin_event,) if r.origin_event else ()),resource=r.id,
                resource_kind=r.kind,key=r.key,origin=sid,destination=dst,
                channel='travelling essence merchant')
   world.magic_resources.transfer(r.id,'settlement',dst,e.id,dst)
   route.exchanges+=1;route.last_used=world.year;moved+=1


def magic_trade_step(world,rng):
 """Annual civilization-level circulation pass; creates no magical resources."""
 adults=_adults_by_settlement(world)
 _dealer_intake(world,adults)
 _retail_browse(world,adults)
 _travelling_merchants(world,adults)
