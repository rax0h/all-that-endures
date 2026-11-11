import copy
import importlib
import importlib.util
import hashlib
from datetime import datetime,timezone
import zipfile
import pytest


def api():
    name='simulation.stage_0_6_genesis_transport'
    assert importlib.util.find_spec(name) is not None,'checkpoint transport is missing'
    return importlib.import_module(name)


def metadata():
    artifact=dict(id=10,name='checkpoint-smoke-capture-'+'a'*40+'-1',expired=False,size_in_bytes=100,
        digest='sha256:'+'b'*64,created_at='2026-11-10T01:02:00Z',expires_at='2026-12-10T01:02:00Z',
        workflow_run=dict(id=20,head_sha='a'*40,head_branch='sol/durable-proof-map'))
    run=dict(id=20,head_sha='a'*40,head_branch='sol/durable-proof-map',event='workflow_dispatch',
        path='.github/workflows/stage-0-6-resumable-proof-genesis.yml',status='completed',conclusion='failure')
    jobs=[dict(name='capture',head_sha='a'*40,status='completed',conclusion='success',
        started_at='2026-11-10T01:00:00Z',completed_at='2026-11-10T01:03:00Z',run_attempt=1,
        steps=[dict(name='Publish closed checkpoint database',number=5,status='completed',conclusion='success',started_at='2026-11-10T01:00:10Z',completed_at='2026-11-10T01:00:50Z'),dict(name='Seal checkpoint provenance',number=6,status='completed',conclusion='success',started_at='2026-11-10T01:00:51Z',completed_at='2026-11-10T01:01:00Z'),dict(name='Publish sealed checkpoint metadata',number=7,status='completed',conclusion='success',started_at='2026-11-10T01:01:01Z',completed_at='2026-11-10T01:02:10Z')])]
    return artifact,run,jobs


def auth(a,r,j):
    return api().authenticate(a,r,j,name=a['name'],job='capture',head='a'*40,run_id=20,
        now=datetime(2026,11,11,tzinfo=timezone.utc))


def test_successful_checkpoint_job_survives_later_workflow_failure():
    a,r,j=metadata();ref=auth(a,r,j)
    assert ref['artifact_id']==10 and ref['archive_sha256']=='b'*64


@pytest.mark.parametrize('damage',['job_failed','job_head','duplicate_job','expiry','artifact_head','workflow','branch','created','digest','size'])
def test_untrusted_checkpoint_producer_is_rejected(damage):
    a,r,j=metadata()
    if damage=='job_failed':
        j[0]['conclusion']='failure';j[0]['steps'][-1]['conclusion']='failure'
    elif damage=='job_head':j[0]['head_sha']='c'*40
    elif damage=='duplicate_job':j*=2
    elif damage=='expiry':a['expires_at']='2026-11-10T03:00:00Z'
    elif damage=='artifact_head':a['workflow_run']['head_sha']='c'*40
    elif damage=='workflow':r['path']='other.yml'
    elif damage=='branch':r['head_branch']='main'
    elif damage=='created':a['created_at']='2026-11-10T01:04:00Z'
    elif damage=='digest':a['digest']='bad'
    else:a['size_in_bytes']=True
    with pytest.raises(ValueError):auth(a,r,j)


def test_exact_bounded_archive_rejects_extra_or_duplicate_members(tmp_path):
    m=api();archive=tmp_path/'data.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('candidate.sqlite',b'checked')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    m.extract(archive,tmp_path/'good',member='candidate.sqlite',member_bytes=7,archive_bytes=archive.stat().st_size,archive_sha256=digest)
    assert (tmp_path/'good/candidate.sqlite').read_bytes()==b'checked'
    with zipfile.ZipFile(archive,'a') as z:z.writestr('extra',b'bad')
    with pytest.raises(ValueError):
        m.extract(archive,tmp_path/'bad',member='candidate.sqlite',member_bytes=7,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert not (tmp_path/'bad').exists()


@pytest.mark.parametrize('conclusion',['failure','cancelled','timed_out'])
def test_committed_checkpoint_survives_post_publication_cleanup_failure(conclusion):
    a,r,j=metadata();j[0]['conclusion']=conclusion
    assert auth(a,r,j)['artifact_id']==10


@pytest.mark.parametrize('damage',['seal_failed','metadata_cancelled','data_failed','step_order','duplicate_step','created_outside_step','wrong_attempt','in_progress'])
def test_checkpoint_commit_requires_exact_successful_publication_steps(damage):
    a,r,j=metadata();steps=j[0]['steps']
    if damage=='seal_failed':steps[1]['conclusion']='failure'
    elif damage=='metadata_cancelled':steps[2]['conclusion']='cancelled'
    elif damage=='data_failed':steps[0]['conclusion']='failure'
    elif damage=='step_order':steps[0]['number']=8
    elif damage=='duplicate_step':steps.append(copy.deepcopy(steps[2]))
    elif damage=='created_outside_step':a['created_at']='2026-11-10T01:00:00Z'
    elif damage=='wrong_attempt':j[0]['run_attempt']=2
    else:j[0]['status']='in_progress'
    with pytest.raises(ValueError):auth(a,r,j)


def test_data_artifact_binds_its_successful_upload_step():
    a,r,j=metadata();a['name']=a['name'].replace('checkpoint-','database-',1)
    a['created_at']='2026-11-10T01:00:30Z';j[0]['conclusion']='failure'
    assert auth(a,r,j)['artifact_id']==10


@pytest.mark.parametrize('mode,stage,job',[('smoke','source_digest','source-digest'),('mature','source','gate')])
def test_read_only_metadata_does_not_require_a_new_database_upload(mode,stage,job):
    a,r,j=metadata();a['name']=f'checkpoint-{mode}-{stage}-'+('a'*40)+'-1';j[0]['name']=job
    j[0]['steps'][0]['conclusion']='skipped';j[0]['conclusion']='failure'
    assert api().authenticate(a,r,j,name=a['name'],job=job,head='a'*40,run_id=20,now=datetime(2026,11,11,tzinfo=timezone.utc))['artifact_id']==10
