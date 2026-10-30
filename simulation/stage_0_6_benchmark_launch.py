"""Reuse authenticated mature transport; never reinterpret the historical source authority."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from simulation import continuation_receipts as r,continuation_checkpoint as checkpoint,construction_mature_continuation_stages as stages
from simulation.stage_0_6_mature_benchmark import check_source
from simulation.stage_0_6_retained_producer import PIN
from simulation.stage_0_6_retained_launch import prepare_retained


def prepare(root,config):
    root=Path(root).resolve()
    r.publish_receipt(root/'evidence/launch.json',config)
    identity=check_source(Path.cwd(),config,os.environ['GITHUB_SHA'])
    if os.environ.get('GITHUB_RUN_ATTEMPT')!='1':
        raise ValueError('measurement rerun requires a new reviewed launch')
    launch=r.load_receipt('simulation/stage_0_5_save1002_preflight.json')
    source=r.ArtifactRef.from_dict(launch['inputs']['candidate'])
    accepted=r.ArtifactRef.from_dict(launch['inputs']['previous'])
    database=launch['candidate_database']
    if database!=config['database']:
        raise ValueError('fixture differs from reviewed launch')
    required=2*database['bytes']+PIN.archive_bytes+8*1024**3
    if shutil.disk_usage(root).free<required:
        raise ValueError('insufficient retained source/copy/archive/upload disk headroom')
    authority=stages.mature_authority()
    performance,transport=prepare_retained(
        root,config,identity,source,accepted,database,authority)
    r.publish_receipt(root/'evidence/source-authority.json',performance)
    r.publish_receipt(root/'evidence/source-transport.json',dict(
        **transport,producer=dict(
            run_id=os.environ['GITHUB_RUN_ID'],sha=os.environ['GITHUB_SHA'])))
    return performance


def summarize(root,config):
    root=Path(root);rows=[];measured=r.load_receipt(root/'evidence/current/result.json')
    fresh_path=root/'evidence/fresh-restore.json';fresh=r.load_receipt(fresh_path) if fresh_path.exists() else {}
    historical=config['historical_seconds'];targets=config['targets_seconds']
    for name in ('open_total','first_step','warm_step','save','fresh_open_total','logical_digest'):
        phase=(fresh if name in ('fresh_open_total','logical_digest') else measured).get('phases',{}).get(name,{})
        status=phase.get('status','not reached');seconds=phase.get('wall_seconds');target=targets.get(name)
        result='not measured' if status!='complete' else ('no defined target' if target is None else 'pass' if seconds<=target else 'fail')
        rows.append(dict(operation=name,historical_seconds=historical.get(name),seconds=seconds,target_seconds=target,status=status,result=result,improvement_percent=(100*(1-seconds/historical[name]) if status=='complete' and name in historical else None),remaining_factor=(seconds/target if status=='complete' and target is not None else None),comparison_limit='different runner/cache; historical default path and current default path, no proof-format activation'))
    r.publish_receipt(root/'evidence/comparison.json',dict(schema='ate-stage06-comparison/1',runtime=measured['runtime'],rows=rows,measurement_complete=measured['status']=='complete' and fresh.get('status')=='complete',performance_targets_met=measured['status']=='complete' and fresh.get('status')=='complete' and all(row['result']=='pass' for row in rows if row['target_seconds'] is not None)))
    lines=['# Stage0.6 current mature measurement','',f"SHA: {measured['runtime']['head']}; runtime: {measured['runtime']['committed_tree']}",'','| Operation | Oct21 seconds | Current seconds | Working target seconds | Result |','|---|---:|---:|---:|---|']
    for row in rows:
        displayed=dict(row)
        if row['status']=='timeout':displayed['seconds']=('>='+str(row['seconds']) if row['seconds'] is not None else 'not recorded')+' (censored timeout)'
        lines.append('| '+ ' | '.join(str(displayed[k]) if displayed[k] is not None else 'not defined/measured' for k in ('operation','historical_seconds','seconds','target_seconds','result'))+' |')
    lines+=['','Open total includes database initialization and state restoration; those subphases are reported separately in result.json and must not be added to the inclusive total. Fresh digest/checks run separately after operational timings. Timeouts are censored observations, never successful timings. Full store scrub and millennium-generation benchmark are separate, not run here. Physical IO counters are process-level kernel accounting, not application payload read counts.','']
    (root/'evidence/summary.md').write_text('\n'.join(lines))
    return measured['status']=='complete' and fresh.get('status')=='complete'

def record_command_exit(root,phase,status):
    if phase not in ('measure','restore','sample') or type(status) is not int:raise ValueError('invalid command exit')
    root=Path(root);directory=root/'evidence/current' if phase=='measure' else root/'evidence/sample' if phase=='sample' else root/'evidence'
    output=directory/'result.json' if phase in ('measure','sample') else directory/'fresh-restore.json'
    value=dict(schema='ate-stage06-command-exit/1',command=phase,exit_status=status,status='complete' if status==0 else 'timeout' if status in (124,137) else 'error',censored=status in (124,137))
    r.publish_receipt(root/'evidence'/('command-exit-'+phase+'.json'),value)
    if status!=0 and not output.exists():
        phases={}
        for p in directory.glob('phase-progress-*.json'):
            phases.update(r.load_receipt(p).get('phases',{}))
        for p in directory.glob('phase-start-*.json'):
            start=r.load_receipt(p);name=start['phase']
            if name not in phases or phases[name].get('status')=='running':
                phases[name]=dict(status=value['status'],censored=value['censored'],budget_seconds=start['budget_seconds'],elapsed_since_phase_start_at_diagnostic_seconds=max(0.,__import__('time').time()-start['started_unix']),diagnostic='process terminated; CPU/IO/final phase time unavailable')
        r.publish_receipt(output,dict(schema='ate-stage06-terminated/1',status=value['status'],censored=value['censored'],runtime=__import__('simulation.profile_stage_0_5_performance',fromlist=['_runtime_identity'])._runtime_identity(),phases=phases,**(dict(acceptance='not-run',profile_available=(directory/'first_step.prof').is_file(),profile_diagnostic='forced termination may prevent profile flush; inspect available journals') if phase=='sample' else {}),error='measurement command terminated; see command exit and phase journals'))
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','summarize','record-exit']);p.add_argument('--root',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--phase',choices=['measure','restore','sample']);p.add_argument('--status',type=int);a=p.parse_args();c=r.load_receipt(a.config)
    try:
        result=prepare(a.root,c) if a.command=='prepare' else record_command_exit(a.root,a.phase,a.status) if a.command=='record-exit' else summarize(a.root,c)
    except Exception as exc:
        r.publish_receipt(a.root/'evidence'/('launch-error-'+a.command+'.json'),dict(status='error',phase=a.command,error_type=type(exc).__name__,error=str(exc)))
        raise
    if result is False:raise SystemExit(1)
