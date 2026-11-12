"""Read-only source/measurement fences for the independent bounded review."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
out = root / 'docs/performance/stage-0-6-current/small-operation-profile/identity-point/review-raw'
area = out.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
runtime = {str(p.relative_to(root)): sha(p) for p in sorted((root / 'simulation/ate_sim').rglob('*.py'))}
base = read(area / 'baseline-raw/report.json')
candidate = read(area / 'candidate-raw/report.json')
profile = read(area / 'candidate-profile/report.json')
expected_changes = {'simulation/ate_sim/persistence_lazy_identity_coordinator.py',
                    'simulation/ate_sim/persistence_history_runtime.py'}
assert {k for k in runtime if runtime[k] != base['runtime_files'][k]} == expected_changes
assert candidate['runtime_files'] == runtime == profile['runtime_files']
for report in (base, candidate, profile):
    assert report['status'] == 'complete' and report['source_preserved'] and report['runtime_preserved']
    assert report['input'] == base['input']
    assert {k: v for k, v in report['restored'].items() if k != 'imports'} == {
        k: v for k, v in base['restored'].items() if k != 'imports'}
    assert all(Path(v).resolve().is_relative_to(root / 'simulation/ate_sim') for v in report['restored']['imports'].values())
qualified = read(root / 'docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json')
fingerprint = read(out / 'runtime-fingerprint.json')
assert all(qualified[k] == v for k, v in fingerprint.items())
assert fingerprint == read(area / 'runtime-fingerprint.json')
dependencies = ['AGENTS.md', 'simulation/tests/test_stage_0_6_proof_placement_reads.py',
    'simulation/tests/test_stage_0_6_proof_native_identity.py',
    'simulation/tests/test_stage_0_6_proof_open.py',
    'docs/superpowers/specs/2026-11-11-proof-placement-read-design.md',
    'docs/superpowers/plans/2026-11-11-proof-placement-read.md',
    'docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py',
    'docs/performance/stage-0-6-current/small-operation-profile/independent-review.md',
    'docs/performance/stage-0-6-current/bounded-genesis/closure.md']
files = [root / p for p in dependencies]
files += sorted(p for p in area.rglob('*') if p.is_file() and p.suffix in ('.json', '.xml', '.log', '.md', '.py') and 'review-raw' not in p.parts)
evidence = dict(status='passed', head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    runtime_files=runtime, dependencies={str(p.relative_to(root)): sha(p) for p in files},
    candidate_runtime_changes=sorted(expected_changes),
    saved=base['restored']['saved'], warm_year=base['restored']['warm_year'], warm_digest=base['restored']['warm_digest'],
    probe_sha256=sha(out / 'test_independent_boundaries.py'), probe_log_sha256=sha(out / 'verification.log'),
    probe_xml_sha256=sha(out / 'verification.xml'), fingerprint=fingerprint,
    raw_seconds={name: {k: report['phases'][k]['wall_seconds'] for k in ('open', 'first_step', 'save', 'warm_step')}
                 for name, report in (('baseline', base), ('candidate', candidate))})
(out / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print('Source fences, qualified software, identical input, saved year2 and fresh continued year3 all verified.')
print(json.dumps({k: runtime[k] for k in sorted(expected_changes)}, indent=2))
