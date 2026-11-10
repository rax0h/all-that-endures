"""Measured construction on complete Worlds with 1k/10k retained values.

Instrumentation counts real SQL and full source audits. These construction
timings are diagnostic, not raw or mature-world acceptance measurements.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time

from ate_sim.core import Settlement
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from ate_sim.persistence_proof_world_session import open_proof_world_session
from ate_sim.persistence_sqlite_guard import _NativeGuardCursor
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, legacy_lazy


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(root, output):
    root.mkdir(parents=True, exist_ok=False)
    rows = []
    for size in (1000, 10000):
        folder = root / str(size)
        folder.mkdir()
        def configure(world):
            world.settlements[1] = Settlement(1, 0, 0, memory={'war': .25})
        legacy = legacy_lazy(folder, size=size, configure=configure)
        source, target = folder/'complete.sqlite', folder/'proof.sqlite'
        upgrade_lazy_snapshot(legacy, source, rules_id=RULES)
        with open_lazy_world_session(source, rules_id=RULES) as session:
            expected = session.world.digest()
            assert session.skills[1, 'craft'].provenance is session.skills[2, 'craft'].provenance
        before = digest(source)
        counts = Counter()
        execute = _NativeGuardCursor.execute
        audit = LazyRecordStore._verify_all_in_snapshot
        def traced(cursor, sql, *args, **kwargs):
            counts['sql_calls'] += 1
            text = sql.lower()
            if 'from save_head' in text: counts['head_queries'] += 1
            if 'integrity_check' in text: counts['physical_checks'] += 1
            return execute(cursor, sql, *args, **kwargs)
        def scrub(store):
            counts['full_source_audits'] += 1
            return audit(store)
        _NativeGuardCursor.execute = traced
        LazyRecordStore._verify_all_in_snapshot = scrub
        started = time.perf_counter()
        try:
            copied = copy_world_with_proofs(source, target, rules_id=RULES, rank_proofs=True)
        finally:
            elapsed = time.perf_counter() - started
            _NativeGuardCursor.execute = execute
            LazyRecordStore._verify_all_in_snapshot = audit
        assert digest(source) == before
        with open_proof_world_session(target, rules_id=RULES, expected_commitment=copied.commitment) as session:
            assert session.world.digest() == expected
            history = session.skills[1, 'craft'].provenance
            assert history is session.skills[2, 'craft'].provenance
            assert len(history) == size and history[0] == 0 and history[-1] == size-1
        row = dict(size=size, status='complete', diagnostic_wall_seconds=elapsed,
            counts=dict(counts), source_bytes=source.stat().st_size,
            source_sha256=before, source_unchanged=True, canonical_digest=expected,
            exact_aliases=True)
        rows.append(row)
        print(json.dumps(row), flush=True)
    result = dict(status='complete', head=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip(), results=rows,
        limitation='Small complete Worlds with retained history values; instrumented construction only; no mature or interactive timing claim',
        runtime_files={str(path): digest(path) for path in sorted(Path('simulation/ate_sim').glob('*.py'))})
    output.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.root, args.output)
