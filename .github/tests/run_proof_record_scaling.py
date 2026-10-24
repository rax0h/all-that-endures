"""Actual proof-aware ordinary point save and retained reads at1k/10k/100k."""
import argparse
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc
from simulation import continuation_receipts as receipts
from simulation.tests.proof_record_fixtures import make_record_store,read_record,record_module,metadata
from ate_sim.incremental_store import RecordChange

SIZES=(1000,10000,100000)


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def measure(store,operation):
    counts=dict(selected_mutable_payload=0,selected_retained_payload=0,unrelated_payload=0,proof=0,other=0);steps=0
    def trace(sql):
        sql=sql.lower()
        if not sql.lstrip().startswith('select'):return
        if 'then payload end' in sql:
            selected="namespace='people'" in sql
            if 'from records ' in sql:counts['selected_mutable_payload' if selected else 'unrelated_payload']+=1
            elif 'from ate_retained_records ' in sql:counts['selected_retained_payload' if selected else 'unrelated_payload']+=1
            else:counts['unrelated_payload']+=1
        elif 'from ate_proof_nodes' in sql:counts['proof']+=1
        else:counts['other']+=1
    def progress():
        nonlocal steps
        steps+=100;return 0
    store.reset_diagnostics();store.db.set_trace_callback(trace);store.db.set_progress_handler(progress,100);tracemalloc.start()
    try:
        start=time.perf_counter();result=operation();seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();store.db.set_trace_callback(None);store.db.set_progress_handler(None,0)
    observed=dict(seconds=seconds,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps+99,selects=counts,
        checked_payloads=store._payload_check_reads,checked_payload_bytes=store._payload_check_bytes,store_world_decode_counter=store._payload_reads)
    if (counts['unrelated_payload'] or counts['proof']>512 or peak>=2*1024*1024 or steps+99>=100000
            or store._payload_reads or store._payload_check_reads!=counts['selected_mutable_payload']+counts['selected_retained_payload']):
        raise ValueError('ordinary proof bounded-work gate failed: '+str(observed))
    return result,observed


def case(output,size,source):
    start=time.perf_counter();store,pin,pair=make_record_store(output/f'record-{size}.sqlite',size)
    try:
        construction=time.perf_counter()-start
        store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE');store.db.execute('PRAGMA temp.cache_size=-2048')
        old=store.capture_pin();before,current=measure(store,lambda:read_record(store,pin,pair))
        if before.payload!=store.codec.encode({'wealth':1}):raise ValueError('initial ordinary mismatch')
        receipts.publish_receipt(output/f'constructed-{size}.json',dict(source=source,size=size,full_construction_seconds=construction,current=current))
        r=record_module()
        committed,save=measure(store,lambda:r.commit_record_proof(store,pin,*pair,commit_token='point-edit',
            changes=(RecordChange('people',0,{'wealth':2}),),version_changes=(),new_segments=(),metadata=metadata(2),preparation_budget=(64,65536)))
        if committed.commit.outcome!='committed' or committed.commit.generation!=2 or committed.certificate.root.count!=size+1:
            raise ValueError('actual ordinary proof commit mismatch')
        after,new=measure(store,lambda:read_record(store,committed.commit.pin,(committed.certificate,committed.commitment)))
        retained,previous=measure(store,lambda:read_record(store,old,pair))
        if retained!=before or after.payload!=store.codec.encode({'wealth':2}) or after.last_changed_generation!=2:
            raise ValueError('retained/successor ordinary body mismatch')
        if save['selects']['selected_mutable_payload']!=1 or save['selects']['selected_retained_payload']:
            raise ValueError('save did not check exactly actual selected written body')
        if any(x['selects']['selected_retained_payload']!=1 for x in (current,new,previous)):
            raise ValueError('raw read did not check exactly one retained body')
        if store.read_record('people',0,expected_record_schema=1)!={'wealth':2}:raise ValueError('ordinary default source mismatch')
        return dict(source=source,size=size,status='complete',exact=True,full_fixture_and_audited_bootstrap_seconds=construction,
            current=current,actual_point_save=save,retained=previous,successor=new,database_bytes=(output/f'record-{size}.sqlite').stat().st_size,
            process_lifetime_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    finally:store.close()


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked execution source')
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=receipts.file_hash(__file__),
        fixture_sha256=receipts.file_hash('simulation/tests/proof_record_fixtures.py'),python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(source=source,sizes=SIZES,schema='ate-record-proof-source/1',sqlite_main_cache_kib=2048,
        sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_proof_cache_bytes=0,limits=[
            'Full fixture/full audited bootstrap outside point-save/read timers.',
            'Actual existing LazyRecordStore.commit with one ordinary changed record and atomic root/body publication.',
            'No complete generation manifest, World admission or full World save/year/open timing.']))
    results=[]
    for size in SIZES:
        result=case(output,size,source);results.append(result);receipts.publish_receipt(output/f'size-{size}.json',result)
        print(f"{size}: actual point save {result['actual_point_save']['seconds']*1000:.2f}ms; unrelated bodies0; exact current/retained/successor",flush=True)
    receipts.publish_receipt(output/'summary.json',dict(source=source,status='complete',schema='ate-record-proof-summary/1',results=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);run(parser.parse_args().output)
