"""Checked event-ID identity headers retain the compact authority."""
import pytest

from ate_sim.incremental_store import StoreConflictError
from ate_sim.persistence_lazy_families import FAMILIES
from ate_sim.persistence_event_ids import AUTHORITY_REFERENCE
from ate_sim.institutions import Institution
from simulation.tests.test_stage_0_5_final_event_id_exceptions import converted, RULES
from ate_sim.persistence_lazy import open_lazy_world_session


@pytest.mark.parametrize('history', [1000, 10000])
@pytest.mark.parametrize('exceptional', [False, True])
def test_root_and_nested_identity_headers_do_not_visit_event_members(tmp_path, history, exceptional):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        ids = session.world.event_ids
        if exceptional:
            ids.remove(history // 2)
            ids.add(history + 20)
        header = Institution(1, 'magic_society', 'Magic', 0, None, members=ids)
        expected = Institution(1, 'magic_society', 'Magic', 0, None,
                               members=AUTHORITY_REFERENCE)
        before = session.store.diagnostics().payload_reads
        root = FAMILIES['world.event_ids'].identity_payload_bytes(session.store, session.pin, ids)
        nested = FAMILIES['world.institutions.institutions'].identity_payload_bytes(
            session.store, session.pin, header)
        alias = FAMILIES['world.currency.wallets'].identity_payload_bytes(
            session.store, session.pin, {'ids': ids})
        assert root == session.store.codec.encode(ids.descriptor())
        assert nested == session.store.codec.encode(expected)
        assert alias == session.store.codec.encode({'ids': AUTHORITY_REFERENCE})
        assert ids.diagnostics()['member_visits'] == 0
        assert session.store.diagnostics().payload_reads == before
        assert max(map(len, (root, nested, alias))) < 4096


def test_event_id_header_rejects_foreign_and_old_authorities(tmp_path):
    left_dir, right_dir = tmp_path / 'left', tmp_path / 'right'
    left_dir.mkdir()
    right_dir.mkdir()
    left_path, right_path = converted(left_dir, 8), converted(right_dir, 8)
    with open_lazy_world_session(left_path, rules_id=RULES) as left, \
            open_lazy_world_session(right_path, rules_id=RULES) as right:
        adapter = FAMILIES['world.event_ids']
        with pytest.raises(StoreConflictError, match='event.*authority'):
            adapter.identity_payload_bytes(right.store, right.pin, left.world.event_ids)
        old = left.store.capture_pin()
        left.world.year += 1
        left.save()
        with pytest.raises(StoreConflictError, match='event.*authority'):
            adapter.identity_payload_bytes(left.store, old, left.world.event_ids)
        left.store.release_pin(old)


def test_event_id_header_rejects_closed_world_authority(tmp_path):
    path = converted(tmp_path, 8)
    session = open_lazy_world_session(path, rules_id=RULES)
    ids, store = session.world.event_ids, session.store
    session.close()
    # Reopen the checked store separately: its pin cannot authorize an alias
    # retained from a closed World session.
    from ate_sim.persistence_lazy_store import LazyRecordStore
    from ate_sim.persistence_adapters import SCHEMA
    with LazyRecordStore.open(store.path, expected_simulation_schema=SCHEMA,
                              expected_rules_id=RULES, codec=store.codec) as reopened:
        pin = reopened.capture_pin()
        with pytest.raises(StoreConflictError, match='event.*authority'):
            FAMILIES['world.event_ids'].identity_payload_bytes(reopened, pin, ids)
        reopened.release_pin(pin)
