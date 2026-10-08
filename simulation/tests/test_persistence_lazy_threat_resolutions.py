import pytest

from ate_sim.core import World
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session

RULES = 'independent-threat-resolution-map'


def converted(tmp_path, history=5):
    world = World(843000)
    # Resolution authority can outlive or disagree with related threat rows.
    # There are deliberately no threat records in this fixture.
    for key in range(1, history + 1):
        world.threat_ecology.resolutions[key] = key * 7
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_resolution_map_opens_without_history_and_eight_probes_load_eight(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        resolutions = session.world.threat_ecology.resolutions
        assert resolutions.diagnostics()['payload_loads'] == 0
        assert resolutions.diagnostics()['resident_records'] == 0
        assert [resolutions[key] for key in range(1, 9)] == [key * 7 for key in range(1, 9)]
        assert resolutions.diagnostics()['payload_loads'] == 8
        assert not session.world.threat_ecology.threats
        resolutions[1] = 9001
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.threat_ecology.resolutions[1] == 9001
        assert not session.world.threat_ecology.threats


def test_resolution_replace_delete_reinsert_noop_and_detach(tmp_path):
    path = converted(tmp_path)
    session = open_lazy_world_session(path, rules_id=RULES)
    resolutions = session.world.threat_ecology.resolutions
    generation = session.pin.captured_head
    resolutions[1] = 7
    assert session.save() == generation
    del resolutions[2]
    resolutions[2] = 999
    resolutions[6] = 1000
    assert tuple(resolutions) == (1, 3, 4, 5, 2, 6)
    session.save()
    session.close()
    session = open_lazy_world_session(path, rules_id=RULES)
    assert tuple(session.world.threat_ecology.resolutions) == (1, 3, 4, 5, 2, 6)
    detached = session.detach(materialize_history=True)
    assert type(detached.threat_ecology.resolutions) is dict
    assert detached.threat_ecology.resolutions == {1: 7, 3: 21, 4: 28, 5: 35, 2: 999, 6: 1000}


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_resolution_save_failure_retry_keeps_independent_authority(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.threat_ecology.resolutions[1] = 789
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
        assert session.world.threat_ecology.resolutions[1] == 789


def test_resolution_clean_cache_and_sidecars_do_not_retain_history(tmp_path):
    path = converted(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        resolutions = session.world.threat_ecology.resolutions
        for key in range(1, 1001):
            assert resolutions[key] == key * 7
        assert resolutions.diagnostics()['resident_records'] <= 256
        assert len(resolutions._baseline_payload) <= 256
        assert len(resolutions._baseline_ordinal) <= 256
