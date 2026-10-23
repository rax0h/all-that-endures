"""Bounded ordered-proof transitions/pages; no World-save latency claim."""
import argparse
import hashlib
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import time
import tracemalloc

from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_order import OrderEntry, entry_commitment, query_order_key, root_commitment, verify_page
from ate_sim.persistence_proof_order_edit import OrderEdit, build_ordered, update_ordered
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation import continuation_receipts as r

DOMAIN = b'proof-order-scaling/1'
SIZES = (1000, 10000, 100000)
FIXED = 500


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def position(i):
    return query_order_key(i, b'same-source-key')


def read_entry(db, key):
    row = db.execute('SELECT value FROM relation WHERE position=?', (key,)).fetchone()
    if row is None:
        raise ValueError('fixture relation key missing')
    previous = db.execute('SELECT max(position) FROM relation WHERE position<?', (key,)).fetchone()[0]
    following = db.execute('SELECT min(position) FROM relation WHERE position>?', (key,)).fetchone()[0]
    return OrderEntry(key, row[0], previous, following)


def source_rows(db):
    return db.execute('SELECT position,value FROM relation ORDER BY position')


def run(output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    git('ls-files', '--error-unmatch', str(Path(__file__).resolve().relative_to(Path(git('rev-parse', '--show-toplevel')))))
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked execution source is dirty')
    source = dict(head=git('rev-parse', 'HEAD'), runtime_tree=git('rev-parse', 'HEAD:simulation/ate_sim'),
        driver_sha256=r.file_hash(__file__), python=platform.python_version(), sqlite=sqlite3.sqlite_version,
        platform=platform.platform())
    r.publish_receipt(output/'source.json', dict(schema='ate-proof-order-source/1', source=source,
        sizes=SIZES, fixed_ordinal=FIXED, sqlite_main_cache_kib=2048, sqlite_temp_cache_kib=2048,
        temp_store='FILE', python_clean_node_cache_bytes=0,
        scope='ordered relation primitive, no World save/open or physical source adapter'))
    original, replacement = (hashlib.sha256(s).digest() for s in (b'initial', b'changed'))
    results = []
    for size in SIZES:
        path = output/f'order-{size}.sqlite'; db = sqlite3.connect(path)
        try:
            db.execute('PRAGMA cache_size=-2048'); db.execute('PRAGMA temp_store=FILE')
            db.execute('PRAGMA temp.cache_size=-2048')
            store = ProofNodeStore(db); store.create_schema()
            m = ProofMap(DOMAIN, lambda d: store.read(DOMAIN,d), lambda d,raw:store.write(DOMAIN,d,raw))
            started = time.perf_counter()
            db.execute('CREATE TABLE relation(position BLOB PRIMARY KEY,value BLOB NOT NULL) WITHOUT ROWID')
            db.execute('CREATE TABLE historical_payloads(position BLOB PRIMARY KEY,payload BLOB NOT NULL) WITHOUT ROWID')
            db.executemany('INSERT INTO relation VALUES(?,?)', ((position(i),original) for i in range(size)))
            db.executemany('INSERT INTO historical_payloads VALUES(?,?)', ((position(i),b'unrelated-history') for i in range(size)))
            db.commit(); setup = dict(wall_seconds=time.perf_counter()-started)
            store.reset_diagnostics();tracemalloc.start()
            try:
                started=time.perf_counter();db.execute('BEGIN'); cursor=source_rows(db)
                try: root=build_ordered(m,db,cursor)
                finally: cursor.close()
                db.commit();wall=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory()
            finally:tracemalloc.stop()
            construction=dict(wall_seconds=wall,python_peak_bytes=peak,node_io=store.diagnostics())
            r.publish_receipt(output/f'constructed-{size}.json',dict(source=source,keys=size,setup=setup,construction=construction))
            sql = dict(proof=0,staging=0,relation=0,historical_payloads=0,other=0)
            def trace(statement):
                if statement.lstrip().upper().startswith('SELECT'):
                    name=('historical_payloads' if 'historical_payloads' in statement else
                          'proof' if 'FROM ate_proof_nodes' in statement else
                          'staging' if 'ate_order_' in statement else
                          'relation' if 'relation' in statement else 'other')
                    sql[name]+=1
            store.reset_diagnostics();db.set_trace_callback(trace);tracemalloc.start()
            try:
                started=time.perf_counter();db.execute('BEGIN')
                old=read_entry(db,position(FIXED))
                left=read_entry(db,old.previous);right=read_entry(db,old.following)
                changed=update_ordered(m,db,root,root_commitment(DOMAIN,root),
                    iter([OrderEdit(old.key,replacement,old,left,right)]))
                db.execute('UPDATE relation SET value=? WHERE position=?',(replacement,old.key))
                db.commit();wall=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory()
            finally:tracemalloc.stop();db.set_trace_callback(None)
            io=store.diagnostics()
            if (io['read_nodes']>512 or io['written_nodes']>256 or peak>=2*1024*1024
                    or sql['historical_payloads'] or root.index.count!=size or changed.index.count!=size):
                raise ValueError('fixed ordered transition work bound exceeded')
            point=dict(wall_seconds=wall,python_peak_bytes=peak,node_io=io,sql_selects=sql)
            r.publish_receipt(output/f'transition-{size}.json',dict(source=source,keys=size,point=point))
            current=read_entry(db,old.key)
            if (m.get(root.index,old.key)!=entry_commitment(DOMAIN,old)
                    or m.get(changed.index,old.key)!=entry_commitment(DOMAIN,current)):
                raise ValueError('retained old/new ordered values disagree')
            page=tuple(read_entry(db,position(i)) for i in range(FIXED-7,FIXED+9))
            verified=verify_page(m,changed,root_commitment(DOMAIN,changed),rows=page,
                after=position(FIXED-8),limit=16)
            if tuple(e.key for e in verified)!=tuple(position(i) for i in range(FIXED-7,FIXED+9)):
                raise ValueError('ordered page differs from independent fixture positions')
            if tuple(e.value for e in verified)!=tuple(replacement if i==FIXED else original for i in range(FIXED-7,FIXED+9)):
                raise ValueError('ordered page values disagree')
            started=time.perf_counter();db.execute('BEGIN');cursor=source_rows(db)
            try: rebuilt=build_ordered(m,db,cursor)
            finally:cursor.close()
            if rebuilt!=changed:raise ValueError('full checked rebuild differs from local ordered transition')
            db.commit();rebuild_wall=time.perf_counter()-started
            if db.execute("SELECT count(*) FROM sqlite_temp_master WHERE name LIKE 'ate_order_%'").fetchone()[0]:
                raise ValueError('temporary ordered staging leaked')
            row=dict(schema='ate-proof-order-scaling/1',status='complete',source=source,keys=size,
                setup=setup,construction=construction,point=point,verified_page_rows=len(verified),
                canonical_rebuild=dict(equal=True,wall_seconds=rebuild_wall),
                root_before=dict(digest=root.index.digest.hex(),count=root.index.count),
                root_after=dict(digest=changed.index.digest.hex(),count=changed.index.count),
                database_bytes=path.stat().st_size,
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
                limits=['Primitive relation metadata only, not World save/open/identity integration.',
                    'Historical payload table is synthetic; no mature workload result.',
                    'Source-row fixture setup and full rebuild are outside transition timer.',
                    'RSS is lifetime peak, including prior cases and construction.'])
            r.publish_receipt(output/f'size-{size}.json',row);results.append(row)
            print(f'{size}: point reads={io["read_nodes"]}, writes={io["written_nodes"]}, heap={peak}B, wall={wall:.6f}s, page/rebuild exact',flush=True)
        finally:db.close()
    r.publish_receipt(output/'summary.json',dict(schema='ate-proof-order-summary/1',status='complete',source=source,
        results=[dict(keys=x['keys'],point=x['point'],construction=x['construction'],
                      verified_page_rows=x['verified_page_rows'],canonical_rebuild=x['canonical_rebuild']) for x in results]))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
