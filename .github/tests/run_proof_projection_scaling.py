"""Fixed physical-owner projection amid growing unrelated physical bodies."""
import argparse
import platform
from pathlib import Path
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc
from simulation import continuation_receipts as receipts
from simulation.tests.proof_projection_fixtures import (
    PAGE,PAGE_VALUE,PAGE_PLACEMENTS,make_projection_store,read_projection,authorities,metadata)
from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference

SIZES=(1000,10000,100000)


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def measure(store,operation):
    store.reset_diagnostics();steps=0;counts=dict(selected_payload=0,unrelated_payload=0,proof=0,other=0)
    target=store.codec.encode((1,0)).hex()
    def progress():
        nonlocal steps
        steps+=100;return 0
    def trace(sql):
        sql=sql.lower()
        if not sql.lstrip().startswith('select'):return
        if 'from lazy_record_versions' in sql and 'then payload end' in sql:
            counts['selected_payload' if f"typed_key=x'{target}'" in sql and PAGE in sql else 'unrelated_payload']+=1
        elif 'from ate_proof_nodes' in sql or 'from ate_ordered_seek_nodes' in sql:counts['proof']+=1
        else:counts['other']+=1
    store.db.set_trace_callback(trace);store.db.set_progress_handler(progress,100);tracemalloc.start()
    try:
        started=time.perf_counter();result=operation();seconds=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();store.db.set_trace_callback(None);store.db.set_progress_handler(None,0)
    observed=dict(seconds=seconds,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps+99,selects=counts,
        source_payload_checks=store._payload_check_reads,source_payload_check_bytes=store._payload_check_bytes,
        store_world_decode_counter=store._payload_reads)
    if (counts['selected_payload']!=1 or counts['unrelated_payload'] or observed['source_payload_checks']!=1
            or observed['store_world_decode_counter'] or counts['proof']>512 or steps+99>=20000 or peak>=2*1024*1024):
        raise ValueError('fixed projection bounded-work gate failed: '+str(observed))
    return result,observed


def case(output,size,source):
    started=time.perf_counter();store,pin,pairs=make_projection_store(output/f'projection-{size}.sqlite',size)
    try:
        setup=time.perf_counter()-started
        store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE');store.db.execute('PRAGMA temp.cache_size=-2048')
        old=store.capture_pin();initial,current_observed=measure(store,lambda:read_projection(store,pin,pairs))
        if initial.reference_count!=4 or initial.source.payload!=store.codec.encode(PAGE_VALUE):raise ValueError('initial projection mismatch')
        receipts.publish_receipt(output/f'current-{size}.json',dict(source=source,size=size,exact=True,construction_seconds=setup,current=current_observed))
        started=time.perf_counter()
        writer=store.commit(pin,commit_token='changed-owner',version_changes=(VersionChange(PAGE,(1,0),(HistoryReference('list',6),)),),
            identity_changes=tuple(IdentityOccurrenceChange(PAGE,(1,0),path,delete=True) for path,_ in PAGE_PLACEMENTS[1:])+
                (IdentityOccurrenceChange(PAGE,(1,0),PAGE_PLACEMENTS[0][0],6),),
            next_incarnation_id=size+10,changes=(),new_segments=(),metadata=metadata(2)).pin
        transition=time.perf_counter()-started
        retained,old_observed=measure(store,lambda:read_projection(store,old,pairs))
        if retained.reference_count!=4 or retained.source.payload!=store.codec.encode(PAGE_VALUE):raise ValueError('old projection mismatch')
        started=time.perf_counter();new_pairs=authorities(store,writer);successor_construction=time.perf_counter()-started
        new,new_observed=measure(store,lambda:read_projection(store,writer,new_pairs))
        if new.reference_count!=1 or new.source.payload!=store.codec.encode((HistoryReference('list',6),)):raise ValueError('new projection mismatch')
        return dict(schema='ate-owner-projection-scaling/1',source=source,size=size,status='complete',exact=True,
            fixture_and_verified_construction_seconds=setup,genuine_owner_transition_seconds=transition,
            full_successor_construction_seconds=successor_construction,current=current_observed,old_pin=old_observed,successor=new_observed,
            database_bytes=(output/f'projection-{size}.sqlite').stat().st_size,
            process_lifetime_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    finally:store.close()


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked execution source')
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=receipts.file_hash(__file__),
        fixture_sha256=receipts.file_hash('simulation/tests/proof_projection_fixtures.py'),python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(schema='ate-owner-projection-source/1',source=source,sizes=SIZES,owner_references=4,successor_references=1,
        sqlite_main_cache_kib=2048,sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_proof_cache_bytes=0,
        instrumentation='tracemalloc/SQL trace/SQLite VM100 ticks',limits=['Selected storage body privately decoded; store World decode counter excludes this parser.',
            'Test-only full row construction is not complete production topology authority.','No World open/save/year timing.']))
    results=[]
    for size in SIZES:
        row=case(output,size,source);receipts.publish_receipt(output/f'size-{size}.json',row);results.append(row)
        print(f'{size}: exact current/old/successor; selected payload checks1 each; unrelated payload SELECTs0; VM<='+
            '/'.join(str(row[k]['sqlite_vm_step_upper_bound']) for k in ('current','old_pin','successor')),flush=True)
    receipts.publish_receipt(output/'summary.json',dict(schema='ate-owner-projection-summary/1',source=source,status='complete',results=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);run(parser.parse_args().output)
