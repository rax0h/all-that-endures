"""Bounded, disposable checkpoint phase measurements; not continuation acceptance.

The caller supplies a source authority receipt obtained from the fixture builder
or authenticated artifact transport. Hash/size and opened world/store identity
are checked here. The receipt records that provenance, not a new CI attestation.
"""
from __future__ import annotations

import argparse
import cProfile
from contextlib import nullcontext
from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import resource
import shutil
import signal
import sqlite3
import subprocess
import sys
import time

from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation import continuation_receipts as r


class BudgetExpired(Exception):
    pass


def _git(*args, cwd):
    try:
        return subprocess.check_output(['git', *args], cwd=cwd,
            stderr=subprocess.DEVNULL).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _runtime_identity():
    engine = Path(sys.modules[Simulation.__module__].__file__).resolve()
    persistence = Path(sys.modules[open_lazy_world_session.__module__].__file__).resolve()
    if engine.parent != persistence.parent:
        raise ValueError('mixed runtime roots are not measurable')
    root = engine.parents[2]
    return {'head': _git('rev-parse', 'HEAD', cwd=root),
            'committed_tree': _git('rev-parse', 'HEAD:simulation/ate_sim', cwd=root),
            'source_sha256': _source_code_digest(engine.parent), 'root': str(root),
            'engine_path': str(engine), 'persistence_path': str(persistence)}


def _source_code_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.glob('*.py')):
        digest.update(path.name.encode() + b'\0')
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
    return digest.hexdigest()


def _rss():
    try:
        with Path('/proc/self/statm').open() as stream:
            import os
            return int(stream.read().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    except (OSError, ValueError, IndexError):
        return None


def _peak_rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024


def _world(session):
    return {'seed': session.world.seed, 'year': session.world.year,
            'pin': asdict(session.pin), 'actions': len(session.world.agency.actions)}


def _verify_authority(source, expected, authority):
    r.exact(authority, ('schema', 'database', 'rules_id', 'pin', 'world', 'provenance'), 'performance source')
    if authority['schema'] != 'ate-performance-source/1':
        raise ValueError('unknown performance source schema')
    r.exact(authority['database'], ('sha256', 'bytes'), 'source database')
    r.hexadecimal(expected, 64, 'expected checksum')
    r.text_value(authority['rules_id'], 'rules ID')
    r.exact(authority['world'], ('seed', 'year'), 'source world')
    r.exact(authority['pin'], ('token', 'store_identity', 'captured_head'), 'source pin')
    r.integer(authority['pin']['captured_head'], 'source generation')
    if not isinstance(authority['provenance'], dict) or not authority['provenance']:
        raise ValueError('source provenance is required')
    if source.is_symlink() or not source.is_file():
        raise ValueError('source must be a regular checkpoint')
    if any(Path(str(source)+suffix).exists() for suffix in ('-wal', '-journal')):
        raise ValueError('source must be a closed standalone checkpoint')
    if (authority['database']['sha256'] != expected or source.stat().st_size != authority['database']['bytes']
            or r.file_hash(source) != expected):
        raise ValueError('source checksum/size differs from authority')


def _attribution():
    # The common helper can be loaded from a newer checkout while simulation
    # imports deliberately select an older baseline runtime.
    path = Path(__file__).resolve().with_name('performance_attribution.py')
    spec = importlib.util.spec_from_file_location('ate_performance_attribution', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PerformanceAttribution()


def _attribution_helper_sha256():
    return r.file_hash(Path(__file__).resolve().with_name('performance_attribution.py'))


def _compare_attribution_helpers(baseline, candidate):
    if baseline.get('instrumentation') == 'attribution-v1':
        checksum = baseline.get('attribution_helper_sha256')
        if (type(checksum) is not str or len(checksum) != 64
                or any(c not in '0123456789abcdef' for c in checksum)
                or checksum != candidate.get('attribution_helper_sha256')):
            raise ValueError('comparison attribution helper differs or is missing')


def run_phase(source, output, *, phase, seconds, expected_sha256, authority, profiled=False, warm_steps=0, attributed=False):
    if phase not in ('open', 'step', 'step-save'):
        raise ValueError('unknown phase')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('seconds must be finite and positive')
    if type(warm_steps) is not int or not 0 <= warm_steps <= 25 or phase == 'open' and warm_steps:
        raise ValueError('warm_steps must be an exact integer 0..25, and zero for open')
    if attributed and profiled:
        raise ValueError('choose attribution or cProfile instrumentation, not both')
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source.is_relative_to(output):
        raise ValueError('output cannot contain source')
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'ate-performance-phase/1', 'status': 'error', 'source': r.plain(authority),
              'profiled': profiled, 'requested_phase': phase, 'warm_steps': warm_steps,
              'instrumentation': 'attribution-v1' if attributed else 'cprofile' if profiled else 'none',
              'attribution_helper_sha256': _attribution_helper_sha256() if attributed else None,
              'budget_seconds': seconds, 'phases': {}, 'runtime': _runtime_identity(),
              'harness_sha256': r.file_hash(__file__),
              'machine': {'platform': platform.platform(), 'processor': platform.processor(),
                          'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version},
              'unavailable': ['physical_disk_bytes', 'sqlite_cache_hits', 'phase_peak_rss']}
    session = None
    trace = _attribution() if attributed else None
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    if old_timer[0]:
        raise ValueError('cannot replace an active caller alarm')

    def expired(*_args):
        raise BudgetExpired('performance run budget exhausted')

    def measure(name, operation):
        nonlocal session
        if session is not None:
            session.store.reset_diagnostics()
        started, cpu, rss = time.perf_counter(), time.process_time(), _rss()
        row = {'status': 'error', 'rss_start_bytes': rss}
        result['phases'][name] = row
        profiler = cProfile.Profile() if profiled else None
        try:
            if profiler: profiler.enable()
            with trace.phase(name) if trace is not None else nullcontext():
                value = operation()
                if name == 'open': session = value
            row['status'] = 'complete'
            return value
        except BudgetExpired:
            row['status'] = 'timeout'
            raise
        finally:
            if profiler: profiler.disable()
            row.update(wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu,
                       rss_end_bytes=_rss(), process_peak_rss_bytes=_peak_rss())
            if session is not None:
                row['io'] = asdict(session.store.diagnostics())
                row['working_set'] = r.plain(_diagnostics(session))
            if trace is not None:
                row['attribution'] = trace.snapshot()
            if profiler:
                profiler.dump_stats(str(output/(name+'.prof')))
                # Counts only; elapsed cProfile values are a separate diagnostic lane.
                import pstats
                stats = pstats.Stats(profiler)
                names = {'_checked_operational_rows', '_shared_object_routes', 'read_identity_group',
                         'read_owner_identity', '_ensure_selection_index', 'best_at_rank',
                         'crafting_capacity', 'validate_publication'}
                row['calls'] = {name: sum(v[1] for k,v in stats.stats.items() if k[2] == name)
                                for name in sorted(names)}
            # Publish outside the measured interval; never use partial progress
            # as an acceptance receipt or as authority for a saved checkpoint.
            r.publish_receipt(output / f'phase-progress-{name}.json', {
                'schema': 'ate-performance-progress/1', 'measurement': r.plain(result)})

    try:
        if trace is not None: trace.__enter__()
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        _verify_authority(source, expected_sha256, authority)
        if shutil.disk_usage(output).free < source.stat().st_size + 8*1024**2:
            raise ValueError('insufficient space for disposable checkpoint')
        target = output/'operational.sqlite'
        shutil.copyfile(source, target)
        if r.file_hash(target) != expected_sha256:
            raise ValueError('disposable copy checksum differs')
        measure('open', lambda: open_lazy_world_session(target, rules_id=authority['rules_id']))
        result['initial'] = _world(session)
        # A newly acquired lease has a new token. The source pin is retained in
        # provenance; exact opened lease tokens are recorded in initial/final.
        pin = authority['pin']
        if (session.pin.store_identity != pin['store_identity'] or session.pin.captured_head != pin['captured_head']
                or {k: result['initial'][k] for k in ('seed','year')} != authority['world']):
            raise ValueError('opened world/pin differs from source authority')
        if phase != 'open': measure('step', lambda: Simulation(session.world).run(1))
        for n in range(warm_steps):
            measure(f'warm_step_{n+1}', lambda: Simulation(session.world).run(1))
        if phase == 'step-save': measure('save', session.save)
        result['final'] = _world(session)
        result['status'] = 'complete'
    except BudgetExpired as exc:
        result.update(status='timeout', error=str(exc))
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            if session is not None: session.close()
        except Exception as exc:
            result.update(status='error', close_error=f'{type(exc).__name__}: {exc}')
        finally:
            if trace is not None: trace.__exit__(None, None, None)
        try:
            result['source_unchanged'] = r.file_hash(source) == expected_sha256
            if not result['source_unchanged']: result.update(status='error', error='source changed during run')
        finally:
            signal.signal(signal.SIGALRM, old_handler)
        (output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def _diagnostics(session):
    """Snapshot existing counters without serializing arbitrary native objects."""
    from dataclasses import is_dataclass
    def plain(value):
        if is_dataclass(value): return plain(asdict(value))
        if isinstance(value, dict): return {str(k): plain(v) for k,v in value.items()}
        if isinstance(value, (tuple, list)): return [plain(v) for v in value]
        return value
    snapshot = plain(session.diagnostics())
    coordinator = getattr(session, '_identity_coordinator', None)
    if coordinator is not None:
        snapshot['identity_coordinator'] = plain(coordinator.diagnostics())
    return snapshot


def compare_receipts(baseline, candidate):
    for row in (baseline, candidate):
        if row.get('schema') != 'ate-performance-phase/1' or row.get('status') != 'complete':
            raise ValueError('comparison requires complete performance receipts')
    if not r.same(baseline['source'], candidate['source']):
        raise ValueError('comparison source/configuration differs')
    if baseline['profiled'] != candidate['profiled']:
        raise ValueError('comparison instrumentation differs')
    if baseline.get('instrumentation', 'none') != candidate.get('instrumentation', 'none'):
        raise ValueError('comparison instrumentation differs')
    _compare_attribution_helpers(baseline, candidate)
    if baseline['harness_sha256'] != candidate['harness_sha256']:
        raise ValueError('comparison harness differs')
    if (baseline['machine'] != candidate['machine'] or baseline['requested_phase'] != candidate['requested_phase']
            or baseline['warm_steps'] != candidate['warm_steps']
            or set(baseline['phases']) != set(candidate['phases'])):
        raise ValueError('comparison runner/phase differs')
    return {name: {'baseline_seconds': row['wall_seconds'],
                   'candidate_seconds': candidate['phases'][name]['wall_seconds'],
                   'speedup': row['wall_seconds']/candidate['phases'][name]['wall_seconds']}
            for name, row in baseline['phases'].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--phase', choices=('open','step','step-save'), required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--authority', type=Path, required=True)
    parser.add_argument('--profiled', action='store_true')
    parser.add_argument('--attributed', action='store_true')
    parser.add_argument('--warm-steps', type=int, default=0)
    args = parser.parse_args()
    result = run_phase(args.source, args.output, phase=args.phase, seconds=args.seconds,
        expected_sha256=args.expected_sha256, authority=r.load_receipt(args.authority), profiled=args.profiled,
        warm_steps=args.warm_steps, attributed=args.attributed)
    print(json.dumps({'status': result['status'], 'receipt': str(args.output/'result.json')}))
    return 0 if result['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
