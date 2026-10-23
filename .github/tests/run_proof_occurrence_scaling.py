"""Real pinned occurrence pages; no World/save/mature speed acceptance."""
import argparse
from contextlib import closing
from itertools import islice
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc

from ate_sim.persistence_proof_occurrence import GroupScope, OwnerScope, read_occurrence_page, OccurrenceProofBudgetError
from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
from simulation import continuation_receipts as receipts
from simulation.tests.proof_occurrence_fixtures import make_occurrence_store, construct_occurrence_certificates, metadata

SIZES=(1000,10000,100000)


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def measure(store,operation):
    store.reset_diagnostics();counts=dict(payload=0,occurrence=0,proof=0,other=0);sources=[];vm_steps=0
    def progress():
        nonlocal vm_steps
        vm_steps+=100
        return 0
    def trace(sql):
        if not sql.lstrip().upper().startswith('SELECT'):return
        category=('payload' if any('FROM '+t in sql for t in ('records','lazy_record_versions','segments')) else
            'occurrence' if 'FROM lazy_identity_occurrence_versions' in sql else
            'proof' if 'FROM ate_proof_nodes' in sql else 'other')
        counts[category]+=1
        if category=='occurrence':sources.append(sql)
    store.db.set_trace_callback(trace);store.db.set_progress_handler(progress,100);tracemalloc.start()
    try:
        started=time.perf_counter();result=operation();elapsed=time.perf_counter()-started
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();store.db.set_trace_callback(None);store.db.set_progress_handler(None,0)
    plans=[tuple(r[3] for r in store.db.execute('EXPLAIN QUERY PLAN '+sql)) for sql in sources]
    if any('TEMP B-TREE' in line.upper() for plan in plans for line in plan):
        raise ValueError('bounded occurrence source unexpectedly sorts a full relation')
    return result,dict(wall_seconds=elapsed,python_peak_bytes=peak,sqlite_vm_step_upper_bound=vm_steps+99,
        sql_selects=counts,source_plans=plans,
        payload_checks=store._payload_check_reads,payload_decodes=store._payload_reads)


def baseline_group(store,pin):
    with closing(store.iter_identity_occurrences_for_incarnation(pin,1)) as rows:
        return tuple(islice(rows,4))


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('tracked execution source dirty')
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),
        driver_sha256=receipts.file_hash(__file__),fixture_sha256=receipts.file_hash('simulation/tests/proof_occurrence_fixtures.py'),
        python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    receipts.publish_receipt(output/'source.json',dict(schema='ate-proof-occurrence-source/1',source=source,
        sizes=SIZES,requested_group_placements=8,requested_owners=4,page_size=4,owner_paths=2,
        sqlite_main_cache_kib=2048,sqlite_temp_cache_kib=2048,temp_store='FILE',python_clean_node_cache_bytes=0,
        scope='Synthetic placements in real store schema, not World topology activation or save latency'))
    results=[]
    for size in SIZES:
        started=time.perf_counter();store,pin=make_occurrence_store(output/f'source-{size}.sqlite',size)
        try:
            fixture_seconds=time.perf_counter()-started
            store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE')
            store.db.execute('PRAGMA temp.cache_size=-2048')
            started=time.perf_counter()
            group,owner,empty=construct_occurrence_certificates(store,pin,(GroupScope(1),OwnerScope('people',store.codec.encode(0)),GroupScope(2)))
            construction_seconds=time.perf_counter()-started
            receipts.publish_receipt(output/f'constructed-{size}.json',dict(source=source,archive_occurrences=size,
                fixture_seconds=fixture_seconds,verified_construction_seconds=construction_seconds,
                group_commitment=group[1].hex(),owner_commitment=owner[1].hex()))
            checked,baseline=measure(store,lambda:baseline_group(store,pin))
            group_page,g=measure(store,lambda:read_occurrence_page(store,pin,*group,limit=4))
            owner_page,o=measure(store,lambda:read_occurrence_page(store,pin,*owner,limit=4))
            exact=tuple(('people',store.codec.encode(i),store.codec.encode((('field',field),)),1)
                for i in range(2) for field in ('other','shared'))
            raw=lambda rows:tuple((r.namespace,r.typed_key,r.path,r.incarnation_id) for r in rows)
            checked_raw=tuple((ns,store.codec.encode(key),store.codec.encode(path),1) for ns,key,path in checked)
            if (raw(group_page.rows)!=exact or raw(group_page.rows)!=checked_raw
                    or raw(owner_page.rows)!=exact[:2]
                    or group_page.next_after!=('people',store.codec.encode(1),store.codec.encode((('field','shared'),)))
                    or owner_page.next_after is not None):raise ValueError('exact owner/group page disagreement')
            for observed in (g,o):
                if (observed['sql_selects']['payload'] or observed['payload_checks'] or observed['payload_decodes']
                        or observed['sql_selects']['proof']>512 or observed['python_peak_bytes']>=2*1024*1024):
                    raise ValueError('proof occurrence work/memory gate failed')
            receipts.publish_receipt(output/f'current-{size}.json',dict(source=source,archive_occurrences=size,
                exact=True,group=g,owner=o,baseline=baseline))
            old=store.capture_pin();started=time.perf_counter()
            def frontier_changes():
                # The old requested group now needs BOTH open and just-closed
                # rows inside its first page. The measured owner0 is unchanged.
                yield IdentityOccurrenceChange('people',1,(('field','other'),),delete=True)
                yield IdentityOccurrenceChange('people',1,(('field','shared'),),2)
                for i in range(size):yield IdentityOccurrenceChange('archive',i,(),2)
            writer=store.commit(pin,commit_token='newer-placement-frontier',version_changes=(),
                identity_changes=frontier_changes(),
                next_incarnation_id=size+3,changes=(),new_segments=(),metadata=metadata(2)).pin
            transition_seconds=time.perf_counter()-started
            prior_group,pg=measure(store,lambda:read_occurrence_page(store,old,*group,limit=4))
            prior_owner,po=measure(store,lambda:read_occurrence_page(store,old,*owner,limit=4))
            if prior_group.rows!=group_page.rows or prior_owner.rows!=owner_page.rows:
                raise ValueError('previous generation source merge disagrees with exact parent')
            def bounded_rejection():
                try:read_occurrence_page(store,old,*empty,limit=4)
                except OccurrenceProofBudgetError:return 'budget-rejected'
                raise ValueError('old pin silently scanned newer placement frontier')
            rejected,budget=measure(store,bounded_rejection)
            for observed in (pg,po,budget):
                if (observed['sql_selects']['payload'] or observed['payload_checks'] or observed['payload_decodes']
                        or observed['sqlite_vm_step_upper_bound']>=20000
                        or observed['python_peak_bytes']>=2*1024*1024):
                    raise ValueError('previous-pin metadata/VM work gate failed')
            row=dict(schema='ate-proof-occurrence-scaling/1',status='complete',source=source,archive_occurrences=size,
                exact=True,fixture_seconds=fixture_seconds,verified_construction_seconds=construction_seconds,
                baseline=baseline,group=g,owner=o,previous_group=pg,previous_owner=po,
                newer_frontier_budget=budget,newer_frontier_result=rejected,
                genuine_frontier_transition_seconds=transition_seconds,
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                limitations=['Raw source metadata only; full topology/link/retirement/content consistency still gated.',
                    'Baseline validates rows individually; proof additionally establishes ordered page completeness.',
                    'Full verification/index construction outside point timing; no hidden ordinary-open schema work.',
                    'Previous pin with intervening newer candidates explicitly rejects within budget; general old-pin path still required before World use.',
                    'Sequential warm/uncontrolled caches, tracemalloc and VM progress instrumentation; no latency distribution/speedup claim.',
                    'SELECT counts are logical application work; RSS includes construction and prior cases.'])
            receipts.publish_receipt(output/f'size-{size}.json',row);results.append(row)
            print(f'{size}: exact; group/owner proof reads={g["sql_selects"]["proof"]}/{o["sql_selects"]["proof"]}; '
                  f'payload checks={g["payload_checks"]}/{o["payload_checks"]}; old-frontier budget VM<={budget["sqlite_vm_step_upper_bound"]}',flush=True)
        finally:store.close()
    receipts.publish_receipt(output/'summary.json',dict(schema='ate-proof-occurrence-summary/1',status='complete',source=source,
        results=[dict(archive_occurrences=x['archive_occurrences'],exact=x['exact'],group=x['group'],owner=x['owner'],baseline=x['baseline'],
            previous_group=x['previous_group'],previous_owner=x['previous_owner'],newer_frontier_budget=x['newer_frontier_budget']) for x in results]))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
