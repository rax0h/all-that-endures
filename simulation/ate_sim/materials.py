from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref

RARITIES=('common','uncommon','rare','epic','legendary','mythic','transcendent')

@dataclass
class MaterialLot:
 id:int;kind:str;quantity:float;quality:float;settlement:int;producer:int;created_year:int;origin_event:int;owner_kind:str;owner_id:int;magical_properties:tuple[str,...]=();consumed:float=0.;transfers:list[int]=field(default_factory=list)
@dataclass
class CraftedItem:
 id:int;kind:str;quality:float;rarity:str;settlement:int;craftsperson:int;created_year:int;origin_event:int;materials:tuple[int,...];magical_properties:tuple[str,...]=();owner_kind:str='person';owner_id:int|None=None
@dataclass
class MaterialEconomy:
 lots:dict[int,MaterialLot]=field(default_factory=dict);items:dict[int,CraftedItem]=field(default_factory=dict);next_lot:int=1;next_item:int=1
 def create_lot(self,kind,quantity,quality,sid,producer,year,event,properties=()):
  i=self.next_lot;self.next_lot+=1;l=MaterialLot(i,kind,quantity,quality,sid,producer,year,event,'person',producer,tuple(properties));self.lots[i]=l;return l
 def available(self,sid,kind=None):return [l for l in self.lots.values() if l.settlement==sid and l.quantity-l.consumed>.01 and (kind is None or l.kind==kind)]
 def create_item(self,kind,quality,rarity,sid,crafter,year,event,materials,properties=()):
  i=self.next_item;self.next_item+=1;x=CraftedItem(i,kind,quality,rarity,sid,crafter,year,event,tuple(materials),tuple(properties),'person',crafter);self.items[i]=x;return x

def _essence_keys(world,pid):
 p=world.advancement.path(pid);return set() if p is None else set(p.base_essences)
def _raw_kind(cell,rr):
 weighted=['grain','clay','stone']
 if cell.forest>.35:weighted+=['timber','timber']
 if cell.fertility>.5:weighted+=['wool','wool','grain']
 if cell.elevation>.45:weighted+=['ore','stone']
 return weighted[int(rr.random()*len(weighted))%len(weighted)]
def _magic_property(world,p,kind,sid,rr):
 keys=_essence_keys(world,p.id);season=world.year%4;local=world.local[sid];props=[]
 if kind=='wool' and season==3 and ('cold' in keys or 'ice' in keys or 'moon' in keys):props.append('winter-bound warmth')
 if kind in ('grain','wool') and ('growth' in keys or 'life' in keys or 'renewal' in keys):props.append('vital abundance')
 if kind in ('clay','stone','ore') and ('earth' in keys or 'iron' in keys or 'crystal' in keys):props.append('earth resonance')
 if kind=='timber' and ('plant' in keys or 'growth' in keys):props.append('living grain')
 if kind=='wool' and local.rain>.72 and season==1 and rr.random()<.08:props.append('rain-silvered fibre')
 return tuple(dict.fromkeys(props))
def _rarity(q,rank,magical):
 score=q+.07*rank+(.16 if magical else 0.)
 return RARITIES[min(len(RARITIES)-1,max(0,int(score*4)-1))]
def _craft_kind(material):return {'wool':'textile','clay':'ceramic','stone':'masonry','timber':'woodwork','ore':'metalwork','grain':'provisions'}.get(material,'craft')

def material_economy_step(world,rng):
 Layer,Ref=layer_ref();living=world.living_by_settlement()
 for sid,people in sorted(living.items()):
  adults=[p for p in people if p.age>=16]
  if not adults:continue
  s=world.settlements[sid];cell=world.cells[(s.x,s.y)];rr=rng.stream('materials',world.year,sid)
  # Real producers create bounded batches; ecology and practiced skill determine what is available.
  producers=sorted(adults,key=lambda p:(world.skills.get(p.id,'agriculture').level+world.skills.get(p.id,'craft').level,p.curiosity,-p.id),reverse=True)[:max(1,min(8,len(adults)))]
  producer=producers[int(rr.random()*len(producers))%len(producers)];kind=_raw_kind(cell,rr);skill=world.skills.get(producer.id,'agriculture' if kind in ('grain','wool','timber') else 'craft').level;quality=max(.05,min(1.25,.25+.08*skill+.2*rr.random()));props=_magic_property(world,producer,kind,sid,rr)
  e=world.emit('material_produced',Layer.REALITY,(Ref('person',producer.id),),Ref('settlement',sid),material=kind,quantity=round(2+skill+rr.random()*4,2),quality=round(quality,3),magical_properties=props);lot=world.materials.create_lot(kind,2+skill+rr.random()*4,quality,sid,producer.id,world.year,e.id,props)
  # Craftspeople can only consume material batches that actually exist locally.
  candidates=sorted(adults,key=lambda p:(world.skills.get(p.id,'craft').level,p.curiosity,-p.id),reverse=True)
  crafter=candidates[0]
  craft_skill=world.skills.get(crafter.id,'craft').level
  available=world.materials.available(sid)
  if craft_skill<.7 or not available or rr.random()>.55:continue
  # Skilled makers actively seek better material instead of receiving arbitrary quality.
  lot=max(available,key=lambda l:(l.quality+(.2 if l.magical_properties else 0.),-l.id)) if craft_skill>=2 else available[int(rr.random()*len(available))%len(available)]
  if lot.owner_kind=='person' and lot.owner_id!=crafter.id:
   seller=world.people.get(lot.owner_id);price=max(.05,(1+lot.quality)*(1+.5*len(lot.magical_properties)))
   if seller is not None and crafter.wealth>=price:
    crafter.wealth-=price;seller.wealth+=price;t=world.emit('material_purchased',Layer.SOCIETY,(Ref('person',crafter.id),Ref('person',seller.id)),Ref('settlement',sid),(lot.origin_event,),material_lot=lot.id,price=round(price,3));lot.owner_id=crafter.id;lot.transfers.append(t.id)
   else:continue
  used=min(1.,lot.quantity-lot.consumed);lot.consumed+=used;rank=world.advancement.rank(crafter.id);q=max(.05,min(1.5,.45*lot.quality+.09*craft_skill+.04*rank+rr.uniform(-.08,.08)));rarity=_rarity(q,rank,lot.magical_properties)
  # Transcendent output requires a transcendent maker; ordinary skill cannot roll into it.
  soul=world.metaphysics.soul(crafter.id)
  if rarity=='transcendent' and soul.ontology=='mortal':rarity='mythic'
  ce=world.emit('item_crafted',Layer.REALITY,(Ref('person',crafter.id),),Ref('settlement',sid),(lot.origin_event,),item_kind=_craft_kind(lot.kind),material_lots=(lot.id,),quality=round(q,3),rarity=rarity,magical_properties=lot.magical_properties);world.materials.create_item(_craft_kind(lot.kind),q,rarity,sid,crafter.id,world.year,ce.id,(lot.id,),lot.magical_properties)
  if craft_skill>=2.5:crafter.occupation='craftsperson'
