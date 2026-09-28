"""Stream the established canonical JSON bytes without expanding cold history."""
from dataclasses import is_dataclass
from enum import Enum
from json.encoder import encode_basestring
import hashlib
import json
from .event_log import EventLog


def digest(value,canonical,field_names):
    from .core import Event
    def pieces(v):
        t=type(v)
        if v is None:yield 'null'
        elif t is str:yield encode_basestring(v)
        elif t is bool:yield 'true' if v else 'false'
        elif t is int:yield str(v)
        elif t is float:yield json.dumps(v)
        elif isinstance(v,Enum):yield from pieces(v.value)
        elif isinstance(v,Event):
            # One small record at a time; let the C JSON encoder handle its
            # tokens without expanding the entire historical event collection.
            yield json.dumps(canonical(v),sort_keys=True,separators=(',',':'),ensure_ascii=False)
        elif is_dataclass(v):
            yield '{'
            for i,(key,name) in enumerate(field_names(type(v))):
                if i:yield ','
                yield encode_basestring(key);yield ':';yield from pieces(getattr(v,name))
            yield '}'
        elif isinstance(v,dict):
            yield '{'
            for i,key in enumerate(sorted(v,key=repr)):
                if i:yield ','
                yield encode_basestring(repr(key));yield ':';yield from pieces(v[key])
            yield '}'
        elif isinstance(v,(list,tuple,EventLog,set,frozenset)):
            values=sorted(v,key=lambda x:repr(canonical(x))) if isinstance(v,(set,frozenset)) else v
            yield '['
            for i,item in enumerate(values):
                if i:yield ','
                yield from pieces(item)
            yield ']'
        else:raise TypeError(f'unsupported canonical value {t}')
    h=hashlib.sha256();buffer=[];size=0
    for piece in pieces(value):
        buffer.append(piece);size+=len(piece)
        if size>=65536:
            h.update(''.join(buffer).encode());buffer=[];size=0
    h.update(''.join(buffer).encode())
    return h.hexdigest()
