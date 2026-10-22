"""Bounded sorted SQLite batch construction; no World/save latency claim."""
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

from ate_sim.persistence_proof_batch import update_sorted
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_nodes import Branch, key_locator
from ate_sim.persistence_proof_store import ProofNodeStore
from simulation import continuation_receipts as r

DOMAIN = b'proof-map-scaling/1'
SIZES = (1000, 10000, 100000)


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def audit_final_nodes(db, m, root):
    db.execute('CREATE TEMP TABLE reachable(digest BLOB PRIMARY KEY) WITHOUT ROWID')
    pending = [(root, ())] if root.count else []
    while pending:
        ref, prefix = pending.pop()
        db.execute('INSERT INTO reachable VALUES(?)', (ref.digest,))
        node = m._read(ref, prefix)
        if type(node) is Branch:
            pending.extend((child, node.prefix + (slot,)) for slot, child in reversed(node.children))
    reachable = db.execute('SELECT count(*) FROM reachable').fetchone()[0]
    physical = db.execute('SELECT count(*) FROM ate_proof_nodes').fetchone()[0]
    surplus = db.execute('SELECT count(*) FROM ate_proof_nodes p WHERE NOT EXISTS '
                         '(SELECT 1 FROM reachable r WHERE r.digest=p.digest)').fetchone()[0]
    if reachable != physical or surplus:
        raise ValueError('batch retained transient or missing final nodes')
    db.commit()
    return dict(reachable_nodes=reachable, physical_nodes=physical, surplus_nodes=surplus)


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    git('ls-files', '--error-unmatch', str(Path(__file__).resolve().relative_to(Path(git('rev-parse', '--show-toplevel')))))
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked benchmark source is dirty')
    source = dict(head=git('rev-parse', 'HEAD'), runtime_tree=git('rev-parse', 'HEAD:simulation/ate_sim'),
        driver_sha256=r.file_hash(__file__), python=platform.python_version(),
        sqlite=sqlite3.sqlite_version, platform=platform.platform())
    r.publish_receipt(output/'source.json', dict(schema='ate-proof-batch-source/1', source=source,
        sizes=SIZES, sqlite_main_cache_kib=2048, sqlite_temp_cache_kib=2048,
        temp_store='FILE', clean_python_cache_bytes=0,
        scope='immutable map construction and point replacement, not World persistence'))
    original, replacement = (hashlib.sha256(x).digest() for x in (b'initial', b'changed'))
    rows = []
    for size in SIZES:
        db_path = output/f'nodes-{size}.sqlite'
        db = sqlite3.connect(db_path)
        try:
            db.execute('PRAGMA cache_size=-2048')
            db.execute('PRAGMA temp_store=FILE')
            db.execute('PRAGMA temp.cache_size=-2048')
            store = ProofNodeStore(db); store.create_schema()
            m = ProofMap(DOMAIN, lambda d: store.read(DOMAIN, d), lambda d, raw: store.write(DOMAIN, d, raw))
            started = time.perf_counter()
            db.execute('CREATE TEMP TABLE delta(locator BLOB PRIMARY KEY, typed_key BLOB NOT NULL) WITHOUT ROWID')
            def keys():
                for i in range(size):
                    key = b'fixed' if i == 0 else b'archive:' + i.to_bytes(8, 'big')
                    yield key_locator(DOMAIN, key), key
            db.executemany('INSERT INTO delta VALUES(?,?)', keys()); db.commit()
            staging = dict(wall_seconds=time.perf_counter()-started,
                temp_page_count=db.execute('PRAGMA temp.page_count').fetchone()[0],
                temp_page_size=db.execute('PRAGMA temp.page_size').fetchone()[0])
            r.publish_receipt(output/f'staged-{size}.json', dict(source=source, keys=size, staging=staging))
            cursor = db.execute('SELECT typed_key FROM delta ORDER BY locator')
            store.reset_diagnostics(); tracemalloc.start()
            try:
                started = time.perf_counter(); db.execute('BEGIN')
                root = update_sorted(m, m.empty, ((key, original) for key, in cursor))
                db.commit(); wall = time.perf_counter()-started
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop(); cursor.close()
            construction = dict(wall_seconds=wall, python_peak_bytes=peak, node_io=store.diagnostics())
            if root.count != size or peak >= 2*1024*1024:
                raise ValueError('batch cardinality/heap bound exceeded')
            inventory = audit_final_nodes(db, m, root)
            if construction['node_io']['write_requests'] != inventory['physical_nodes']:
                raise ValueError('batch wrote a final node more than once')
            store.reset_diagnostics(); selects = dict(proof=0, other=0)
            def trace(statement):
                if statement.lstrip().upper().startswith('SELECT'):
                    selects['proof' if 'FROM ate_proof_nodes' in statement else 'other'] += 1
            db.set_trace_callback(trace); tracemalloc.start()
            try:
                started = time.perf_counter(); db.execute('BEGIN')
                changed = update_sorted(m, root, iter([(b'fixed', replacement)]))
                db.commit(); point_wall = time.perf_counter()-started
                _, point_peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop(); db.set_trace_callback(None)
            io = store.diagnostics()
            if io['read_nodes'] > 66 or io['written_nodes'] > 65 or selects['other'] or point_peak >= 512*1024:
                raise ValueError('point batch work bound exceeded')
            if m.get(root, b'fixed') != original or m.get(changed, b'fixed') != replacement:
                raise ValueError('retained old/new mapping disagrees')
            row = dict(schema='ate-proof-batch-scaling/1', status='complete', source=source, keys=size,
                staging=staging, construction=construction, inventory=inventory,
                point=dict(wall_seconds=point_wall, python_peak_bytes=point_peak, node_io=io, sql_selects=selects),
                database_bytes=db_path.stat().st_size,
                process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024),
                root_before=dict(digest=root.digest.hex(), count=root.count),
                root_after=dict(digest=changed.digest.hex(), count=changed.count),
                limitations=['No World row, save, manifest, migration or GC exercised.',
                    'Staging sort spills to SQLite; batch peak excludes completed staging.',
                    'RSS includes all previous phases; no whole-process phase peak claimed.',
                    'Old and new roots are both intentionally retained.'])
            r.publish_receipt(output/f'size-{size}.json', row); rows.append(row)
            print(f'{size}: final nodes={inventory["physical_nodes"]}, batch={wall:.3f}s, heap={peak}B, point reads={io["read_nodes"]}', flush=True)
        finally:
            db.close()
    r.publish_receipt(output/'summary.json', dict(schema='ate-proof-batch-summary/1', status='complete', source=source,
        results=[dict(keys=row['keys'], inventory=row['inventory'], construction=row['construction'],
                      point=row['point'], database_bytes=row['database_bytes'], staging=row['staging']) for row in rows]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
