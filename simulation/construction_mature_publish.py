"""Publish the verified mature candidate; no construction or verification repeats."""
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as old
from simulation import construction_mature_catalog as catalog
from simulation import checkpoint_mature_capture as legacy

ROOT = Path('evidence')
WORKFLOW = '.github/workflows/stage-0-5-mature-publish.yml'
BRANCH = 'sol/stage-0-5-mature-publish'
RUNTIME_SHA, RUNTIME_TREE = catalog.RUNTIME_SHA, catalog.RUNTIME_TREE
CONTEXT, SOURCE_CONFIG = catalog.CONTEXT, catalog.SOURCE_CONFIG
SOURCE_WORKFLOW_SHA, SOURCE_GENERATION = catalog.SOURCE_WORKFLOW_SHA, catalog.SOURCE_GENERATION
CANDIDATE_MANIFEST_SHA = catalog.CANDIDATE_MANIFEST_SHA
CANDIDATE_DATABASE, CANDIDATE_PIN = catalog.CANDIDATE_DATABASE, catalog.CANDIDATE_PIN
STORAGE_RECEIPT_SHA, STORAGE_RECEIPT_BYTES = catalog.STORAGE_RECEIPT_SHA, catalog.STORAGE_RECEIPT_BYTES
CATALOG_RECEIPT_SHA = 'f453b3f861ad868d64a5b18adcfdf6869542ede4bc3cb9b564f03e594ccef3e3'
CATALOG_RECEIPT_BYTES = 753
SOURCE_DATABASE_SHA = 'f03e1755c7e847c861502eedda11c2100bada806259698c531bf8a2a57ae3d03'
SOURCE_MAX_BYTES = 16*1024**3
# One working copy plus a full journal (or upload ZIP), and an 8 GiB margin.
WORK_FREE_BYTES = 2*CANDIDATE_DATABASE['bytes'] + 8*1024**3
START_FREE_BYTES = WORK_FREE_BYTES + CANDIDATE_DATABASE['bytes'] + SOURCE_MAX_BYTES + 4342414844 + 64*1024**2


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('mature publication rerun requires inspection before retry')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA']
            or current.get('path') != WORKFLOW or current.get('head_branch') != BRANCH):
        raise ValueError('mature publication executing workflow mismatch')
    runs = artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}', 'workflow_runs')
    matching = [r['id'] for r in runs if r.get('path') == WORKFLOW
        and r.get('head_sha') == current['head_sha'] and r.get('head_branch') == BRANCH]
    if not matching or min(matching) != run_id:
        raise ValueError('duplicate mature publication run; inspect the earlier run')


def check_helpers():
    catalog.check_helpers()
    for path, expected in {
        'simulation/construction_mature_catalog.py': '441a2faaf8ead96d0662f68653632079031deab717259e3b45a61edd2cdafcde',
        'simulation/persistence_p5_long_validation.py': '7ae326f2b52362493f485fa5102f69d4b939ef4bac6880232662bff461a0b510',
    }.items():
        if old.file_hash(path) != expected:
            raise ValueError('publication helper differs from reviewed candidate')


def download_inputs():
    specs = dict(
        candidate=(38867766111, 12032507300, 'construction-mature-ordered', 'mature-orders',
            '8b8c108f032f1e6d58339cc436310402b40a10ce', catalog.storage.ordering.WORKFLOW,
            'b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4', 4342414844,
            {'candidate.sqlite', 'manifest.json'}),
        storage=(38872643738, 12037828504, 'construction-mature-storage', 'mature-storage',
            '4f1a7d7f0bd6c90704b5370f5e508669afe3b00f', catalog.storage.WORKFLOW,
            '7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4', 554, {'storage.json'}),
        catalog=(38884880079, 12043567528, 'construction-mature-catalog', 'mature-catalog',
            'ee5000a156ebcf1fcec4a893da1a06958feb0ed5', catalog.WORKFLOW,
            '854c941a708c3aa7abd8a85836369c4a209e089496d6b82906afe30f9a9b1bbd', 585, {'catalog.json'}),
        source=(38508408370, 11870590333, 'late-lazy-checkpoint', 'late-lazy',
            legacy.SOURCE_WORKFLOW_SHA, legacy.WORKFLOW, legacy.SOURCE_DIGEST, 1339563957,
            {'checkpoint.json', 'p5-long-lazy.sqlite'}))
    directories, proofs = {}, {}
    for label, row in specs.items():
        directories[label] = ROOT/label
        proof = artifacts.download(directories[label], run_id=row[0], artifact_id=row[1],
            name=row[2], job=row[3], workflow_sha=row[4], workflow_path=row[5],
            expected_digest=row[6], members=row[8])
        if proof['archive_bytes'] != row[7]:
            raise ValueError('publication input archive size mismatch')
        proofs[label] = proof
    return directories, proofs


def run_publish(candidate, storage_receipt, catalog_receipt, source, bundle, *, workflow_sha):
    candidate, source, bundle = Path(candidate), Path(source), Path(bundle)
    storage_receipt, catalog_receipt = Path(storage_receipt), Path(catalog_receipt)
    if bundle.exists(): raise FileExistsError(bundle)
    if old.file_hash(candidate/'manifest.json') != CANDIDATE_MANIFEST_SHA:
        raise ValueError('ordered mature candidate lineage mismatch')
    manifest = old._json(candidate/'manifest.json')
    if (manifest.get('context') != CONTEXT or manifest.get('database') != CANDIDATE_DATABASE
            or manifest.get('pin') != CANDIDATE_PIN or manifest.get('source_generation') != SOURCE_GENERATION):
        raise ValueError('ordered mature candidate lineage mismatch')
    original = json.loads(manifest['source_receipt'])
    if original.get('config') != SOURCE_CONFIG or original.get('workflow_sha') != SOURCE_WORKFLOW_SHA:
        raise ValueError('ordered mature source configuration mismatch')
    for path, size, digest in ((storage_receipt, STORAGE_RECEIPT_BYTES, STORAGE_RECEIPT_SHA),
            (catalog_receipt, CATALOG_RECEIPT_BYTES, CATALOG_RECEIPT_SHA)):
        if path.stat().st_size != size or old.file_hash(path) != digest:
            raise ValueError('retained verification receipt differs from inspected artifact')
    manifest = old.validate(candidate, context=CONTEXT)
    old._require_receipt(storage_receipt, candidate, manifest, 'storage-verified')
    old._require_receipt(catalog_receipt, candidate, manifest, 'catalog-verified', storage_receipt)
    if (source.is_symlink() or set(p.name for p in source.iterdir()) != {'checkpoint.json', 'p5-long-lazy.sqlite'}
            or any(p.is_symlink() or not p.is_file() for p in source.iterdir())):
        raise ValueError('unexpected original source members')
    if (source/'p5-long-lazy.sqlite').stat().st_size > SOURCE_MAX_BYTES:
        raise ValueError('original source size exceeds reserved cap')
    expected = {candidate/'manifest.json': CANDIDATE_MANIFEST_SHA,
        candidate/'candidate.sqlite': CANDIDATE_DATABASE['sha256'], storage_receipt: STORAGE_RECEIPT_SHA,
        catalog_receipt: CATALOG_RECEIPT_SHA, source/'checkpoint.json': manifest['source_receipt_sha256'],
        source/'p5-long-lazy.sqlite': SOURCE_DATABASE_SHA}
    if (any(old.file_hash(path) != digest for path, digest in expected.items())
            or (source/'checkpoint.json').read_text() != manifest['source_receipt']
            or original['database'] != dict(name='p5-long-lazy.sqlite', sha256=SOURCE_DATABASE_SHA)):
        raise ValueError('original source differs from prepared lineage')
    bundle.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mature-publish-', dir=bundle.parent) as directory:
        private = Path(directory)
        # P5 replaces its receipt, so only that file is copied. The lazy source
        # is read-only in this stage and the original retained receipt survives.
        os.link(source/'p5-long-lazy.sqlite', private/'p5-long-lazy.sqlite')
        shutil.copyfile(source/'checkpoint.json', private/'checkpoint.json')
        with redirect_stdout(catalog.storage._DiagnosticOutput(sys.stdout)), legacy.progress():
            result = old.publish_p5(candidate, storage_receipt, catalog_receipt, private,
                context=CONTEXT, workflow_sha=workflow_sha)
        if (result.get('passed') is not False or result.get('checkpoint_stage') != 'complete'
                or any(old.file_hash(path) != digest for path, digest in expected.items())):
            raise ValueError('publication changed retained prerequisite or missed complete boundary')
        receipt = old._json(private/'checkpoint.json')
        database = private/'p5-long-complete.sqlite'
        conversion = dict(source_generation=SOURCE_GENERATION, generation=CANDIDATE_PIN['captured_head'],
            store_identity=CANDIDATE_PIN['store_identity'], source_preserved=True, complete_format=True)
        authority = dict(schema=1, stage='complete', config=dict(SOURCE_CONFIG, product_sha=RUNTIME_SHA),
            workflow_sha=workflow_sha, database=dict(name=database.name, sha256=old.file_hash(database)),
            state=dict(original['state'], conversion_result=conversion), product_sha=RUNTIME_SHA,
            checkpoint_product_sha=SOURCE_CONFIG['product_sha'], source_checkpoint=dict(
                product_sha=SOURCE_CONFIG['product_sha'], workflow_sha=SOURCE_WORKFLOW_SHA, stage='lazy',
                database=original['database'], receipt_sha256=manifest['source_receipt_sha256'],
                prior_source=original.get('source_checkpoint')))
        if receipt != authority:
            raise ValueError('normal published checkpoint authority mismatch')
        # Only closed, durable output is exposed. No second full DB copy or
        # source/receipt overwrite is needed, and no continuation runs here.
        with database.open('rb') as stream: os.fsync(stream.fileno())
        old._write_new(private/'retained-checkpoint.json', receipt)
        bundle.mkdir()
        try:
            os.link(database, bundle/database.name)
            os.link(private/'retained-checkpoint.json', bundle/'checkpoint.json')
            old._fsync_dir(bundle); old._fsync_dir(bundle.parent)
        except BaseException:
            shutil.rmtree(bundle)
            raise
    return receipt


def main():
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:simulation/ate_sim'], text=True).strip()
    if sha != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != RUNTIME_SHA or tree != RUNTIME_TREE:
        raise ValueError('mature publication harness/runtime differs from reviewed candidate')
    check_helpers(); unique_launch()
    if shutil.disk_usage('.').free < START_FREE_BYTES:
        raise ValueError(f'need {START_FREE_BYTES} bytes disk headroom before publication downloads')
    inputs, proofs = download_inputs()
    if shutil.disk_usage('.').free < WORK_FREE_BYTES:
        raise ValueError(f'need {WORK_FREE_BYTES} bytes disk headroom before publication')
    started, cpu = time.monotonic(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_SELF)
    receipt = run_publish(inputs['candidate'], inputs['storage']/'storage.json', inputs['catalog']/'catalog.json',
        inputs['source'], ROOT/'published', workflow_sha=os.environ['GITHUB_SHA'])
    # Diagnostics cannot strand a completed durable normal checkpoint bundle.
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        old._write_new(ROOT/'publish-summary.json', dict(stage='complete-published',
            execution_harness_sha=sha, execution_workflow_sha=os.environ['GITHUB_SHA'], context=CONTEXT,
            runtime_sha=RUNTIME_SHA, inputs=proofs, wall_seconds=time.monotonic()-started,
            cpu_seconds=time.process_time()-cpu, peak_rss_kib=usage.ru_maxrss,
            filesystem_output_blocks=usage.ru_oublock-before.ru_oublock,
            files={p.name: dict(bytes=p.stat().st_size, sha256=old.file_hash(p)) for p in (ROOT/'published').iterdir()},
            receipt=receipt, source_bytes=(inputs['source']/'p5-long-lazy.sqlite').stat().st_size,
            disk_free_bytes=shutil.disk_usage('.').free))
    except Exception:
        pass


if __name__ == '__main__': main()
