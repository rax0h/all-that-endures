"""Checked retirement ranges, old pins and exact revival in one hybrid commit."""
import importlib
import random
import subprocess
import sys
import textwrap
from dataclasses import replace

import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreFormatError
from simulation.ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange, GenerationPin
from simulation.tests.test_persistence_lazy_store import make_store, metadata, open_store
from simulation.tests.test_stage_0_5_final_identity_catalog import catalog, groups, NS


def ranges():
    return importlib.import_module('simulation.ate_sim.persistence_lazy_identity_retired')


def save_ranges(store, editor, token):
    versions = editor.pending_changes()
    result = store.commit(editor.pin, commit_token=token, version_changes=versions,
        identity_changes=(), changes=(), new_segments=(),
        metadata=metadata(editor.pin.captured_head + 1, ()))
    return ranges().RetiredIdentityRanges(store, result.pin)


def test_coalescing_and_split_preserve_checked_old_pin(tmp_path):
    with make_store(tmp_path / 'ranges.sqlite') as store:
        tree = ranges().RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        for inc in (1, 3, 2, 6, 5, 4): tree.add(inc)
        assert tree.intervals() == ((1, 6),)
        tree = save_ranges(store, tree, 'initial')
        old = ranges().RetiredIdentityRanges(store, store.capture_pin())
        tree.remove(3)
        assert tree.intervals() == ((1, 2), (4, 6))
        tree = save_ranges(store, tree, 'split')
        assert old.contains(3) and not tree.contains(3)
        tree.scrub(); old.scrub()
        tree.add(3)
        assert tree.intervals() == ((1, 6),)
        tree.remove(1); tree.remove(6)
        assert tree.intervals() == ((2, 5),)


def test_range_differential_insert_remove_and_reopen(tmp_path):
    with make_store(tmp_path / 'trace.sqlite') as store:
        tree = ranges().RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        expected = set()
        rng = random.Random(843000)
        for step in range(240):
            inc = rng.randrange(1, 150)
            if rng.randrange(2): tree.add(inc); expected.add(inc)
            else: tree.remove(inc); expected.discard(inc)
            assert {n for lo, hi in tree.intervals() for n in range(lo, hi + 1)} == expected
            if step % 40 == 39:
                tree = save_ranges(store, tree, f'trace-{step}')
                tree.scrub()
        assert all(tree.contains(n) == (n in expected) for n in range(1, 151))


@pytest.mark.parametrize('count', [1000, 10000])
def test_one_range_change_reads_and_writes_only_local_paths(tmp_path, count):
    with make_store(tmp_path / 'local.sqlite') as store:
        tree = ranges().RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        for n in range(1, count * 3, 3): tree.add(n)
        tree = save_ranges(store, tree, 'initial')
        before = store.diagnostics()
        target = count * 3 // 2 + 2
        assert not tree.contains(target)
        tree.add(target)
        changes = tree.pending_changes()
        assert any(v.namespace == ranges().NODE_NAMESPACE and not v.delete for v in changes)
        assert len(changes) < 100
        assert store.diagnostics().payload_reads - before.payload_reads < 100
        assert tree.diagnostics()['clean_entries'] <= 64
        # Dirty reporting must include the actual retained node objects, not
        # just the shallow size of the journal dictionaries.
        assert tree.diagnostics()['dirty_bytes'] >= (sys.getsizeof(tree._dirty)
            + sum(sys.getsizeof(node) for node in tree._dirty.values()))
        tree = save_ranges(store, tree, 'edit')
        assert tree.contains(target)
        tree.scrub()


def test_missing_and_extra_range_nodes_are_corruption(tmp_path):
    mod = ranges()
    with make_store(tmp_path / 'corrupt.sqlite') as store:
        tree = mod.RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        for n in (1, 4, 7): tree.add(n)
        tree = save_ranges(store, tree, 'initial')
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (mod.NODE_NAMESPACE,))
        store.db.commit()
        tree = mod.RetiredIdentityRanges(store, tree.pin)
        with pytest.raises(StoreIntegrityError): tree.contains(4)
    with make_store(tmp_path / 'extra.sqlite') as store:
        tree = mod.RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        tree.add(1)
        tree = save_ranges(store, tree, 'initial')
        pin = store.commit(tree.pin, commit_token='extra',
            version_changes=(VersionChange(mod.NODE_NAMESPACE, 99, ('unused',)),),
            changes=(), new_segments=(), metadata=metadata(2, ())).pin
        with pytest.raises(StoreIntegrityError): mod.RetiredIdentityRanges(store, pin).scrub()


def retire(store, pin, *, protected=(), limit=256, token='retire'):
    cat = catalog().IdentityCatalog(store)
    delta = cat.prepare_retirement_delta(pin, protected_incarnations=protected, row_budget=limit)
    successor = store.commit(pin, commit_token=token, version_changes=delta.decode(store.codec)[0],
        changes=(), new_segments=(), metadata=metadata(pin.captured_head + 1, (NS, 'world_identity_links'))).pin
    cat.validate_publication(delta, successor)
    return successor, delta


def test_retired_header_absence_is_proved_and_live_or_protected_id_is_not_reclaimed(tmp_path):
    with make_store(tmp_path / 'catalog.sqlite') as store:
        cat = catalog().IdentityCatalog(store)
        pin = groups(store)
        placements = tuple(IdentityOccurrenceChange(NS, n, (), delete=True) for n in (1, 2))
        delta = cat.prepare_delta(pin, (), placements, next_incarnation_id=3)
        pin = store.commit(pin, commit_token='empty', version_changes=delta.decode(store.codec)[0],
            identity_changes=placements, changes=(), new_segments=(), metadata=metadata(2, (NS, 'world_identity_links'))).pin
        old = store.capture_pin()
        # Advance the retention floor to the generation that removed placements.
        pin = store.commit(pin, commit_token='advance', version_changes=(), changes=(),
            new_segments=(), metadata=metadata(3, (NS, 'world_identity_links'))).pin
        delta = cat.prepare_retirement_delta(pin, protected_incarnations=(1,))
        assert not any(v.namespace == catalog().GROUP_NAMESPACE and v.delete for v in delta.decode(store.codec)[0])
        store.release_pin(old)
        pin, delta = retire(store, pin, token='retire-now')
        assert any(v.namespace == catalog().GROUP_NAMESPACE and v.key == 1 and v.delete for v in delta.decode(store.codec)[0])
        assert store.read_identity_group(pin, 1).occurrences == ()
        assert len(store.read_identity_group(pin, 2).occurrences) == 2
        store.verify_all()


def test_retirement_respects_floor_and_old_pin_witness_then_revives_same_id(tmp_path):
    with make_store(tmp_path / 'revival.sqlite') as store:
        cat = catalog().IdentityCatalog(store)
        pin = groups(store)
        old = store.capture_pin()
        placements = tuple(IdentityOccurrenceChange(NS, n, (), delete=True) for n in (1, 2))
        delta = cat.prepare_delta(pin, (), placements, next_incarnation_id=3)
        pin = store.commit(pin, commit_token='empty', version_changes=delta.decode(store.codec)[0],
            identity_changes=placements, changes=(), new_segments=(), metadata=metadata(2, (NS, 'world_identity_links'))).pin
        delta = cat.prepare_retirement_delta(pin)
        assert not any(v.namespace == catalog().GROUP_NAMESPACE and v.delete for v in delta.decode(store.codec)[0])
        assert len(store.read_identity_group(old, 1).occurrences) == 2
        store.release_pin(old)
        pin, delta = retire(store, pin, token='eligible')
        assert store.read_identity_group(pin, 1).occurrences == ()
        placements = (IdentityOccurrenceChange(NS, 1, (), 1),)
        delta = cat.prepare_delta(pin, (), placements, next_incarnation_id=3)
        pin = store.commit(pin, commit_token='revive', version_changes=delta.decode(store.codec)[0],
            identity_changes=placements, changes=(), new_segments=(), metadata=metadata(4, (NS, 'world_identity_links'))).pin
        cat.validate_publication(delta, pin)
        assert store.read_identity_group(pin, 1).occurrences == ((NS, 1, ()),)
        assert not ranges().RetiredIdentityRanges(store, pin).contains(1)


def test_unproved_missing_header_and_tampered_retirement_commitment_are_corruption(tmp_path):
    with make_store(tmp_path / 'missing.sqlite') as store:
        pin = groups(store)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
            (catalog().GROUP_NAMESPACE, store.codec.encode(1)))
        store.db.commit()
        with pytest.raises(StoreIntegrityError): store.read_identity_group(pin, 1)


@pytest.mark.parametrize('corruption', ['missing', 'payload'])
def test_full_range_scrub_bypasses_warmed_nodes(tmp_path, corruption):
    mod = ranges()
    with make_store(tmp_path / 'warm.sqlite') as store:
        tree = mod.RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        tree.add(1); tree.add(4)
        tree = save_ranges(store, tree, 'initial')
        assert tree.contains(1)
        if corruption == 'missing':
            store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (mod.NODE_NAMESPACE,))
        else:
            store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=? AND typed_key=?',
                (b'corrupt', mod.NODE_NAMESPACE, store.codec.encode(tree.root[0])))
        store.db.commit()
        with pytest.raises(StoreIntegrityError): tree.scrub()


def test_initial_directory_cannot_overwrite_existing_authority(tmp_path):
    mod = ranges()
    with make_store(tmp_path / 'reset.sqlite') as store:
        tree = mod.RetiredIdentityRanges(store, store.capture_pin(), initial=True)
        tree.add(1)
        tree = save_ranges(store, tree, 'initial')
        with pytest.raises(StoreIntegrityError): mod.RetiredIdentityRanges(store, tree.pin, initial=True)


def test_catalog_churn_reclaims_headers_into_one_range_with_bounded_plans(tmp_path):
    mod = catalog()
    with make_store(tmp_path / 'churn.sqlite') as store:
        pin = store.capture_pin()
        initial = mod.initial_catalog_delta(store.codec, (), (), next_incarnation_id=601, generation=1)
        pin = store.commit(pin, commit_token='reserved', version_changes=initial.decode(store.codec)[0],
            changes=(), new_segments=(), next_incarnation_id=601,
            metadata=metadata(1, (NS, 'world_identity_links'))).pin
        for step in range(3):
            pin, delta = retire(store, pin, token=f'retire-{step}')
            versions = delta.decode(store.codec)[0]
            assert len(versions) <= 256
            assert any(v.namespace == mod.GROUP_NAMESPACE and v.delete for v in versions)
            store.verify_all()
        assert store.namespace_size(pin, mod.GROUP_NAMESPACE) == 0
        tree = ranges().RetiredIdentityRanges(store, pin)
        assert tree.intervals() == ((1, 600),)
        assert store.namespace_size(pin, ranges().NODE_NAMESPACE) == 1
        assert all(store.read_identity_group(pin, n).occurrences == () for n in (1, 128, 300, 600))
        tree.scrub()


def test_retired_range_missing_mandatory_node_or_root_is_corruption(tmp_path):
    mod = catalog()
    with make_store(tmp_path / 'catalog-corrupt.sqlite') as store:
        pin = store.capture_pin()
        initial = mod.initial_catalog_delta(store.codec, (), (), next_incarnation_id=3, generation=1)
        pin = store.commit(pin, commit_token='reserved', version_changes=initial.decode(store.codec)[0],
            changes=(), new_segments=(), next_incarnation_id=3,
            metadata=metadata(1, (NS, 'world_identity_links'))).pin
        pin, _ = retire(store, pin)
        store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (ranges().NODE_NAMESPACE,))
        store.db.commit()
        with pytest.raises(StoreIntegrityError): store.read_identity_group(pin, 1)


def test_legacy_catalog_stays_in_compatibility_mode_without_hidden_upgrade(tmp_path):
    mod = catalog()
    with make_store(tmp_path / 'legacy.sqlite') as store:
        pin = store.capture_pin()
        owners = (VersionChange(NS, 1, 'old payload'),)
        placements = (IdentityOccurrenceChange(NS, 1, (), 1),)
        initial = mod.initial_catalog_delta(store.codec, owners, placements, next_incarnation_id=2, generation=1)
        versions = []
        for v in initial.decode(store.codec)[0]:
            if v.namespace == ranges().NODE_NAMESPACE: continue
            if v.namespace == mod.RETIRED_NAMESPACE:
                v = replace(v, value=('identity-retired-directory/v1', 0, None))
            if v.namespace == mod.CATALOG_NAMESPACE:
                v = replace(v, value=('identity-catalog/v1', mod.LEGACY_FEATURES, 2, 1,
                                     ('identity-retired-directory/v1', 0, None)))
            versions.append(v)
        pin = store.commit(pin, commit_token='legacy', version_changes=owners + tuple(versions),
            identity_changes=placements, next_incarnation_id=2, changes=(), new_segments=(),
            metadata=metadata(1, (NS, 'world_identity_links'))).pin
        cat = mod.IdentityCatalog(store)
        assert len(cat.read_identity_group(pin, 1).occurrences) == 1
        with pytest.raises(StoreFormatError, match='explicit copy upgrade'):
            cat.prepare_retirement_delta(pin)
        changed = (VersionChange(NS, 1, 'new scalar'),)
        delta = cat.prepare_delta(pin, changed, (), next_incarnation_id=2)
        pin = store.commit(pin, commit_token='scalar', version_changes=changed + delta.decode(store.codec)[0],
            changes=(), new_segments=(), metadata=metadata(2, (NS, 'world_identity_links'))).pin
        cat.validate_publication(delta, pin)
        assert cat._descriptor(pin)[0] == 'identity-catalog/v1'
        assert store._namespace_state_at(ranges().NODE_NAMESPACE, pin.captured_head) is None


def test_allocator_only_reservations_get_mandatory_headers_and_can_be_retired(tmp_path):
    mod = catalog()
    with make_store(tmp_path / 'reserved.sqlite') as store:
        pin = groups(store)
        delta = mod.IdentityCatalog(store).prepare_delta(pin, (), (), next_incarnation_id=6)
        assert {v.key for v in delta.decode(store.codec)[0] if v.namespace == mod.GROUP_NAMESPACE} == {3, 4, 5}
        pin = store.commit(pin, commit_token='reserve', version_changes=delta.decode(store.codec)[0],
            next_incarnation_id=6, changes=(), new_segments=(), metadata=metadata(2, (NS, 'world_identity_links'))).pin
        mod.IdentityCatalog(store).validate_publication(delta, pin)
        pin, _ = retire(store, pin)
        assert ranges().RetiredIdentityRanges(store, pin).intervals() == ((3, 5),)
        assert store.read_identity_group(pin, 3).occurrences == ()


@pytest.mark.parametrize('phase', ['during_version_writes', 'before_commit', 'after_commit'])
def test_retirement_subprocess_death_recovers_complete_old_or_new_authority(tmp_path, phase):
    mod = catalog()
    path = tmp_path / 'death.sqlite'
    with make_store(path) as store:
        pin = store.capture_pin()
        delta = mod.initial_catalog_delta(store.codec, (), (), next_incarnation_id=6, generation=1)
        pin = store.commit(pin, commit_token='initial', version_changes=delta.decode(store.codec)[0],
            changes=(), new_segments=(), next_incarnation_id=6,
            metadata=metadata(1, (NS, 'world_identity_links'))).pin
        initial_token = pin.token
    worker = textwrap.dedent('''
        import os, signal, sys
        from simulation.tests.test_persistence_lazy_store import open_store, metadata
        from simulation.ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
        with open_store(sys.argv[1]) as store:
            pin = store.capture_pin()
            delta = IdentityCatalog(store).prepare_retirement_delta(pin)
            store._phase_hook = lambda p: os.kill(os.getpid(), signal.SIGKILL) if p == sys.argv[2] else None
            store.commit(pin, commit_token='death', version_changes=delta.decode(store.codec)[0],
                changes=(), new_segments=(), metadata=metadata(2, ('world.people','world_identity_links')))
    ''')
    result = subprocess.run([sys.executable, '-c', worker, str(path), phase], capture_output=True, text=True)
    assert result.returncode == -9, result.stderr
    with open_store(path) as store:
        token = store.db.execute('SELECT token FROM generation_pins WHERE token != ?', (initial_token,)).fetchone()[0]
        resolved = store.resolve_commit(GenerationPin(token, store.store_identity, 1), 'death')
        assert resolved.outcome == ('committed' if phase == 'after_commit' else 'not_committed')
        pin = store.capture_pin()
        assert store.namespace_size(pin, mod.GROUP_NAMESPACE) == (0 if phase == 'after_commit' else 5)
        assert ranges().RetiredIdentityRanges(store, pin).intervals() == (((1, 5),) if phase == 'after_commit' else ())
        assert store.read_identity_group(pin, 1).occurrences == ()
        ranges().RetiredIdentityRanges(store, pin).scrub()
        store.verify_all()
