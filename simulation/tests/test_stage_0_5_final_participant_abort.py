"""Thaw only a checked unpublished plan; retain committed/ambiguous journals."""
from dataclasses import replace

import pytest

from simulation.ate_sim.incremental_store import StoreConflictError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.test_stage_0_5_final_sequence_compat import native, store_at
from simulation.tests.test_stage_0_5_final_sequence import publish
from simulation.tests.test_stage_0_5_final_owner_replacement import setup, NS, LEFT, Child
from simulation.tests.test_persistence_lazy_store import make_store, metadata


def fail(phase):
    def hook(actual):
        if actual == phase:
            raise OSError('injected ' + phase)
    return hook


def test_sequence_thaws_failed_attempt_and_retains_dirty_edits_for_retry(tmp_path):
    with store_at(tmp_path / 'sequence.sqlite') as store:
        seq = native(store, [1, 2])
        old = store.capture_pin()
        seq.append(3)
        prepared = seq.prepare_delta()
        store._phase_hook = fail('before_transaction')
        with pytest.raises(OSError):
            store.commit(seq._pin, commit_token='failed',
                version_changes=prepared.decode(store.codec)[0], changes=(), new_segments=(),
                metadata=metadata(2, ()))
        with pytest.raises(StoreConflictError):
            seq.append(4)
        with pytest.raises(StoreConflictError):
            seq.abort_delta(prepared, 'wrong-token')
        with pytest.raises(StoreConflictError):
            seq.abort_delta(replace(prepared, fingerprint='wrong'), 'failed')
        seq.abort_delta(prepared, 'failed')
        assert seq._dirty and seq._prepared is None
        seq.append(4)
        store._phase_hook = lambda phase: None
        publish(seq, 'retry')
        assert list(seq) == [1, 2, 3, 4]
        from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence
        assert list(LazyOrderedSequence(store, old, 1)) == [1, 2]
        seq.scrub()


def test_sequence_lost_ack_cannot_thaw_or_discard_frozen_plan(tmp_path):
    with store_at(tmp_path / 'lost-ack.sqlite') as store:
        seq = native(store, [1, 2])
        seq.append(3)
        prepared = seq.prepare_delta()
        store._phase_hook = fail('after_commit')
        with pytest.raises(OSError):
            store.commit(seq._pin, commit_token='committed',
                version_changes=prepared.decode(store.codec)[0], changes=(), new_segments=(),
                metadata=metadata(2, ()))
        with pytest.raises(StoreConflictError):
            seq.abort_delta(prepared, 'committed')
        assert seq._prepared[0] == prepared and seq._dirty
        store._phase_hook = lambda phase: None
        result = store.resolve_commit(seq._pin, 'committed')
        seq.accept_delta(prepared, result.pin)
        seq.accept_delta(prepared, result.pin)
        assert list(seq) == [1, 2, 3] and not seq._dirty


def test_stale_parent_cannot_thaw_a_failed_plan(tmp_path):
    with store_at(tmp_path / 'stale.sqlite') as store:
        seq = native(store, [1])
        competitor = store.capture_pin()
        seq.append(2)
        prepared = seq.prepare_delta()
        store._phase_hook = fail('before_head')
        with pytest.raises(OSError):
            store.commit(seq._pin, commit_token='failed',
                version_changes=prepared.decode(store.codec)[0], changes=(), new_segments=(),
                metadata=metadata(2, ()))
        store._phase_hook = lambda phase: None
        store.commit(competitor, commit_token='competitor', version_changes=(),
                     changes=(), new_segments=(), metadata=metadata(2, ()))
        with pytest.raises(StoreConflictError):
            seq.abort_delta(prepared, 'failed')
        assert seq._prepared[0] == prepared and seq._dirty


def test_corrupt_attempt_cannot_authorize_thaw(tmp_path):
    with store_at(tmp_path / 'corrupt.sqlite') as store:
        seq = native(store, [1])
        seq.append(2)
        prepared = seq.prepare_delta()
        store._phase_hook = fail('before_head')
        with pytest.raises(OSError):
            store.commit(seq._pin, commit_token='failed',
                version_changes=prepared.decode(store.codec)[0], changes=(), new_segments=(),
                metadata=metadata(2, ()))
        store.db.execute('UPDATE pin_attempts SET row_checksum=? WHERE pin_token=?',
                         ('bad', seq._pin.token))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            seq.abort_delta(prepared, 'failed')
        assert seq._prepared[0] == prepared


def test_coordinator_thaw_retains_overlay_and_retries_exact_current_owner(tmp_path):
    with make_store(tmp_path / 'coordinator.sqlite') as store:
        coord, registry, owners, loads, dirty, installed, original = setup(store)
        first = Child(10)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, first),))
        payloads = (VersionChange(NS, 1, owners[NS, 1]),)
        prepared = coord.prepare_delta(payloads)
        versions, ordinary, placements = prepared.decode(store.codec)
        store._phase_hook = fail('before_commit')
        with pytest.raises(OSError):
            store.commit(coord.pin, commit_token='failed',
                version_changes=payloads + versions, changes=ordinary, new_segments=(),
                identity_changes=placements, next_incarnation_id=registry.next_incarnation,
                metadata=metadata(2, (NS, 'world_identity_links')))
        coord.abort_delta(prepared, 'failed')
        assert coord.placement_overlay and coord.dirty_owners and coord._prepared is None
        second = Child(11)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, second),))
        assert coord.routes_for_mutation(first) == ()
        payloads = (VersionChange(NS, 1, owners[NS, 1]),)
        prepared = coord.prepare_delta(payloads)
        versions, ordinary, placements = prepared.decode(store.codec)
        store._phase_hook = lambda phase: None
        successor = store.commit(coord.pin, commit_token='retry',
            version_changes=payloads + versions, changes=ordinary, new_segments=(),
            identity_changes=placements, next_incarnation_id=registry.next_incarnation,
            metadata=metadata(2, (NS, 'world_identity_links'))).pin
        coord.accept_delta(prepared, successor)
        assert not coord.placement_overlay and not coord.dirty_owners
        assert store.read_version(successor, NS, 1, expected_record_schema=1).value.left.value == 11


def test_unattempted_plan_can_thaw_using_checked_parent_and_prior_ack(tmp_path):
    with store_at(tmp_path / 'unattempted.sqlite') as store:
        seq = native(store, [1])
        seq.append(2)
        prepared = seq.prepare_delta()
        seq.abort_delta(prepared, 'never-attempted')
        seq.append(3)
        assert list(seq) == [1, 2, 3] and seq._prepared is None


def test_advanced_runtime_lease_cannot_misclassify_committed_delta_as_unattempted(tmp_path):
    with store_at(tmp_path / 'advanced-lease.sqlite') as store:
        seq = native(store, [1])
        seq.append(2)
        prepared = seq.prepare_delta()
        result = store.commit(seq._pin, commit_token='committed',
            version_changes=prepared.decode(store.codec)[0], changes=(), new_segments=(),
            metadata=metadata(2, ()))
        # The hybrid publisher advances leases before final runtime acceptance.
        seq._pin = result.pin
        with pytest.raises(StoreConflictError):
            seq.abort_delta(prepared, 'never-attempted')
        assert seq._prepared[0] == prepared and seq._dirty
        seq.accept_delta(prepared, result.pin)
        assert list(seq) == [1, 2]


@pytest.mark.parametrize('kind', ['sequence', 'coordinator'])
def test_unrelated_registered_successor_lease_cannot_acknowledge_plan(tmp_path, kind):
    factory = store_at if kind == 'sequence' else make_store
    with factory(tmp_path / 'lease.sqlite') as store:
        if kind == 'sequence':
            participant = native(store, [1])
            participant.append(2)
            prepared = participant.prepare_delta()
            versions, ordinary, placements = prepared.decode(store.codec)
            pin, allocator = participant._pin, None
            namespaces = ()
        else:
            participant, registry, owners, loads, dirty, installed, original = setup(store)
            participant.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
            payloads = (VersionChange(NS, 1, owners[NS, 1]),)
            prepared = participant.prepare_delta(payloads)
            versions, ordinary, placements = prepared.decode(store.codec)
            versions = payloads + versions
            pin, allocator = participant.pin, registry.next_incarnation
            namespaces = (NS, 'world_identity_links')
        successor = store.commit(pin, commit_token='committed', version_changes=versions,
            changes=ordinary, new_segments=(), identity_changes=placements,
            next_incarnation_id=allocator, metadata=metadata(2, namespaces)).pin
        unrelated = store.capture_pin()
        with pytest.raises(StoreConflictError):
            participant.validate_publication(prepared, unrelated)
        participant.accept_delta(prepared, successor)
