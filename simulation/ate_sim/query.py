from .core import World

def causal_chain(world:World,event_id:int):
    by={e.id:e for e in world.events}; seen=set(); out=[]
    def visit(i):
        if i in seen or i not in by:return
        seen.add(i)
        for c in by[i].causes: visit(c)
        out.append(i)
    visit(event_id); return out

def present_summary(w): return {"seed":w.seed,"year":w.year,"people_alive":sum(p.alive for p in w.people.values()),"settlements":len(w.settlements),"events":len(w.events),"digest":w.digest()}
