"""Bounded proof-map work evidence; not a World-save or mature-speed benchmark."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc

from ate_sim.persistence_proof_nodes import empty_root
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation import continuation_receipts as r

DOMAIN = b'proof-map-scaling/1'
SIZES = (1000, 10000, 100000)


def git(*args):
    return subprocess.check_output(['git',*args],text=True).strip()


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    git('ls-files','--error-unmatch',str(Path(__file__).resolve().relative_to(Path(git('rev-parse','--show-toplevel')))))
    if git('status','--porcelain','--untracked-files=no'):
        raise ValueError('tracked benchmark source is dirty')
    source = dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),
        driver_sha256=r.file_hash(__file__),python=platform.python_version(),
        sqlite=sqlite3.sqlite_version,platform=platform.platform())
    r.publish_receipt(output/'source.json',dict(schema='ate-proof-map-source/1',source=source,
        sizes=SIZES,sqlite_cache_kib=2048,clean_python_cache_bytes=0,
        scope='immutable-map primitive; no World/save integration',instrumentation='point-tracemalloc-v1'))
    original, replacement = (hashlib.sha256(value).digest() for value in (b'initial',b'changed'))
    root, built, rows = empty_root(DOMAIN), 0, []
    db = sqlite3.connect(output/'nodes.sqlite')
    try:
        db.execute('PRAGMA cache_size=-2048')
        store=ProofNodeStore(db);store.create_schema()
        m=ProofMap(DOMAIN,lambda digest:store.read(DOMAIN,digest),
                   lambda digest,raw:store.write(DOMAIN,digest,raw))
        for size in SIZES:
            started=time.perf_counter();store.reset_diagnostics();db.execute('BEGIN')
            for i in range(built,size):
                key=b'fixed' if i==0 else b'archive:'+i.to_bytes(8,'big')
                root=m.set(root,key,original)
            db.commit();built=size
            construction=dict(wall_seconds=time.perf_counter()-started,node_io=store.diagnostics())
            store.reset_diagnostics(); selects=dict(proof=0,other=0)
            def trace(statement):
                if statement.lstrip().upper().startswith('SELECT'):
                    selects['proof' if 'FROM ate_proof_nodes' in statement else 'other']+=1
            db.set_trace_callback(trace)
            tracemalloc.start()
            try:
                started=time.perf_counter();db.execute('BEGIN')
                changed=m.set(root,b'fixed',replacement)
                db.commit();wall=time.perf_counter()-started
                _,peak=tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop();db.set_trace_callback(None)
            io=store.diagnostics()
            if (io['read_nodes']>66 or io['written_nodes']>65 or selects['other']
                    or peak>512*1024 or root.count!=size or changed.count!=size):
                raise ValueError('proof-map point-work/residency bound exceeded')
            if m.get(root,b'fixed')!=original or m.get(changed,b'fixed')!=replacement:
                raise ValueError('old/new root lookup disagrees after commit')
            row=dict(schema='ate-proof-map-scaling/1',status='complete',source=source,keys=size,
                scope='proof-map point replacement only; no World/save integration',
                root_before=dict(digest=root.digest.hex(),count=root.count),
                root_after=dict(digest=changed.digest.hex(),count=changed.count),
                construction=construction,point=dict(wall_seconds=wall,node_io=io,
                    sql_selects=selects,python_peak_bytes=peak,
                    process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)),
                retained_nodes=db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0],
                database_bytes=(output/'nodes.sqlite').stat().st_size,
                limitations=['No World payload tables, saves, migration or root publication exercised.',
                             'RSS is process-lifetime peak including construction, not a phase peak.',
                             'Obsolete immutable nodes are retained; root-aware collection is future work.'])
            r.publish_receipt(output/f'size-{size}.json',row);rows.append(row)
            print(json.dumps(dict(keys=size,status='complete',point=row['point'])),flush=True)
        r.publish_receipt(output/'summary.json',dict(schema='ate-proof-map-scaling-summary/1',
            status='complete',source=source,results=[dict(keys=row['keys'],point=row['point']) for row in rows]))
    finally:
        db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
