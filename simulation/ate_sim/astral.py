from __future__ import annotations
from dataclasses import dataclass,field

GREAT_ASTRAL_BEINGS={
 'world_phoenix':('World-Phoenix',('worlds','passage','renewal')),
 'reaper':('Reaper',('death','ending','transition')),
 'builder':('Builder',('creation','construction','worlds')),
}

@dataclass
class GreatAstralBeing:
 id:str
 name:str
 authorities:tuple[str,...]
 ontology:str='great_astral_being'
 transcendent:bool=True
 interventions:list[int]=field(default_factory=list)
 relationships:dict[int,float]=field(default_factory=dict)

@dataclass
class AstralState:
 great_astral_beings:dict[str,GreatAstralBeing]=field(default_factory=dict)

 def seed_cosmology(self):
  if self.great_astral_beings:return
  for eid,(name,authorities) in GREAT_ASTRAL_BEINGS.items():self.great_astral_beings[eid]=GreatAstralBeing(eid,name,authorities)

 def entity(self,eid):return self.great_astral_beings.get(eid)


def seed_astral_cosmology(world):world.astral.seed_cosmology()


def grant_world_phoenix_resurrection(world,pid,causes=()):
 from .metaphysics import grant_resurrection_token
 entity=world.astral.entity('world_phoenix')
 if entity is None:raise ValueError('World-Phoenix is not present in cosmology')
 token=grant_resurrection_token(world,pid,'great_astral_being','world_phoenix',causes);entity.interventions.append(token.grant_event);entity.relationships[pid]=max(entity.relationships.get(pid,0.),.25);world.metaphysics.mark(pid,'world_phoenix_touched','world_phoenix',.25);return token
