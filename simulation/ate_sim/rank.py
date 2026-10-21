from __future__ import annotations
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class RankProfile:
    rank:int; name:str; aging_rate:float; adult_mortality:float; senescence_start:int|None
    food_need:float; spirit_need:float; sleep_need:float; respiration_need:float
    disease_resistance:float; healing:float; injury_resilience:float; physical_capacity:float
    travel_capacity:float; perception:float; cognitive_capacity:float; magical_body:float
    social_presence:float; economic_capacity:float; military_capacity:float

# Provisional mechanical profiles. Exact named-rank thresholds remain canon-configurable.
# Rank is capability/ontology, never guaranteed wealth, wisdom, fame, dynasty or political power.
PROFILES={
0:RankProfile(0,"ordinary",1.0,0.0030,65,1.00,0.00,1.00,1.00,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.00,1.0,1.0,1.0),
1:RankProfile(1,"rank-1",0.72,0.0019,92,0.92,0.03,0.90,0.92,1.4,1.5,1.35,1.30,1.25,1.25,1.08,0.12,1.15,1.18,1.35),
2:RankProfile(2,"rank-2",0.42,0.0009,150,0.72,0.12,0.72,0.72,2.3,2.4,2.00,1.75,1.70,1.65,1.18,0.30,1.35,1.42,2.00),
3:RankProfile(3,"rank-3",0.18,0.00032,300,0.42,0.32,0.48,0.45,4.2,4.4,3.30,2.60,2.55,2.50,1.32,0.58,1.70,1.85,3.40),
4:RankProfile(4,"rank-4",0.05,0.00008,None,0.12,0.68,0.20,0.12,8.0,8.5,6.20,4.60,4.80,4.70,1.50,0.86,2.25,2.55,6.50),
}

# ATE numerical profiles, not book measurements. Lifespan changes rescale
# physical age (including rejuvenation); ordinary species mortality still applies.
for _rank,_name,_aging,_force in (
 (1,'iron',.72,4.),(2,'bronze',.48,20.),(3,'silver',.27,100.),
 (4,'gold',.16,1000.)):
    PROFILES[_rank]=replace(PROFILES[_rank],name=_name,aging_rate=_aging,
        senescence_start=65,physical_capacity=_force,military_capacity=_force)
PROFILES[4]=replace(PROFILES[4],respiration_need=0.,magical_body=.98)
PROFILES[5]=replace(PROFILES[4],rank=5,name='diamond',aging_rate=0.,
    adult_mortality=0.,senescence_start=None,food_need=.02,spirit_need=1.,
    sleep_need=.02,respiration_need=0.,disease_resistance=100.,healing=100.,
    injury_resilience=100.,physical_capacity=10000.,travel_capacity=100.,
    perception=200.,cognitive_capacity=200.,magical_body=1.,
    social_presence=4.,economic_capacity=10.,military_capacity=10000.)

@dataclass(frozen=True)
class CognitiveCapacity:
    attention:float
    sensory_integration:float
    magical_modeling:float

COGNITION=(CognitiveCapacity(1.,1.,1.),CognitiveCapacity(1.2,1.5,2.),
    CognitiveCapacity(2.,3.,5.),CognitiveCapacity(5.,10.,20.),
    CognitiveCapacity(20.,50.,100.),CognitiveCapacity(100.,200.,1000.))

def cognition(rank):return COGNITION[max(0,min(5,int(rank)))]

def profile(rank:int)->RankProfile:
    return PROFILES[max(min(int(rank),max(PROFILES)),min(PROFILES))]

def biological_age(chronological_age:int, rank:int)->float:
    return chronological_age*profile(rank).aging_rate

def annual_mortality(age:int, rank:int, scarcity:float=0.0, trauma:float=0.0)->float:
    p=profile(rank); bio=biological_age(age,rank)
    sen=0.0 if p.senescence_start is None else max(0.0,bio-p.senescence_start)*0.006
    environmental=(0.025*scarcity+0.012*trauma)/max(1.0,p.injury_resilience)
    return min(.95,p.adult_mortality+sen+environmental)

def sustenance(rank:int)->dict[str,float]:
    p=profile(rank); return {"food":p.food_need,"spirit":p.spirit_need,"sleep":p.sleep_need,"respiration":p.respiration_need}

def effective_capacity(rank:int, skill:float=1.0, health:float=1.0)->float:
    p=profile(rank); return p.physical_capacity*max(.05,skill)*max(.05,health)

def opportunity_multiplier(rank:int)->float:
    return profile(rank).economic_capacity

def social_signal(rank:int)->float:
    return profile(rank).social_presence

def military_value(rank:int, skill:float=1.0, health:float=1.0)->float:
    p=profile(rank); return p.military_capacity*max(.05,skill)*max(.05,health)

def appearance_state(rank:int)->dict[str,float|str]:
    p=profile(rank)
    return {"rank":p.name,"magical_body":p.magical_body,"healing":p.healing,"physical_capacity":p.physical_capacity}
