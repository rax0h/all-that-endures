"""Artifact origin and extraction are checked before any checkpoint is trusted."""
import importlib
import json
import zipfile
import pytest


def module():
    assert importlib.util.find_spec('simulation.checkpoint_artifacts'), 'artifact authentication missing'
    return importlib.import_module('simulation.checkpoint_artifacts')


def fixture():
    artifact = {'name':'candidate', 'expired':False, 'digest':'sha256:'+'a'*64,
        'workflow_run':{'id':7, 'head_sha':'b'*40}, 'created_at':'2026-10-15T01:01:00Z'}
    run = {'id':7, 'head_sha':'b'*40, 'path':'.github/workflows/checkpointed-upgrade-validation.yml'}
    jobs = [{'name':'construct', 'conclusion':'success', 'started_at':'2026-10-15T01:00:00Z',
             'completed_at':'2026-10-15T01:02:00Z'}]
    expected = dict(run_id=7, workflow_sha='b'*40, name='candidate', job='construct',
                    workflow_path=run['path'])
    return artifact, run, jobs, expected


def test_authenticate_successful_producer():
    a,r,j,e = fixture()
    assert module().authenticate(a,r,j,**e) == 'a'*64


@pytest.mark.parametrize('change', ['run', 'commit', 'workflow', 'name', 'expired', 'digest', 'job', 'time'])
def test_reject_foreign_or_incomplete_producer(change):
    a,r,j,e = fixture()
    if change=='run': a['workflow_run']['id']=8
    elif change=='commit': r['head_sha']='c'*40
    elif change=='workflow': r['path']='foreign.yml'
    elif change=='name': a['name']='storage'
    elif change=='expired': a['expired']=True
    elif change=='digest': a['digest']='sha256:unknown'
    elif change=='job': j[0]['conclusion']='failure'
    elif change=='time': j[0]['completed_at']='2026-10-15T01:00:30Z'
    with pytest.raises(ValueError): module().authenticate(a,r,j,**e)


@pytest.mark.parametrize('members', [['../escape'], ['/absolute'], ['candidate.sqlite','extra'],
                                     ['candidate.sqlite','candidate.sqlite']])
def test_extract_rejects_unexpected_duplicate_or_traversing_members(tmp_path,members):
    archive=tmp_path/'input.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for member in members: z.writestr(member,b'data')
    with pytest.raises(ValueError): module().extract(archive,tmp_path/'out',{'candidate.sqlite','manifest.json'})
    assert not (tmp_path/'out').exists()


def test_extract_exact_files_no_overwrite(tmp_path):
    archive=tmp_path/'input.zip'
    with zipfile.ZipFile(archive,'w') as z: z.writestr('receipt.json',b'{}')
    module().extract(archive,tmp_path/'out',{'receipt.json'})
    assert json.loads((tmp_path/'out'/'receipt.json').read_text()) == {}
    with pytest.raises(FileExistsError): module().extract(archive,tmp_path/'out',{'receipt.json'})
