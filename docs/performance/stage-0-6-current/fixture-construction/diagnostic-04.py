"""Observe original construction failures without changing construction behavior."""
import argparse, gc, hashlib, json, shutil, sqlite3, subprocess, time, traceback
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(exist_ok=False)
log=out/'events.jsonl';started=time.perf_counter();seen=set()

def emit(kind,**data):
    value=dict(kind=kind,seconds=time.perf_counter()-started,**data)
    with log.open('a') as target:target.write(json.dumps(value,default=str)+'\n')
    print(json.dumps(value,default=str),flush=True)

def inspect_db(label,db,path,extra=None):
    data=dict(path=str(path),in_transaction=db.in_transaction,extra=extra)
    for name,connection in [('original',db),('fresh',None)]:
        try:
            if connection is None:connection=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)
            values={}
            for key,sql in [('quick_check','PRAGMA quick_check'),('schema','SELECT name,type,rootpage FROM sqlite_schema'),('head','SELECT generation FROM main.save_head WHERE singleton=1'),('replay_counts','SELECT stream,count(*) FROM replay_rows GROUP BY stream'),('index_counts','SELECT stream,count(*) FROM preparation_index GROUP BY stream')]:
                try:values[key]=connection.execute(sql).fetchall()
                except Exception as exc:values[key]=repr(exc)
            data[name]=values
        except Exception as exc:data[name]=repr(exc)
        finally:
            if name=='fresh' and connection is not None:connection.close()
    destination=out/(label+'.sqlite');shutil.copyfile(path,destination)
    data['saved_sha256']=hashlib.sha256(destination.read_bytes()).hexdigest()
    data['saved_bytes']=destination.stat().st_size
    emit('db_diagnostic',label=label,**data)

from ate_sim import persistence_catalog_copy as catalog
from ate_sim import persistence_conversion_workspace as conversion
import os,weakref
workspaces=[]
def fds():
    result={}
    for fd in os.listdir('/proc/self/fd'):
        try:result[fd]=os.readlink('/proc/self/fd/'+fd)
        except FileNotFoundError:pass
    return result
old_init=conversion.ConversionWorkspace.__init__
def init(self,*a,**k):
    old_init(self,*a,**k);workspaces.append(weakref.ref(self))
    emit('workspace_open',path=str(self.path),inode=self.path.stat().st_ino,fds=fds())
conversion.ConversionWorkspace.__init__=init
old_phase=catalog._copy_phase

def phase(name,path):
    emit('copy_phase',phase=name,path=str(path),bytes=path.stat().st_size if path.exists() else None,fds=fds())
    if name=='before_catalog_commit':
        for ref in workspaces:
            workspace=ref()
            if workspace is not None and not workspace._closed:
                inspect_db('before-commit-workspace',workspace.db,workspace.path)
    return old_phase(name,path)
catalog._copy_phase=phase
old_verify=catalog._verify_catalog

def verify(store,*a,**k):
    try:return old_verify(store,*a,**k)
    except BaseException as exc:
        if id(exc) not in seen:
            seen.add(id(exc));emit('catalog_error',error=repr(exc),code=getattr(exc,'sqlite_errorcode',None),name=getattr(exc,'sqlite_errorname',None))
            inspect_db('failed-target',store.db,store.path)
        raise
catalog._verify_catalog=verify
old_groups=conversion.PreparedRows.namespace_groups

def groups(self):
    try:yield from old_groups(self)
    except BaseException as exc:
        if id(exc) not in seen:
            seen.add(id(exc));emit('group_error',error=repr(exc),stream=self.stream,expected_count=self.count)
            inspect_db('failed-workspace',self.workspace.db,self.workspace.path,dict(stream=self.stream,count=self.count,seal=self.seal))
        raise
conversion.PreparedRows.namespace_groups=groups
def capture(exc,label,db,path,extra=None):
    if (id(exc),label) in seen:return
    seen.add((id(exc),label))
    try:inspect_db(label,db,path,extra)
    except BaseException as failure:emit('diagnostic_error',error=repr(failure),original=repr(exc))
old_replay=conversion.ReplayRows.__iter__
def replay(self):
    try:yield from old_replay(self)
    except BaseException as exc:
        capture(exc,'failed-replay',self.workspace.db,self.workspace.path,dict(stream=self.stream,count=self.count,seal=self.seal))
        raise
conversion.ReplayRows.__iter__=replay
old_stage=conversion.ConversionWorkspace.stage
def stage(self,*a,**k):
    try:return old_stage(self,*a,**k)
    except BaseException as exc:
        capture(exc,'failed-stage',self.db,self.path,dict(stream=self._stream))
        raise
conversion.ConversionWorkspace.stage=stage
from ate_sim.persistence_lazy_store import LazyRecordStore
old_head=LazyRecordStore._checked_head_row
def head(self,*a,**k):
    try:return old_head(self,*a,**k)
    except sqlite3.DatabaseError as exc:
        capture(exc,'failed-head',self.db,self.path)
        raise
LazyRecordStore._checked_head_row=head
from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
import copy

def run_phase(name,action):
    emit('start',phase=name)
    result=action();emit('complete',phase=name);return result
try:
    emit('source',head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sqlite=sqlite3.sqlite_version,gc=gc.get_stats())
    world=run_phase('generate',lambda:generate_world(843000,width=8,height=6,settlements=1,mature=True))
    run_phase('initial_years',lambda:Simulation(world).run(2))
    control=run_phase('eager_copy',lambda:copy.deepcopy(world))
    run_phase('eager_year',lambda:Simulation(control).run(1))
    rules='stage-0-6-real-year-probe'
    run_phase('cold',lambda:write_cold_snapshot(world,out/'cold.sqlite',rules_id=rules))
    run_phase('lazy',lambda:convert_cold_to_lazy(out/'cold.sqlite',out/'lazy.sqlite',rules_id=rules,native_graph_buckets=True))
    proof=run_phase('proof',lambda:copy_world_with_proofs(out/'lazy.sqlite',out/'accepted.sqlite',rules_id=rules,rank_proofs=True))
    emit('success',commitment=proof.commitment.hex(),expected_digest=control.digest())
except BaseException as exc:
    frames=[];tb=exc.__traceback__
    while tb:
        frame=tb.tb_frame
        values={key:value for key,value in frame.f_locals.items() if key in ('stream','count','total','ordinal','seen','namespace') and isinstance(value,(str,int,float,type(None)))}
        frames.append(dict(file=frame.f_code.co_filename,line=tb.tb_lineno,function=frame.f_code.co_name,values=values));tb=tb.tb_next
    emit('failure',error=repr(exc),code=getattr(exc,'sqlite_errorcode',None),name=getattr(exc,'sqlite_errorname',None),frames=frames,gc=gc.get_stats())
    traceback.print_exc();raise SystemExit(1)
