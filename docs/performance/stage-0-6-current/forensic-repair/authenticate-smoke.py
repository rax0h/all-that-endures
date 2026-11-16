"""Recheck recorded hosted smoke evidence; never simulate or substitute local runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from simulation import stage_0_6_genesis_checkpoint as c
from simulation import stage_0_6_genesis_resume as resume
from simulation import stage_0_6_genesis_transport as transport
from simulation import stage_0_6_preserved_transport as preserved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--archives', type=Path, required=True)
    parser.add_argument('--live-preflight', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    metadata = json.loads(args.metadata.read_text())
    run, jobs = metadata['run'], metadata['jobs']['jobs']
    assert run['id'] == 43778758497
    assert run['head_sha'] == '935df38b5f9267c25fddbea8bda0e3f50121b49f'
    assert run['status'] == 'completed' and run['conclusion'] == 'success'
    assert all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs)
    artifacts = {a['id']: a for a in metadata['artifacts']['artifacts']}
    receipts, references, archives = {}, {}, []
    for aid, artifact in artifacts.items():
        name = artifact['name']
        if name.startswith(('checkpoint-', 'database-')):
            kind, mode, stage, head, attempt = name.split('-')
            ref = transport.authenticate(artifact, run, jobs, name=name, job=c.JOB[stage],
                                         head=head, run_id=run['id'])
            references[aid] = ref
        archive = args.archives / f'{aid}.zip'
        if not archive.is_file():
            assert name.startswith('database-'), name
            continue
        assert archive.stat().st_size == artifact['size_in_bytes']
        assert c.file_hash(archive) == artifact['digest'][7:]
        archives.append(dict(id=aid, name=name, bytes=archive.stat().st_size,
                             sha256=c.file_hash(archive)))
        if name.startswith('checkpoint-'):
            with zipfile.ZipFile(archive) as z:
                assert z.namelist() == ['checkpoint.json']
                value = json.loads(z.read('checkpoint.json'))
            c.validate(value, require_remote=True)
            resume.match_receipt_reference(value, references[aid], mode='smoke', stage=stage)
            receipts[stage] = value
    assert set(receipts) == set(c.ORDER)
    current_runtime, blobs = resume.fence(root)
    resume.compatible(root, run['head_sha'])
    context = receipts['fresh_restore']['context']
    assert context['runtime_tree'] == current_runtime == resume.RUNTIME
    assert context['critical_blobs'] == blobs
    resume.check_software(context['execution_runtime'])
    assert context['mode'] == 'smoke' and context['source']['year'] == 1
    for index, stage in enumerate(c.ORDER):
        value = receipts[stage]
        assert value['context'] == context
        if index:
            assert value['parent']['receipt'] == receipts[c.ORDER[index-1]]
        assert value['data_ref'] == references[value['data_ref']['artifact_id']]
    acceptance = resume.evaluate_acceptance(receipts['fresh_restore'], 'smoke')
    assert acceptance['acceptance'] == 'smoke-functional-only'
    for stage in ('catalog', 'rebase', 'measure'):
        value = receipts[stage]
        archive = args.archives / f"{value['data_ref']['artifact_id']}.zip"
        with zipfile.ZipFile(archive) as z:
            assert z.namelist() == ['candidate.sqlite']
            assert z.getinfo('candidate.sqlite').file_size == value['database']['bytes']
            with z.open('candidate.sqlite') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == value['database']['sha256']
    recovery_artifact = next(a for a in artifacts.values() if a['name'].startswith('resume-evidence-smoke-rebase-'))
    with zipfile.ZipFile(args.archives / f"{recovery_artifact['id']}.zip") as z:
        recovery = json.loads(z.read('recovery-work/recovery.json'))
    assert recovery['status'] == 'passed' and recovery['worker_exit'] == 77
    assert recovery['interrupted_stage'] == 'rebase' and recovery['retained_stage'] == 'catalog'
    assert recovery['receipt_sha256'] == c.receipt_hash(receipts['catalog'])
    assert recovery['database_sha256'] == receipts['catalog']['database']['sha256']
    assert receipts['rebase']['parent']['receipt'] == receipts['catalog']
    gate_artifact = next(a for a in artifacts.values() if a['name'].startswith('resume-evidence-gate-'))
    with zipfile.ZipFile(args.archives / f"{gate_artifact['id']}.zip") as z:
        runtime = json.loads(z.read('resume-work/runtime.json'))
        green = json.loads(z.read('resume-work/green-reuse.json'))
        suites = ET.fromstring(z.read('resume-tests/harness.xml'))
    assert c.receipt_hash(runtime) == context['execution_runtime']['signature']
    assert green['green_run'] == resume.GREEN_RUN and green['runtime_tree'] == current_runtime
    counts = {key: sum(int(s.get(key, 0)) for s in suites.iter('testsuite'))
              for key in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['failures'] == counts['errors'] == 0
    live = json.loads(args.live_preflight.read_text())
    assert live['release']['id'] == 446184821 and live['release']['draft'] is True
    assert live['release']['tag_name'] == 'ate-stage-0-6-fixtures-2026-11'
    assets = {a['id']: a for a in live['assets']}
    pins = json.loads((root/'simulation/stage_0_6_preserved_fixtures.json').read_text())
    for key, entry in pins['fixtures'].items():
        preserved.manifest(key)
        for item in [entry['asset'], *entry['manifest']['parts']]:
            actual = assets[item['id']]
            assert actual['state'] == 'uploaded' and actual['name'] == item['name']
            assert actual['size'] == item['bytes'] and actual['digest'] == 'sha256:' + item['sha256']
    qualified = {a['id']: a for a in live['qualified_artifacts']['artifacts']}
    for aid, name, digest in resume.GREEN_ARTIFACTS.values():
        a = qualified[aid]
        assert a['name'] == name and a['expired'] is False and a['digest'] == 'sha256:' + digest
    summary = dict(schema='ate-authenticated-smoke-launch-preflight/1',
                   scope='recorded hosted evidence; no local hosted-runtime impersonation',
                   producer_run=run['id'], producer_head=run['head_sha'],
                   checked_head=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                   engine=current_runtime, critical_paths=len(blobs),
                   hosted_runtime=context['execution_runtime'], harness=counts,
                   acceptance=acceptance, fresh_restored=receipts['fresh_restore']['metrics']['restored'],
                   recovery=recovery, authenticated_archives=archives,
                   preservation_live_checked_at=live['observed_at'],
                   original_mature=preserved.manifest('mature-year1001')['original'],
                   mature_status='unmeasured')
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key:summary[key] for key in ('producer_run','engine','critical_paths','harness','acceptance','fresh_restored','mature_status')}, indent=2))


if __name__ == '__main__':
    main()
