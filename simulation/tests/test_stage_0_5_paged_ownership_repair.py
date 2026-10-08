"""Ownership transitions use real stores and retained public aliases."""
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import weakref

from ate_sim.core import Household, World
from ate_sim.incremental_store import StoreConflictError, StoreError, StoreIntegrityError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'paged-ownership-repair'

class PagedOwnershipRepair(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def make(self, *, foreign=True, count=260, shared=False):
        world = World(843000)
        world.households[1] = Household(1, 1, list(range(1, count+1)))
        world.households[2] = Household(2, 1, world.households[1].members if shared else [4, 5])
        world.next_household = 3
        if foreign:
            world.currency.wallets[99] = {'members': world.households[1].members}
        cold, target = self.root/'cold.sqlite', self.root/'lazy.sqlite'
        write_cold_snapshot(world, cold, rules_id=RULES)
        convert_cold_to_lazy(cold, target, rules_id=RULES)
        return target

    def open(self, path):
        return open_lazy_world_session(path, rules_id=RULES)

    def test_delete_unloaded_foreign_then_reopen_and_mutate_twice(self):
        path = self.make()
        with self.open(path) as s:
            del s.world.households[1]
            s.save()
        for value in (901, 902):
            with self.open(path) as s:
                held = s.world.currency.wallets[99]['members']
                self.assertEqual(held[:3], [1, 2, 3])
                held.append(value)
                s.save()
                self.assertIs(held, s.world.currency.wallets[99]['members'])
                before = s.pin.captured_head
                self.assertEqual(s.save(), before)
        with self.open(path) as s:
            self.assertEqual(s.world.currency.wallets[99]['members'][-3:], [260, 901, 902])

    def test_replacement_does_not_overwrite_foreign_or_retained_old_alias(self):
        path = self.make()
        with self.open(path) as s:
            old = s.world.households[1].members
            s.world.households[1].members = [7]
            old.append(901)
            s.save()
            self.assertIs(old, s.world.currency.wallets[99]['members'])
            self.assertEqual(s.world.households[1].members, [7])
        with self.open(path) as s:
            self.assertEqual(s.world.households[1].members, [7])
            self.assertEqual(s.world.currency.wallets[99]['members'][-2:], [260, 901])

    def test_shared_merge_then_split_keeps_current_and_external_identity(self):
        path = self.make(foreign=False)
        with self.open(path) as s:
            a, b = s.world.households.values()
            old_b = b.members
            b.members = a.members
            held = a.members
            s.save()
            self.assertIs(a.members, b.members)
            old_b.append(7)
            self.assertEqual(old_b, [4, 5, 7])
            a.members = [8]
            held.append(900)
            s.save()
            self.assertIs(b.members, held)
        with self.open(path) as s:
            self.assertEqual(s.world.households[1].members, [8])
            self.assertEqual(s.world.households[2].members[-2:], [260, 900])

    def test_before_commit_retry_and_lost_ack_preserve_aliases(self):
        for phase in ('before_commit', 'after_commit'):
            with self.subTest(phase=phase):
                # A distinct fixture per fault.
                self.root = self.root / phase
                self.root.mkdir()
                path = self.make()
                with self.open(path) as s:
                    held = s.world.households[1].members
                    s.world.households[2].members = held
                    del s.world.households[1]
                    held.append(901)
                    baseline = s.pin.captured_head
                    self.assertEqual(s.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0], '3')
                    def fault(point):
                        if point == phase:
                            raise RuntimeError('ownership fault')
                    s.store._phase_hook = fault
                    with self.assertRaisesRegex(RuntimeError, 'ownership fault'):
                        s.save()
                    s.store._phase_hook = lambda _: None
                    self.assertEqual(s.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0], '4' if phase == 'after_commit' else '3')
                    if s._state == 'recovery-required':
                        self.assertEqual(s.resolve_save(), baseline + (phase == 'after_commit'))
                    self.assertIs(held, s.world.households[2].members)
                    s.save()
                    self.assertEqual(s.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0], '4')
                with self.open(path) as s:
                    held = s.world.currency.wallets[99]['members']
                    self.assertIs(held, s.world.households[2].members)
                    self.assertEqual(held[-2:], [260, 901])

    def test_foreign_last_owner_deleted_does_not_leave_current_links(self):
        path = self.make()
        with self.open(path) as s:
            held = s.world.households[1].members
            del s.world.currency.wallets[99]
            del s.world.households[1]
            s.save()
            prior = s.pin.captured_head
            held.append(901)
            self.assertEqual(s.save(), prior)
        with self.open(path) as s:
            self.assertNotIn(99, s.world.currency.wallets)
            self.assertNotIn(1, s.world.households)

    def test_merge_without_edit_before_commit_retry_keeps_backing(self):
        path = self.make(foreign=False)
        with self.open(path) as s:
            s.world.households[2].members = s.world.households[1].members
            def fault(point):
                if point == 'before_commit':
                    raise RuntimeError('ownership fault')
            s.store._phase_hook = fault
            with self.assertRaisesRegex(RuntimeError, 'ownership fault'):
                s.save()
            s.store._phase_hook = lambda _: None
            if s._state == 'recovery-required':
                s.resolve_save()
            s.save()
        with self.open(path) as s:
            self.assertIs(s.world.households[1].members, s.world.households[2].members)
            self.assertEqual(s.world.households[1].members[-1], 260)

    def test_descriptor_deletion_fails_closed(self):
        from ate_sim.persistence_lazy_household_members import BACKING_NAMESPACE
        path = self.make()
        with self.open(path) as s:
            s.world.households[1].members.append(901)
            s.save()
            s.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (BACKING_NAMESPACE,))
            s.store.db.commit()
        with self.assertRaises(StoreIntegrityError):
            self.open(path)

    def test_foreign_alias_eviction_reactivation_preserves_identity(self):
        path = self.make()
        with self.open(path) as s:
            del s.world.households[1]
            s.save()
        with self.open(path) as s:
            held = s.world.currency.wallets[99]['members']
            # Accessing enough unrelated buckets evicts the clean owner while
            # the caller retains only its nested sequence.
            for key in range(1000, 1280):
                s.world.currency.wallets[key] = {'gold': key}
            s.save()
        with self.open(path) as s:
            held = s.world.currency.wallets[99]['members']
            for key in range(1000, 1280):
                s.world.currency.wallets[key]
            gc.collect()
            held.append(901)
            self.assertIs(held, s.world.currency.wallets[99]['members'])
            s.save()
        with self.open(path) as s:
            self.assertEqual(s.world.currency.wallets[99]['members'][-2:], [260, 901])

    def test_new_raw_shared_list_remains_shared_after_save(self):
        path = self.make(foreign=False)
        with self.open(path) as s:
            a, b = s.world.households.values()
            values = [7, 8]
            a.members = values
            b.members = a.members
            s.save()
            self.assertIs(a.members, b.members)
        with self.open(path) as s:
            self.assertIs(s.world.households[1].members, s.world.households[2].members)

    def test_scalar_only_edits_do_not_emit_unpublished_references(self):
        path = self.make()
        with self.open(path) as s:
            s.world.households[1].wealth = 3
            s.world.currency.wallets[99]['gold'] = 7
            s.save()
        with self.open(path) as s:
            self.assertEqual(s.world.households[1].members[-1], 260)
            self.assertIs(s.world.households[1].members, s.world.currency.wallets[99]['members'])

    def test_deleted_alias_group_is_collectible(self):
        path = self.make()
        with self.open(path) as s:
            held = s.world.households[1].members
            ref = weakref.ref(held)
            del s.world.currency.wallets[99]
            del s.world.households[1]
            s.save()
            del held
            gc.collect()
            self.assertIsNone(ref())

    def test_inserted_household_retained_field_stays_current(self):
        path = self.make(foreign=False)
        with self.open(path) as s:
            s.world.households[3] = Household(3, 1, [8, 9])
            held = s.world.households[3].members
            s.save()
            self.assertIs(held, s.world.households[3].members)
            held.append(10)
            s.save()
        with self.open(path) as s:
            self.assertEqual(s.world.households[3].members, [8, 9, 10])
            s.world.households[3].members.append(11)
            s.save()
        with self.open(path) as s:
            self.assertEqual(s.world.households[3].members, [8, 9, 10, 11])

    def test_genealogy_owner_survives_household_and_materializes(self):
        world = World(843000)
        world.households[1] = Household(1, 1, [1, 2, 1])
        world.genealogy.children[1] = world.households[1].members
        cold, path = self.root/'cold.sqlite', self.root/'lazy.sqlite'
        write_cold_snapshot(world, cold, rules_id=RULES)
        convert_cold_to_lazy(cold, path, rules_id=RULES)
        with self.open(path) as s:
            self.assertIs(s.world.genealogy.children[1], s.world.households[1].members)
            del s.world.households[1]
            s.save()
        with self.open(path) as s:
            s.world.genealogy.children[1].append(3)
            s.save()
            detached = s.detach(materialize_history=True)
        self.assertEqual(detached.genealogy.children[1], [1, 2, 1, 3])

    def test_orphaned_foreign_append_has_history_independent_io(self):
        observed = []
        root = self.root
        for count in (1000, 10000):
            self.root = root / str(count)
            self.root.mkdir()
            path = self.make(count=count)
            with self.open(path) as s:
                del s.world.households[1]
                s.save()
            with self.open(path) as s:
                s.store.reset_diagnostics()
                held = s.world.currency.wallets[99]['members']
                self.assertEqual(len(held), count)
                self.assertEqual(held.diagnostics()['cached_member_ids'], 0)
                held.append(20001)
                s.save()
                stats = s.store.diagnostics()
                self.assertLessEqual(held.diagnostics()['cached_member_ids'], 512)
                self.assertLess(stats.payload_read_bytes, 10000)
                self.assertLess(stats.payload_write_bytes, 5000)
                observed.append((stats.payload_reads, stats.payload_writes))
            with self.open(path) as s:
                self.assertEqual(s.world.currency.wallets[99]['members'][-1], 20001)
        self.assertEqual(observed[0], observed[1])

    def test_retired_alias_can_be_reinserted_without_changing_identity(self):
        path = self.make(foreign=False)
        with self.open(path) as s:
            held = s.world.households[1].members
            del s.world.households[1]
            s.save()
            held.append(901)
            s.world.households[2].members = held
            self.assertIs(s.world.households[2].members, held)
            self.assertNotIn(99999, held)
            s.save()
            held.append(902)
            s.save()
        with self.open(path) as s:
            self.assertEqual(s.world.households[2].members[-3:], [260, 901, 902])

    def test_current_head_copy_preserves_reference_format_and_aliases(self):
        from ate_sim.persistence_lazy_store import LazyRecordStore
        from ate_sim.persistence_adapters import WorldCodec, SCHEMA
        path = self.make()
        with self.open(path) as s:
            del s.world.households[1]
            s.save()
        copied = self.root / 'copy.sqlite'
        LazyRecordStore.copy_current_head(path, copied,
            codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA, expected_rules_id=RULES)
        with self.open(copied) as s:
            self.assertEqual(s.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0], '4')
            self.assertEqual(s.world.currency.wallets[99]['members'][-1], 260)
            s.world.currency.wallets[99]['members'].append(901)
            s.save()
        with self.open(copied) as s:
            self.assertEqual(s.world.currency.wallets[99]['members'][-2:], [260, 901])

    def test_shared_initial_lists_append_reopen_and_order(self):
        path = self.make(shared=True)
        with self.open(path) as s:
            s.world.households[2].members.append(901)
            s.save()
        with self.open(path) as s:
            a, b = s.world.households.values()
            self.assertIs(a.members, b.members)
            self.assertEqual(a.members[-2:], [260, 901])

    def test_list_operators_and_removed_suffix_membership(self):
        path = self.make(foreign=False)
        with self.open(path) as s:
            a = s.world.households[1]
            a.members = [1, 2]
            s.save()
            self.assertEqual(a.members + [3], [1, 2, 3])
            self.assertEqual([3] + a.members, [3, 1, 2])
            self.assertEqual(a.members * 2, [1, 2, 1, 2])
            self.assertNotEqual(a.members, (1, 2))
        with self.open(path) as s:
            a = s.world.households[1].members
            self.assertNotIn(259, a)
            self.assertEqual(a, [1, 2])

if __name__ == '__main__':
    unittest.main()
