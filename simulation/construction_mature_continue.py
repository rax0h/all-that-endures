"""Continue the exact published mature checkpoint, without recreating controls."""
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

import persistence_p5_long_validation as p5
from simulation import checkpoint_artifacts as artifacts
from simulation import complete_upgrade_checkpoint as old
from simulation import construction_mature_publish as publish

ROOT = Path('evidence')
WORKFLOW = '.github/workflows/stage-0-5-mature-continue.yml'
BRANCH = 'sol/stage-0-5-mature-continue'
RUNTIME_SHA, RUNTIME_TREE = publish.RUNTIME_SHA, publish.RUNTIME_TREE
# Retained inputs keep their original producer; only continuation executes the
# reviewed save repair. P5 already supports explicit checkpoint provenance.
EXECUTION_RUNTIME_SHA = 'f312cc288ec5f583d34e16f63aa58d3093ca6b7c'
EXECUTION_RUNTIME_TREE = 'e2142c50e54ece5495312860094052e09338497a'
CONTEXT, SOURCE_CONFIG = publish.CONTEXT, publish.SOURCE_CONFIG
CANDIDATE_PIN, SOURCE_GENERATION = publish.CANDIDATE_PIN, publish.SOURCE_GENERATION
CANDIDATE_DATABASE, CANDIDATE_MANIFEST_SHA = publish.CANDIDATE_DATABASE, publish.CANDIDATE_MANIFEST_SHA
STORAGE_RECEIPT_SHA, STORAGE_RECEIPT_BYTES = publish.STORAGE_RECEIPT_SHA, publish.STORAGE_RECEIPT_BYTES
CATALOG_RECEIPT_SHA, CATALOG_RECEIPT_BYTES = publish.CATALOG_RECEIPT_SHA, publish.CATALOG_RECEIPT_BYTES
PUBLISHED_WORKFLOW_SHA = '5fe99ca2faf0c0668ff73032fe9cc33fd1d6e9a9'
PUBLISHED_HARNESS_SHA = '73370b253f0cb14550f6f43e8a20e4b577246c31'
PUBLISHED_FILES = {
    'checkpoint.json': dict(bytes=134251, sha256='082081583f68c8e032669df7114e5a75950ed6e1a94d7000b653fe37d6f39f53'),
    'p5-long-complete.sqlite': dict(bytes=29601284096, sha256='0d884e52a012ab55325c7111bfc1d054fa7c27aaf0947cf9ab8de4423c213e1c')}
SUMMARY_SHA = '8cd587c1e86035369b274d5f387458f9b02f3c75cb7d38f24a4e3d815667ea7a'
SUMMARY_BYTES = 147292
SOURCE_CHECKPOINT = dict(product_sha=SOURCE_CONFIG['product_sha'], workflow_sha=publish.SOURCE_WORKFLOW_SHA,
    stage='lazy', database=dict(name='p5-long-lazy.sqlite', sha256=publish.SOURCE_DATABASE_SHA),
    receipt_sha256='598b4875d7dad6b63990f6901e57c22708b19edf9cfa2c41c2790c9b3d345084', prior_source=None)
PUBLISH_INPUTS = {
    'candidate': dict(artifact_id=12032507300,run_id=38867766111,workflow_sha='8b8c108f032f1e6d58339cc436310402b40a10ce',
        archive_sha256='b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4',archive_bytes=4342414844,producer_job='mature-orders'),
    'storage': dict(artifact_id=12037828504,run_id=38872643738,workflow_sha='4f1a7d7f0bd6c90704b5370f5e508669afe3b00f',
        archive_sha256='7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4',archive_bytes=554,producer_job='mature-storage'),
    'catalog': dict(artifact_id=12043567528,run_id=38884880079,workflow_sha='ee5000a156ebcf1fcec4a893da1a06958feb0ed5',
        archive_sha256='854c941a708c3aa7abd8a85836369c4a209e089496d6b82906afe30f9a9b1bbd',archive_bytes=585,producer_job='mature-catalog'),
    'source': dict(artifact_id=11870590333,run_id=38508408370,workflow_sha='124c3215468a60862b7848086f00a8e768a6ed66',
        archive_sha256='409cf0230ff1606b7eddd587a69c22076c11447eb6497e642e584c4fd3b74ef9',archive_bytes=1339563957,producer_job='late-lazy')}
# One growing working database plus its full journal OR final backup; no third copy.
OUTPUT_MAX_BYTES = PUBLISHED_FILES['p5-long-complete.sqlite']['bytes'] + 8*1024**3
WORK_FREE_BYTES = 2*OUTPUT_MAX_BYTES + 8*1024**3
START_FREE_BYTES = WORK_FREE_BYTES + sum(f['bytes'] for f in PUBLISHED_FILES.values()) + 3910109453 + 64*1024**2


def unique_launch():
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('mature continuation rerun requires inspection before retry')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    current = artifacts._api(f'/actions/runs/{run_id}')
    if (current.get('head_sha') != os.environ['GITHUB_SHA']
            or current.get('path') != WORKFLOW or current.get('head_branch') != BRANCH):
        raise ValueError('mature continuation executing workflow mismatch')
    runs = artifacts._pages(f'/actions/runs?head_sha={current["head_sha"]}', 'workflow_runs')
    matching = [r['id'] for r in runs if r.get('path') == WORKFLOW
        and r.get('head_sha') == current['head_sha'] and r.get('head_branch') == BRANCH]
    if not matching or min(matching) != run_id:
        raise ValueError('duplicate mature continuation run; inspect the earlier run')


def check_helpers():
    publish.check_helpers()
    if old.file_hash('simulation/construction_mature_publish.py') != '9220b51c93ca1c1c4d1e347fe51cebc8418abbbcfd4a729ee245203ce749e07b':
        raise ValueError('continuation helper differs from reviewed candidate')


def download_inputs():
    specs = dict(
        published=(38907665230,12049884660,'construction-mature-published','mature-publish',PUBLISHED_WORKFLOW_SHA,publish.WORKFLOW,
            '5ea709166d2bba7f7a22d614fed604f471973ae9ff757979a4148ff197c43382',3910109453,{'checkpoint.json','p5-long-complete.sqlite'}),
        diagnostics=(38907665230,12050152952,'construction-mature-publish-diagnostics','mature-publish',PUBLISHED_WORKFLOW_SHA,publish.WORKFLOW,
            '58e4d2584cdbcaffa8ee31e9173473c46d07d60b202e4d8d0e319ac2da597823',19421,{'publish-summary.json','publish.log','disk-start.txt'}),
        storage=(38872643738,12037828504,'construction-mature-storage','mature-storage',PUBLISH_INPUTS['storage']['workflow_sha'],publish.catalog.storage.WORKFLOW,
            PUBLISH_INPUTS['storage']['archive_sha256'],554,{'storage.json'}),
        catalog=(38884880079,12043567528,'construction-mature-catalog','mature-catalog',PUBLISH_INPUTS['catalog']['workflow_sha'],publish.catalog.WORKFLOW,
            PUBLISH_INPUTS['catalog']['archive_sha256'],585,{'catalog.json'}))
    directories, proofs = {}, {}
    for label, row in specs.items():
        directories[label] = ROOT/label
        proof = artifacts.download(directories[label], run_id=row[0], artifact_id=row[1], name=row[2], job=row[3],
            workflow_sha=row[4], workflow_path=row[5], expected_digest=row[6], members=row[8])
        if proof['archive_bytes'] != row[7]: raise ValueError('continuation input archive size mismatch')
        proofs[label] = proof
    return directories, proofs


def validate_inputs(published, diagnostics, storage_receipt, catalog_receipt):
    for directory, members in ((published,set(PUBLISHED_FILES)),
            (diagnostics,{'publish-summary.json','publish.log','disk-start.txt'})):
        if (directory.is_symlink() or set(p.name for p in directory.iterdir()) != members
                or any(p.is_symlink() or not p.is_file() for p in directory.iterdir())):
            raise ValueError('unexpected mature continuation input members')
    for name, expected in PUBLISHED_FILES.items():
        path = published/name
        if path.stat().st_size != expected['bytes'] or old.file_hash(path) != expected['sha256']:
            raise ValueError('published checkpoint differs from inspected artifact')
    summary_path = diagnostics/'publish-summary.json'
    if summary_path.stat().st_size != SUMMARY_BYTES or old.file_hash(summary_path) != SUMMARY_SHA:
        raise ValueError('publication summary differs from inspected artifact')
    summary, receipt = old._json(summary_path), old._json(published/'checkpoint.json')
    if (summary.get('stage') != 'complete-published' or summary.get('context') != CONTEXT
            or summary.get('runtime_sha') != RUNTIME_SHA or summary.get('execution_harness_sha') != PUBLISHED_HARNESS_SHA
            or summary.get('execution_workflow_sha') != PUBLISHED_WORKFLOW_SHA
            or summary.get('receipt') != receipt or summary.get('files') != PUBLISHED_FILES
            or {k:{a:b for a,b in v.items() if a!='seconds'} for k,v in summary.get('inputs',{}).items()} != PUBLISH_INPUTS):
        raise ValueError('publication summary authority mismatch')
    conversion = dict(source_generation=SOURCE_GENERATION,generation=CANDIDATE_PIN['captured_head'],
        store_identity=CANDIDATE_PIN['store_identity'],source_preserved=True,complete_format=True)
    if (type(receipt.get('schema')) is not int or receipt['schema'] != 1 or receipt.get('stage') != 'complete'
            or receipt.get('config') != dict(SOURCE_CONFIG,product_sha=RUNTIME_SHA)
            or receipt.get('workflow_sha') != PUBLISHED_WORKFLOW_SHA or receipt.get('product_sha') != RUNTIME_SHA
            or receipt.get('checkpoint_product_sha') != SOURCE_CONFIG['product_sha']
            or receipt.get('database') != dict(name='p5-long-complete.sqlite',sha256=PUBLISHED_FILES['p5-long-complete.sqlite']['sha256'])
            or receipt.get('source_checkpoint') != SOURCE_CHECKPOINT or not isinstance(receipt.get('state'),dict)
            or receipt['state'].get('conversion_result') != conversion
            or set(receipt['state'].get('controls',{})) != {str(y) for y in SOURCE_CONFIG['milestones']}):
        raise ValueError('normal published checkpoint authority mismatch')
    for path, size, digest, stage, previous in (
            (storage_receipt,STORAGE_RECEIPT_BYTES,STORAGE_RECEIPT_SHA,'storage-verified',None),
            (catalog_receipt,CATALOG_RECEIPT_BYTES,CATALOG_RECEIPT_SHA,'catalog-verified',STORAGE_RECEIPT_SHA)):
        authority = dict(schema=old.SCHEMA_NAME,stage=stage,manifest_sha256=CANDIDATE_MANIFEST_SHA,
            database=CANDIDATE_DATABASE,context=CONTEXT,previous_receipt_sha256=previous)
        if (path.is_symlink() or path.stat().st_size != size or old.file_hash(path) != digest
                or old._json(path) != authority):
            raise ValueError('retained verification receipt authority mismatch')
    return receipt


def run_continue(published, diagnostics, storage_receipt, catalog_receipt, bundle, *, workflow_sha):
    published, diagnostics, bundle = Path(published), Path(diagnostics), Path(bundle)
    storage_receipt, catalog_receipt = Path(storage_receipt), Path(catalog_receipt)
    if bundle.exists(): raise FileExistsError(bundle)
    receipt = validate_inputs(published,diagnostics,storage_receipt,catalog_receipt)
    expected = {p:old.file_hash(p) for p in [*published.iterdir(),*diagnostics.iterdir(),storage_receipt,catalog_receipt]}
    bundle.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mature-continue-',dir=bundle.parent) as directory:
        private = Path(directory)
        # World sessions mutate pins on open/close. NEVER hard-link the input DB.
        for name in PUBLISHED_FILES: shutil.copyfile(published/name,private/name)
        with redirect_stdout(publish.catalog.storage._DiagnosticOutput(sys.stdout)), publish.legacy.progress():
            result = p5.run(SOURCE_CONFIG['seed'],SOURCE_CONFIG['milestones'],SOURCE_CONFIG['bootstrap_year'],private,
                SOURCE_CONFIG['rules_id'],EXECUTION_RUNTIME_SHA,workflow_sha,complete_format=True,
                initialization=SOURCE_CONFIG['initialization'],resume_from='complete',
                checkpoint_product_sha=RUNTIME_SHA)
        result = json.loads(json.dumps(result))
        source = dict(product_sha=RUNTIME_SHA,workflow_sha=PUBLISHED_WORKFLOW_SHA,stage='complete',
            database=receipt['database'],receipt_sha256=PUBLISHED_FILES['checkpoint.json']['sha256'],
            prior_source=receipt['source_checkpoint'])
        if (result.get('passed') is not True or result.get('schema') != 1 or result.get('workflow_sha') != workflow_sha
                or result.get('product_sha') != EXECUTION_RUNTIME_SHA or result.get('source_checkpoint') != source
                or result.get('checkpoint_product_sha') != RUNTIME_SHA or result.get('control') != receipt['state']['controls']
                or any(result.get(k) != SOURCE_CONFIG[k] for k in ('seed','milestones','bootstrap_year','rules_id','complete_format','initialization','simulation_schema'))
                or set(result.get('p4',{})) != {str(y) for y in SOURCE_CONFIG['milestones']}):
            raise ValueError('continuation result authority mismatch')
        for index, year in enumerate(SOURCE_CONFIG['milestones'],1):
            row, control = result['p4'][str(year)], receipt['state']['controls'][str(year)]
            if (row.get('matches_control') is not True or row.get('reopen_digest') != control['digest']
                    or row.get('generation') != CANDIDATE_PIN['captured_head']+index
                    or {k:v for k,v in row.get('audit',{}).items() if k!='audit_seconds'}
                        != {k:v for k,v in control['audit'].items() if k!='audit_seconds'}):
                raise ValueError('continuation milestone differs from bound independent control')
        restored = private/'p5-long-restore.sqlite'; info = result['restore_artifact']
        if (info.get('path') != str(restored) or info.get('year') != SOURCE_CONFIG['milestones'][-1]
                or info.get('generation') != result['p4'][str(info['year'])]['generation']
                or info.get('digest') != receipt['state']['controls'][str(info['year'])]['digest']
                or info.get('sha256') != old.file_hash(restored) or info.get('bytes') != restored.stat().st_size
                or not 0 < restored.stat().st_size <= OUTPUT_MAX_BYTES):
            raise ValueError('continued restore artifact checksum/authority/size mismatch')
        if any(old.file_hash(path) != digest for path,digest in expected.items()):
            raise ValueError('continuation changed retained prerequisite')
        with restored.open('rb') as stream: os.fsync(stream.fileno())
        info['path'] = 'restore.sqlite'
        info['restore_command'] = (
            'PYTHONPATH=simulation:. python -c "from ate_sim.persistence_lazy import open_lazy_world_session; '
            f"s=open_lazy_world_session('restore.sqlite', rules_id={SOURCE_CONFIG['rules_id']!r}); "
            'print(s.world.year, s.world.digest()); s.close()"')
        old._write_new(private/'result.json',result)
        bundle.mkdir()
        try:
            os.link(restored,bundle/'restore.sqlite')
            os.link(private/'result.json',bundle/'result.json')
            os.link(published/'checkpoint.json',bundle/'checkpoint.json')
            old._fsync_dir(bundle); old._fsync_dir(bundle.parent)
        except BaseException:
            shutil.rmtree(bundle)
            raise
    return result


def main():
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    ROOT.mkdir(exist_ok=True)
    sha = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    tree = subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip()
    if (sha != os.environ['HARNESS_SHA'] or os.environ['RUNTIME_SHA'] != EXECUTION_RUNTIME_SHA
            or tree != EXECUTION_RUNTIME_TREE):
        raise ValueError('mature continuation harness/runtime differs from reviewed candidate')
    check_helpers(); unique_launch()
    if shutil.disk_usage('.').free < START_FREE_BYTES:
        raise ValueError(f'need {START_FREE_BYTES} bytes disk headroom before continuation downloads')
    inputs, proofs = download_inputs()
    if shutil.disk_usage('.').free < WORK_FREE_BYTES:
        raise ValueError(f'need {WORK_FREE_BYTES} bytes disk headroom before continuation')
    started, cpu = time.monotonic(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_SELF)
    result = run_continue(inputs['published'],inputs['diagnostics'],inputs['storage']/'storage.json',
        inputs['catalog']/'catalog.json',ROOT/'continued',workflow_sha=os.environ['GITHUB_SHA'])
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        old._write_new(ROOT/'continue-summary.json',dict(stage='exact-continued',execution_harness_sha=sha,
            execution_workflow_sha=os.environ['GITHUB_SHA'],runtime_sha=EXECUTION_RUNTIME_SHA,
            checkpoint_runtime_sha=RUNTIME_SHA,context=CONTEXT,inputs=proofs,
            wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,peak_rss_kib=usage.ru_maxrss,
            filesystem_output_blocks=usage.ru_oublock-before.ru_oublock,disk_free_bytes=shutil.disk_usage('.').free,
            files={p.name:dict(bytes=p.stat().st_size,sha256=old.file_hash(p)) for p in (ROOT/'continued').iterdir()},
            passed=result['passed'],milestones=SOURCE_CONFIG['milestones'],restore_artifact=result['restore_artifact']))
    except Exception:
        pass


if __name__ == '__main__': main()
