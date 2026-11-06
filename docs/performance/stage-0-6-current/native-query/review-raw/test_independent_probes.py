"""Independent whole-package review probes; not runtime/product test changes."""
import pytest
from simulation.tests.test_stage_0_6_proof_native_query import query_fixture, opened, reset_epoch, NS
from simulation.tests.test_stage_0_5_proof_world_session import fixture
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_lazy_store import _query_checksum


def test_duplicate_current_interval_at_admitted_generation(tmp_path):
    path, pair = query_fixture(tmp_path)
    with opened(path, pair) as session:
        session.world.year = 1
        assert session.save() == 1
        store = session.store
        key, value = store.codec.encode(1), store.codec.encode(True)
        store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',
            (NS, 'alive', value, key, 0, 1, None,
             _query_checksum(NS, 'alive', value, key, 0, 1, None)))
        store.db.commit()
        reset_epoch(store)
        for kwargs in ({}, {'limit': 1}, {'limit': 1, 'exclude_keys': (1,)}):
            with pytest.raises(StoreIntegrityError):
                store.query_memberships(session.pin, NS, 'alive', True, **kwargs)
        with pytest.raises(StoreIntegrityError):
            next(store.iter_query_memberships(session.pin, NS, 'alive', True))
        assert not store.db.in_transaction


def test_large_query_keys_shrink_windows_without_skips(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_native_query as native
    keys = [(1, 10**3950 + i) for i in range(132)]
    def configure(world):
        for key in keys:
            world.communities.memberships[key] = .5
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        store = session.store
        original, windows = native._window, []
        def observed(s, g, scope, after, positions, exhausted):
            windows.append(len(positions))
            return original(s, g, scope, after, positions, exhausted)
        monkeypatch.setattr(native, '_window', observed)
        actual = store.query_memberships(session.pin, 'world.communities.memberships', 'person', 1)
        assert actual == tuple((key, i) for i, key in enumerate(keys))
        assert len(windows) >= 2 and windows[0] < 129
        assert not store.db.in_transaction


def exploratory_unsupported_old_household_projection(tmp_path):
    # Historical failed fixture attempt, retained deliberately but not collected.
    # Complete-format normalization removes this old member_pages projection;
    # querying it correctly returns (). This does not exercise multiplicity.
    from ate_sim.core import Person, Household
    from ate_sim.persistence_lazy_household_members import PAGE_NAMESPACE
    def configure(world):
        world.people[1] = Person(1, 0, 1, 1)
        world.households[1] = Household(1, 1, members=[1, 1])
        world.next_person = world.next_household = 2
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        store = session.store
        actual = store.query_memberships(session.pin, PAGE_NAMESPACE, 'member', 1)
        assert len(actual) == 2
        assert actual[0][0] == actual[1][0]
        assert [ordinal for _, ordinal in actual] == [0, 1]
        assert tuple(store.iter_query_memberships(session.pin, PAGE_NAMESPACE, 'member', 1)) == actual
        assert store.query_memberships(session.pin, PAGE_NAMESPACE, 'member', 1, limit=1) == actual[:1]
        assert store.query_memberships(session.pin, PAGE_NAMESPACE, 'member', 1, exclude_keys=(actual[0][0],)) == ()
