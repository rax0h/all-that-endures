"""Append-only objective events with lossless cold segments and bounded reads.

Cold bytes are owned by the world/checkpoint or the opt-in persistence store, not
an external cache or a second source of truth. Index positions, IDs, fields and
chronology never change.
"""
from bisect import bisect_left, bisect_right
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
import pickle
import struct
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


def _typed_value_token(value):
    """Lossless value token matching persistence's typed-value semantics."""
    cls=type(value)
    if value is None:return ('none',)
    if cls is bool:return ('bool',value)
    if cls is int:return ('int',value)
    if cls is float:return ('float64',struct.pack('>d',value))
    if cls is str:return ('str',value)
    if cls is bytes:return ('bytes',value)
    if isinstance(value,Enum):return ('enum',cls,value.name)
    if is_dataclass(value):
        return ('record',cls,tuple(
            (field.name,_typed_value_token(getattr(value,field.name)))
            for field in fields(value)
        ))
    if isinstance(value,dict):
        return ('mapping',cls,tuple(
            (_typed_value_token(key),_typed_value_token(child))
            for key,child in value.items()
        ))
    if isinstance(value,(list,tuple)):
        return ('sequence',cls,tuple(_typed_value_token(child) for child in value))
    if isinstance(value,(set,frozenset)):
        items=[_typed_value_token(child) for child in value]
        items.sort(key=repr)
        return ('set',cls,tuple(items))
    raise TypeError(f'unsupported persisted event value: {cls.__name__}')


class EventLog(Sequence):
    """One logical event sequence with an optional immutable disk prefix.

    In legacy/in-memory mode, _chunks are the ordinary compressed sealed prefix.
    With a disk prefix installed, committed history lives only in that reader,
    _chunks contain pending sealed suffix chunks, and _tail contains live events.
    The year index contains only resident suffix years; it never mirrors disk
    history.
    """
    chunk_size=2048
    cache_size=4

    def __init__(self,events=(),*,disk_prefix=None,pending_sealed_events=0):
        if type(pending_sealed_events) is not int or pending_sealed_events<0:
            raise ValueError('pending_sealed_events must be a nonnegative int')
        if pending_sealed_events%self.chunk_size:
            raise ValueError('pending sealed history requires complete chunks')
        self._disk_prefix=disk_prefix
        self._disk_count=0
        self._chunks=[];self._tail=[];self._count=0
        self._years=[];self._offsets=[];self._cache=OrderedDict()
        self._last_year=None
        if disk_prefix is not None:
            self._disk_count=self._checked_prefix_count(disk_prefix)
            self._count=self._disk_count
            self._last_year=disk_prefix.last_year
        for event in events:self.append(event)
        if pending_sealed_events:
            if pending_sealed_events>len(self._tail):
                raise ValueError('pending sealed history exceeds supplied suffix')
            self._pack_existing_pending(pending_sealed_events)

    @classmethod
    def from_disk_prefix(cls,prefix,suffix=(),*,pending_sealed_events=0):
        """Construct the opt-in three-range form without reading cold payloads."""
        return cls(suffix,disk_prefix=prefix,pending_sealed_events=pending_sealed_events)

    def _checked_prefix_count(self,prefix):
        count=len(prefix)
        if count%self.chunk_size:
            raise ValueError('disk prefix must contain complete EventLog chunks')
        segments=prefix.segment_count
        if segments*self.chunk_size!=count:
            raise ValueError('disk prefix segment/event count mismatch')
        last_year=prefix.last_year
        if count==0 and last_year is not None:
            raise ValueError('empty disk prefix has a last year')
        if count and type(last_year) is not int:
            raise ValueError('non-empty disk prefix requires an integer last year')
        return count

    def _ensure_backend_readable(self):
        if self._disk_prefix is not None:
            count=len(self._disk_prefix)
            if count!=self._disk_count:
                raise RuntimeError('disk EventLog prefix changed after capture')

    def __len__(self):
        self._ensure_backend_readable()
        return self._count

    def __eq__(self,other):
        if not isinstance(other,Sequence):return NotImplemented
        return len(self)==len(other) and all(a==b for a,b in zip(self,other))

    @property
    def disk_event_count(self):
        self._ensure_backend_readable()
        return self._disk_count

    @property
    def pending_sealed_event_count(self):
        self._ensure_backend_readable()
        return len(self._chunks)*self.chunk_size

    @property
    def tail_event_count(self):
        self._ensure_backend_readable()
        return len(self._tail)

    def _mutable_identity_start(self):
        """Absolute index of the resident live tail without touching cold payloads."""
        self._ensure_backend_readable()
        return self._disk_count+len(self._chunks)*self.chunk_size

    def _iter_mutable_identity_events(self):
        """Yield absolute-index mutable tail Events only; never decode sealed history."""
        start=self._mutable_identity_start()
        for local,event in enumerate(self._tail):
            self._ensure_backend_readable()
            if event.__dict__.get('_sealed') is not True:
                yield start+local,event

    def _mutable_identity_event_at(self,index):
        """Resolve only a mutable tail identity path, without reading older ranges."""
        self._ensure_backend_readable()
        if type(index) is not int:
            raise IndexError(index)
        start=self._disk_count+len(self._chunks)*self.chunk_size
        local=index-start
        if local<0 or local>=len(self._tail):
            raise IndexError(index)
        event=self._tail[local]
        if event.__dict__.get('_sealed') is True:
            raise IndexError(index)
        return event

    def append(self,event):
        self._ensure_backend_readable()
        if event.id!=self._count+1:raise ValueError('events require consecutive stable IDs')
        if self._last_year is not None and event.year<self._last_year:
            raise ValueError('event time cannot run backwards')
        if not self._years or event.year!=self._years[-1]:
            self._years.append(event.year);self._offsets.append(self._count)
        self._tail.append(event);self._count+=1;self._last_year=event.year

    def _chunk(self,number):
        """Decode one resident sealed chunk; disk chunks are read by their reader."""
        cache=self._cache
        if number<0 or number>=len(self._chunks):raise IndexError(number)
        if number not in cache:
            cache[number]=pickle.loads(zlib.decompress(self._chunks[number]))
            if len(cache)>self.cache_size:cache.popitem(last=False)
        cache.move_to_end(number)
        return cache[number]

    def __getitem__(self,index):
        self._ensure_backend_readable()
        if isinstance(index,slice):
            start,stop,step=index.indices(self._count)
            return [self[i] for i in range(start,stop,step)]
        if index<0:index+=self._count
        if index<0 or index>=self._count:raise IndexError(index)
        if index<self._disk_count:return self._disk_prefix[index]
        local=index-self._disk_count
        pending=len(self._chunks)*self.chunk_size
        if local<pending:
            number,offset=divmod(local,self.chunk_size)
            return self._chunk(number)[offset]
        return self._tail[local-pending]

    def __iter__(self):
        self._ensure_backend_readable()
        if self._disk_prefix is not None:yield from self._disk_prefix
        for number in range(len(self._chunks)):
            for event in self._chunk(number):
                self._ensure_backend_readable()
                yield event
        for event in self._tail:
            self._ensure_backend_readable()
            yield event

    def between(self,first,last):
        self._ensure_backend_readable()
        if last<first:return []
        out=[]
        if self._disk_prefix is not None and self._disk_count:
            disk_last=self._disk_prefix.last_year
            if first<=disk_last:out.extend(self._disk_prefix.between(first,last))
        left=bisect_left(self._years,first);right=bisect_right(self._years,last)
        start=self._offsets[left] if left<len(self._offsets) else self._count
        stop=self._offsets[right] if right<len(self._offsets) else self._count
        if start<stop:out.extend(self[start:stop])
        return out

    def seal_before(self,year):
        self._ensure_backend_readable()
        while len(self._tail)>=self.chunk_size and self._tail[self.chunk_size-1].year<year:
            chunk=self._tail[:self.chunk_size]
            for event in chunk:event.seal()
            self._chunks.append(zlib.compress(pickle.dumps(chunk,protocol=5),level=1))
            del self._tail[:self.chunk_size]

    def _pack_existing_pending(self,count):
        """Compress already-sealed leading suffix chunks without freezing them."""
        chunks=count//self.chunk_size
        for number in range(chunks):
            start=number*self.chunk_size
            chunk=self._tail[start:start+self.chunk_size]
            if len(chunk)!=self.chunk_size:
                raise ValueError('pending sealed history requires complete chunks')
            if any(event.__dict__.get('_sealed') is not True for event in chunk):
                raise ValueError('pending sealed history must already be frozen')
            self._chunks.append(zlib.compress(pickle.dumps(chunk,protocol=5),level=1))
        del self._tail[:count]

    def _pruned_suffix_year_index(self,new_disk_count,first_remaining_year):
        pairs=[(year,offset) for year,offset in zip(self._years,self._offsets)
               if offset>=new_disk_count]
        if first_remaining_year is None:return [],[]
        if not pairs or pairs[0][1]>new_disk_count:
            pairs.insert(0,(first_remaining_year,new_disk_count))
        elif pairs[0][1]!=new_disk_count or pairs[0][0]!=first_remaining_year:
            raise ValueError('suffix year boundary disagrees with replacement prefix')
        return [p[0] for p in pairs],[p[1] for p in pairs]

    def _adopt_committed_prefix(self,new_prefix,*,transferred_events):
        """Install a confirmed enlarged prefix and retire exactly its source chunks.

        This performs no commit. A caller invokes it only after publication. All
        validation finishes before pending chunks are discarded. The returned old
        reader remains caller-owned.
        """
        self._ensure_backend_readable()
        if self._disk_prefix is None:
            raise ValueError('prefix adoption requires an existing disk prefix')
        if type(transferred_events) is not int or transferred_events<0:
            raise ValueError('transferred_events must be a nonnegative int')
        if transferred_events%self.chunk_size:raise ValueError('transfers require complete chunks')
        chunks=transferred_events//self.chunk_size
        if chunks>4:raise ValueError('transfer exceeds bounded four-chunk adoption window')
        pending=len(self._chunks)*self.chunk_size
        if transferred_events>pending:raise ValueError('transfer exceeds pending sealed history')
        if not self._disk_prefix._shares_store_authority(new_prefix):
            raise ValueError('replacement prefix belongs to an unrelated store')
        if new_prefix.captured_generation<self._disk_prefix.captured_generation:
            raise ValueError('replacement prefix captured generation regressed')
        new_count=self._checked_prefix_count(new_prefix)
        expected_count=self._disk_count+transferred_events
        if new_count!=expected_count:
            raise ValueError('replacement prefix boundary does not match transfer')

        if transferred_events:
            first_chunk=pickle.loads(zlib.decompress(self._chunks[0]))
            last_chunk=pickle.loads(zlib.decompress(self._chunks[chunks-1]))
            first=first_chunk[0];last=last_chunk[-1]
            if first.id!=self._disk_count+1 or last.id!=expected_count:
                raise ValueError('pending source IDs disagree with replacement boundary')
            if new_prefix.last_year!=last.year:
                raise ValueError('replacement prefix year disagrees with pending source')
            first_ordinal=self._disk_count//self.chunk_size
            for local_ordinal in range(chunks):
                source=pickle.loads(zlib.decompress(self._chunks[local_ordinal]))
                replacement=new_prefix._read_segment_from_store(
                    first_ordinal+local_ordinal
                )
                if len(source)!=len(replacement) or any(
                    type(a) is not type(b)
                    or _typed_value_token(vars(a))!=_typed_value_token(vars(b))
                    for a,b in zip(source,replacement)
                ):
                    raise ValueError(
                        'replacement prefix values disagree with pending source'
                    )
        else:
            old_year=self._disk_prefix.last_year
            if new_prefix.last_year!=old_year:
                raise ValueError('replacement prefix changed without a transfer')

        remaining=self._count-new_count
        first_remaining_year=self[new_count].year if remaining else None
        years,offsets=self._pruned_suffix_year_index(new_count,first_remaining_year)

        old_prefix=self._disk_prefix
        self._disk_prefix=new_prefix;self._disk_count=new_count
        if chunks:
            del self._chunks[:chunks]
            self._cache.clear()
        self._years=years;self._offsets=offsets
        if self._count==0:self._last_year=None
        return old_prefix

    def __getstate__(self):
        return {k:v for k,v in self.__dict__.items() if k!='_cache'}

    def __setstate__(self,state):
        self.__dict__.update(state);self._cache=OrderedDict()
        if '_disk_prefix' not in self.__dict__:self._disk_prefix=None
        if '_disk_count' not in self.__dict__:self._disk_count=0
        if '_last_year' not in self.__dict__:
            self._last_year=self._years[-1] if self._years else None

    def storage_stats(self):
        self._ensure_backend_readable()
        disk_segments=self._disk_count//self.chunk_size
        pending_segments=len(self._chunks)
        disk_cache_segments=self._disk_prefix.resident_segments if self._disk_prefix is not None else 0
        pending_cache_segments=len(self._cache)
        disk_diagnostics=self._disk_prefix.diagnostics() if self._disk_prefix is not None else None
        decoded_cache_events=disk_cache_segments*self.chunk_size+sum(len(v) for v in self._cache.values())
        pending_bytes=sum(map(len,self._chunks))
        return {
            'events':self._count,
            'sealed_events':self._disk_count+pending_segments*self.chunk_size,
            'resident_events':len(self._tail)+decoded_cache_events,
            'cold_bytes':pending_bytes,
            'segments':disk_segments+pending_segments,
            'disk_events':self._disk_count,
            'disk_segments':disk_segments,
            'pending_sealed_events':pending_segments*self.chunk_size,
            'pending_sealed_segments':pending_segments,
            'pending_sealed_bytes':pending_bytes,
            'tail_events':len(self._tail),
            'decoded_cache_segments':disk_cache_segments+pending_cache_segments,
            'decoded_cache_events':decoded_cache_events,
            'disk_cache_segments':disk_cache_segments,
            'pending_cache_segments':pending_cache_segments,
            'disk_segment_reads':disk_diagnostics.segment_reads if disk_diagnostics else 0,
            'disk_segment_read_bytes':disk_diagnostics.segment_read_bytes if disk_diagnostics else 0,
            'resident_compressed_bytes':pending_bytes,
        }
