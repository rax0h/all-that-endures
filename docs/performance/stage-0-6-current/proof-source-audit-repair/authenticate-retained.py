"""Authenticate historical checkpoint evidence without admitting a new engine."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from simulation import stage_0_6_genesis_checkpoint as c
from simulation import stage_0_6_genesis_transport as t

root=Path(sys.argv[1]).resolve()
evidence=Path(sys.argv[2]).resolve()
raw=json.loads((evidence/'metadata.json').read_text())
run=raw['run'];jobs={j['name']:j for j in raw['jobs']['jobs']}
artifacts={a['id']:a for a in raw['artifacts']['artifacts']}
authenticated={}
assert run['id']==43918798385 and run['head_sha']=='71967a3d9a3713a038bc5ec360094945bf312700'
assert run['status']=='completed' and run['conclusion']=='failure'

def archive(artifact_id,job_name):
    a=artifacts[artifact_id];job=jobs[job_name];path=evidence/(str(artifact_id)+'.zip')
    assert not a['expired'] and a['workflow_run']['id']==run['id']
    assert a['workflow_run']['head_sha']==run['head_sha']
    assert job['conclusion']=='success' or job_name=='proofs'
    assert job['started_at']<=a['created_at']<=a['updated_at']<=job['completed_at']
    assert datetime.datetime.fromisoformat(a['expires_at'].replace('Z','+00:00'))>datetime.datetime.now(datetime.timezone.utc)
    assert path.stat().st_size==a['size_in_bytes']
    assert 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()==a['digest']
    if a['name'].startswith(('checkpoint-','database-')):
        authenticated[artifact_id]=t.authenticate(a,run,raw['jobs']['jobs'],name=a['name'],job=job_name,head=run['head_sha'],run_id=run['id'])
    return a,path

def receipt(artifact_id,job_name):
    a,path=archive(artifact_id,job_name)
    with zipfile.ZipFile(path) as z:
        assert z.namelist()==['checkpoint.json']
        row=json.loads(z.read('checkpoint.json'))
    c.validate(row,require_remote=True)
    assert row['producer']==dict(run_id=run['id'],head_sha=run['head_sha'],job=job_name,attempt=1)
    return row

after=receipt(14267625292,'after-digest')
rebase=receipt(14260383532,'rebase')
assert after['parent']==dict(sha256=c.receipt_hash(rebase),receipt=rebase)
assert after['database']==rebase['database'] and after['data_ref']==rebase['data_ref']
assert after['context']==rebase['context']
assert after['baseline_digest']=='57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed'
assert after['database']==dict(bytes=29409034240,format=6,generation=0,seed=843000,year=1001,
    sha256='b1c7ffcd9379d246002d9052065a44d5de539606bb00c43ef7997785962521a5',store_identity='6d0b5191-fd61-4bb8-845a-4dddbd0e3213')
data=artifacts[after['data_ref']['artifact_id']]
assert t.authenticate(data,run,raw['jobs']['jobs'],name=data['name'],job='rebase',head=run['head_sha'],run_id=run['id'])==after['data_ref']
assert data['id']==14261110486 and data['size_in_bytes']==after['data_ref']['archive_bytes']
assert data['digest']=='sha256:'+after['data_ref']['archive_sha256'] and not data['expired']
assert data['name']==after['data_ref']['name'] and data['expires_at']==after['data_ref']['expires_at']
assert data['workflow_run']['id']==run['id'] and data['workflow_run']['head_sha']==run['head_sha']
assert jobs['rebase']['started_at']<=data['created_at']<=data['updated_at']<=jobs['rebase']['completed_at']
def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
assert git('rev-parse',run['head_sha']+':simulation/ate_sim')==after['context']['runtime_tree']
for name,blob in after['context']['critical_blobs'].items():
    assert git('rev-parse',run['head_sha']+':'+name)==blob,name
subprocess.run(['git','merge-base','--is-ancestor',run['head_sha'],'HEAD'],cwd=root,check=True)
contract_bytes=subprocess.check_output(['git','show',run['head_sha']+':simulation/stage_0_6_catalog_admission.json'],cwd=root)
contract=json.loads(contract_bytes)
cut=rebase['metrics']['catalog_admission']
assert cut['contract_sha256']==hashlib.sha256(contract_bytes).hexdigest()
old=rebase['parent']['receipt'];pair=contract['catalogs']['mature']
assert c.receipt_hash(old)==pair['receipt_sha256']
assert old['context']==pair['context'] and old['database']==pair['database'] and old['data_ref']==pair['data_ref']
source=old
while source['stage']!='source_digest':source=source['parent']['receipt']
assert source['metrics']['source_control']==pair['source_control']
assert after['context']['execution_runtime']['signature']=='a6cc6e5e404ca8bd7cfdf50e08b3f0c163405fb3941b77d83921f492213b3982'
for artifact_id,job_name in ((14261435674,'rebase'),(14267210493,'after-digest'),(14285020598,'proofs')):
    archive(artifact_id,job_name)
with zipfile.ZipFile(evidence/'14285020598.zip') as z:
    assert json.loads(z.read('failure.json'))['prior_checkpoint']==authenticated[14267625292]
with zipfile.ZipFile(evidence/'14267210493.zip') as z:
    assert json.loads(z.read('input-reference.json'))['metadata_artifact']==authenticated[14260383532]
print(json.dumps(dict(run_id=run['id'],head_sha=run['head_sha'],qualified_engine=after['context']['runtime_tree'],
    after_digest_receipt_sha256=c.receipt_hash(after),rebase_receipt_sha256=c.receipt_hash(rebase),
    critical_paths_checked=len(after['context']['critical_blobs']),database=after['database'],data_ref=after['data_ref'],
    original_catalog_cut_preserved=cut,source_control_unchanged=True,
    raw_database_redownloaded=False,new_engine_admitted=False),indent=2))
