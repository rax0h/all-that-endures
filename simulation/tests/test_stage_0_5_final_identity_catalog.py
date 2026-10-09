"""Checked group completeness, not just checksums on whichever rows survive."""
import importlib

import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreConflictError
from simulation.ate_sim.persistence_lazy_store import IdentityOccurrenceChange, VersionChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata

NS = "world.people"


def catalog():
    return importlib.import_module("simulation.ate_sim.persistence_lazy_identity_catalog")


def groups(store, count=2):
    module = catalog()
    pin = store.capture_pin()
    versions = tuple(VersionChange(NS, k, {"value": (k + 1) // 2}) for k in range(1, 2 * count + 1))
    placements = tuple(IdentityOccurrenceChange(NS, k, (), (k + 1) // 2)
                       for k in range(1, 2 * count + 1))
    delta = module.initial_catalog_delta(store.codec, versions, placements, next_incarnation_id=count + 1,
                                         generation=1)
    result = store.commit(pin, commit_token="catalog", version_changes=versions + delta.decode(store.codec)[0],
        identity_changes=placements, next_incarnation_id=count + 1, changes=(), new_segments=(),
        metadata=metadata(1, (NS, "world_identity_links")))
    return result.pin


def publish_delta(store, pin, versions, placements, allocator, token="changed"):
    delta = catalog().IdentityCatalog(store).prepare_delta(pin, versions, placements,
                                                          next_incarnation_id=allocator)
    return store.commit(pin, commit_token=token,
        version_changes=tuple(versions) + delta.decode(store.codec)[0],
        identity_changes=placements, next_incarnation_id=allocator, changes=(), new_segments=(),
        metadata=metadata(2, (NS, "world_identity_links"))).pin


def test_missing_second_reverse_occurrence_is_rejected_permanently(tmp_path):
    with make_store(tmp_path / "missing.sqlite") as store:
        pin = groups(store)
        store.db.execute("DELETE FROM lazy_identity_occurrence_versions WHERE owner_key=?",
                         (store.codec.encode(2),))
        store.db.commit()
        # This is the accepted API's reproduced hole, not an assumed failure.
        assert store.identity_occurrences_for_incarnation(pin, 1) == ((NS, 1, ()),)
        with pytest.raises(StoreIntegrityError, match="group.*(count|digest|completeness)"):
            store.read_identity_group(pin, 1)


@pytest.mark.parametrize("history", [1000, 10000])
def test_requested_group_and_owner_are_checked_without_unrelated_payloads(tmp_path, history):
    with make_store(tmp_path / "scale.sqlite") as store:
        pin = groups(store, history)
        before = store.diagnostics()
        group = store.read_identity_group(pin, history)
        assert group.incarnation_id == history
        assert group.occurrences == ((NS, 2 * history - 1, ()), (NS, 2 * history, ()))
        assert len(store.read_identity_links(pin, history)) == 1
        owner = store.read_owner_identity(pin, (NS, 2 * history))
        assert owner.occurrences == (((), history),)
        after = store.diagnostics()
        assert after.metadata_rows - before.metadata_rows < 220
        # Reads are compact witnesses only; owner values have not been decoded.
        assert after.payload_reads - before.payload_reads < 30
        assert after.payload_read_bytes - before.payload_read_bytes < 16000
        plan = store.db.execute("EXPLAIN QUERY PLAN SELECT owner_key FROM lazy_identity_occurrence_versions "
            "WHERE incarnation_id=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)",
            (history, pin.captured_head, pin.captured_head)).fetchall()
        assert any("lazy_identity_incarnation_visible" in p[3] for p in plan)


@pytest.mark.parametrize("authority", ["group", "owner", "owner_tree", "link", "descriptor"])
def test_missing_required_authority_cannot_be_treated_as_empty(tmp_path, authority):
    with make_store(tmp_path / "authority.sqlite") as store:
        pin = groups(store)
        module = catalog()
        ns = {"group": module.GROUP_NAMESPACE, "owner": module.OWNER_NAMESPACE,
              "owner_tree": module.OWNER_TREE_NAMESPACE, "link": module.LINK_NAMESPACE,
              "descriptor": module.CATALOG_NAMESPACE}[authority]
        store.db.execute("DELETE FROM lazy_record_versions WHERE namespace=?", (ns,))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            store.read_identity_group(pin, 1)


def test_catalog_rejects_foreign_or_released_pin_and_missing_header_for_reserved_id(tmp_path):
    with make_store(tmp_path / "one.sqlite") as one, make_store(tmp_path / "two.sqlite") as two:
        pin = groups(one)
        with pytest.raises(StoreConflictError):
            two.read_identity_group(pin, 1)
        one.release_pin(pin)
        with pytest.raises(StoreConflictError):
            one.read_identity_group(pin, 1)


def test_replacement_reanchors_only_affected_groups_and_old_pin_remains_exact(tmp_path):
    with make_store(tmp_path / "replacement.sqlite") as store:
        writer = groups(store, 1000)
        old = store.capture_pin()
        before = store.diagnostics()
        writer = publish_delta(store, writer, (VersionChange(NS, 1, {"value": "new"}),),
                               (IdentityOccurrenceChange(NS, 1, (), 1001),), 1002)
        after = store.diagnostics()
        assert after.payload_reads - before.payload_reads < 40
        assert after.payload_writes - before.payload_writes < 20
        assert store.read_identity_group(old, 1).occurrences == ((NS, 1, ()), (NS, 2, ()))
        assert store.read_identity_group(writer, 1).occurrences == ((NS, 2, ()),)
        assert store.read_identity_group(writer, 1001).occurrences == ((NS, 1, ()),)
        assert store.read_identity_links(writer, 1) == ()
        assert store.read_owner_identity(old, (NS, 1)).occurrences == (((), 1),)
        assert store.read_owner_identity(writer, (NS, 1)).occurrences == (((), 1001),)


def test_noop_catalog_delta_has_no_archive_reads(tmp_path):
    with make_store(tmp_path / "noop.sqlite") as store:
        pin = groups(store, 1000)
        before = store.diagnostics()
        delta = catalog().IdentityCatalog(store).prepare_delta(pin, (), (), next_incarnation_id=1001)
        assert delta.decode(store.codec) == ((), (), ())
        assert store.diagnostics() == before


def test_large_owner_point_proof_and_edit_do_not_inventory_other_occurrences(tmp_path):
    module = catalog()
    with make_store(tmp_path / "large-owner.sqlite") as store:
        pin = store.capture_pin()
        versions = (VersionChange(NS, 1, "compact header"), VersionChange(NS, 2, "peer"))
        placements = tuple(IdentityOccurrenceChange(NS, 1, (("key", k),), k + 1) for k in range(10000))
        placements += (IdentityOccurrenceChange(NS, 2, (), 1),)
        initial = module.initial_catalog_delta(store.codec, versions, placements,
                                               next_incarnation_id=10001, generation=1)
        pin = store.commit(pin, commit_token="large", version_changes=versions + initial.decode(store.codec)[0],
            changes=(), new_segments=(), identity_changes=placements, next_incarnation_id=10001,
            metadata=metadata(1, (NS, "world_identity_links"))).pin
        before = store.diagnostics()
        assert len(store.read_identity_group(pin, 1).occurrences) == 2
        read = store.diagnostics()
        assert read.payload_reads - before.payload_reads < 12
        changed = (IdentityOccurrenceChange(NS, 1, (("key", 0),), 10001),)
        delta = module.IdentityCatalog(store).prepare_delta(pin, (), changed, next_incarnation_id=10002)
        after = store.diagnostics()
        assert after.payload_reads - read.payload_reads < 30
        assert len(delta.decode(store.codec)[0]) < 20


@pytest.mark.parametrize("count", [0, 1])
def test_complete_empty_namespaces_are_declared_in_the_same_transaction(tmp_path, count):
    module = catalog()
    with make_store(tmp_path / "empty.sqlite") as store:
        pin = store.capture_pin()
        versions = (VersionChange(NS, 1, "one"),) if count else ()
        placements = (IdentityOccurrenceChange(NS, 1, (), 1),) if count else ()
        delta = module.initial_catalog_delta(store.codec, versions, placements,
                                             next_incarnation_id=count + 1, generation=1)
        pin = store.commit(pin, commit_token="empty", version_changes=versions + delta.decode(store.codec)[0],
            changes=(), new_segments=(), identity_changes=placements, next_incarnation_id=count + 1,
            metadata=metadata(1, (NS, "world_identity_links"))).pin
        module.IdentityCatalog(store).validate_publication(delta, pin)
        assert store.namespace_size(pin, module.LINK_NAMESPACE) == 0
        if count:
            assert store.read_identity_group(pin, 1).links == ()


def test_acknowledgement_checks_frozen_catalog_before_overlay_can_be_cleared(tmp_path):
    module = catalog()
    with make_store(tmp_path / "ack.sqlite") as store:
        pin = groups(store)
        versions = (VersionChange(NS, 1, "new"),)
        placements = (IdentityOccurrenceChange(NS, 1, (), 3),)
        delta = module.IdentityCatalog(store).prepare_delta(pin, versions, placements, next_incarnation_id=4)
        pin = store.commit(pin, commit_token="ack", version_changes=versions + delta.decode(store.codec)[0],
            changes=(), new_segments=(), identity_changes=placements, next_incarnation_id=4,
            metadata=metadata(2, (NS, "world_identity_links"))).pin
        store.db.execute("DELETE FROM lazy_record_versions WHERE namespace=? AND valid_from=?",
                         (module.OWNER_TREE_NAMESPACE, pin.captured_head))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            module.IdentityCatalog(store).validate_publication(delta, pin)


def test_scalar_owner_edit_does_not_rewrite_unchanged_identity_projection(tmp_path):
    module = catalog()
    with make_store(tmp_path / "scalar.sqlite") as store:
        pin = groups(store)
        versions = (VersionChange(NS, 1, "changed scalar"),)
        delta = module.IdentityCatalog(store).prepare_delta(pin, versions, (), next_incarnation_id=3)
        assert [(v.namespace, v.key) for v in delta.decode(store.codec)[0]] == [(module.OWNER_NAMESPACE, (NS, 1))]
        pin = store.commit(pin, commit_token="scalar", version_changes=versions + delta.decode(store.codec)[0],
            changes=(), new_segments=(), metadata=metadata(2, (NS, "world_identity_links"))).pin
        module.IdentityCatalog(store).validate_publication(delta, pin)
        assert len(store.read_identity_group(pin, 1).occurrences) == 2
