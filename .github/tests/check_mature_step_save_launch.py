"""Exercise the real workflow launcher on a small closed checkpoint.

Only the external checkpoint checksum is substituted. The shell command, runtime
selection, common harness imports, and output-directory lifecycle are unchanged.
"""
from dataclasses import asdict
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile

import yaml

from ate_sim.agency import ActionRecord
from ate_sim.core import World
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from simulation import continuation_receipts as r


def launch_command(workflow):
    workflow = yaml.safe_load(Path(workflow).read_text())
    return next(step['run'] for step in workflow['jobs']['measure']['steps']
                if step.get('id') == 'measure')


def check_launch(workspace, lane, workflow='stage-0-5-mature-step-save.yml'):
    workspace = Path(workspace).resolve()
    candidate = (workspace / 'candidate').resolve()
    runtime = (workspace / lane).resolve()
    command = launch_command(candidate / '.github/workflows' / workflow)
    original_hash = r.load_receipt(candidate / 'simulation/stage_0_5_save1002_preflight.json')['candidate_database']['sha256']
    with tempfile.TemporaryDirectory(prefix=f'ate-launch-{lane}-') as temp:
        root = Path(temp)
        for name in ('baseline', 'candidate'):
            (root / name).symlink_to((workspace / name).resolve(), target_is_directory=True)
        (root / 'source').mkdir()
        (root / 'evidence').mkdir()
        world = World(843000)
        world.agency.actions = [ActionRecord(0, i, 'work', 'wealth', .5) for i in range(16)]
        cold, legacy = root / 'cold.sqlite', root / 'legacy.sqlite'
        source = root / 'source/candidate.sqlite'
        rules = 'mature-launch-smoke'
        write_cold_snapshot(world, cold, rules_id=rules)
        convert_cold_to_lazy(cold, legacy, rules_id=rules, native_graph_buckets=True)
        upgrade_lazy_snapshot(legacy, source, rules_id=rules)
        with open_lazy_world_session(source, rules_id=rules) as session:
            pin = asdict(session.pin)
            source_world = {'seed': session.world.seed, 'year': session.world.year}
        source_hash = r.file_hash(source)
        authority = {'schema': 'ate-performance-source/1',
                     'database': {'sha256': source_hash, 'bytes': source.stat().st_size},
                     'rules_id': rules, 'pin': pin, 'world': source_world,
                     'provenance': {'kind': 'workflow-launch-regression', 'actions': 16}}
        r.publish_receipt(root / 'evidence/source-authority.json', authority)
        env = dict(os.environ, GITHUB_WORKSPACE=str(root), LANE=lane, PYTHONPATH='.:simulation')
        launched = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c',
                                   command.replace(original_hash, source_hash)],
                                  cwd=runtime, env=env, capture_output=True, text=True, timeout=120)
        assert launched.returncode == 0, f'{lane} launch failed:\n{launched.stdout}\n{launched.stderr}'
        result = r.load_receipt(root / 'evidence' / lane / 'result.json')
        assert result['status'] == 'complete', result
        assert set(result['phases']) == {'open', 'first_step', 'save', 'warm_step'}
        assert result['saved']['year'] == source_world['year'] + 1
        assert result['final']['year'] == source_world['year'] + 2
        assert result['saved']['pin'] == result['final']['pin']
        assert Path(result['runtime']['engine_path']).is_relative_to(runtime)
        assert result['common_harness_sha256'] == r.file_hash(
            candidate / 'simulation/profile_stage_0_5_performance.py')
        assert result['source_unchanged'] and r.file_hash(source) == source_hash
        if workflow == 'stage-0-6-current-mature-performance.yml':
            # Derive only the tiny fixture's expected digest in an independent
            # copy. The actual saved file/hash used by the workflow stays intact.
            preview = root/'preview.sqlite'
            shutil.copyfile(root/'evidence'/lane/'operational.sqlite', preview)
            with open_lazy_world_session(preview, rules_id=rules) as session:
                digest = session.world.digest()
            steps = yaml.safe_load((candidate/'.github/workflows'/workflow).read_text())['jobs']['measure']['steps']
            restore = next(step['run'] for step in steps if step.get('id') == 'restore')
            restore = restore.replace("'1002'", repr(str(result['saved']['year'])))
            restore = restore.replace("'127'", repr(str(result['saved']['pin']['captured_head'])))
            restore = restore.replace('2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7', digest)
            gate = next(step['run'] for step in steps if step.get('name') == 'Require completed timing and fresh restore')
            for command in (restore, gate):
                checked = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', command],
                    cwd=runtime, env=env, capture_output=True, text=True, timeout=120)
                assert checked.returncode == 0, f'{checked.stdout}\n{checked.stderr}'
            restored = r.load_receipt(root/'evidence'/lane/'fresh-restore.json')
            assert restored['status'] == 'complete' and restored['actual_digest'] == digest
            assert restored['phases']['fresh_open']['status'] == 'complete'
        print(json.dumps({'lane': lane, 'status': 'complete',
                          'runtime_root': result['runtime']['root']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--lane', choices=('baseline', 'candidate'), required=True)
    parser.add_argument('--workflow', default='stage-0-5-mature-step-save.yml')
    args = parser.parse_args()
    check_launch(args.workspace, args.lane, args.workflow)
