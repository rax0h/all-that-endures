"""Probe legacy checked snapshot nesting across two legitimate pins."""
from tempfile import TemporaryDirectory
from pathlib import Path
from simulation.tests.test_stage_0_5_proof_world_session import opened, fixture
from simulation.tests.test_stage_0_5_final_catalog_copy import opened as store_opened

with TemporaryDirectory() as td:
    path,pair=fixture(Path(td))
    with store_opened(path) as capture:
        ancient=capture.capture_pin()
    s=opened(path,pair)
    try:
        s.world.year=1
        assert s.save()==1
        with s.store.read_snapshot(ancient) as outer:
            assert outer==0
            print('inside_owned_gen0_snapshot accepted, observed',s.proof_manifest[0].generation,s.store.read_record('world.year',0))
    finally:s.store.close()
