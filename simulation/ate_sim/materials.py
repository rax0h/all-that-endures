from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref
from heapq import heappush, heappop, heapify
RARITIES=('common','uncommon','rare','epic','legendary','mythic','transcendent')
@dataclass
class MaterialLot:
 id:int;kind:str;quantity:float;quality:float;settlement:int;producer:int;created_year:int;origin_event:int;owner_kind:str;owner_id:int;magical_properties:tuple[str,...]=();consumed:float=0.;transfers:list[int]=field(default_factory=list);material_rank:int=0
@dataclass
class CraftedItem:
 id:int;kind:str;quality:float;rarity:str;settlement:int;craftsperson:int;created_year:int;origin_event:int;materials:tuple[int,...];magical_properties:tuple[str,...]=();owner_kind:str='person';owner_id:int|None=None;item_rank:int=0;magical:bool=False
@dataclass
class MaterialEconomy:
 lots:dict[int,MaterialLot]=field(default_factory=dict);items:dict[int,CraftedItem]=field(default_factory=dict);lot_index:dict[int,list[int]]=field(default_factory=dict);active_lot_index:dict[int,set[int]]=field(default_factory=dict);next_lot:int=1;next_item:int=1
 def create_lot(self,kind,quantity,quality,sid,producer,year,event,properties=(),material_rank=0):
  i=self.next_lot;self.next_lot+=1;l=MaterialLot(i,kind,quantity,quality,sid,producer,year,event,'person',producer,tuple(properties),0,[],material_rank);self.lots[i]=l;self.lot_index.setdefault(sid,[]).append(i);self.active_lot_index.setdefault(sid,set()).add(i)
  if hasattr(self,'_selection_index'):
   heaps,counts=self._selection_index;heappush(heaps.setdefault(sid,[]),self._selection_key(l));counts[sid]=counts.get(sid,0)+bool(l.magical_properties)
  return l
 def available(self,sid,kind=None):
  ids=self.active_lot_index.get(sid,())
  return [self.lots[i] for i in ids if (kind is None or self.lots[i].kind==kind)]
 def consume(self,lot,amount):
  used=min(max(0.,amount),max(0.,lot.quantity-lot.consumed));lot.consumed+=used
  if lot.quantity-lot.consumed<=.01:
   active=self.active_lot_index.get(lot.settlement,set())
   if lot.id in active:
    active.discard(lot.id)
    if hasattr(self,'_selection_index'):
     _,counts=self._selection_index;counts[lot.settlement]=counts.get(lot.settlement,0)-bool(lot.magical_properties)
  return used
 def rebuild_active_index(self):
  self.__dict__.pop('_selection_index',None)
  self.active_lot_index={}
  for sid,ids in self.lot_index.items():
   active={i for i in ids if i in self.lots and self.lots[i].quantity-self.lots[i].consumed>.01}
   if active:self.active_lot_index[sid]=active
 def _selection_key(self,lot):
  return (-(lot.quality+(.2 if lot.magical_properties else 0.)),lot.id)
 def _ensure_selection_index(self):
  # Derived runtime state: excluded from canonical history, rebuilt for old checkpoints.
  # Quality/properties are fixed after creation. Rebuild after explicit data repair.
  if not hasattr(self,'_selection_index'):
   heaps={};counts={}
   for sid,ids in self.active_lot_index.items():
    heaps[sid]=[self._selection_key(self.lots[i]) for i in ids];heapify(heaps[sid])
    counts[sid]=sum(bool(self.lots[i].magical_properties) for i in ids)
   self._selection_index=(heaps,counts)
  return self._selection_index
 def has_available(self,sid):
  return bool(self.active_lot_index.get(sid))
 def best_available(self,sid):
  heaps,_=self._ensure_selection_index();heap=heaps.get(sid,[]);active=self.active_lot_index.get(sid,())
  while heap and heap[0][1] not in active:heappop(heap)
  return self.lots[heap[0][1]] if heap else None
 def magical_available_count(self,sid):
  return self._ensure_selection_index()[1].get(sid,0)
 def create_item(self,kind,quality,rarity,sid,crafter,year,event,materials,properties=(),item_rank=0,magical=False):
  i=self.next_item;self.next_item+=1;x=CraftedItem(i,kind,quality,rarity,sid,crafter,year,event,tuple(materials),tuple(properties),'person',crafter,item_rank,magical);self.items[i]=x;return x

def _essence_keys(world,pid):
 p=world.advancement.path(pid);return set() if p is None else set(p.base_essences)
def _raw_kind(cell,rr):
 weighted=['grain','clay','stone']
 if cell.forest>.35:weighted+=['timber','timber']
 if cell.fertility>.5:weighted+=['wool','wool','grain']
 if cell.elevation>.45:weighted+=['ore','stone']
 return weighted[int(rr.random()*len(weighted))%len(weighted)]
def _magic_property(world,p,kind,sid,rr):
 keys=_essence_keys(world,p.id);season=world.year%4;local=world.local[sid];ambient=world.ambient_magic.field(sid).level;props=[]
 if kind=='wool' and season==3 and ('cold' in keys or 'ice' in keys or 'moon' in keys):props.append('winter-bound warmth')
 if kind in ('grain','wool') and ('growth' in keys or 'life' in keys or 'renewal' in keys):props.append('vital abundance')
 if kind in ('clay','stone','ore') and ('earth' in keys or 'iron' in keys or 'crystal' in keys):props.append('earth resonance')
 if kind=='timber' and ('plant' in keys or 'growth' in keys):props.append('living grain')
 if kind=='wool' and local.rain>.72 and season==1 and rr.random()<.08:props.append('rain-silvered fibre')
 if ambient>.72 and rr.random()<min(.25,(ambient-.72)*.3):props.append('ambient-saturated')
 return tuple(dict.fromkeys(props))
def _rarity(q,rank,magical):
 score=q+.07*rank+(.16 if magical else 0.);return RARITIES[min(len(RARITIES)-1,max(0,int(score*4)-1))]
def _craft_kind(material):return {'wool':'textile','clay':'ceramic','stone':'masonry','timber':'woodwork','ore':'metalwork','grain':'provisions'}.get(material,'craft')
def _material_rank(world,sid,props,rr):
 if not props:return 0
 ambient=world.ambient_magic.field(sid).level
 if ambient<.72:return 1
 return min(6,1+int((ambient-.72)*5)+(1 if ambient>1.15 and rr.random()<.05 else 0))
def _magical_craft_permission(world,crafter,target_rank,craft_skill):
 maker=world.advancement.rank(crafter.id)
 if maker<=0:return False
 if target_rank<=maker:return True
 path=world.advancement.path(crafter.id)
 if path is None:return False
 craft_domains=('craft','forge','creation','rune','transformation','weave')
 gift=any(any(k in (a.domain or '').lower() or k in (a.function or '').lower() for k in craft_domains) for a in path.abilities)
 return gift and target_rank<=maker+1 and craft_skill>=2.5

def _produce_lot(world,sid,producer,rr,Layer,Ref):
 s=world.settlements[sid];cell=world.cells[(s.x,s.y)];kind=_raw_kind(cell,rr);skill=world.skills.get(producer.id,'agriculture' if kind in ('grain','wool','timber') else 'craft').level;quality=max(.05,min(1.25,.25+.08*skill+.2*rr.random()));props=_magic_property(world,producer,kind,sid,rr);mr=_material_rank(world,sid,props,rr)
 demand=1+.45*world.local[sid].scarcity+.25*s.prosperity;qty=(2+skill+rr.random()*4)*demand;e=world.emit('material_produced',Layer.REALITY,(Ref('person',producer.id),),Ref('settlement',sid),material=kind,quantity=round(qty,2),quality=round(quality,3),magical_properties=props,material_rank=mr);return world.materials.create_lot(kind,qty,quality,sid,producer.id,world.year,e.id,props,mr)
def _craft_once(world,sid,crafter,rr,Layer,Ref):
 craft_skill=world.skills.get(crafter.id,'craft').level
 if craft_skill<.7 or not world.materials.has_available(sid):return False
 if craft_skill>=2:lot=world.materials.best_available(sid)
 else:
  available=world.materials.available(sid);lot=available[int(rr.random()*len(available))%len(available)]
 if lot.owner_kind=='person' and lot.owner_id!=crafter.id:
  seller=world.people.get(lot.owner_id);price=max(.05,(1+lot.quality)*(1+.5*len(lot.magical_properties))*(1+.4*lot.material_rank))
  if seller is None or crafter.wealth<price:return False
  crafter.wealth-=price;seller.wealth+=price;t=world.emit('material_purchased',Layer.SOCIETY,(Ref('person',crafter.id),Ref('person',seller.id)),Ref('settlement',sid),(lot.origin_event,),material_lot=lot.id,price=round(price,3));lot.owner_id=crafter.id;lot.transfers.append(t.id)
 used=world.materials.consume(lot,1.);rank=world.advancement.rank(crafter.id);q=max(.05,min(1.5,.45*lot.quality+.09*craft_skill+.04*rank+rr.uniform(-.08,.08)));target=max(0,min(lot.material_rank,rank+1));magical=bool(lot.magical_properties) and _magical_craft_permission(world,crafter,target,craft_skill);item_props=lot.magical_properties if magical else ();rarity=_rarity(q,rank,magical)
 if used<=0:return False
 if not magical and lot.magical_properties:rarity=_rarity(q,0,False)
 ce=world.emit('item_crafted',Layer.REALITY,(Ref('person',crafter.id),),Ref('settlement',sid),(lot.origin_event,),item_kind=_craft_kind(lot.kind),material_lots=(lot.id,),quality=round(q,3),rarity=rarity,magical=magical,item_rank=target if magical else 0,magical_properties=item_props,material_properties_retained=lot.magical_properties if not magical else ());world.materials.create_item(_craft_kind(lot.kind),q,rarity,sid,crafter.id,world.year,ce.id,(lot.id,),item_props,target if magical else 0,magical)
 if craft_skill>=2.5:crafter.occupation='craftsperson'
 return True

def material_economy_step(world,rng):
 Layer,Ref=layer_ref();living=world.living_by_settlement()
 for sid,people in sorted(living.items()):
  adults=[p for p in people if p.age>=16]
  if not adults:continue
  s=world.settlements[sid];rr=rng.stream('materials',world.year,sid);producers=sorted(adults,key=lambda p:(world.skills.get(p.id,'agriculture').level+world.skills.get(p.id,'craft').level,p.curiosity,-p.id),reverse=True)[:max(1,min(16,len(adults)))]
  pressure=world.local[sid].scarcity*.8+s.prosperity*.35
  labor_batches=len(adults)//12
  pressure_batches=int(pressure*2)
  lot_count=min(8,max(1,1+labor_batches+pressure_batches))
  for n in range(lot_count):
   prng=rng.stream('material_producer',world.year,sid*100+n);producer=producers[int(prng.random()*len(producers))%len(producers)];_produce_lot(world,sid,producer,prng,Layer,Ref)
  crafters=sorted(adults,key=lambda p:(world.skills.get(p.id,'craft').level,p.curiosity,-p.id),reverse=True);qualified=[p for p in crafters if world.skills.get(p.id,'craft').level>=.7]
  if not qualified:continue
  available=world.materials.available(sid);available_units=sum(max(0.,l.quantity-l.consumed) for l in available);craft_count=min(10,max(0,int(available_units//8)),max(1,len(qualified)//35))
  for n in range(craft_count):
   crng=rng.stream('material_craft',world.year,sid*100+n);crafter=qualified[n%len(qualified)]
   if crng.random()<=min(.82,.28+.30*s.prosperity+.22*world.local[sid].scarcity):_craft_once(world,sid,crafter,crng,Layer,Ref)
