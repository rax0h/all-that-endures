from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class SpeciesProfile:
 key:str; stature:float=1.; mass:float=1.; baseline_longevity:float=1.; fertility:float=1.; endurance:float=1.; strength:float=1.; heat_tolerance:float=1.; cold_tolerance:float=1.; aquatic:float=0.; low_light:float=1.; magical_affinity:float=1.; built_scale:float=1.
SPECIES={"human":SpeciesProfile("human"),"elf":SpeciesProfile("elf",.96,.88,1.35,1.,1.05,.92,1.,1.05,0.,1.25,1.08,.98),"celestine":SpeciesProfile("celestine",1.03,.96,1.12,1.,1.08,1.,1.,1.,0.,1.12,1.28,1.02),"leonid":SpeciesProfile("leonid",1.14,1.28,1.,1.,1.55,1.42,.86,1.2,0.,1.12,1.,1.12),"smoulder":SpeciesProfile("smoulder",1.,1.02,1.,1.,1.08,1.04,2.4,.82,0.,1.05,1.12,1.),"draconian":SpeciesProfile("draconian",1.22,1.55,1.18,1.,1.35,1.55,1.35,1.12,0.,1.1,1.22,1.22),"merfolk":SpeciesProfile("merfolk",1.,1.02,1.,1.,1.08,1.,.95,.92,1.,1.05,1.05,1.08),"runic":SpeciesProfile("runic",magical_affinity=1.15),"outworlder":SpeciesProfile("outworlder")}
def species(key): return SPECIES.get(key,SPECIES["human"])
def reproductive_compatibility(a_key,b_key):
 """Canon-neutral compatibility until explicit interspecies rules are ratified."""
 return 1.0
def reproductive_span(species_key):
 """Current reproductive window scales with lifespan while annual opportunity is normalized elsewhere."""
 return 34.*species(species_key).baseline_longevity
def inherit_species(a_key,b_key,rng):
 """No invented hybrid species: a child takes one parental species."""
 return a_key if a_key==b_key or rng.random()<.5 else b_key
def habitat_suitability(species_key,elevation,moisture,forest):
 """Embodied habitat fit only. This does not encode culture, homeland, or preference."""
 s=species(species_key)
 heat=max(0.,min(1.,.72-.40*elevation-.18*moisture))
 cold=max(0.,min(1.,.10+.72*elevation+.10*(1-moisture)))
 thermal=1/(1+.75*max(0.,heat-s.heat_tolerance/2)+.75*max(0.,cold-s.cold_tolerance/2))
 water=max(0.,min(1.,.68*moisture+.32*(1-elevation)))
 aquatic_fit=(.18+.82*water) if s.aquatic>.5 else 1.0
 forest_fit=.82+.18*forest if s.low_light>1.12 else 1.0
 return max(.05,min(1.25,thermal*aquatic_fit*forest_fit))
def compose_biology(species_key,rank_profile):
 s=species(species_key); r=rank_profile; mundane=max(.08,1-r.magical_body)
 return {"stature":s.stature,"mass":s.mass,"food_need":r.food_need*(.75+.25*s.mass)*mundane+r.food_need*(1-mundane),"spirit_need":r.spirit_need,"sleep_need":r.sleep_need,"respiration_need":r.respiration_need*mundane,"endurance":r.physical_capacity*s.endurance,"strength":r.physical_capacity*s.strength,"heat_tolerance":s.heat_tolerance+r.magical_body*2,"cold_tolerance":s.cold_tolerance+r.magical_body*2,"aquatic":s.aquatic,"perception":r.perception*s.low_light,"magical_affinity":s.magical_affinity,"magical_body":r.magical_body,"built_scale":s.built_scale}
def accommodation_requirements(population):
 ps=[species(x) for x in population]
 if not ps:return {"clearance":1.,"load":1.,"water_access":0.}
 return {"clearance":max(p.built_scale for p in ps),"load":max(p.mass for p in ps),"water_access":sum(p.aquatic for p in ps)/len(ps)}
architecture_requirements=accommodation_requirements
