"""A failed full verification resumes from the same retained saved generation."""
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from simulation import continuation_receipts as r
from simulation.tests.test_continuation_checkpoint import publication,inputs,module,hashes,forbidden
from simulation.tests.test_continuation_receipts import producer


@pytest.fixture(scope='module')
def saved_template(tmp_path_factory,publication):
    root=tmp_path_factory.mktemp('saved-verifiers');source,a,previous=inputs(root,publication)
    saved=root/'saved';manifest=module().save_year(source,saved,authority=a,year=1,
        predecessor=previous,producer=producer())
    candidate=replace(a.publication,artifact_id=10,name='saved1',producer_job='save1',
        runtime_sha=a.execution_runtime_sha,runtime_tree=a.execution_runtime_tree)
    return saved,a,manifest,candidate


def saved_inputs(tmp_path,saved_template):
    source,a,manifest,candidate=saved_template
    saved=tmp_path/'saved';shutil.copytree(source,saved)
    return saved,a,manifest,candidate


def api():
    m=module();assert hasattr(m,'audit_year') and hasattr(m,'digest_year'), 'independent saved verification missing'
    return m


def test_independent_audit_and_digest_check_the_exact_saved_world(tmp_path,saved_template,monkeypatch):
    m=api();saved,a,manifest,candidate=saved_inputs(tmp_path,saved_template);before=hashes(saved)
    monkeypatch.setattr(m.Simulation,'run',forbidden)
    monkeypatch.setattr(m.p5,'generate_world',forbidden);monkeypatch.setattr(m.p5,'_control',forbidden)
    audit=m.audit_year(saved,tmp_path/'audit.json',authority=a,candidate=candidate,producer=producer('audit','audit1'))
    digest=m.digest_year(saved,tmp_path/'digest.json',authority=a,candidate=candidate,producer=producer('digest','digest1'))
    original=r.validate_original(saved/'checkpoint.json',a)['state']['controls']['1']
    assert audit['stage']=='year-audited' and audit['observation']['audited_state']=='saved-reopened'
    assert {k:v for k,v in audit['observation']['audit'].items() if k!='audit_seconds'}=={
        k:v for k,v in original['audit'].items() if k!='audit_seconds'}
    assert digest['observation']['digest']==original['digest']
    assert audit['binding']==digest['binding']
    assert audit['binding']['save_sha256']==r.file_hash(saved/'save.json')
    assert digest['observation']['counters']==original['counters']
    assert audit['input_preserved'] is digest['input_preserved'] is True
    assert hashes(saved)==before


@pytest.mark.parametrize('stage',['audit','digest'])
def test_failed_verifier_retries_in_new_process_without_simulation(tmp_path,saved_template,monkeypatch,stage):
    m=api();saved,a,manifest,candidate=saved_inputs(tmp_path,saved_template);before=hashes(saved)
    actual=m._phase
    def fail(name,**kw):
        actual(name,**kw)
        if name=='after_'+stage:raise OSError('verification interrupted')
    monkeypatch.setattr(m,'_phase',fail)
    with pytest.raises(OSError,match='interrupted'):
        getattr(m,stage+'_year')(saved,tmp_path/'failed.json',authority=a,candidate=candidate,producer=producer(stage,stage+'1'))
    assert not (tmp_path/'failed.json').exists() and hashes(saved)==before
    r.publish_receipt(tmp_path/'authority.json',a.to_dict())
    r.publish_receipt(tmp_path/'candidate.json',candidate.to_dict())
    code="""
import sys
from pathlib import Path
from simulation import continuation_checkpoint as m, continuation_receipts as r
def forbidden(*args,**kw): raise AssertionError('retry repeated simulation')
m.Simulation.run=forbidden
m.p5.generate_world=forbidden
m.p5._control=forbidden
a=r.Authority.from_dict(r.load_receipt(sys.argv[3]))
c=r.ArtifactRef.from_dict(r.load_receipt(sys.argv[4]))
p=dict(harness_sha='e'*40,workflow_sha='c'*40,run_id=1,job='retry',stage=sys.argv[5])
getattr(m,sys.argv[5]+'_year')(Path(sys.argv[1]),Path(sys.argv[2]),authority=a,candidate=c,producer=p)
"""
    result=subprocess.run([sys.executable,'-c',code,str(saved),str(tmp_path/'retry.json'),
        str(tmp_path/'authority.json'),str(tmp_path/'candidate.json'),stage],
        env=dict(os.environ,PYTHONPATH='simulation:.'),capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr
    assert (tmp_path/'retry.json').exists() and hashes(saved)==before


@pytest.mark.parametrize('stage',['audit','digest'])
def test_wrong_actual_values_block_a_verification_receipt(tmp_path,saved_template,monkeypatch,stage):
    m=api();saved,a,manifest,candidate=saved_inputs(tmp_path,saved_template)
    if stage=='audit':
        actual=m.p5._audit
        def wrong(world):
            result=actual(world);result['snapshot']['magic_access']['treasuries']['1']['iron']+=1
            return result
        monkeypatch.setattr(m.p5,'_audit',wrong)
    else:monkeypatch.setattr(m.p5,'_digest',lambda world:('0'*64,0.1))
    with pytest.raises(ValueError,match='control') as error:
        getattr(m,stage+'_year')(saved,tmp_path/'wrong.json',authority=a,candidate=candidate,producer=producer(stage,stage+'1'))
    if stage=='audit':
        assert '/snapshot/magic_access/treasuries/1/iron' in str(error.value)
        assert 'expected=' in str(error.value) and 'actual=' in str(error.value)
    assert not (tmp_path/'wrong.json').exists()


def test_audit_mismatch_diagnostics_bound_values_and_difference_count(tmp_path,saved_template,monkeypatch):
    m=api();saved,a,manifest,candidate=saved_inputs(tmp_path,saved_template)
    actual=m.p5._audit
    def wrong(world):
        result=actual(world)
        result.update({f'unknown/{i}':'x'*10000 for i in range(30)})
        return result
    monkeypatch.setattr(m.p5,'_audit',wrong)
    with pytest.raises(ValueError,match='control') as error:
        m.audit_year(saved,tmp_path/'wrong.json',authority=a,candidate=candidate,producer=producer('audit','audit1'))
    message=str(error.value)
    assert '/unknown~10' in message and 'actual=' in message
    assert len(message)<4096
    assert not (tmp_path/'wrong.json').exists()


def test_foreign_candidate_producer_is_rejected_before_open(tmp_path,saved_template,monkeypatch):
    m=api();saved,a,manifest,candidate=saved_inputs(tmp_path,saved_template)
    monkeypatch.setattr(m,'open_lazy_world_session',forbidden)
    with pytest.raises(ValueError):m.audit_year(saved,tmp_path/'wrong.json',authority=a,
        candidate=replace(candidate,harness_sha='9'*40),producer=producer('audit','audit1'))
