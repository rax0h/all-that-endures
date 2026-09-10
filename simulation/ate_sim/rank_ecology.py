from __future__ import annotations

from .core import Layer, Ref

# Advancement is earned through lived use, not passive annual XP.  A person's
# work, preparation, study, danger and reflection determine which parts of a
# completed path actually receive practice.
_ACTION_FUNCTIONS={
    'secure_food':{'creation','control','support','detection','recovery'},
    'prepare':{'enhancement','control','movement','detection','recovery'},
    'work':{'creation','enhancement','control','support','exchange'},
    'socialize':{'influence','support','detection','exchange'},
    'learn':{'detection','control','transformation','support'},
    'teach':{'influence','support','control','exchange'},
    'build':{'creation','enhancement','control','transformation'},
}

def _latest_action(world,pid):
    for rec in reversed(world.agency.actions):
        if rec.person==pid and rec.year==world.year:return rec
    return None

def rank_ecology_step(world,rng):
    for p in sorted((x for x in world.people.values() if x.alive),key=lambda x:x.id):
        path=world.advancement.path(p.id)
        if path is None or not path.abilities:continue
        rec=_latest_action(world,p.id);action='work' if rec is None else rec.action;strength=.35 if rec is None else rec.strength
        relevant=_ACTION_FUNCTIONS.get(action,set())
        rr=rng.stream('rank_ecology',world.year,p.id)
        # Practice several abilities that could actually have contributed to the
        # year's life. Full paths therefore progress only if the person develops
        # breadth instead of grinding one convenient power.
        candidates=[(i,a) for i,a in enumerate(path.abilities) if a.function in relevant]
        if not candidates:candidates=list(enumerate(path.abilities))
        rr.shuffle(candidates);uses=max(1,min(len(candidates),2+int(3*strength)))
        before=world.advancement.rank(p.id)
        for i,a in candidates[:uses]:
            meaningful=(.10+.22*strength)*(.75+.5*p.curiosity)
            reflection=(.25+.75*p.curiosity) if action in ('learn','teach','socialize') else .08*p.curiosity
            world.advancement.practice(p.id,i,meaningful,reflection)
        after=world.advancement.rank(p.id)
        if after>before:
            p.rank=after
            world.emit('rank_advanced',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),from_rank=before,to_rank=after,practice_context=action)
