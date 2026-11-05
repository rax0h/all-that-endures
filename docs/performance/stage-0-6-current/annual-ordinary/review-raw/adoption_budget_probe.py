"""Single-fixture reproduction for the independent annual-ordinary review."""
from contextlib import ExitStack
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ate_sim import persistence_proof_world as world
from ate_sim import persistence_proof_manifest_publish as pub
from ate_sim import persistence_proof_world_adoption as adoption
from ate_sim.persistence_lazy_adoption import BUCKET_NAMESPACE
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened

def configure(w):
    w.culture.adoption[1, 1] = .25

children = []
original = pub.commit_world_manifest

def omit_buckets(*args, **kwargs):
    versions = kwargs["version_changes"]
    removed = [c.key for c in versions if c.namespace == BUCKET_NAMESPACE]
    assert removed
    print("removed counters", removed)
    kwargs["version_changes"] = tuple(c for c in versions if c.namespace != BUCKET_NAMESPACE)
    result = original(*args, **kwargs)
    children.append(result.manifest)
    print("committed manifest generation", result.manifest[0].generation, "reaudited", result.reaudited)
    return result

with TemporaryDirectory(dir='/tmp', prefix='annual-review-budget-') as tmp:
    path, pair = fixture(Path(tmp), configure=configure)
    session = opened(path, pair)
    try:
        session.world.culture.adoption[1,1] = .5
        with ExitStack() as stack:
            stack.enter_context(patch.object(adoption, 'MAX_READS', 1))
            stack.enter_context(patch.object(pub, 'commit_world_manifest', omit_buckets))
            if os.environ.get('FORCE_FULL_AUDIT'):
                from ate_sim import persistence_proof_world_value as value
                from ate_sim import persistence_proof_world_insert as insert
                stack.enter_context(patch.object(value, 'validate_value_transition', return_value=False))
                stack.enter_context(patch.object(insert, 'prepare', return_value=None))
            else:
                stack.enter_context(patch.object(world, '_audit_world', side_effect=AssertionError('unexpected audit')))
            generation = session.save()
        print("committed generation", generation)
    except Exception as e:
        print("participant validation after commit", type(e).__name__, str(e))
    finally:
        session.store.close()
    child, = children
    with opened(path, child) as restored:
        print("restored value", restored.world.culture.adoption[1, 1])
        print("restored query", restored.world.culture.adoption.items_above(.35))
