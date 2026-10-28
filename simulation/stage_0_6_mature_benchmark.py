"""Current-source mature measurement. Operational timers exclude copy/hash/control verification."""
from contextlib import contextmanager
from dataclasses import asdict
import argparse,json,math,os,platform,resource,shutil,signal,sqlite3,subprocess,time
from pathlib import Path
from unittest.mock import patch
from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.core import World
from simulation import profile_stage_0_5_performance as base,stage_0_5_mature_step_save as previous,continuation_receipts as r


def check_source(root,config,expected_sha):
    root=Path(root).resolve()
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    if git('rev-parse','HEAD')!=expected_sha or git('rev-parse','HEAD:simulation/ate_sim')!=config['runtime_tree']:raise ValueError('execution SHA/runtime differs from reviewed source')
    subprocess.run(['git','merge-base','--is-ancestor',config['green_commit'],'HEAD'],cwd=root,check=True)
    if git('status','--porcelain','--untracked-files=no') or git('status','--porcelain','--untracked-files=all','--','simulation/ate_sim'):raise ValueError('execution source is dirty')
    identity=base._runtime_identity()
    if Path(identity['root']).resolve()!=root or identity['head']!=expected_sha:raise ValueError('imported runtime differs from execution checkout')
    for name,digest in config['fingerprints'].items():
        git('cat-file','-e','HEAD:'+name)
        if r.file_hash(root/name)!=digest:raise ValueError('benchmark source fingerprint differs: '+name)
    return identity


def machine():
    try:model=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    except (OSError,StopIteration):model=platform.processor()
    return dict(platform=platform.platform(),python=platform.python_version(),sqlite=sqlite3.sqlite_version,cpu_count=os.cpu_count(),processor=model)


def resources():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    try:physical={k:int(v) for k,v in (row.split(':') for row in Path('/proc/self/io').read_text().splitlines())}
    except (OSError,ValueError):physical={}
    return dict(cpu_seconds=time.process_time(),rss_bytes=base._rss(),peak_rss_bytes=base._peak_rss(),minor_faults=usage.ru_minflt,major_faults=usage.ru_majflt,block_inputs=usage.ru_inblock,block_outputs=usage.ru_oublock,process_io=physical)


def delta(after,before):return {k:after[k]-before.get(k,0) for k in after if type(after[k]) in (int,float)}

def io_delta(after,before):return {k:v for k,v in delta(after,before).items() if not k.endswith('_peak')}

def high_water(after,before):return {k:dict(before=before.get(k,0),after=v) for k,v in after.items() if k.endswith('_peak')}


class Recorder:
    def __init__(self,output,budgets):
        self.output=Path(output);self.budgets=budgets;self.phases={};self.store=None
        if any(type(n) not in (int,float) or not math.isfinite(n) or n<=0 for n in budgets.values()):raise ValueError('phase budgets must be finite and positive')
    def measure(self,name,operation,*,on_budget_expiry=None):
        row=dict(status='running',budget_seconds=self.budgets.get(name));self.phases[name]=row
        r.publish_receipt(self.output/('phase-start-'+name+'.json'),dict(status='running',phase=name,started_unix=time.time(),budget_seconds=self.budgets.get(name)))
        before=resources();started=time.perf_counter();io=asdict(self.store.diagnostics()) if self.store is not None else {};row['resources_start']=before
        old=signal.getsignal(signal.SIGALRM);timer=signal.getitimer(signal.ITIMER_REAL)
        owns_alarm=name in self.budgets
        if owns_alarm and timer[0]:raise ValueError('cannot replace an active alarm')
        def expired(*_):
            if on_budget_expiry is not None:on_budget_expiry()
            raise base.BudgetExpired(name+' phase budget exhausted')
        try:
            if owns_alarm:signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,self.budgets[name])
            value=operation();row['status']='complete';return value
        except base.BudgetExpired:
            row['status']='timeout';row['censored']=True;raise
        except BaseException:
            row['status']='error';raise
        finally:
            if owns_alarm:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
            after=resources();row.update(wall_seconds=time.perf_counter()-started,cpu_seconds=after['cpu_seconds']-before['cpu_seconds'],resources_end=after,resource_delta=delta(after,before),process_io_delta=delta(after['process_io'],before['process_io']))
            if self.store is not None:
                after_io=asdict(self.store.diagnostics());row['io']=io_delta(after_io,io);row['io_high_water']=high_water(after_io,io)
            r.publish_receipt(self.output/('phase-progress-'+name+'.json'),dict(schema='ate-stage06-progress/1',phases=self.phases))
    @contextmanager
    def split_open(self,prefix=''):
        original=LazyRecordStore.open
        def opened(*args,**kwargs):
            start=time.perf_counter();cpu=time.process_time();before=resources()
            try:
                store=original(*args,**kwargs);self.store=store;return store
            finally:
                self.phases[prefix+'database_open']=dict(status='complete' if self.store is not None else 'error',wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,resources_start=before,resources_end=resources(),io=io_delta(asdict(self.store.diagnostics()),{}) if self.store is not None else {},io_high_water=high_water(asdict(self.store.diagnostics()),{}) if self.store is not None else {})
        with patch.object(LazyRecordStore,'open',side_effect=opened):yield
    def finish_split(self,total,prefix=''):
        outer=self.phases.get(total);inner=self.phases.get(prefix+'database_open')
        if outer is None or inner is None:return
        self.phases[prefix+'state_restore']=dict(status=outer['status'],wall_seconds=max(0.,outer['wall_seconds']-inner['wall_seconds']),cpu_seconds=max(0.,outer['cpu_seconds']-inner['cpu_seconds']),io=io_delta(outer.get('io',{}),inner.get('io',{})),io_high_water={k:dict(before=inner.get('io_high_water',{}).get(k,{}).get('after',0),after=v['after']) for k,v in outer.get('io_high_water',{}).items()},meaning='open total minus database initialization; includes checked admission and canonical restoration')


def run(source,output,*,authority,budgets):
    if Path(source).is_symlink():raise ValueError('source symlink is forbidden')
    source=Path(source).resolve();output=Path(output).resolve()
    if source==output or source.is_relative_to(output):raise ValueError('output cannot contain input')
    output.mkdir(parents=True,exist_ok=False);rec=Recorder(output,{('open_total' if k=='open' else k):v for k,v in budgets.items()});session=None
    result=dict(schema='ate-stage06-mature/1',status='error',runtime=base._runtime_identity(),source=authority,machine=machine(),instrumentation='application counters/process resource counters; no SQL trace or cProfile',phases=rec.phases,unavailable=['SQLite VM/page-cache counters','controlled filesystem cache','independent per-phase RSS peak','full historical scrub timing'])
    try:
        rec.measure('source_verification',lambda:base._verify_authority(source,authority['database']['sha256'],authority))
        if shutil.disk_usage(output).free<source.stat().st_size+8*1024**3:raise ValueError('insufficient disposable database headroom')
        target=output/'operational.sqlite';rec.measure('database_copy',lambda:shutil.copyfile(source,target))
        copied=rec.measure('copy_verification',lambda:r.file_hash(target))
        if copied!=authority['database']['sha256']:raise ValueError('copied fixture hash differs')
        try:
            with rec.split_open():session=rec.measure('open_total',lambda:open_lazy_world_session(target,rules_id=authority['rules_id']))
        finally:rec.finish_split('open_total')
        result['initial']=base._world(session);pin=authority['pin']
        if (session.pin.store_identity!=pin['store_identity'] or session.pin.captured_head!=pin['captured_head'] or {k:result['initial'][k] for k in ('seed','year')}!=authority['world']):raise ValueError('opened world/pin differs from accepted fixture')
        rec.measure('first_step',lambda:Simulation(session.world).run(1))
        if session.world.year!=authority['world']['year']+1:raise ValueError('first step year differs')
        rec.measure('save',session.save);result['saved']=base._world(session)
        if result['saved']['pin']['captured_head']!=pin['captured_head']+1 or result['saved']['year']!=authority['world']['year']+1:raise ValueError('save successor differs')
        rec.measure('warm_step',lambda:Simulation(session.world).run(1));result['final']=base._world(session)
        if result['final']['year']!=authority['world']['year']+2 or result['final']['pin']!=result['saved']['pin']:raise ValueError('warm step modified saved pin or year differs')
        result['status']='complete'
    except base.BudgetExpired as exc:result.update(status='timeout',error=str(exc),censored=True)
    except Exception as exc:result.update(status='error',error=type(exc).__name__+': '+str(exc))
    finally:
        try:
            if session is not None:rec.measure('close',session.close)
        except Exception as exc:result['close_error']=str(exc);result['status']='error' if result['status']!='timeout' else 'timeout'
        try:
            result['source_unchanged']=rec.measure('retained_input_verification',lambda:r.file_hash(source))==authority['database']['sha256']
            if not result['source_unchanged']:raise ValueError('accepted source changed')
            target=output/'operational.sqlite'
            if result['status']=='complete':
                if not target.is_file() or any(Path(str(target)+suffix).exists() for suffix in ('-journal','-wal','-shm')):raise ValueError('saved output is not closed/standalone')
                result['saved_database']=dict(sha256=rec.measure('saved_file_hash',lambda:r.file_hash(target)),bytes=target.stat().st_size)
            result['disk']=dict(database_bytes=target.stat().st_size if target.exists() else None,allocated_database_bytes=target.stat().st_blocks*512 if target.exists() else None,free_bytes=shutil.disk_usage(output).free)
        except Exception as exc:result.update(status='error',verification_error=str(exc))
        r.publish_receipt(output/'result.json',result)
    return result


def verify(database,output,*,seconds,**expected):
    if Path(database).is_symlink():raise ValueError('database symlink is forbidden')
    output=Path(output);rec=Recorder(output.parent,{'verification_total':seconds});original_open=previous.open_lazy_world_session;original_digest=World.digest
    def opened(*args,**kwargs):return rec.measure('fresh_open_total',lambda:original_open(*args,**kwargs))
    def digest(world,*args,**kwargs):return rec.measure('logical_digest',lambda:original_digest(world,*args,**kwargs))
    # Inner measurements inherit the one outer verification alarm.
    def total():
        with rec.split_open('fresh_'),patch.object(previous,'open_lazy_world_session',side_effect=opened),patch.object(World,'digest',digest):
            return previous.verify_checkpoint(database,output.with_name('original-'+output.name),**expected)
    # Recorder nested alarms are forbidden; verification budget lives around
    # the entire existing verifier, while inner measurements only record time.
    rec.budgets={};old=signal.getsignal(signal.SIGALRM)
    if signal.getitimer(signal.ITIMER_REAL)[0]:raise ValueError('active caller alarm')
    def expired(*_):raise base.BudgetExpired('fresh verification budget exhausted')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:
        # Inner recorder must preserve, rather than replace, this alarm.
        with patch.object(rec,'budgets',{}):
            result=rec.measure('verification_total',total)
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
    rec.finish_split('fresh_open_total','fresh_');result['phases']=rec.phases;result['runtime']=base._runtime_identity();result['machine']=machine()
    if 'BudgetExpired' in result.get('error',''):result.update(status='timeout',censored=True)
    rec.phases['verification_total']['status']=result['status'];rec.phases['verification_total']['budget_seconds']=seconds
    if result['status']=='timeout':rec.phases['verification_total']['censored']=True
    r.publish_receipt(output,result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','verify']);p.add_argument('--config',type=Path,required=True);p.add_argument('--root',type=Path,required=True);args=p.parse_args();config=r.load_receipt(args.config)
    identity=check_source(Path.cwd(),config,os.environ['GITHUB_SHA']);root=args.root
    authority=r.load_receipt(root/'evidence/source-authority.json')
    if (authority['database']!={k:config['database'][k] for k in ('sha256','bytes')} or authority['world']!=config['world']
            or any(authority['pin'][k]!=config['pin'][k] for k in ('store_identity','captured_head'))):raise ValueError('measurement authority differs from pinned launch')
    if args.command=='run':result=run(root/'source/candidate.sqlite',root/'evidence/current',authority=authority,budgets=config['budgets'])
    else:
        measured=r.load_receipt(root/'evidence/current/result.json');saved=measured['saved_database']
        if measured['status']!='complete' or measured['runtime']['head']!=identity['head']:raise ValueError('saved receipt is not this completed execution')
        result=verify(root/'evidence/current/operational.sqlite',root/'evidence/fresh-restore.json',seconds=config['verification_budget_seconds'],expected_sha256=saved['sha256'],expected_bytes=saved['bytes'],rules_id=authority['rules_id'],expected_year=config['world']['year']+1,expected_seed=config['world']['seed'],expected_generation=config['pin']['captured_head']+1,expected_store_identity=config['pin']['store_identity'],expected_digest=config['expected_saved_digest'])
    print(json.dumps(dict(status=result['status'],runtime=identity)));return 0 if result['status']=='complete' else 1

if __name__=='__main__':raise SystemExit(main())
