"""Legacy-runtime budget evidence; does not claim new-format catalog bounds."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time
import tracemalloc

from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy_budget import schema_resident_bytes
from simulation.tests.test_persistence_lazy_people import people_world, RULES


def measure(root, history):
    world = people_world(history, active=8)
    world.currency.wallets[1] = {'alias': world.people[1]}
    source, target = root / f'source-{history}.sqlite', root / f'target-{history}.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    convert_cold_to_lazy(source, target, rules_id=RULES)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_digest
    with open_lazy_world_session(target, rules_id=RULES) as session:
        opening = asdict(session.store.diagnostics())
        candidates = [session.people[pid] for pid in range(1, 9)]
        alias = session.wallets[1]['alias']
        assert alias is candidates[0]
        old_pin = session.store.capture_pin()
        previous = alias.wealth
        session.store.reset_diagnostics()
        tracemalloc.start()
        started = time.perf_counter()
        alias.wealth += 1.
        dirty = dict(owners=sum(len(table._dirty) for table in session._family_bindings.tables.values()),
                     resident_python_bytes=schema_resident_bytes((alias, dict.__getitem__(session.wallets, 1))))
        generation = session.save()
        elapsed = time.perf_counter() - started
        retained, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        save_io = asdict(session.store.diagnostics())
        assert session.store.read_version(old_pin, 'world.people', 1, expected_record_schema=1).value.wealth == previous
        session.store.release_pin(old_pin)
        session.store.reset_diagnostics()
        assert session.save() == generation
        noop = asdict(session.store.diagnostics())
        clean_edit = session._record_cache_budget.diagnostics()
        # Explicit cache-churn read is separate from the fixed-current-work edit.
        session.store.reset_diagnostics()
        tracemalloc.start()
        for pid in range(1, history + 1):
            session.people[pid]
        churn_retained, churn_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        churn_io = asdict(session.store.diagnostics())
        clean_churn = session._record_cache_budget.diagnostics()
        assert clean_churn['bytes'] <= 32 * 1024 * 1024
        assert len(session.people._lru) <= 256
        assert session.people[1] is alias
        assert candidates[0] is alias
        for table in session._family_bindings.tables.values():
            for name in ('_baseline_payload', '_baseline_presence', '_baseline_incarnation',
                         '_baseline_ordinal', '_baseline_identity_labels'):
                assert set(getattr(table, name, {})) <= set(dict.keys(table)) | table._dirty
        return dict(history_owners=history, live_candidates=8, edits=1, sharing_placements=2,
            source_preserved=True, open_io=opening, save_io=save_io, subsequent_noop=noop,
            edit_seconds=elapsed, dirty_before_save=dirty,
            edit_traced_retained_bytes=retained, edit_traced_peak_bytes=peak,
            clean_after_edit=clean_edit, clean_after_explicit_churn=clean_churn,
            explicit_churn_io=churn_io, churn_traced_retained_bytes=churn_retained,
            churn_traced_peak_bytes=churn_peak, external_aliases=8,
            old_pin_exact=True, retained_alias_is_canonical=True, sql_rows_examined=None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    simulation = Path(__file__).resolve().parent
    sources = ('ate_sim/persistence_lazy.py', 'ate_sim/persistence_tracking.py', 'ate_sim/persistence_lazy_budget.py',
               'ate_sim/persistence_lazy_families.py', 'ate_sim/persistence_lazy_lineage_children.py',
               'measure_stage_0_5_record_budget.py')
    with tempfile.TemporaryDirectory(prefix='ate-record-budget-') as directory:
        rows = [measure(Path(directory), history) for history in (1000, 10000)]
    payload = dict(scope='legacy World shared record-cache bytes and concrete alias routing; not final acceptance',
        limitations=['Legacy ordinary open still reads global P2C authority; new-format catalog is not activated.',
            'Legacy hot-step entry-count behavior is preserved; a complete capability6 runtime still needs strict per-family counts.',
            'Unpaged skill/resource/soul nested histories remain outside history-budget closure.',
            'Clean bytes are recursive Python residency estimates, not RSS. tracemalloc excludes native SQLite and fixture construction.',
            'Dirty estimate covers two edited payload objects, not all registry/callback/transaction memory.',
            'One long history has separate existing evidence; this fixture holds payload size fixed.',
            'SQL examined rows are unknown; returned row counters are not a scan bound.'],
        source_sha256={name: hashlib.sha256((simulation / name).read_bytes()).hexdigest() for name in sources},
        results=rows)
    Path(args.output).write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
