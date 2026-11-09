"""Mature execution cannot substitute an unaccepted source or false success."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from simulation import stage_0_6_proof_mature_genesis as g
from simulation import continuation_receipts as r


def request():
    original = r.load_receipt(g.ORIGINAL)
    from simulation.construction_mature_continuation_stages import mature_authority
    authority = mature_authority()
    config = dict(schema='ate-stage06-proof-genesis-request/1',operation='convert-then-one-year',
        database=deepcopy(original['candidate_database']),world=dict(seed=843000,year=1001),
        pin=dict(store_identity=authority.store_identity,captured_head=126),
        expected_saved_digest=g.EXPECTED_DIGEST,
        budgets=dict(construction=12600,open=900,first_step=900,save=900,warm_step=900,fresh_restore=1800))
    return config, original, authority


def test_valid_original_authority_is_required():
    config, original, authority = request()
    g.check_request(config,original,authority)


@pytest.mark.parametrize('path,value',[
    (('world','year'),1002),(('world','seed'),1),(('world','year'),1001.0),
    (('pin','captured_head'),126.0),(('pin','captured_head'),True),
    (('pin','store_identity'),'other'),(('database','bytes'),1),
    (('database','sha256'),'0'*64),(('expected_saved_digest',),'0'*64),
    (('operation',),'inventory-only'),(('budgets','construction'),True),
    (('budgets','save'),0),(('budgets','warm_step'),14401),
])
def test_wrong_request_rejected_before_transport(monkeypatch,tmp_path,path,value):
    config, original, authority = request()
    cursor=config
    for part in path[:-1]:cursor=cursor[part]
    cursor[path[-1]]=value
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    monkeypatch.setattr(g,'check_source',lambda *a: {})
    monkeypatch.setattr(g,'prepare_retained',lambda *a: pytest.fail('invalid request reached transport'))
    monkeypatch.setattr(r,'load_receipt',lambda *a:original)
    from simulation import construction_mature_continuation_stages as stages
    monkeypatch.setattr(stages,'mature_authority',lambda:authority)
    with pytest.raises(ValueError):g.launch(tmp_path,config,expected_sha='test')


@pytest.mark.parametrize('status',[0,1,124,137,143])
def test_exit_never_accepts_missing_result(tmp_path,status):
    if status==0:
        with pytest.raises(ValueError):g.record_exit(tmp_path,status)
    else:
        g.record_exit(tmp_path,status)
        row=r.load_receipt(tmp_path/'evidence/mature-genesis/command-exit.json')
        assert row['acceptance']=='not-accepted' and row['censored']==(status in (124,137,143))


@pytest.mark.parametrize('field,value',[('year',1003),('generation',0),('digest','wrong'),('world_audits',1)])
def test_fresh_result_must_match_accepted_year_and_digest(monkeypatch,tmp_path,field,value):
    row=dict(year=1002,seed=843000,generation=1,digest=g.EXPECTED_DIGEST,world_audits=0)
    row[field]=value
    monkeypatch.setattr(g.subprocess,'run',lambda *a,**k:SimpleNamespace(stdout=json.dumps(row)))
    with pytest.raises(ValueError,match='differs'):
        g.fresh_restore(tmp_path/'proof.sqlite','rules',b'x'*32,g.EXPECTED_DIGEST,1)


def test_no_mature_execution_before_both_validation_jobs_pass():
    import yaml
    path=Path('.github/workflows/stage-0-5-proof-map-validation.yml')
    workflow=yaml.safe_load(path.read_text())
    job=workflow['jobs']['mature-genesis']
    assert set(job['needs'])=={'proof-map','full-suite','mature-genesis-request'}
    assert "outputs.enabled == 'true'" in job['if']
    assert job['timeout-minutes']<=360
    script='\n'.join(s.get('run','') for s in job['steps'])
    assert '330m python -m simulation.stage_0_6_proof_mature_genesis run' in script
    assert 'record-exit' in script
