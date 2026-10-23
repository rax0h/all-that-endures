"""Root-selected group joins and retained queries under real archive growth."""
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
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.incremental_store import Membership
from ate_sim.persistence_proof_query import QueryScope
from ate_sim.persistence_proof_query_seek import read_query_seek_page
from ate_sim import persistence_lazy_identity_catalog as catalog
from simulation.tests.proof_identity_group_fixtures import make_group_store,read_group,group_authorities,reanchor
from simulation.tests.proof_query_fixtures import make_store,metadata
from simulation.tests.proof_query_seek_fixtures import construct_query_seek

SIZES=(1000,10000,100000)


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def configure(store):
    store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE');store.db.execute('PRAGMA temp.cache_size=-2048')


def measure(store,operation,*,query=False):
    counts=dict(metadata_payload=0,unrelated_payload=0,proof=0,other=0);steps=0
    def trace(sql):
        sql=sql.lower()
        if not sql.lstrip().startswith('select'):return
        if 'from lazy_record_versions' in sql and 'then payload end' in sql:
            counts['metadata_payload' if any("'"+ns+"'" in sql for ns in catalog.CATALOG_NAMESPACES) else 'unrelated_payload']+=1
        elif 'from ate_proof_nodes' in sql or 'from ate_ordered_seek_nodes' in sql:counts['proof']+=1
        else:counts['other']+=1
    def progress():
        nonlocal steps
        steps+=100;return 0
    store.reset_diagnostics();store.db.set_trace_callback(trace);store.db.set_progress_handler(progress,100);tracemalloc.start()
    try:
        start=time.perf_counter();result=operation();seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();store.db.set_trace_callback(None);store.db.set_progress_handler(None,0)
    observed=dict(seconds=seconds,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps+99,selects=counts,
        checked_source_payloads=store._payload_check_reads,checked_source_bytes=store._payload_check_bytes,
        store_world_decode_counter=store._payload_reads)
    if (counts['unrelated_payload'] or counts['proof']>1024 or peak>=2*1024*1024 or steps+99>=100000
            or store._payload_reads or store._payload_check_reads!=counts['metadata_payload']
            or query and counts['metadata_payload']):raise ValueError('bounded group/query gate failed: '+str(observed))
    return result,observed


def group_case(output,size,source):
    start=time.perf_counter();store,pin,pairs=make_group_store(output/f'group-{size}.sqlite',size)
    try:
        setup=time.perf_counter()-start;configure(store);old=store.capture_pin()
        literal=catalog.IdentityCatalog(store).read_identity_group(pin,1)
        encoded=tuple((store.codec.encode(t),store.codec.encode(a)) for t,a in literal.links)
        initial,current=measure(store,lambda:read_group(store,pin,pairs))
        if len(initial.occurrences)!=2 or initial.links!=encoded or initial.anchor!=store.codec.encode(literal.anchor):raise ValueError('group literal mismatch')
        receipts.publish_receipt(output/f'group-current-{size}.json',dict(source=source,size=size,exact=True,current=current,construction_seconds=setup))
        start=time.perf_counter();writer=reanchor(store,pin);transition=time.perf_counter()-start
        retained,old_observed=measure(store,lambda:read_group(store,old,pairs))
        if retained!=initial:raise ValueError('retained group mismatch')
        start=time.perf_counter();newpairs=group_authorities(store,writer);construction=time.perf_counter()-start
        successor,new_observed=measure(store,lambda:read_group(store,writer,newpairs))
        if len(successor.occurrences)!=1 or successor.links or successor.anchor!=store.codec.encode((('field','people'),('key',2))):raise ValueError('successor group mismatch')
        return dict(size=size,exact=True,fixture_and_verified_construction_seconds=setup,genuine_transition_seconds=transition,
            full_successor_construction_seconds=construction,current=current,old_pin=old_observed,successor=new_observed,
            database_bytes=(output/f'group-{size}.sqlite').stat().st_size)
    finally:store.close()


def query_case(output,size,source):
    store,pin=make_store(output/f'query-{size}.sqlite');configure(store)
    try:
        scope=QueryScope('people','cohort',store.codec.encode('active'));empty_scope=QueryScope('people','cohort',store.codec.encode('empty'))
        start=time.perf_counter();active=construct_query_seek(store,pin,scope);empty=construct_query_seek(store,pin,empty_scope)
        setup=time.perf_counter()-start;old=store.capture_pin()
        def changes():
            yield VersionChange('people',1,{},memberships=(Membership('cohort','empty',0),))
            for i in range(size):yield VersionChange('people',1000+i,{},memberships=(Membership('cohort','active',i),Membership('cohort','empty',i)))
        start=time.perf_counter();writer=store.commit(pin,commit_token='frontier',version_changes=changes(),changes=(),new_segments=(),metadata=metadata(2)).pin
        transition=time.perf_counter()-start
        populations=store.db.execute('SELECT index_value,count(*) FROM lazy_query_versions WHERE valid_from=2 GROUP BY index_value').fetchall()
        actual=dict(populations)
        if actual.get(scope.index_value)!=size or actual.get(empty_scope.index_value)!=size+1:raise ValueError('newer query populations incorrect')
        old_active,nonempty=measure(store,lambda:read_query_seek_page(store,old,*active,limit=4),query=True)
        old_empty,empty_observed=measure(store,lambda:read_query_seek_page(store,old,*empty,limit=4),query=True)
        enc=store.codec.encode
        if old_active.positions!=((enc(0),0),(enc(0),1),(enc(1),2),(enc(1),3)) or old_empty.positions:raise ValueError('retained query literal mismatch')
        receipts.publish_receipt(output/f'query-old-{size}.json',dict(source=source,size=size,exact=True,newer_active=size,newer_empty=size+1,old_nonempty=nonempty,old_empty=empty_observed))
        start=time.perf_counter();current=construct_query_seek(store,writer,scope);construction=time.perf_counter()-start
        page,new_observed=measure(store,lambda:read_query_seek_page(store,writer,*current,limit=4),query=True)
        if current[0].root.count!=size+14 or page.positions!=((enc(0),0),(enc(1000),0),(enc(0),1),(enc(1001),1)):raise ValueError('current query literal mismatch')
        return dict(size=size,exact=True,initial_verified_construction_seconds=setup,genuine_transition_seconds=transition,
            full_successor_construction_seconds=construction,newer_active=size,newer_empty=size+1,
            old_nonempty=nonempty,old_empty=empty_observed,successor=new_observed,database_bytes=(output/f'query-{size}.sqlite').stat().st_size)
    finally:store.close()


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked execution source')
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=receipts.file_hash(__file__),
        group_fixture_sha256=receipts.file_hash('simulation/tests/proof_identity_group_fixtures.py'),query_fixture_sha256=receipts.file_hash('simulation/tests/proof_query_seek_fixtures.py'),
        python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(schema='ate-group-source/1',source=source,sizes=SIZES,
        sqlite_main_cache_kib=2048,sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_proof_cache_bytes=0,
        limits=['Construction and genuine transitions are separately reported, not timed reader work.',
            'Raw checked metadata privately decoded; no World admission or complete production topology.',
            'No World open/save/year performance acceptance.']))
    results=[]
    for size in SIZES:
        group=group_case(output,size,source);query=query_case(output,size,source)
        row=dict(size=size,group=group,query=query,source=source,status='complete',exact=True,
            process_lifetime_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
        receipts.publish_receipt(output/f'size-{size}.json',row);results.append(row)
        print(f'{size}: exact group current/old/new; metadata payloads'+
            '/'.join(str(group[k]['selects']['metadata_payload']) for k in ('current','old_pin','successor'))+
            '; owner/archive bodies0; old nonempty/empty query VM<='+str(query['old_nonempty']['sqlite_vm_step_upper_bound'])+'/'+str(query['old_empty']['sqlite_vm_step_upper_bound']),flush=True)
    receipts.publish_receipt(output/'summary.json',dict(schema='ate-group-summary/1',source=source,status='complete',results=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);run(parser.parse_args().output)
