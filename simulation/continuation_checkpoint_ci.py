"""Bounded fresh-runner proof of retained saves, retry and downloaded restore."""
import argparse
import os
from pathlib import Path
import resource
import shutil
import tempfile

from simulation import continuation_receipts as r
from simulation import continuation_checkpoint as checkpoint
from simulation import construction_mature_continuation_stages as runner


ROOT = Path('evidence')
PREFIX = 'continuation-small-'
FIXTURE_CAP = 256*1024**2
ROLES = {
    'save1':('save',1,{}),
    'audit1':('audit',1,{'candidate':'save1'}),
    'digest1':('digest',1,{'candidate':'save1'}),
    'accept1':('accept-year',1,{'candidate':'save1','audit':'audit1','digest':'digest1'}),
    'save2':('save',2,{'candidate':'save1','previous':'accept1'}),
    'audit2':('audit',2,{'candidate':'save2'}),
    'digest2':('digest',2,{'candidate':'save2'}),
    'accept2':('accept-year',2,{'candidate':'save2','audit':'audit2','digest':'digest2','previous':'accept1'}),
    'continued':('accept-continuation',2,{'candidate':'save2','first':'accept1','second':'accept2'}),
    'restore-values':('restore-values',2,{'candidate':'save2','continuation':'continued'}),
    'restore-digest':('restore-digest',2,{'candidate':'save2','continuation':'continued'}),
    'restored':('accept-restore',2,{'candidate':'save2','continuation':'continued','values':'restore-values','digest':'restore-digest'}),
}


def build_source(destination):
    # Fixture creation is deliberately outside the mature dispatcher. Its
    # explicit 6x6 World, two years and treasury/alias setup are test utilities.
    from simulation.tests.continuation_fixtures import build_publication
    destination = Path(destination)
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bounded-source-',dir=destination.parent) as directory:
        info = build_publication(directory,runtime=os.environ['RUNTIME_SHA'],
            harness=os.environ['HARNESS_SHA'],workflow=os.environ['GITHUB_SHA'])
        published = info.pop('published')
        info['kind'] = 'bounded-continuation-fixture'
        r.publish_receipt(published/'fixture.json',info)
        destination.mkdir()
        try:
            for path in published.iterdir():
                os.link(path,destination/path.name)
            r.fsync_dir(destination);r.fsync_dir(destination.parent)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination


def reference(role):
    run_id = int(os.environ['GITHUB_RUN_ID'])
    matches = [row for row in runner.artifacts._pages(f'/actions/runs/{run_id}/artifacts','artifacts')
        if row.get('name')==PREFIX+role]
    if len(matches) != 1:raise ValueError('missing or ambiguous bounded artifact')
    row = matches[0]
    digest = row.get('digest','')
    if not digest.startswith('sha256:'):raise ValueError('bounded artifact digest missing')
    ref = r.ArtifactRef(artifact_id=row['id'],run_id=run_id,workflow_sha=os.environ['GITHUB_SHA'],
        workflow_path=runner.PROOF_WORKFLOW,producer_job=role,name=PREFIX+role,
        archive_sha256=digest[7:],archive_bytes=row['size_in_bytes'],
        harness_sha=os.environ['HARNESS_SHA'],runtime_sha=os.environ['RUNTIME_SHA'],
        runtime_tree=runner.original.EXECUTION_RUNTIME_TREE)
    runner.authenticate_ref(ref,max_archive_bytes=FIXTURE_CAP+2*r.METADATA_MAX_BYTES+runner.SMALL_SPACE)
    return ref


def original_authority(root):
    source_ref = reference('source')
    source = root/'original-source'
    runner.download_ref(source_ref,source,members={'checkpoint.json','p5-long-complete.sqlite','fixture.json'},
        database_cap=FIXTURE_CAP)
    info = r.load_receipt(source/'fixture.json')
    r.exact(info,('kind','context','source_config','generation','store_identity'),'bounded fixture')
    if (info['kind'] != 'bounded-continuation-fixture'
            or info['source_config']['milestones'] != [1,2] or info['source_config']['bootstrap_year'] != 0
            or info['source_config']['seed'] != 843000 or info['source_config']['rules_id'] != 'continuation-proof'
            or info['context']['harness_sha'] != os.environ['HARNESS_SHA']
            or info['context']['runtime_sha'] != os.environ['RUNTIME_SHA']):
        raise ValueError('unexpected bounded fixture authority')
    published = root/'published';published.mkdir()
    for name in ('checkpoint.json','p5-long-complete.sqlite'):
        os.link(source/name,published/name)  # Retained input only; core makes mutable copies.
    from simulation.tests.continuation_fixtures import fixture_authority
    authority = fixture_authority(dict(info,published=published),publication=source_ref)
    if authority.output_max_bytes > FIXTURE_CAP:raise ValueError('bounded fixture exceeds cap')
    r.validate_original(published/'checkpoint.json',authority)
    return authority,published


def interrupted_audit(root,authority):
    ref = reference('save1');saved = root/'candidate'
    runner.download_ref(ref,saved,members=r.SAVED_MEMBERS,database_cap=authority.output_max_bytes)
    before = {p.name:r.file_hash(p) for p in saved.iterdir()}
    actual = checkpoint._phase
    def interrupt(name,**details):
        actual(name,**details)
        if name=='after_audit':raise OSError('deliberate audit interruption')
    checkpoint._phase = interrupt
    try:
        try:
            checkpoint.audit_year(saved,root/'must-not-exist.json',authority=authority,candidate=ref,
                producer=runner.producer('audit','interrupt-audit1'))
        except OSError as error:
            if str(error) != 'deliberate audit interruption':raise
        else:
            raise AssertionError('bounded audit did not interrupt')
    finally:
        checkpoint._phase = actual
    checkpoint._unchanged(saved,before)
    if (root/'must-not-exist.json').exists():raise AssertionError('interrupted audit exposed receipt')
    r.publish_receipt(root/'output/interrupt.json',dict(passed=True,no_receipt=True,
        candidate=ref.to_dict(),save_sha256=before['save.json'],database_sha256=before['candidate.sqlite']))


def proof_summary(root):
    ref = reference('restored')
    runner.download_ref(ref,root/'restored',members={'restore-verified.json'})
    result = r.load_receipt(root/'restored/restore-verified.json')
    authority = r.Authority.from_dict(result['authority'])
    r.match_producer(ref,result['producer'],authority)
    r.validate_restore_acceptance(result,authority)
    if result['binding']['year'] != 2:raise ValueError('bounded restore did not observe year2')
    r.publish_receipt(root/'output/proof.json',dict(stage='fresh-runner-continuation-proof',passed=True,
        runtime_sha=os.environ['RUNTIME_SHA'],runtime_tree=runner.original.EXECUTION_RUNTIME_TREE,
        harness_sha=os.environ['HARNESS_SHA'],implementation_hashes=runner.implementation_hashes(),
        restore_artifact=ref.to_dict(),restore_receipt_sha256=r.file_hash(root/'restored/restore-verified.json')))


def fixture_features(root,saved,authority):
    """Point-check the bounded fixture's shared alias and real counted storage."""
    before = {p.name:r.file_hash(p) for p in saved.iterdir()}
    with tempfile.TemporaryDirectory(prefix='.fixture-observe-',dir=root) as directory:
        copy = Path(directory)/'copy.sqlite';shutil.copyfile(saved/'candidate.sqlite',copy)
        with checkpoint.open_lazy_world_session(copy,rules_id=authority.source_config['rules_id']) as session:
            checkpoint._check_session(session,authority,2,authority.bootstrap_generation+2)
            shared = (session.world.skills.skills[1,'craft'].provenance
                      is session.world.skills.skills[2,'craft'].provenance)
            count = session.store.db.execute('SELECT count(*) FROM lazy_record_versions WHERE namespace=? AND valid_to IS NULL',
                ('aux.lazy.sequence.descriptors',)).fetchone()[0]
            if not shared or count <= 0:raise AssertionError('bounded restore lost shared/counteds fixture')
    checkpoint._unchanged(saved,before)
    values = dict(year=2,shared_nested_identity=shared,counted_histories=count)
    r.publish_receipt(root/'fixture-check.json',values)
    checkpoint._phase('fixture_features_verified',**values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',choices=sorted(set(ROLES)|{'source','interrupt-audit1','proof-summary'}),required=True)
    args = parser.parse_args(argv)
    resource.setrlimit(resource.RLIMIT_AS,(runner.MARGIN,runner.MARGIN))
    runner.check_source()
    if os.environ.get('GITHUB_RUN_ATTEMPT','1') != '1':
        raise ValueError('bounded proof rerun requires inspection')
    ROOT.mkdir(exist_ok=True)
    root = ROOT/args.job
    if root.exists():raise FileExistsError(root)
    root.mkdir()
    runner.check_space(runner.MARGIN+runner.SMALL_SPACE+4*FIXTURE_CAP)
    if args.job=='source':
        build_source(root/'output')
        return
    if args.job=='proof-summary':
        proof_summary(root)
        return
    authority,published = original_authority(root)
    if args.job=='interrupt-audit1':
        interrupted_audit(root,authority)
        return
    stage,year,roles = ROLES[args.job]
    refs = {label:reference(role) for label,role in roles.items()}
    paths = runner.fetch_stage_inputs(stage,year,root=root,authority=authority,refs=refs)
    if args.job=='save1':paths['publication'] = published
    if args.job=='audit1':
        probe = reference('interrupt-audit1')
        runner.download_ref(probe,root/'interruption',members={'interrupt.json'})
        evidence = r.load_receipt(root/'interruption/interrupt.json')
        if (evidence.get('passed') is not True or evidence.get('no_receipt') is not True
                or not r.same(evidence.get('candidate'),refs['candidate'].to_dict())
                or evidence.get('save_sha256') != r.file_hash(paths['candidate']/'save.json')
                or evidence.get('database_sha256') != r.file_hash(paths['candidate']/'candidate.sqlite')):
            raise ValueError('audit retry does not bind the interrupted saved artifact')
    runner.check_space(runner.required_space(stage,authority.output_max_bytes,0,authority.output_max_bytes,before=False))
    runner.execute_stage(stage,year,authority=authority,inputs=paths,refs=refs,
        producer=runner.producer(stage,args.job),output=root/'output')
    if args.job=='restore-values':fixture_features(root,paths['candidate'],authority)


if __name__=='__main__':main()
