"""Actual hybrid saves acknowledge immutable family/control bytes."""
import importlib

import pytest

from ate_sim.incremental_store import StoreIntegrityError, StoreConflictError
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_persistence_lazy_people import converted_people_store, RULES


def test_world_preparation_uses_family_participants_and_detached_replay(tmp_path):
    destination = converted_people_store(tmp_path, 12, active=3)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.people[1].wealth += 3
        plan = session._prepare_hybrid_save()
        publication = plan.publication
        assert publication.next_incarnation == session._registry.next_incarnation
        assert 'world.people' in {unit.namespace for unit in publication.participants}
        original = publication.replay_plan(plan)
        plan.version_changes[0].value.wealth = 999
        plan.cold_plan.metadata['seed'] = -1
        replay = publication.replay_plan(plan)
        assert replay.version_changes[0].value.wealth == original.version_changes[0].value.wealth
        assert replay.cold_plan.metadata['seed'] == original.cold_plan.metadata['seed']
        replay.version_changes[0].value.wealth = 888
        assert publication.replay_plan(plan).version_changes[0].value.wealth != 888


def test_frozen_publication_replays_original_token_and_generation(tmp_path):
    from dataclasses import replace
    destination = converted_people_store(tmp_path, 12, active=3)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.people[1].wealth += 3
        plan = session._prepare_hybrid_save()
        altered = replace(plan, token='different-token', target_generation=999,
                          cold_plan=replace(plan.cold_plan, token='different-token'))
        replay = plan.publication.replay_plan(altered)
        assert replay.token == replay.cold_plan.token == plan.token
        assert replay.target_generation == plan.target_generation
        assert plan.publication.commit_arguments(altered)['commit_token'] == plan.token


def test_corrupt_failed_attempt_cannot_discard_world_pending_plan(tmp_path):
    destination = converted_people_store(tmp_path, 12, active=3)
    session = open_lazy_world_session(destination, rules_id=RULES)
    commit = session.store.commit
    try:
        session.world.people[1].wealth += 3
        def fail(phase):
            if phase == 'before_head':
                raise OSError('failed transaction')
        def corrupt_failure(pin, **kwargs):
            try:
                return commit(pin, **kwargs)
            except OSError:
                assert session.store.resolve_commit(pin, kwargs['commit_token']).outcome == 'not_committed'
                session.store.db.execute('UPDATE pin_attempts SET row_checksum=? WHERE pin_token=?',
                                         ('bad', pin.token))
                session.store.db.commit()
                raise
        session.store._phase_hook = fail
        session.store.commit = corrupt_failure
        with pytest.raises(StoreIntegrityError):
            session.save()
        assert session._state == 'recovery-required'
        assert session._pending_save is not None
        assert all(not unit.accepted for unit in session._pending_save.publication.participants)
        assert session.people._dirty
    finally:
        # Restore the exact checked row so cleanup can resolve the deliberately
        # retained failure. This does not authorize a corrupt row in production.
        session.store.commit = commit
        session.store._phase_hook = lambda phase: None
        row = session.store.db.execute('SELECT commit_token,parent_generation,state,generation '
                                      'FROM pin_attempts WHERE pin_token=?', (session.pin.token,)).fetchone()
        if row is not None:
            from ate_sim.persistence_lazy_store import _attempt_checksum
            checksum = _attempt_checksum(session.pin.token, *row)
            session.store.db.execute('UPDATE pin_attempts SET row_checksum=? WHERE pin_token=?',
                                     (checksum, session.pin.token))
            session.store.db.commit()
        if session._state == 'recovery-required':
            session.resolve_save()
        session.close()


def test_lost_ack_replays_exact_participant_plan_and_accepts_once(tmp_path):
    destination = converted_people_store(tmp_path, 12, active=3)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.people[1].wealth += 3
        expected = session.world.people[1].wealth
        commit = session.store.commit
        def checked_commit(pin, **kwargs):
            assert kwargs['version_changes'][0].value.wealth == expected
            return commit(pin, **kwargs)
        def lose_ack(phase):
            if phase != 'after_commit':
                return
            plan = session._pending_save
            plan.version_changes[0].value.wealth = 999
            plan.cold_plan.metadata['seed'] = -1
            raise OSError('participant acknowledgement lost')
        session.store.commit = checked_commit
        session.store._phase_hook = lose_ack
        with pytest.raises(OSError, match='participant acknowledgement lost'):
            session.save()
        publication = session._pending_save.publication
        assert all(not unit.accepted for unit in publication.participants)
        session.store.commit = commit
        session.store._phase_hook = lambda phase: None
        successor = session.resolve_save()
        assert all(unit.accepted for unit in publication.participants)
        assert session.resolve_save() == successor
        assert session.save() == successor
    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.people[1].wealth == expected


def test_publication_rejects_wrong_delta_and_wrong_pin_before_acceptance(tmp_path):
    from dataclasses import replace
    destination = converted_people_store(tmp_path, 12, active=3)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.people[1].wealth += 3
        plan = session._prepare_hybrid_save()
        unit = next(unit for unit in plan.publication.participants if unit.namespace == 'world.people')
        with pytest.raises(StoreIntegrityError):
            unit.accept_delta(unit.delta, session.pin)
        with pytest.raises(StoreIntegrityError):
            unit.validate_publication(replace(unit.delta, fingerprint='bad'), session.pin)
        assert not unit.accepted


def test_new_save_source_field_cannot_be_silently_excluded(tmp_path):
    from dataclasses import make_dataclass, fields
    module = importlib.import_module('ate_sim.persistence_lazy_participants')
    destination = converted_people_store(tmp_path, 12, active=3)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        session.world.people[1].wealth += 3
        plan = session._prepare_hybrid_save()
        extended = make_dataclass('ExtendedPlan', [(f.name, object) for f in fields(plan)] +
                                  [('forgotten_version_changes', object)])
        value = extended(**{f.name: getattr(plan, f.name) for f in fields(plan)}, forgotten_version_changes=())
        with pytest.raises(StoreIntegrityError, match='source.*coverage'):
            module.freeze_hybrid_publication(session.store, session.pin, value,
                next_incarnation=session._registry.next_incarnation, required_format_version=5)


def test_superseded_successor_is_stale_before_any_participant_acceptance(tmp_path):
    destination = converted_people_store(tmp_path, 12, active=3)
    first = open_lazy_world_session(destination, rules_id=RULES)
    later = []
    try:
        first.world.people[1].wealth += 3
        captured = []
        def supersede(phase):
            if phase == 'after_commit':
                captured.append(first._pending_save.publication)
                second = open_lazy_world_session(destination, rules_id=RULES)
                later.append(second)
                second.world.people[2].wealth += 5
                second.save()
        first.store._phase_hook = supersede
        with pytest.raises(StoreConflictError):
            first.save()
        assert first.diagnostics()['state'] == 'stale'
        assert all(not unit.accepted for unit in captured[0].participants)
    finally:
        first.store._phase_hook = lambda phase: None
        if first._state == 'recovery-required':
            with pytest.raises(StoreConflictError):
                first.resolve_save()
        first.close()
        for session in later:
            session.close()


@pytest.mark.parametrize('fault_kind', ['conflict', 'pressure'])
def test_postcommit_failure_type_cannot_discard_acknowledged_plan(tmp_path, fault_kind):
    from ate_sim.persistence_lazy_store import GenerationPressureError
    destination = converted_people_store(tmp_path, 12, active=3)
    session = open_lazy_world_session(destination, rules_id=RULES)
    try:
        session.world.people[1].wealth += 3
        generation = session.pin.captured_head
        error = StoreConflictError('postcommit callback conflict') if fault_kind == 'conflict' else GenerationPressureError(3, 2)
        def fail(phase):
            if phase == 'after_commit':
                raise error
        session.store._phase_hook = fail
        with pytest.raises(type(error)):
            session.save()
        assert session._state == 'recovery-required'
        assert session._pending_save is not None
        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == generation + 1
        assert session.save() == generation + 1
    finally:
        session.store._phase_hook = lambda phase: None
        # Keep a failing regression from leaking the deliberately uncertain pin.
        if session._state != 'active':
            plan = session._pending_save
            if plan is not None and session._state == 'recovery-required':
                session.resolve_save()
            elif session._state == 'stale':
                attempt = session.store._attempt_row(session.pin.token)
                if attempt is not None:
                    result = session.store.resolve_commit(session.pin, session.store.codec.decode(attempt[0]))
                    session.pin = result.pin
        session.close()
