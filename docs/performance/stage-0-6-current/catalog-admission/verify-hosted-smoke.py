"""Offline recorded-evidence verification; never impersonates hosted execution."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from simulation import stage_0_6_catalog_admission as admission
from simulation import stage_0_6_genesis_checkpoint as c
from simulation import stage_0_6_genesis_resume as resume
from simulation import stage_0_6_genesis_transport as transport


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata',type=Path,required=True);p.add_argument('--archives',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();root=Path.cwd()
    meta=json.loads(args.metadata.read_text());run=meta['run'];jobs=meta['jobs']['jobs']
    assert run['id']==43916382557 and run['head_sha']=='43b9fbb273cbcb658fbfde0fb6996d02ae456629'
    assert run['status']=='completed' and run['conclusion']=='success'
    assert {j['name'] for j in jobs if j['conclusion']=='skipped'}=={'source-digest','capture','catalog'}
    assert all(j['conclusion'] in ('success','skipped') for j in jobs)
    receipts={};refs={};archives=[]
    for a in meta['artifacts']['artifacts']:
        archive=args.archives/f"{a['id']}.zip"
        assert archive.stat().st_size==a['size_in_bytes'] and c.file_hash(archive)==a['digest'][7:]
        archives.append(dict(id=a['id'],bytes=a['size_in_bytes'],sha256=a['digest'][7:],name=a['name']))
        if a['name'].startswith(('checkpoint-','database-')):
            kind,mode,stage,head,attempt=a['name'].split('-')
            refs[a['id']]=transport.authenticate(a,run,jobs,name=a['name'],job=c.JOB[stage],head=head,run_id=run['id'])
            if kind=='checkpoint':
                with zipfile.ZipFile(archive) as z:
                    assert z.namelist()==['checkpoint.json'];value=json.loads(z.read('checkpoint.json'))
                c.validate(value,require_remote=True)
                resume.match_receipt_reference(value,refs[a['id']],mode='smoke',stage=stage)
                receipts[stage]=value
    assert set(receipts)=={'rebase','after_digest','proofs','measure','fresh_restore'}
    engine,blobs=resume.fence(root);resume.compatible(root,run['head_sha'])
    fresh=receipts['fresh_restore'];ctx=fresh['context'];transition=admission.cut(fresh)
    assert transition==receipts['rebase'] and ctx['runtime_tree']==engine==resume.RUNTIME
    assert ctx['critical_blobs']==blobs
    parent=transition['parent']['receipt'];admission.validate_prior(root,parent)
    pair=admission.contract(root)['catalogs']['smoke']
    assert c.receipt_hash(parent)==pair['receipt_sha256']
    assert transition['metrics']['catalog_admission']['contract_sha256']==c.file_hash(root/admission.CONTRACT)
    assert all(v['context']==ctx for v in receipts.values())
    acceptance=resume.evaluate_acceptance(fresh,'smoke')
    for stage in ('rebase','proofs','measure'):
        v=receipts[stage];assert v['data_ref']==refs[v['data_ref']['artifact_id']]
        with zipfile.ZipFile(args.archives/f"{v['data_ref']['artifact_id']}.zip") as z:
            assert z.namelist()==['candidate.sqlite']
            assert z.getinfo('candidate.sqlite').file_size==v['database']['bytes']
            with z.open('candidate.sqlite') as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==v['database']['sha256']
    gate=next(a for a in archives if a['name'].startswith('resume-evidence-gate-'))
    with zipfile.ZipFile(args.archives/f"{gate['id']}.zip") as z:
        details=json.loads(z.read('resume-work/runtime.json'));green=json.loads(z.read('resume-work/green-reuse.json'))
        xml=ET.fromstring(z.read('resume-tests/harness.xml'))
    assert c.receipt_hash(details)==ctx['execution_runtime']['signature']
    resume.check_software(ctx['execution_runtime'])
    assert green['green_run']==resume.GREEN_RUN and green['runtime_tree']==engine
    counts={k:sum(int(s.get(k,0)) for s in xml.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    assert counts==dict(tests=399,failures=0,errors=0,skipped=0)
    recovery_artifact=next(a for a in archives if a['name'].startswith('resume-evidence-smoke-rebase-'))
    with zipfile.ZipFile(args.archives/f"{recovery_artifact['id']}.zip") as z:
        recovery=json.loads(z.read('recovery-work/recovery.json'))
    assert recovery['status']=='passed' and recovery['worker_exit']==77
    assert recovery['retained_stage']=='catalog' and recovery['receipt_sha256']==pair['receipt_sha256']
    assert recovery['database_sha256']==pair['database']['sha256']
    result=dict(schema='ate-authenticated-admitted-smoke/1',run_id=run['id'],head=run['head_sha'],engine=engine,
        critical_paths=len(blobs),scope=__doc__,harness=counts,hosted_runtime=ctx['execution_runtime'],
        original_catalog_sha256=pair['receipt_sha256'],admission=transition['metrics']['catalog_admission'],
        recovery=recovery,acceptance=acceptance,restored=fresh['metrics']['restored'],archives=archives,
        mature_status='unmeasured')
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('run_id','engine','harness','acceptance','restored','mature_status')},indent=2))


if __name__=='__main__':main()
