"""Physical receipt proofs survive real audit JSON key conversion and reuse."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from simulation import checkpoint_artifacts as artifacts
from simulation import continuation_receipts as r
from simulation import construction_mature_continuation_stages as runner


ARCHIVE_SHA = 'c9b502c71e355644b26ae4b0bdb3ca3edc6dfb567335d73465da009af4cd1943'
MEMBER_SHA = '4be22bcfeea6dd71e588d8f65c4e63ab7538c2faca7c4a07640b26b2f1252b97'
CONTENT_SHA = 'd5b3f1c750c7355c342ed3f127a660ccd2d09d36e5a4c48951902361c04c1f0d'


def retained_reference():
    return r.ArtifactRef(artifact_id=12148235361,run_id=39152488567,
        workflow_sha='247b5dc2f6ef5b0aa6596798e6ccad3235a6c317',
        workflow_path='.github/workflows/stage-0-5-mature-continuation-stage.yml',
        producer_job='mature-stage',name='continuation-stage-audit-1001',
        archive_sha256=ARCHIVE_SHA,archive_bytes=35605,
        harness_sha='60eaf810fbc156e333722672627a8dc2caf20bc1',
        runtime_sha='2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a',
        runtime_tree='76dee76973928dbce72860156feb32f2d7f02f86')


@pytest.fixture
def retained(tmp_path):
    # Exact downloaded public artifact, not a re-created receipt or mature DB.
    archive=Path(__file__).with_name('fixtures')/'continuation-audit1001.zip'
    assert archive.stat().st_size==35605 and r.file_hash(archive)==ARCHIVE_SHA
    dest=tmp_path/'retained'
    artifacts.extract(archive,dest,{'audit.json'})
    path=dest/'audit.json'
    assert path.stat().st_size==223650 and r.file_hash(path)==MEMBER_SHA
    row=r.load_receipt(path)
    authority=runner.mature_authority()
    r.validate_verification(row,authority,kind='audit',binding=row['binding'])
    return dest,row,authority,retained_reference()


@pytest.mark.parametrize('years',[{2:1,10:3},{0:2,9:8,100:4,1001:6}])
def test_published_year_keys_have_a_stable_reload_hash(tmp_path,years):
    row={'nested':[{'new_irons_by_year':years}],'strict_values':[True,1,1.0,-0.0]}
    path=tmp_path/'receipt.json';r.publish_receipt(path,row)
    decoded=r.load_receipt(path)
    assert r.receipt_bytes(decoded)==path.read_bytes()
    assert r.receipt_hash(row)==r.receipt_hash(decoded)==r.file_hash(path)
    assert [type(x) for x in decoded['strict_values']]==[bool,int,float,float]
    assert json.dumps(decoded['strict_values'][-1])=='-0.0'


def test_key_collision_rejects_before_publishing_any_receipt(tmp_path):
    path=tmp_path/'receipt.json'
    with pytest.raises(ValueError,match='duplicate'):
        r.publish_receipt(path,{'years':{1:'first','1':'second'}})
    assert not path.exists()


def test_exact_retained_audit_is_read_without_rewriting_or_world_open(retained,monkeypatch):
    dest,row,authority,ref=retained
    def forbidden(*args,**kwargs):raise AssertionError('receipt handoff opened a World')
    monkeypatch.setattr(runner.checkpoint,'open_lazy_world_session',forbidden)
    actual=runner._small({'audit':dest},'audit','audit.json',ref,authority)
    assert r.same(actual,row) and r.file_hash(dest/'audit.json')==MEMBER_SHA
    assert r.receipt_hash(actual)==CONTENT_SHA


def digest_fixture(audit):
    # Metadata fixture only. This does not stand in for the actual mature digest.
    row=copy.deepcopy(audit)
    row['stage']='year-digest-verified'
    row['producer']=dict(harness_sha='e'*40,workflow_sha='c'*40,run_id=1,
        job='digest-test',stage='digest')
    del row['observation']['audit'];del row['observation']['audited_state']
    control=json.loads(row['original_checkpoint'])['state']['controls']['1001']
    row['observation']['digest']=control['digest']
    row['metrics']=dict(phases={},io={},working_set={})
    ref=replace(retained_reference(),artifact_id=90,run_id=1,workflow_sha='c'*40,
        harness_sha='e'*40,producer_job='digest-test',name='digest-test',archive_sha256='d'*64)
    return row,ref


def accept(audit,authority,audit_ref):
    digest,digest_ref=digest_fixture(audit)
    return r.accept_year(audit['saved'],audit,digest,authority=authority,
        candidate=r.ArtifactRef.from_dict(audit['binding']['candidate']),
        audit_proof=audit_ref,digest_proof=digest_ref,previous_acceptance=None,
        producer=dict(harness_sha='e'*40,workflow_sha='c'*40,run_id=1,
            job='accept-test',stage='accept-year'))


def test_retained_acceptance_binds_the_actual_member_sha_after_publish_reload(retained,tmp_path):
    dest,audit,authority,ref=retained
    row=accept(audit,authority,ref)
    assert row['proofs']['audit']['receipt_sha256']==MEMBER_SHA
    assert row['proofs']['audit']['artifact']==ref.to_dict()
    path=tmp_path/'accepted.json';r.publish_receipt(path,row)
    decoded=r.load_receipt(path);r.validate_year_acceptance(decoded,authority)
    assert r.file_hash(path)==r.receipt_hash(decoded)
    assert r.file_hash(dest/'audit.json')==MEMBER_SHA


def test_new_live_audit_can_publish_reload_and_advance_without_hash_drift(retained,tmp_path):
    _dest,audit,authority,ref=retained
    audit=copy.deepcopy(audit)
    years=audit['observation']['audit']['new_irons_by_year']
    audit['observation']['audit']['new_irons_by_year']={int(k):v for k,v in years.items()}
    assert 9 in years or any(len(k)!=len(next(iter(years))) for k in years)
    audit['producer']=dict(harness_sha='e'*40,workflow_sha='c'*40,run_id=1,
        job='new-audit-test',stage='audit')
    ref=replace(ref,artifact_id=91,run_id=1,workflow_sha='c'*40,harness_sha='e'*40,
        producer_job='new-audit-test',name='new-audit-test',archive_sha256='d'*64)
    dest=tmp_path/'new-audit';r.publish_receipt(dest/'audit.json',audit)
    decoded=runner._small({'audit':dest},'audit','audit.json',ref,authority)
    r.validate_verification(decoded,authority,kind='audit',binding=decoded['binding'])
    accepted=accept(decoded,authority,ref)
    path=tmp_path/'year.json';r.publish_receipt(path,accepted)
    r.validate_year_acceptance(r.load_receipt(path),authority)
    assert accepted['proofs']['audit']['receipt_sha256']==r.file_hash(dest/'audit.json')


@pytest.mark.parametrize('field,value',[
    ('artifact_id',12148235362),('run_id',39152488568),('archive_sha256','0'*64),
    ('archive_bytes',35606),('name','another-audit'),
])
def test_noncanonical_compatibility_requires_every_retained_artifact_pin(retained,field,value):
    dest,_row,authority,ref=retained
    with pytest.raises(ValueError):
        runner._small({'audit':dest},'audit','audit.json',replace(ref,**{field:value}),authority)


@pytest.mark.parametrize('damage',['canonical-rewrite','whitespace','control','count','duplicate-key'])
def test_retained_byte_proof_rejects_reserialization_or_tampering(retained,damage):
    dest,row,authority,ref=retained;path=dest/'audit.json'
    if damage=='whitespace':path.write_bytes(path.read_bytes()+b' ')
    elif damage=='duplicate-key':path.write_bytes(path.read_bytes().replace(b'{',b'{"schema":"duplicate",',1))
    else:
        if damage=='control':row['original_checkpoint']+=' '
        elif damage=='count':row['observation']['counters']['next_person']+=1
        path.write_bytes(r.receipt_bytes(row))
    with pytest.raises(ValueError):runner._small({'audit':dest},'audit','audit.json',ref,authority)


def test_recomputed_semantic_digest_cannot_replace_physical_retained_proof(retained):
    _dest,audit,authority,ref=retained
    accepted=accept(audit,authority,ref)
    accepted['proofs']['audit']['receipt_sha256']=CONTENT_SHA
    with pytest.raises(ValueError,match='digest'):
        r.validate_year_acceptance(accepted,authority)


def test_proof_workflow_requires_actual_retained_audit_download(tmp_path):
    import yaml
    workflow=yaml.safe_load((Path(__file__).resolve().parents[2]/runner.PROOF_WORKFLOW).read_text())
    steps=workflow['jobs']['harness-tests']['steps']
    step=next((s for s in steps if s.get('name')=='Authenticate retained mature audit handoff'),None)
    assert step is not None,'fresh proof must reuse and authenticate the actual mature audit'
    assert not step.get('continue-on-error',False)
    assert step['env']['GH_TOKEN']=='${{ github.token }}'
    # Exercise the actual timeout/pipefail/copy script. Only the external
    # authenticated CLI process is replaced; its arguments and exit contract
    # must propagate, and failures must not publish a successful check.
    executable=tmp_path/'bin/python';executable.parent.mkdir()
    executable.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
Path('called.json').write_text(json.dumps(sys.argv[1:]))
status=int(os.environ['HANDOFF_TEST_STATUS'])
if status:raise SystemExit(status)
path=Path('evidence/retained-audit/output/retained-audit-check.json')
path.parent.mkdir(parents=True);path.write_text('byte-proof')
''')
    executable.chmod(0o755)
    for status in (0,1,124):
        root=tmp_path/str(status);(root/'evidence').mkdir(parents=True)
        result=subprocess.run(['bash','-c',step['run']],cwd=root,capture_output=True,text=True,
            env=dict(os.environ,PATH=str(executable.parent)+os.pathsep+os.environ['PATH'],
                HANDOFF_TEST_STATUS=str(status)),timeout=10)
        assert json.loads((root/'called.json').read_text())==[
            '-m','simulation.continuation_checkpoint_ci','--job','retained-audit']
        assert result.returncode==status
        published=root/'evidence/retained-audit-check.json'
        assert published.exists()==(status==0)
        if status==0:assert published.read_text()=='byte-proof'


def test_retained_proof_consumes_real_archive_without_any_world_work(retained,tmp_path,monkeypatch):
    from simulation import continuation_checkpoint_ci as ci
    assert hasattr(ci,'retained_audit'),'retained audit proof entry point missing'
    _dest,_row,_authority,ref=retained
    archive=Path(__file__).with_name('fixtures')/'continuation-audit1001.zip'
    seen=[]
    def download(actual,destination,*,members):
        assert actual==ref and members=={'audit.json'}
        seen.append(actual)
        artifacts.extract(archive,destination,members)
    def forbidden(*args,**kwargs):raise AssertionError('retained proof repeated World work')
    monkeypatch.setattr(ci.runner,'download_ref',download)
    monkeypatch.setattr(ci.checkpoint,'open_lazy_world_session',forbidden)
    monkeypatch.setattr(ci.checkpoint.Simulation,'run',forbidden)
    root=tmp_path/'proof';ci.retained_audit(root)
    check=r.load_receipt(root/'output/retained-audit-check.json')
    assert seen==[ref] and check['artifact']==ref.to_dict()
    assert check['member_sha256']==MEMBER_SHA and check['canonical_sha256']==CONTENT_SHA
    assert check['input_preserved'] is True and check['full_original_control_match'] is True
