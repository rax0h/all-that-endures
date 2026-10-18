"""Real bounded authority/World fixtures shared by continuation tests only."""
import json
from pathlib import Path
import shutil

from simulation import complete_upgrade_checkpoint as old


def build_publication(root, *, runtime='b'*40, harness='e'*40, workflow='c'*40):
    import persistence_p5_long_validation as p5
    from simulation.construction_checkpoint_ci import fixture_world
    root=Path(root);root.mkdir(parents=True,exist_ok=True);source=root/'source'
    original=p5.generate_world
    def populated(seed, **kw):
        world=fixture_world(original,seed,width=6,height=6,settlements=1,**kw)
        world.currency.treasuries[1]={'iron':7,'lesser':5}
        for denomination,count in world.currency.treasuries[1].items():
            world.currency.minted[denomination]=world.currency.minted.get(denomination,0)+count
        return world
    p5.generate_world=populated
    try:
        p5.run(843000,[1,2],0,source,'continuation-proof','a'*40,workflow,
            complete_format=True,initialization='mature',stop_after='lazy')
    finally:
        p5.generate_world=original
    context=dict(runtime_sha=runtime,harness_sha=harness,
        source_artifact=dict(id=17,run_id=23,archive_sha256='c'*64))
    candidate=root/'candidate';storage=root/'storage.json';catalog=root/'catalog.json'
    manifest=old.capture(source/'p5-long-lazy.sqlite',source/'checkpoint.json',candidate,
        rules_id='continuation-proof',context=context)
    old.verify_storage(candidate,storage,context=context)
    old.verify_catalog(candidate,storage,catalog,context=context)
    prior=old._json(source/'checkpoint.json')
    old.publish_p5(candidate,storage,catalog,source,context=context,workflow_sha=workflow)
    published=root/'published';published.mkdir()
    for name in ('checkpoint.json','p5-long-complete.sqlite'):
        shutil.copyfile(source/name,published/name)
    return dict(published=published,context=context,source_config=prior['config'],
        generation=manifest['pin']['captured_head'],store_identity=manifest['pin']['store_identity'])


def fixture_authority(info, publication=None):
    from simulation import continuation_receipts as r
    published=Path(info['published'])
    if publication is None:
        publication=r.ArtifactRef(artifact_id=1,run_id=1,workflow_sha='c'*40,
            workflow_path='.github/workflows/proof.yml',producer_job='source',name='source',
            archive_sha256='d'*64,archive_bytes=100,harness_sha='e'*40,
            runtime_sha='b'*40,runtime_tree='f'*40)
    original=r.load_receipt(published/'checkpoint.json')
    return r.Authority(checkpoint_sha256=r.file_hash(published/'checkpoint.json'),
        checkpoint_bytes=(published/'checkpoint.json').stat().st_size,context=info['context'],
        source_config=info['source_config'],publication=publication,
        published_database_sha256=r.file_hash(published/'p5-long-complete.sqlite'),
        published_database_bytes=(published/'p5-long-complete.sqlite').stat().st_size,
        checkpoint_runtime_sha=original['product_sha'],execution_runtime_sha=publication.runtime_sha,
        execution_runtime_tree=publication.runtime_tree,bootstrap_generation=info['generation'],
        store_identity=info['store_identity'],output_max_bytes=(published/'p5-long-complete.sqlite').stat().st_size+8*1024**2)
