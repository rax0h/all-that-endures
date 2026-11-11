"""Bounded CI launcher: reuse green code and resume only verified closed stages."""
import argparse
import ast
import hashlib
import platform
import sqlite3
import sys
import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from simulation import stage_0_6_genesis_checkpoint as c
from simulation import stage_0_6_genesis_transport as t
from simulation import stage_0_6_genesis_source_control as controls
from simulation import checkpoint_artifacts as github
from simulation import continuation_receipts as r
from simulation.stage_0_6_retained_transport import _stream_archive,_signed_url

GREEN_RUN=42823293423
GREEN_JOBS={'full-suite':129854000533,'proof-map':129853999993}
GREEN_SHA='9e6f022fa556c25394dfd381f4d7d0356e5d8711'
RUNTIME='94267bb00a219702a4bd1700a2fc0600a5c5aa56'
REQUEST='simulation/stage_0_6_genesis_resume_request.json'
OLD_REQUEST='simulation/stage_0_6_proof_genesis_request.json'
CRITICAL=('simulation/stage_0_6_genesis_checkpoint.py','simulation/stage_0_6_genesis_transport.py',
    'simulation/stage_0_6_genesis_stages.py','simulation/stage_0_6_genesis_resume.py',
    '.github/tests/run_genesis_recovery_drill.py',c.WORKFLOW)
GREEN_ARTIFACTS={
    'full-suite':(13778449621,'stage-0-5-proof-map-suite-'+GREEN_SHA,'2c1bd46f45c878bef22131acf4d3b1b70bb9ceef7527bc3f1a1a1652be7cb333'),
    'proof-map':(13774870495,'stage-0-5-proof-map-'+GREEN_SHA,'24fd08053d558e6f9bad1a19b187afef143e7536db5137f3d75c7a6862b8ec87')}
TIMEOUTS=dict(source_digest=120,capture=240,catalog=240,rebase=240,after_digest=180,proofs=350,measure=150,fresh_restore=180)



def runtime_description():
    import _sqlite3
    def sha(path):
        return c.file_hash(path) if path and Path(path).is_file() else None
    db=sqlite3.connect(':memory:')
    try:
        details=dict(python=sys.version,compiler=platform.python_compiler(),executable=sha(sys.executable),
            sqlite=sqlite3.sqlite_version,sqlite_source_id=db.execute('select sqlite_source_id()').fetchone()[0],
            sqlite_compile_options=sorted(x[0] for x in db.execute('pragma compile_options')),
            extension=sha(getattr(_sqlite3,'__file__',None)))
    finally:db.close()
    paths=sorted(set(line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines() if 'libsqlite3.so' in line))
    details['sqlite_libraries']=[dict(name=Path(path).name,sha256=sha(path)) for path in paths]
    return dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,signature=c.receipt_hash(details)),details


def check_software(value):
    if value.get('python')!='3.12.16' or value.get('sqlite')!='3.45.1':raise ValueError('hosted software differs from green evidence; qualify before expensive work')


def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()


def dependency_paths(root,seeds):
    """Fence imported repository helpers/data, excluding operational budgets."""
    root=Path(root);pending=list(seeds);result=set()
    def module_path(name):
        if name=='ate_sim' or name.startswith(('ate_sim.','simulation.ate_sim.')):return
        relative=name.replace('.','/')
        for candidate in (relative+'.py',relative+'/__init__.py','simulation/'+relative+'.py'):
            if (root/candidate).is_file():pending.append(candidate)
    while pending:
        name=pending.pop()
        if name in result or name==REQUEST:continue
        path=root/name
        if not path.is_file():raise ValueError('missing critical dependency: '+name)
        result.add(name)
        if path.suffix!='.py':continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import):
                for alias in node.names:module_path(alias.name)
            elif isinstance(node,ast.ImportFrom) and node.module:
                module_path(node.module)
                if node.module=='simulation':
                    for alias in node.names:module_path('simulation.'+alias.name)
            elif isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.endswith('.json'):
                for candidate in (node.value,'simulation/'+node.value):
                    if candidate!=REQUEST and (root/candidate).is_file():pending.append(candidate)
    return result


def fence(root):
    runtime=git(root,'rev-parse','HEAD:simulation/ate_sim')
    if runtime!=RUNTIME or git(root,'status','--porcelain','--untracked-files=no'):raise ValueError('execution source/runtime is dirty or untested')
    authority=json.loads((Path(root)/OLD_REQUEST).read_text())
    paths=dependency_paths(root,(*CRITICAL,OLD_REQUEST,*authority['fingerprints']))
    blobs={name:git(root,'rev-parse','HEAD:'+name) for name in sorted(paths)}
    if any(git(root,'hash-object',name)!=sha for name,sha in blobs.items()):raise ValueError('critical code differs from commit')
    return runtime,blobs


def compatible(root,head):
    c.hexadecimal(head,40,'producer head')
    subprocess.run(['git','merge-base','--is-ancestor',head,'HEAD'],cwd=root,check=True,stdout=subprocess.DEVNULL)
    runtime,blobs=fence(root)
    if git(root,'rev-parse',head+':simulation/ate_sim')!=runtime:raise ValueError('checkpoint runtime changed')
    if any(git(root,'rev-parse',head+':'+name)!=blob for name,blob in blobs.items()):raise ValueError('checkpoint producer algorithm/workflow changed')


def validate_green(run,jobs,sources,*,current_runtime):
    if (current_runtime!=RUNTIME or run.get('id')!=GREEN_RUN or run.get('head_sha')!=GREEN_SHA
        or run.get('head_branch')!=t.BRANCH or run.get('event')!='push'
        or run.get('path')!='.github/workflows/stage-0-5-proof-map-validation.yml'
        or run.get('status')!='completed'):raise ValueError('green source/runtime differs')
    for name in ('full-suite','proof-map'):
        matches=[j for j in jobs if j.get('id')==GREEN_JOBS[name] and j.get('name')==name and j.get('head_sha')==GREEN_SHA and j.get('status')=='completed' and j.get('conclusion')=='success']
        if len(matches)!=1:raise ValueError('missing unique green '+name)
        source=sources.get(name,{})
        check_software(source)
        if source.get('head')!=GREEN_SHA or source.get('runtime_tree')!=current_runtime:raise ValueError('green job imported different source')
    return dict(green_run=GREEN_RUN,green_commit=GREEN_SHA,runtime_tree=RUNTIME,
        jobs=['full-suite','proof-map'],parent_conclusion=run.get('conclusion'),scope='successful prerequisite jobs only')


def inspect_green(root):
    runtime,_=fence(root)
    check_software(runtime_description()[0])
    if git(root,'rev-parse',GREEN_SHA+':simulation/ate_sim')!=runtime:raise ValueError('green ancestor runtime differs')
    subprocess.run(['git','merge-base','--is-ancestor',GREEN_SHA,'HEAD'],cwd=root,check=True)
    run=github._api(f'/actions/runs/{GREEN_RUN}');jobs=github._pages(f'/actions/runs/{GREEN_RUN}/jobs?filter=all','jobs');sources={}
    for job,(artifact_id,name,expected) in GREEN_ARTIFACTS.items():
        a=github._api(f'/actions/artifacts/{artifact_id}')
        digest=github.authenticate(a,run,jobs,run_id=GREEN_RUN,workflow_sha=GREEN_SHA,name=name,job=job,workflow_path='.github/workflows/stage-0-5-proof-map-validation.yml')
        if digest!=expected or a['size_in_bytes']>2*c.MAX_METADATA:raise ValueError('green evidence archive differs')
        from simulation.stage_0_6_retained_producer import _timestamp
        from datetime import datetime,timezone
        if datetime.now(timezone.utc)>=_timestamp(a['expires_at']):raise ValueError('green evidence unavailable/expired; do not automatically rerun suites')
        with tempfile.TemporaryDirectory(prefix='green-source-') as directory:
            archive=Path(directory)/'green.zip'
            _stream_archive(_signed_url(artifact_id),archive,archive_sha256=expected,archive_bytes=a['size_in_bytes'])
            with zipfile.ZipFile(archive) as z:
                entries=[x for x in z.infolist() if x.filename=='source.json']
                if len(entries)!=1 or entries[0].file_size>c.MAX_METADATA:raise ValueError('invalid green source receipt')
                sources[job]=json.loads(z.read(entries[0]))
    return validate_green(run,jobs,sources,current_runtime=runtime)


def producer(stage):
    p=dict(run_id=int(os.environ['GITHUB_RUN_ID']),head_sha=os.environ['GITHUB_SHA'],job=os.environ['GITHUB_JOB'],attempt=int(os.environ['GITHUB_RUN_ATTEMPT']))
    if p['job']!=c.JOB[stage]:raise ValueError('wrong CI producer job')
    return p


def config(root):
    value=json.loads((Path(root)/REQUEST).read_text())
    c.exact(value,{'schema','request_id','mode','smoke_run_id','resume_run_id','budgets'},'resume request')
    if value['schema']!='ate-proof-genesis-resume-request/1' or value['mode'] not in ('smoke','mature'):raise ValueError('invalid resume request')
    if type(value['request_id']) is not str or re.fullmatch('[a-zA-Z0-9_-]{1,96}',value['request_id']) is None:raise ValueError('invalid request id')
    for k in ('smoke_run_id','resume_run_id'):c.integer(value[k],k)
    c.exact(value['budgets'],c.STAGES,'phase budgets')
    for stage,budget in value['budgets'].items():
        c.integer(budget,'budget',1)
        if budget>12600 or budget/60+30>TIMEOUTS[stage]:raise ValueError('phase lacks compute/upload reserve')
    return value


def context(root,mode,source,*,rules_id,expected_saved_digest):
    runtime,blobs=fence(root)
    return dict(mode=mode,runtime_tree=runtime,critical_blobs=blobs,source=source,rules_id=rules_id,
        rank_proofs=True,execution_runtime=runtime_description()[0],expected_saved_digest=expected_saved_digest)


def mature_context(root):
    from simulation import construction_mature_continuation_stages as stages
    old=r.load_receipt(Path(root)/OLD_REQUEST);authority=stages.mature_authority()
    db=dict(bytes=old['database']['bytes'],sha256=old['database']['sha256'],store_identity=old['pin']['store_identity'],
        generation=old['pin']['captured_head'],format=6,year=old['world']['year'],seed=old['world']['seed'])
    return context(root,'mature',db,rules_id=authority.source_config['rules_id'],expected_saved_digest=old['expected_saved_digest'])


def check_context(root,value,mode):
    c.check_context(value);runtime,blobs=fence(root)
    if value['mode']!=mode or value['runtime_tree']!=runtime or value['critical_blobs']!=blobs or value['execution_runtime']!=runtime_description()[0]:raise ValueError('checkpoint mode/code differs')
    if mode=='mature' and value!=mature_context(root):raise ValueError('checkpoint original authority differs')
    if mode=='smoke' and (value['source']['seed']!=843000 or value['source']['year']!=1 or value['rules_id']!='stage-0-6-resume-smoke'):raise ValueError('unexpected smoke source')


def find_reference(root,run_id,artifact_id,*,mode,stage):
    a=github._api(f'/actions/artifacts/{artifact_id}');run=github._api(f'/actions/runs/{run_id}');head=run['head_sha']
    compatible(root,head)
    pattern='checkpoint-'+re.escape(mode)+'-'+re.escape(stage)+'-'+re.escape(head)+r'-(\d+)'
    match=re.fullmatch(pattern,a.get('name',''))
    if match is None:raise ValueError('wrong checkpoint stage/name')
    jobs=github._pages(f'/actions/runs/{run_id}/jobs?filter=all','jobs')
    return t.authenticate(a,run,jobs,name=a['name'],job=c.JOB[stage],head=head,run_id=run_id)


def match_receipt_reference(value,ref,*,mode,stage):
    p=value['producer']
    if (value['stage']!=stage or p['run_id']!=ref['run_id'] or p['head_sha']!=ref['head_sha']
        or p['job']!=ref['job'] or ref['name']!=t.name_for('checkpoint',mode,stage,p['head_sha'],p['attempt'])):
        raise ValueError('checkpoint producing receipt/attempt differs')


def restore_receipt(root,ref,destination,*,mode,stage):
    t.restore(ref,destination,member='checkpoint.json',compatible=lambda head:compatible(root,head))
    value=c.load(destination,require_remote=True);check_context(root,value['context'],mode)
    controls.validate_control_chain(root,value,current_runtime_tree=git(root,'rev-parse','HEAD:simulation/ate_sim'))
    match_receipt_reference(value,ref,mode=mode,stage=stage)
    return value


def discover(root,run_id,mode,workspace):
    run=github._api(f'/actions/runs/{run_id}');head=run['head_sha'];compatible(root,head)
    candidates=[]
    for a in github._pages(f'/actions/runs/{run_id}/artifacts','artifacts'):
        for stage in c.ORDER:
            match=re.fullmatch('checkpoint-'+re.escape(mode)+'-'+re.escape(stage)+'-'+re.escape(head)+r'-(\d+)',a.get('name',''))
            if match and a.get('expired') is False:candidates.append((c.ORDER.index(stage),int(match[1]),a['id'],stage))
    if not candidates:raise ValueError('no compatible completed checkpoint; no automatic restart')
    for index,attempt,aid,stage in sorted(candidates,reverse=True):
        # A named partial or failed producer is not a usable checkpoint.
        try:ref=find_reference(root,run_id,aid,mode=mode,stage=stage)
        except ValueError:continue
        value=restore_receipt(root,ref,workspace/'selected',mode=mode,stage=stage)
        return ref,value
    raise ValueError('no successful checkpoint producer')


def require_smoke(root,run_id,workspace):
    c.integer(run_id,'successful smoke run',1)
    run=github._api(f'/actions/runs/{run_id}')
    if run.get('status')!='completed' or run.get('conclusion')!='success':raise ValueError('small hosted smoke has not passed')
    ref,value=discover(root,run_id,'smoke',workspace/'smoke-proof')
    if value['stage']!='fresh_restore' or value['metrics'].get('restored',{}).get('digest')!=value['context']['expected_saved_digest']:raise ValueError('smoke lacks fresh-process completion')
    return ref


def _output(**values):
    path=os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path,'a') as stream:
            for key,value in values.items():stream.write(key+'='+str(value)+'\n')
    print(json.dumps(values),flush=True)


def gate(root,workspace,*,input_mode='',input_resume_run=0,input_smoke_run=0):
    cfg=config(root);green=inspect_green(root);mode=input_mode
    if not mode:
        before=os.environ.get('BEFORE','')
        changed=bool(before and git(root,'diff','--name-only',before,'HEAD','--',REQUEST))
        mode=cfg['mode'] if changed else 'smoke'
    if mode not in ('smoke','mature'):raise ValueError('invalid execution mode')
    workspace.mkdir(parents=True,exist_ok=True)
    r.publish_receipt(workspace/'green-reuse.json',green)
    r.publish_receipt(workspace/'runtime.json',runtime_description()[1])
    smoke_run=input_smoke_run or cfg['smoke_run_id']
    if mode=='mature':
        require_smoke(root,smoke_run,workspace)
        controls.mature_control_contract(root,current_runtime_tree=git(root,'rev-parse','HEAD:simulation/ate_sim'))
    resume_run=input_resume_run or (cfg['resume_run_id'] if mode==cfg['mode'] else 0)
    if not resume_run and int(os.environ['GITHUB_RUN_ATTEMPT'])>1:resume_run=int(os.environ['GITHUB_RUN_ID'])
    if resume_run:
        ref,value=discover(root,resume_run,mode,workspace)
        _output(mode=mode,resume_index=c.ORDER.index(value['stage'])-1,resume_artifact_id=ref['artifact_id'],resume_run_id=ref['run_id'],has_database='false',fresh='false')
        return
    if mode=='mature':
        from simulation.stage_0_6_retained_producer import inspect_retained_producer
        inspect_retained_producer();ctx=mature_context(root);data_ref={'kind':'retained-original'};db=None
    else:
        from ate_sim.worldgen import generate_world
        from ate_sim.engine import Simulation
        from ate_sim.persistence_session import write_cold_snapshot
        from ate_sim.persistence_lazy import convert_cold_to_lazy
        from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
        world=generate_world(843000,width=4,height=3,settlements=1,mature=True)
        Simulation(world).run(1);control=copy.deepcopy(world);Simulation(control).run(1)
        temporary=workspace/'smoke-source';temporary.mkdir()
        cold=temporary/'cold.sqlite';legacy=temporary/'legacy.sqlite';db=temporary/'complete.sqlite'
        rules='stage-0-6-resume-smoke'
        write_cold_snapshot(world,cold,rules_id=rules);convert_cold_to_lazy(cold,legacy,rules_id=rules,native_graph_buckets=True)
        upgrade_lazy_snapshot(legacy,db,rules_id=rules)
        ctx=context(root,mode,c.describe(db,rules_id=rules),rules_id=rules,expected_saved_digest=control.digest());data_ref=None
    value=c.record('source',ctx,ctx['source'],producer('source'),data_ref=data_ref,metrics=dict(green=green,smoke_run_id=smoke_run))
    c.publish(workspace/'out',value,database=db)
    _output(mode=mode,resume_index=-1,resume_artifact_id='',resume_run_id='',has_database=str(db is not None).lower(),fresh='true')


def original_input(root,workspace,value):
    from simulation.stage_0_6_retained_launch import prepare_retained
    from simulation import construction_mature_continuation_stages as stages
    from simulation import profile_stage_0_5_performance as profile
    old=r.load_receipt(Path(root)/OLD_REQUEST);original=r.load_receipt(Path(root)/'simulation/stage_0_5_save1002_preflight.json')
    authority=stages.mature_authority();workspace.mkdir(parents=True,exist_ok=True)
    prepare_retained(workspace,old,profile._runtime_identity(),r.ArtifactRef.from_dict(original['inputs']['candidate']),
        r.ArtifactRef.from_dict(original['inputs']['previous']),original['candidate_database'],authority)
    path=workspace/'source/candidate.sqlite';c.verify_database(path,value['database'])
    return path


def run(root,workspace,*,stage,mode,parent_run,parent_artifact):
    from simulation.stage_0_6_genesis_stages import run_stage,Recorder
    from simulation.stage_0_6_mature_benchmark import resources
    cfg=config(root);fence(root);workspace.mkdir(parents=True,exist_ok=True)
    previous=c.ORDER[c.ORDER.index(stage)-1]
    ref=find_reference(root,parent_run,parent_artifact,mode=mode,stage=previous)
    value=restore_receipt(root,ref,workspace/'input-metadata',mode=mode,stage=previous)
    r.publish_receipt(workspace/'input-reference.json',dict(stage=stage,metadata_artifact=ref,database=value['database'],context_sha256=c.receipt_hash(value['context']),budget_seconds=cfg['budgets'][stage]))
    data_ref=value['data_ref'];transport=Recorder(workspace/'transport',{'restore':1800})
    def restore():
        if data_ref.get('kind')=='retained-original':return original_input(root,workspace/'original',value)
        cap=2*1024**3 if mode=='smoke' else 96*1024**3
        if value['database']['bytes']>cap:raise ValueError('checkpoint database exceeds admitted stage size')
        t.restore(data_ref,workspace/'input-data',member='candidate.sqlite',member_bytes=value['database']['bytes'],compatible=lambda head:compatible(root,head))
        path=workspace/'input-data/candidate.sqlite';c.verify_database(path,value['database']);return path
    database=transport.measure('restore',restore)
    active='start';sequence=0;stopped=threading.Event()
    def progress(phase):
        nonlocal active,sequence
        active=str(phase);r.publish_receipt(workspace/('progress-%05d.json'%sequence),dict(phase=active,time=time.time(),resources=resources()));sequence+=1
        print(json.dumps(dict(phase=active,time=time.time())),flush=True)
    def heartbeat():
        while not stopped.wait(30):print(json.dumps(dict(heartbeat=active,resources=resources(),time=time.time())),flush=True)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        source_control=None
        if stage=='source_digest' and mode=='mature':
            progress('source_control.authenticate_retained_acceptance')
            source_control=controls.mature_control(root,workspace/'original/accepted/year-verified.json',
                value['database'],current_runtime_tree=git(root,'rev-parse','HEAD:simulation/ate_sim'))
            progress('source_control.historical_control_reused')
        run_stage(stage,value,database,workspace/'out',producer=producer(stage),budget=cfg['budgets'][stage],progress=progress,source_control=source_control)
    except BaseException as exc:
        r.publish_receipt(workspace/'failure.json',dict(stage=stage,status='timeout' if isinstance(exc,TimeoutError) or type(exc).__name__=='BudgetExpired' else 'error',error=type(exc).__name__+': '+str(exc),last_phase=active,notes=getattr(exc,'__notes__',[]),prior_checkpoint=ref))
        raise
    finally:stopped.set();thread.join(timeout=2)
    completed=c.load(workspace/'out')
    cap=2*1024**3 if mode=='smoke' else 96*1024**3
    if completed['database']['bytes']>cap:raise ValueError('completed output exceeds admitted transfer cap')
    _output(has_database=str((workspace/'out/candidate.sqlite').exists()).lower())


def seal(root,workspace,*,artifact_id=0):
    directory=workspace/'out';value=c.load(directory);p=value['producer']
    if p!=producer(value['stage']):raise ValueError('cannot seal another producer receipt')
    db=directory/'candidate.sqlite'
    if db.exists():
        if not artifact_id:raise ValueError('closed database was not uploaded')
        a=t.read_uploaded_artifact(artifact_id)
        value['data_ref']=t.reference(a,name=t.name_for('database',value['context']['mode'],value['stage'],p['head_sha'],p['attempt']),
            job=p['job'],head=p['head_sha'],run_id=p['run_id'])
        c.verify_database(db,value['database'])
    elif artifact_id:raise ValueError('read-only checkpoint cannot claim new database')
    c.validate(value,require_remote=True);check_context(root,value['context'],value['context']['mode'])
    controls.validate_control_chain(root,value,current_runtime_tree=git(root,'rev-parse','HEAD:simulation/ate_sim'))
    temp=directory/'checkpoint.sealed';temp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    with temp.open('rb') as stream:os.fsync(stream.fileno())
    temp.replace(directory/'checkpoint.json')
    _output(metadata_name=t.name_for('checkpoint',value['context']['mode'],value['stage'],p['head_sha'],p['attempt']))


def check_measured_targets(measured,mode):
    c.validate(measured)
    if measured['stage']!='measure' or measured['context']['mode']!=mode:raise ValueError('wrong measurement stage/mode')
    benchmark=measured['metrics'].get('benchmark',{})
    if benchmark.get('saved_commitment')!=measured['proof_commitment']:raise ValueError('saved checkpoint commitment differs')
    targets=dict(open=10,save=2,warm_step=1);actual={}
    for name in ('open','first_step','save','warm_step'):
        phase=benchmark.get('phases',{}).get(name,{})
        seconds=phase.get('wall_seconds')
        if (phase.get('status')!='complete' or type(seconds) not in (int,float)
                or not math.isfinite(seconds) or seconds<0):raise ValueError('incomplete operational measurement')
        if name in targets:actual[name]=seconds<=targets[name]
    flags=benchmark.get('targets_met',{})
    if benchmark.get('targets_seconds')!=targets or flags!=actual or any(type(flags.get(k)) is not bool for k in targets):raise ValueError('target claims differ from actual measured times')
    if mode=='mature' and not all(actual.values()):raise ValueError('mature performance targets not met; saved checkpoint retained; skip deep verification')
    return actual


def check_targets(root,workspace,*,mode,parent_run,parent_artifact):
    ref=find_reference(root,parent_run,parent_artifact,mode=mode,stage='measure')
    value=restore_receipt(root,ref,workspace/'preflight',mode=mode,stage='measure')
    _output(targets_met=check_measured_targets(value,mode))


def evaluate_acceptance(value,mode):
    c.validate(value)
    if value['stage']!='fresh_restore' or value['context']['mode']!=mode:raise ValueError('wrong acceptance mode/stage')
    restored=value['metrics'].get('restored',{});ctx=value['context']
    expected=dict(year=ctx['source']['year']+1,seed=ctx['source']['seed'],generation=1,digest=ctx['expected_saved_digest'],world_audits=0)
    if restored!=expected or any(type(restored.get(k)) is not int for k in ('year','seed','generation','world_audits')):raise ValueError('missing exact saved/fresh validation')
    measured=value['parent']['receipt']
    if measured['proof_commitment']!=value['proof_commitment']:raise ValueError('fresh checkpoint commitment differs')
    check_measured_targets(measured,mode)
    return dict(acceptance='mature-targets-met' if mode=='mature' else 'smoke-functional-only',saved_digest=restored['digest'])


def accept(root,workspace,*,mode,parent_run,parent_artifact):
    ref=find_reference(root,parent_run,parent_artifact,mode=mode,stage='fresh_restore')
    value=restore_receipt(root,ref,workspace/'accepted',mode=mode,stage='fresh_restore')
    _output(**evaluate_acceptance(value,mode))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['gate','run-stage','seal','check-targets','accept'])
    p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--workspace',type=Path,default=Path('resume-work'))
    p.add_argument('--mode',default='');p.add_argument('--stage',choices=c.STAGES);p.add_argument('--parent-run',type=int,default=0);p.add_argument('--parent-artifact',type=int,default=0)
    p.add_argument('--artifact-id',type=int,default=0);p.add_argument('--resume-run',type=int,default=0);p.add_argument('--smoke-run',type=int,default=0)
    a=p.parse_args();root=a.root.resolve();work=a.workspace.resolve()
    if root!=Path.cwd().resolve() or not work.is_relative_to(root) or work==root:raise ValueError('execution/workspace root differs')
    from simulation.stage_0_6_mature_benchmark import check_source
    check_source(root,r.load_receipt(root/OLD_REQUEST),os.environ['GITHUB_SHA'])
    if a.command=='gate':gate(root,work,input_mode=a.mode,input_resume_run=a.resume_run,input_smoke_run=a.smoke_run)
    elif a.command=='run-stage':run(root,work,stage=a.stage,mode=a.mode,parent_run=a.parent_run,parent_artifact=a.parent_artifact)
    elif a.command=='seal':seal(root,work,artifact_id=a.artifact_id)
    elif a.command=='check-targets':check_targets(root,work,mode=a.mode,parent_run=a.parent_run,parent_artifact=a.parent_artifact)
    else:accept(root,work,mode=a.mode,parent_run=a.parent_run,parent_artifact=a.parent_artifact)


if __name__=='__main__':main()
