"""The release harness must actually exercise the complete persistence format."""
from persistence_p5_long_validation import run, _control
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.worldgen import generate_world


def test_long_harness_complete_lane_restores_exact_two_milestones(tmp_path):
    result = run(843000, [1, 2], 0, tmp_path, 'final-long-test',
                 'runtime-source', 'workflow-source', complete_format=True)
    assert result['passed'] and result['complete_format']
    assert all(result['p4'][str(year)]['matches_control'] for year in (1, 2))
    assert result['cold_source_preserved']
    with open_lazy_world_session(result['restore_artifact']['path'], rules_id='final-long-test') as session:
        assert session.world.year == 2
        assert session.world.digest() == result['control']['2']['digest']
        assert int(session.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0]) == 6


def test_long_harness_mature_control_matches_canonical_initialization():
    rows = _control(843000, [0], initialization='mature')
    assert rows['0']['digest'] == generate_world(843000, mature=True).digest()
    assert rows['0']['digest'] != generate_world(843000, mature=False).digest()
