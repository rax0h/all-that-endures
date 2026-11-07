"""The admitted World head, not a locally recomputed checksum, owns metadata."""
import pytest

from ate_sim.incremental_store import StoreIntegrityError, _head_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def _match_manifest(store, manifest):
    metadata = store.head_metadata()
    assert store.codec.encode(metadata["simulation_position"]) == manifest.head.simulation_position
    assert metadata["seed"] == manifest.head.seed
    assert store.codec.encode(metadata["next_ids"]) == manifest.head.next_ids
    assert store.codec.encode(metadata["namespaces"]) == manifest.head.namespace_inventory


def test_native_head_metadata_matches_manifest_after_save_and_fresh_restore(tmp_path):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        store = session.store
        _match_manifest(store, pair[0])
        with store.read_snapshot(session.pin):
            _match_manifest(store, pair[0])
        assert not store.db.in_transaction
        session.skills[1, "craft"].level = .625
        assert session.save() == 1
        child = session.proof_manifest
        _match_manifest(store, child[0])
    with opened(path, child) as session:
        _match_manifest(session.store, child[0])
        assert not session.store.db.in_transaction


@pytest.mark.parametrize("field", [
    "simulation_position", "seed", "next_ids",
    "namespace_inventory", "namespace_counts",
])
def test_native_head_rejects_checksum_consistent_forgery_before_codec_decode(
    tmp_path, monkeypatch, field
):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        store = session.store
        row = list(store.db.execute(
            "SELECT generation,parent_generation,simulation_position,seed,"
            "next_ids,namespace_inventory,namespace_counts,head_checksum "
            "FROM save_head WHERE singleton=1"
        ).fetchone())
        original_row = tuple(row)
        fields = {
            "simulation_position": (2, store.codec.encode(2000)),
            "seed": (3, row[3] + 1),
            "next_ids": (4, store.codec.encode({})),
            "namespace_inventory": (5, store.codec.encode(("forged.namespace",))),
            "namespace_counts": (6, store.codec.encode(())),
        }
        slot, forged = fields[field]
        assert row[slot] != forged
        row[slot] = forged
        row[-1] = _head_checksum(*row[:-1])
        store.db.execute(
            "UPDATE save_head SET simulation_position=?,seed=?,next_ids=?,"
            "namespace_inventory=?,namespace_counts=?,head_checksum=? WHERE singleton=1",
            (*row[2:7], row[7])
        )
        store.db.commit()
        # Isolate the manifest join from the coarse epoch check, without
        # adding any production bypass.
        authority = store._world_proof_authority
        authority.epoch = authority._epoch()
        original = store.codec.decode
        def observe(payload):
            assert payload != forged, "forged accepted-head bytes reached codec"
            return original(payload)
        monkeypatch.setattr(store.codec, "decode", observe)
        try:
            with pytest.raises(StoreIntegrityError, match="accepted manifest"):
                store.head_metadata()
            assert not store.db.in_transaction
        finally:
            # Restore the deliberately forged fixture before context-manager
            # cleanup releases its pin. A bad head must not leak into teardown.
            monkeypatch.setattr(store.codec, "decode", original)
            store.db.execute(
                "UPDATE save_head SET simulation_position=?,seed=?,next_ids=?,"
                "namespace_inventory=?,namespace_counts=?,head_checksum=? WHERE singleton=1",
                (*original_row[2:7], original_row[7]),
            )
            store.db.commit()
            authority.epoch = authority._epoch()
        _match_manifest(store, pair[0])
        assert not store.db.in_transaction


def test_head_forgery_rejection_does_not_suppress_ordinary_source_checks(tmp_path):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        store = session.store
        assert store.read_record("world.year", 0) == (0, 0)
        _match_manifest(store, pair[0])
        assert not store.db.in_transaction
