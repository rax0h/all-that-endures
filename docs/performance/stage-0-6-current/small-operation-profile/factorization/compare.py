"""Sequential small-input latency/work comparison; no mature acceptance claim."""
import argparse
import cProfile
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pstats
import shutil
import subprocess
import sys

from ate_sim.engine import Simulation
from ate_sim.persistence_proof_world_session import open_proof_world_session
from simulation import stage_0_6_genesis_checkpoint as c
from simulation.stage_0_6_genesis_stages import Recorder


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_files(root):
    return {str(p.relative_to(root)): sha(p)
            for p in sorted((root / 'simulation/ate_sim').rglob('*.py'))}


def loaded_paths(root):
    result = {}
    for name, module in list(sys.modules.items()):
        if name == 'ate_sim' or name.startswith('ate_sim.'):
            path = Path(module.__file__).resolve()
            if not path.is_relative_to(root / 'simulation/ate_sim'):
                raise ValueError('runtime import escaped selected source: ' + name)
            result[name] = str(path.relative_to(root))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    info = json.loads((Path(__file__).parent.parent / 'input.json').read_text())
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    if source.is_relative_to(out):
        raise ValueError('output cannot contain immutable source')
    c.verify_database(source, info['database'])
    fence = runtime_files(root)
    report = dict(kind='instrumented-small-diagnostic' if args.profile else 'raw-small-diagnostic',
                  head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  runtime_files=fence, python=sys.version, input=info, phases={}, work={})
    (out / 'source-before.json').write_text(json.dumps(report, indent=2) + '\n')
    working = out / 'working.sqlite'
    shutil.copyfile(source, working)
    rec = Recorder(out / 'phases', dict(open=60, first_step=180, save=120,
                                      warm_step=180, fresh_verify=120))
    session = None

    def phase(name, operation):
        profiler = cProfile.Profile() if args.profile else None
        before = asdict(session.store.diagnostics()) if session else {}
        if profiler:
            profiler.enable()
        try:
            return rec.measure(name, operation)
        finally:
            if profiler:
                profiler.disable()
                stats = pstats.Stats(profiler)
                rows = [dict(file=k[0], line=k[1], function=k[2], primitive_calls=v[0],
                             calls=v[1], own_seconds=v[2], cumulative_seconds=v[3])
                        for k, v in stats.stats.items()]
                (out / (name + '-calls.json')).write_text(json.dumps(rows, indent=2) + '\n')
                report['work'][name] = dict(before=before,
                    after=asdict(session.store.diagnostics()) if session else {},
                    total_calls=sum(v[1] for v in stats.stats.values()))

    try:
        session = phase('open', lambda: open_proof_world_session(working,
            rules_id=info['rules_id'], expected_commitment=bytes.fromhex(info['proof_commitment'])))
        rec.store = session.store
        assert session.world.year == 1 and session.proof_manifest[0].generation == 0
        phase('first_step', lambda: Simulation(session.world).run(1))
        phase('save', session.save)
        commitment = session.proof_manifest[1].hex()
        assert session.world.year == 2 and session.proof_manifest[0].generation == 1
        phase('warm_step', lambda: Simulation(session.world).run(1))
        warm_digest = session.world.digest()
        assert session.world.year == 3
        session.close()
        session = None
        rec.store = None
        fresh_code = '''
import json,sys
from pathlib import Path
from ate_sim.engine import Simulation
from ate_sim.persistence_proof_world_session import open_proof_world_session
with open_proof_world_session(sys.argv[1],rules_id=sys.argv[2],expected_commitment=bytes.fromhex(sys.argv[3])) as s:
 saved=dict(year=s.world.year,seed=s.world.seed,generation=s.proof_manifest[0].generation,digest=s.world.digest())
 Simulation(s.world).run(1)
 print(json.dumps(dict(saved=saved,warm_digest=s.world.digest(),warm_year=s.world.year,imports={n:str(Path(m.__file__).resolve()) for n,m in list(sys.modules.items()) if n=='ate_sim' or n.startswith('ate_sim.')})))
'''
        def fresh():
            completed = subprocess.run([sys.executable, '-c', fresh_code, str(working),
                info['rules_id'], commitment], check=True, capture_output=True, text=True, timeout=120)
            return json.loads(completed.stdout)
        restored = rec.measure('fresh_verify', fresh)
        assert restored['saved'] == dict(year=2, seed=843000, generation=1,
                                         digest=info['expected_saved_digest'])
        assert restored['warm_year'] == 3 and restored['warm_digest'] == warm_digest
        for name, path in restored['imports'].items():
            assert Path(path).is_relative_to(root / 'simulation/ate_sim'), name
        report.update(status='complete', phases=rec.phases, restored=restored,
                      saved_commitment=commitment, loaded_paths=loaded_paths(root))
        print(json.dumps({name: value['wall_seconds'] for name, value in rec.phases.items()}), flush=True)
    finally:
        if session is not None:
            session.close()
        c.verify_database(source, info['database'])
        assert runtime_files(root) == fence, 'working runtime changed during diagnostic'
        report.update(source_preserved=True, runtime_preserved=True)
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        working.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
