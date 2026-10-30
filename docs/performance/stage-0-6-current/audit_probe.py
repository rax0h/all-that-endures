"""Opt-in, bounded Stage 0.6 audit call attribution for *selected* pytest cases.

Usage (from repository root, no workflow dispatch):
    timeout 10m python docs/performance/stage-0-6-current/audit_probe.py \
      --output /tmp/ate-audit-probe.json \
      simulation/tests/test_stage_0_5_proof_world_session.py::test_native_noop_preserves_manifest_and_generation \
      simulation/tests/test_stage_0_5_proof_world_value.py::test_actual_native_scalar_save_does_not_call_full_audit \
      simulation/tests/test_stage_0_5_proof_world_tail.py::test_new_history_backing_retains_checked_structural_fallback

This profiler adds overhead; durations are *attribution*, not acceptance benchmarks.
No persistent data is changed by the probe itself. Tests use their own fixtures.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import sys
import time


# Match by code filename and function name to survive test-local monkeypatches.
TARGETS = {
    ('persistence_lazy.py', 'save'): 'save',
    ('persistence_proof_world_session.py', 'execute'): 'proof.execute',
    ('persistence_proof_world_session.py', 'commit'): 'proof.commit',
    ('persistence_proof_world_session.py', '_audit'): 'authority.audit',
    ('persistence_proof_world_session.py', '_audit_inner'): 'authority.audit_inner',
    ('persistence_proof_world_session.py', '_settle'): 'authority.settle',
    ('persistence_proof_manifest_publish.py', '_stage'): 'manifest.stage',
    ('persistence_proof_manifest_publish.py', 'commit_world_manifest'): 'manifest.commit_world',
    ('persistence_proof_world.py', '_audit_world'): 'world.audit',
    ('persistence_lazy_store.py', 'verify_all'): 'store.verify_all',
    ('persistence_catalog_copy.py', '_verify_catalog'): 'catalog.verify',
    ('persistence_lazy_store.py', 'commit'): 'store.commit',
}


class CallAttribution:
    def __init__(self):
        self.stack = []
        self.save_ids = []
        self.save_count = 0
        self.manifest_outcomes = []
        self.audit_epochs = defaultdict(list)
        self.execution_epoch_checks = []
        self.rows = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0]))

    def __call__(self, frame, event, arg):
        if event == 'call':
            name = TARGETS.get((Path(frame.f_code.co_filename).name, frame.f_code.co_name))
            if name is None:
                return
            if name == 'save':
                self.save_count += 1
                self.save_ids.append(self.save_count)
            bucket = f'save_{self.save_ids[-1]}' if self.save_ids else 'outside_save'
            self.stack.append([frame, name, bucket, time.perf_counter_ns(), time.process_time_ns(), 0, 0])
        elif event == 'return' and self.stack and self.stack[-1][0] is frame:
            tracked = self.stack.pop()
            _, name, bucket, start_wall, start_cpu, child_wall, child_cpu = tracked
            wall = time.perf_counter_ns() - start_wall
            cpu = time.process_time_ns() - start_cpu
            row = self.rows[bucket][name]
            row[0] += 1
            row[1] += wall
            row[2] += max(0, wall - child_wall)
            row[3] += cpu
            row[4] += max(0, cpu - child_cpu)
            if self.stack:
                self.stack[-1][5] += wall
                self.stack[-1][6] += cpu
            # Compare verified epochs only; never export connection/codec objects.
            # The first authority audit in a fallback save occurs in commit();
            # execute() may invoke a second audit after observing the epoch.
            if name == 'authority.audit' and type(arg) is tuple:
                self.audit_epochs[bucket].append(arg)
            if name == 'proof.execute':
                observed = frame.f_locals.get('observed')
                verified = frame.f_locals.get('verified')
                if type(observed) is tuple and type(verified) is tuple:
                    epochs = self.audit_epochs.get(bucket, ())
                    self.execution_epoch_checks.append({
                        'bucket': bucket,
                        'can_settle': getattr(frame.f_locals.get('self'), '_can_settle', None),
                        'authority_audit_count': len(epochs),
                        'first_audit_equals_observed': epochs[0] == observed if epochs else None,
                        'first_audit_equals_final': epochs[0] == verified if epochs else None,
                        'last_audit_equals_observed': epochs[-1] == observed if epochs else None,
                        'observed_equals_final': observed == verified,
                    })
            if name == 'manifest.commit_world' and arg is not None:
                reaudited = getattr(arg, 'reaudited', None)
                outcome = getattr(getattr(arg, 'commit', None), 'outcome', None)
                if type(reaudited) is bool and type(outcome) is str:
                    self.manifest_outcomes.append({'bucket': bucket, 'reaudited': reaudited,
                                                   'commit_outcome': outcome})
            if name == 'save':
                self.save_ids.pop()

    def snapshot(self):
        return {
            'save_calls': self.save_count,
            'manifest_outcomes': self.manifest_outcomes,
            'execution_epoch_checks': self.execution_epoch_checks,
            'buckets': {
                bucket: {
                    name: dict(zip(('calls', 'inclusive_wall_s', 'exclusive_wall_s',
                                    'inclusive_cpu_s', 'exclusive_cpu_s'),
                                   (v[0], *(round(n / 1e9, 6) for n in v[1:]))))
                    for name, v in sorted(rows.items())
                }
                for bucket, rows in sorted(self.rows.items())
            },
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('selectors', nargs='+', help='Explicit test node IDs only; no whole-suite runs')
    args = parser.parse_args(argv)
    if len(args.selectors) > 8 or any(not x.startswith('simulation/tests/') or '::test_' not in x for x in args.selectors):
        parser.error('specify 1..8 explicit simulation/tests/...::test_... selectors (no whole-suite runs)')
    import pytest

    class Plugin:
        def __init__(self):
            self.tests = []

        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_call(self, item):
            previous = sys.getprofile()
            if previous is not None:
                raise RuntimeError('refusing to replace an existing process profiler')
            tracker = CallAttribution()
            sys.setprofile(tracker)
            try:
                yield
            finally:
                sys.setprofile(previous)
                self.tests.append({'nodeid': item.nodeid, **tracker.snapshot()})

    plugin = Plugin()
    started = time.perf_counter()
    exit_code = int(pytest.main(['-q', '--disable-warnings', *args.selectors], plugins=[plugin]))
    try:
        sha = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True,
                             check=False, timeout=5).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        sha = None
    report = {
        'schema': 'ate-stage06-audit-probe/1', 'source_sha': sha,
        'selectors': args.selectors, 'pytest_exit_code': exit_code,
        'instrumented_wall_seconds': round(time.perf_counter() - started, 6),
        'warning': 'Python call profiling changes runtime; do not treat as mature-world latency',
        'tests': plugin.tests,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f'Audit attribution written to {path} (pytest exit {exit_code})')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
