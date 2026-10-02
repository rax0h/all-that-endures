import pytest

from ate_sim.advancement import AdvancementState
from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world


def test_iron_body_requires_all_twenty_abilities():
    advancement = AdvancementState()
    for essence in ("fire", "water", "wind"):
        advancement.absorb_essence(1, essence, 0)

    path = advancement.path(1)
    assert len(path.base_essences) == 3
    assert path.confluence is not None
    assert len(path.abilities) == 4
    assert advancement.rank(1) == 0

    for essence in path.essences:
        for _ in range(4):
            advancement.awaken_skill(1, "eyes", 1, target_essence=essence)

    assert len(path.abilities) == 20
    assert advancement.rank(1) == 1


@pytest.mark.parametrize("seed", [843001, 843002])
def test_ranked_living_people_have_complete_loadouts(seed):
    world = generate_world(seed)
    Simulation(world).run(300)

    offenders = []
    for person in world.people.values():
        if not person.alive:
            continue
        path = world.advancement.paths.get(person.id)
        if path is None:
            continue
        rank = world.advancement.rank(person.id)
        if rank <= 0:
            continue
        counts = {essence: 0 for essence in path.essences}
        for ability in path.abilities:
            if ability.essence in counts:
                counts[ability.essence] += 1
        complete = (
            len(path.base_essences) == 3
            and path.confluence is not None
            and len(path.essences) == 4
            and len(path.abilities) == 20
            and len(counts) == 4
            and all(count == 5 for count in counts.values())
        )
        if not complete:
            offenders.append(
                {
                    "person": person.id,
                    "rank": rank,
                    "bases": len(path.base_essences),
                    "confluence": path.confluence is not None,
                    "abilities": len(path.abilities),
                    "per_essence": counts,
                }
            )

    assert not offenders, f"ranked living people with incomplete loadouts: {offenders[:20]}"
