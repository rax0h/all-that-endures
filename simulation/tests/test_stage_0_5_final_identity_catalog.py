"""Checked group completeness, not just checksums on whichever rows survive."""
import importlib

import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreConflictError, RecordChange
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


def test_new_scalar_owner_publishes_mandatory_empty_identity_witness(tmp_path):
    with make_store(tmp_path / 'empty-owner.sqlite') as store:
        pin = groups(store)
        namespace = 'world.currency.minted'
        ordinary = (RecordChange(namespace, 'copper', (0, 7)),)
        cat = catalog().IdentityCatalog(store)
        delta = cat.prepare_delta(pin, (), (), ordinary_changes=ordinary, next_incarnation_id=3)
        pin = store.commit(pin, commit_token='scalar-owner', changes=ordinary,
            version_changes=delta.decode(store.codec)[0], identity_changes=(), next_incarnation_id=3,
            new_segments=(), metadata=metadata(2, (NS, namespace, 'world_identity_links'))).pin
        cat.validate_publication(delta, pin)
        owner = cat.read_owner_identity(pin, (namespace, 'copper'))
        assert tuple(owner.occurrences) == () and owner.storage_kind == 'ordinary'


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
        after = store.diagnostics()
        assert after.payload_reads == before.payload_reads
        assert after.payload_read_bytes == before.payload_read_bytes
        assert after.payload_writes == before.payload_writes
        assert after.query_rows == before.query_rows
        # Checked pin/allocator metadata distinguishes a real no-op from
        # reservations without placements; no owner/group inventory is read.
        assert after.metadata_rows - before.metadata_rows <= 2


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


def test_scalar_acknowledgement_validates_source_owner_commitment(tmp_path):
    module = catalog()
    with make_store(tmp_path / 'wrong-source.sqlite') as store:
        pin = groups(store)
        expected = (VersionChange(NS, 1, 'expected scalar'),)
        delta = module.IdentityCatalog(store).prepare_delta(pin, expected, (), next_incarnation_id=3)
        pin = store.commit(pin, commit_token='wrong-source', changes=(), new_segments=(),
            version_changes=(VersionChange(NS, 1, 'different scalar'),) + delta.decode(store.codec)[0],
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        with pytest.raises(StoreIntegrityError, match='owner/header'):
            module.IdentityCatalog(store).validate_publication(delta, pin)


EAGER_NS = 'world.settlements'


def mixed_catalog(store):
    pin = store.capture_pin()
    versions = (VersionChange(NS, 1, {'shared': [1], 'scalar': 0}),)
    ordinary = (RecordChange(EAGER_NS, 1, {'shared': [1], 'scalar': 0}),)
    placements = (IdentityOccurrenceChange(NS, 1, (('key', 'shared'),), 1),
                  IdentityOccurrenceChange(EAGER_NS, 1, (('key', 'shared'),), 1))
    delta = catalog().initial_catalog_delta(store.codec, versions, placements, ordinary_changes=ordinary,
                                            next_incarnation_id=2, generation=1)
    pin = store.commit(pin, commit_token='mixed', version_changes=versions + delta.decode(store.codec)[0],
        changes=ordinary, new_segments=(), identity_changes=placements, next_incarnation_id=2,
        metadata=metadata(1, (NS, EAGER_NS, 'world_identity_links'))).pin
    return pin


def test_eager_owner_witness_is_pinned_without_using_current_rows_for_old_payloads(tmp_path):
    with make_store(tmp_path / 'mixed.sqlite') as store:
        pin = mixed_catalog(store)
        old = store.capture_pin()
        previous = store.read_owner_identity(old, (EAGER_NS, 1))
        assert previous.storage_kind == 'ordinary' and previous.payload_revision == 1
        ordinary = (RecordChange(EAGER_NS, 1, {'shared': [1], 'scalar': 99}),)
        delta = catalog().IdentityCatalog(store).prepare_delta(pin, (), (), ordinary_changes=ordinary,
                                                              next_incarnation_id=2)
        assert len(delta.decode(store.codec)[0]) == 1  # no unchanged P2C writes
        pin = store.commit(pin, commit_token='scalar', version_changes=delta.decode(store.codec)[0],
            changes=ordinary, new_segments=(), metadata=metadata(2, (NS, EAGER_NS, 'world_identity_links'))).pin
        catalog().IdentityCatalog(store).validate_publication(delta, pin)
        assert store.read_owner_identity(old, (EAGER_NS, 1)) == previous
        current = store.read_owner_identity(pin, (EAGER_NS, 1))
        assert current.payload_revision == 2 and current.payload_commitment != previous.payload_commitment
        assert store.read_identity_group(old, 1).occurrences == store.read_identity_group(pin, 1).occurrences


def test_missing_eager_owner_or_header_is_corruption_not_new_owner(tmp_path):
    with make_store(tmp_path / 'eager-missing.sqlite') as store:
        pin = mixed_catalog(store)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (catalog().OWNER_NAMESPACE, store.codec.encode((EAGER_NS, 1))))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            catalog().IdentityCatalog(store).read_identity_membership(pin, (EAGER_NS, 1), (('key', 'new'),))
        with pytest.raises(StoreIntegrityError):
            catalog().IdentityCatalog(store).prepare_delta(pin, (), (),
                ordinary_changes=(RecordChange(EAGER_NS, 1, {'shared': [1]}),), next_incarnation_id=2)


def test_eager_scalar_ack_rejects_a_different_ordinary_payload(tmp_path):
    with make_store(tmp_path / 'eager-ack.sqlite') as store:
        pin = mixed_catalog(store)
        delta = catalog().IdentityCatalog(store).prepare_delta(pin, (), (),
            ordinary_changes=(RecordChange(EAGER_NS, 1, {'shared': [1], 'scalar': 9}),), next_incarnation_id=2)
        pin = store.commit(pin, commit_token='wrong', version_changes=delta.decode(store.codec)[0],
            changes=(RecordChange(EAGER_NS, 1, {'shared': [1], 'scalar': 10}),), new_segments=(),
            metadata=metadata(2, (NS, EAGER_NS, 'world_identity_links'))).pin
        with pytest.raises(StoreIntegrityError, match='owner/header'):
            catalog().IdentityCatalog(store).validate_publication(delta, pin)


def test_eager_retirement_keeps_old_pin_witness_and_current_group_exact(tmp_path):
    with make_store(tmp_path / 'eager-retired.sqlite') as store:
        pin = mixed_catalog(store)
        old = store.capture_pin()
        ordinary = (RecordChange(EAGER_NS, 1, delete=True),)
        placements = (IdentityOccurrenceChange(EAGER_NS, 1, (('key', 'shared'),), delete=True),)
        delta = catalog().IdentityCatalog(store).prepare_delta(pin, (), placements,
            ordinary_changes=ordinary, next_incarnation_id=2)
        pin = store.commit(pin, commit_token='delete-eager', version_changes=delta.decode(store.codec)[0],
            changes=ordinary, identity_changes=placements, new_segments=(),
            metadata=metadata(2, (NS, EAGER_NS, 'world_identity_links'))).pin
        catalog().IdentityCatalog(store).validate_publication(delta, pin)
        assert not store.read_owner_identity(pin, (EAGER_NS, 1)).exists
        assert store.read_owner_identity(old, (EAGER_NS, 1)).exists
        assert len(store.read_identity_group(pin, 1).occurrences) == 1
        assert len(store.read_identity_group(old, 1).occurrences) == 2


def test_missing_owner_header_and_body_cannot_hide_surviving_placements(tmp_path):
    with make_store(tmp_path / 'missing-all.sqlite') as store:
        pin = mixed_catalog(store)
        store.db.execute('DELETE FROM records WHERE namespace=?', (EAGER_NS,))
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (catalog().OWNER_NAMESPACE, store.codec.encode((EAGER_NS, 1))))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            catalog().IdentityCatalog(store).read_identity_membership(pin, (EAGER_NS, 1), (('key', 'new'),))


def test_in_place_authority_move_is_rejected_without_changing_source(tmp_path):
    with make_store(tmp_path / 'transition.sqlite') as store:
        pin = mixed_catalog(store)
        old = store.capture_pin()
        versions = (VersionChange(EAGER_NS, 1, {'shared': [1], 'scalar': 0}),)
        ordinary = (RecordChange(EAGER_NS, 1, delete=True),)
        # Final-format conversion writes an empty isolated destination, never
        # changes the authority of a live source namespace in place.
        with pytest.raises(ValueError, match='competing'):
            catalog().IdentityCatalog(store).prepare_delta(pin, versions, (), ordinary_changes=ordinary,
                                                          next_incarnation_id=2)
        with pytest.raises(StoreConflictError, match='ordinary record authority'):
            store.commit(pin, commit_token='transition', version_changes=versions,
                changes=ordinary, new_segments=(), metadata=metadata(2, (NS, EAGER_NS, 'world_identity_links')))
        assert store.resolve_commit(pin, 'transition').outcome == 'not_committed'
        assert store.read_owner_identity(pin, (EAGER_NS, 1)).storage_kind == 'ordinary'
        assert store.read_owner_identity(old, (EAGER_NS, 1)).storage_kind == 'ordinary'
        assert store.db.execute('SELECT COUNT(*) FROM records WHERE namespace=?', (EAGER_NS,)).fetchone()[0] == 1
        assert len(store.read_identity_group(old, 1).occurrences) == 2
        assert len(store.read_identity_group(pin, 1).occurrences) == 2
        store.verify_all()
