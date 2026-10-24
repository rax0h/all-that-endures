"""Actual unified content/ordinary/scope saves at1k/10k/100k inventories."""
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
from simulation.tests.proof_publication_fixtures import make_publication_store,commit_publication,next_authorities,read_version,read_event,metadata
from ate_sim.persistence_proof_record import read_record_proof_bytes
from ate_sim.persistence_proof_scope import read_scope_certificate
from ate_sim.persistence_proof_occurrence import GroupScope
from ate_sim.persistence_proof_occurrence_seek import read_occurrence_seek_page

SIZES=(1000,10000,100000)
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def measure(store,operation):
    counts=dict(selected_version_payload=0,selected_ordinary_payload=0,selected_event_payload=0,unrelated_payload=0,body_size_probes=0,proof=0,other=0);steps=0
    def trace(sql):
        sql=sql.lower()
        if not sql.lstrip().startswith('select'):return
        source=next((name for name in ('lazy_record_versions','ate_retained_records','records','segments') if 'from '+name in sql),None)
        if source and re.search(r'\bpayload\b',sql):
            if 'then 1 else 0 end' in sql:counts['body_size_probes']+=1;return
            selected="namespace='people'" in sql or "namespace='ordinary'" in sql or "namespace='events'" in sql and any('ordinal='+str(n) in sql for n in (0,1000001))
            if not selected:counts['unrelated_payload']+=1
            else:counts['selected_event_payload' if source=='segments' else 'selected_version_payload' if source=='lazy_record_versions' else 'selected_ordinary_payload']+=1
        elif any('from '+name in sql for name in ('ate_proof_nodes','ate_ordered_seek_nodes','ate_scope_descriptors','ate_scope_generations','ate_record_roots','ate_content_generations')):counts['proof']+=1
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
    if counts['unrelated_payload'] or counts['proof']>1536 or peak>=2*1024*1024 or steps+99>=150000 or store._payload_reads:raise ValueError('unified content bounded-work gate failed: '+str(observed))
    return result,observed


def selected(store,pin,a,*,new=False):
    version=read_version(store,pin,a);event=read_event(store,pin,a,1000001 if new else 0)
    ordinary=read_record_proof_bytes(store,pin,*a.record,'ordinary',store.codec.encode(0),expected_record_schema=1)
    scope,expected=read_scope_certificate(store,pin,*a.scope,GroupScope(2 if new else 1))
    group=read_occurrence_seek_page(store,pin,scope,expected)
    return version,event,ordinary,group


def case(output,size,source):
    start=time.perf_counter();store,pin,a=make_publication_store(output/f'publication-{size}.sqlite',size)
    try:
        construction=time.perf_counter()-start
        if a.content[0].versions.count!=size+1 or a.content[0].events.count!=size+1 or tuple(r.count for r in a.scope[0].roots)!=(size+1,)*4:raise ValueError('unified construction inventory mismatch')
        store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE');store.db.execute('PRAGMA temp.cache_size=-2048')
        old=store.capture_pin();before,current=measure(store,lambda:selected(store,pin,a))
        if before[0].payload!=store.codec.encode({'wealth':1}) or before[1].payload!=store.codec.encode(['first']):raise ValueError('initial selected content mismatch')
        receipts.publish_receipt(output/f'constructed-{size}.json',dict(source=source,size=size,full_construction_seconds=construction,current=current))
        result,save=measure(store,lambda:commit_publication(store,pin,a,preparation_budget=(64,65536)))
        if result.commit.outcome!='committed' or result.commit.generation!=2 or result.certificate.events.count!=size+2:raise ValueError('actual unified commit mismatch')
        new=next_authorities(result)
        if result.commit!=result.scope.commit or result.commit!=result.scope.record.commit:raise ValueError('components did not share existing receipt')
        after,successor=measure(store,lambda:selected(store,result.commit.pin,new,new=True));retained,previous=measure(store,lambda:selected(store,old,a))
        if (retained[0].payload,retained[0].memberships,retained[0].record_schema,retained[0].valid_from)!=(before[0].payload,before[0].memberships,before[0].record_schema,before[0].valid_from) or retained[0].valid_to!=2 or retained[1:]!=before[1:]:raise ValueError('retained selected content mismatch')
        # valid_to changes when a version closes; immutable payload/membership
        # bytes and content identity remain exact at the retained pin.
        if (after[0].payload!=store.codec.encode({'wealth':2}) or after[1].payload!=store.codec.encode(['second'])
                or after[2].payload!=store.codec.encode({'value':2}) or after[3].rows[0].incarnation_id!=2):raise ValueError('successor selected content mismatch')
        if any(obs['checked_payloads']!=3 for obs in (current,successor,previous)):raise ValueError('raw selection did not check exactly selected bodies')
        store.release_pin(old)
        shared,metadata_save=measure(store,lambda:commit_publication(store,result.commit.pin,new,token='metadata',version_changes=(),identity_changes=(),changes=(),new_segments=(),metadata=metadata(3)))
        if (shared.certificate.versions,shared.certificate.events)!=(result.certificate.versions,result.certificate.events):raise ValueError('metadata save rewrote content roots')
        if shared.scope.certificate.roots!=result.scope.certificate.roots or shared.scope.record.certificate.root!=result.scope.record.certificate.root:raise ValueError('metadata save rewrote unchanged component roots')
        return dict(source=source,size=size,status='complete',exact=True,full_fixture_and_audited_bootstrap_seconds=construction,
            current=current,actual_unified_save=save,retained=previous,successor=successor,metadata_only_save=metadata_save,
            database_bytes=(output/f'publication-{size}.sqlite').stat().st_size,
            process_lifetime_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
    finally:store.close()


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked execution source')
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=receipts.file_hash(__file__),
        fixture_sha256=receipts.file_hash('simulation/tests/proof_publication_fixtures.py'),python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(source=source,sizes=SIZES,schema='ate-content-publication-source/1',sqlite_main_cache_kib=2048,
        sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_proof_cache_bytes=0,limits=[
            'Full fixture and all explicit full-audited component bootstraps outside operation timers.',
            'Actual existing save changes one version/membership/placement/ordinary body and appends one event.',
            'All implemented roots share one existing transaction/receipt; this is not the complete seven-root manifest.',
            'No World admission or full World/year performance acceptance.']))
    results=[]
    for size in SIZES:
        row=case(output,size,source);results.append(row);receipts.publish_receipt(output/f'size-{size}.json',row)
        print(f"{size}: actual unified save {row['actual_unified_save']['seconds']*1000:.2f}ms; unrelated bodies0; current/retained exact",flush=True)
    receipts.publish_receipt(output/'summary.json',dict(source=source,status='complete',schema='ate-content-publication-summary/1',results=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);run(parser.parse_args().output)
