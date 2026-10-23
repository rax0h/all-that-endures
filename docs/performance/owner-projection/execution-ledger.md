# SDD ledger — plan: docs/superpowers/plans/2026-10-23-ate-owner-reference-projection.md
Pre-flight: Task1 API/fixtures match Task2 measurements; no shared-interface conflict.
Ruling: five existing physical-owner adapters only — preserve established ownership semantics — complete World topology remains a gate.
Ruling: closed storage-value codec subset — reject hooks/mutable restoration — custom codecs need a separately checked path.
Task 1: complete (commits 5db6178..d8e7ea6, tests: /workspace/scratch/757e611173bc/venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_proof_projection.py → 36 passed in 13.13s)
Final: fixed inherited metadata restoration/hooks, surrogate encoding boundary and delegated budgets —6 regressions RED→GREEN;43 projection/449 affected cases GREEN.
Final: minor (deferred): raw pytest log whitespace is preserved; scoped source/doc checks exclude *.log.
Final: Ruling: complete topology/publication/admission deferred — World inactive until remaining gates — unsafe admission if bypassed.
Final: Ruling: target existence/kind deferred — admission must check targets — dangling-target risk otherwise.
Final: Ruling: ordinary owners/payload retention unsupported — need separate checked paths — no general World support claimed.
Final: Ruling: unselected surplus requires full audit — never admitted — unread corruption not detected.
Final: Ruling: World timing/activation deferred — actual mature timings still required — no target-speed claim.
Task 2: complete (commits d8e7ea6..51b3297, tests: /workspace/scratch/757e611173bc/venv/bin/python -c 'import pathlib,json,xml.etree.ElementTree as E,hashlib,subprocess
p=pathlib.Path('docs/performance/owner-projection');s=list(E.parse(p/'repaired-affected.xml').getroot())[0];assert (s.attrib['tests'],s.attrib['errors'],s.attrib['failures'])==('449','0','0')
j=json.loads((p/'scaling/summary.json').read_text());assert j['status']=='complete' and [r['size'] for r in j['results']]==[1000,10000,100000]
assert j['source']['runtime_tree']==subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()
for key,name in [('driver_sha256','.github/tests/run_proof_projection_scaling.py'),('fixture_sha256','simulation/tests/proof_projection_fixtures.py')]:assert j['source'][key]==hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()
for r in j['results']:
 assert r['exact'] and r['status']=='complete'
 for k in ('current','old_pin','successor'):assert r[k]['selects']['selected_payload']==1 and r[k]['selects']['unrelated_payload']==0 and r[k]['source_payload_checks']==1
c=json.loads((p/'ci-launch.json').read_text());assert c['candidate']=='5da550512eb21bad44ea902612f0b1235fe0ad8b' and c['run_id']==39981711210 and c['runtime_tree']==j['source']['runtime_tree']
print('449 affected tests green; repaired1k/10k/100k exact; runtime/driver/fixture hashes match; successor CI39981711210 launched, acceptance pending')' → 449 affected tests green; repaired1k/10k/100k exact; runtime/driver/fixture hashes match; successor CI39981711210 launched, acceptance pending)
