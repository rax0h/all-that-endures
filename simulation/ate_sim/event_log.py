"""Append-only objective events with lossless cold segments and bounded reads.

Cold bytes are owned by the world/checkpoint, not an external cache or a second
source of truth. Index positions, IDs, fields and chronology never change.
"""
from bisect import bisect_left, bisect_right
from collections import OrderedDict
from collections.abc import Sequence
import pickle
import zlib


def _immutable(*args,**kwargs):raise TypeError('sealed historical events are immutable; append a new cause')


class FrozenDict(dict):
    __setitem__=__delitem__=clear=pop=popitem=setdefault=update=__ior__=_immutable
    def __reduce__(self):return FrozenDict,(dict(self),)


class FrozenList(list):
    __setitem__=__delitem__=append=extend=insert=pop=remove=clear=sort=reverse=__iadd__=__imul__=_immutable
    def __reduce__(self):return FrozenList,(list(self),)


def freeze(value):
    if isinstance(value,dict):return FrozenDict((k,freeze(v)) for k,v in value.items())
    if isinstance(value,list):return FrozenList(freeze(v) for v in value)
    if isinstance(value,tuple):return tuple(freeze(v) for v in value)
    if isinstance(value,set):return frozenset(freeze(v) for v in value)
    return value


class EventLog(Sequence):
    chunk_size=2048
    cache_size=4

    def __init__(self, events=()):
        self._chunks=[];self._tail=[];self._count=0
        self._years=[];self._offsets=[];self._cache=OrderedDict()
        for event in events:self.append(event)

    def __len__(self):return self._count
    def __eq__(self,other):
        if not isinstance(other,Sequence):return NotImplemented
        return len(self)==len(other) and all(a==b for a,b in zip(self,other))

    def append(self,event):
        if event.id!=self._count+1:raise ValueError('events require consecutive stable IDs')
        if self._years and event.year<self._years[-1]:raise ValueError('event time cannot run backwards')
        if not self._years or event.year!=self._years[-1]:
            self._years.append(event.year);self._offsets.append(self._count)
        self._tail.append(event);self._count+=1

    def _chunk(self,number):
        cache=self._cache
        if number not in cache:
            cache[number]=pickle.loads(zlib.decompress(self._chunks[number]))
            if len(cache)>self.cache_size:cache.popitem(last=False)
        cache.move_to_end(number)
        return cache[number]

    def __getitem__(self,index):
        if isinstance(index,slice):
            start,stop,step=index.indices(len(self))
            return [self[i] for i in range(start,stop,step)]
        if index<0:index+=len(self)
        if index<0 or index>=len(self):raise IndexError(index)
        number,offset=divmod(index,self.chunk_size)
        return self._chunk(number)[offset] if number<len(self._chunks) else self._tail[index-len(self._chunks)*self.chunk_size]

    def __iter__(self):
        for number in range(len(self._chunks)):yield from self._chunk(number)
        yield from self._tail

    def between(self,first,last):
        left=bisect_left(self._years,first);right=bisect_right(self._years,last)
        start=self._offsets[left] if left<len(self._offsets) else len(self)
        stop=self._offsets[right] if right<len(self._offsets) else len(self)
        return self[start:stop]

    def seal_before(self,year):
        while len(self._tail)>=self.chunk_size and self._tail[self.chunk_size-1].year<year:
            chunk=self._tail[:self.chunk_size]
            for event in chunk:event.seal()
            self._chunks.append(zlib.compress(pickle.dumps(chunk,protocol=5),level=1))
            del self._tail[:self.chunk_size]

    def __getstate__(self):
        return {k:v for k,v in self.__dict__.items() if k!='_cache'}

    def __setstate__(self,state):self.__dict__.update(state);self._cache=OrderedDict()

    def storage_stats(self):
        return {'events':len(self),'sealed_events':len(self._chunks)*self.chunk_size,
                'resident_events':len(self._tail)+sum(len(v) for v in self._cache.values()),
                'cold_bytes':sum(map(len,self._chunks)),'segments':len(self._chunks)}
