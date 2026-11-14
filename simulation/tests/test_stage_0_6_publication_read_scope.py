"""Closed acknowledgement shares metadata while all physical rows remain checked."""
from ate_sim.core import Person
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.persistence_lazy_participants import CoordinatorSaveParticipant
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open


def test_native_acknowledgement_head_validation_is_bounded_per_operation(tmp_path, monkeypatch):
    def setup(world):
        for pid in range(1, 33):
            world.people[pid] = Person(pid, -30, 1, 1, age=30)
        world.next_person = 33
    path, pair = ranked_fixture(tmp_path, size=4, configure=setup)
    original = CoordinatorSaveParticipant.validate_publication
    head = LazyRecordStore._checked_head_row
    counts = []
    active = False
    def checked_head(*args, **kwargs):
        if active: counts[-1] += 1
        return head(*args, **kwargs)
    def validate(*args, **kwargs):
        nonlocal active
        active = True; counts.append(0)
        try: return original(*args, **kwargs)
        finally: active = False
    monkeypatch.setattr(CoordinatorSaveParticipant, 'validate_publication', validate)
    monkeypatch.setattr(LazyRecordStore, '_checked_head_row', checked_head)
    with fast_open(path, pair) as session:
        for pid in range(1, 33): session.world.people[pid].wealth += .125
        session.save()
        assert counts and max(counts) <= 10, counts
        assert getattr(session.store, '_validation_scope', None) is None
        saved = session.proof_manifest
    with fast_open(path, saved) as restored:
        assert all(restored.world.people[pid].wealth == .125 for pid in range(1, 33))


def test_publication_scope_respects_configured_small_catalog_budget(tmp_path, monkeypatch):
    from simulation.tests.test_stage_0_5_publication_proof_reuse import prepared, make_store
    from simulation.ate_sim.persistence_lazy_participants import CoordinatorSaveParticipant as Participant
    from simulation.ate_sim.persistence_validation_scope import ValidationScope
    with make_store(tmp_path/'budget.sqlite') as store:
        coord, delta, pin = prepared(store)
        coord.catalog.byte_limit = 128
        part = Participant(coord, delta, coord.pin, pin.captured_head)
        seen = []
        original = ValidationScope.remember
        def remember(scope, *args, **kwargs):
            result = original(scope, *args, **kwargs)
            seen.append((scope.byte_limit, scope.bytes))
            return result
        monkeypatch.setattr(ValidationScope, 'remember', remember)
        part.validate_publication(delta, pin)
        assert seen and all(limit <= coord.catalog.byte_limit//6 and size <= limit
                            for limit, size in seen), seen
        assert getattr(store, '_validation_scope', None) is None
