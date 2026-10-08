"""Independent architect probes for frozen e8e216d; no production edits.

Run: PYTHONPATH=simulation:. python simulation/review_stage_0_5_r3_reproductions.py
Expected on the reviewed candidate: two passes, two failures, two errors.
The failures assert required behavior; do not weaken them to bless the candidate.
"""
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ate_sim.core import Household, Person, World
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = "stage-0.5-independent-r3-review"


class FinalRepairReview(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def world(self, people=8):
        world = World(843000)
        world.year = 11
        for key in range(1, people + 1):
            world.people[key] = Person(key, 0, 1, 1, alive=key <= 8)
        world.next_person = people + 1
        world.households[1] = Household(1, 1, list(range(1, 261)))
        world.households[2] = Household(2, 1, [4, 5])
        world.next_household = 3
        return world

    def convert(self, world):
        source, target = self.root / "cold.sqlite", self.root / "lazy.sqlite"
        write_cold_snapshot(world, source, rules_id=RULES)
        convert_cold_to_lazy(source, target, rules_id=RULES)
        return target

    def test_r1_clean_eviction_and_retained_person(self):
        world = self.world(900)
        path = self.convert(world)
        with open_lazy_world_session(path, rules_id=RULES) as session:
            held = session.world.people[1]
            for key in range(1, 901):
                self.assertEqual(session.world.people[key].id, key)
            gc.collect()
            table = session.people
            for name in ("_baseline_payload", "_baseline_presence",
                         "_baseline_incarnation", "_baseline_ordinal"):
                self.assertLessEqual(len(getattr(table, name)), 256)
            # Two resident household member incarnations plus retained person.
            self.assertLessEqual(len(session._registry._occurrences), 259)
            held.wealth += 7
            self.assertIs(session.world.people[1], held)
            session.save()
        with open_lazy_world_session(path, rules_id=RULES) as session:
            self.assertEqual(session.world.people[1].wealth, 7)

    def test_r2_public_digest_guard_and_release(self):
        path = self.convert(self.world())
        with open_lazy_world_session(path, rules_id=RULES) as session:
            world = session.world
            members = world.households[1].members
            def callback(_):
                for action in (lambda: members.append(999), session.close,
                               session.save, world.digest):
                    with self.assertRaises(StoreError):
                        action()
                raise RuntimeError("review callback")
            with patch("ate_sim.core._digest_world_unchecked", callback):
                with self.assertRaisesRegex(RuntimeError, "review callback"):
                    world.digest()
                with world.current_people_scope():
                    with self.assertRaises(StoreError):
                        world.digest()
            self.assertIsNone(session._lifecycle_operation)
            self.assertEqual(len(members), 260)
            self.assertIsInstance(world.digest(), str)

    def test_r3_dynamic_merge_preserves_one_list(self):
        path = self.convert(self.world())
        with open_lazy_world_session(path, rules_id=RULES) as session:
            left, right = session.world.households.values()
            right.members = left.members
            self.assertIs(left.members, right.members)
            session.save()
            self.assertIs(left.members, right.members)
        with open_lazy_world_session(path, rules_id=RULES) as session:
            self.assertIs(session.world.households[1].members,
                          session.world.households[2].members)

    def test_r3_replacement_shrink_removes_old_index_entries(self):
        path = self.convert(self.world())
        with open_lazy_world_session(path, rules_id=RULES) as session:
            session.world.households[1].members = [1]
            session.save()
            self.assertTrue(session.store.verify_all())
        with open_lazy_world_session(path, rules_id=RULES) as session:
            members = session.world.households[1].members
            self.assertEqual(list(members), [1])
            self.assertNotIn(259, members)

    def test_r3_foreign_owner_survives_last_household_deletion(self):
        world = self.world()
        world.currency.wallets[99] = {"members": world.households[1].members}
        path = self.convert(world)
        with open_lazy_world_session(path, rules_id=RULES) as session:
            held = session.world.currency.wallets[99]["members"]
            self.assertIs(held, session.world.households[1].members)
            del session.world.households[1]
            held.append(999)
            expected = list(held)
            session.save()
        with open_lazy_world_session(path, rules_id=RULES) as session:
            self.assertEqual(list(session.world.currency.wallets[99]["members"]),
                             expected)

    def test_r3_source_genealogy_list_alias_contract(self):
        world = self.world()
        world.genealogy.children[1] = world.households[1].members
        path = self.convert(world)
        with open_lazy_world_session(path, rules_id=RULES) as session:
            self.assertIs(session.world.genealogy.children[1],
                          session.world.households[1].members)


if __name__ == "__main__":
    unittest.main(verbosity=2)
