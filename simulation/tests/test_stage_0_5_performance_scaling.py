"""Optimized checked work follows requested groups, not unrelated history."""
from unittest.mock import patch

import pytest

from simulation.tests.test_persistence_lazy_store import make_store
from simulation.tests.test_stage_0_5_final_identity_catalog import groups, catalog, NS
from simulation.ate_sim.persistence_validation_scope import checked_read_operation


@pytest.mark.parametrize('history', [2, 32, 320])
@pytest.mark.parametrize('requested', [1, 2])
def test_group_work_tracks_requested_state_not_unrelated_history(tmp_path, history, requested):
    with make_store(tmp_path/'scale.sqlite') as store:
        pin = groups(store, history)
        cat = catalog().IdentityCatalog(store)
        store.reset_diagnostics()
        with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
            with checked_read_operation(store, pin) as scope:
                for inc in range(1,requested+1):
                    result = cat.read_identity_group(pin, inc)
                    assert result.occurrences == ((NS, 2*inc-1, ()), (NS, 2*inc, ()))
                assert scope.entries <= 256 and scope.bytes <= 256*1024
            assert checks.call_count == 1
        diag = store.diagnostics()
        assert diag.payload_reads <= 20*requested
        assert diag.metadata_rows <= 180*requested


def test_failed_owned_scope_does_not_change_following_public_checks(tmp_path):
    with make_store(tmp_path/'exception.sqlite') as store:
        pin = groups(store, 32)
        with pytest.raises(ValueError):
            with checked_read_operation(store, pin):
                catalog().IdentityCatalog(store).read_identity_group(pin, 1)
                raise ValueError('abort operation')
        with patch.object(store, '_checked_operational_rows', wraps=store._checked_operational_rows) as checks:
            for _ in range(3):
                store.read_version(pin, NS, 1, expected_record_schema=1)
            assert checks.call_count == 3
