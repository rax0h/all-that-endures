"""Portable functional checks for the isolated reconstruction diagnostic."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import reconstruction_probe as probe


class ReconstructionTrialTests(unittest.TestCase):
    def setUp(self):
        self.store = object()
        self.pin = SimpleNamespace(captured_head=0)
        self.recorder = Mock()
        self.recorder.measure.side_effect = lambda phase, call: call()
        self.write = Mock()
        self.root = SimpleNamespace(digest=b'\xd3' * 32, count=27)

    def run_trial(self, constructor, component='scope', **kwargs):
        with patch.dict(probe.CONSTRUCTORS, {component: constructor}):
            return probe.sample(
                self.store, self.pin, component, self.recorder, self.write, **kwargs
            )

    def test_pairs_compare_exact_roots_and_counts_inside_the_same_snapshot(self):
        for component in ('scope', 'collection'):
            with self.subTest(component=component):
                self.recorder.reset_mock()
                constructor = Mock(return_value=(self.root,))
                first, repeat = self.run_trial(constructor, component)
                self.assertEqual(first, repeat)
                self.assertEqual(first, [{'digest': 'd3' * 32, 'count': 27}])
                self.assertEqual(
                    [call.args[0] for call in self.recorder.measure.call_args_list],
                    ['first', 'repeat'],
                )
                self.assertEqual([call.args for call in constructor.call_args_list],
                                 [(self.store, 0), (self.store, 0)])

    def test_root_or_count_change_has_no_success_result(self):
        for other in (SimpleNamespace(digest=b'\xd3' * 32, count=26),
                      SimpleNamespace(digest=b'\xd4' * 32, count=27)):
            with self.subTest(other=other):
                self.write.reset_mock()
                constructor = Mock(side_effect=[(self.root,), (other,)])
                with self.assertRaisesRegex(ValueError, 'reconstruction roots differ'):
                    self.run_trial(constructor)
                self.assertEqual([call.args[0] for call in self.write.call_args_list],
                                 ['first', 'repeat'])

    def test_interruption_retains_first_roots_and_never_starts_repeat(self):
        constructor = Mock(return_value=(self.root,))
        with self.assertRaises(probe.ProbeInterrupted):
            self.run_trial(constructor, interrupt=True)
        constructor.assert_called_once_with(self.store, 0)
        self.write.assert_called_once_with('first', [{'digest': 'd3' * 32, 'count': 27}])


if __name__ == '__main__':
    unittest.main()
