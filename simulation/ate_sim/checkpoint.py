from __future__ import annotations
import copy,hashlib,pickle
from dataclasses import dataclass,fields,is_dataclass

# Schema 8 adds explicit health/cohort truth and rebuildable runtime indexes.
# Legacy worlds with incompatible magical histories are intentionally rejected.
CHECKPOINT_SCHEMA=8

@dataclass
class Checkpoint:
    schema:int
    year:int
    seed:int
    digest:str
    world:object


def _strip_runtime(value,seen=None):
    """Remove derived underscore state from a detached checkpoint clone."""
    if seen is None:seen=set()
    oid=id(value)
    if oid in seen:return
    if value is None or isinstance(value,(str,int,float,bool,bytes)):return
    seen.add(oid)
    d=getattr(value,'__dict__',None)
    if d is not None:
        for key in tuple(d):
            if key.startswith('_'):d.pop(key,None)
        for child in tuple(d.values()):_strip_runtime(child,seen)
    if isinstance(value,dict):
        for k,v in value.items():_strip_runtime(k,seen);_strip_runtime(v,seen)
    elif isinstance(value,(list,tuple,set,frozenset)):
        for child in value:_strip_runtime(child,seen)
    elif is_dataclass(value):
        for f in fields(value):_strip_runtime(getattr(value,f.name),seen)


def dumps(world)->bytes:
    digest=world.digest();snapshot=copy.deepcopy(world);_strip_runtime(snapshot)
    if snapshot.digest()!=digest:raise ValueError('runtime cache stripping changed canonical world state')
    cp=Checkpoint(CHECKPOINT_SCHEMA,snapshot.year,snapshot.seed,digest,snapshot)
    return pickle.dumps(cp,protocol=pickle.HIGHEST_PROTOCOL)


def loads(data:bytes):
    cp=pickle.loads(data)
    if not isinstance(cp,Checkpoint):raise ValueError('not an ATE checkpoint')
    if cp.schema!=CHECKPOINT_SCHEMA:raise ValueError(f'checkpoint schema {cp.schema} is not supported by {CHECKPOINT_SCHEMA}')
    if cp.world.year!=cp.year or cp.world.seed!=cp.seed:raise ValueError('checkpoint metadata mismatch')
    _strip_runtime(cp.world)
    if cp.world.digest()!=cp.digest:raise ValueError('checkpoint integrity failure')
    return cp.world


def save(world,path):
    data=dumps(world);open(path,'wb').write(data);return hashlib.sha256(data).hexdigest()


def load(path):
    with open(path,'rb') as f:return loads(f.read())
