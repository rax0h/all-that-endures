"""Save retention and verifier retries use actual closed complete-format stores."""
import importlib
import importlib.util
from pathlib import Path
import shutil

import pytest

from simulation import continuation_receipts as r
from simulation.tests.continuation_fixtures import build_publication,fixture_authority
from simulation.tests.test_continuation_receipts import producer


def module():
    assert importlib.util.find_spec('simulation.continuation_checkpoint'), 'single-year continuation stage missing'
    return importlib.import_module('simulation.continuation_checkpoint')


@pytest.fixture(scope='module')
def publication(tmp_path_factory):
    info=build_publication(tmp_path_factory.mktemp('real-continuation'))
    return info,fixture_authority(info)


def inputs(tmp_path,publication):
    info,a=publication;root=tmp_path/'published';shutil.copytree(info['published'],root)
    return root,a,dict(kind='publication',artifact=a.publication.to_dict())


def hashes(root):
    return {p.name:r.file_hash(p) for p in root.iterdir()}


def forbidden(*args,**kw):raise AssertionError('stage repeated forbidden expensive work')


def test_save_publishes_closed_unverified_year_without_audit_or_digest(tmp_path,publication,monkeypatch):
    m=module();source,a,previous=inputs(tmp_path,publication);before=hashes(source)
    import persistence_p5_long_validation as p5
    monkeypatch.setattr(p5,'_audit',forbidden);monkeypatch.setattr(p5,'_digest',forbidden)
    monkeypatch.setattr(p5,'generate_world',forbidden)
    output=tmp_path/'saved'
    result=m.save_year(source,output,authority=a,year=1,predecessor=previous,producer=producer())
    assert result['stage']=='year-saved-unverified'
    assert result['generation']==a.bootstrap_generation+1 and result['year']==1
    assert set(hashes(output))=={'candidate.sqlite','checkpoint.json','save.json'}
    assert (output/'checkpoint.json').read_bytes()==(source/'checkpoint.json').read_bytes()
    assert result['live_before']==result['live_after']
    assert hashes(source)==before
    assert r.validate_saved(output,authority=a,expected_year=1,
        expected_predecessor=previous,producer=producer())==result
    # The retained artifact is never opened for this independent test observation.
    disposable=tmp_path/'observe.sqlite';shutil.copyfile(output/'candidate.sqlite',disposable)
    from ate_sim.persistence_lazy import open_lazy_world_session
    with open_lazy_world_session(disposable,rules_id=a.source_config['rules_id']) as session:
        assert session.world.year==1
        original=r.validate_original(source/'checkpoint.json',a)
        assert session.world.digest()==original['state']['controls']['1']['digest']
    retained=hashes(output)
    with pytest.raises(FileExistsError):m.save_year(source,output,authority=a,year=1,predecessor=previous,producer=producer())
    assert hashes(output)==retained


@pytest.mark.parametrize('phase',['after_simulation','after_save','before_close','after_close','before_hash','before_publish'])
def test_interrupted_save_stage_preserves_original_and_has_no_completed_bundle(tmp_path,publication,monkeypatch,phase):
    m=module();source,a,previous=inputs(tmp_path,publication);before=hashes(source)
    actual=m._phase
    def fail(name,**kw):
        actual(name,**kw)
        if name==phase:raise OSError('stage interrupted')
    monkeypatch.setattr(m,'_phase',fail)
    with pytest.raises(OSError,match='interrupted'):
        m.save_year(source,tmp_path/'saved',authority=a,year=1,predecessor=previous,producer=producer())
    assert not (tmp_path/'saved').exists() and hashes(source)==before


def test_wrong_year_is_rejected_before_simulation(tmp_path,publication,monkeypatch):
    m=module();source,a,previous=inputs(tmp_path,publication)
    monkeypatch.setattr(m.Simulation,'run',forbidden)
    with pytest.raises(ValueError):m.save_year(source,tmp_path/'saved',authority=a,year=2,
        predecessor=previous,producer=producer())
    assert not (tmp_path/'saved').exists()


def test_failed_receipt_publication_preserves_original(tmp_path,publication,monkeypatch):
    m=module();source,a,previous=inputs(tmp_path,publication);before=hashes(source)
    def fail(*args,**kw):raise OSError('receipt write failed')
    monkeypatch.setattr(r,'publish_receipt',fail)
    with pytest.raises(OSError,match='receipt write'):
        m.save_year(source,tmp_path/'saved',authority=a,year=1,predecessor=previous,producer=producer())
    assert not (tmp_path/'saved').exists() and hashes(source)==before
