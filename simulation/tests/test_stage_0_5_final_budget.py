"""Shared clean budgets release payloads and weak metadata across owners."""
import gc
import importlib
import weakref

import pytest

from simulation.ate_sim.persistence_lazy_sequence import LazyOrderedSequence
from simulation.tests.test_persistence_lazy_store import make_store, metadata


def module(): return importlib.import_module('simulation.ate_sim.persistence_lazy_budget')


class Owner:
    def __init__(self):
        self.clean = {}
        self.dirty = {'private': [1]}
        self.evicted = []

    def _budget_evict(self, key):
        self.clean.pop(key, None)
        self.evicted.append(key)


def admit(budget, owner, key, size):
    owner.clean[key] = bytearray(size)
    return budget.admit(owner, key, size)


def test_byte_and_entry_limits_apply_across_owners_with_global_lru():
    budget = module().SharedCacheBudget(entry_limit=3, byte_limit=100)
    left, right = Owner(), Owner()
    admit(budget, left, 1, 40); admit(budget, left, 2, 40)
    budget.touch(left, 1)
    admit(budget, right, 1, 40)
    assert left.evicted == [2]
    assert set(left.clean) == {1} and set(right.clean) == {1}
    assert budget.diagnostics()['bytes'] == 80
    admit(budget, right, 2, 10); admit(budget, right, 3, 10)
    assert left.evicted == [2, 1]
    assert budget.diagnostics()['entries'] == 3
    assert budget.diagnostics()['bytes'] == 60


def test_oversized_entry_is_not_retained_and_release_keeps_private_dirty_state():
    budget = module().SharedCacheBudget(entry_limit=3, byte_limit=100)
    owner = Owner()
    assert not admit(budget, owner, 1, 101)
    assert owner.clean == {} and budget.diagnostics()['owners'] == 0
    admit(budget, owner, 2, 20); admit(budget, owner, 3, 20)
    budget.release(owner)
    assert owner.clean == {} and owner.dirty == {'private': [1]}
    assert budget.diagnostics()['entries'] == budget.diagnostics()['bytes'] == 0


def test_weak_owner_metadata_does_not_keep_abandoned_payloads_alive():
    budget = module().SharedCacheBudget(entry_limit=64, byte_limit=10000)
    owner = Owner()
    admit(budget, owner, 'page', 100)
    ref = weakref.ref(owner)
    del owner
    gc.collect()
    assert ref() is None
    assert budget.diagnostics()['owners'] == budget.diagnostics()['entries'] == budget.diagnostics()['bytes'] == 0


def test_replacing_cache_entry_and_forgetting_dirty_page_preserve_accounting():
    budget = module().SharedCacheBudget(entry_limit=3, byte_limit=100)
    owner = Owner()
    admit(budget, owner, 1, 40)
    admit(budget, owner, 1, 20)
    assert owner.evicted == [] and budget.diagnostics()['bytes'] == 20
    owner.clean.pop(1)
    budget.forget(owner, 1)
    assert budget.diagnostics()['owners'] == budget.diagnostics()['entries'] == 0


def test_invalid_budgets_or_entry_weights_do_not_mutate_accounting():
    for entries, size in ((0, 1), (1, 0), (True, 10), (1, 1.0)):
        with pytest.raises(ValueError): module().SharedCacheBudget(entry_limit=entries, byte_limit=size)
    budget = module().SharedCacheBudget(entry_limit=2, byte_limit=100)
    owner = Owner()
    for size in (-1, True, 1.5):
        with pytest.raises(ValueError): budget.admit(owner, 1, size)
    assert budget.diagnostics()['entries'] == 0


def test_sequences_share_one_clean_budget_and_acknowledgement_releases_sidecars(tmp_path):
    budget = module().SharedCacheBudget(entry_limit=8, byte_limit=8192)
    with make_store(tmp_path / 'shared.sqlite') as store:
        pin = store.capture_pin()
        sequences = [LazyOrderedSequence(store, pin, inc, initial_values=range(1, 1001), cache_budget=budget)
                     for inc in (1, 2)]
        changes = tuple(v for seq in sequences for v in seq.pending_changes())
        pin = store.commit(pin, commit_token='initial', version_changes=changes, changes=(),
            new_segments=(), metadata=metadata(1, ())).pin
        for seq in sequences: seq.accept_save(pin)
        sequences = [LazyOrderedSequence(store, pin, inc, cache_budget=budget) for inc in (1, 2)]
        for index in range(0, 1000, 17):
            for seq in sequences:
                assert seq[index] == index + 1
                assert sum(len(s._cache) for s in sequences) == budget.diagnostics()['entries']
                assert budget.diagnostics()['entries'] <= 8
                assert budget.diagnostics()['bytes'] <= 8192
        left, right = sequences
        left.insert(500, 2000)
        assert left[500] == 2000 and right[500] == 501
        versions = left.pending_changes()
        pin = store.commit(pin, commit_token='edit', version_changes=versions, changes=(),
            new_segments=(), metadata=metadata(2, ())).pin
        left.accept_save(pin); right.accept_save(pin)
        assert budget.diagnostics()['entries'] == 0
        assert not left._dirty and list(left)[500] == 2000


@pytest.mark.parametrize('kind', ['list', 'map', 'set'])
def test_typed_histories_share_budget_without_retaining_clean_dirty_duplicates(tmp_path, kind):
    history_module = importlib.import_module('simulation.ate_sim.persistence_lazy_nested_history')
    cls = history_module.HISTORY_CLASSES[kind]
    budget = module().SharedCacheBudget(entry_limit=5, byte_limit=16384)
    values = dict.fromkeys(range(500), 'old') if kind == 'map' else range(500)
    with make_store(tmp_path / 'histories.sqlite') as store:
        pin = store.capture_pin()
        histories = [cls(store, pin, inc, initial_values=values, cache_budget=budget) for inc in (1, 2)]
        changes = tuple(change for history in histories for change in history.pending_changes())
        pin = store.commit(pin, commit_token='initial', version_changes=changes, changes=(),
            new_segments=(), metadata=metadata(1, ())).pin
        for history in histories: history.accept_save(pin)
        for index in range(0, 500, 17):
            for history in histories:
                assert (index in history) if kind == 'set' else history[index] == ('old' if kind == 'map' else index)
                assert sum(len(h._cache) for h in histories) == budget.diagnostics()['entries']
                assert budget.diagnostics()['entries'] <= 5
                assert budget.diagnostics()['bytes'] <= 16384
        left, right = histories
        if kind == 'set': left.remove(0)
        else: left[0] = 'changed'
        dirty_keys = left._dirty_pages if kind == 'list' else left._dirty_entries
        assert not set(dirty_keys).intersection(left._cache)
        budget.release(left)
        assert not left._cache and dirty_keys
        assert (0 not in left and 0 in right) if kind == 'set' else (left[0] == 'changed' and right[0] != 'changed')
        pin = store.commit(pin, commit_token='edit', version_changes=left.pending_changes(), changes=(),
            new_segments=(), metadata=metadata(2, ())).pin
        for history in histories: history.accept_save(pin)
        assert budget.diagnostics()['entries'] == budget.diagnostics()['owners'] == 0
        assert not left._baseline_page_bytes if kind == 'list' else not left._baseline_bytes


def test_oversized_history_page_is_streamed_without_clean_sidecars(tmp_path):
    cls = importlib.import_module('simulation.ate_sim.persistence_lazy_nested_history').LazyHistoryList
    budget = module().SharedCacheBudget(entry_limit=2, byte_limit=1024)
    value = 'x' * 2000
    with make_store(tmp_path / 'large-page.sqlite') as store:
        pin = store.capture_pin()
        history = cls(store, pin, 1, initial_values=[value], cache_budget=budget)
        pin = store.commit(pin, commit_token='initial', version_changes=history.pending_changes(), changes=(),
            new_segments=(), metadata=metadata(1, ())).pin
        history.accept_save(pin)
        assert history[0] == value
        assert budget.diagnostics()['entries'] == 0
        assert not history._cache and not history._cache_weights


def test_household_pages_share_history_budget_and_detach_releases_clean_state(tmp_path):
    cls = importlib.import_module('simulation.ate_sim.persistence_lazy_household_members').LazyHouseholdMembers
    history_cls = importlib.import_module('simulation.ate_sim.persistence_lazy_nested_history').LazyHistoryList
    budget = module().SharedCacheBudget(entry_limit=3, byte_limit=16384)
    with make_store(tmp_path / 'households.sqlite') as store:
        pin = store.capture_pin()
        household = cls(store, pin, 1, initial_values=range(1, 501), cache_budget=budget)
        history = history_cls(store, pin, 2, initial_values=range(500), cache_budget=budget)
        pin = store.commit(pin, commit_token='initial', version_changes=(*household.pending_changes(), *history.pending_changes()),
            changes=(), new_segments=(), metadata=metadata(1, ())).pin
        household.accept_save(pin); history.accept_save(pin)
        for index in range(0, 500, 17):
            assert household[index] == index + 1 and history[index] == index
            assert len(household._cache) + len(history._cache) == budget.diagnostics()['entries'] <= 3
        household[0] = 900
        assert not set(household._dirty_pages).intersection(household._cache)
        household.detach_to_memory()
        assert household[0] == 900 and len(household) == 500
        assert not household._cache and not household._cache_weights
        assert budget.diagnostics()['entries'] == len(history._cache)


def test_restoring_typed_pages_releases_cancelled_dirty_baselines(tmp_path):
    cls = importlib.import_module('simulation.ate_sim.persistence_lazy_nested_history').LazyHistoryList
    budget = module().SharedCacheBudget(entry_limit=2, byte_limit=16384)
    with make_store(tmp_path / 'cancelled.sqlite') as store:
        pin = store.capture_pin()
        history = cls(store, pin, 1, initial_values=range(1000), cache_budget=budget)
        pin = store.commit(pin, commit_token='initial', version_changes=history.pending_changes(), changes=(),
            new_segments=(), metadata=metadata(1, ())).pin
        history.accept_save(pin)
        for index in range(0, 1000, 128):
            history[index] = -1
            history[index] = index
        assert history.pending_changes() == ()
        assert not history._dirty_pages and not history._baseline_page_bytes
        assert budget.diagnostics()['entries'] <= 2
