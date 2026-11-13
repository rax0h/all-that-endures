"""Practice retains only its current canonical operands between lazy passes."""
from collections import Counter
from copy import deepcopy
import random

import pytest

from ate_sim.agency import _practice_path
from ate_sim.core import Person
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim import persistence_history_runtime as records
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open


def configure(world):
    world.people[1] = Person(1, -30, 1, 1, age=30, rank=1)
    for essence in ('fire', 'water', 'wind'):
        world.advancement.absorb_essence(1, essence, 0)
    path = world.advancement.path(1)
    for essence in path.essences:
        for _ in range(4):
            world.advancement.awaken_skill(1, 'eyes', 0, target_essence=essence)


def test_one_practice_action_loads_each_canonical_ability_header_once(tmp_path, monkeypatch):
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
        _practice_path(session.world, session.world.people[1], random.Random(32), 'work', .5)
        assert len(loads) == 20
        assert max(loads.values()) == 1, dict(loads)
        assert session.world.people[1].rank == 1


@pytest.mark.parametrize('mode', ['empty', 'partial', 'full', 'ceiling', 'milestone', 'body_transition'])
def test_action_matches_eager_state_rng_events_and_saved_identity(tmp_path, mode):
    expected = []
    def setup(world):
        configure(world)
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
                ability.function = 'creation'
                ability.rank = 2
            # Seed32 shuffles indices to19,14,10,... . The first use raises
            # the last Iron ability, allowing later uses to practice Bronze.
            path.abilities[19].rank = 1
            path.abilities[19].level = 9
            path.abilities[19].progress = .99
        world.people[1].rank = world.advancement.rank(1)
        expected.append(deepcopy(world))
    path, pair = ranked_fixture(tmp_path, size=4, configure=setup)
    eager = expected.pop()
    reference_rng = random.Random(32)
    _practice_path(eager, eager.people[1], reference_rng, 'work', .5)
    expected_digest = eager.digest()
    with fast_open(path, pair) as session:
        rng = random.Random(32)
        _practice_path(session.world, session.world.people[1], rng, 'work', .5)
        assert rng.getstate() == reference_rng.getstate()
        assert session.world.digest() == expected_digest
        assert session.skills[1, 'craft'].provenance is session.skills[2, 'craft'].provenance
        if mode == 'body_transition':
            assert session.world.people[1].rank == 2
            assert session.world.advancement.path(1).abilities[14].progress > 0
            transitions = [e for e in session.world.events if e.kind == 'rank_advanced']
            assert len(transitions) == 1
            assert transitions[0].data['from_rank'] == 1
            assert transitions[0].data['to_rank'] == 2
        if mode in ('milestone', 'body_transition'):
            # Existing proof publisher cannot certify this fresh-child
            # replacement. Baseline and candidate both reject it; preserve
            # the supported boundary instead of claiming rank-up save support.
            before = session.pin.captured_head
            with pytest.raises(StoreIntegrityError, match='AbilityProgress.response_model'):
                session.save()
            assert session.resolve_save() == before
            return
        session.save()
        saved = session.proof_manifest
    with fast_open(path, saved) as restored:
        assert restored.world.digest() == expected_digest
        assert restored.skills[1, 'craft'].provenance is restored.skills[2, 'craft'].provenance
