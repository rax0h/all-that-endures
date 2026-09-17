"""Persistent magical-goods circulation for mature settlements.

This module moves existing resources only.  Local dealers buy unwanted goods into
settlement inventory, and bounded travelling merchants redistribute that stock
along established trade routes.  The existing magic ecology market remains the
authoritative retail buyer: failed sales therefore leave stock available for a
later buyer instead of consuming the opportunity.
"""
from .core_types import layer_ref
from .magic_resources import _wants, _aspiration


def _adults_by_settlement(world):
 out={sid:[] for sid in world.settlements}
 for p in world.current_people():
  if p.alive and p.age>=16:out[p.settlement].append(p)
 for people in out.values():people.sort(key=lambda p:p.id)
 return out


def _dealer_intake(world,adults):
 """Put person-held surplus into persistent local shop stock.

Ordinary wealth is the existing non-ranked civilian economy, not conserved
ranked coin.  Dealers pay a modest wholesale price; retail spread represents
storage, brokerage and transport.  At most one item/person/year enters stock,
so this is bounded by living adults rather than resources x people.
 """
 Layer,Ref=layer_ref()
 for sid,people in sorted(adults.items()):
  for p in people:
   held=world.magic_resources.inventory('person',p.id)
   if not held:continue
   surplus=[r for r in held if not _wants(world,p,r)]
   if not surplus:continue
   # Stable oldest-first inventory disposal prevents a random annual lottery
   # from trapping an unwanted resource indefinitely.
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


def _route_neighbors(world,sid):
 neighbors=[]
 for key,route in world.trade_routes.items():
  if route.a==sid:neighbors.append((route.strength,route.b,route))
  elif route.b==sid:neighbors.append((route.strength,route.a,route))
 return sorted(neighbors,key=lambda x:(-x[0],x[1]))


def _demand_score(world,people,r):
 # Merchant batches are tiny, so this bounded local scan is cheaper than a
 # global resource-person market and preserves actual essence compatibility.
 score=0.0
 for p in people:
  if _wants(world,p,r):
   a=_aspiration(world,p);score+=.25+a.drive+.5*a.urgency+.25*a.preparation
 return score


def _travelling_merchants(world,adults):
 """Move persistent shop stock toward demand through real trade routes."""
 if world.year%3:return
 Layer,Ref=layer_ref()
 # Snapshot prevents the same item hopping through many settlements in one year.
 stock={sid:list(world.magic_resources.inventory('settlement',sid)) for sid in world.settlements}
 for sid in sorted(world.settlements):
  inventory=stock[sid]
  if len(inventory)<=4:continue
  neighbors=_route_neighbors(world,sid)
  if not neighbors:continue
  moved=0
  for r in inventory:
   if moved>=2:break
   local_score=_demand_score(world,adults[sid],r)
   choices=[]
   for strength,dst,route in neighbors:
    score=_demand_score(world,adults[dst],r)
    if score>local_score:choices.append((score,strength,-dst,dst,route))
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
 _travelling_merchants(world,adults)
