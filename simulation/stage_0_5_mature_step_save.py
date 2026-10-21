"""Matched mature-year step/save/warm-step timing and fresh restore checks.

This small, bounded harness uses the same authenticated year-1001 source and
runtime identity helpers as the open benchmark. The saved database is captured
at year 1002 before the warm year-1003 step, so a separate process can validate
the exact persisted year-1002 state.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import sqlite3
import time

from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation import continuation_receipts as r
from simulation import profile_stage_0_5_performance as base


PHASES = ('open', 'first_step', 'save', 'warm_step')


def _world(session):
    return base._world(session)


def run(source, output, *, seconds, expected_sha256, authority):
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('seconds must be finite and positive')
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source.is_relative_to(output):
        raise ValueError('output cannot contain source')
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'ate-mature-step-save/1', 'status': 'error',
              'source': r.plain(authority), 'harness_sha256': r.file_hash(__file__),
              'runtime': base._runtime_identity(),
              'machine': {'platform': platform.platform(), 'processor': platform.processor(),
                          'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
                          'cpu_count': os.cpu_count()},
              'budget_seconds': seconds, 'phases': {}, 'unavailable': ['phase_peak_rss']}
    session = None
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    if old_timer[0]:
        raise ValueError('cannot replace an active caller alarm')

    def expired(*_args):
        raise base.BudgetExpired('mature step/save run budget exhausted')

    def measure(name, operation):
        if session is not None:
            session.store.reset_diagnostics()
        started, cpu, rss = time.perf_counter(), time.process_time(), base._rss()
        row = {'status': 'error', 'rss_start_bytes': rss}
        result['phases'][name] = row
        try:
            value = operation()
            row['status'] = 'complete'
            return value
        except base.BudgetExpired:
            row['status'] = 'timeout'
            raise
        finally:
            row.update(wall_seconds=time.perf_counter() - started,
                       cpu_seconds=time.process_time() - cpu, rss_end_bytes=base._rss(),
                       process_peak_rss_bytes=base._peak_rss())
            if session is not None:
                row['io'] = asdict(session.store.diagnostics())
                row['working_set'] = r.plain(base._diagnostics(session))

    try:
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        base._verify_authority(source, expected_sha256, authority)
        if shutil.disk_usage(output).free < source.stat().st_size + 8 * 1024**2:
            raise ValueError('insufficient space for disposable checkpoint')
        target = output / 'operational.sqlite'
        shutil.copyfile(source, target)
        if r.file_hash(target) != expected_sha256:
            raise ValueError('disposable copy checksum differs')

        session = measure('open', lambda: open_lazy_world_session(
            target, rules_id=authority['rules_id']))
        result['initial'] = _world(session)
        pin = authority['pin']
        if (session.pin.store_identity != pin['store_identity']
                or session.pin.captured_head != pin['captured_head']
                or {key: result['initial'][key] for key in ('seed', 'year')} != authority['world']):
            raise ValueError('opened world/pin differs from source authority')

        measure('first_step', lambda: Simulation(session.world).run(1))
        if session.world.year != authority['world']['year'] + 1:
            raise ValueError('first step did not advance exactly one year')
        measure('save', session.save)
        result['saved'] = _world(session)
        if (result['saved']['year'] != authority['world']['year'] + 1
                or result['saved']['pin']['store_identity'] != pin['store_identity']
                or result['saved']['pin']['captured_head'] != pin['captured_head'] + 1):
            raise ValueError('saved state is not the expected one-generation successor')

        measure('warm_step', lambda: Simulation(session.world).run(1))
        result['final'] = _world(session)
        if (result['final']['year'] != authority['world']['year'] + 2
                or result['final']['pin'] != result['saved']['pin']):
            raise ValueError('warm step changed the saved pin or advanced the wrong year')
        result['status'] = 'complete'
    except base.BudgetExpired as exc:
        result.update(status='timeout', error=str(exc))
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            if session is not None:
                session.close()
        except Exception as exc:
            result.update(status='error', close_error=f'{type(exc).__name__}: {exc}')
        try:
            result['source_unchanged'] = r.file_hash(source) == expected_sha256
            if not result['source_unchanged']:
                result.update(status='error', error='source changed during run')
        finally:
            signal.signal(signal.SIGALRM, old_handler)
        target = output / 'operational.sqlite'
        if result['status'] == 'complete':
            if not target.is_file() or target.is_symlink():
                result.update(status='error', error='saved checkpoint is not a regular file')
            elif any(Path(str(target) + suffix).exists()
                     for suffix in ('-wal', '-journal', '-shm')):
                result.update(status='error', error='saved checkpoint is not closed and standalone')
            else:
                result['saved_database'] = {'sha256': r.file_hash(target),
                                            'bytes': target.stat().st_size}
        r.publish_receipt(output / 'result.json', result)
    return result


def verify_checkpoint(database, output, *, expected_sha256, expected_bytes, rules_id,
                      expected_year, expected_seed, expected_generation,
                      expected_store_identity, expected_digest):
    database = Path(database).resolve()
    output = Path(output).resolve()
    result = {'schema': 'ate-mature-fresh-restore/1', 'status': 'error',
              'expected': {'sha256': expected_sha256, 'bytes': expected_bytes,
                           'rules_id': rules_id, 'year': expected_year,
                           'seed': expected_seed, 'generation': expected_generation,
                           'store_identity': expected_store_identity, 'digest': expected_digest}}
    session = None
    try:
        if database.is_symlink() or not database.is_file():
            raise ValueError('checkpoint must be a regular file')
        if any(Path(str(database) + suffix).exists()
               for suffix in ('-wal', '-journal', '-shm')):
            raise ValueError('checkpoint is not closed and standalone')
        before = r.file_hash(database)
        if database.stat().st_size != expected_bytes or before != expected_sha256:
            raise ValueError('checkpoint bytes/hash differ from the saved artifact')

        session = open_lazy_world_session(database, rules_id=rules_id)
        pin = asdict(session.pin)
        world = {'seed': session.world.seed, 'year': session.world.year}
        actual_digest = session.world.digest()
        result.update(world=world, pin=pin, actual_digest=actual_digest)
        if world != {'seed': expected_seed, 'year': expected_year}:
            raise ValueError('freshly opened world seed/year differs')
        if (pin['store_identity'] != expected_store_identity
                or pin['captured_head'] != expected_generation):
            raise ValueError('freshly opened store identity/generation differs')
        if actual_digest != expected_digest:
            raise ValueError('freshly opened world digest differs')
        session.close()
        session = None
        reopened_hash = r.file_hash(database)
        result['database_sha256_after_restore_close'] = reopened_hash
        result['database_bytes_after_restore_close'] = database.stat().st_size
        result['database_bytes_changed_by_restore_open'] = reopened_hash != before
        if any(Path(str(database) + suffix).exists()
               for suffix in ('-wal', '-journal', '-shm')):
            raise ValueError('fresh verification left SQLite sidecars')
        result['status'] = 'complete'
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result['close_error'] = f'{type(exc).__name__}: {exc}'
                result['status'] = 'error'
        r.publish_receipt(output, result)
    return result


def compare_receipts(baseline, candidate):
    for row in (baseline, candidate):
        if row.get('schema') != 'ate-mature-step-save/1' or row.get('status') != 'complete':
            raise ValueError('comparison requires complete mature step/save receipts')
        if set(row.get('phases', {})) != set(PHASES):
            raise ValueError('measurement phases differ from the required workload')
        if any(row['phases'][name].get('status') != 'complete'
               or row['phases'][name].get('wall_seconds', 0) <= 0 for name in PHASES):
            raise ValueError('measurement phase is incomplete')
        if not row.get('source_unchanged'):
            raise ValueError('source immutability was not preserved')
        saved_database = row.get('saved_database')
        if not isinstance(saved_database, dict):
            raise ValueError('saved checkpoint manifest is missing')
        r.exact(saved_database, ('sha256', 'bytes'), 'saved checkpoint manifest')
        r.hexadecimal(saved_database['sha256'], 64, 'saved checkpoint checksum')
        r.integer(saved_database['bytes'], 'saved checkpoint size', minimum=1)
    if not r.same(baseline['source'], candidate['source']):
        raise ValueError('comparison source/configuration differs')
    if baseline['harness_sha256'] != candidate['harness_sha256']:
        raise ValueError('comparison harness differs')
    if baseline['machine'] != candidate['machine']:
        raise ValueError('comparison machine/runtime instrumentation differs')
    for label in ('initial', 'saved', 'final'):
        left, right = baseline[label], candidate[label]
        if any(left[key] != right[key] for key in ('seed', 'year', 'actions')):
            raise ValueError(f'{label} world differs')
        if any(left['pin'][key] != right['pin'][key]
               for key in ('store_identity', 'captured_head')):
            raise ValueError(f'{label} pin differs')
    for row in (baseline, candidate):
        if (row['saved']['year'] != row['initial']['year'] + 1
                or row['final']['year'] != row['saved']['year'] + 1
                or row['saved']['pin']['captured_head'] != row['initial']['pin']['captured_head'] + 1
                or row['final']['pin'] != row['saved']['pin']):
            raise ValueError('step/save/warm-step state sequence is invalid')
    return {'schema': 'ate-mature-step-save-comparison/1',
            'source_sha256': baseline['source']['database']['sha256'],
            'saved_database': {
                'baseline': baseline.get('saved_database'),
                'candidate': candidate.get('saved_database'),
                'byte_identical': baseline.get('saved_database') == candidate.get('saved_database')},
            'phases': {name: {'baseline_seconds': baseline['phases'][name]['wall_seconds'],
                              'candidate_seconds': candidate['phases'][name]['wall_seconds'],
                              'speedup': baseline['phases'][name]['wall_seconds'] /
                                         candidate['phases'][name]['wall_seconds']}
                       for name in PHASES}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run_parser = sub.add_parser('run')
    run_parser.add_argument('source', type=Path)
    run_parser.add_argument('output', type=Path)
    run_parser.add_argument('--seconds', type=float, required=True)
    run_parser.add_argument('--expected-sha256', required=True)
    run_parser.add_argument('--authority', type=Path, required=True)
    verify_parser = sub.add_parser('verify')
    verify_parser.add_argument('database', type=Path)
    verify_parser.add_argument('output', type=Path)
    verify_parser.add_argument('--expected-sha256', required=True)
    verify_parser.add_argument('--expected-bytes', type=int, required=True)
    verify_parser.add_argument('--rules-id', required=True)
    verify_parser.add_argument('--expected-year', type=int, required=True)
    verify_parser.add_argument('--expected-seed', type=int, required=True)
    verify_parser.add_argument('--expected-generation', type=int, required=True)
    verify_parser.add_argument('--expected-store-identity', required=True)
    verify_parser.add_argument('--expected-digest', required=True)
    compare_parser = sub.add_parser('compare')
    compare_parser.add_argument('baseline', type=Path)
    compare_parser.add_argument('candidate', type=Path)
    compare_parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'run':
        result = run(args.source, args.output, seconds=args.seconds,
                     expected_sha256=args.expected_sha256,
                     authority=r.load_receipt(args.authority))
        receipt_path = args.output / 'result.json'
    elif args.command == 'verify':
        result = verify_checkpoint(args.database, args.output,
            expected_sha256=args.expected_sha256, expected_bytes=args.expected_bytes,
            rules_id=args.rules_id, expected_year=args.expected_year,
            expected_seed=args.expected_seed, expected_generation=args.expected_generation,
            expected_store_identity=args.expected_store_identity,
            expected_digest=args.expected_digest)
        receipt_path = args.output
    else:
        result = compare_receipts(r.load_receipt(args.baseline), r.load_receipt(args.candidate))
        r.publish_receipt(args.output, result)
        receipt_path = args.output
    print(json.dumps({'status': result.get('status', 'complete'), 'receipt': str(receipt_path)}))
    return 0 if result.get('status', 'complete') == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
