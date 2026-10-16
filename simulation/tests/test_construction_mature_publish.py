"""Publish only after exact saved verifier receipts; never repeat their work."""
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from simulation import complete_upgrade_checkpoint as old
from simulation import construction_checkpoint as construction
from simulation.tests.test_construction_checkpoint import inputs, hashes
from simulation.tests.test_checkpointed_upgrade_validation import CONTEXT
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES, sha


def module():
    assert importlib.util.find_spec('simulation.construction_mature_publish'), 'mature publication wiring missing'
    return importlib.import_module('simulation.construction_mature_publish')


def fixture(tmp_path, monkeypatch):
    m = module(); original, _ = inputs(tmp_path)
    source = tmp_path/'source'; source.mkdir()
    shutil.copyfile(original, source/'p5-long-lazy.sqlite')
    config = dict(seed=843000, milestones=[1, 2], bootstrap_year=0, rules_id=RULES,
        product_sha='c'*40, complete_format=True, initialization='founders', simulation_schema='ate-world-p2a/1')
    data = dict(schema=1, stage='lazy', config=config, workflow_sha='d'*40,
        database=dict(name='p5-long-lazy.sqlite', sha256=sha(source/'p5-long-lazy.sqlite')),
        state=dict(controls={'1': {'digest': 'original-control'}, '2': {'digest': 'second-control'}},
                   fixture_marker=['preserve', 17]), source_checkpoint={'stage': 'cold', 'marker': 'prior'})
    old._write_new(source/'checkpoint.json', data)
    prepared, committed, candidate = (tmp_path/n for n in ('prepared', 'committed', 'candidate'))
    construction.prepare(source/'p5-long-lazy.sqlite', source/'checkpoint.json', prepared, rules_id=RULES, context=CONTEXT)
    construction.commit_prepared(prepared, committed, context=CONTEXT)
    manifest = construction.restore_orders(prepared, committed, candidate, context=CONTEXT)
    storage, catalog = tmp_path/'storage.json', tmp_path/'catalog.json'
    old.verify_storage(candidate, storage, context=CONTEXT)
    old.verify_catalog(candidate, storage, catalog, context=CONTEXT)
    for key, value in dict(CONTEXT=CONTEXT, RUNTIME_SHA=CONTEXT['runtime_sha'], SOURCE_CONFIG=config,
        SOURCE_WORKFLOW_SHA='d'*40, SOURCE_DATABASE_SHA=data['database']['sha256'],
        CANDIDATE_MANIFEST_SHA=sha(candidate/'manifest.json'), CANDIDATE_DATABASE=manifest['database'],
        CANDIDATE_PIN=manifest['pin'], SOURCE_GENERATION=manifest['source_generation'],
        STORAGE_RECEIPT_SHA=sha(storage), STORAGE_RECEIPT_BYTES=storage.stat().st_size,
        CATALOG_RECEIPT_SHA=sha(catalog), CATALOG_RECEIPT_BYTES=catalog.stat().st_size).items():
        monkeypatch.setattr(m, key, value)
    return m, candidate, storage, catalog, source


def forbidden(*args, **kwargs): raise AssertionError('publication repeated an earlier or later stage')


def run(m, candidate, storage, catalog, source, output):
    return m.run_publish(candidate, storage, catalog, source, output, workflow_sha='e'*40)


def test_real_publication_preserves_values_aliases_controls_and_all_inputs(tmp_path, monkeypatch):
    from ate_sim.persistence_lazy import open_lazy_world_session
    import persistence_p5_long_validation as p5
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    before = hashes(candidate), hashes(source), sha(storage), sha(catalog)
    for name in ('prepare', 'commit_prepared', 'restore_orders', 'upgrade_lazy_snapshot'):
        monkeypatch.setattr(construction, name, forbidden)
    for name in ('capture', 'verify_storage', 'verify_catalog'):
        monkeypatch.setattr(old, name, forbidden)
    monkeypatch.setattr(p5, 'generate_world', forbidden); monkeypatch.setattr(p5, '_control', forbidden)
    monkeypatch.setattr(p5.Simulation, 'run', forbidden)
    output = tmp_path/'published'; receipt = run(m, candidate, storage, catalog, source, output)
    assert set(hashes(output)) == {'checkpoint.json', 'p5-long-complete.sqlite'}
    assert receipt == old._json(output/'checkpoint.json')
    assert receipt['schema'] == 1 and receipt['stage'] == 'complete'
    assert receipt['workflow_sha'] == 'e'*40 and receipt['config'] == dict(m.SOURCE_CONFIG, product_sha=m.RUNTIME_SHA)
    assert receipt['source_checkpoint']['receipt_sha256'] == sha(source/'checkpoint.json')
    assert receipt['source_checkpoint']['prior_source'] == {'stage': 'cold', 'marker': 'prior'}
    assert receipt['state']['controls'] == old._json(source/'checkpoint.json')['state']['controls']
    assert receipt['state']['fixture_marker'] == ['preserve', 17]
    assert receipt['database'] == dict(name='p5-long-complete.sqlite', sha256=sha(output/'p5-long-complete.sqlite'))
    assert (hashes(candidate), hashes(source), sha(storage), sha(catalog)) == before
    # An ordinary World session writes operational pin metadata on open/close.
    # Inspect a disposable source copy, never the immutable retained input.
    comparison=tmp_path/'source-comparison.sqlite'; shutil.copyfile(source/'p5-long-lazy.sqlite', comparison)
    published_before=hashes(output); published_copy=tmp_path/'published-comparison.sqlite'
    shutil.copyfile(output/'p5-long-complete.sqlite', published_copy)
    with open_lazy_world_session(published_copy, rules_id=RULES) as a, open_lazy_world_session(comparison, rules_id=RULES) as b:
        assert a.detach(materialize_history=True).digest() == b.detach(materialize_history=True).digest()
        assert a.world.skills.skills[1, 'craft'].provenance is a.world.skills.skills[2, 'craft'].provenance
        assert a.world.events[0].data['shared'] is a.world.skills.skills[1, 'craft'].provenance
    assert (hashes(candidate), hashes(source), sha(storage), sha(catalog)) == before
    assert hashes(output) == published_before
    with pytest.raises(FileExistsError): run(m, candidate, storage, catalog, source, output)


@pytest.mark.parametrize('which', ['storage', 'catalog'])
@pytest.mark.parametrize('field', ['stage', 'context', 'database', 'manifest_sha256', 'previous_receipt_sha256'])
def test_refreshed_receipt_hash_cannot_excuse_wrong_original_authority(tmp_path, monkeypatch, which, field):
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    path = storage if which == 'storage' else catalog
    value = old._json(path); value[field] = 'foreign'; path.write_text(json.dumps(value))
    monkeypatch.setattr(m, which.upper()+'_RECEIPT_SHA', sha(path))
    monkeypatch.setattr(m, which.upper()+'_RECEIPT_BYTES', path.stat().st_size)
    monkeypatch.setattr(old, 'publish_p5', forbidden)
    with pytest.raises(ValueError, match='receipt stage/lineage'):
        run(m, candidate, storage, catalog, source, tmp_path/'published')
    assert not (tmp_path/'published').exists()


@pytest.mark.parametrize('which', ['candidate', 'storage', 'catalog', 'source', 'source_database'])
def test_uninspected_or_foreign_input_rejects_before_publication(tmp_path, monkeypatch, which):
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    path = dict(candidate=candidate/'manifest.json', storage=storage, catalog=catalog,
        source=source/'checkpoint.json', source_database=source/'p5-long-lazy.sqlite')[which]
    with path.open('ab') as stream: stream.write(b'foreign')
    monkeypatch.setattr(old, 'publish_p5', forbidden)
    with pytest.raises(ValueError): run(m, candidate, storage, catalog, source, tmp_path/'published')


def test_source_size_cap_rejects_before_publication(tmp_path, monkeypatch):
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(m, 'SOURCE_MAX_BYTES', 1); monkeypatch.setattr(old, 'publish_p5', forbidden)
    with pytest.raises(ValueError, match='source size'):
        run(m, candidate, storage, catalog, source, tmp_path/'published')


@pytest.mark.parametrize('field', ['context', 'pin', 'source_generation', 'source_receipt'])
def test_refreshed_candidate_hash_cannot_excuse_foreign_typed_authority(tmp_path, monkeypatch, field):
    m, candidate, storage, catalog, source=fixture(tmp_path, monkeypatch)
    path=candidate/'manifest.json'; value=old._json(path)
    if field=='source_receipt':
        prior=json.loads(value[field]); prior['config']['seed']+=1
        value[field]=json.dumps(prior)
        import hashlib
        value['source_receipt_sha256']=hashlib.sha256(value[field].encode()).hexdigest()
    else: value[field]='foreign'
    path.write_text(json.dumps(value)); monkeypatch.setattr(m,'CANDIDATE_MANIFEST_SHA',sha(path))
    monkeypatch.setattr(old,'publish_p5',forbidden)
    with pytest.raises(ValueError): run(m,candidate,storage,catalog,source,tmp_path/'published')


@pytest.mark.parametrize('field', ['config', 'state', 'source_checkpoint', 'database'])
def test_foreign_normal_publication_receipt_cannot_advance(tmp_path, monkeypatch, field):
    m, candidate, storage, catalog, source=fixture(tmp_path, monkeypatch)
    original=old.publish_p5
    def changed(*args, **kwargs):
        result=original(*args, **kwargs); path=Path(args[3])/'checkpoint.json'
        value=old._json(path); value[field]='foreign'; path.write_text(json.dumps(value)); return result
    monkeypatch.setattr(old,'publish_p5',changed)
    with pytest.raises(ValueError,match='published checkpoint authority'):
        run(m,candidate,storage,catalog,source,tmp_path/'published')
    assert not (tmp_path/'published').exists()


@pytest.mark.parametrize('fault', ['interrupted', 'receipt', 'publication_race'])
def test_failed_publication_preserves_inputs_and_emits_no_bundle(tmp_path, monkeypatch, fault):
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    before = hashes(candidate), hashes(source), sha(storage), sha(catalog)
    if fault == 'interrupted':
        def fail(*a, **k): raise RuntimeError('interrupted')
        monkeypatch.setattr(old, 'publish_p5', fail)
    elif fault == 'receipt':
        def fail(*a, **k): raise OSError('receipt')
        monkeypatch.setattr(old, '_write_new', fail)
    else:
        original = old._publish_private_cold_file
        def race(private, destination):
            Path(destination).write_bytes(b'other writer'); original(private, destination)
        monkeypatch.setattr(old, '_publish_private_cold_file', race)
    with pytest.raises((RuntimeError, OSError)): run(m, candidate, storage, catalog, source, tmp_path/'published')
    assert not (tmp_path/'published').exists()
    assert (hashes(candidate), hashes(source), sha(storage), sha(catalog)) == before


def test_changed_prerequisite_during_publication_cannot_advance(tmp_path, monkeypatch):
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    original = old.publish_p5
    def changed(*args, **kwargs):
        result = original(*args, **kwargs); storage.write_text('{}'); return result
    monkeypatch.setattr(old, 'publish_p5', changed)
    with pytest.raises(ValueError, match='retained prerequisite'):
        run(m, candidate, storage, catalog, source, tmp_path/'published')
    assert not (tmp_path/'published').exists()


def test_broken_diagnostic_stdout_does_not_strand_published_bundle(tmp_path, monkeypatch):
    m, candidate, storage, catalog, source = fixture(tmp_path, monkeypatch)
    class Broken:
        def write(self, value): raise OSError('stdout diagnostic')
        def flush(self): raise OSError('stdout diagnostic')
    with monkeypatch.context() as patch:
        patch.setattr(m.sys, 'stdout', Broken())
        receipt = run(m, candidate, storage, catalog, source, tmp_path/'published')
    assert receipt['stage'] == 'complete'


@pytest.mark.parametrize('condition', ['first', 'duplicate', 'rerun', 'workflow', 'branch', 'head'])
def test_publish_launch_guard(monkeypatch, condition):
    m = module(); monkeypatch.setenv('GITHUB_RUN_ID', '23'); monkeypatch.setenv('GITHUB_SHA', 'a'*40)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2' if condition == 'rerun' else '1')
    current = dict(id=23, head_sha='a'*40, path=m.WORKFLOW, head_branch=m.BRANCH)
    if condition == 'workflow': current['path'] = 'foreign.yml'
    if condition == 'branch': current['head_branch'] = 'foreign'
    if condition == 'head': current['head_sha'] = 'b'*40
    rows = [current]
    if condition == 'duplicate': rows.append(dict(current, id=22))
    monkeypatch.setattr(m.artifacts, '_api', lambda *a: current)
    monkeypatch.setattr(m.artifacts, '_pages', lambda *a: rows)
    if condition == 'first': m.unique_launch()
    else:
        with pytest.raises(ValueError): m.unique_launch()


@pytest.mark.parametrize('wrong_size', [False, True])
def test_publication_downloads_pin_exact_all_four_producers(tmp_path, monkeypatch, wrong_size):
    m = module(); monkeypatch.setattr(m, 'ROOT', tmp_path)
    expected = dict(candidate=(38867766111, 12032507300, 'construction-mature-ordered', 'mature-orders',
        '8b8c108f032f1e6d58339cc436310402b40a10ce', '.github/workflows/stage-0-5-mature-orders.yml',
        'b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4', 4342414844, {'candidate.sqlite', 'manifest.json'}),
        storage=(38872643738, 12037828504, 'construction-mature-storage', 'mature-storage',
        '4f1a7d7f0bd6c90704b5370f5e508669afe3b00f', '.github/workflows/stage-0-5-mature-storage.yml',
        '7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4', 554, {'storage.json'}),
        catalog=(38884880079, 12043567528, 'construction-mature-catalog', 'mature-catalog',
        'ee5000a156ebcf1fcec4a893da1a06958feb0ed5', '.github/workflows/stage-0-5-mature-catalog.yml',
        '854c941a708c3aa7abd8a85836369c4a209e089496d6b82906afe30f9a9b1bbd', 585, {'catalog.json'}),
        source=(38508408370, 11870590333, 'late-lazy-checkpoint', 'late-lazy',
        '124c3215468a60862b7848086f00a8e768a6ed66', '.github/workflows/stage-0-5-final-release-validation.yml',
        '409cf0230ff1606b7eddd587a69c22076c11447eb6497e642e584c4fd3b74ef9', 1339563957, {'checkpoint.json', 'p5-long-lazy.sqlite'}))
    seen=[]
    def download(destination, **kwargs):
        label=Path(destination).name; row=expected[label]; seen.append(label)
        assert kwargs == dict(run_id=row[0], artifact_id=row[1], name=row[2], job=row[3],
            workflow_sha=row[4], workflow_path=row[5], expected_digest=row[6], members=row[8])
        return dict(archive_bytes=row[7]-int(wrong_size), artifact_id=row[1])
    monkeypatch.setattr(m.artifacts, 'download', download)
    if wrong_size:
        with pytest.raises(ValueError, match='archive size'): m.download_inputs()
    else:
        directories, proofs=m.download_inputs()
        assert set(seen)==set(directories)==set(proofs)==set(expected)


def main_environment(m, monkeypatch):
    monkeypatch.setenv('HARNESS_SHA', 'd'*40); monkeypatch.setenv('RUNTIME_SHA', m.RUNTIME_SHA)
    monkeypatch.setenv('GITHUB_SHA', 'e'*40)
    monkeypatch.setattr(m.subprocess, 'check_output', lambda args, **kw: 'd'*40 if args[-1]=='HEAD' else m.RUNTIME_TREE)
    monkeypatch.setattr(m.resource, 'setrlimit', lambda *a: None)
    monkeypatch.setattr(m, 'check_helpers', lambda: None); monkeypatch.setattr(m, 'unique_launch', lambda: None)


@pytest.mark.parametrize('where', ['before', 'after'])
def test_publication_headroom_checked_before_mutation(tmp_path, monkeypatch, where):
    m=module(); monkeypatch.setattr(m, 'ROOT', tmp_path/'evidence'); main_environment(m, monkeypatch)
    assert m.WORK_FREE_BYTES >= 2*m.CANDIDATE_DATABASE['bytes']+8*1024**3
    assert m.START_FREE_BYTES >= m.WORK_FREE_BYTES+m.CANDIDATE_DATABASE['bytes']+m.SOURCE_MAX_BYTES+4342414844
    values=iter([m.START_FREE_BYTES-int(where=='before'), m.WORK_FREE_BYTES-1])
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=next(values)))
    def download():
        if where=='before': pytest.fail('downloads before headroom')
        return {n:tmp_path/n for n in ('candidate', 'source', 'storage', 'catalog')}, {}
    monkeypatch.setattr(m, 'download_inputs', download); monkeypatch.setattr(m, 'run_publish', forbidden)
    with pytest.raises(ValueError, match='disk headroom'): m.main()


def test_summary_failure_cannot_suppress_completed_publication(tmp_path, monkeypatch):
    m, candidate, storage, catalog, source=fixture(tmp_path, monkeypatch)
    for path in (storage, catalog):
        directory=tmp_path/(path.stem+'-bundle'); directory.mkdir(); shutil.copyfile(path, directory/path.name)
    root=tmp_path/'evidence'; monkeypatch.setattr(m, 'ROOT', root); main_environment(m, monkeypatch)
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda *a: SimpleNamespace(free=m.START_FREE_BYTES))
    monkeypatch.setattr(m, 'download_inputs', lambda: (dict(candidate=candidate,source=source,
        storage=tmp_path/'storage-bundle',catalog=tmp_path/'catalog-bundle'),{}))
    original=old._write_new
    def failed(path, value):
        if Path(path).name=='publish-summary.json': raise OSError('summary diagnostic')
        return original(path,value)
    monkeypatch.setattr(old,'_write_new',failed); m.main()
    assert old._json(root/'published/checkpoint.json')['stage']=='complete'


@pytest.mark.parametrize('status', [0, 7, 124])
def test_workflow_is_publication_only_with_mandatory_upload(status):
    import subprocess,yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-publish.yml'
    assert path.exists(), 'mature publication workflow missing'
    workflow=yaml.safe_load(path.read_text()); assert set(workflow['jobs'])=={'mature-publish'}
    assert workflow['concurrency']['cancel-in-progress'] is False
    job=workflow['jobs']['mature-publish']; assert job['timeout-minutes']==360
    script=next(s['run'] for s in job['steps'] if s.get('name')=='Publish verified mature candidate')
    assert '300m python -m simulation.construction_mature_publish' in script
    for earlier in ('construction_mature_storage', 'construction_mature_catalog', 'construction_mature_orders'):
        assert earlier not in script
    script=script.replace('timeout --signal=TERM --kill-after=30s 300m python -m simulation.construction_mature_publish',f"bash -c 'exit {status}'")
    script=script.replace('tee evidence/publish.log',"bash -c 'cat >/dev/null; exit 42'")
    assert subprocess.run(['bash','-e','-o','pipefail','-c',script],capture_output=True).returncode==status
    diagnostic=next(s for s in job['steps'] if s.get('name')=='Retain diagnostics')
    assert diagnostic['if']=='always()' and diagnostic['continue-on-error'] is True
    upload=next(s for s in job['steps'] if s.get('name')=='Retain published checkpoint')
    assert 'if' not in upload and upload['with']['path']=='evidence/published'
    assert upload['with']['name']=='construction-mature-published' and upload['with']['if-no-files-found']=='error'


def test_runner_cleanup_reclaims_large_stage_caches_but_preserves_python(tmp_path):
    import subprocess,yaml
    path=Path(__file__).resolve().parents[2]/'.github/workflows/stage-0-5-mature-publish.yml'
    workflow=yaml.safe_load(path.read_text())
    script=next(s['run'] for s in workflow['jobs']['mature-publish']['steps']
        if s.get('name')=='Reserve disk on this disposable runner')
    # Execute the actual cleanup against a disposable fixture, never host paths.
    locations={'/usr/share/dotnet':'dotnet', '/usr/local/lib/android':'android', '/opt/ghc':'ghc',
        '/usr/share/swift':'swift', '/usr/local/.ghcup':'ghcup', '/usr/local/share/powershell':'powershell',
        '/opt/hostedtoolcache':'toolcache'}
    for original,label in locations.items():
        directory=tmp_path/label; directory.mkdir()
        script=script.replace(original,str(directory))
    cache=tmp_path/'toolcache'
    for name in ('Python','CodeQL','node'):
        (cache/name).mkdir(); (cache/name/'runtime').write_bytes(name.encode())
    actions=tmp_path/'actions-runtime'; actions.write_bytes(b'Actions bundled Node remains outside toolcache')
    script=script.replace('sudo ','')
    docker="docker() { test \"$*\" = 'image prune -af'; touch docker-pruned; }\n"
    subprocess.run(['bash','-e','-o','pipefail','-c',docker+script],cwd=tmp_path,check=True,capture_output=True)
    assert {p.name for p in cache.iterdir()}=={'Python'}
    assert (cache/'Python/runtime').read_bytes()==b'Python'
    assert actions.read_bytes()==b'Actions bundled Node remains outside toolcache'
    assert all(not (tmp_path/label).exists() for label in locations.values() if label!='toolcache')
    assert (tmp_path/'docker-pruned').exists()
