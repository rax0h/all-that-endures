"""Authenticate completed checkpoint producers independently of later failures."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time
from urllib.error import HTTPError
import zipfile
from simulation import checkpoint_artifacts as github
from simulation import stage_0_6_genesis_checkpoint as c
from simulation.stage_0_6_retained_producer import _timestamp
from simulation.stage_0_6_retained_transport import _stream_archive,_signed_url

BRANCH='sol/durable-proof-map'
DATA_STEP='Publish closed checkpoint database'
SEAL_STEP='Seal checkpoint provenance'
METADATA_STEP='Publish sealed checkpoint metadata'


def read_uploaded_artifact(artifact_id):
    """Read back a just-completed upload without repeating its stage on a 404."""
    c.integer(artifact_id,'uploaded artifact id',1)
    for attempt in range(4):
        try:
            value=github._api(f'/actions/artifacts/{artifact_id}')
            if type(value) is not dict or type(value.get('id')) is not int or value['id']!=artifact_id:
                raise ValueError('uploaded artifact readback identity differs')
            return value
        except HTTPError as exc:
            if exc.code!=404 or attempt==3:raise
            time.sleep(2**attempt)


def _publication(job,created,*,kind,mode,stage,attempt):
    if job.get('status')!='completed' or job.get('conclusion') not in ('success','failure','cancelled','timed_out'):return False
    if 'run_attempt' in job and (type(job['run_attempt']) is not int or job['run_attempt']!=attempt):return False
    steps=job.get('steps',[])
    if type(steps) is not list:return False
    found={}
    needed_data=kind=='database' or stage in c.WRITES and not (stage=='source' and mode=='mature')
    for name in (DATA_STEP,SEAL_STEP,METADATA_STEP):
        matches=[s for s in steps if s.get('name')==name]
        required=name!=DATA_STEP or needed_data
        if len(matches)>1 or required and len(matches)!=1:return False
        if not required:continue
        step=matches[0]
        if step.get('status')!='completed' or step.get('conclusion')!='success':return False
        if type(step.get('number')) is not int or step['number']<1:return False
        found[name]=step
    ordered=([found[DATA_STEP]] if needed_data else [])+[found[SEAL_STEP],found[METADATA_STEP]]
    prior_number=0;prior_time=_timestamp(job.get('started_at'))
    for step in ordered:
        start,end=_timestamp(step.get('started_at')),_timestamp(step.get('completed_at'))
        if not (prior_number<step['number'] and prior_time<=start<=end<=_timestamp(job.get('completed_at'))):return False
        prior_number,prior_time=step['number'],end
    upload=found[DATA_STEP] if kind=='database' else found[METADATA_STEP]
    return _timestamp(upload.get('started_at'))<=created<=_timestamp(upload.get('completed_at'))


def name_for(kind,mode,stage,head,attempt):
    if kind not in ('checkpoint','database') or mode not in ('smoke','mature') or stage not in c.ORDER:raise ValueError('invalid checkpoint artifact name')
    c.hexadecimal(head,40,'artifact head');c.integer(attempt,'attempt',1)
    return f'{kind}-{mode}-{stage}-{head}-{attempt}'


def reference(artifact,*,name,job,head,run_id):
    if type(artifact) is not dict:raise ValueError('missing artifact')
    origin=artifact.get('workflow_run',{})
    if (artifact.get('name')!=name or artifact.get('expired') is not False or origin.get('id')!=run_id
        or origin.get('head_sha')!=head or origin.get('head_branch')!=BRANCH):raise ValueError('checkpoint artifact origin differs')
    c.integer(artifact.get('id'),'artifact id',1);c.integer(artifact.get('size_in_bytes'),'archive size',1)
    digest=artifact.get('digest','')
    if type(digest) is not str or not digest.startswith('sha256:'):raise ValueError('missing artifact digest')
    c.hexadecimal(digest[7:],64,'artifact digest')
    return dict(kind='github',artifact_id=artifact['id'],run_id=run_id,head_sha=head,name=name,job=job,
        archive_sha256=digest[7:],archive_bytes=artifact['size_in_bytes'],expires_at=artifact['expires_at'])


def authenticate(artifact,run,jobs,*,name,job,head,run_id,now=None):
    c.integer(run_id,'run id',1);c.hexadecimal(head,40,'producer head')
    if (type(run) is not dict or run.get('id')!=run_id or run.get('head_sha')!=head
        or run.get('head_branch')!=BRANCH or run.get('path')!=c.WORKFLOW
        or run.get('event') not in ('push','workflow_dispatch')
        or run.get('status') not in ('in_progress','completed')):raise ValueError('checkpoint run differs')
    result=reference(artifact,name=name,job=job,head=head,run_id=run_id)
    match=re.fullmatch('(checkpoint|database)-(smoke|mature)-('+ '|'.join(c.ORDER)+')-'+re.escape(head)+r'-([1-9][0-9]*)',name)
    if match is None:raise ValueError('invalid checkpoint producer name/attempt')
    kind,mode,stage,attempt=match.groups();attempt=int(attempt)
    if job!=c.JOB[stage] or kind=='database' and stage not in c.WRITES:raise ValueError('artifact stage/producer role differs')
    created=_timestamp(artifact.get('created_at'));expires=_timestamp(artifact.get('expires_at'))
    now=datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or not created<expires or now.astimezone(timezone.utc)>=expires:raise ValueError('checkpoint expired')
    matches=[x for x in jobs if type(x) is dict and x.get('name')==job and x.get('head_sha')==head
        and _publication(x,created,kind=kind,mode=mode,stage=stage,attempt=attempt)]
    if len(matches)!=1:raise ValueError('checkpoint requires one completed authoritative publication')
    return result


def extract(archive,destination,*,member,member_bytes,archive_bytes,archive_sha256):
    archive,destination=Path(archive),Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
    if member not in ('checkpoint.json','candidate.sqlite'):raise ValueError('invalid checkpoint member')
    if member_bytes is not None:c.integer(member_bytes,'member size',1)
    c.integer(archive_bytes,'archive size',1);c.hexadecimal(archive_sha256,64,'archive hash')
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size!=archive_bytes or c.file_hash(archive)!=archive_sha256:raise ValueError('checkpoint archive differs')
    limit=c.MAX_METADATA if member=='checkpoint.json' else member_bytes
    if limit is None:raise ValueError('database extraction requires exact size')
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        if len(entries)!=1 or entries[0].filename!=member:raise ValueError('checkpoint member inventory differs')
        entry=entries[0]
        if (entry.is_dir() or stat.S_IFMT(entry.external_attr>>16) not in (0,stat.S_IFREG)
            or entry.flag_bits&1 or not 0<entry.file_size<=limit
            or member_bytes is not None and entry.file_size!=member_bytes):raise ValueError('unsafe checkpoint member')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.parent.is_symlink():raise ValueError('symlink checkpoint parent')
        with tempfile.TemporaryDirectory(prefix='.checkpoint-extract-',dir=destination.parent) as directory:
            pending=Path(directory)/member;size=0
            with z.open(entry) as source,pending.open('xb') as target:
                while True:
                    block=source.read(min(1024*1024,limit-size+1))
                    if not block:break
                    size+=len(block)
                    if size>limit:raise ValueError('checkpoint decompression exceeds cap')
                    target.write(block)
            if size!=entry.file_size:raise ValueError('checkpoint decompressed length differs')
            destination.mkdir()
            try:pending.replace(destination/member)
            except BaseException:
                shutil.rmtree(destination)
                raise


def inspect_reference(ref,*,compatible):
    c.check_ref(ref,remote=True)
    if ref.get('kind')!='github':raise ValueError('requires GitHub artifact reference')
    compatible(ref['head_sha'])
    artifact=github._api(f'/actions/artifacts/{ref["artifact_id"]}')
    run=github._api(f'/actions/runs/{ref["run_id"]}')
    jobs=github._pages(f'/actions/runs/{ref["run_id"]}/jobs?filter=all','jobs')
    actual=authenticate(artifact,run,jobs,name=ref['name'],job=ref['job'],head=ref['head_sha'],run_id=ref['run_id'])
    if actual!=ref:raise ValueError('checkpoint reference changed')
    return actual


def restore(ref,destination,*,member,member_bytes=None,compatible):
    ref=inspect_reference(ref,compatible=compatible)
    ceiling=c.MAX_METADATA*2 if member=='checkpoint.json' else member_bytes+16*1024*1024
    if ref['archive_bytes']>ceiling:raise ValueError('checkpoint archive exceeds size ceiling')
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    required=ref['archive_bytes']+(member_bytes or c.MAX_METADATA)+64*1024*1024
    if shutil.disk_usage(destination.parent).free<required:raise ValueError('insufficient checkpoint restore headroom')
    with tempfile.TemporaryDirectory(prefix='.checkpoint-download-',dir=destination.parent) as directory:
        archive=Path(directory)/'artifact.zip'
        _stream_archive(_signed_url(ref['artifact_id']),archive,
            archive_sha256=ref['archive_sha256'],archive_bytes=ref['archive_bytes'])
        extract(archive,destination,member=member,member_bytes=member_bytes,
            archive_bytes=ref['archive_bytes'],archive_sha256=ref['archive_sha256'])
    return ref
