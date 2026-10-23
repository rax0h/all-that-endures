"""Matched checked/proof query reads on actual store schemas; not World speed."""
import argparse
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc

from ate_sim.persistence_proof_query import read_query_page
from simulation import continuation_receipts as r
from simulation.tests.proof_query_fixtures import make_store, construct_certificate

SIZES=(1000,10000,100000)


def git(*args):
    return subprocess.check_output(['git',*args],text=True).strip()


def measure(store,operation):
    store.reset_diagnostics();selects=dict(payload=0,proof=0,query=0,other=0)
    def trace(statement):
        if statement.lstrip().upper().startswith('SELECT'):
            which=('payload' if any('FROM '+table in statement for table in ('lazy_record_versions','records','segments')) else
                   'proof' if 'FROM ate_proof_nodes' in statement else
                   'query' if 'FROM lazy_query_versions' in statement else 'other')
            selects[which]+=1
    store.db.set_trace_callback(trace);tracemalloc.start()
    try:
        started=time.perf_counter();result=operation();wall=time.perf_counter()-started
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();store.db.set_trace_callback(None)
    return result,dict(wall_seconds=wall,python_peak_bytes=peak,sql_selects=selects,
        payload_reads=store._payload_reads,payload_check_reads=store._payload_check_reads,
        payload_check_bytes=store._payload_check_bytes)


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('tracked source is dirty')
    source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),
        driver_sha256=r.file_hash(__file__),fixture_sha256=r.file_hash('simulation/tests/proof_query_fixtures.py'),
        python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform())
    r.publish_receipt(output/'source.json',dict(schema='ate-proof-query-source/1',source=source,
        archive_sizes=SIZES,active_owners=8,memberships_per_owner=2,query_limit=8,
        scope='actual store metadata read; no World adoption or mature save/year result'))
    results=[]
    for size in SIZES:
        started=time.perf_counter();store,pin=make_store(output/f'source-{size}.sqlite',size)
        try:
            fixture_seconds=time.perf_counter()-started
            store.db.execute('PRAGMA cache_size=-2048');store.db.execute('PRAGMA temp_store=FILE')
            store.db.execute('PRAGMA temp.cache_size=-2048')
            started=time.perf_counter();certificate,expected=construct_certificate(store,pin)
            construction_seconds=time.perf_counter()-started
            r.publish_receipt(output/f'constructed-{size}.json',dict(source=source,archive_records=size,
                fixture_seconds=fixture_seconds,construction_seconds=construction_seconds,
                certificate_commitment=expected.hex(),query_entries=certificate.order.index.count))
            baseline,before=measure(store,lambda:store.query_memberships(pin,'people','cohort','active',limit=8))
            page,after=measure(store,lambda:read_query_page(store,pin,certificate,expected,limit=8))
            raw_baseline=tuple((store.codec.encode(key),ordinal) for key,ordinal in baseline)
            exact=tuple((store.codec.encode(i),ordinal) for i in range(4) for ordinal in (2*i,2*i+1))
            if page.positions!=raw_baseline or page.positions!=exact or page.next_after!=(7,store.codec.encode(3)):
                raise ValueError('checked/proof/raw fixture results disagree')
            if (after['sql_selects']['payload'] or after['payload_check_reads'] or after['payload_reads']
                    or after['sql_selects']['proof']>512 or after['python_peak_bytes']>=2*1024*1024):
                raise ValueError('proof query payload/metadata budget gate failed')
            if before['payload_check_reads']!=8 or before['sql_selects']['payload']!=8:
                raise ValueError('baseline did not exercise expected repeated owner checks')
            row=dict(schema='ate-proof-query-scaling/1',status='complete',source=source,archive_records=size,
                active_owners=8,query_entries=16,returned_positions=8,exact=True,
                fixture_seconds=fixture_seconds,construction_seconds=construction_seconds,
                baseline=before,proof=after,certificate_commitment=expected.hex(),
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                limitations=['Raw membership metadata only, no admitted objects or World save/open integration.',
                    'Proof construction includes one explicit full store verification outside query timers.',
                    'SQLite caches are warm/uncontrolled between sequential matched reads; no latency distribution.',
                    'Source fixture/schema are real, archive contents and active owners are synthetic.',
                    'RSS is lifetime peak including fixture, verification and prior cases.'])
            r.publish_receipt(output/f'size-{size}.json',row);results.append(row)
            print(f'{size}: baseline payload checks={before["payload_check_reads"]}, proof={after["payload_check_reads"]}, proof node reads={after["sql_selects"]["proof"]}, exact',flush=True)
        finally:store.close()
    r.publish_receipt(output/'summary.json',dict(schema='ate-proof-query-summary/1',status='complete',source=source,
        results=[dict(archive_records=x['archive_records'],baseline=x['baseline'],proof=x['proof'],exact=x['exact']) for x in results]))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
