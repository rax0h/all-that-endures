"""Read-only resource inventory for the accepted mature proof-genesis input.

No World restoration, simulation, save, migration or performance acceptance.
"""
import argparse
import math
import os
from pathlib import Path
import resource
import shutil
import sqlite3
import sys
import time
from simulation import continuation_receipts as r
from simulation.stage_0_6_mature_benchmark import check_source
from simulation.stage_0_6_retained_launch import prepare_retained
from simulation.stage_0_6_retained_producer import PIN

MAX_NAMESPACES=4096
ORIGINAL_LAUNCH=Path('simulation/stage_0_5_save1002_preflight.json')
TABLES=(('records','namespace','payload',False),('segments','namespace','payload',False),
    ('lazy_record_versions','namespace','payload',True),('lazy_order_versions','namespace',None,True),
    ('lazy_query_versions','namespace',None,True),('lazy_namespace_state','namespace',None,True),
    ('lazy_identity_occurrence_versions','owner_namespace',None,True),('lazy_identity_state',None,None,True))


def _budget(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=900:
        raise ValueError('invalid inventory time budget')


def inspect_database(path,authority,*,budget_seconds=900,output=None,execution=None):
    path=Path(path)
    output=Path(output) if output is not None else None
    if output is not None and (output.resolve()==path.resolve() or output.is_symlink()
            or output.exists() and path.exists() and output.samefile(path)):
        raise ValueError('inventory output cannot replace input')
    if output is not None and output.exists():raise FileExistsError(output)
    result=dict(schema='ate-stage06-proof-preflight/1',status='running',acceptance='not-run',tables={})
    if execution is not None:result['execution']=execution
    started=time.monotonic();deadline=started+budget_seconds if type(budget_seconds) in (int,float) else started
    failure=None
    def publish(prefix=''):
        if output is not None:r.publish_receipt(output.with_name(prefix+output.name),result)
    def check_time():
        if time.monotonic()>=deadline:raise TimeoutError('inventory budget exhausted')
    def standalone():
        if (path.is_symlink() or not path.is_file()
                or any(Path(str(path)+suffix).exists() for suffix in ('-journal','-wal','-shm'))):
            raise ValueError('inventory requires closed standalone regular source')
    try:
        publish('started-')
        _budget(budget_seconds)
        standalone();database=authority['database']
        r.integer(database['bytes'],'source bytes',1);r.hexadecimal(database['sha256'],64,'source digest')
        if path.stat().st_size!=database['bytes'] or r.file_hash(path)!=database['sha256']:
            raise ValueError('inventory source hash or size differs')
        check_time()
        db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
        interrupted=False
        def stop():
            nonlocal interrupted
            interrupted=time.monotonic()>=deadline
            return interrupted
        try:
            db.set_progress_handler(stop,1000)
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
            db.execute('PRAGMA temp_store=FILE');db.execute('BEGIN')
            required=('store_metadata','save_head',*(t[0] for t in TABLES))
            rows=db.execute("SELECT name,type FROM main.sqlite_schema WHERE name IN ("+
                ','.join('?' for _ in required)+')',required).fetchall()
            if set(rows)!={(name,'table') for name in required}:raise ValueError('missing inventory tables')
            pairs=db.execute("SELECT CASE WHEN typeof(key)='text' AND length(CAST(key AS BLOB))<=128 THEN key END,"
                "CASE WHEN typeof(value)='text' AND length(CAST(value AS BLOB))<=4096 THEN value END "
                'FROM main.store_metadata LIMIT 9').fetchall()
            metadata=dict(pairs)
            if (len(pairs)!=7 or set(metadata)!={'store_uuid','format_version','codec_version','simulation_schema',
                    'rules_id','journal_mode','synchronous'} or any(type(x) is not str for x in metadata.values())
                    or metadata['store_uuid']!=authority['pin']['store_identity']
                    or metadata['rules_id']!=authority['rules_id']):raise ValueError('inventory metadata context differs')
            head=db.execute("SELECT singleton,CASE WHEN typeof(generation)='integer' THEN generation END,"
                "CASE WHEN typeof(seed) IN ('integer','null') THEN seed END,typeof(seed) "
                'FROM main.save_head LIMIT 2').fetchall()
            if (len(head)!=1 or head[0][0]!=1 or type(head[0][1]) is not int
                    or head[0][1]!=authority['pin']['captured_head'] or head[0][2]!=authority['world']['seed']
                    or head[0][3] not in ('integer','null')):
                raise ValueError('inventory head context differs')
            generation=head[0][1]
            result.update(metadata=metadata,head_generation=generation,source=authority)
            result['pages']={key:db.execute('PRAGMA main.'+key).fetchone()[0]
                for key in ('page_size','page_count','freelist_count')}
            for table,namespace,payload,interval in TABLES:
                check_time();begin=time.monotonic()
                key=("CASE WHEN typeof("+namespace+")='text' AND length(CAST("+namespace+
                    ' AS BLOB)) BETWEEN 1 AND 1024 THEN '+namespace+' END') if namespace else "'all'"
                visible='valid_from<=? AND (valid_to IS NULL OR ?<valid_to)' if interval else '1'
                length='length('+payload+')' if payload else '0'
                sql=('SELECT '+key+',count(*),COALESCE(sum('+length+'),0),COALESCE(max('+length+'),0),'
                    'COALESCE(sum(CASE WHEN '+visible+' THEN 1 ELSE 0 END),0),'
                    'COALESCE(sum(CASE WHEN '+visible+' THEN '+length+' ELSE 0 END),0) FROM main.'+table+
                    (' GROUP BY '+namespace if namespace else '')+' LIMIT ?')
                params=(*(generation,generation)*2,MAX_NAMESPACES+1) if interval else (MAX_NAMESPACES+1,)
                rows=db.execute(sql,params).fetchmany(MAX_NAMESPACES+1)
                if len(rows)>MAX_NAMESPACES:raise ValueError('inventory namespace budget exceeded')
                groups=[]
                for name,count,total,largest,current,current_bytes in rows:
                    if type(name) is not str or any(type(n) is not int or n<0 for n in (count,total,largest,current,current_bytes)):
                        raise ValueError('invalid inventory aggregate metadata')
                    groups.append(dict(namespace=name,rows=count,payload_bytes=total,max_payload_bytes=largest,
                        visible_rows=current,visible_payload_bytes=current_bytes))
                result['tables'][table]=dict(namespaces=groups,rows=sum(g['rows'] for g in groups),
                    payload_bytes=sum(g['payload_bytes'] for g in groups),visible_rows=sum(g['visible_rows'] for g in groups),
                    visible_payload_bytes=sum(g['visible_payload_bytes'] for g in groups),
                    max_payload_bytes=max((g['max_payload_bytes'] for g in groups),default=0),wall_seconds=time.monotonic()-begin)
                publish(table+'-')
        except sqlite3.OperationalError as exc:
            if interrupted:raise TimeoutError('inventory SQL budget exhausted') from exc
            raise
        finally:db.close()
        standalone();check_time()
        if r.file_hash(path)!=database['sha256']:raise ValueError('inventory source changed')
        check_time();result.update(status='complete',source_unchanged=True)
        return result
    except BaseException as exc:
        failure=exc
        result.update(status='timeout' if isinstance(exc,TimeoutError) else 'error',
            censored=isinstance(exc,TimeoutError),error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        result['wall_seconds']=time.monotonic()-started
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['resources']=dict(process_peak_rss_bytes=peak if sys.platform=='darwin' else peak*1024,
            meaning='whole-process high water including transport/setup; not an independent inventory peak')
        if path.is_file():result['resources'].update(source_allocated_bytes=path.stat().st_blocks*512,
            disk_free_bytes=shutil.disk_usage(path.parent).free)
        try:publish()
        except BaseException as exc:
            if failure is None:raise
            failure.add_note('inventory diagnostic publication failed: '+str(exc))


def launch(root,config,*,expected_sha):
    from simulation import construction_mature_continuation_stages as stages
    root=Path(root).resolve();evidence=root/'evidence'
    try:
        if config.get('schema')!='ate-stage06-proof-preflight-request/1' or config.get('operation')!='inventory-only':
            raise ValueError('invalid proof preflight request')
        if os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('preflight rerun requires a new request')
        _budget(config['inventory_budget_seconds'])
        identity=check_source(Path.cwd(),config,expected_sha)
        original=r.load_receipt(ORIGINAL_LAUNCH)
        if original['candidate_database']!=config['database']:raise ValueError('preflight differs from original accepted source')
        authority=stages.mature_authority()
        world=dict(seed=authority.source_config['seed'],year=original['expected_previous_year'])
        pin=dict(store_identity=authority.store_identity,captured_head=original['expected_previous_generation'])
        if not r.same(config.get('world'),world) or not r.same(config.get('pin'),pin):
            raise ValueError('preflight world/pin request differs from original accepted source')
        required=config['database']['bytes']+PIN.archive_bytes+6*1024**3
        if shutil.disk_usage(root).free<required:raise ValueError('insufficient source/archive/preflight disk headroom')
        r.publish_receipt(evidence/'launch.json',dict(request=config,execution=identity,acceptance='not-run',required_free_bytes=required))
        performance,transport=prepare_retained(root,config,identity,
            r.ArtifactRef.from_dict(original['inputs']['candidate']),
            r.ArtifactRef.from_dict(original['inputs']['previous']),original['candidate_database'],authority)
        r.publish_receipt(evidence/'source-authority.json',performance)
        r.publish_receipt(evidence/'source-transport.json',transport)
        return inspect_database(root/'source/candidate.sqlite',performance,
            budget_seconds=config['inventory_budget_seconds'],output=evidence/'result.json',execution=identity)
    except BaseException as exc:
        try:r.publish_receipt(evidence/'launch-error.json',dict(status='error',acceptance='not-run',
            error=type(exc).__name__+': '+str(exc)))
        except BaseException as failure:exc.add_note('preflight error receipt failed: '+str(failure))
        raise


def record_exit(root,status):
    if type(status) is not int:raise ValueError('invalid preflight command status')
    evidence=Path(root)/'evidence';result=evidence/'result.json'
    if status==0 and (not result.exists() or r.load_receipt(result).get('status')!='complete'):
        raise ValueError('successful command lacks a complete inventory')
    row=dict(schema='ate-stage06-proof-preflight-exit/1',exit_status=status,
        status='complete' if status==0 else 'timeout' if status in (124,137,143) else 'error',
        censored=status in (124,137,143),acceptance='not-run')
    r.publish_receipt(evidence/'command-exit.json',row)
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','record-exit'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--status',type=int)
    args=parser.parse_args()
    if args.command=='record-exit':record_exit(args.root,args.status)
    else:
        if args.config is None:parser.error('run requires --config')
        launch(args.root,r.load_receipt(args.config),expected_sha=os.environ['GITHUB_SHA'])
