"""Instrument read-entry custody on the restored green engine; no latency claim."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import runpy
import sys

from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
from simulation.stage_0_6_genesis_stages import Recorder

root = Path.cwd()
out = Path(sys.argv[2]).resolve()
phase = 'setup'
counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
original_measure = Recorder.measure
originals = {}


def measure(self, name, operation, **kwargs):
    global phase
    previous = phase
    phase = name
    try:
        return original_measure(self, name, operation, **kwargs)
    finally:
        phase = previous


def observed(name, original):
    def call(self, pin, *args, **kwargs):
        st = self.store
        row = counts[phase][name]
        row['calls'] += 1
        borrowed = st.db.in_transaction or st._active_read_transaction or getattr(st, '_checked_snapshot_depth', 0)
        row['borrowed' if borrowed else 'owned_entry_candidate'] += 1
        before = self._owner_cache_hits if name == 'read_owner_identity' else None
        try:
            return original(self, pin, *args, **kwargs)
        finally:
            if before is not None:
                row['owner_cache_hits'] += self._owner_cache_hits - before
    return call


try:
    Recorder.measure = measure
    for name in ['read_owner_identity', 'read_identity_group', 'read_identity_membership']:
        original = getattr(IdentityCatalog, name)
        originals[name] = original
        setattr(IdentityCatalog, name, observed(name, original))
    driver = root / 'docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py'
    runpy.run_path(str(driver), run_name='__main__')
finally:
    Recorder.measure = original_measure
    for name, original in originals.items():
        setattr(IdentityCatalog, name, original)
    out.mkdir(parents=True, exist_ok=True)
    value = dict(kind='instrumented-entry-custody-only', counts=counts,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitation='Diagnostic wrappers only; borrowed entries are not eligible for minting certificates. Owned entry is a necessary condition, not proof of safe scope. No latency acceptance claim.')
    (out / 'read-entry-custody.json').write_text(json.dumps(value, indent=2) + '\n')
    report_path = out / 'report.json'
    if report_path.exists():
        report = json.loads(report_path.read_text())
        report['kind'] = 'instrumented-read-entry-custody-diagnostic'
        report['instrumentation'] = value['limitation']
        report_path.write_text(json.dumps(report, indent=2) + '\n')
