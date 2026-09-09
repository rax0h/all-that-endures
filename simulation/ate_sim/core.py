from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib, random
from typing import Any

class Layer(str, Enum):
    REALITY="reality"; SOCIETY="society"; KNOWLEDGE="knowledge"; NARRATIVE="narrative"
@dataclass(frozen=True)
class Ref: kind:str; id:int
@dataclass
class Event:
    id:int; year:int; kind:str; layer:Layer; actors:tuple[Ref,...]=(); location:Ref|None=None; causes:tuple[int,...]=(); data:dict[str,Any]=field(default_factory=dict)
@dataclass
class Person:
    id:int; born:int; settlement:int; household:int; alive:bool=True; age:int=0; wealth:float=0.; health:float=1.; temperament:float=.5; attachment:float=.5; curiosity:float=.5; inhibition:float=.5; grief:float=0.; fear:float=0.; rank:int=0; species:str="human"; occupation:str="labor"
@dataclass
class Household:
    id:int; settlement:int; members:list[int]=field(default_factory=list); wealth:float=0.; food:float=10.; preparedness:float=.2; lineage:str=""; alive:bool=True
@dataclass
class Settlement:
    id:int; x:int; y:int; households:list[int]=field(default_factory=list); food_stock:float=100.; defense:float=.1; irrigation:float=.1; roads:float=.1; prosperity:float=.3; memory:dict[str,float]=field(default_factory=dict)
@dataclass
class Cell:
    x:int; y:int; elevation:float; moisture:float; fertility:float; forest:float; hazard:float
@dataclass
class World:
    seed:int; year:int=0; cells:dict[tuple[int,int],Cell]=field(default_factory=dict); people:dict[int,Person]=field(default_factory=dict); households:dict[int,Household]=field(default_factory=dict); settlements:dict[int,Settlement]=field(default_factory=dict); events:list[Event]=field(default_factory=list); next_person:int=1; next_household:int=1; next_settlement:int=1; next_event:int=1
    def emit(self,kind,layer,actors=(),location=None,causes=(),**data):
        e=Event(self.next_event,self.year,kind,layer,tuple(actors),location,tuple(causes),data); self.next_event+=1; self.events.append(e); return e
    def digest(self): return hashlib.sha256(repr(asdict(self)).encode()).hexdigest()
class RNG:
    """Namespaced deterministic streams prevent subsystem ordering from perturbing unrelated randomness."""
    def __init__(self,seed): self.seed=seed
    def stream(self,namespace,year=0,entity=0):
        h=hashlib.blake2b(f"{self.seed}|{namespace}|{year}|{entity}".encode(),digest_size=8).digest(); return random.Random(int.from_bytes(h,"big"))
