from __future__ import annotations
from .core_types import layer_ref
from .metaphysics import try_resurrection

def kill(world,p,cause,causes=()):
 if not p.alive:return None
 Layer,Ref=layer_ref();p.alive=False;e=world.emit('death',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),causes,age=p.age,rank=p.rank,species=p.species,cause=cause);world.metaphysics.record_death(p.id)
 if try_resurrection(world,p.id,e) is not None:return e
 h=world.households[p.household];survivors=[i for i in h.members if i!=p.id and world.people[i].alive]
 for oid in survivors:
  q=world.people[oid];rel=world.social.get(p.id,oid);q.grief=min(1,q.grief+.12+.55*rel.attachment);world.social.record(p.id,oid,e.id,attachment=.01);world.emit('bereavement',Layer.SOCIETY,(Ref('person',oid),Ref('person',p.id)),Ref('settlement',p.settlement),(e.id,),grief=q.grief)
 if survivors:
  children=[x for x in world.genealogy.children.get(p.id,[]) if world.people.get(x) and world.people[x].alive];heir=min(children) if children else min(survivors);inherited=p.wealth;world.people[heir].wealth+=inherited;p.wealth=0.;world.emit('inheritance',Layer.SOCIETY,(Ref('person',heir),Ref('person',p.id)),Ref('settlement',p.settlement),(e.id,),wealth=inherited)
 return e
