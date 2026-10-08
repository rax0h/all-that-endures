"""Adversarial R3 World commit recovery checks, independent of pilot author."""
import pytest

from ate_sim.incremental_store import StoreError, StoreConflictError
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_paged_household_world import make
from simulation.tests.test_persistence_lazy_people import RULES


def test_paged_household_before_commit_fault_preserves_unsaved_alias(tmp_path, monkeypatch):
    original, path = make(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as session:
        members = session.world.households[1].members
        baseline = session.pin.captured_head
        members.append(7001)
        def fault(phase):
            if phase == "before_commit":
                raise RuntimeError("injected-before-commit")
        monkeypatch.setattr(session.store, "_phase_hook", fault)
        with pytest.raises(RuntimeError, match="injected-before-commit"):
            session.save()
        monkeypatch.setattr(session.store, "_phase_hook", lambda _phase: None)
        if session._state == "recovery-required":
            assert session.resolve_save() == baseline
        assert session.pin.captured_head == baseline
        assert members[-1] == 7001
        assert session.save() == baseline + 1
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as reopened:
        assert reopened.world.households[1].members[-1] == 7001
        assert len(reopened.world.households[1].members) == 1001


def test_paged_household_lost_acknowledgement_reconciles_without_duplicate(tmp_path, monkeypatch):
    original, path = make(tmp_path, 1000)
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as session:
        members = session.world.households[1].members
        prior = session.pin.captured_head
        members.append(8001)
        def fault(phase):
            if phase == "after_commit":
                raise RuntimeError("injected-after-commit")
        monkeypatch.setattr(session.store, "_phase_hook", fault)
        with pytest.raises(RuntimeError, match="injected-after-commit"):
            session.save()
        monkeypatch.setattr(session.store, "_phase_hook", lambda _phase: None)
        assert session._state == "recovery-required"
        assert session.resolve_save() == prior + 1
        assert session.pin.captured_head == prior + 1
        assert members[-1] == 8001
        assert members.count(8001) == 1
        session.store.reset_diagnostics()
        assert session.save() == prior + 1
        assert session.store.diagnostics().payload_writes == 0
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as reopened:
        assert reopened.world.households[1].members[-1] == 8001
        assert reopened.world.households[1].members.count(8001) == 1


def test_paged_household_stale_writer_keeps_local_alias_without_durable_leak(tmp_path):
    original, path = make(tmp_path, 1000)
    winner = open_lazy_world_session(path, rules_id=RULES, paged_household_members=True)
    loser = open_lazy_world_session(path, rules_id=RULES, paged_household_members=True)
    try:
        winner_members = winner.world.households[1].members
        loser_members = loser.world.households[1].members
        winner_members.append(9001)
        loser_members.append(9002)
        generation = winner.pin.captured_head
        assert winner.save() == generation + 1
        with pytest.raises(StoreConflictError):
            loser.save()
        assert loser_members[-1] == 9002
        with pytest.raises((StoreError, StoreConflictError)):
            loser_members.append(9003)
    finally:
        winner.close()
        loser.close()
    with open_lazy_world_session(path, rules_id=RULES, paged_household_members=True) as reopened:
        assert reopened.world.households[1].members[-1] == 9001
        assert 9002 not in reopened.world.households[1].members
