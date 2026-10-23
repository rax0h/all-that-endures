"""Immutable index updates and exact old-pin access; no World speed acceptance."""
import argparse
import hashlib
import heapq
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc

from ate_sim.persistence_proof_seek import OrderedSeekMap
from ate_sim.persistence_proof_occurrence import GroupScope,OwnerScope,RawOccurrence
from ate_sim.persistence_proof_occurrence_seek import read_occurrence_seek_page
from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
from simulation import continuation_receipts as receipts
from simulation.tests.proof_occurrence_fixtures import make_occurrence_store,metadata
from simulation.tests.proof_occurrence_seek_fixtures import construct_seek_certificates

SIZES=(1000,10000,100000)


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def value(i):return hashlib.sha256(str(i).encode()).digest()


def measure(db,operation,store=None):
    if store is not None:store.reset_diagnostics()
    counters=dict(proof=0,occurrence=0,payload=0,other=0);steps=0
    def progress():
        nonlocal steps
        steps+=100;return 0
    def trace(sql):
        if not sql.lstrip().upper().startswith('SELECT'):return
        category=('proof' if 'FROM ate_ordered_seek_nodes' in sql else 'occurrence' if 'FROM lazy_identity_occurrence_versions' in sql else
                  'payload' if any('FROM '+t in sql for t in ('records','lazy_record_versions','segments')) else 'other')
        counters[category]+=1
    db.set_progress_handler(progress,100);db.set_trace_callback(trace);tracemalloc.start()
    try:
        started=time.perf_counter();result=operation();elapsed=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();db.set_trace_callback(None);db.set_progress_handler(None,0)
    return result,dict(wall_seconds=elapsed,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps+99,sql_selects=counters,
        payload_checks=0 if store is None else store._payload_check_reads,payload_decodes=0 if store is None else store._payload_reads)


def index_case(output,size,source):
    db=sqlite3.connect(output/f'index-{size}.sqlite',isolation_level=None)
    db.execute('PRAGMA cache_size=-2048');db.execute('PRAGMA temp_store=FILE');db.execute('PRAGMA temp.cache_size=-2048')
    m=OrderedSeekMap(db,b'seek-scaling');db.execute('BEGIN');m.create_schema();started=time.perf_counter()
    root=m.build((i.to_bytes(8,'big'),value(i)) for i in range(size));db.commit()
    construction=dict(seconds=time.perf_counter()-started,node_io=m.diagnostics())
    assert construction['node_io']['written_nodes']<=2*size-1
    receipts.publish_receipt(output/f'index-constructed-{size}.json',dict(source=source,size=size,construction=construction))
    m.reset_diagnostics();changed_key=(500).to_bytes(8,'big');new_value=value('replacement')
    def edit():
        db.execute('BEGIN')
        try:changed=m.set(root,changed_key,new_value);db.commit();return changed
        except BaseException:db.rollback();raise
    changed,observed=measure(db,edit);observed['node_io']=m.diagnostics()
    assert m.get(root,changed_key)==value(500) and m.get(changed,changed_key)==new_value
    assert m.page(changed,after=(499).to_bytes(8,'big'),limit=2)==((changed_key,new_value),((501).to_bytes(8,'big'),value(501)))
    if (observed['node_io']['read_nodes']>512 or observed['node_io']['written_nodes']>256
            or observed['python_peak_bytes']>=2*1024*1024):raise ValueError('ordered index point work budget failed')
    receipts.publish_receipt(output/f'index-point-{size}.json',dict(source=source,size=size,point=observed,exact=True))
    started=time.perf_counter();m.verify(root);m.verify(changed);verify_seconds=time.perf_counter()-started
    db.execute('BEGIN');started=time.perf_counter()
    rebuilt=m.build((i.to_bytes(8,'big'),new_value if i==500 else value(i)) for i in range(size));db.commit()
    rebuild_seconds=time.perf_counter()-started
    if rebuilt!=changed:raise ValueError('ordered index canonical rebuild mismatch')
    if db.execute('SELECT count(*) FROM ate_ordered_seek_paths').fetchone()[0]:raise ValueError('update spool not cleaned')
    row=dict(source=source,size=size,exact=True,construction=construction,point=observed,
        verify_seconds=verify_seconds,rebuild_seconds=rebuild_seconds,database_bytes=Path(output/f'index-{size}.sqlite').stat().st_size)
    db.close();return row


def source_case(output,size,source):
    started=time.perf_counter();store,pin=make_occurrence_store(output/f'source-{size}.sqlite',2*size)
    try:
        store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE');store.db.execute('PRAGMA temp.cache_size=-2048')
        fixture_seconds=time.perf_counter()-started;started=time.perf_counter()
        group,owner,empty=construct_seek_certificates(store,pin,(GroupScope(1),OwnerScope('people',store.codec.encode(0)),GroupScope(2)))
        construction_seconds=time.perf_counter()-started;old=store.capture_pin()
        original=read_occurrence_seek_page(store,old,*group).rows
        original_owner=read_occurrence_seek_page(store,old,*owner).rows
        def frontier():
            yield IdentityOccurrenceChange('people',0,(('field','other'),),2)
            yield IdentityOccurrenceChange('people',1,(('field','shared'),),delete=True)
            for i in range(2*size):yield IdentityOccurrenceChange('archive',i,(),1 if i<size else 2)
        started=time.perf_counter()
        writer=store.commit(pin,commit_token='newer',version_changes=(),identity_changes=frontier(),
            next_incarnation_id=2*size+3,changes=(),new_segments=(),metadata=metadata(2)).pin
        transition_seconds=time.perf_counter()-started
        newer_counts=store.db.execute("SELECT incarnation_id,count(*) FROM lazy_identity_occurrence_versions "
            "WHERE owner_namespace='archive' AND valid_from=2 GROUP BY incarnation_id ORDER BY incarnation_id").fetchall()
        if newer_counts!=[(1,size),(2,size)]:raise ValueError('both old scopes must face the full newer frontier')
        receipts.publish_receipt(output/f'source-constructed-{size}.json',dict(source=source,size=size,fixture_seconds=fixture_seconds,
            verified_construction_seconds=construction_seconds,genuine_transition_seconds=transition_seconds,newer_placements_per_scope=newer_counts))
        group_page,g=measure(store.db,lambda:read_occurrence_seek_page(store,old,*group,limit=4),store)
        owner_page,o=measure(store.db,lambda:read_occurrence_seek_page(store,old,*owner,limit=4),store)
        empty_page,e=measure(store.db,lambda:read_occurrence_seek_page(store,old,*empty,limit=4),store)
        if group_page.rows!=original[:4] or owner_page.rows!=original_owner or empty_page.rows!=():
            raise ValueError('old root result mismatch or false absence')
        for observed in (g,o,e):
            if (observed['sql_selects']['payload'] or observed['payload_checks'] or observed['payload_decodes']
                    or observed['sql_selects']['proof']>512 or observed['sqlite_vm_step_upper_bound']>=20000
                    or observed['python_peak_bytes']>=2*1024*1024):raise ValueError('old pin bounded access gate failed')
        current=construct_seek_certificates(store,writer,(GroupScope(1),))[0]
        expected_current=tuple(RawOccurrence('archive',key,store.codec.encode(()),1)
            for key in heapq.nsmallest(4,(store.codec.encode(i) for i in range(size))))
        if (current[0].root.count!=size+6 or
                read_occurrence_seek_page(store,writer,*current,limit=4).rows!=expected_current):
            raise ValueError('current root incorrect')
        return dict(size=size,exact=True,fixture_seconds=fixture_seconds,verified_construction_seconds=construction_seconds,
            genuine_transition_seconds=transition_seconds,old_group=g,old_owner=o,old_empty=e,
            old_pin_budget_rejections=0,current_group_entries=size+6,newer_placements_per_scope=newer_counts)
    finally:store.close()


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked execution source')
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),
        driver_sha256=receipts.file_hash(__file__),fixture_sha256=receipts.file_hash('simulation/tests/proof_occurrence_seek_fixtures.py'),
        python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(schema='ate-root-ordered-selection-source/1',source=source,sizes=SIZES,
        point_key=500,old_group_fanout=8,newer_placements_per_measured_group='size',archive_placements='2*size',old_owner_paths=2,old_empty_size=0,read_page=4,
        sqlite_main_cache_kib=2048,sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_node_cache_bytes=0,
        instrumentation='tracemalloc,SQL trace,SQLite VM progress100',
        limits=['Inactive root authority, not World open/save/year timing.','Root defines committed membership; unselected physical surplus remains full-audit work.']))
    results=[]
    for size in SIZES:
        index=index_case(output,size,source);physical=source_case(output,size,source)
        row=dict(schema='ate-root-ordered-selection-scaling/1',source=source,status='complete',size=size,index=index,physical=physical,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024))
        receipts.publish_receipt(output/f'size-{size}.json',row);results.append(row)
        print(f'{size}: exact; index node reads/writes={index["point"]["node_io"]["read_nodes"]}/{index["point"]["node_io"]["written_nodes"]}; '
              f'old group/owner/empty VM<={physical["old_group"]["sqlite_vm_step_upper_bound"]}/{physical["old_owner"]["sqlite_vm_step_upper_bound"]}/{physical["old_empty"]["sqlite_vm_step_upper_bound"]}; zero payloads, no budget rejection',flush=True)
    receipts.publish_receipt(output/'summary.json',dict(schema='ate-root-ordered-selection-summary/1',status='complete',source=source,results=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
