"""Independent review probes; not an expanded production test contract."""
from dataclasses import replace

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError
from ate_sim.persistence_lazy_store import _identity_occurrence_checksum
from simulation.tests.test_stage_0_6_proof_placement_reads import OWNER, PATH
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open


@pytest.mark.parametrize('change', ['replacement', 'tombstone'])
@pytest.mark.parametrize('baseline', ['present', 'absent'])
def test_overlay_never_hides_physical_point_drift(tmp_path, change, baseline):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st, coord = s.store, s._identity_coordinator
        inc = st.read_identity_occurrence(s.pin, *OWNER, PATH).incarnation_id
        selected = PATH if baseline == 'present' else (('field', 'review-new'),)
        original = inc if baseline == 'present' else None
        chosen = (s._registry.bind(s.skills[1, 'craft'].teachers).value
                  if change == 'replacement' else None)
        # A deletion of an absent path ordinarily collapses to no overlay;
        # preserve that ordinary no-op and still demand the point proof.
        coord._record_placement_change(OWNER, selected, original, original, chosen)
        key, encoded = st.codec.encode(OWNER[1]), st.codec.encode(selected)
        if baseline == 'present':
            st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?', (OWNER[0], key, encoded))
        else:
            st.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',
                (OWNER[0], key, encoded, inc, 0, None,
                 _identity_occurrence_checksum(OWNER[0], key, encoded, inc, 0, None)))
        st.db.commit()
        st._world_proof_authority.epoch = st._world_proof_authority._epoch()
        with pytest.raises(StoreIntegrityError):
            coord._placement_for_read(OWNER, selected)
        assert not st.db.in_transaction


def test_point_caller_pin_callback_and_path_boundaries(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        st, coord = s.store, s._identity_coordinator
        for bad in ((('index', -1),), (('field', ''),), (('bogus', 0),)):
            with pytest.raises(StoreIntegrityError):
                coord._placement_for_read(OWNER, bad)
        saved = coord.pin
        try:
            for pin in (replace(saved, token='review-unknown'), replace(saved, captured_head=saved.captured_head + 1)):
                coord.pin = pin
                with pytest.raises(StoreError):
                    coord._placement_for_read(OWNER, PATH)
        finally:
            coord.pin = saved
        for field in ('_callback_guard', '_native_sql_callback_depth'):
            previous = getattr(st.db, field, 0)
            try:
                setattr(st.db, field, 1)
                with pytest.raises(StoreError):
                    coord._placement_for_read(OWNER, PATH)
            finally:
                setattr(st.db, field, previous)
        assert not st.db.in_transaction


def test_decode_keeps_incarnation_and_live_kind_checks(tmp_path):
    path, pair = ranked_fixture(tmp_path, size=4)
    with fast_open(path, pair) as s:
        value = s.store.read_version(s.pin, *OWNER, expected_record_schema=1).value.provenance
        s._recursive_histories.decode(value, OWNER, PATH)
        with pytest.raises(StoreIntegrityError):
            s._recursive_histories.decode(replace(value, incarnation=value.incarnation + 1), OWNER, PATH)
        with pytest.raises(StoreIntegrityError):
            s._recursive_histories.decode(replace(value, kind='map'), OWNER, PATH)
        assert not s.store.db.in_transaction
