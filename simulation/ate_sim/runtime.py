"""Rebuildable hot-state views for the simulation engine.

RuntimeView is deliberately outside canonical World state.  It is a derived index over authoritative
objects and may be discarded/rebuilt without changing history, determinism, checkpoints or digests.
"""
from __future__ import annotations

class RuntimeView:
    __slots__=("world","epoch","living","alive_ids","by_settlement","adults16_by_settlement",
               "adults18_by_settlement","dependents","living_household_ids")
    def __init__(self,world,epoch):
        self.world=world;self.epoch=epoch
        living=tuple(p for p in world.people.values() if p.alive)
        self.living=living
        self.alive_ids={p.id for p in living}
        by={sid:[] for sid in world.settlements}
        a16={sid:[] for sid in world.settlements}
        a18={sid:[] for sid in world.settlements}
        dependents={}
        households=set()
        for p in living:
            by.setdefault(p.settlement,[]).append(p)
            households.add(p.household)
            if p.age>=16:a16.setdefault(p.settlement,[]).append(p)
            if p.age>=18:a18.setdefault(p.settlement,[]).append(p)
            if p.age<18:
                for parent in p.parents:dependents[parent]=dependents.get(parent,0)+1
        self.by_settlement={sid:tuple(v) for sid,v in by.items()}
        self.adults16_by_settlement={sid:tuple(v) for sid,v in a16.items()}
        self.adults18_by_settlement={sid:tuple(v) for sid,v in a18.items()}
        self.dependents=dependents
        self.living_household_ids=households
