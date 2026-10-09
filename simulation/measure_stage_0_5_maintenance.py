"""Actual bounded GC and SQLite VM work with valid expired-version backlogs.

PYTHONPATH=.:simulation python simulation/measure_stage_0_5_maintenance.py --output result.json
Fixture construction suppresses reclamation to isolate history-sensitive reads.
The real cleanup implementation is restored for measured ordinary commits.
This is a store gate, not integrated World/identity/pressure acceptance.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time
import tracemalloc

from simulation.ate_sim.incremental_store import Membership
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata
from simulation.tests.test_stage_0_5_final_maintenance import vm_steps, eligible


def difference(after, before): return {key: after[key] - before[key] for key in after}


def measure(history, path):
    with make_store(path) as store:
        pin = store.capture_pin()
        actual_cleanup = store._cleanup_expired
        store._cleanup_expired = lambda floor, **kw: 0
        for year in range(1, history + 1):
            pin = store.commit(pin, commit_token=year,
                version_changes=(VersionChange('people', 1, year, reinsertion=year > 1,
                    memberships=(Membership('fixed', True, 0),)),),
                identity_changes=(IdentityOccurrenceChange('people', 1, (), year % 2 + 1),),
                next_incarnation_id=year + 3, changes=(), new_segments=(),
                metadata=metadata(year, ('people',))).pin
        store._cleanup_expired = actual_cleanup
        key = store.codec.encode(1)
        path_key = store.codec.encode(())
        queries = {
            'checked_record': lambda: store.read_version(pin, 'people', 1, expected_record_schema=1),
            'order': lambda: store._visible_order('people', key, history),
            'namespace': lambda: store._namespace_state_at('people', history),
            'allocator': lambda: store._identity_state_at(history),
            'occurrence': lambda: store._visible_identity_occurrence(history, 'people', key, path_key),
            'reverse_group': lambda: store.identity_occurrences_for_incarnation(pin, 1),
            'owner': lambda: store.identity_occurrences_for_owner(pin, 'people', 1),
            'limited_query': lambda: store.query_memberships(pin, 'people', 'fixed', True, limit=1),
        }
        measured = {}
        for name, query in queries.items():
            before = asdict(store.diagnostics())
            started = time.perf_counter()
            steps, _ = vm_steps(store, query)
            measured[name] = {'sqlite_vm_steps': steps, 'seconds': time.perf_counter() - started,
                'io': difference(asdict(store.diagnostics()), before), 'sql_rows_examined': None}
        backlog_before = eligible(store, history)
        before = asdict(store.diagnostics())
        tracemalloc.start()
        started = time.perf_counter()
        steps, committed = vm_steps(store, lambda: store.commit(pin, commit_token='scalar',
            version_changes=(VersionChange('people', 1, history + 1,
                memberships=(Membership('fixed', True, 0),)),), changes=(), new_segments=(),
            metadata=metadata(history + 1, ('people',))))
        duration = time.perf_counter() - started
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        pin = committed.pin
        commit_io = difference(asdict(store.diagnostics()), before)
        assert commit_io['maintenance_removed_rows'] <= 256
        backlog_after = eligible(store, history + 1)
        before = asdict(store.diagnostics())
        explicitly_removed = store.maintenance(row_budget=64)
        explicit_io = difference(asdict(store.diagnostics()), before)
        report = store.verify_all()
        assert report['expired_rows_pending_maintenance'] == eligible(store, history + 1)
        plan = [row[3] for row in store.db.execute(
            'EXPLAIN QUERY PLAN SELECT valid_from FROM lazy_record_versions INDEXED BY lazy_record_interval '
            'WHERE namespace=? AND typed_key=? AND valid_to IS NULL AND valid_from<=? UNION ALL '
            'SELECT valid_from FROM lazy_record_versions INDEXED BY lazy_record_interval '
            'WHERE namespace=? AND typed_key=? AND valid_to>? AND valid_from<=? LIMIT 2',
            ('people', key, pin.captured_head, 'people', key, pin.captured_head, pin.captured_head))]
        return {'H': history, 'reads': measured, 'ordinary_scalar_commit': {'sqlite_vm_steps': steps,
                'seconds': duration, 'io': commit_io, 'tracemalloc_current_bytes': current,
                'tracemalloc_peak_bytes': peak}, 'expired_rows_before_commit': backlog_before,
            'expired_rows_after_commit': backlog_after, 'explicit_maintenance': {
                'row_budget': 64, 'removed': explicitly_removed, 'io': explicit_io},
            'point_query_plan': plan, 'sql_rows_examined': None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).parent
    names = ('persistence_lazy_store.py', 'persistence_lazy_identity_catalog.py')
    hashes = {name: hashlib.sha256((root / 'ate_sim' / name).read_bytes()).hexdigest() for name in names}
    with tempfile.TemporaryDirectory() as temporary:
        results = [measure(h, Path(temporary) / f'{h}.sqlite') for h in (1000, 10000)]
    result = {'scope': 'store maintenance and backlog reads; not World or pressure acceptance',
        'fixture': 'genuine MVCC versions with cleanup suspended during construction only',
        'source_sha256': hashes, 'measurements': results}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{'H': r['H'], 'read_vm_steps': {k: v['sqlite_vm_steps'] for k, v in r['reads'].items()},
        'commit_vm_steps': r['ordinary_scalar_commit']['sqlite_vm_steps'],
        'ordinary_rows_removed': r['ordinary_scalar_commit']['io']['maintenance_removed_rows'],
        'explicit_rows_removed': r['explicit_maintenance']['removed']} for r in results], indent=2))


if __name__ == '__main__': main()
