"""Closeout contracts: additions to the schema must receive an explicit policy."""

from dataclasses import FrozenInstanceError
import importlib

import pytest

from simulation.ate_sim.persistence_schema import RECORD_FIELDS, ROOT_FIELDS
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.ate_sim.incremental_store import RecordChange, Membership
from simulation.tests.test_persistence_lazy_store import codec, make_store, metadata


def families():
    return importlib.import_module("simulation.ate_sim.persistence_lazy_families")


def test_manifest_covers_every_root_collection_including_eager_owners():
    module = families()
    expected = {f"{root}.{field}" for root, fields in ROOT_FIELDS.items()
                for field, kind in fields.items() if kind not in ("int", "state")}
    assert set(module.FAMILIES) == expected
    assert module.FAMILIES["world.skills.skills"].identity_enabled
    assert module.FAMILIES["world.magic_resources.owner_index"].identity_enabled
    assert module.FAMILIES["world.lineage.children"].identity_enabled
    assert module.FAMILIES["world.settlements"].storage_mode == "eager"
    for adapter in module.FAMILIES.values():
        assert adapter.record_schema > 0
        assert adapter.absolute_path(3, (("field", "child"),))[-1] == ("field", "child")
    module.validate_manifest()


def test_schema_inventory_is_exhaustive_and_future_field_cannot_inherit_a_default():
    module = families()
    inventory = module.FIELD_POLICIES
    assert set(inventory) == {(module.record_name(cls), field) for cls, fields in RECORD_FIELDS.items()
                              for field in fields}
    assert all(p.category and p.writer and p.representation and p.bound for p in inventory.values())
    household = next(cls for cls in RECORD_FIELDS if cls.__name__ == "Household")
    changed = dict(RECORD_FIELDS)
    changed[household] += ("unclassified_history",)
    with pytest.raises(ValueError, match="unclassified_history"):
        module.validate_field_inventory(changed)
    # Generated-state guards must not be advertised as bounds on imported values.
    assert "import" in inventory["EssencePath", "abilities"].bound
    assert "unbounded" in inventory["SoulState", "transformations"].bound


def test_participant_delta_freezes_values_keys_indexes_and_ordinary_changes():
    module = families()
    value = {"history": [1, 2]}
    ordinary = {"other": [7]}
    delta = module.ParticipantDelta.freeze(
        codec(), "test", version_changes=(VersionChange("people", 1, value,
            memberships=(Membership("alive", True, 0),)),),
        ordinary_changes=(RecordChange("eager", 2, ordinary),),
    )
    before = delta.fingerprint
    value["history"].append(3)
    ordinary["other"].append(8)
    versions, records, identities = delta.decode(codec())
    assert versions[0].value == {"history": [1, 2]}
    assert records[0].value == {"other": [7]}
    assert identities == ()
    versions[0].value["history"].clear()
    assert delta.decode(codec())[0][0].value == {"history": [1, 2]}
    assert delta.fingerprint == before
    with pytest.raises(FrozenInstanceError):
        delta.fingerprint = "changed"


def test_measurement_records_real_store_io_and_does_not_claim_examined_sql_rows(tmp_path):
    module = families()
    with make_store(tmp_path / "metrics.sqlite") as store:
        pin = store.capture_pin()
        before = module.Measurement.capture(store)
        result = store.commit(pin, commit_token="one", version_changes=(
            VersionChange("people", 1, "Ada"),), changes=(), new_segments=(), metadata=metadata(1))
        store.read_version(result.pin, "people", 1, expected_record_schema=1)
        measured = module.Measurement.capture(store).since(before)
        assert measured["payload_reads"] == 1
        assert measured["payload_writes"] == 1
        assert measured["payload_read_bytes"] > 0
        assert measured["payload_write_bytes"] > 0
        assert measured["sql_rows_examined"] is None
        assert measured["metadata_rows"] > 0


def test_ordinary_participant_preserves_query_memberships():
    member = Membership('scope', ('settlement', 2), 7)
    delta = families().ParticipantDelta.freeze(codec(), 'ordinary', ordinary_changes=(
        RecordChange('eager', 1, [True, 1.0], memberships=(member,)),))
    assert delta.decode(codec())[1][0].memberships == (member,)
