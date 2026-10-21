"""Operational certificates are reusable only inside an owned read operation."""
from unittest.mock import patch
import sqlite3

import pytest

from simulation.ate_sim.incremental_store import StoreIntegrityError, StoreError
from simulation.tests.test_persistence_lazy_store import make_store
from simulation.tests.test_stage_0_5_final_identity_catalog import groups, catalog, NS


def operation(store, pin):
    from simulation.ate_sim.persistence_validation_scope import checked_read_operation
    return checked_read_operation(store, pin)


def test_private_nested_reads_validate_operational_rows_once(tmp_path):
    with make_store(tmp_path/'scope.sqlite') as store:
        pin = groups(store)
        with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
            with operation(store, pin):
                for _ in range(10):
                    assert store.read_version(pin, NS, 1, expected_record_schema=1).value == {'value': 1}
            assert checks.call_count == 1


def test_public_and_borrowed_scopes_keep_validation(tmp_path):
    with make_store(tmp_path/'borrowed.sqlite') as store:
        pin = groups(store)
        with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
            with store.read_snapshot(pin):
                for _ in range(10):
                    with store.read_snapshot(pin): pass
            assert checks.call_count == 11
        with store.read_snapshot(pin):
            with operation(store, pin) as scope:
                assert not scope.can_reuse(store, pin)
                assert store.read_version(pin, NS, 1, expected_record_schema=1).value == {'value': 1}
        with store.read_transaction():
            with operation(store, pin) as scope:
                assert not scope.can_reuse(store, pin)


def test_catalog_group_checks_once_without_skipping_payload_validation(tmp_path):
    with make_store(tmp_path/'catalog.sqlite') as store:
        pin = groups(store)
        with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
            result = catalog().IdentityCatalog(store).read_identity_group(pin, 1)
            assert result.occurrences == ((NS, 1, ()), (NS, 2, ()))
            assert checks.call_count == 1
        store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?',
                         (b'corrupt', catalog().GROUP_NAMESPACE))
        store.db.commit()
        with pytest.raises(StoreIntegrityError):
            catalog().IdentityCatalog(store).read_identity_group(pin, 1)


def test_write_and_rollback_permanently_invalidate_scope(tmp_path):
    with make_store(tmp_path/'rollback.sqlite') as store:
        pin = groups(store)
        with operation(store, pin) as scope:
            assert scope.can_reuse(store, pin)
            store.db.execute('SAVEPOINT corrupt')
            store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=?', (NS,))
            assert not scope.can_reuse(store, pin)
            with pytest.raises(StoreIntegrityError): store.read_version(pin, NS, 1, expected_record_schema=1)
            store.db.execute('ROLLBACK TO corrupt')
            store.db.execute('RELEASE corrupt')
            assert not scope.can_reuse(store, pin)
            assert store.read_version(pin, NS, 1, expected_record_schema=1).value == {'value': 1}


@pytest.mark.parametrize('change', ['codec', 'schema', 'released', 'foreign'])
def test_changed_authority_cannot_reuse_scope(tmp_path, change):
    with make_store(tmp_path/'epoch.sqlite') as store, make_store(tmp_path/'other.sqlite') as other:
        pin = groups(store)
        foreign = groups(other)
        with operation(store, pin) as scope:
            if change == 'codec': store.codec = type(store.codec)()
            elif change == 'schema': store.db.execute('CREATE TABLE changed(x)')
            elif change == 'released': store.db.execute('DELETE FROM generation_pins WHERE token=?', (pin.token,))
            else:
                assert not scope.can_reuse(store, foreign)
                return
            assert not scope.can_reuse(store, pin)


def test_external_change_between_operations_is_not_cached(tmp_path):
    path = tmp_path/'external.sqlite'
    with make_store(path) as store:
        pin = groups(store)
        with operation(store, pin):
            assert store.read_version(pin, NS, 1, expected_record_schema=1).value == {'value': 1}
        with sqlite3.connect(path) as db:
            db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?', (b'bad', NS))
        with pytest.raises(StoreIntegrityError):
            with operation(store, pin): store.read_version(pin, NS, 1, expected_record_schema=1)


def test_scope_does_not_escape_callback_or_iterator(tmp_path):
    with make_store(tmp_path/'end.sqlite') as store:
        pin = groups(store)
        with pytest.raises(RuntimeError):
            with operation(store, pin) as scope:
                raise RuntimeError('end')
        assert not scope.can_reuse(store, pin)
        assert getattr(store, '_validation_scope', None) is None
        with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
            store.read_version(pin, NS, 1, expected_record_schema=1)
            assert checks.call_count == 1


def test_scope_budget_is_history_independent(tmp_path):
    with make_store(tmp_path/'budget.sqlite') as store:
        pin = groups(store)
        with operation(store, pin) as scope:
            for i in range(1000): scope.remember('header', (i,), ('small', i))
            assert scope.entries <= 256
            assert scope.bytes <= 256*1024
            assert scope.lookup('header', (999,)) == ('small', 999)
            scope.remember('header', ('large',), ('x'*(256*1024),))
            assert scope.lookup('header', ('large',)) is None
        assert scope.entries == 0


def test_closed_store_and_replaced_connection_invalidate_scope(tmp_path):
    with make_store(tmp_path/'connection.sqlite') as store:
        pin = groups(store)
        with operation(store, pin) as scope:
            db = store.db
            store.db = sqlite3.connect(':memory:')
            try: assert not scope.can_reuse(store, pin)
            finally:
                store.db.close()
                store.db = db
        store.close()
        assert not scope.can_reuse(store, pin)
