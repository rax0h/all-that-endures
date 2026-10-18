"""Pinned one-stage mature continuation runner; no automatic stage advancement."""
import argparse
import base64
from contextlib import contextmanager, redirect_stdout
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import urllib.parse
import zipfile

import yaml

from simulation import checkpoint_artifacts as artifacts
from simulation import construction_mature_continue as original
from simulation import continuation_checkpoint as checkpoint
from simulation import continuation_receipts as r


WORKFLOW = '.github/workflows/stage-0-5-mature-continuation-stage.yml'
BRANCH = 'sol/stage-0-5-mature-continuation-stage'
PROOF_WORKFLOW = '.github/workflows/stage-0-5-continuation-proof.yml'
LAUNCH_SCHEMA = 'ate-validation-continuation-launch/1'
MARGIN = 8*1024**3
SMALL_SPACE = 64*1024**2
OUTPUT_FILES = {'audit':'audit.json','digest':'digest.json','accept-year':'year-verified.json',
    'accept-continuation':'continuation-verified.json','restore-values':'restore-values.json',
    'restore-digest':'restore-digest.json','accept-restore':'restore-verified.json'}
IMPLEMENTATION_FILES = (
    'simulation/continuation_receipts.py','simulation/continuation_checkpoint.py',
    'simulation/construction_mature_continuation_stages.py','simulation/continuation_checkpoint_ci.py',
    'simulation/checkpoint_artifacts.py','simulation/persistence_p5_long_validation.py',
    'simulation/run_long_history.py','simulation/construction_mature_continue.py',
    'simulation/long_history_scaling.py','simulation/tests/continuation_fixtures.py',
    'simulation/construction_checkpoint_ci.py',
    '.github/workflows/stage-0-5-continuation-proof.yml')
_SOURCE_IDENTITIES = set()


def mature_authority():
    publication = r.ArtifactRef(artifact_id=12049884660,run_id=38907665230,
        workflow_sha=original.PUBLISHED_WORKFLOW_SHA,workflow_path=original.publish.WORKFLOW,
        producer_job='mature-publish',name='construction-mature-published',
        archive_sha256='5ea709166d2bba7f7a22d614fed604f471973ae9ff757979a4148ff197c43382',
        archive_bytes=3910109453,harness_sha=original.PUBLISHED_HARNESS_SHA,
        runtime_sha=original.RUNTIME_SHA,runtime_tree=original.RUNTIME_TREE)
    files = original.PUBLISHED_FILES
    return r.Authority(checkpoint_sha256=files['checkpoint.json']['sha256'],
        checkpoint_bytes=files['checkpoint.json']['bytes'],context=original.CONTEXT,
        source_config=original.SOURCE_CONFIG,publication=publication,
        published_database_sha256=files['p5-long-complete.sqlite']['sha256'],
        published_database_bytes=files['p5-long-complete.sqlite']['bytes'],
        checkpoint_runtime_sha=original.RUNTIME_SHA,execution_runtime_sha=original.EXECUTION_RUNTIME_SHA,
        execution_runtime_tree=original.EXECUTION_RUNTIME_TREE,
        bootstrap_generation=original.CANDIDATE_PIN['captured_head'],
        store_identity=original.CANDIDATE_PIN['store_identity'],output_max_bytes=original.OUTPUT_MAX_BYTES)


def required_space(stage,input_bytes,archive_bytes,cap,*,before):
    if stage not in r.STAGES:
        raise ValueError('unknown continuation stage')
    for value in (input_bytes,archive_bytes,cap):r.integer(value,'disk size')
    if stage == 'save':
        peak = max(input_bytes+archive_bytes,input_bytes+2*cap) if before else 2*cap
    elif stage in ('audit','digest','restore-values','restore-digest'):
        peak = max(input_bytes+archive_bytes,3*input_bytes) if before else 2*input_bytes
    else:
        peak = 0
    return peak+MARGIN+SMALL_SPACE


def check_space(required,*,free=None):
    free = shutil.disk_usage('.').free if free is None else free
    if free < required:
        raise ValueError(f'need {required} bytes disk headroom; have {free}')


def upload_space(stage,result):
    size = result['database']['bytes'] if stage=='save' else 0
    r.integer(size,'upload allowance')
    return size+MARGIN+SMALL_SPACE


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT','1') != '1':
        raise ValueError('mature stage rerun requires inspection')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA'] or current.get('path') != WORKFLOW
            or current.get('head_branch') != BRANCH):
        raise ValueError('executing mature workflow differs')
    runs = {}
    for branch in (BRANCH,original.BRANCH):
        for row in artifacts._pages('/actions/runs?branch='+urllib.parse.quote(branch,safe=''),'workflow_runs'):
            runs[row['id']] = row
    if run_id not in runs:
        raise ValueError('current mature run missing')
    paths = {WORKFLOW,original.WORKFLOW}
    if any(row.get('path')==WORKFLOW and row.get('head_sha')==current['head_sha']
           and row['id']<run_id for row in runs.values()):
        raise ValueError('duplicate mature stage run')
    active = {'queued','in_progress','waiting','requested','pending'}
    if any(row['id']!=run_id and row.get('path') in paths and row.get('status') in active for row in runs.values()):
        raise ValueError('another active mature continuation must be inspected')


def input_roles(stage,year,authority):
    r.integer(year,'stage year')
    if year not in authority.source_config['milestones'] or stage not in r.STAGES:
        raise ValueError('unknown stage/year')
    second = year == authority.source_config['milestones'][1]
    if stage == 'save':return {'candidate','previous'} if second else set()
    if stage in ('audit','digest'):return {'candidate'}
    if stage == 'accept-year':return {'candidate','audit','digest'} | ({'previous'} if second else set())
    if not second:raise ValueError('final continuation/restore requires the last milestone')
    if stage == 'accept-continuation':return {'first','second','candidate'}
    if stage in ('restore-values','restore-digest'):return {'candidate','continuation'}
    return {'candidate','continuation','values','digest'}


def load_launch(path,*,stage,year):
    config = r.load_receipt(path)
    r.exact(config,('schema','stage','year','inputs','candidate_database','proof'),'launch')
    a = mature_authority()
    r.integer(config['year'],'launch year')
    if config['schema'] != LAUNCH_SCHEMA or config['stage'] != stage or config['year'] != year:
        raise ValueError('launch stage/year differs')
    roles = input_roles(stage,year,a)
    r.exact(config['inputs'],roles,'stage input roles')
    refs = {key:r.ArtifactRef.from_dict(value) for key,value in config['inputs'].items()}
    if any(ref.runtime_sha!=a.execution_runtime_sha or ref.runtime_tree!=a.execution_runtime_tree for ref in refs.values()):
        raise ValueError('input execution runtime differs')
    if config['proof'] is None:
        raise ValueError('fresh-runner proof is not pinned')
    proof = r.ArtifactRef.from_dict(config['proof'])
    if proof.runtime_sha != a.execution_runtime_sha or proof.runtime_tree != a.execution_runtime_tree:
        raise ValueError('proof execution runtime differs')
    if proof.workflow_path != PROOF_WORKFLOW or proof.producer_job != 'proof-summary' or proof.name != 'continuation-small-proof':
        raise ValueError('unexpected fresh-runner proof')
    database = config['candidate_database']
    if database is not None:
        r.exact(database,('name','bytes','sha256'),'launch candidate database')
        r.integer(database['bytes'],'launch database bytes',1)
        r.hexadecimal(database['sha256'],64,'launch database digest')
        if database['name'] != 'candidate.sqlite' or database['bytes'] > a.output_max_bytes:
            raise ValueError('launch database bounds differ')
    return config,refs,proof


def verify_source_identity(ref):
    key = (ref.workflow_sha,ref.workflow_path,ref.harness_sha,ref.runtime_sha,ref.runtime_tree)
    if key in _SOURCE_IDENTITIES:return
    content = artifacts._api('/contents/'+ref.workflow_path+'?ref='+ref.workflow_sha)
    if content.get('encoding') != 'base64':raise ValueError('workflow source is not base64')
    workflow = yaml.safe_load(base64.b64decode(content['content'],validate=False))
    env = workflow.get('env',{})
    harness = env.get('HARNESS_SHA')
    if harness == '${{ github.sha }}':harness = ref.workflow_sha
    if harness != ref.harness_sha or env.get('RUNTIME_SHA') != ref.runtime_sha:
        raise ValueError('producing workflow harness/runtime pins differ')
    for sha in {ref.harness_sha,ref.runtime_sha}:
        tree = artifacts._api('/git/trees/'+sha+'?recursive=1')
        matches = [row.get('sha') for row in tree.get('tree',[]) if row.get('path')=='simulation/ate_sim' and row.get('type')=='tree']
        if tree.get('truncated') is not False or matches != [ref.runtime_tree]:
            raise ValueError('producing source runtime subtree differs')
    _SOURCE_IDENTITIES.add(key)


def authenticate_ref(ref,*,max_archive_bytes):
    started = time.monotonic()
    if ref.archive_bytes > max_archive_bytes:
        raise ValueError('declared archive exceeds stage cap')
    metadata = artifacts._api(f'/actions/artifacts/{ref.artifact_id}')
    run = artifacts._api(f'/actions/runs/{ref.run_id}')
    jobs = artifacts._pages(f'/actions/runs/{ref.run_id}/jobs?filter=all','jobs')
    digest = artifacts.authenticate(metadata,run,jobs,run_id=ref.run_id,workflow_sha=ref.workflow_sha,
        name=ref.name,job=ref.producer_job,workflow_path=ref.workflow_path)
    if (metadata.get('id') != ref.artifact_id or type(metadata.get('size_in_bytes')) is not int
            or metadata['size_in_bytes'] != ref.archive_bytes or digest != ref.archive_sha256):
        raise ValueError('artifact ID/archive size/digest differs')
    verify_source_identity(ref)
    checkpoint._phase('artifact_authenticated',artifact_id=ref.artifact_id,
        wall_seconds=time.monotonic()-started)
    return metadata


@contextmanager
def bounded_extraction(database_cap):
    """Guard the existing serial transport's public extraction seam, without changing it."""
    original_extract = artifacts.extract
    def extract(archive,destination,members):
        with zipfile.ZipFile(archive) as zipped:
            for info in zipped.infolist():
                limit = database_cap if info.filename in ('candidate.sqlite','p5-long-complete.sqlite') else r.METADATA_MAX_BYTES
                if info.file_size > limit:
                    raise ValueError('artifact member exceeds stage extraction bound')
        return original_extract(archive,destination,members)
    artifacts.extract = extract
    try:
        yield
    finally:
        artifacts.extract = original_extract


def download_ref(ref,destination,*,members,database_cap=0):
    meta_count = len(members)-len(set(members)&{'candidate.sqlite','p5-long-complete.sqlite'})
    maximum = database_cap+meta_count*r.METADATA_MAX_BYTES+(SMALL_SPACE if database_cap else 65536*len(members))
    authenticate_ref(ref,max_archive_bytes=maximum)
    with bounded_extraction(database_cap):
        proof = artifacts.download(destination,run_id=ref.run_id,artifact_id=ref.artifact_id,
            workflow_sha=ref.workflow_sha,workflow_path=ref.workflow_path,name=ref.name,
            job=ref.producer_job,members=set(members),expected_digest=ref.archive_sha256)
    if proof['archive_bytes'] != ref.archive_bytes:
        raise ValueError('downloaded archive size differs')
    return proof


def implementation_hashes():
    return {path:r.file_hash(path) for path in IMPLEMENTATION_FILES}


def check_source():
    head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    tree = subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()
    if (head != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != original.EXECUTION_RUNTIME_SHA
            or tree != original.EXECUTION_RUNTIME_TREE):
        raise ValueError('execution source/runtime differs from reviewed pin')
    original.check_helpers()
    return head


def producer(stage,job):
    return dict(harness_sha=os.environ['HARNESS_SHA'],workflow_sha=os.environ['GITHUB_SHA'],
        run_id=int(os.environ['GITHUB_RUN_ID']),job=job,stage=stage)


def _small(inputs,label,filename,ref,authority):
    directory = inputs[label]
    checkpoint._inventory(directory,{filename})
    row = r.load_receipt(directory/filename)
    r.match_producer(ref,row.get('producer',{}),authority)
    if not r.same(row.get('authority'),authority.to_dict()):
        raise ValueError('receipt original authority differs from expected checkpoint')
    if r.receipt_hash(row) != r.file_hash(directory/filename):
        raise ValueError('noncanonical receipt member bytes')
    return row


def execute_stage(stage,year,*,authority,inputs,refs,producer,output):
    """Transport is completed by the caller; local stages still recheck all file authority."""
    output = Path(output)
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    roles = input_roles(stage,year,authority)
    if set(refs) != roles:raise ValueError('unexpected authenticated input roles')
    if stage in ('audit','digest','restore-values','restore-digest'):
        saved = r.load_receipt(inputs['candidate']/'save.json')
        if type(saved.get('year')) is not int or saved['year'] != year:
            raise ValueError('saved input differs from requested milestone')
    previous = None
    if 'previous' in roles:
        previous = _small(inputs,'previous','year-verified.json',refs['previous'],authority)
        r.validate_year_acceptance(previous,authority)
    if stage == 'save':
        if previous is None:
            predecessor = dict(kind='publication',artifact=authority.publication.to_dict())
            source = inputs['publication']
        else:
            if not r.same(previous['binding']['candidate'],refs['candidate'].to_dict()):
                raise ValueError('save input differs from accepted predecessor')
            predecessor = dict(kind='year-verified',artifact=refs['previous'].to_dict(),
                receipt_sha256=r.receipt_hash(previous),receipt=previous)
            source = inputs['candidate']
        return checkpoint.save_year(source,output,authority=authority,year=year,predecessor=predecessor,producer=producer)
    if stage in ('audit','digest'):
        return getattr(checkpoint,stage+'_year')(inputs['candidate'],output/OUTPUT_FILES[stage],
            authority=authority,candidate=refs['candidate'],producer=producer)
    if stage in ('restore-values','restore-digest'):
        continued = _small(inputs,'continuation','continuation-verified.json',refs['continuation'],authority)
        return getattr(checkpoint,stage.replace('-','_'))(inputs['candidate'],output/OUTPUT_FILES[stage],
            authority=authority,candidate=refs['candidate'],producer=producer,continuation=continued)
    if stage == 'accept-year':
        audit = _small(inputs,'audit','audit.json',refs['audit'],authority)
        digest = _small(inputs,'digest','digest.json',refs['digest'],authority)
        if audit['binding']['year'] != year:raise ValueError('wrong acceptance milestone')
        result = r.accept_year(audit['saved'],audit,digest,authority=authority,candidate=refs['candidate'],
            audit_proof=refs['audit'],digest_proof=refs['digest'],previous_acceptance=previous,producer=producer)
    elif stage == 'accept-continuation':
        first = _small(inputs,'first','year-verified.json',refs['first'],authority)
        second = _small(inputs,'second','year-verified.json',refs['second'],authority)
        result = r.accept_continuation(first,second,authority=authority,producer=producer)
        if not r.same(result['final_binding']['candidate'],refs['candidate'].to_dict()):
            raise ValueError('final continuation artifact differs')
    else:
        continued = _small(inputs,'continuation','continuation-verified.json',refs['continuation'],authority)
        values = _small(inputs,'values','restore-values.json',refs['values'],authority)
        digest = _small(inputs,'digest','restore-digest.json',refs['digest'],authority)
        if not r.same(continued['final_binding']['candidate'],refs['candidate'].to_dict()):
            raise ValueError('restored candidate differs')
        result = r.accept_restore(values,digest,continuation=continued,
            proofs={key:refs[key] for key in ('values','digest','continuation')},producer=producer)
    r.publish_receipt(output/OUTPUT_FILES[stage],result)
    return result


MEMBERS = {'candidate':r.SAVED_MEMBERS,'previous':{'year-verified.json'},'audit':{'audit.json'},
    'digest':{'digest.json'},'first':{'year-verified.json'},'second':{'year-verified.json'},
    'continuation':{'continuation-verified.json'},'values':{'restore-values.json'}}


def fetch_stage_inputs(stage,year,*,root,authority,refs,database_cap=None):
    cap = authority.output_max_bytes if database_cap is None else database_cap
    r.integer(cap,'candidate extraction cap',1)
    if cap > authority.output_max_bytes:raise ValueError('candidate extraction cap exceeds authority')
    paths = {}
    for label,ref in refs.items():
        large = label == 'candidate' and stage in ('save','audit','digest','restore-values','restore-digest')
        if label == 'candidate' and not large:
            authenticate_ref(ref,max_archive_bytes=authority.output_max_bytes+2*r.METADATA_MAX_BYTES+SMALL_SPACE)
            continue
        members = {'restore-digest.json'} if stage=='accept-restore' and label=='digest' else MEMBERS[label]
        paths[label] = root/label
        download_ref(ref,paths[label],members=members,database_cap=cap if large else 0)
    return paths


def check_proof(ref,root):
    download_ref(ref,root/'proof',members={'proof.json'})
    row = r.load_receipt(root/'proof/proof.json')
    r.exact(row,('stage','passed','runtime_sha','runtime_tree','harness_sha','implementation_hashes',
        'restore_artifact','restore_receipt_sha256'),'fresh-runner proof')
    if (row.get('stage') != 'fresh-runner-continuation-proof' or row.get('passed') is not True
            or row.get('runtime_sha') != original.EXECUTION_RUNTIME_SHA
            or row.get('runtime_tree') != original.EXECUTION_RUNTIME_TREE
            or row.get('harness_sha') != ref.harness_sha
            or not r.same(row.get('implementation_hashes'),implementation_hashes())):
        raise ValueError('fresh-runner protocol proof does not cover executing bytes')
    jobs = artifacts._pages(f'/actions/runs/{ref.run_id}/jobs?filter=all','jobs')
    required = {'harness-tests','full-suite','source','save1','interrupt-audit1','audit1','digest1',
        'accept1','save2','audit2','digest2','accept2','continued','restore-values','restore-digest','restored','proof-summary'}
    if not required <= {job['name'] for job in jobs if job.get('conclusion')=='success'}:
        raise ValueError('fresh-runner protocol CI is incomplete')
    final_ref = r.ArtifactRef.from_dict(row['restore_artifact'])
    download_ref(final_ref,root/'proof-restore',members={'restore-verified.json'})
    restored = r.load_receipt(root/'proof-restore/restore-verified.json')
    proof_authority = r.Authority.from_dict(restored['authority'])
    r.match_producer(final_ref,restored['producer'],proof_authority)
    r.validate_restore_acceptance(restored,proof_authority)
    if r.file_hash(root/'proof-restore/restore-verified.json') != row['restore_receipt_sha256']:
        raise ValueError('fresh-runner actual restore receipt differs')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=sorted(r.STAGES),required=True)
    parser.add_argument('--year',type=int,required=True)
    parser.add_argument('--config',type=Path,required=True)
    args = parser.parse_args(argv)
    resource.setrlimit(resource.RLIMIT_AS,(MARGIN,MARGIN))
    head = check_source()
    expected = os.environ['LAUNCH_CONFIG_SHA256']
    r.hexadecimal(expected,64,'launch configuration pin')
    if r.file_hash(args.config) != expected:raise ValueError('launch configuration bytes differ')
    config,refs,proof = load_launch(args.config,stage=args.stage,year=args.year)
    unique_launch()
    root = Path('evidence');root.mkdir(exist_ok=True)
    a = mature_authority()
    large = args.stage in ('save','audit','digest','restore-values','restore-digest')
    size = (config['candidate_database']['bytes'] if config['candidate_database'] else a.output_max_bytes) if refs.get('candidate') else a.published_database_bytes
    archive = refs['candidate'].archive_bytes if 'candidate' in refs else a.publication.archive_bytes
    check_space(required_space(args.stage,size,archive,a.output_max_bytes,before=True))
    check_proof(proof,root)
    if args.stage=='save' and args.year==a.source_config['milestones'][0]:
        previous_root = original.ROOT
        original.ROOT = root/'bootstrap'
        try:
            with bounded_extraction(a.published_database_bytes):
                directories,_ = original.download_inputs()
            original.validate_inputs(directories['published'],directories['diagnostics'],
                directories['storage']/'storage.json',directories['catalog']/'catalog.json')
        finally:
            original.ROOT = previous_root
        inputs = {'publication':directories['published']}
    else:
        inputs = fetch_stage_inputs(args.stage,args.year,root=root,authority=a,refs=refs,
            database_cap=config['candidate_database']['bytes'] if config['candidate_database'] else None)
        if config['candidate_database'] is not None and 'candidate' in inputs:
            saved = r.load_receipt(inputs['candidate']/'save.json')
            if not r.same(saved.get('database'),config['candidate_database']):
                raise ValueError('downloaded candidate differs from launch database pin')
    check_space(required_space(args.stage,size,archive,a.output_max_bytes,before=False))
    started = time.monotonic()
    with redirect_stdout(original.publish.catalog.storage._DiagnosticOutput(sys.stdout)),original.publish.legacy.progress():
        result = execute_stage(args.stage,args.year,authority=a,inputs=inputs,refs=refs,
            producer=producer(args.stage,'mature-stage'),output=root/'output')
    check_space(upload_space(args.stage,result))
    try:
        r.publish_receipt(root/'stage-summary.json',dict(stage=args.stage,year=args.year,harness_sha=head,
            runtime_sha=a.execution_runtime_sha,inputs={key:value.to_dict() for key,value in refs.items()},
            wall_seconds=time.monotonic()-started,result=result))
    except (OSError,ValueError):
        pass


if __name__ == '__main__':main()
