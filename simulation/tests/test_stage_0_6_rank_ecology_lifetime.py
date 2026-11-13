"""Yearly rank training retains canonical abilities through its existing passes."""
from collections import Counter
from copy import deepcopy

import pytest

from ate_sim import persistence_history_runtime as records
from ate_sim.rank_ecology import rank_ecology_step
from ate_sim.core import RNG, LocalState
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open


def test_annual_training_loads_each_canonical_ability_header_once(tmp_path, monkeypatch):
    path, pair = ranked_fixture(tmp_path, size=4, configure=configure)
    with fast_open(path, pair) as session:
        loads = Counter()
        original = records.read_record_header
        def checked(*args, **kwargs):
            header = original(*args, **kwargs)
            if header[1] == 'advancement.AbilityProgress/v1':
                loads[args[2]] += 1
            return header
        monkeypatch.setattr(records, 'read_record_header', checked)
        rank_ecology_step(session.world, RNG(32))
        assert len(loads) == 20
        assert max(loads.values()) == 1, dict(loads)


class ObservedRNG(RNG):
    def __init__(self, seed):
        super().__init__(seed)
        self.used = []

    def stream(self, namespace, year=0, entity=0):
        result = super().stream(namespace, year, entity)
        self.used.append((namespace, year, entity, result))
        return result

    def states(self):
        return [(n, y, e, r.state, r._gauss) for n, y, e, r in self.used]


@pytest.mark.parametrize('mode', ['empty', 'partial', 'full', 'ceiling', 'milestone', 'body_transition', 'mastery'])
def test_annual_training_matches_eager_rng_events_and_saved_identity(tmp_path, mode):
    expected = []
    def setup(world):
        configure(world)
        world.people[1].occupation = 'adventurer'
        path = world.advancement.path(1)
        if mode == 'empty':
            path.abilities.clear()
        elif mode == 'partial':
            del path.abilities[4:]
        elif mode == 'ceiling':
            for ability in path.abilities:
                ability.rank = 5
        elif mode == 'milestone':
            for ability in path.abilities:
                ability.level = 9
                ability.progress = .99
        elif mode == 'body_transition':
            for ability in path.abilities:
                ability.rank = 2
                ability.level = 0
                ability.progress = 0.
            order = list(range(20))
            RNG(32).stream('rank_ecology', world.year, 1).shuffle(order)
            path.abilities[order[0]].rank = 1
            path.abilities[order[0]].level = 9
            path.abilities[order[0]].progress = .99
        elif mode == 'mastery':
            world.local[1] = LocalState()
            for ability in path.abilities:
                ability.rank = 3
        world.people[1].rank = world.advancement.rank(1)
        expected.append(deepcopy(world))
    path, pair = ranked_fixture(tmp_path, size=4, configure=setup)
    eager = expected.pop()
    reference = ObservedRNG(32)
    rank_ecology_step(eager, reference)
    digest = eager.digest()
    with fast_open(path, pair) as session:
        rng = ObservedRNG(32)
        rank_ecology_step(session.world, rng)
        assert rng.states() == reference.states()
        assert session.world.digest() == digest
        assert session.skills[1, 'craft'].provenance is session.skills[2, 'craft'].provenance
        if mode == 'body_transition':
            assert session.world.people[1].rank == 2
            abilities = tuple(session.world.advancement.path(1).abilities)
            assert any(a.rank == 2 and a.progress > 0 for a in abilities)
            transitions = [e for e in session.world.events if e.kind == 'rank_advanced']
            assert len(transitions) == 1
        if mode == 'mastery':
            assert any(e.kind == 'ability_control_trial' for e in session.world.events)
        session.save()
        saved = session.proof_manifest
    with fast_open(path, saved) as restored:
        assert restored.world.digest() == digest
        assert restored.skills[1, 'craft'].provenance is restored.skills[2, 'craft'].provenance
