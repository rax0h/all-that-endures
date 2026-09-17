"""Persistent magical-goods circulation for mature settlements.

This module moves existing resources only. Local dealers buy unwanted goods into
settlement inventory, people browse that literal persistent stock and purchase
what they can use, and bounded travelling merchants redistribute unsold stock
along established trade routes. A failed sale never consumes the opportunity.
"""
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
needs can inspect the distinct goods actually present and buy one affordable,
usable item per year. Priority, aspiration score and preparation never reserve
stock or decide who is allowed to shop. Those states determine what the person
wants; money and actual shelf availability determine whether a purchase occurs.

The shelf index is bounded by distinct demand identities, not accumulated copies.
A buyer who already holds an item they currently want waits to use it rather than
hoarding more stock before absorption.
 """
 Layer,Ref=layer_ref()
 institution=world.institutions.institution_by_kind('adventure_society')
 for sid,people in sorted(adults.items()):
  stock=world.magic_resources.inventory('settlement',sid)
  if not stock:continue
  shelves={}
  for r in stock:shelves.setdefault(_demand_key(r),[]).append(r)
  for goods in shelves.values():goods.sort(key=lambda r:r.id,reverse=True)
  shelf_keys=sorted(shelves,key=lambda k:(k[0],'' if k[1] is None else k[1]))
  for p in people:
   # Owning a currently useful resource is already a successful acquisition;
   # give the person a chance to absorb/use it before another retail purchase.
   held=world.magic_resources.inventory('person',p.id)
   if any(_wants(world,p,r) for r in held):continue
   choices=[]
   for key in shelf_keys:
    goods=shelves.get(key)
    if not goods:continue
    r=goods[-1]
    if not _wants(world,p,r):continue
    price=_retail_price(r)
    if p.wealth>=price or can_pay_tier(world,p.id,'iron',ceil(price)):
     choices.append((price,r.id,key,r))
   if not choices:continue
   price,_,key,r=min(choices,key=lambda x:(x[0],x[1]))
   coins={}
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
   shelves[key].pop()


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
