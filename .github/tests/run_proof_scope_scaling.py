"""Actual scoped point saves and retained root selection at1k/10k/100k."""
import argparse
from pathlib import Path
import platform
import re
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc
from simulation import continuation_receipts as receipts
from simulation.tests.proof_scope_fixtures import make_scope_store,scope_module,scopes,read_scope,commit_scope,metadata
from ate_sim.persistence_proof_occurrence import GroupScope
from ate_sim.persistence_proof_query import QueryScope
from ate_sim.persistence_proof_occurrence_seek import read_occurrence_seek_page
from ate_sim.persistence_proof_query_seek import read_query_seek_page

SIZES=(1000,10000,100000)
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def measure(store,operation):
    counts=dict(selected_payload=0,unrelated_payload=0,proof=0,other=0,descriptor_write_attempts=0);steps=0
    def trace(sql):
        sql=sql.lower()
        if sql.startswith('insert or ignore into ate_scope_descriptors'):counts['descriptor_write_attempts']+=1
        if not sql.lstrip().startswith('select'):return
        if re.search(r'\bpayload\b',sql) and any('from '+table in sql for table in ('lazy_record_versions','records','ate_retained_records')):
            counts['selected_payload' if "namespace='people'" in sql else 'unrelated_payload']+=1
        elif any('from '+table in sql for table in ('ate_proof_nodes','ate_ordered_seek_nodes','ate_scope_descriptors','ate_scope_generations')):counts['proof']+=1
        else:counts['other']+=1
    def progress():
        nonlocal steps
        steps+=100;return 0
    store.reset_diagnostics();store.db.set_trace_callback(trace);store.db.set_progress_handler(progress,100);tracemalloc.start()
    try:
        start=time.perf_counter();result=operation();seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();store.db.set_trace_callback(None);store.db.set_progress_handler(None,0)
    observed=dict(seconds=seconds,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps+99,sql=counts,
        checked_payloads=store._payload_check_reads,checked_payload_bytes=store._payload_check_bytes,world_payload_decodes=store._payload_reads)
    if counts['unrelated_payload'] or counts['proof']>1024 or counts['descriptor_write_attempts']>6 or peak>=2*1024*1024 or steps+99>=100000 or store._payload_reads:
        raise ValueError('scope bounded-work gate failed: '+str(observed))
    return result,observed


def selected_pages(store,pin,pair,*,new=False):
    owner,group,query=scopes(store)
    if new:group,query=GroupScope(2),QueryScope('people','cohort',store.codec.encode('new'))
    result=[]
    for scope in (owner,group,query):
        cert,expected=read_scope(store,pin,pair,scope)
        p=(read_query_seek_page if type(scope) is QueryScope else read_occurrence_seek_page)(store,pin,cert,expected)
        result.append(p)
    return tuple(result)


def case(output,size,source):
    start=time.perf_counter();store,pin,pair=make_scope_store(output/f'scope-{size}.sqlite',size)
    try:
        construction=time.perf_counter()-start
        if tuple(r.count for r in pair[0].roots)!=(size+1,)*4:raise ValueError('scope inventory construction incomplete')
        store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE');store.db.execute('PRAGMA temp.cache_size=-2048')
        old=store.capture_pin();before,current=measure(store,lambda:selected_pages(store,pin,pair))
        if before[1].rows[0].incarnation_id!=1 or before[2].positions!=((store.codec.encode(0),0),):raise ValueError('initial scoped source mismatch')
        receipts.publish_receipt(output/f'constructed-{size}.json',dict(source=source,size=size,full_construction_seconds=construction,current=current))
        result,save=measure(store,lambda:commit_scope(store,pin,pair,preparation_budget=(64,65536)))
        if result.commit.outcome!='committed' or result.commit.generation!=2:raise ValueError('actual scoped commit failed')
        new_pair=result.certificate,result.commitment
        after,successor=measure(store,lambda:selected_pages(store,result.commit.pin,new_pair,new=True))
        retained,previous=measure(store,lambda:selected_pages(store,old,pair))
        if retained!=before or after[1].rows[0].incarnation_id!=2 or after[2].positions!=((store.codec.encode(0),7),):raise ValueError('retained scoped source mismatch')
        if any(x['sql']['selected_payload'] or x['checked_payloads'] for x in (current,successor,previous)):raise ValueError('raw scope pages read owner bodies')
        # A separate actual metadata/allocator save must share all four roots
        # and write no descriptors despite size+1 nonempty scopes per directory.
        store.release_pin(old)
        shared,metadata_save=measure(store,lambda:commit_scope(store,result.commit.pin,new_pair,token='allocator',version_changes=(),identity_changes=(),metadata=metadata(3),next_incarnation_id=size+100))
        if shared.certificate.roots!=result.certificate.roots or metadata_save['sql']['descriptor_write_attempts']!=0:raise ValueError('unchanged scopes rewritten by allocator/generation')
        return dict(source=source,size=size,status='complete',exact=True,full_fixture_and_audited_bootstrap_seconds=construction,
            current=current,actual_point_save=save,retained=previous,successor=successor,allocator_only_save=metadata_save,
            database_bytes=(output/f'scope-{size}.sqlite').stat().st_size,
            process_lifetime_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    finally:store.close()


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked execution source')
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=receipts.file_hash(__file__),
        fixture_sha256=receipts.file_hash('simulation/tests/proof_scope_fixtures.py'),python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(source=source,sizes=SIZES,schema='ate-scope-proof-source/1',sqlite_main_cache_kib=2048,
        sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_proof_cache_bytes=0,limits=[
            'Full fixture/full audit and four complete scope directories outside measured operations.',
            'Existing actual commit changes one lazy owner membership and one placement; complete old query-owner witness checked.',
            'No complete generation manifest, World admission or full World performance result.']))
    results=[]
    for size in SIZES:
        row=case(output,size,source);results.append(row);receipts.publish_receipt(output/f'size-{size}.json',row)
        print(f"{size}: scoped point save {row['actual_point_save']['seconds']*1000:.2f}ms; unrelated bodies0; allocator root sharing exact",flush=True)
    receipts.publish_receipt(output/'summary.json',dict(source=source,status='complete',schema='ate-scope-proof-summary/1',results=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);run(parser.parse_args().output)
