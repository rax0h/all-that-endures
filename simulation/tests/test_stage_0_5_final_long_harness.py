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
        old_receipt = (previous / 'checkpoint.json').read_bytes()
        stage_kw = dict(kw, product_sha='repaired-product') if after == 'complete' else kw
        override = dict(checkpoint_product_sha='runtime-source') if after == 'complete' else {}
        result = run(*args, target, **stage_kw, resume_from=before, stop_after=after, **override)
        assert (previous / 'checkpoint.json').read_bytes() == old_receipt
        if after == 'complete':
            import json
            receipt = json.loads((target / 'checkpoint.json').read_text())
            assert receipt['config']['product_sha'] == 'repaired-product'
            assert receipt['checkpoint_product_sha'] == 'runtime-source'
            assert receipt['source_checkpoint']['product_sha'] == 'runtime-source'
            assert receipt['source_checkpoint']['workflow_sha'] == 'workflow-source'
            assert receipt['source_checkpoint']['database']['sha256'] == json.loads(old_receipt)['database']['sha256']
        assert result['checkpoint_stage'] == after and not result['passed']
        previous = target
    kw = dict(kw, product_sha='repaired-product')
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
    assert result['product_sha'] == 'repaired-product'
    assert result['source_checkpoint']['product_sha'] == 'repaired-product'
    assert result['source_checkpoint']['prior_source']['product_sha'] == 'runtime-source'
    assert all(result['p4'][str(y)]['matches_control'] for y in (1, 2))
    assert result['restore_artifact']['year'] == 2


def test_source_product_override_is_rejected_without_explicit_resume(tmp_path):
    import pytest
    with pytest.raises(ValueError,match='resume'):
        run(843000,[1,2],0,tmp_path,'repair-test','new-product','new-workflow',
            complete_format=True,stop_after='cold',checkpoint_product_sha='old-product')


def test_repair_resume_keeps_all_nonproduct_configuration_checks(tmp_path):
    import json,hashlib,pytest
    import persistence_p5_long_validation as harness
    config=dict(seed=843000,milestones=[1,2],bootstrap_year=0,rules_id='repair-test',
        product_sha='old-product',complete_format=True,initialization='founders',simulation_schema=harness.SCHEMA)
    db=tmp_path/'p5-long-lazy.sqlite';db.write_bytes(b'not-opened-in-preflight')
    receipt=dict(schema=1,stage='lazy',config=config,workflow_sha='old-workflow',
        database=dict(name=db.name,sha256=hashlib.sha256(db.read_bytes()).hexdigest()),state={})
    path=tmp_path/'checkpoint.json';path.write_text(json.dumps(receipt));before=path.read_bytes()
    args=(843000,[1,2],0,tmp_path,'repair-test','new-product','new-workflow')
    base=dict(complete_format=True,resume_from='lazy',stop_after='complete',checkpoint_product_sha='old-product')
    for change in ('seed','rules','maturity','milestones','source-product','stage','checksum','no-provenance'):
        requested=list(args);kw=dict(base)
        if change=='seed':requested[0]=7
        elif change=='rules':requested[4]='wrong-rules'
        elif change=='maturity':kw['initialization']='mature'
        elif change=='milestones':requested[1]=[1,3]
        elif change=='source-product':kw['checkpoint_product_sha']='wrong-source'
        elif change=='stage':kw['resume_from']='cold'
        elif change=='no-provenance':kw.pop('checkpoint_product_sha')
        else:db.write_bytes(b'corrupt')
        with pytest.raises(ValueError,match='configuration|stage|checksum'):
            run(*requested,**kw)
        assert path.read_bytes()==before
