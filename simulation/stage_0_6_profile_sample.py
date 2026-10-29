"""Bounded diagnostic of the ordinary mature path; never saves a sampled year."""
import argparse
import cProfile
import json
import math
import os
from pathlib import Path
import pstats
import shutil
import signal
import time


class _SampleTerminated(Exception):
    pass

from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.stage_0_6_mature_benchmark import Recorder, base, check_source, machine, r


def _counter_snapshot(session):
    """Read existing in-memory counters; do not query persistence metadata."""
    coordinator = getattr(session, '_identity_coordinator', None)
    catalog = getattr(coordinator, 'catalog', None)
    return {
        'owner_cache': catalog.owner_cache_diagnostics() if catalog is not None else None,
        'people': session.people.diagnostics(),
    }


def _counter_attribution(before, after):
    deltas = {}
    for section, keys in (('owner_cache', ('hits', 'misses')),
                          ('people', ('person_payload_loads',))):
        start, end = before[section], after[section]
        deltas[section] = None if start is None or end is None else {
            key: end[key] - start[key] if end[key] >= start[key] else None
            for key in keys
        }
    return {
        'start': before, 'end': after, 'deltas': deltas,
        'meaning': ('Counters are cumulative; negative differences indicate a reset and are null. '
                    'Owner-cache misses include required transactional bypasses, not just evictions. '
                    'A censored sample measures only the observed prefix.'),
    }


def sample(source, output, *, authority, open_seconds=900, step_seconds=60):
    for value, cap in ((open_seconds, 900), (step_seconds, 60)):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= cap:
            raise ValueError('sample budgets must be positive, open <=900s and step <=60s')
    source, output = Path(source).absolute(), Path(output).absolute()
    if source.is_symlink() or source == output or source.is_relative_to(output):
        raise ValueError('sample output cannot contain the retained input')
    output.mkdir(parents=True, exist_ok=False)
    rec = Recorder(output, {'open_total': open_seconds, 'first_step': step_seconds})
    result = dict(schema='ate-stage06-profile-sample/1', status='error', acceptance='not-run',
                  runtime=base._runtime_identity(), machine=machine(), phases=rec.phases,
                  source=authority, instrumentation='cProfile on sampled first step only',
                  limitation='Profile costs include instrumentation. A censored prefix is not a full year or a save benchmark.')
    session = None
    stop_active_profile = lambda: None
    previous_term = signal.getsignal(signal.SIGTERM)
    def terminated(*_):
        stop_active_profile()
        raise _SampleTerminated('sample command received SIGTERM')
    signal.signal(signal.SIGTERM, terminated)
    try:
        rec.measure('source_verification', lambda: base._verify_authority(source, authority['database']['sha256'], authority))
        if shutil.disk_usage(output).free < source.stat().st_size + 8 * 1024**3:
            raise ValueError('insufficient diagnostic copy headroom')
        target = output / 'operational.sqlite'
        rec.measure('database_copy', lambda: shutil.copyfile(source, target))
        if rec.measure('copy_verification', lambda: r.file_hash(target)) != authority['database']['sha256']:
            raise ValueError('diagnostic copy hash differs')
        try:
            with rec.split_open():
                session = rec.measure('open_total', lambda: open_lazy_world_session(target, rules_id=authority['rules_id']))
        finally:
            rec.finish_split('open_total')
        initial = base._world(session)
        if ({k: initial[k] for k in ('seed', 'year')} != authority['world']
                or any(initial['pin'][k] != authority['pin'][k] for k in ('store_identity', 'captured_head'))):
            raise ValueError('sample opened wrong world/pin')
        result['initial'] = initial
        counters_before = _counter_snapshot(session)
        profiler = cProfile.Profile()
        profile_started = profile_finished = None
        def stop_profile():
            nonlocal profile_finished
            profiler.disable()
            if profile_started is not None and profile_finished is None:
                profile_finished = time.perf_counter()
        stop_active_profile = stop_profile
        def profiled_step():
            nonlocal profile_started
            profile_started = time.perf_counter()
            profiler.enable()
            try:
                return Simulation(session.world).run(1)
            finally:
                stop_profile()
        try:
            rec.measure('first_step', profiled_step, on_budget_expiry=stop_profile)
            result['diagnostic_status'] = 'step_completed'
        except base.BudgetExpired:
            result['diagnostic_status'] = 'sample_limit_reached'
        finally:
            stop_profile()
            result['counter_attribution'] = _counter_attribution(counters_before, _counter_snapshot(session))
            phase = rec.phases['first_step']
            phase['profiled_wall_seconds'] = ((profile_finished - profile_started)
                if profile_started is not None and profile_finished is not None else 0.)
            phase['non_profiled_wall_seconds'] = max(0., phase['wall_seconds'] - phase['profiled_wall_seconds'])
            phase['wall_meaning'] = 'inclusive operation/unwind; profiling stops before budget-exception cleanup'
            profiler.dump_stats(str(output / 'first_step.prof'))
            stats = pstats.Stats(profiler)
            result['profile_top'] = [dict(file=key[0], line=key[1], function=key[2],
                primitive_calls=value[0], calls=value[1], self_seconds=value[2], cumulative_seconds=value[3])
                for key, value in sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:40]]
        result['working_set'] = base._diagnostics(session)
        result['status'] = 'complete'
    except _SampleTerminated as exc:
        result.update(diagnostic_status='terminated', error=str(exc), censored=True)
    except base.BudgetExpired as exc:
        result.update(diagnostic_status='open_timeout', error=str(exc), censored=True)
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        try:
            if session is not None:
                rec.measure('close_without_save', session.close)
        except Exception as exc:
            result.update(status='error', close_error=f'{type(exc).__name__}: {exc}')
        try:
            result['source_unchanged'] = rec.measure('retained_input_verification', lambda: r.file_hash(source)) == authority['database']['sha256']
            if not result['source_unchanged']:
                raise ValueError('retained input changed')
        except Exception as exc:
            result.update(status='error', source_verification_error=f'{type(exc).__name__}: {exc}')
        try:
            r.publish_receipt(output / 'result.json', result)
        finally:
            signal.signal(signal.SIGTERM, previous_term)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = r.load_receipt(args.config)
    check_source(Path.cwd(), config, os.environ['GITHUB_SHA'])
    authority = r.load_receipt(args.root / 'evidence/source-authority.json')
    if (authority['database'] != {k: config['database'][k] for k in ('sha256', 'bytes')}
            or authority['world'] != config['world']
            or any(authority['pin'][k] != config['pin'][k] for k in ('store_identity', 'captured_head'))):
        raise ValueError('sample authority differs from launch')
    result = sample(args.root / 'source/candidate.sqlite', args.root / 'evidence/sample', authority=authority)
    print(json.dumps({k: result.get(k) for k in ('status', 'diagnostic_status', 'acceptance')}))
    return 0 if result['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
