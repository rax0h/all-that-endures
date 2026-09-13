from dataclasses import replace
from unittest.mock import patch
import pytest
from simulation.ate_sim import Simulation, generate_world
from simulation.ate_sim.core import Layer, Ref, World
from simulation.ate_sim.metaphysics import grant_resurrection_token


def test_population_index_birth_death_resurrection_and_archive():
    world=generate_world(17)
    sim=Simulation(world)
    original=list(world.people.values())
    person=original[0]
    with world.current_people_scope():
        assert list(world.current_people())==original
        sim._die(person,'test')
        assert person not in world.current_people()
        assert world.people[person.id] is person
        survivor=original[1]
        grant_resurrection_token(world,survivor.id,'test','test')
        sim._die(survivor,'test')
        assert survivor.alive and survivor in world.current_people()
        child=replace(survivor,id=world.next_person,age=0)
        world.people[child.id]=child
        world.emit('birth',Layer.REALITY,(Ref('person',child.id),))
        assert world.current_people()[-1] is child
        cached=world.current_people()
        assert world.current_people() is cached
    # Direct scenario edits outside the engine never see a stale cache.
    person.alive=True
    assert list(world.current_people())==original+[child]


def test_scope_clears_on_exception():
    world=generate_world(17)
    with pytest.raises(RuntimeError),world.current_people_scope():
        world.current_people()
        raise RuntimeError('interrupted step')
    assert '_living_cache' not in world.__dict__
    assert '_index_current_people' not in world.__dict__


def test_indexed_population_matches_archive_scan_simulation():
    indexed=Simulation(generate_world(843000)).run(100)
    with patch.object(World,'current_people',lambda w:tuple(p for p in w.people.values() if p.alive)):
        reference=Simulation(generate_world(843000)).run(100)
    assert indexed.digest()==reference.digest()=='6b542d4f9f10ff8548d277128443aaf313d13eecef20e9490965d25806cb50d9'
