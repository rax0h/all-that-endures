"""Focused World scalar-edit evidence; not final integrated Stage 0.5 acceptance."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time
import tracemalloc

from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_persistence_lazy_people import converted_people_store, RULES


def measure(root, count):
    path = converted_people_store(root, count, active=8, name=f'participants-{count}')
    with open_lazy_world_session(path, rules_id=RULES) as session:
        person = session.world.people[1]
        before = person.wealth
        old = session.store.capture_pin()
        person.wealth += 1.
        session.store.reset_diagnostics()
        frozen = {}
        def capture(phase):
            if phase == 'before_commit':
                publication = session._pending_save.publication
                frozen.update(bytes=publication.frozen_bytes,
                    participants=len(publication.participants),
                    namespaces=[unit.namespace for unit in publication.participants])
        session.store._phase_hook = capture
        tracemalloc.start()
        started = time.perf_counter()
        generation = session.save()
        elapsed = time.perf_counter() - started
        traced, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        counters = asdict(session.store.diagnostics())
        session.store._phase_hook = lambda phase: None
        counters['sql_rows_examined'] = None
        assert session.store.read_version(old, 'world.people', 1,
            expected_record_schema=1).value.wealth == before
        session.store.release_pin(old)
        session.store.reset_diagnostics()
        reads = []
        read_record, read_version, read_records = session.store.read_record, session.store.read_version, session.store.read_records
        def ordinary_read(namespace, key, **kwargs):
            reads.append(('ordinary', namespace, key))
            return read_record(namespace, key, **kwargs)
        def version_read(pin, namespace, key, **kwargs):
            reads.append(('version', namespace, key))
            return read_version(pin, namespace, key, **kwargs)
        def ordinary_rows(namespace, **kwargs):
            reads.append(('ordinary-bulk', namespace, None))
            return read_records(namespace, **kwargs)
        session.store.read_record, session.store.read_version = ordinary_read, version_read
        session.store.read_records = ordinary_rows
        assert session.save() == generation
        noop = asdict(session.store.diagnostics())
        session.store.read_record, session.store.read_version = read_record, read_version
        session.store.read_records = read_records
        # These legacy control descriptors count as payload IO in store counters.
        # Report them honestly; the contract prohibits archive payload reads.
        assert noop['payload_writes'] == 0
        assert all(kind in ('ordinary', 'ordinary-bulk') and namespace == 'world_event_storage' for kind, namespace, key in reads)
        noop['checked_control_reads'] = reads
        return dict(history_owners=count, live_candidates=8, edits=1, seconds=elapsed,
            traced_python_retained_bytes=traced, traced_python_peak_bytes=peak,
            frozen=frozen, save=counters, subsequent_noop=noop, old_pin_exact=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    simulation = Path(__file__).resolve().parent
    sources = ('ate_sim/persistence_lazy.py', 'ate_sim/persistence_lazy_families.py',
               'ate_sim/persistence_lazy_participants.py', 'ate_sim/persistence_lazy_store.py',
               'measure_stage_0_5_participants.py')
    with tempfile.TemporaryDirectory(prefix='ate-participants-') as directory:
        rows = [measure(Path(directory), count) for count in (1000, 10000)]
    payload = dict(scope='legacy World scalar edit + immutable participant integration; not final acceptance',
        limitations=['No claim about global identity discovery, households, nested closure or pressure.',
                     'Fixture has no cross-family sharing placements; separate alias tests cover compatibility.',
                     'SQL examined rows and total process RSS are not measured.',
                     'tracemalloc excludes fixture construction and native SQLite memory.'],
        source_sha256={name: hashlib.sha256((simulation / name).read_bytes()).hexdigest() for name in sources},
        results=rows)
    Path(args.output).write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
