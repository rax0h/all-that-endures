"""Stable-ID order statistics for an incrementally changing active inventory.

Fenwick counts select the kth live ID in O(log n), without copying/sorting the
stockpile for each purchase. IDs arrive monotonically. Exhausted slots compact
amortized, and this entirely derived structure can always be rebuilt.
"""
from collections.abc import Sequence


class SelectionPool(Sequence):
    def __init__(self, ids=()):
        self._ids=[]
        self._positions={}
        self._counts=[0]
        for key in sorted(ids):self.add(key)

    def __len__(self):return len(self._positions)

    def _prefix(self, pos):
        count=0
        while pos:
            count+=self._counts[pos];pos-=pos & -pos
        return count

    def add(self, key):
        if key in self._positions:return
        if self._ids and key<=self._ids[-1]:
            raise ValueError('material IDs must increase; rebuild after data repair')
        pos=len(self._ids)+1
        self._ids.append(key);self._positions[key]=pos
        self._counts.append(1+self._prefix(pos-1)-self._prefix(pos-(pos & -pos)))

    def discard(self,key):
        pos=self._positions.pop(key,None)
        if pos is None:return
        while pos<len(self._counts):
            self._counts[pos]-=1;pos+=pos & -pos
        if len(self._ids)>1024 and len(self)*2<len(self._ids):
            self.__init__(self._positions)

    def __getitem__(self,index):
        if isinstance(index,slice):return list(self)[index]
        if index<0:index+=len(self)
        if index<0 or index>=len(self):raise IndexError(index)
        pos=0;step=1 << (len(self._ids).bit_length()-1)
        while step:
            candidate=pos+step
            if candidate<len(self._counts) and self._counts[candidate]<=index:
                index-=self._counts[candidate];pos=candidate
            step>>=1
        return self._ids[pos]

    def __iter__(self):
        return (key for key in self._ids if key in self._positions)
