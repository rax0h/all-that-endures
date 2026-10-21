from ate_sim.worldgen import generate_world
from ate_sim.advancement import AbilityProgress, EssencePath
from run_long_history import snapshot
from ate_sim.diagnostics import world_snapshot

def test_rank_diagnostics_separate_complete_and_incomplete_paths():
    world = generate_world(843000)
    people = list(world.people.values())[:2]
    world.advancement.paths = {}
    for person, count in zip(people, (1,20)):
        world.advancement.paths[person.id] = EssencePath(base_essences=["fire","water","wind"] if count==20 else ["fire"],
            confluence="confluence-test" if count==20 else None, abilities=[
            AbilityProgress(("fire","water","wind","confluence-test")[n//5],"test",str(n),"test","control","fire",0,rank=5)
            for n in range(count)])
    result = snapshot(world)
    assert result["essence_user_ranks"] == {0:1,5:1}
    assert result["completed_path_ranks"] == {5:1}
    assert result["incomplete_path_ranks"] == {0:1}

    standard=world_snapshot(world)
    assert standard["completed_path_ranks"] == {5:1}
    assert standard["incomplete_path_ranks"] == {0:1}
