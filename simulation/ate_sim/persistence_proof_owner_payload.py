"""Private inert World-schema payload projection; never mutable native records.

Only selected typed storage references are certified, not inline mutable alias
identity or namespace-specific field domains. Unsupported key/set routes reject.
"""
from dataclasses import dataclass
from .incremental_store import StoreError, StoreIntegrityError, CodecError
from .persistence_proof_projection import _ProjectionCodec, ProjectionProofBudgetError
from .persistence_schema import RECORD_FIELDS
from .persistence_nonreflexive_keys import stored_immutable_key
from .persistence_lazy_nested_history import HistoryReference
from .persistence_record_headers import RecordReference
from .persistence_nonreflexive_keys import NonreflexiveKeyReference
from .persistence_event_id_reference import EventIdReference
from .core import Ref

_RECORD_NAMES = {f'{cls.__module__.split(".")[-1]}.{cls.__name__}/v1': names for cls,names in RECORD_FIELDS.items()}
_REFERENCES = (HistoryReference, RecordReference, NonreflexiveKeyReference, EventIdReference)


@dataclass(frozen=True)
class _Record:
    name: str
    fields: tuple
    event_state: tuple | None = None


class _OwnerCodec(_ProjectionCodec):
    def __init__(self):super().__init__(metadata=True)

    def _decode_value(self,node):
        if type(node) is list and node and type(node[0]) is str:
            tag=node[0]
            if tag=='record' and len(node)==3 and node[1]!='core.Ref/v1':
                if type(node[1]) is not str or node[1] not in _RECORD_NAMES or type(node[2]) is not list:
                    raise CodecError('undeclared owner record schema')
                pairs=node[2]
                if (any(type(p) is not list or len(p)!=2 or type(p[0]) is not str for p in pairs)
                        or tuple(p[0] for p in pairs)!=_RECORD_NAMES[node[1]]):
                    raise CodecError('owner record field schema disagreement')
                return _Record(node[1],tuple((name,self._decode_value(value)) for name,value in pairs))
            if tag=='ate_event/v1':
                if len(node)!=4 or type(node[1]) is not bool or type(node[2]) is not bool or not node[1] and node[2]:
                    raise CodecError('invalid owner event envelope')
                value=self._decode_value(node[3])
                if type(value) is not _Record or value.name!='core.Event/v1':raise CodecError('event envelope has wrong record')
                return _Record(value.name,value.fields,(node[1],node[2]))
            if tag in ('ate_frozen_list/v1','ate_frozen_dict/v1'):
                if len(node)!=2 or type(node[1]) is not list:raise CodecError('invalid owner frozen container')
                if tag=='ate_frozen_list/v1':return tuple(self._decode_value(v) for v in node[1])
                node=['dict',node[1]]
        value=super()._decode_value(node)
        if type(value) is dict and any(not stored_immutable_key(k) for k in value):
            raise CodecError('owner dictionary key is not a closed immutable value')
        return value


def world_target_paths(payload,kind,incarnation,*,max_members=4096,charge=None):
    """Return all exact paths to one typed target in a closed World owner body."""
    from .persistence_proof_target import _reference
    try:
        codec=_OwnerCodec();value=codec.decode(payload);found=[]
        def visit(item,path,unsupported=False):
            if type(item) in _REFERENCES:
                actual,inc=_reference(item)
                if inc==incarnation:
                    if unsupported:raise StoreError('selected reference uses unsupported inline key/set route')
                    if actual!=kind:raise StoreIntegrityError('incoming owner reference kind disagrees with target')
                    encoded=codec.encode(path)
                    if len(encoded)>4096:raise ProjectionProofBudgetError('incoming owner path exceeds bounded field')
                    if charge is not None:charge(len(encoded)+8)
                    found.append(encoded)
                    if len(found)>max_members:raise ProjectionProofBudgetError('incoming payload projection exceeds member budget')
            elif type(item) is _Record:
                for name,child in item.fields:visit(child,path+(('field',name),),unsupported)
            elif type(item) is Ref:
                visit(item.kind,path+(('field','kind'),),unsupported);visit(item.id,path+(('field','id'),),unsupported)
            elif type(item) is dict:
                for key,child in item.items():
                    visit(key,path,True);visit(child,path+(('key',key),),unsupported)
            elif type(item) in (tuple,list):
                for offset,child in enumerate(item):visit(child,path+(('index',offset),),unsupported)
            elif type(item) in (set,frozenset):
                for child in item:visit(child,path,True)
        visit(value,())
        if len(set(found))!=len(found):raise StoreIntegrityError('duplicate incoming payload reference path')
        return tuple(sorted(found))
    except (CodecError, ValueError, TypeError, UnicodeError, RecursionError, IndexError, AttributeError) as exc:
        raise StoreIntegrityError('invalid closed owner payload') from exc
