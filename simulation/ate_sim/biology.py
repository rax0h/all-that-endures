from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from .rank import profile, annual_mortality, military_value
from .species import species, compose_biology, reproductive_compatibility, reproductive_span, inherit_species

@dataclass(frozen=True)
class BiologyState:
    species:str
    rank:int
    stature:float
    mass:float
    food_need:float
    spirit_need:float
    sleep_need:float
    respiration_need:float
    endurance:float
    strength:float
    heat_tolerance:float
    cold_tolerance:float
    aquatic:float
    perception:float
    magical_affinity:float
    magical_body:float
    built_scale:float

def state(person)->BiologyState:
    # Cache by immutable rule profiles as well as identity, so rule replacement
    # and rank/species changes cannot return a stale biological composition.
    return _state(person.species,person.rank,species(person.species),profile(person.rank))

@lru_cache(maxsize=512)
def _state(species_key,rank,species_profile,rank_profile):
    values=compose_biology(species_key,rank_profile)
    return BiologyState(species_key,rank,**values)

def mortality_risk(person,scarcity:float=0.,trauma:float=0.)->float:
    return annual_mortality(person.age,person.rank,scarcity,trauma)/max(.4,species(person.species).baseline_longevity)

def reproductive_window(person)->bool:
    return 18<=person.age<=18+int(reproductive_span(person.species))

def pair_reproductive_opportunity(a,b)->float:
    # Do not pre-discount today's reproductive opportunity because a long-lived
    # species might have more opportunities decades from now. Scarcity, death,
    # migration and partnership loss can prevent those hypothetical future
    # years from ever being realized; doing so created a systematic extinction
    # pressure on long-lived populations. Lifetime fertility now emerges from
    # actual survived reproductive years and household circumstances.
    fertility=(species(a.species).fertility+species(b.species).fertility)/2
    return fertility*reproductive_compatibility(a.species,b.species)

def child_species(a,b,rng)->str:
    return inherit_species(a.species,b.species,rng)

def combat_value(person)->float:
    b=state(person)
    return military_value(person.rank,health=person.health)*b.strength

def injury_resilience(person)->float:
    return profile(person.rank).injury_resilience*state(person).endurance
