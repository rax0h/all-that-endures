from simulation.ate_sim import Simulation,generate_world
from simulation.ate_sim.biology import pair_reproductive_opportunity
from simulation.ate_sim.checkpoint import dumps,loads
from simulation.ate_sim.core import Person
from simulation.ate_sim.diagnostics import world_snapshot
from simulation.ate_sim.narrative_sampler import sample_history
from simulation.ate_sim.warfare import Conflict,_campaign


def test_checkpoint_resume_matches_uninterrupted_history():
    direct=Simulation(generate_world(731)).run(30)
    staged=Simulation(generate_world(731)).run(15)
    staged=loads(dumps(staged))
    resumed=Simulation(staged).run(15)
    assert resumed.digest()==direct.digest()


def test_long_lived_species_is_not_charged_for_future_reproductive_years():
    elf_a=Person(1,0,1,1,age=30,species='elf')
    elf_b=Person(2,0,1,1,age=30,species='elf')
    human_a=Person(3,0,1,1,age=30,species='human')
    human_b=Person(4,0,1,1,age=30,species='human')
    assert pair_reproductive_opportunity(elf_a,elf_b)==pair_reproductive_opportunity(human_a,human_b)


def test_snapshot_exposes_species_rank_society_war_and_craft_diagnostics():
    w=Simulation(generate_world(17)).run(5);snap=world_snapshot(w)
    assert snap['year']==5 and snap['population']==len(w.living())
    for key in ('species','reproductive_age','death_causes','essence_ranks','complete_paths','society_members','society_applications','magic_registry_records','adventure_notices','wars_total','battles','war_deaths','crafted_items','magical_items'):assert key in snap


def test_conflict_campaign_produces_causal_battle_record():
    w=generate_world(19);Simulation(w).run(1);sids=sorted(w.settlements)[:2]
    c=Conflict(1,sids[0],sids[1],w.year,'political_rivalry');w.warfare.conflicts[c.id]=c;w.warfare.next_conflict=2
    _campaign(w,Simulation(w).rng,c)
    assert c.battles==1
    assert any(e.kind=='battle' and e.data.get('conflict')==c.id for e in w.events)


def test_narrative_sampler_only_reports_existing_subjects():
    w=Simulation(generate_world(23)).run(8);samples=sample_history(w)
    for s in samples:
        if s['kind']=='life':assert s['subject'] in w.people
        elif s['kind']=='artifact':assert s['subject'] in w.materials.items
        elif s['kind']=='war':assert s['subject'] in w.warfare.conflicts
        assert s['text']
