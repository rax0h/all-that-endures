import pytest

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session

RULES = 'bounded-belief-scalars'


def converted(tmp_path, history=5):
    world = World(843000)
    for key in range(1, history + 1):
        world.knowledge.beliefs[(key, 1)] = .75
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_belief_teaching_loads_only_teacher_and_existing_student(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        beliefs = session.world.knowledge.beliefs
        assert beliefs.diagnostics()['payload_loads'] == 0
        historical_pin = session.store.capture_pin()
        session.world.knowledge.teach(1, 2, 1, reliability=.8)
        assert beliefs[(2, 1)] == .75 * .8
        session.save()
        assert beliefs.diagnostics()['payload_loads'] <= 2
        counts = session.store.db.execute("SELECT COUNT(*) FROM lazy_record_versions WHERE namespace='world.knowledge.beliefs'").fetchone()[0]
        assert counts == history + 1
        session.store.release_pin(historical_pin)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.knowledge.beliefs[(2, 1)] == .75 * .8


def test_belief_teach_default_clamp_order_noop_and_portable_detach(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    knowledge = session.world.knowledge
    generation = session.pin.captured_head
    knowledge.beliefs[(1, 1)] = .75
    assert session.save() == generation
    knowledge.teach(99, 6, 2, reliability=4)
    assert knowledge.beliefs[(6, 2)] == 1.
    del knowledge.beliefs[(1, 1)]
    knowledge.beliefs[(1, 1)] = .4
    assert tuple(knowledge.beliefs)[-2:] == ((6, 2), (1, 1))
    session.save()
    detached = session.detach(materialize_history=True)
    assert type(detached.knowledge.beliefs) is dict
    assert checkpoint.loads(checkpoint.dumps(detached)).digest() == detached.digest()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_belief_teach_save_recovery(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.knowledge.teach(1, 2, 1, reliability=.8)
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.knowledge.beliefs[(2, 1)] == .75 * .8
