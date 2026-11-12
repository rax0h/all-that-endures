"""Recursive proof reads validate one placement; mutations keep full closures."""
import cProfile
import pstats
import sqlite3

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError
from ate_sim.persistence_lazy_store import _identity_occurrence_checksum
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open, RULES

NS = 'world.skills.skills'
OWNER = (NS, (1, 'craft'))
PATH = (('field', 'provenance'),)


def populate(session):
    from ate_sim.agency import ActionRecord
    child = [3]
    record = ActionRecord(1, 2, 'work', 'wealth', .5)
    root = [child, {'notes': child}, (child,), record]
    session.skills[1, 'craft'].provenance = root
    # Leave the original shared history on skill2: full retirement has a
    # separately checked proof contract and is not this read fixture's scope.
    session.save()


def nested_fixture(tmp_path):
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    path, pair = ranked_fixture(tmp_path, size=4)
    # Recursive descendants are admitted through the established native writer,
    # after legacy conversion; that converter deliberately rejects this graph.
    with open_audited_proof_world_session(path, rules_id=RULES, expected_commitment=pair[1]) as session:
        populate(session)
        pair = session.proof_manifest
    return path, pair


def owner_calls(profile, *, from_decode=False):
    total = 0
    for (file, _, name), stats in pstats.Stats(profile).stats.items():
        if file.endswith('/persistence_lazy_identity_coordinator.py') and name == '_owner_changes':
            if not from_decode:
                total += stats[1]
            else:
                total += sum(v[1] for (caller, _, function), v in stats[4].items()
                             if caller.endswith('/persistence_history_runtime.py') and function == 'decode')
    return total


def test_recursive_proof_reads_do_not_enumerate_owner_to_decode_one_reference(tmp_path):
    # Reintroducing the owner scan for a single reference repeats complete work.
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        value = session.store.read_version(session.pin, *OWNER, expected_record_schema=1).value.provenance
        profile = cProfile.Profile()
        profile.enable()
        try:
            child = session._recursive_histories.decode(value, OWNER, PATH)
            assert session._recursive_histories.decode(value, OWNER, PATH) is child
            assert session.skills[1, 'craft'].provenance is session.skills[2, 'craft'].provenance is child
            assert list(child) == [0, 1, 2, 3]
        finally:
            profile.disable()
        assert owner_calls(profile) == 0
        assert not session.store.db.in_transaction


@pytest.mark.parametrize('mode', ['ordinary', 'audited'])
def test_default_and_audited_reads_keep_owner_completeness(tmp_path, mode):
    from ate_sim.persistence_lazy import open_lazy_world_session
    from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
    path, pair = ranked_fixture(tmp_path, size=4)
    opened = (open_lazy_world_session(tmp_path / 'source/complete.sqlite', rules_id=RULES)
              if mode == 'ordinary' else
              open_audited_proof_world_session(path, rules_id=RULES, expected_commitment=pair[1]))
    with opened as session:
        value = session.store.read_version(session.pin, *OWNER, expected_record_schema=1).value.provenance
        profile = cProfile.Profile()
        profile.enable()
        try:
            assert session._recursive_histories.decode(value, OWNER, PATH) is session.skills[2, 'craft'].provenance
        finally:
            profile.disable()
        assert owner_calls(profile) > 0


def test_point_read_applies_replacement_tombstone_and_reversion(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        coord = session._identity_coordinator
        original = session.store.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        replacement = session._registry.bind(session.skills[1, 'craft'].teachers).value
        assert coord._placement_for_read(OWNER, PATH) == original
        coord._record_placement_change(OWNER, PATH, original, original, replacement)
        assert coord._placement_for_read(OWNER, PATH) == replacement
        coord._record_placement_change(OWNER, PATH, original, replacement, None)
        assert coord._placement_for_read(OWNER, PATH) is None
        coord._record_placement_change(OWNER, PATH, original, None, original)
        assert coord._placement_for_read(OWNER, PATH) == original


def test_point_read_authenticates_new_owner_absence_before_overlay(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        coord = session._identity_coordinator
        owner = (NS, (999, 'craft'))
        assert coord._placement_for_read(owner, PATH) is None
        replacement = session._registry.bind(session.skills[1, 'craft'].teachers).value
        coord._record_placement_change(owner, PATH, None, None, replacement)
        assert coord._placement_for_read(owner, PATH) == replacement


@pytest.mark.parametrize('overlay', [False, True])
@pytest.mark.parametrize('damage', ['missing', 'moved', 'future', 'extra'])
def test_point_read_rejects_coherent_physical_forgery_even_under_overlay(tmp_path, overlay, damage):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        coord = session._identity_coordinator
        key, encoded = st.codec.encode(OWNER[1]), st.codec.encode(PATH)
        inc, start, end, _ = st._visible_identity_occurrence(0, NS, key, encoded)
        selected_path = PATH
        if overlay:
            coord._record_placement_change(OWNER, PATH, inc, inc, session._registry.bind(session.skills[1, 'craft'].teachers).value)
        if damage == 'missing':
            st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?', (NS, key, encoded))
        elif damage == 'extra':
            selected_path = (('field', 'forged'),)
            encoded = st.codec.encode(selected_path)
            st.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',
                          (NS, key, encoded, inc, 0, None, _identity_occurrence_checksum(NS, key, encoded, inc, 0, None)))
        else:
            if damage == 'moved':
                inc = inc + 1 if inc + 1 < st.read_identity_state(session.pin) else 1
            else:
                end = 1
            st.db.execute('UPDATE lazy_identity_occurrence_versions SET incarnation_id=?,valid_to=?,row_checksum=? WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',
                          (inc, end, _identity_occurrence_checksum(NS, key, encoded, inc, start, end), NS, key, encoded))
        st.db.commit()
        # Deliberately pass the outer epoch gate to exercise actual proof refusal.
        st._world_proof_authority.epoch = st._world_proof_authority._epoch()
        with pytest.raises(StoreIntegrityError):
            coord._placement_for_read(OWNER, selected_path)
        assert not st.db.in_transaction


@pytest.mark.parametrize('drift', ['local', 'external', 'uncertain', 'released'])
def test_overlay_cannot_bypass_point_read_authority_drift(tmp_path, drift):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as session:
        st = session.store
        coord = session._identity_coordinator
        inc = st.read_identity_occurrence(session.pin, *OWNER, PATH).incarnation_id
        coord._record_placement_change(OWNER, PATH, inc, inc, session._registry.bind(session.skills[1, 'craft'].teachers).value)
        if drift in ('local', 'external'):
            db = sqlite3.connect(path) if drift == 'external' else st.db
            db.execute("UPDATE records SET payload_checksum='drift' WHERE namespace='world.seed'")
            db.commit()
            if db is not st.db:
                db.close()
        elif drift == 'uncertain':
            st._world_proof_authority.uncertain = True
        else:
            st.release_pin(session.pin)
        with pytest.raises(StoreError):
            coord._placement_for_read(OWNER, PATH)
        assert not st.db.in_transaction


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_recursive_point_reads_keep_private_alias_replacement_and_recovery(tmp_path, phase):
    path, pair = nested_fixture(tmp_path)
    with fast_open(path, pair) as session:
        root = session.skills[1, 'craft'].provenance
        old = root[0]
        root[0] = [9]
        old.append(4)
        assert list(root[0]) == [9] and root[1]['notes'] is old
        def fault(at):
            if at == phase:
                raise RuntimeError('point-read recovery')
        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='point-read recovery'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        session.save()
        pair = session.proof_manifest
    with fast_open(path, pair) as session:
        root = session.skills[1, 'craft'].provenance
        assert list(root[0]) == [9]
        assert root[1]['notes'] is root[2][0]
        assert list(root[2][0]) == [3, 4]
