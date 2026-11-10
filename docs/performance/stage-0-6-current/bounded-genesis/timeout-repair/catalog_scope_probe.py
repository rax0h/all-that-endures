"""Bounded owned-catalog component; excludes live World and canonical sort costs."""
import argparse,hashlib,json,platform,resource,sqlite3,time,tracemalloc
from pathlib import Path
from unittest.mock import patch
from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_catalog_copy import _verify_catalog
from ate_sim.persistence_genesis_transaction import catalog_snapshot
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy,opened,RULES

p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
args.workspace.mkdir(parents=True,exist_ok=False)
rows=[]
for size in (1000,10000):
 folder=args.workspace/str(size);folder.mkdir()
 source=legacy_lazy(folder,size=size);target=folder/'complete.sqlite'
 upgrade_lazy_snapshot(source,target,rules_id=RULES)
 with opened(target) as store:
  pin=store.capture_pin()
  try:
   with lazy._bounded_conversion_audits(),patch.object(store,'_checked_operational_rows',wraps=store._checked_operational_rows) as checks:
    tracemalloc.start();start=time.monotonic()
    with catalog_snapshot(store,pin):
     _verify_catalog(store,pin)
     scope=store._validation_scope
     row=dict(history_elements=size,cache_entries=scope.entries,cache_bytes=scope.bytes,
         operational_checks=checks.call_count,wall_seconds_instrumented=time.monotonic()-start,
         traced_peak_bytes=tracemalloc.get_traced_memory()[1],database_bytes=target.stat().st_size,
         process_high_water_kib_including_setup=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
     assert row['cache_entries']<=256 and row['cache_bytes']<=256*1024 and row['operational_checks']==1
    tracemalloc.stop()
    assert not store.db.in_transaction and store._validation_scope is None
    rows.append(row)
  finally:store.release_pin(pin)
 args.output.write_text(json.dumps(dict(status='complete' if size==10000 else 'running',rows=rows,
     python=platform.python_version(),sqlite=sqlite3.sqlite_version,
     limitation='Catalog component under tracemalloc; setup, canonical sorting and native live World retention excluded. Disk inventory grows with rows. No mature timing extrapolation.'),indent=2)+'\n')
 print(json.dumps(row),flush=True)
