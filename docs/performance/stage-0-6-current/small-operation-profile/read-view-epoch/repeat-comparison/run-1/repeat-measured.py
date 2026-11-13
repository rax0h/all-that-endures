"""Compare two engine trees on one input, with independently retained trials."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[6]
BASELINE = ROOT.parent / 'read-view-baseline'
SOURCE = ROOT.parent / 'small-proof-profile/source.sqlite/candidate.sqlite'
DRIVER = Path('docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py')
INPUT = ROOT / 'docs/performance/stage-0-6-current/small-operation-profile/input.json'
WARM_DIGEST = 'a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3'
SOURCES = {'baseline': BASELINE, 'candidate': ROOT}
EXPECTED_TREES = {'baseline': '41d21d8dfd2eedd44b35c12c894cbb4a59ba6058',
                  'candidate': '4654b0194149f735a15c79507a6e57c88a7acbb2'}
ORDER = [('pair1', 'baseline'), ('pair1', 'candidate'),
         ('pair2', 'candidate'), ('pair2', 'baseline')]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def runtime_files(root):
    return {str(path.relative_to(root)): sha(path)
            for path in sorted((root / 'simulation/ate_sim').rglob('*.py'))}


def machine():
    info = Path('/proc/cpuinfo').read_text()
    model = next((line.split(':', 1)[1].strip() for line in info.splitlines()
                  if line.startswith('model name')), '')
    result = dict(platform=platform.platform(), python=sys.version, cpu=model,
                  affinity=sorted(os.sched_getaffinity(0)))
    for name, path in [('cpu_max', '/sys/fs/cgroup/cpu.max'),
                       ('cpu_stat', '/sys/fs/cgroup/cpu.stat')]:
        p = Path(path)
        result[name] = p.read_text().strip() if p.exists() else None
    return result


def record(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def stop_group(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    info = json.loads(INPUT.read_text())
    if sha(SOURCE) != info['database']['sha256']:
        raise ValueError('source database differs from the recorded input')
    expected = {}
    for label, root in SOURCES.items():
        tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'],
                                       cwd=root, text=True).strip()
        if tree != EXPECTED_TREES[label]:
            raise ValueError(f'{label} runtime tree is not the recorded tree')
        subprocess.run(['git', 'diff', '--quiet', '--', 'simulation/ate_sim'],
                       cwd=root, check=True)
        if not (root / DRIVER).is_file():
            raise FileNotFoundError(f'{label} driver is missing')
        expected[label] = runtime_files(root)
    if args.dry_run:
        print(json.dumps(dict(source=info['database']['sha256'], trees=EXPECTED_TREES,
                              order=ORDER, context=machine())))
        return
    if args.output is None:
        parser.error('--output is required unless --dry-run is used')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(status='running', source=info['database'], trees=EXPECTED_TREES,
                    order=ORDER, wall_limit_seconds=120, context=machine(), trials=[])
    record(out / 'manifest.json', manifest)
    saved = None
    for pair, label in ORDER:
        name = f'{pair}-{label}'
        trial = dict(name=name, status='running', started=datetime.now(timezone.utc).isoformat(),
                     context_before=machine())
        manifest['trials'].append(trial)
        record(out / 'manifest.json', manifest)
        proc = None
        try:
            with (out / f'{name}.log').open('w') as log:
                proc = subprocess.Popen([sys.executable, str(DRIVER), str(SOURCE), str(out / name)],
                                        cwd=SOURCES[label], stdout=log, stderr=subprocess.STDOUT,
                                        start_new_session=True)
                status = proc.wait(timeout=120)
            if status:
                raise RuntimeError(f'driver exited {status}; see its log')
            result = json.loads((out / name / 'report.json').read_text())
            if (result['status'] != 'complete' or not result['source_preserved']
                    or not result['runtime_preserved'] or result['runtime_files'] != expected[label]
                    or result['input'] != info or result['python'] != sys.version
                    or result['restored']['warm_year'] != 3
                    or result['restored']['warm_digest'] != WARM_DIGEST):
                raise ValueError('source, runtime, input or continuation differs')
            if saved is None:
                saved = result['restored']['saved']
            elif result['restored']['saved'] != saved:
                raise ValueError('saved state differs')
            timings = {phase: dict(wall=round(row['wall_seconds'], 6),
                                  cpu=round(row['cpu_seconds'], 6))
                       for phase, row in result['phases'].items()}
        except BaseException as exc:
            stop_group(proc)
            trial.update(status='timeout' if isinstance(exc, subprocess.TimeoutExpired) else 'failed',
                         error=f'{type(exc).__name__}: {exc}', context_after=machine())
            manifest['status'] = 'incomplete'
            record(out / 'manifest.json', manifest)
            raise
        trial.update(status='complete', timings=timings, context_after=machine())
        record(out / 'manifest.json', manifest)
        print(json.dumps(dict(trial=name, timings=timings)), flush=True)
    manifest['status'] = 'complete'
    manifest['saved'] = saved
    manifest['warm_digest'] = WARM_DIGEST
    record(out / 'manifest.json', manifest)


if __name__ == '__main__':
    main()
