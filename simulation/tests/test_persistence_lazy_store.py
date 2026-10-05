import sqlite3
from itertools import islice
from pathlib import Path

import pytest

from simulation.ate_sim.incremental_store import (
    Membership,
    NewSegment,
    RecordChange,
    StoreConflictError,
    StoreFormatError,
    StoreIntegrityError,
    TypedCodec,
    create as create_p1,
    open as open_p1,
)
from simulation.ate_sim.persistence_lazy_store import (
    GenerationPressureError,
    LazyRecordStore,
    VersionChange,
)


def codec():
    return TypedCodec()


def metadata(position=0, namespaces=("people",), seed=7):
    return {
        "simulation_position": position,
        "seed": seed,
        "next_ids": {"person": position + 10},
        "namespaces": namespaces,
    }


def make_store(path):
    return LazyRecordStore.create(
        path,
        codec=codec(),
        simulation_schema="8",
        rules_id="stage-0.5",
    )


def open_store(path):
    return LazyRecordStore.open(
        path,
        codec=codec(),
        expected_simulation_schema="8",
        expected_rules_id="stage-0.5",
    )


def commit(store, pin, token, version_changes=(), *, position=1, changes=(), segments=(), namespaces=("people",)):
    return store.commit(
        pin,
        commit_token=token,
        version_changes=version_changes,
        changes=changes,
        new_segments=segments,
        metadata=metadata(position, namespaces),
    )


def test_format3_is_explicit_and_legacy_format2_is_rejected_both_ways(tmp_path):
    p4 = tmp_path / "p4.sqlite"
    with make_store(p4) as store:
        assert store.generation == 0
        assert dict(store.db.execute("SELECT key,value FROM store_metadata"))["format_version"] == "3"
    with pytest.raises(StoreFormatError):
        open_p1(p4, codec=codec(), expected_simulation_schema="8", expected_rules_id="stage-0.5")

    p1 = tmp_path / "p1.sqlite"
    p1_store = create_p1(
        p1,
        codec=codec(),
        simulation_schema="8",
        rules_id="stage-0.5",
        metadata=metadata(),
    )
    p1_store.close()
    with pytest.raises(StoreFormatError):
        open_store(p1)


def test_versioned_read_query_order_previous_snapshot_and_reinsertion(tmp_path):
    path = tmp_path / "save.sqlite"
    with make_store(path) as store:
        writer = store.capture_pin()
        first = commit(
            store,
            writer,
            "g1",
            (
                VersionChange("people", "a", {"name": "Ada"}, memberships=(Membership("city", "north", 0),)),
                VersionChange("people", "b", {"name": "Bryn"}, memberships=(Membership("city", "north", 1),)),
            ),
            position=1,
        )
        assert first.outcome == "committed"
        writer = first.pin
        previous = store.capture_pin()
        assert previous.captured_head == 1

        second = commit(
            store,
            writer,
            "g2",
            (
                VersionChange(
                    "people",
                    "a",
                    {"name": "Ada II"},
                    memberships=(Membership("city", "south", 0),),
                    reinsertion=True,
                ),
            ),
            position=2,
        )
        writer = second.pin
        assert store.read_version(previous, "people", "a", expected_record_schema=1).value == {"name": "Ada"}
        assert store.read_version(writer, "people", "a", expected_record_schema=1).value == {"name": "Ada II"}
        assert tuple(store.iter_keys(previous, "people")) == ("a", "b")
        assert tuple(store.iter_keys(writer, "people")) == ("b", "a")
        assert store.query_keys(previous, "people", "city", "north") == ("a", "b")
        assert store.query_keys(writer, "people", "city", "north") == ("b",)
        assert store.query_keys(writer, "people", "city", "south") == ("a",)
        assert store.verify_all()["generation"] == 2
        store.release_pin(previous)
        store.release_pin(writer)


def test_delete_absence_empty_namespace_and_generic_identity_link_records(tmp_path):
    path = tmp_path / "save.sqlite"
    with make_store(path) as store:
        pin = store.capture_pin()
        result = commit(
            store,
            pin,
            "insert",
            (
                VersionChange("people", 1, "Ada"),
                VersionChange("world_identity_links", ("people", 1, "wallet"), ("wallets", 9)),
            ),
            position=1,
            namespaces=("people", "world_identity_links"),
        )
        pin = result.pin
        link = store.read_version(
            pin,
            "world_identity_links",
            ("people", 1, "wallet"),
            expected_record_schema=1,
        )
        assert link.value == ("wallets", 9)

        result = commit(
            store,
            pin,
            "delete",
            (VersionChange("people", 1, delete=True),),
            position=2,
            namespaces=("people", "world_identity_links"),
        )
        pin = result.pin
        with pytest.raises(KeyError):
            store.read_version(pin, "people", 1, expected_record_schema=1)
        assert tuple(store.iter_keys(pin, "people")) == ()
        state = store._namespace_state_at("people", pin.captured_head)
        assert state is not None and state[0] == 0
        assert store.verify_all()["lazy_records"] == 1


def test_missing_payload_membership_and_tampered_interval_fail_checked_paths(tmp_path):
    path = tmp_path / "save.sqlite"
    with make_store(path) as store:
        pin = store.capture_pin()
        pin = commit(
            store,
            pin,
            "g1",
            (VersionChange("people", 1, "Ada", memberships=(Membership("alive", True, 0),)),),
        ).pin
        typed_key = store.codec.encode(1)
        store.db.execute(
            "DELETE FROM lazy_record_versions WHERE namespace='people' AND typed_key=?", (typed_key,)
        )
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="absent lazy record"):
            store.read_version(pin, "people", 1, expected_record_schema=1)

    path2 = tmp_path / "membership.sqlite"
    with make_store(path2) as store:
        pin = store.capture_pin()
        pin = commit(
            store,
            pin,
            "g1",
            (VersionChange("people", 1, "Ada", memberships=(Membership("alive", True, 0),)),),
        ).pin
        store.db.execute("DELETE FROM lazy_query_versions")
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="incomplete"):
            store.verify_all()

    path_update = tmp_path / "corrupt-update.sqlite"
    with make_store(path_update) as store:
        pin = store.capture_pin()
        pin = commit(
            store,
            pin,
            "g1",
            (VersionChange("people", 1, "Ada", memberships=(Membership("alive", True, 0),)),),
        ).pin
        store.db.execute("DELETE FROM lazy_query_versions")
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="membership"):
            commit(store, pin, "g2", (VersionChange("people", 1, "Ada 2"),), position=2)
        assert store.generation == 1

    path3 = tmp_path / "interval.sqlite"
    with make_store(path3) as store:
        pin = store.capture_pin()
        pin = commit(store, pin, "g1", (VersionChange("people", 1, "Ada"),)).pin
        store.db.execute("UPDATE lazy_record_versions SET valid_to=99 WHERE namespace='people'")
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match="checksum"):
            store.read_version(pin, "people", 1, expected_record_schema=1)


def test_keyset_iteration_obeys_128_cap_and_preserves_typed_order(tmp_path):
    with make_store(tmp_path / "save.sqlite") as store:
        pin = store.capture_pin()
        changes = tuple(VersionChange("people", i, {"i": i}) for i in range(300))
        pin = commit(store, pin, "bulk", changes).pin
        assert tuple(store.iter_keys(pin, "people", page_size=128)) == tuple(range(300))
        assert tuple(store.iter_keys(pin, "people", page_size=17)) == tuple(range(300))
        with pytest.raises(ValueError):
            store.iter_keys(pin, "people", page_size=129)
        with pytest.raises(ValueError):
            store.iter_keys(pin, "people", page_size=0)


def test_noop_does_not_advance_or_replace_receipt(tmp_path):
    with make_store(tmp_path / "save.sqlite") as store:
        pin = store.capture_pin()
        store.reset_diagnostics()
        result = store.commit(
            pin,
            commit_token="noop",
            version_changes=(),
            changes=(),
            new_segments=(),
            metadata={"simulation_position": None, "seed": 0, "next_ids": {}, "namespaces": ()},
        )
        assert result.outcome == "not_committed"
        assert result.generation == 0
        assert store.db.execute("SELECT COUNT(*) FROM pin_receipts").fetchone()[0] == 0
        assert store.db.execute("SELECT COUNT(*) FROM pin_attempts").fetchone()[0] == 0
        assert store.diagnostics().payload_writes == 0


def test_single_writer_100_saves_is_bounded_and_never_self_blocks(tmp_path):
    with make_store(tmp_path / "save.sqlite") as store:
        pin = store.capture_pin()
        for i in range(100):
            result = commit(
                store,
                pin,
                f"token-{i}",
                (VersionChange("people", 1, i),),
                position=i + 1,
            )
            assert result.outcome == "committed"
            pin = result.pin
        metrics = store.storage_metrics()
        assert store.generation == 100
        assert metrics["lazy_record_versions"] == 1
        assert metrics["lazy_order_versions"] == 1
        assert metrics["lazy_namespace_versions"] == 1
        assert metrics["pins"] == 1
        assert metrics["receipts"] == 1
        assert metrics["attempts"] == 1
        assert store.read_version(pin, "people", 1, expected_record_schema=1).value == 99
        store.verify_all()


def test_old_pin_allows_one_advance_then_generation_pressure_until_release(tmp_path):
    with make_store(tmp_path / "save.sqlite") as store:
        winner = store.capture_pin()
        loser = store.capture_pin()
        first = commit(store, winner, "g1", (VersionChange("people", 1, 1),), position=1)
        winner = first.pin
        assert first.generation == 1
        with pytest.raises(GenerationPressureError) as exc:
            commit(store, winner, "g2-blocked", (VersionChange("people", 1, 2),), position=2)
        assert (exc.value.head_generation, exc.value.minimum_pinned_generation) == (1, 0)
        assert store.generation == 1
        store.release_pin(loser)
        second = commit(store, winner, "g2", (VersionChange("people", 1, 2),), position=2)
        assert second.generation == 2
        assert store.read_version(second.pin, "people", 1, expected_record_schema=1).value == 2


@pytest.mark.parametrize("n", [1000, 10000])
def test_fixed_query_work_does_not_decode_or_return_irrelevant_history(tmp_path, n):
    with make_store(tmp_path / f"save-{n}.sqlite") as store:
        writer = store.capture_pin()
        rows = [
            VersionChange("people", i, i, memberships=(Membership("bucket", "cold", i),))
            for i in range(n)
        ]
        rows.append(VersionChange("people", "target", 1, memberships=(Membership("bucket", "hot", 0),)))
        writer = commit(store, writer, "bulk", tuple(rows), position=1).pin
        previous = store.capture_pin()
        writer = commit(
            store,
            writer,
            "edit-target",
            (VersionChange("people", "target", 2, memberships=(Membership("bucket", "hot", 0),)),),
            position=2,
        ).pin

        for pin, expected in ((previous, 1), (writer, 2)):
            store.reset_diagnostics()
            assert store.query_keys(pin, "people", "bucket", "hot") == ("target",)
            diag = store.diagnostics()
            assert diag.payload_reads == 0
            assert diag.payload_check_reads == 1
            assert diag.payload_check_bytes > 0
            assert diag.query_rows == 1
            assert store.read_version(pin, "people", "target", expected_record_schema=1).value == expected
        store.reset_diagnostics()
        assert store.query_keys(writer, "people", "bucket", "missing") == ()
        assert store.diagnostics().query_rows == 0
        plan = " ".join(store.query_plan(writer, "people", "bucket", "hot"))
        assert "lazy_query_current" in plan
        assert store.storage_metrics()["lazy_record_versions"] == n + 2
        store.verify_all()


def test_full_scrub_rejects_duplicate_visible_ordinal_and_wrong_head_counts(tmp_path):
    path = tmp_path / "save.sqlite"
    with make_store(path) as store:
        pin = store.capture_pin()
        pin = commit(
            store,
            pin,
            "g1",
            (VersionChange("people", "a", 1), VersionChange("people", "b", 2)),
        ).pin
        key_b = store.codec.encode("b")
        row = store.db.execute(
            "SELECT valid_from FROM lazy_order_versions WHERE namespace='people' AND typed_key=?", (key_b,)
        ).fetchone()
        store.db.execute(
            "UPDATE lazy_order_versions SET ordinal=0 WHERE namespace='people' AND typed_key=? AND valid_from=?",
            (key_b, row[0]),
        )
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            store.verify_all()



def _sqlite_work(store, fn):
    callbacks = 0

    def progress():
        nonlocal callbacks
        callbacks += 1
        return 0

    store.db.set_progress_handler(progress, 10)
    try:
        result = fn()
    finally:
        store.db.set_progress_handler(None, 0)
    return callbacks * 10, result


def test_iter_keys_is_page_lazy_closes_snapshot_before_yield_and_detects_pin_move(tmp_path):
    with make_store(tmp_path / "lazy-iter.sqlite") as store:
        pin = store.capture_pin()
        pin = commit(
            store,
            pin,
            "bulk",
            tuple(
                VersionChange("people", i, {"i": i, "body": "x" * 256})
                for i in range(1000)
            ),
        ).pin

        store.reset_diagnostics()
        iterator = store.iter_keys(pin, "people")
        assert list(islice(iterator, 1)) == [0]
        diag = store.diagnostics()
        assert diag.query_rows <= 128
        assert diag.temporary_keys_peak <= 128
        assert diag.payload_check_reads <= 128
        assert diag.payload_check_bytes > 0
        assert not store.db.in_transaction

        iterator.close()
        boundary = store.iter_keys(pin, "people", page_size=1)
        assert next(boundary) == 0
        assert not store.db.in_transaction
        moved = commit(
            store,
            pin,
            "move-pin",
            (VersionChange("people", 0, {"i": 0, "body": "changed"}),),
            position=2,
        )
        with pytest.raises(StoreConflictError, match="pin moved"):
            next(boundary)
        assert not store.db.in_transaction

        replacement = store.iter_keys(moved.pin, "people", page_size=17)
        assert next(replacement) == 0
        assert not store.db.in_transaction
        replacement.close()
        assert not store.db.in_transaction
        assert tuple(store.iter_keys(moved.pin, "people", page_size=17)) == tuple(range(1000))


@pytest.mark.parametrize("n", [1000, 10000])
def test_generation_specific_query_paths_bound_history_and_measure_actual_body_checks(tmp_path, n):
    with make_store(tmp_path / f"query-history-{n}.sqlite") as store:
        writer = store.capture_pin()
        writer = commit(
            store,
            writer,
            "initial-hot",
            tuple(
                VersionChange(
                    "people",
                    i,
                    {"i": i, "body": "x" * 64},
                    memberships=(Membership("bucket", "hot", i),),
                )
                for i in range(n)
            ),
            position=1,
        ).pin
        previous = store.capture_pin()

        order_steps, ordered = _sqlite_work(
            store, lambda: tuple(store.iter_keys(writer, "people", page_size=128))
        )
        assert ordered == tuple(range(n))

        writer = commit(
            store,
            writer,
            "mostly-cold",
            tuple(
                VersionChange(
                    "people",
                    i,
                    {"i": i, "body": "y" * 64},
                    memberships=(Membership("bucket", "cold", i),),
                )
                for i in range(1, n)
            ),
            position=2,
        ).pin

        store.reset_diagnostics()
        hot_steps, hot = _sqlite_work(
            store, lambda: store.query_keys(writer, "people", "bucket", "hot")
        )
        assert hot == (0,)
        diag = store.diagnostics()
        assert diag.query_rows == 1
        assert diag.payload_reads == 0
        assert diag.payload_check_reads == 1
        assert diag.payload_check_bytes > 0
        assert len(store.query_keys(previous, "people", "bucket", "hot")) == n
        previous_plan = " ".join(store.query_plan(previous, "people", "bucket", "hot"))
        assert "lazy_query_open_generation" in previous_plan
        assert "lazy_query_closed_generation" in previous_plan

        store.release_pin(previous)
        previous = store.capture_pin()
        writer = commit(
            store,
            writer,
            "newer-only",
            tuple(
                VersionChange(
                    "people",
                    n + i,
                    {"i": n + i},
                    memberships=(Membership("newer", True, i),),
                )
                for i in range(n)
            ),
            position=3,
        ).pin
        zero_steps, zero = _sqlite_work(
            store, lambda: store.query_keys(previous, "people", "newer", True)
        )
        assert zero == ()
        assert len(store.query_keys(writer, "people", "newer", True)) == n

        # The exact limits are deliberately loose across SQLite patch releases;
        # scaling must remain indexed rather than proportional to hidden history.
        if n == 1000:
            test_generation_specific_query_paths_bound_history_and_measure_actual_body_checks.small = (
                hot_steps,
                zero_steps,
                order_steps,
            )
        else:
            small_hot, small_zero, small_order = (
                test_generation_specific_query_paths_bound_history_and_measure_actual_body_checks.small
            )
            assert hot_steps <= small_hot * 4 + 500
            assert zero_steps <= small_zero * 4 + 500
            assert order_steps <= small_order * 15 + 5000


def test_checked_iteration_delete_and_reinsert_preserve_both_visible_orders(tmp_path):
    with make_store(tmp_path / "order-versions.sqlite") as store:
        writer = store.capture_pin()
        writer = commit(
            store,
            writer,
            "g1",
            tuple(VersionChange("people", i, i) for i in range(260)),
            position=1,
        ).pin
        previous = store.capture_pin()
        writer = commit(
            store,
            writer,
            "g2",
            (
                VersionChange("people", 10, delete=True),
                VersionChange("people", 20, 20, reinsertion=True),
                VersionChange("people", 260, 260),
            ),
            position=2,
        ).pin
        old = tuple(store.iter_keys(previous, "people", page_size=64))
        new = tuple(store.iter_keys(writer, "people", page_size=64))
        assert old == tuple(range(260))
        assert 10 not in new
        assert new[-2:] == (20, 260)
        assert len(new) == 260
