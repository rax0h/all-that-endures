from __future__ import annotations
from .core_types import layer_ref
from .magic_progression import practice_ability,record_body_transition
from .magic_resources import _aspiration
from .mastery_training import mastery_training_step
ACTION_FUNCTIONS={'secure_food':{'creation','control','support','detection','recovery'},'prepare':{'enhancement','control','movement','detection','recovery'},'work':{'creation','enhancement','control','support','exchange','transformation'},'socialize':{'influence','support','detection','exchange'},'learn':{'detection','control','transformation','support'},'teach':{'influence','support','control','exchange'},'build':{'creation','enhancement','control','transformation'}}
RARITY_CATALYST={'rare':.20,'epic':.35,'legendary':.55,'mythic':.75,'transcendent':1.}

def _career_training(world,p,path,asp,member,strength):
 rank=world.advancement.rank(p.id)
 if len(path.abilities)!=20:return None
 commitment=max(0.,min(1.,.45*asp.drive+.30*asp.urgency+.25*p.curiosity));combat=asp.adventurer_aspiration or p.occupation in ('adventurer','guard','hunter','soldier');professional=member or combat
 if rank==1:
  if not professional and commitment<.50:return None
  return (2.0+.65*strength+.40*commitment,10,.14+.18*p.curiosity)
 if rank==2:
  if not professional and commitment<.48:return None
  return (1.0+.34*strength+.28*commitment,8,.24+.24*p.curiosity)
 if rank==3:
  if commitment<.38:return None
  return (.58+.20*strength+.24*commitment,8,.52+.36*p.curiosity)
 if rank==4:
  if commitment<.68 or p.curiosity<.58:return None
  return (.14+.05*strength+.07*commitment,4,.82+.16*p.curiosity)
 return None

def _local_cores(world,sid):
 ids=world.materials.active_lot_index.get(sid,())
 return sorted((world.materials.lots[i] for i in ids if world.materials.lots[i].kind=='monster_core' and world.materials.lots[i].quantity-world.materials.lots[i].consumed>.01),key=lambda x:(x.material_rank,x.created_year,x.id))

def _owned_catalyst(world,pid):
 # Items are sparse; only Silver people call this, avoiding a global annual item
 # scan for the overwhelmingly Iron/Bronze/unranked population.
 best=None
 for item in world.materials.items.values():
  if item.owner_kind!='person' or item.owner_id!=pid or not item.magical or item.rarity not in RARITY_CATALYST:continue
  if best is None or (RARITY_CATALYST[item.rarity],item.item_rank,-item.id)>(RARITY_CATALYST[best.rarity],best.item_rank,-best.id):best=item
 return best

def _use_core(world,p,path,cores):
 if len(path.abilities)!=20 or not cores:return None
 rank=world.advancement.rank(p.id)
 if rank<=0 or rank>=5:return None
 lot=next((x for x in cores if x.quantity-x.consumed>.01 and x.material_rank<=max(1,rank)),None)
 if lot is None:return None
 seller=world.people.get(lot.owner_id) if lot.owner_kind=='person' else None;price=float(1+3*lot.material_rank)
 if seller is not None and seller.id!=p.id:
  if p.wealth<price:return None
  p.wealth-=price;seller.wealth+=price
 Layer,Ref=layer_ref();actors=(Ref('person',p.id),) if seller is None or seller.id==p.id else (Ref('person',p.id),Ref('person',seller.id));bought=world.emit('monster_core_acquired',Layer.SOCIETY,actors,Ref('settlement',p.settlement),(lot.origin_event,),core_lot=lot.id,core_rank=lot.material_rank,price=0. if seller is None or seller.id==p.id else price,mechanism='owned core' if seller is not None and seller.id==p.id else 'local core purchase')
 if world.materials.consume(lot,1.)<=0:return None
 i,_=min(enumerate(path.abilities),key=lambda x:(x[1].rank,x[1].level,x[1].progress,x[0]));strength=.35+.15*lot.material_rank;practice_ability(world,p,i,0.,0.,context='monster_core',core=strength,core_event=bought.id);world.emit('monster_core_consumed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),(bought.id,),core_lot=lot.id,core_rank=lot.material_rank,ability=path.abilities[i].semantic_key,core_strength=strength,grants_understanding=False);return lot

def _apply_catalyst(world,p,path,ability,item):
 if item is None or ability.rank!=3 or not ability.understanding.ready(3):return
 strength=RARITY_CATALYST[item.rarity]
 if world.advancement.integrate_path(p.id,ability,0.,item.origin_event,strength):
  Layer,Ref=layer_ref();world.emit('path_integration_catalyzed',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),(item.origin_event,),ability=ability.semantic_key,item=item.id,rarity=item.rarity,mechanism='rare magical item amplifying earned introspection')

def rank_ecology_step(world,rng):
 Layer,Ref=layer_ref();adv=world.institutions.institution_by_kind('adventure_society');members=set() if adv is None else adv.members;latest={};core_cache={}
 for rec in reversed(world.agency.actions):
  if rec.year!=world.year:break
  latest.setdefault(rec.person,rec)
 for p in sorted((x for x in world.current_people() if x.alive),key=lambda x:x.id):
  path=world.advancement.path(p.id)
  if path is None or not path.abilities:continue
  rec=latest.get(p.id);action='work' if rec is None else rec.action;strength=.35 if rec is None else rec.strength;relevant=ACTION_FUNCTIONS.get(action,set());indexed=list(enumerate(path.abilities));weakest=min((a.rank,a.level,a.progress) for _,a in indexed);asp=_aspiration(world,p);member=p.id in members;career=_career_training(world,p,path,asp,member,strength);purposeful_reflection=None
  if career is not None:exposure,uses,purposeful_reflection=career;candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))
  elif member:
   candidates=[x for x in indexed if (x[1].rank,x[1].level,x[1].progress)<=weakest]
   if len(candidates)<4:candidates=sorted(indexed,key=lambda x:(x[1].rank,x[1].level,x[1].progress))[:8]
   exposure=.24+.16*strength;uses=min(len(candidates),5)
  else:candidates=[x for x in indexed if x[1].function in relevant] or indexed;exposure=.11+.14*strength;uses=min(len(candidates),3)
  rr=rng.stream('rank_ecology',world.year,p.id);rr.shuffle(candidates);before=world.advancement.rank(p.id);body_rank=before;catalyst=_owned_catalyst(world,p.id) if body_rank==3 else None
  for i,a in candidates[:uses]:
   reflection=purposeful_reflection if purposeful_reflection is not None else ((.45+.55*p.curiosity) if action in ('learn','teach','socialize') else .10*p.curiosity);practice_ability(world,p,i,exposure*(.8+.4*rr.random()),reflection,context=action);_apply_catalyst(world,p,path,a,catalyst)
  if len(path.abilities)==20 and rr.random()<min(.55,.08+.28*asp.drive+.12*asp.urgency):
   local=core_cache.get(p.settlement)
   if local is None:local=core_cache[p.settlement]=_local_cores(world,p.settlement)
   _use_core(world,p,path,local)
  body_rank=world.advancement.rank(p.id)
  if len(path.abilities)==20 and body_rank>=3 and (member or action in ('work','learn','teach','build','prepare')):mastery_training_step(world,p,path,rng.stream('mastery_training',world.year,p.id))
  after=world.advancement.rank(p.id);p.rank=after;record_body_transition(world,p,before,context=action)
