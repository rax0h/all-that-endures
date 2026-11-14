"""Instrument only the real parent guard; use the existing exact-state driver."""
import cProfile
import json
from pathlib import Path
import pstats
import runpy
import sys

root = Path.cwd().resolve()
sys.path[:0] = [str(root), str(root/'simulation')]
from ate_sim import persistence_proof_publication as content
original = content._guard_content_parent
output = Path(sys.argv[2]).resolve()
observations = []

def checked(*args, **kwargs):
    profile = cProfile.Profile()
    profile.enable()
    try:
        return original(*args, **kwargs)
    finally:
        profile.disable()
        observations.append([dict(file=f, line=line, function=name, calls=v[1],
            primitive_calls=v[0], own_seconds=v[2], cumulative_seconds=v[3])
            for (f, line, name), v in pstats.Stats(profile).stats.items()])
        (output/'parent-work.json').write_text(json.dumps(observations, indent=2)+'\n')

content._guard_content_parent = checked
try:
    driver = root/'docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py'
    sys.argv[0] = str(driver)
    runpy.run_path(str(driver), run_name='__main__')
finally:
    content._guard_content_parent = original
    if (output/'report.json').exists():
        report = json.loads((output/'report.json').read_text())
        report['kind'] = 'instrumented-content-parent-guard-only'
        report['limitation'] = 'Guard cProfile overhead; work counts, not raw latency acceptance'
        (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
