from ate_sim.worldgen import generate_world
from ate_sim.advancement import AbilityProgress, EssencePath
from run_long_history import snapshot

def test_rank_diagnostics_separate_complete_and_incomplete_paths():
    world = generate_world(843000)
    people = list(world.people.values())[:2]
    world.advancement.paths = {}
    for person, count in zip(people, (1,20)):
        world.advancement.paths[person.id] = EssencePath(abilities=[
            AbilityProgress("fire","test",str(n),"test","control","fire",0,rank=5)
            for n in range(count)])
    result = snapshot(world)
    assert result["essence_user_ranks"] == {5:2}
    assert result["completed_path_ranks"] == {5:1}
    assert result["incomplete_path_ranks"] == {5:1}
