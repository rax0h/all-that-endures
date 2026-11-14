"""Closed metadata reuse preserves real family and dependency publication."""
from ate_sim.core import Person
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_participants import FamilySaveParticipant
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

def test_native_family_acknowledgement_bounds_head_checks(tmp_path, monkeypatch):

    def setup(w):
        for pid in range(1, 33):
            w.people[pid] = Person(pid, -30, 1, 1, age=30)
        w.next_person = 33
    path, pair = ranked_fixture(tmp_path, size=4, configure=setup)
    cls = FamilySaveParticipant
    orig = cls.validate_publication
    head = LazyRecordStore._checked_head_row
    counts = []
    active = False

    def counted(*a, **kw):
        if active:
            counts[-1] += 1
        return head(*a, **kw)

    def validate(*a, **kw):
        nonlocal active
        active = True
        counts.append(0)
        try:
            return orig(*a, **kw)
        finally:
            active = False
    monkeypatch.setattr(cls, 'validate_publication', validate)
    monkeypatch.setattr(LazyRecordStore, '_checked_head_row', counted)
    with fast_open(path, pair) as session:
        for pid in range(1, 33):
            session.world.people[pid].wealth += 0.125
        session.save()
        assert getattr(session.store, '_validation_scope', None) is None
        saved = session.proof_manifest
        assert counts and max(counts) <= 10, counts
    with fast_open(path, saved) as restored:
        assert all((restored.world.people[pid].wealth == 0.125 for pid in range(1, 33)))

def test_dependency_validation_bounds_head_checks(tmp_path, monkeypatch):
    from simulation.tests.test_persistence_lazy_store import make_store, metadata
    from simulation.ate_sim.persistence_history_dependencies import BackingDependencyPool as Pool, active_backing_dependencies
    from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList
    from simulation.ate_sim.persistence_lazy_store import LazyRecordStore as Store
    with make_store(tmp_path / 'dependency.sqlite') as store:
        pool = Pool(store, store.capture_pin())
        aliases = [LazyHistoryList(store, pool.pin, inc, initial_values=[inc]) for inc in range(1, 33)]
        for alias in aliases:
            pool.acquire(alias)
        delta = pool.prepare_delta()
        changes = tuple((c for alias in aliases for c in alias.pending_changes())) + delta.decode(store.codec)[0]
        result = store.commit(pool.pin, commit_token='dependency-work', version_changes=changes, changes=(), new_segments=(), metadata=metadata(1, ()))
        original = Store._checked_head_row
        heads = []

        def counted(*a, **kw):
            heads.append(1)
            return original(*a, **kw)
        with monkeypatch.context() as patch:
            patch.setattr(Store, '_checked_head_row', counted)
            pool.validate_publication(delta, result.pin)
        assert len(heads) <= 10, len(heads)
        assert getattr(store, '_validation_scope', None) is None
        pool.accept_delta(delta, result.pin)
        assert all((active_backing_dependencies(store, result.pin, inc) == (pool.token,) for inc in range(1, 33)))
