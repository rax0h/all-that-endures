"""Checked owner-local history lookup must scale with the requested household.

The common case is many independent historical households containing the same
person ID. Querying member ID alone loads an unbounded global hit set.
"""
import pytest

from ate_sim.incremental_store import Membership
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange
from ate_sim.persistence_lazy_household_members import (
    LazyHouseholdMembers, LENGTH_NAMESPACE, PAGE_NAMESPACE,
    bootstrap_household_members,
)

RULES = "stage-0.5-owner-scoped-member-occurrences"


@pytest.mark.parametrize("household_count", [1000, 10000])
def test_independent_households_do_not_expand_requested_match_set(
    tmp_path, household_count
):
    store = LazyRecordStore.create(
        tmp_path / "scoped.sqlite",
        codec=WorldCodec(identity_links_recorded=True),
        simulation_schema=SCHEMA, rules_id=RULES,
    )
    try:
        store.db.execute("BEGIN IMMEDIATE")
        try:
            bootstrap_household_members(
                store, 0,
                ((owner, (1, 1, 2)) for owner in range(1, household_count + 1))
            )
            store.db.commit()
        except BaseException:
            store.db.rollback()
            raise
        pin = store.capture_pin()
        try:
            requested = LazyHouseholdMembers(store, pin, 1)
            store.reset_diagnostics()
            assert requested.matching_member_ids((1, 2)) == [1, 1, 2]
            measured = store.diagnostics()
            assert measured.query_rows <= 3
            assert measured.payload_reads <= 2
            assert requested.diagnostics()["resident_cached_pages"] <= 4
            store.reset_diagnostics()
            assert 1 in requested and 55 not in requested
            assert store.diagnostics().query_rows <= 2
        finally:
            store.release_pin(pin)
    finally:
        store.close()


def test_old_schema_one_length_keeps_complete_legacy_fallback(tmp_path):
    store = LazyRecordStore.create(
        tmp_path / "legacy.sqlite",
        codec=WorldCodec(identity_links_recorded=True),
        simulation_schema=SCHEMA, rules_id=RULES,
    )
    try:
        store.db.execute("BEGIN IMMEDIATE")
        try:
            bootstrap_household_members(store, 0, [(1, [3, 7, 3])])
            store.db.commit()
        except BaseException:
            store.db.rollback()
            raise
        pin = store.capture_pin()
        outcome = store.commit(
            pin, commit_token=("legacy", 1),
            version_changes=(
                VersionChange(LENGTH_NAMESPACE, 1, 3, record_schema=1),
                VersionChange(
                    PAGE_NAMESPACE, (1, 0), (3, 7, 3),
                    memberships=(
                        Membership("member", 3, 0),
                        Membership("member", 7, 1),
                        Membership("member", 3, 2),
                    ),
                ),
            ),
            changes=(), new_segments=(),
            metadata=store.checked_head().metadata,
        )
        assert outcome.outcome == "committed"
        legacy = LazyHouseholdMembers(store, outcome.pin, 1)
        assert legacy.matching_member_ids([3, 7]) == [3, 7, 3]
        assert 7 in legacy
    finally:
        store.close()


def test_scoped_dirty_pages_override_pinned_index(tmp_path):
    store = LazyRecordStore.create(
        tmp_path / "dirty.sqlite",
        codec=WorldCodec(identity_links_recorded=True),
        simulation_schema=SCHEMA, rules_id=RULES,
    )
    try:
        store.db.execute("BEGIN IMMEDIATE")
        try:
            bootstrap_household_members(store, 0, [(1, [4, 5, 4, 6])])
            store.db.commit()
        except BaseException:
            store.db.rollback()
            raise
        pin = store.capture_pin()
        try:
            seq = LazyHouseholdMembers(store, pin, 1)
            seq[0] = 5
            seq[2] = 7
            seq.append(5)
            assert seq.matching_member_ids([4, 5, 7]) == [5, 5, 7, 5]
            changes = seq.pending_changes()
            outcome = store.commit(
                pin, commit_token=("dirty", 1),
                version_changes=changes, changes=(), new_segments=(),
                metadata=store.checked_head().metadata,
            )
            assert outcome.outcome == "committed"
            seq.accept_save(outcome.pin)
            assert seq.matching_member_ids([4, 5, 7]) == [5, 5, 7, 5]
            reopened = LazyHouseholdMembers(store, outcome.pin, 1)
            assert reopened.matching_member_ids([4, 5, 7]) == [5, 5, 7, 5]
        finally:
            pass
    finally:
        store.close()
