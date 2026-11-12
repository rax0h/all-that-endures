"""Two raw children in one command execution; underlying driver owns checks."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[5]
base = root.parent / 'read-view-baseline'
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
source = root.parent / 'small-proof-profile/source.sqlite/candidate.sqlite'
driver = Path('docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py')
host = dict(parent_pid=os.getpid(), python=sys.version, platform=platform.platform(),
            affinity=sorted(os.sched_getaffinity(0)))
for name, path in [('cpu', '/proc/cpuinfo'), ('cpu_max', '/sys/fs/cgroup/cpu.max')]:
    text = Path(path).read_text() if Path(path).exists() else ''
    host[name] = next((line.split(':', 1)[1].strip() for line in text.splitlines()
                       if line.startswith('model name')), '') if name == 'cpu' else text.strip()
(out / 'host.json').write_text(json.dumps(host, indent=2) + '\n')
reports = {}
for label, cwd in [('baseline', base), ('candidate', root)]:
    with (out / (label + '.log')).open('w') as log:
        subprocess.run([sys.executable, str(driver), str(source), str(out / label)],
                       cwd=cwd, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=720)
    report = json.loads((out / label / 'report.json').read_text())
    assert report['status'] == 'complete' and report['source_preserved'] and report['runtime_preserved']
    reports[label] = report
assert reports['baseline']['input'] == reports['candidate']['input']
assert reports['baseline']['restored']['saved'] == reports['candidate']['restored']['saved']
assert reports['baseline']['restored']['warm_digest'] == reports['candidate']['restored']['warm_digest']
summary = {label: {k: v['wall_seconds'] for k, v in report['phases'].items()}
           for label, report in reports.items()}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
