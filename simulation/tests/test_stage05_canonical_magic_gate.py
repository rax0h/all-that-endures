from ate_sim.advancement import AdvancementState


def _three_essence_path():
    state = AdvancementState()
    for essence in ('fire', 'water', 'wind'):
        state.absorb_essence(1, essence, 0)
    return state


def test_nineteen_of_twenty_is_still_unranked():
    state = _three_essence_path()
    path = state.path(1)
    remaining = 15
    for essence in path.essences:
        for _ in range(min(4, remaining)):
            state.awaken_skill(1, 'eyes', 1, target_essence=essence)
            remaining -= 1
            if remaining == 0:
                break
        if remaining == 0:
            break
    assert len(path.abilities) == 19
    assert state.rank(1) == 0


def test_twenty_requires_exact_five_per_essence():
    state = _three_essence_path()
    path = state.path(1)
    for essence in path.essences:
        for _ in range(4):
            state.awaken_skill(1, 'eyes', 1, target_essence=essence)
    assert len(path.abilities) == 20
    assert all(len(path.abilities_for(essence)) == 5 for essence in path.essences)
    assert state.rank(1) == 1

    # Twenty abilities by raw count is not enough if the canonical distribution
    # is corrupted: body rank must fall back to unranked rather than leak Iron.
    path.abilities[-1].essence = path.essences[0]
    assert len(path.abilities) == 20
    assert state.rank(1) == 0
