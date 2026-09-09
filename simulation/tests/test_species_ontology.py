from ate_sim.rank import profile
from ate_sim.species import species, compose_biology, architecture_requirements, reproductive_compatibility, reproductive_span, habitat_suitability

def test_species_not_personality():
    for key,p in __import__('ate_sim.species',fromlist=['SPECIES']).SPECIES.items():
        assert not hasattr(p,'temperament') and not hasattr(p,'morality') and not hasattr(p,'culture')

def test_rank_composes_without_erasing_species():
    low_l=compose_biology('leonid',profile(0)); high_l=compose_biology('leonid',profile(4)); high_h=compose_biology('human',profile(4))
    assert low_l['strength']>compose_biology('human',profile(0))['strength']
    assert high_l['magical_body']==high_h['magical_body']
    assert high_l['stature']!=high_h['stature']
    assert high_l['respiration_need']<low_l['respiration_need']

def test_environmental_traits_are_physical():
    assert species('smoulder').heat_tolerance>species('human').heat_tolerance
    assert species('merfolk').aquatic>species('human').aquatic

def test_mixed_population_changes_accommodation():
    mixed=architecture_requirements(['human','draconian','merfolk']); human=architecture_requirements(['human'])
    assert mixed['clearance']>human['clearance']
    assert mixed['load']>human['load']
    assert mixed['water_access']>0

def test_unratified_reproduction_does_not_create_species_selection():
    assert reproductive_compatibility('human','human')==1.0
    assert reproductive_compatibility('human','elf')==1.0
    assert reproductive_compatibility('human','merfolk')==1.0
    assert reproductive_span('elf')>reproductive_span('human')

def test_habitat_fit_is_embodied_not_cultural():
    wet_low=habitat_suitability('merfolk',.22,.92,.35)
    dry_high=habitat_suitability('merfolk',.82,.12,.10)
    assert wet_low>dry_high
    assert habitat_suitability('smoulder',.28,.18,.05)>=habitat_suitability('human',.28,.18,.05)
