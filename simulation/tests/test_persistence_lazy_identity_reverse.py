"""Checked, pinned discovery of one incarnation without owner enumeration."""

import pytest

from simulation.ate_sim.incremental_store import StoreFormatError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_store import (
    IdentityOccurrenceChange, LazyRecordStore, VersionChange,
    _identity_occurrence_checksum,
)
from simulation.tests.test_persistence_lazy_store import codec, make_store, metadata, open_store


def _groups(store, count):
    pin = store.capture_pin()
    result = store.commit(
        pin, commit_token="groups", changes=(), new_segments=(),
        version_changes=tuple(
            VersionChange("people", key, key)
            for key in range(1, 2 * count + 1)
        ),
        identity_changes=tuple(
            IdentityOccurrenceChange("people", key, (), incarnation_id=(key + 1) // 2)
            for key in range(1, 2 * count + 1)
        ),
        next_incarnation_id=count + 1, metadata=metadata(1),
    )
    return result.pin


@pytest.mark.parametrize("history", [1_000, 10_000])
def test_reverse_identity_lookup_reads_only_one_checked_group(tmp_path, history):
    with make_store(tmp_path / "groups.sqlite") as store:
        pin = _groups(store, history)
        before = store.diagnostics()
        assert store.identity_occurrences_for_incarnation(pin, history) == (
            ("people", 2 * history - 1, ()), ("people", 2 * history, ()),
        )
        after = store.diagnostics()
        assert after.payload_reads == before.payload_reads
        assert after.metadata_rows - before.metadata_rows <= 20
        plan = store.db.execute(
            "EXPLAIN QUERY PLAN SELECT owner_key FROM lazy_identity_occurrence_versions "
            "WHERE incarnation_id=? AND valid_from<=? "
            "AND (valid_to IS NULL OR ?<valid_to)",
            (history, pin.captured_head, pin.captured_head),
        ).fetchall()
        assert any("lazy_identity_incarnation_visible" in row[3] for row in plan)
        assert not any("SCAN lazy_identity_occurrence_versions" in row[3] for row in plan)


def test_reverse_identity_lookup_preserves_old_pin_after_replacement(tmp_path):
    with make_store(tmp_path / "old-pin.sqlite") as store:
        writer = _groups(store, 2)
        old = store.capture_pin()
        writer = store.commit(
            writer, commit_token="replacement", version_changes=(), changes=(),
            new_segments=(), identity_changes=(
                IdentityOccurrenceChange("people", 2, (), incarnation_id=3),
            ), next_incarnation_id=4, metadata=metadata(2),
        ).pin
        assert store.identity_occurrences_for_incarnation(old, 1) == (
            ("people", 1, ()), ("people", 2, ()),
        )
        assert store.identity_occurrences_for_incarnation(writer, 1) == (("people", 1, ()),)
        assert store.identity_occurrences_for_incarnation(writer, 3) == (("people", 2, ()),)
        assert store.identity_occurrences_for_incarnation(old, 3) == ()


def test_reverse_identity_lookup_checks_rows_and_requires_explicit_index_upgrade(tmp_path):
    with make_store(tmp_path / "checked.sqlite") as store:
        pin = _groups(store, 2)
        store.db.execute(
            "UPDATE lazy_identity_occurrence_versions SET row_checksum='corrupt' WHERE incarnation_id=1"
        )
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="identity occurrence checksum"):
            store.identity_occurrences_for_incarnation(pin, 1)

    with make_store(tmp_path / "legacy-index.sqlite") as store:
        pin = _groups(store, 2)
        store.db.execute("DROP INDEX lazy_identity_incarnation_visible")
        store.db.commit()
        with pytest.raises(StoreFormatError, match="explicit.*upgrade"):
            store.identity_occurrences_for_incarnation(pin, 1)


@pytest.mark.parametrize("incarnation", [0, -1, True, 1.0, "1"])
def test_reverse_identity_lookup_rejects_invalid_incarnation(tmp_path, incarnation):
    with make_store(tmp_path / "invalid.sqlite") as store:
        pin = store.capture_pin()
        with pytest.raises(ValueError, match="positive int"):
            store.identity_occurrences_for_incarnation(pin, incarnation)


def test_explicit_current_head_copy_adds_reverse_index_without_changing_source(tmp_path):
    source, destination = tmp_path / "legacy.sqlite", tmp_path / "upgraded.sqlite"
    with make_store(source) as store:
        _groups(store, 2)
        store.db.execute("DROP INDEX lazy_identity_incarnation_visible")
        store.db.commit()
    original = source.read_bytes()
    with open_store(source) as store:
        assert store.db.execute(
            "SELECT name FROM sqlite_master WHERE name='lazy_identity_incarnation_visible'"
        ).fetchone() is None
    LazyRecordStore.copy_current_head(
        source, destination, codec=codec(), expected_simulation_schema="8",
        expected_rules_id="stage-0.5",
    )
    assert source.read_bytes() == original
    with open_store(destination) as store:
        pin = store.capture_pin()
        assert store.identity_occurrences_for_incarnation(pin, 1) == (
            ("people", 1, ()), ("people", 2, ()),
        )


@pytest.mark.parametrize("corruption", ["overlap", "path", "allocator"])
def test_reverse_identity_lookup_rejects_semantically_invalid_checked_rows(tmp_path, corruption):
    with make_store(tmp_path / "semantic.sqlite") as store:
        pin = _groups(store, 2)
        row = store.db.execute(
            "SELECT owner_namespace,owner_key,occurrence_path,incarnation_id,"
            "valid_from,valid_to,row_checksum FROM lazy_identity_occurrence_versions "
            "WHERE incarnation_id=1 ORDER BY owner_key LIMIT 1"
        ).fetchone()
        namespace, key, path, identity, start, end, _ = row
        if corruption == "overlap":
            start = 0
            checksum = _identity_occurrence_checksum(namespace, key, path, identity, start, end)
            store.db.execute(
                "INSERT INTO lazy_identity_occurrence_versions VALUES (?,?,?,?,?,?,?)",
                (namespace, key, path, identity, start, end, checksum),
            )
        else:
            if corruption == "path":
                path = store.codec.encode((("unsupported", 1),))
            else:
                identity = 10
            checksum = _identity_occurrence_checksum(namespace, key, path, identity, start, end)
            store.db.execute(
                "UPDATE lazy_identity_occurrence_versions SET occurrence_path=?,"
                "incarnation_id=?,row_checksum=? WHERE owner_namespace=? AND owner_key=?",
                (path, identity, checksum, namespace, key),
            )
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="identity occurrence"):
            store.identity_occurrences_for_incarnation(pin, 10 if corruption == "allocator" else 1)
