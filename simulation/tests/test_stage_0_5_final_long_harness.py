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


def test_staged_harness_resumes_checked_artifacts_without_rebuilding(tmp_path, monkeypatch):
    import persistence_p5_long_validation as harness
    import pytest
    import shutil
    args = (843000, [1, 2], 0)
    kw = dict(rules_id='staged-test', product_sha='runtime-source',
              workflow_sha='workflow-source', complete_format=True)
    cold = tmp_path / 'cold'
    result = run(*args, cold, **kw, stop_after='cold')
    assert result['checkpoint_stage'] == 'cold' and not result['passed']

    def forbidden(*args, **kwargs):
        raise AssertionError('resume regenerated the independent control')
    monkeypatch.setattr(harness, '_control', forbidden)
    previous = cold
    for before, after in [('cold', 'lazy'), ('lazy', 'complete')]:
        target = tmp_path / after
        target.mkdir()
        shutil.copyfile(previous / 'checkpoint.json', target / 'checkpoint.json')
        name = f'p5-long-{before}.sqlite'
        shutil.copyfile(previous / name, target / name)
        result = run(*args, target, **kw, resume_from=before, stop_after=after)
        assert result['checkpoint_stage'] == after and not result['passed']
        previous = target
    with pytest.raises(ValueError, match='configuration'):
        run(1, [1, 2], 0, previous, **kw, resume_from='complete')
    damaged = tmp_path / 'damaged'
    shutil.copytree(previous, damaged)
    with (damaged / 'p5-long-complete.sqlite').open('ab') as stream:
        stream.write(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        run(*args, damaged, **kw, resume_from='complete')
    result = run(*args, previous, **kw, resume_from='complete')
    assert result['passed'] and result['cold_source_preserved']
    assert all(result['p4'][str(y)]['matches_control'] for y in (1, 2))
    assert result['restore_artifact']['year'] == 2
