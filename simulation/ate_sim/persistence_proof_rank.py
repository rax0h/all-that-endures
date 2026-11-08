"""Rank-ordered minimum projection, separate from ordinal query membership."""
from dataclasses import dataclass
from .incremental_store import StoreIntegrityError,StoreError
from .persistence_proof_nodes import _digest
from .persistence_proof_content import _namespace,_integer

MAX_FIELD_BYTES=4096
_INDEX='CREATE INDEX ate_rank_query_closed ON lazy_query_versions(namespace,index_name,valid_to,index_value,ordinal,record_key) WHERE valid_to IS NOT NULL'


@dataclass(frozen=True)
class RankScope:
    namespace:str
    index_name:str


def ranked(namespace,name):
    return name.startswith('minimum/v1/')


def index(store,*,create=False):
    if create:store.db.execute(_INDEX.replace('CREATE INDEX','CREATE INDEX IF NOT EXISTS',1))
    row=store.db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name='ate_rank_query_closed' AND type='index'").fetchone()
    if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(_INDEX.lower().split()):
        raise StoreError('rank index requires verified construction')


def seek_domain(identity,codec,scope):
    if type(scope) is not RankScope:raise StoreIntegrityError('invalid rank scope')
    return _digest(b'ate-rank-seek-domain/1',_namespace(identity),_integer(codec,1),
        _namespace(scope.namespace),_namespace(scope.index_name))


def position(rank,ordinal,typed):
    if type(rank) is not bytes or type(typed) is not bytes or type(ordinal) is not int or not 0<=ordinal<2**63:
        raise StoreIntegrityError('invalid rank position')
    if max(len(rank),len(typed))>MAX_FIELD_BYTES:raise StoreError('rank position exceeds field budget')
    return rank.replace(b'\0',b'\0\xff')+b'\0\0'+ordinal.to_bytes(8,'big')+typed


def parse_position(raw):
    if type(raw) is not bytes or len(raw)>3*MAX_FIELD_BYTES+10:raise StoreIntegrityError('invalid rank position bytes')
    rank=bytearray();offset=0
    while offset<len(raw):
        byte=raw[offset];offset+=1
        if byte:
            rank.append(byte)
        else:
            if offset==len(raw):raise StoreIntegrityError('truncated rank position escape')
            escaped=raw[offset];offset+=1
            if escaped==0:break
            if escaped!=255:raise StoreIntegrityError('invalid rank position escape')
            rank.append(0)
        if len(rank)>MAX_FIELD_BYTES:raise StoreError('rank field exceeds budget')
    else:raise StoreIntegrityError('rank position lacks terminator')
    if offset+8>len(raw):raise StoreIntegrityError('rank position lacks ordinal')
    value=bytes(rank),int.from_bytes(raw[offset:offset+8],'big'),raw[offset+8:]
    if position(*value)!=raw:raise StoreIntegrityError('noncanonical rank position')
    return value


def member(domain,rank,ordinal,typed):
    return _digest(b'ate-rank-member/1',domain,position(rank,ordinal,typed))
