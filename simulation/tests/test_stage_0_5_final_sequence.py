"""Counted order-tree authority and native list behavior, independent of World."""
import importlib
import random
import subprocess
import sys
import textwrap

import pytest

from simulation.ate_sim.incremental_store import StoreConflictError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_store import GenerationPin, VersionChange
from simulation.tests.test_persistence_lazy_store import make_store, metadata, open_store


def module():
    return importlib.import_module('simulation.ate_sim.persistence_lazy_sequence')


def publish(sequence, token):
    delta = sequence.prepare_delta()
    result = sequence._store.commit(sequence._pin, commit_token=token,
        version_changes=delta.decode(sequence._store.codec)[0], changes=(), new_segments=(),
        metadata=metadata(sequence._pin.captured_head + 1, ()))
    sequence.accept_delta(delta, result.pin)
    return result.pin


def sequence(store, values):
    result = module().LazyOrderedSequence(store, store.capture_pin(), 1, initial_values=values)
    publish(result, 'initial')
    return result


@pytest.mark.parametrize('size', [0, 1, 127, 128, 129, 4096, 4097])
def test_conversion_and_checked_scrub(tmp_path, size):
    with make_store(tmp_path / 'sequence.sqlite') as store:
        seq = sequence(store, [k % 11 + 1 for k in range(size)])
        assert list(seq) == [k % 11 + 1 for k in range(size)]
        seq.scrub()
        assert seq.occurrences(3) == tuple(k for k in range(size) if k % 11 == 2)
        before = store.diagnostics()
        assert seq.prepare_delta().decode(store.codec) == ((), (), ())
        after = store.diagnostics()
        # Lifecycle pin checks are permitted; no archive payload/index work.
        assert after.payload_reads == before.payload_reads
        assert after.payload_writes == before.payload_writes
        assert after.metadata_rows == before.metadata_rows


def test_differential_trace_reopen_duplicates_and_numeric_equality(tmp_path):
    with make_store(tmp_path / 'trace.sqlite') as store:
        native = [1, 2, 2, 3] * 40
        seq = sequence(store, native)
        rng = random.Random(843000)
        for step in range(240):
            action = rng.randrange(5)
            index = rng.randrange(-len(native) - 10, len(native) + 10)
            value = rng.randrange(1, 10)
            if action == 0:
                native.insert(index, value); seq.insert(index, value)
            elif action == 1 and native:
                index %= len(native)
                native[index] = value; seq[index] = value
            elif action == 2 and native:
                index %= len(native)
                assert seq.pop(index) == native.pop(index)
            elif action == 3:
                native.append(value); seq.append(value)
            else:
                probe = float(value) if step % 2 else value
                if probe in native:
                    native.remove(probe); seq.remove(probe)
                else:
                    with pytest.raises(ValueError): seq.remove(probe)
            assert list(seq) == native
            if step % 40 == 39:
                pin = publish(seq, f'trace-{step}')
                seq = module().LazyOrderedSequence(store, pin, 1)
                seq.scrub()
        assert seq[:] == native
        assert seq[::-3] == native[::-3]
        assert seq == native
        assert seq != tuple(native)
        if 1 in native:
            native.remove(True); seq.remove(True)
            assert list(seq) == native


def test_repeated_same_gap_splits_then_merges_and_stable_occurrences(tmp_path):
    with make_store(tmp_path / 'gap.sqlite') as store:
        seq = sequence(store, range(1, 5001))
        anchor = seq.occurrence_id(2500)
        for number in range(300): seq.insert(2500, 9000 + number)
        assert seq.rank_of_occurrence(anchor) == 2800
        publish(seq, 'split')
        seq.scrub()
        for number in range(300): del seq[2500]
        assert seq.rank_of_occurrence(anchor) == 2500
        publish(seq, 'merge')
        assert list(seq) == list(range(1, 5001))
        seq.scrub()


@pytest.mark.parametrize('size', [1000, 10000])
def test_one_middle_edit_is_local_and_old_pin_is_exact(tmp_path, size):
    with make_store(tmp_path / 'local.sqlite') as store:
        seq = sequence(store, [1] * size)
        old = module().LazyOrderedSequence(store, store.capture_pin(), 1)
        before = store.diagnostics()
        seq.insert(size // 2, 2)
        delta = seq.prepare_delta()
        changes = delta.decode(store.codec)[0]
        depth = seq.tree_height + 1
        assert sum(v.namespace == module().NODE_NAMESPACE for v in changes) <= 3 * depth + 3
        assert sum(v.namespace == module().LOCATOR_NAMESPACE for v in changes) <= 256
        assert len(changes) < 400
        assert store.diagnostics().payload_reads - before.payload_reads < 350
        assert seq.diagnostics()['clean_entries'] <= 64
        assert seq.diagnostics()['clean_bytes'] <= 8 * 1024 * 1024
        publish(seq, 'middle')
        assert len(old) == size and old[size // 2] == 1
        assert len(seq) == size + 1 and seq[size // 2] == 2
        old.scrub(); seq.scrub()


@pytest.mark.parametrize('authority', ['node', 'parent', 'locator', 'member', 'directory'])
def test_missing_index_authority_is_corruption(tmp_path, authority):
    mod = module()
    with make_store(tmp_path / 'corrupt.sqlite') as store:
        seq = sequence(store, [1, 2, 1] * 60)
        namespace = {'node': mod.NODE_NAMESPACE, 'parent': mod.PARENT_NAMESPACE,
            'locator': mod.LOCATOR_NAMESPACE, 'member': mod.MEMBER_NAMESPACE,
            'directory': mod.DIRECTORY_NAMESPACE}[authority]
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (namespace,))
        store.db.commit()
        seq = mod.LazyOrderedSequence(store, seq._pin, 1)
        with pytest.raises(StoreIntegrityError): seq.occurrences(1)


def test_frozen_plan_failure_retry_and_exact_acknowledgement(tmp_path):
    with make_store(tmp_path / 'frozen.sqlite') as store:
        seq = sequence(store, [1, 2, 3])
        seq.insert(1, 4)
        delta = seq.prepare_delta()
        assert seq.prepare_delta() == delta
        with pytest.raises(StoreConflictError): seq.append(5)
        with pytest.raises(StoreConflictError): seq.accept_delta(delta, seq._pin)
        assert list(seq) == [1, 4, 2, 3]
        result = store.commit(seq._pin, commit_token='retry', changes=(), new_segments=(),
            version_changes=delta.decode(store.codec)[0], metadata=metadata(2, ()))
        seq.accept_delta(delta, result.pin)
        seq.accept_delta(delta, result.pin)
        seq.append(5)
        assert list(seq) == [1, 4, 2, 3, 5]


def test_slice_and_mutating_iterator_follow_list(tmp_path):
    with make_store(tmp_path / 'slices.sqlite') as store:
        seq = sequence(store, list(range(1, 150)))
        native = list(seq)
        seq[10:20] = [7, 8]; native[10:20] = [7, 8]
        seq[::7] = [9] * len(seq[::7]); native[::7] = [9] * len(native[::7])
        del seq[::-9]; del native[::-9]
        assert list(seq) == native
        a, b = iter(seq), iter(native)
        assert next(a) == next(b)
        seq.insert(0, 99); native.insert(0, 99)
        assert list(a) == list(b)
        seq.reverse(); native.reverse()
        seq.sort(); native.sort()
        assert list(seq) == native
        with pytest.raises(ValueError): seq[::2] = []
        with pytest.raises(TypeError): seq.append(True)
        seq.scrub()


@pytest.mark.parametrize('phase', ['before_transaction', 'during_version_writes', 'before_head', 'before_commit', 'after_commit'])
def test_interrupted_commit_keeps_frozen_plan_until_exact_resolution(tmp_path, phase):
    with make_store(tmp_path / 'failure.sqlite') as store:
        seq = sequence(store, [1, 2, 1] * 100)
        seq.insert(150, 7)
        delta = seq.prepare_delta()
        pin = seq._pin
        store._phase_hook = lambda p: (_ for _ in ()).throw(OSError(phase)) if p == phase else None
        with pytest.raises(OSError, match=phase):
            store.commit(pin, commit_token='interrupted', changes=(), new_segments=(),
                version_changes=delta.decode(store.codec)[0], metadata=metadata(2, ()))
        store._phase_hook = lambda p: None
        resolution = store.resolve_commit(pin, 'interrupted')
        assert seq._prepared[0] == delta
        if phase == 'after_commit':
            assert resolution.outcome == 'committed'
            successor = resolution.pin
        else:
            assert resolution.outcome == 'not_committed'
            # The checked receipt protocol requires a fresh attempt token after
            # a resolved non-commit; reuse of the failed token is forbidden.
            successor = store.commit(pin, commit_token='resolved-retry', changes=(), new_segments=(),
                version_changes=delta.decode(store.codec)[0], metadata=metadata(2, ())).pin
        seq.accept_delta(delta, successor)
        assert seq[150] == 7 and len(seq) == 301
        seq.scrub()


def test_full_scrub_rejects_extra_locator_and_point_read_remains_scoped(tmp_path):
    mod = module()
    with make_store(tmp_path / 'extra.sqlite') as store:
        seq = sequence(store, [1, 2, 3])
        result = store.commit(seq._pin, commit_token='extra', changes=(), new_segments=(),
            version_changes=(VersionChange(mod.LOCATOR_NAMESPACE, (1, 10000), (1, 0)),),
            metadata=metadata(2, ()))
        seq = mod.LazyOrderedSequence(store, result.pin, 1)
        assert seq[0] == 1
        with pytest.raises(StoreIntegrityError, match='extra/missing'):
            seq.scrub()


def test_membership_root_count_and_absence_have_directory_proofs(tmp_path):
    mod = module()
    with make_store(tmp_path / 'root.sqlite') as store:
        seq = sequence(store, [1, 2, 1])
        prefix = seq._member_hash(1)
        node = store.read_version(seq._pin, mod.DIRECTORY_NAMESPACE, (1, prefix), expected_record_schema=1).value
        member = node[2]
        # A valid SQLite payload/checksum with an invalid higher-level witness.
        changed = (node[0], node[1], (member[0], member[1] - 1, member[2], member[3]))
        result = store.commit(seq._pin, commit_token='wrong-count', changes=(), new_segments=(),
            version_changes=(VersionChange(mod.DIRECTORY_NAMESPACE, (1, prefix), changed),), metadata=metadata(2, ()))
        seq = mod.LazyOrderedSequence(store, result.pin, 1)
        with pytest.raises(StoreIntegrityError, match='digest'):
            seq.occurrences(1)


def test_delete_to_empty_root_and_failed_mutation_rollback(tmp_path):
    with make_store(tmp_path / 'empty.sqlite') as store:
        seq = sequence(store, [1] * 4200)
        native = list(seq)
        with pytest.raises(TypeError): seq.extend([1, 2, False])
        assert list(seq) == native
        with pytest.raises(IndexError): del seq[999999]
        assert list(seq) == native
        # Explicit bulk removal is allowed to visit the whole affected history.
        del seq[:]
        assert not seq
        seq.scrub()
        publish(seq, 'empty')
        seq.append(8)
        publish(seq, 'again')
        assert list(seq) == [8]
        seq.scrub()


def test_new_backing_must_not_reuse_a_persisted_incarnation(tmp_path):
    with make_store(tmp_path / 'reuse.sqlite') as store:
        seq = sequence(store, [1])
        with pytest.raises(StoreConflictError, match='persisted'):
            module().LazyOrderedSequence(store, seq._pin, 1, initial_values=[2])


def test_full_leaf_and_full_internal_node_split_then_root_collapse(tmp_path):
    with make_store(tmp_path / 'fanout.sqlite') as store:
        seq = sequence(store, [1] * 4096)
        assert seq.tree_height == 1
        seq.insert(0, 2)
        assert seq.tree_height == 2
        seq.scrub()
        publish(seq, 'grow-root')
        del seq[0]
        assert seq.tree_height == 1
        seq.scrub()
        publish(seq, 'shrink-root')
        assert len(seq) == 4096 and seq[0] == 1


def test_failed_projection_read_rolls_back_main_tree_edits(tmp_path):
    mod = module()
    with make_store(tmp_path / 'rollback.sqlite') as store:
        seq = sequence(store, [1, 2, 3] * 60)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (mod.DIRECTORY_NAMESPACE,))
        store.db.commit()
        seq = mod.LazyOrderedSequence(store, seq._pin, 1)
        descriptor = seq._descriptor()
        with pytest.raises(StoreIntegrityError): seq.insert(90, 4)
        assert seq._descriptor() == descriptor
        assert not seq._dirty and not seq._baseline
        assert seq[90] == 1


def test_local_edit_cannot_silently_repair_a_corrupt_moved_locator(tmp_path):
    mod = module()
    with make_store(tmp_path / 'moved.sqlite') as store:
        seq = sequence(store, [1, 2, 3] * 60)
        occurrence = seq.occurrence_id(5)
        result = store.commit(seq._pin, commit_token='bad-locator', changes=(), new_segments=(),
            version_changes=(VersionChange(mod.LOCATOR_NAMESPACE, (1, occurrence), (1, 0)),), metadata=metadata(2, ()))
        seq = mod.LazyOrderedSequence(store, result.pin, 1)
        with pytest.raises(StoreIntegrityError, match='locator'):
            seq.insert(0, 4)


def test_local_branch_edit_cannot_repair_a_corrupt_child_parent(tmp_path):
    mod = module()
    with make_store(tmp_path / 'parent-move.sqlite') as store:
        seq = sequence(store, [1] * 4096)
        root = store.read_version(seq._pin, mod.NODE_NAMESPACE, (1, seq._root[0]), expected_record_schema=1).value
        child = root[1][-1][0]
        result = store.commit(seq._pin, commit_token='bad-parent', changes=(), new_segments=(),
            version_changes=(VersionChange(mod.PARENT_NAMESPACE, (1, child), (seq._root[0], 0)),), metadata=metadata(2, ()))
        seq = mod.LazyOrderedSequence(store, result.pin, 1)
        with pytest.raises(StoreIntegrityError, match='parent'):
            seq.insert(0, 4)


@pytest.mark.parametrize('phase', ['during_version_writes', 'before_commit', 'after_commit'])
def test_subprocess_death_publishes_one_complete_sequence_generation(tmp_path, phase):
    path = tmp_path / 'death.sqlite'
    with make_store(path) as store:
        seq = sequence(store, [1, 2, 3] * 60)
        initial_token = seq._pin.token
    worker = textwrap.dedent('''
        import os, signal, sys
        from simulation.tests.test_persistence_lazy_store import open_store, metadata
        from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence
        with open_store(sys.argv[1]) as store:
            pin = store.capture_pin()
            seq = LazyOrderedSequence(store, pin, 1)
            seq.insert(90, 4)
            delta = seq.prepare_delta()
            store._phase_hook = lambda p: os.kill(os.getpid(), signal.SIGKILL) if p == sys.argv[2] else None
            store.commit(pin, commit_token='death', changes=(), new_segments=(),
                version_changes=delta.decode(store.codec)[0], metadata=metadata(2, ()))
    ''')
    result = subprocess.run([sys.executable, '-c', worker, str(path), phase], capture_output=True, text=True)
    assert result.returncode == -9, result.stderr
    with open_store(path) as store:
        row = store.db.execute('SELECT token FROM generation_pins WHERE token != ?', (initial_token,)).fetchone()
        resolution = store.resolve_commit(GenerationPin(row[0], store.store_identity, 1), 'death')
        assert resolution.outcome == ('committed' if phase == 'after_commit' else 'not_committed')
        seq = module().LazyOrderedSequence(store, store.capture_pin(), 1)
        assert len(seq) == (181 if phase == 'after_commit' else 180)
        assert seq[90] == (4 if phase == 'after_commit' else 1)
        seq.scrub()
        store.verify_all()
