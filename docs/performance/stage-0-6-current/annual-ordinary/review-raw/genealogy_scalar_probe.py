"""Check that a zero-projection tuple still meets its native family value contract."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from ate_sim import persistence_lazy_identity_catalog as catalog
from ate_sim import persistence_proof_manifest_publish as pub
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened

ns = 'world.genealogy.parents'
def configure(w):
    w.genealogy.parents[1] = (12,)
children = []
original = pub.commit_world_manifest
def forge(store, pin, *args, **kwargs):
    changes = kwargs['version_changes']
    src, = [c for c in changes if c.namespace == ns and c.key == 1]
    bad = replace(src, value=('invalid-parent',))
    digest = catalog._source_commitment(store.codec, bad, 'lazy', pin.captured_head+1)
    def damage(c):
        if c is src:
            return bad
        if c.namespace == catalog.OWNER_NAMESPACE and c.key == (ns, 1):
            return replace(c, value=c.value[:5]+(digest,)+c.value[6:])
        return c
    kwargs['version_changes'] = tuple(damage(c) for c in changes)
    result = original(store, pin, *args, **kwargs)
    children.append(result.manifest)
    print('committed', result.manifest[0].generation, 'reaudited', result.reaudited)
    return result
with TemporaryDirectory(dir='/tmp', prefix='annual-review-parents-') as tmp:
    path, pair = fixture(Path(tmp), configure=configure)
    session = opened(path, pair)
    try:
        session.world.genealogy.parents[1] = (13,)
        with patch.object(pub, 'commit_world_manifest', forge):
            session.save()
    except Exception as e:
        print('publication', type(e).__name__, str(e))
    finally:
        session.store.close()
    if children:
        with opened(path, children[0]) as restored:
            print('restored parents', restored.world.genealogy.parents[1])
