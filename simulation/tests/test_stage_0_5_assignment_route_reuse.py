"""Native scalar assignment authenticates its shared routes once."""
from unittest.mock import patch
import math

import pytest

from ate_sim.agency import ActionRecord
from ate_sim.persistence_lazy import open_lazy_world_session
from ate_sim.persistence_tracking import _binding
from simulation.tests.test_stage_0_5_final_identity_only_headers import complete
from simulation.tests.test_stage_0_5_final_catalog_copy import RULES


def install_record(session):
    record = ActionRecord(1, 2, 'work', 'wealth', .5)
    session.skills[1, 'craft'].provenance = [record, {'record': record}]
    session.save()
    return record


@pytest.mark.parametrize('unrelated', [16, 320])
def test_scalar_assignment_routes_once_and_marks_all_owners(tmp_path, unrelated):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.agency.actions.extend(ActionRecord(0,i,'work','wealth',.5) for i in range(unrelated))
        record = install_record(session)
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as routes:
            record.strength = .875
            assert routes.call_count == 1
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1]['record'] is record
        assert root[1]['record'].strength == .875
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1]['record'] and root[0].strength == .875


def test_structural_edit_reconciles_immediately(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = install_record(session)
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as routes:
            record.motive = {'values': [1]}
            assert routes.call_count >= 2
        record.motive['values'].append(2)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert list(session.skills[1, 'craft'].provenance[0].motive['values']) == [1, 2]


def test_nan_and_recursive_values_use_checked_path(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = install_record(session)
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as routes:
            record.strength = float('nan')
            assert math.isnan(record.strength)
            assert routes.call_count >= 2
        record.strength = .75
        session.save()


def test_failed_assignment_leaves_state_unchanged(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = install_record(session)
        before = session._registry.next_incarnation
        with pytest.raises(TypeError): record.motive = [[1], object()]
        assert record.motive == 'wealth'
        assert session._registry.next_incarnation == before
        record.strength = .8
        session.save()


def test_reentrant_or_revision_change_invalidates_ticket(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = install_record(session)
        binding = _binding(record)
        token = binding.before_assignment(record, 'strength', .8)
        record.person = 99  # A reentrant assignment invalidates the earlier ticket.
        object.__setattr__(record, 'strength', token[-1])
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as routes:
            binding.after_assignment(record, 'strength', token[-1], token)
            assert routes.call_count == 1
        session.save()


def test_deleted_owner_is_not_resurrected(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = install_record(session)
        session.skills[1, 'craft'].provenance = []
        record.strength = .25
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert list(session.skills[1, 'craft'].provenance) == []
