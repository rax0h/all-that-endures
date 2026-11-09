"""Small row-count retention check; never mature performance acceptance."""
import gc
import json
from pathlib import Path
import resource
import tempfile
import time
import tracemalloc
from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_proof_world_copy import _rebase_private_snapshot
from ate_sim.incremental_store import TypedCodec
from simulation.tests.test_stage_0_6_bounded_genesis import archive

results=[]
for count in (1000,10000):
    with tempfile.TemporaryDirectory(prefix='ate-genesis-retention-') as directory:
        root=Path(directory)
        with archive(root/'source.sqlite',count):pass
        gc.collect()
        rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        tracemalloc.start()
        start=time.monotonic()
        with lazy._bounded_conversion_audits():
            copied=lazy.LazyRecordStore.copy_current_head(root/'source.sqlite',root/'copy.sqlite',
                codec=TypedCodec(),expected_simulation_schema='test',expected_rules_id='test')
            with lazy.LazyRecordStore.open(root/'copy.sqlite',codec=TypedCodec(),
                    expected_simulation_schema='test',expected_rules_id='test') as store:
                before=store.verify_all()
                _rebase_private_snapshot(store)
                after=store.verify_all()
                assert before['lazy_records']==after['lazy_records']==count
                assert after['generation']==0 and after['identity_occurrences']==count
        live,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        row=dict(rows=count,payload_bytes=count*1024,wall_seconds=time.monotonic()-start,
            python_traced_peak_bytes=peak,python_traced_live_bytes=live,
            process_peak_rss_before_bytes=rss_before,process_peak_rss_after_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            limitation='RSS high water includes fixture construction; allocator measurement covers streamed copy/audit/rebase only')
        results.append(row);print(json.dumps(row),flush=True)
Path('docs/performance/stage-0-6-current/bounded-genesis/retention.json').write_text(json.dumps(results,indent=2)+'\n')
