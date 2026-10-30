"""Fresh native scalar-owner insertion beside 1k/10k/100k retained values.

Construction/admission and instrumented SQL-work checks are separate from raw
save timing. These archives count history values, not simulated world years.
"""
import argparse
import hashlib
import json
import platform
import re
import sqlite3
import subprocess
import time
from pathlib import Path

from ate_sim.core import Person
from ate_sim import persistence_proof_world as world
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def run(output, sizes):
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked source is dirty')
    output.mkdir(parents=True, exist_ok=False)
    source = dict(head=git('rev-parse', 'HEAD'), runtime_tree=git('rev-parse', 'HEAD:simulation/ate_sim'),
                  python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                  driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    rows = []
    for size in sizes:
        start = time.perf_counter()
        path, pair = fixture(output / str(size), size=size)
        construction = time.perf_counter() - start
        start = time.perf_counter()
        session = opened(path, pair)
        admission = time.perf_counter() - start
        body_reads = 0

        def trace(sql):
            nonlocal body_reads
            text = sql.lower()
            if (text.startswith('select') and (re.search(r'(?:select|,|then)\s*payload\b', text)
                    or re.match(r'select\s+\*', text)) and any(ns in text for ns in (
                        'aux.lazy.nested.list_pages', 'aux.lazy.nested.entries',
                        'aux.lazy.sequence.nodes', 'from segments'))):
                body_reads += 1

        def forbidden(*args, **kw):
            raise AssertionError('fresh scalar insertion invoked full World audit')

        original = world._audit_world
        try:
            session.store.db.set_trace_callback(trace)
            world._audit_world = forbidden
            start = time.perf_counter()
            session.world.people[99] = Person(99, 0, 1, 1)
            session.world.next_person = 100
            assert session.save() == 1
            instrumented = time.perf_counter() - start
            pair = session.proof_manifest
        finally:
            world._audit_world = original
            session.store.db.set_trace_callback(None)
            session.close()
        assert body_reads == 0
        with opened(path, pair) as session:
            assert session.world.people[99].id == 99
            world._audit_world = forbidden
            start_wall, start_cpu = time.perf_counter(), time.process_time()
            try:
                session.world.people[100] = Person(100, 0, 1, 1)
                session.world.next_person = 101
                assert session.save() == 2
                raw_wall, raw_cpu = time.perf_counter() - start_wall, time.process_time() - start_cpu
                pair = session.proof_manifest
            finally:
                world._audit_world = original
        steps = 0

        def vm_work():
            nonlocal steps
            steps += 1
            return int(steps > 6_000_000)

        with opened(path, pair) as session:
            session.store.db.set_progress_handler(vm_work, 1)
            world._audit_world = forbidden
            try:
                session.world.people[101] = Person(101, 0, 1, 1)
                session.world.next_person = 102
                assert session.save() == 3
                pair = session.proof_manifest
            finally:
                world._audit_world = original
                session.store.db.set_progress_handler(None, 0)
        with opened(path, pair) as restored:
            assert tuple(restored.world.people) == (99, 100, 101)
            assert len(restored.skills[1, 'craft'].provenance) == size
        row = dict(size=size, archive_unit='retained history values', source=source,
                   construction_seconds=construction, audited_admission_seconds=admission,
                   traced_first_save_seconds=instrumented, raw_save_seconds=raw_wall,
                   raw_save_cpu_seconds=raw_cpu, unrelated_history_body_reads=body_reads,
                   sqlite_vm_steps=steps, full_world_audits_within_save=0,
                   database_bytes=path.stat().st_size, status='complete',
                   limitation='Synthetic history scaling; not mature-world latency acceptance')
        (output / f'size-{size}.json').write_text(json.dumps(row, indent=2) + '\n')
        rows.append(row)
        print(size, 'values:', round(raw_wall, 6), 's raw save;', steps, 'VM steps; zero history bodies', flush=True)
    (output / 'summary.json').write_text(json.dumps(dict(status='complete', source=source, results=rows), indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000, 100000])
    args = parser.parse_args()
    if not args.sizes or any(n not in (1000, 10000, 100000) for n in args.sizes):
        parser.error('sizes must be selected from 1000,10000,100000 retained values')
    run(args.output, args.sizes)
