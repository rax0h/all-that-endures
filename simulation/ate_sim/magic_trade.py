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
from .magic_resources import _wants, _aspiration, _demand_key, absorb_essence_resource, use_awakening_stone


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
   wholesale=round(_retail_price(r)*.55,2) if r.kind=='essence' else 1.5
   p.wealth+=wholesale
   e=world.emit('magic_resource_listed',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',sid),
                ((r.origin_event,) if r.origin_event else ()),resource=r.id,
                resource_kind=r.kind,key=r.key,rarity=r.rarity,
                channel='local essence dealer',wholesale_price=round(wholesale,2),
                price_domain='ordinary_wealth')
   world.magic_resources.transfer(r.id,'settlement',sid,e.id,sid)


def _retail_price(resource):
 """Civilian shelf price in ordinary wealth.

 Common/uncommon essences are entry-level goods in a mature magical economy;
 rarity, rather than basic access to magic, carries the steep price curve.
 """
 if resource.kind!='essence':return 3
 rarity=str(resource.rarity).lower()
 if 'transcendent' in rarity:return 21.
 if 'mythic' in rarity:return 13.
 if 'legendary' in rarity:return 8.
 if 'epic' in rarity:return 5.
 if 'rare' in rarity:return 3.
 if 'uncommon' in rarity:return 1.5
 if 'common' in rarity:return 1.
 return 2.


def _retail_browse(world,adults,rng=None):
 """Let people buy ordinary magical goods from literal local shelf stock.

Essences are the beginning of a magical path, not a multi-year acquisition
quest. A shopper who wants base essences may buy every useful affordable base
essence needed for their current goal in the same annual shopping pass. Each
purchased essence is absorbed immediately. Adventurers/full-path aspirants can
therefore leave an adequately stocked shop with all three bases in one visit.

Scarce stock is still first-come rather than allocated by a controller. Urgency,
drive and preparation affect deterministic arrival order only when buyers really
are competing for too few goods.
 """
 Layer,Ref=layer_ref()
 institution=world.institutions.institution_by_kind('adventure_society')
 for sid,people in sorted(adults.items()):
  stock=world.magic_resources.inventory('settlement',sid)
  if not stock:continue
  essence_by_key={};stone_heap=[]
  for resource in stock:
   if resource.kind=='essence':essence_by_key.setdefault(resource.key,[]).append(resource.id)
   else:stone_heap.append(resource.id)
  for heap in essence_by_key.values():heapify(heap)
  heapify(stone_heap)
  essence_front={key:heap[0] for key,heap in essence_by_key.items() if heap}
  eligible=[]
  for p in people:
   a=_aspiration(world,p);path=world.advancement.path(p.id)
   base=0 if path is None else len(path.base_essences)
   abilities=0 if path is None else len(path.abilities)
   if base<a.desired_base_essences or (path is not None and abilities<min(a.desired_abilities,path.capacity)):
    eligible.append(p)
  if rng is None:
   shoppers=eligible
  else:
   arrivals=[]
   for p in eligible:
    a=_aspiration(world,p)
    effort=.45*a.urgency+.15*a.drive+.10*a.preparation
    rr=rng.stream('magic_shopping_arrival',world.year,p.id)
    arrivals.append((rr.random()-effort,p.id,p))
   shoppers=[p for _,_,p in sorted(arrivals,key=lambda x:(x[0],x[1]))]

  def purchase(p,r,price):
   coins={}
   if p.wealth>=price:p.wealth-=price
   elif institution is not None and can_pay_tier(world,p.id,'iron',ceil(price)):
    coins=world.currency.treasury_transfer(institution.id,p.id,{'iron':ceil(price)},deposit=True)
   else:return False
   e=world.emit('magic_resource_purchased',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',sid),
                ((r.origin_event,) if r.origin_event else ()),resource=r.id,key=r.key,
                price=price,coin_deposit=coins,
                institution=None if institution is None else institution.id,
                price_domain='ranked_coin' if coins else 'ordinary_wealth',
                channel='local essence dealer',mechanism='browsed shelf stock')
   world.magic_resources.transfer(r.id,'person',p.id,e.id,sid)
   return True

  for p in shoppers:
   # Base essences come first. Keep buying while this person's own path goal is
   # unmet and distinct affordable essences are physically on the shelf.
   while essence_front:
    a=_aspiration(world,p);path=world.advancement.path(p.id)
    base=0 if path is None else len(path.base_essences)
    if base>=a.desired_base_essences:break
    owned=set() if path is None else set(path.base_essences)
    candidates=[]
    for key,rid in essence_front.items():
     if key in owned:continue
     resource=world.magic_resources.resources[rid];price=_retail_price(resource)
     if p.wealth>=price or can_pay_tier(world,p.id,'iron',ceil(price)):
      candidates.append((price,rid,key))
    if not candidates:break
    price,rid,key=min(candidates);resource=world.magic_resources.resources[rid]
    if not purchase(p,resource,price):break
    heap=essence_by_key[key];removed=heappop(heap);assert removed==rid
    if heap:essence_front[key]=heap[0]
    else:essence_front.pop(key,None)
    absorb_essence_resource(world,p.id,rid)

   # Awakening stones have no artificial annual throttle. A committed
   # adventurer who can afford the physically available stock may buy as many
   # stones as needed in this visit, up to the path's actual ability capacity.
   a=_aspiration(world,p)
   while stone_heap:
    path=world.advancement.path(p.id);abilities=0 if path is None else len(path.abilities)
    wants_stone=path is not None and abilities<a.desired_abilities and abilities<path.capacity
    if not wants_stone or not (p.wealth>=3 or can_pay_tier(world,p.id,'iron',3)):break
    rid=stone_heap[0];resource=world.magic_resources.resources[rid]
    if not purchase(p,resource,3):break
    heappop(stone_heap)
    # A shop visit is not an annual awakening timer. The purchased stone is
    # physically in hand and may be used immediately; repeat while stock,
    # funds and the person's own path goal permit it.
    if use_awakening_stone(world,p.id,rid) is None:break


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
 _retail_browse(world,adults,rng)
 _travelling_merchants(world,adults)
