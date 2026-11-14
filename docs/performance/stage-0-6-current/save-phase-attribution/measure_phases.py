"""Attribute the three real save phases; timings include per-phase cProfile."""
import cProfile
from dataclasses import asdict
import json
from pathlib import Path
import pstats
import runpy
import sys
import time

root = Path.cwd().resolve()
sys.path[:0] = [str(root), str(root/'simulation')]
from ate_sim.persistence_lazy import LazyWorldSession
from ate_sim.persistence_proof_world_session import _WorldProofAuthority

output = Path(sys.argv[2]).resolve()
originals = []
observations = []

def install(cls, method, label):
    original = getattr(cls, method)
    originals.append((cls, method, original))
    def measured(self, *args, **kwargs):
        profile = cProfile.Profile()
        before = asdict(self.store.diagnostics())
        started, cpu = time.perf_counter(), time.process_time()
        status = 'failed'
        profile.enable()
        try:
            result = original(self, *args, **kwargs)
            status = 'complete'
            return result
        finally:
            profile.disable()
            row = dict(phase=label, status=status, wall_seconds=time.perf_counter()-started,
                cpu_seconds=time.process_time()-cpu, before=before,
                after=asdict(self.store.diagnostics()))
            stats = [dict(file=f, line=line, function=name, calls=v[1],
                primitive_calls=v[0], own_seconds=v[2], cumulative_seconds=v[3],
                callers=[dict(caller=list(k), data=list(c) if isinstance(c,tuple) else c)
                         for k,c in v[4].items()])
                for (f,line,name),v in pstats.Stats(profile).stats.items()]
            (output/(label+'-calls.json')).write_text(json.dumps(stats,indent=2)+'\n')
            observations.append(row)
            (output/'save-phases.json').write_text(json.dumps(observations,indent=2)+'\n')
    setattr(cls, method, measured)

install(LazyWorldSession, '_prepare_hybrid_save', 'prepare')
install(_WorldProofAuthority, 'commit', 'commit')
install(LazyWorldSession, '_publish_committed_hybrid', 'acknowledge')
try:
    driver = root/'docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py'
    sys.argv[0] = str(driver)
    runpy.run_path(str(driver), run_name='__main__')
finally:
    for cls, method, original in reversed(originals): setattr(cls, method, original)
    if (output/'report.json').exists():
        report = json.loads((output/'report.json').read_text())
        report.update(kind='instrumented-save-phase-attribution',
            limitation='Original methods wrapped only for profiling; not raw latency acceptance')
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
