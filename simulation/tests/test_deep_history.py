from simulation.ate_sim import Simulation,generate_world
from simulation.ate_sim.biology import pair_reproductive_opportunity
from simulation.ate_sim.checkpoint import dumps,loads
from simulation.ate_sim.core import Person
from simulation.ate_sim.diagnostics import world_snapshot


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


def test_snapshot_exposes_species_and_rank_diagnostics():
    w=Simulation(generate_world(17)).run(5);snap=world_snapshot(w)
    assert snap['year']==5 and snap['population']==len(w.living())
    assert 'species' in snap and 'reproductive_age' in snap and 'death_causes' in snap
    assert 'essence_ranks' in snap and 'complete_paths' in snap
