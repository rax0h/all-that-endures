from collections import Counter
from .core import World
from .culture import accommodation

def causal_chain(world:World,event_id:int):
    by={e.id:e for e in world.events};seen=set();out=[]
    def visit(i):
        if i in seen or i not in by:return
        seen.add(i)
        for c in by[i].causes:visit(c)
        out.append(i)
    visit(event_id);return out

def lineage_chain(world:World,kind:str,entity_id:int,depth=16):
    return sorted(world.lineage.ancestors(kind,entity_id,depth))

def reconstruct_cultural_pattern(world:World,sid:int,minimum=.12):
    """Reconstruct a settlement's recognizable pattern without a culture label."""
    practices=[]
    for (place,pid),adoption in world.culture.adoption.items():
        if place!=sid or adoption<minimum:continue
        p=world.culture.practices[pid];practices.append({"id":pid,"domain":p.domain,"name":p.name,"adoption":round(adoption,3),"origin":p.origin_settlement,"parent":p.parent})
    practices.sort(key=lambda x:(x["domain"],-x["adoption"],x["id"]))
    institutions=[{"id":i.id,"kind":i.kind,"founded":i.founded,"legitimacy":round(i.legitimacy,3),"practices":sorted(i.practices)} for i in world.culture.institutions.values() if i.settlement==sid]
    laws=[{"id":l.id,"domain":l.domain,"strictness":round(l.strictness,3),"enforcement":round(l.enforcement,3)} for l in world.culture.laws.values() if l.settlement==sid]
    residents=[p for p in world.people.values() if p.alive and p.settlement==sid];community_weight=Counter()
    for p in residents:
        for cid,v in world.communities.memberships_for(p.id).items():community_weight[cid]+=v
    communities=[{"id":cid,"weight":round(weight,2),"origin":world.communities.communities[cid].origin_settlement,"founded":world.communities.communities[cid].founded} for cid,weight in community_weight.most_common(8)]
    expertise=Counter()
    for p in residents:
        for (pid,domain),skill in world.skills.skills.items():
            if pid==p.id:expertise[domain]+=skill.level
    expertise={k:round(v/max(1,len(residents)),3) for k,v in sorted(expertise.items())}
    infrastructure=[{"id":a.id,"kind":a.kind,"condition":round(a.condition,3),"capacity":round(a.capacity,2),"built":a.built,"settlements":a.settlements} for a in world.infrastructure.assets.values() if sid in a.settlements]
    return {"settlement":sid,"practices":practices,"institutions":institutions,"laws":laws,"communities":communities,"expertise":expertise,"infrastructure":infrastructure,"accommodation":accommodation(world,sid)}

def present_summary(w):return {"seed":w.seed,"year":w.year,"people_alive":sum(p.alive for p in w.people.values()),"settlements":len(w.settlements),"events":len(w.events),"communities":len(w.communities.communities),"transmissions":len(w.transmission.records),"lineage_nodes":len(w.lineage.nodes),"skills":len(w.skills.skills),"infrastructure":len(w.infrastructure.assets),"digest":w.digest()}
