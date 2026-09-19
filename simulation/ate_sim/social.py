from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Relationship:
    a:int; b:int; familiarity:float=0.; trust:float=.5; attachment:float=0.; obligation:float=0.; resentment:float=0.; attraction:float=0.; shared_history:list[int]=field(default_factory=list)
    def __setattr__(self,name,value):
        if name=='attachment':
            old=getattr(self,'attachment',None);object.__setattr__(self,name,value)
            if old is not None and old!=value:
                graph=getattr(self,'_graph',None)
                if graph is not None:graph.__dict__.setdefault('_attachment_dirty',set()).update((self.a,self.b))
            return
        object.__setattr__(self,name,value)

@dataclass
class SocialGraph:
    edges:dict[tuple[int,int],Relationship]=field(default_factory=dict)
    partnerships:dict[tuple[int,int],int]=field(default_factory=dict)
    adjacency:dict[int,set[int]]=field(default_factory=dict)
    def key(self,a,b): return (min(a,b),max(a,b))
    def _ensure_adjacency_index(self):
        # adjacency is derived from authoritative edges.  Old checkpoints and
        # direct test fixtures may bypass get(), so validate by edge count.
        if getattr(self,'_adjacency_edge_count',-1)!=len(self.edges):
            rebuilt={}
            for a,b in self.edges:
                rebuilt.setdefault(a,set()).add(b);rebuilt.setdefault(b,set()).add(a)
            self.adjacency=rebuilt;self._adjacency_edge_count=len(self.edges)
            self.__dict__.pop('_relationships',None)
    def get(self,a,b):
        k=self.key(a,b)
        if k not in self.edges:
            self.edges[k]=Relationship(*k)
            self.adjacency.setdefault(k[0],set()).add(k[1])
            self.adjacency.setdefault(k[1],set()).add(k[0])
            self._adjacency_edge_count=len(self.edges)
            self.__dict__.setdefault('_attachment_dirty',set()).update(k)
            cached=self.__dict__.get('_relationships',{})
            for pid,other in ((k[0],k[1]),(k[1],k[0])):
                if pid in cached:cached[pid][other]=self.edges[k]
        relationship=self.edges[k]
        if getattr(relationship,'_graph',None) is not self:object.__setattr__(relationship,'_graph',self)
        return relationship
    def record(self,a,b,event_id,trust=0.,attachment=0.,obligation=0.,resentment=0.):
        r=self.get(a,b); r.familiarity=min(1.,r.familiarity+.03); r.trust=max(0.,min(1.,r.trust+trust)); r.attachment=max(0.,min(1.,r.attachment+attachment)); r.obligation=max(0.,min(1.,r.obligation+obligation)); r.resentment=max(0.,min(1.,r.resentment+resentment)); r.shared_history.append(event_id); return r
    def neighbors(self,pid):
        self._ensure_adjacency_index();return self.adjacency.get(pid,())
    def relationships_for(self,pid):
        # Retain references, not copies of mutable weights. Direct relationship
        # edits remain visible; new edges extend already materialized adjacency.
        self._ensure_adjacency_index()
        if not hasattr(self,'_relationships'):self._relationships={}
        if pid not in self._relationships:
            self._relationships[pid]={other:self.edges[self.key(pid,other)] for other in self.neighbors(pid)}
        return self._relationships[pid].values()
    def max_attachment(self,pid):
        self._ensure_adjacency_index()
        cache=self.__dict__.setdefault('_attachment_max',{});dirty=self.__dict__.setdefault('_attachment_dirty',set())
        if pid not in cache or pid in dirty:
            best=0.
            for other in self.adjacency.get(pid,()):
                relationship=self.edges[self.key(pid,other)]
                if getattr(relationship,'_graph',None) is not self:object.__setattr__(relationship,'_graph',self)
                if relationship.attachment>best:best=relationship.attachment
            cache[pid]=best;dirty.discard(pid)
        return cache.get(pid,0.)
    def partner(self,a,b,event_id):
        key=self.key(a,b);self.partnerships[key]=event_id
        if hasattr(self,'_partnership_index'):
            for pid in key:self._partnership_index.setdefault(pid,set()).add(key)
            self._partnership_count=len(self.partnerships)
    def living_partnerships(self,people):
        # Historical pairs remain authoritative; query through living endpoints.
        # Rebuild on old checkpoints or direct additions/removals to the archive.
        if not hasattr(self,'_partnership_index') or self._partnership_count!=len(self.partnerships):
            self._partnership_index={}
            for key in self.partnerships:
                for pid in key:self._partnership_index.setdefault(pid,set()).add(key)
            self._partnership_count=len(self.partnerships)
        living={p.id for p in people if p.alive};pairs=set()
        for pid in living:
            for key in self._partnership_index.get(pid,()):
                if key[0] in living and key[1] in living:pairs.add(key)
        return {key:self.partnerships[key] for key in pairs}
    def is_partnered(self,a,b): return self.key(a,b) in self.partnerships
