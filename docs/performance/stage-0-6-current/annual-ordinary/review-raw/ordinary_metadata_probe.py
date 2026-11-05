"""A tiny body and oversized SQL checksum should reject without transferring the checksum."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from ate_sim import persistence_lazy_identity_catalog as catalog
from ate_sim import persistence_proof_world_insert as insert
from ate_sim import persistence_proof_world_ordinary as ordinary
from ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api

with TemporaryDirectory(dir='/tmp', prefix='annual-review-metadata-') as tmp:
    store, pin, pair = _proof_store(Path(tmp))
    try:
        store.db.execute("UPDATE records SET payload_checksum=replace(hex(zeroblob(524288)),'0','x') WHERE namespace='world.year'")
        store.db.commit()
        zero = store.codec.encode(0)
        c = VersionChange(catalog.CATALOG_NAMESPACE, 0, ())
        row = dict(namespace=c.namespace, typed_key=zero, payload=store.codec.encode(()), memberships_blob=store.codec.encode(()), change=c)
        request = SimpleNamespace(pin=pin, pairs=manifest_api()._pairs(store, pin.captured_head))
        def guarded_text(value):
            if len(value)>8192:
                raise AssertionError(f"SQLite transferred {len(value)} bytes of malformed text to Python")
            return value.decode()
        def read_year(store, request, rows, read, forest):
            return read('world.year', zero)
        store.db.text_factory = guarded_text
        with store.read_snapshot(pin), patch.object(ordinary, 'prepare', read_year), patch.object(insert, 'MAX_BYTES', 65536):
            insert.prepare(store, request, (row,), (), ())
    finally:
        store.close()
