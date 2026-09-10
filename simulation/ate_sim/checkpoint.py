from __future__ import annotations
import hashlib,pickle
from dataclasses import dataclass

CHECKPOINT_SCHEMA=2
@dataclass
class Checkpoint:
    schema:int
    year:int
    seed:int
    digest:str
    world:object

def dumps(world)->bytes:
    cp=Checkpoint(CHECKPOINT_SCHEMA,world.year,world.seed,world.digest(),world)
    return pickle.dumps(cp,protocol=pickle.HIGHEST_PROTOCOL)

def loads(data:bytes):
    cp=pickle.loads(data)
    if not isinstance(cp,Checkpoint):raise ValueError('not an ATE checkpoint')
    if cp.schema!=CHECKPOINT_SCHEMA:raise ValueError(f'checkpoint schema {cp.schema} is not supported by {CHECKPOINT_SCHEMA}')
    if cp.world.year!=cp.year or cp.world.seed!=cp.seed:raise ValueError('checkpoint metadata mismatch')
    if cp.world.digest()!=cp.digest:raise ValueError('checkpoint integrity failure')
    return cp.world

def save(world,path):
    data=dumps(world);open(path,'wb').write(data);return hashlib.sha256(data).hexdigest()

def load(path):
    with open(path,'rb') as f:return loads(f.read())
