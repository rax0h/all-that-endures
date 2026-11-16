"""Synthetic locator scaling only; no mature World or acceptance claim."""
import ast
import json
import platform
import sqlite3
import subprocess
import time

from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_proof_world_copy import _bounded_rows

BASELINE = '6f3d0a88e910376427ce81bc0ae224bf4bc742e3'
source = subprocess.check_output(['git', 'show', BASELINE + ':simulation/ate_sim/persistence_proof_world_copy.py'], text=True)
node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == '_bounded_rows')
scope = {'StoreIntegrityError': RuntimeError}
exec(compile(ast.Module(body=[node], type_ignores=[]), 'baseline-bounded-rows', 'exec'), scope)
result = dict(scope=__doc__, baseline=BASELINE,
              candidate=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              candidate_helper_blob=subprocess.check_output(['git', 'hash-object', 'simulation/ate_sim/persistence_proof_world_copy.py'], text=True).strip(),
              candidate_engine_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], text=True).strip(),
              python=platform.python_version(), sqlite=sqlite3.sqlite_version, trials=[])

for count in (512, 1024, 2048):
    for name, operation in [('baseline', scope['_bounded_rows']), ('candidate', _bounded_rows)]:
        with sqlite3.connect(':memory:') as db:
            db.executescript('CREATE TABLE query_membership(namespace TEXT,record_key BLOB);' + lazy.P4_DDL)
            db.executemany('INSERT INTO lazy_order_versions VALUES (?,?,?,?,?,?)',
                           (('people', i.to_bytes(4, 'big'), count-i, 126, None, 'checksum') for i in range(count)))
            work = [0]
            def tick():
                work[0] += 1000
                return 0
            db.set_progress_handler(tick, 1000)
            start = time.perf_counter()
            rows = list(operation(db, 'lazy_order_versions', ('namespace', 'typed_key'),
                                  ('namespace', 'typed_key', 'ordinal')))
            elapsed = time.perf_counter() - start
            db.set_progress_handler(None, 0)
            assert rows == [('people', i.to_bytes(4, 'big'), count-i) for i in range(count)]
            result['trials'].append(dict(rows=count, kind=name,
                                         vm_instructions_rounded_down=work[0], wall_seconds=elapsed))
with sqlite3.connect(':memory:') as db:
    db.executescript('CREATE TABLE query_membership(namespace TEXT,record_key BLOB);' + lazy.P4_DDL)
    result['old_point_plan'] = db.execute('EXPLAIN QUERY PLAN SELECT namespace,typed_key,ordinal FROM lazy_order_versions WHERE namespace=? AND typed_key=?', ('people', b'key')).fetchall()
    result['new_point_plan'] = db.execute('EXPLAIN QUERY PLAN SELECT namespace,typed_key,ordinal FROM lazy_order_versions WHERE rowid=?', (1,)).fetchall()
print(json.dumps(result, indent=2))
