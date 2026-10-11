"""A lazy family field cannot admit the owner into its own new history."""
import pytest
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    converted_catalog, open_bridge, activate, RULES,
)


@pytest.mark.parametrize('wrapped', [False, True])
def test_unbacked_lazy_record_owner_cycle_rejects_before_native_admission(tmp_path, wrapped):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = session.skills[1, 'craft']
        original = record.provenance
        before = session._registry.next_incarnation
        incoming = [{'owner': record}] if wrapped else [record]
        with pytest.raises(TypeError, match='cyclic'):
            record.provenance = incoming
        assert record.provenance is original
        assert session._registry.next_incarnation == before
        assert session.save() == session.pin.captured_head
