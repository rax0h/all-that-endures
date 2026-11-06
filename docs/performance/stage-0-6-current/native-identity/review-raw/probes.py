"""Independent review-only native identity edge probes; no product edits."""
import pytest
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_lazy_store import _identity_occurrence_checksum
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened

NS = 'world.skills.skills'
PATH = (('field', 'provenance'),)

def reset(st):
    st.db.commit()
    st._world_proof_authority.epoch = st._world_proof_authority._epoch()

def insert(st, ns, key, path, inc, start=0, end=None):
    st.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',
                  (ns, key, path, inc, start, end,
                   _identity_occurrence_checksum(ns, key, path, inc, start, end)))

@pytest.mark.parametrize('query', ['owner', 'allocated-empty', 'unallocated'])
@pytest.mark.parametrize('closure', [None, 1])
def test_empty_scope_cannot_hide_physical_row(tmp_path, query, closure):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as s:
        st = s.store
        next_id = st.read_identity_state(s.pin)
        # Choose an allocated incarnation without skill999's nonexistent owner.
        inc = 1 if query != 'unallocated' else next_id + 3
        key, encoded = st.codec.encode((999, 'craft')), st.codec.encode(PATH)
        if query == 'allocated-empty':
            # Root-selected existing memberships must still expose this surplus.
            pass
        insert(st, NS, key, encoded, inc, end=closure)
        reset(st)
        with pytest.raises(StoreIntegrityError):
            if query == 'owner':
                st.identity_occurrences_for_owner(s.pin, NS, (999, 'craft'))
            else:
                st.identity_occurrences_for_incarnation(s.pin, inc)
        assert not st.db.in_transaction

def test_compensated_group_omission_fails_before_decode(tmp_path, monkeypatch):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as s:
        st = s.store
        inc = st.read_identity_occurrence(s.pin, NS, (1, 'craft'), PATH).incarnation_id
        encoded = st.codec.encode(PATH)
        before = st.db.execute('SELECT count(*) FROM lazy_identity_occurrence_versions WHERE incarnation_id=? AND valid_to IS NULL', (inc,)).fetchone()[0]
        st.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?', (NS, st.codec.encode((2, 'craft')), encoded))
        insert(st, NS, st.codec.encode((999, 'craft')), encoded, inc)
        reset(st)
        assert st.db.execute('SELECT count(*) FROM lazy_identity_occurrence_versions WHERE incarnation_id=? AND valid_to IS NULL', (inc,)).fetchone()[0] == before
        seen = []
        decode = st.codec.decode
        def observed(raw):
            if raw == encoded:
                seen.append(raw)
            return decode(raw)
        monkeypatch.setattr(st.codec, 'decode', observed)
        with pytest.raises(StoreIntegrityError):
            st.identity_occurrences_for_incarnation(s.pin, inc)
        assert not seen and not st.db.in_transaction

@pytest.mark.parametrize('extra', [b'\x01', b'\xff'])
def test_owner_surplus_on_either_side_fails_before_decode(tmp_path, monkeypatch, extra):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as s:
        st = s.store
        inc = st.read_identity_occurrence(s.pin, NS, (1, 'craft'), PATH).incarnation_id
        insert(st, NS, st.codec.encode((1, 'craft')), extra, inc)
        reset(st)
        seen = []
        decode = st.codec.decode
        def observed(raw):
            seen.append(raw)
            return decode(raw)
        monkeypatch.setattr(st.codec, 'decode', observed)
        with pytest.raises(StoreIntegrityError):
            st.identity_occurrences_for_owner(s.pin, NS, (1, 'craft'))
        assert not seen and not st.db.in_transaction

@pytest.mark.parametrize('query', ['owner', 'group', 'point'])
def test_duplicate_exact_locator_cannot_escape_tuple_cursor(tmp_path, query):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as s:
        st = s.store
        s.world.year = 1
        assert s.save() == 1
        inc = st.read_identity_occurrence(s.pin, NS, (1, 'craft'), PATH).incarnation_id
        insert(st, NS, st.codec.encode((1, 'craft')), st.codec.encode(PATH), inc, start=1)
        reset(st)
        with pytest.raises(StoreIntegrityError):
            if query == 'owner':
                st.identity_occurrences_for_owner(s.pin, NS, (1, 'craft'))
            elif query == 'group':
                st.identity_occurrences_for_incarnation(s.pin, inc)
            else:
                st.read_identity_occurrence(s.pin, NS, (1, 'craft'), PATH)
        assert not st.db.in_transaction

def test_current_group_count_and_owner_cursor_use_prefix_indexes(tmp_path):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as s:
        st = s.store
        statements = [
            ('SELECT count(*) FROM lazy_identity_occurrence_versions INDEXED BY lazy_identity_incarnation_interval WHERE incarnation_id=? AND valid_to IS NULL', (1,)),
            ('SELECT 1 FROM lazy_identity_occurrence_versions INDEXED BY lazy_identity_occurrence_current WHERE owner_namespace=? AND owner_key=? AND valid_to IS NULL AND (occurrence_path,incarnation_id)>(?,?) ORDER BY occurrence_path,incarnation_id LIMIT 1', (NS, st.codec.encode((1, 'craft')), b'', 0)),
        ]
        for sql, args in statements:
            plan = ' '.join(row[-1] for row in st.db.execute('EXPLAIN QUERY PLAN ' + sql, args))
            assert 'SEARCH' in plan and 'TEMP B-TREE' not in plan and 'SCAN ' not in plan, plan
