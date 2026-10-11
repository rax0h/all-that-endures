"""Concrete immutable World values retain their types and native key equality."""
import pytest

from ate_sim.core import Ref, Layer
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    converted_catalog, open_bridge, activate, RULES,
)


def test_registered_value_records_and_enums_round_trip_in_recursive_history(tmp_path):
    target = converted_catalog(tmp_path)
    value = Ref('person', 7)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [value, (value, Layer.SOCIETY), {'where': value}]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0] == value and type(root[0]) is Ref
        assert root[1] == (value, Layer.SOCIETY)
        assert root[1][1] is Layer.SOCIETY
        assert root[2]['where'] == value
        plain = session.detach(materialize_history=True)
        assert type(plain.skills.skills[1, 'craft'].provenance[0]) is Ref


@pytest.mark.parametrize('key,equal', [
    (Ref('person', True), Ref('person', 1.0)),
    ((Ref('person', True),), (Ref('person', 1),)),
    (frozenset({Ref('person', True)}), frozenset({Ref('person', 1.0)})),
    (Layer.SOCIETY, 'society'),
    (('kind', Layer.REALITY), ('kind', 'reality')),
    (Ref(Layer.SOCIETY, 1), Ref('society', 1.0)),
])
def test_recursive_map_value_keys_follow_native_equality_and_keep_representative(tmp_path, key, equal):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [{key: [1]}]
        mapping = session.skills[1, 'craft'].provenance[0]
        child = mapping[equal]
        assert list(child) == [1]
        mapping[equal] = child
        assert len(mapping) == 1 and type(next(iter(mapping))) is type(key)
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        mapping = session.skills[1, 'craft'].provenance[0]
        assert len(mapping) == 1 and list(mapping[equal]) == [1]
        assert type(next(iter(mapping))) is type(key)
        generation = session.pin.captured_head
        mapping[equal] = mapping[equal]
        assert session.save() == generation
        del mapping[equal]
        session.save()
        assert not mapping


def test_recursive_set_value_keys_keep_native_enum_and_ref_representatives(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [{Ref('person', True), Layer.SOCIETY}]
        values = session.skills[1, 'craft'].provenance[0]
        assert Ref('person', 1) in values and 'society' in values
        values.add(Ref('person', 1.0))
        values.add('society')
        assert len(values) == 2
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        values = session.skills[1, 'craft'].provenance[0]
        assert len(values) == 2
        assert Layer.SOCIETY in values and Ref('person', 1.0) in values
        assert any(type(item) is Layer for item in values)
        generation = session.pin.captured_head
        values.add('society')
        values.add(Ref('person', 1.0))
        assert session.save() == generation
        values.discard('society')
        values.discard(Ref('person', 1))
        session.save()
        assert not values


def test_mutable_child_hidden_in_frozen_ref_rejects_before_owner_or_allocator_edit(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        before = session._registry.next_incarnation
        with pytest.raises(TypeError):
            session.skills[1, 'craft'].provenance = [Ref('person', [1])]
        assert session.skills[1, 'craft'].provenance is root
        assert session._registry.next_incarnation == before


@pytest.mark.parametrize('invalid', ['cycle', 'extra', 'foreign_record', 'foreign_enum'])
def test_undeclared_or_invalid_value_records_fail_closed_before_admission(tmp_path, invalid):
    from dataclasses import dataclass
    from enum import Enum
    @dataclass(frozen=True)
    class ForeignRef:
        kind: str
        id: int
    class ForeignLayer(str, Enum):
        SOCIETY = 'society'
    value = Ref('person', 1)
    if invalid == 'cycle':
        object.__setattr__(value, 'id', value)
    elif invalid == 'extra':
        object.__setattr__(value, 'extra', 'unclassified')
    elif invalid == 'foreign_record':
        value = ForeignRef('person', 1)
    else:
        value = ForeignLayer.SOCIETY
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        before = session._registry.next_incarnation
        with pytest.raises(TypeError):
            session.skills[1, 'craft'].provenance = [value]
        assert session.skills[1, 'craft'].provenance is root
        assert session._registry.next_incarnation == before


def test_all_declared_frozen_records_are_explicitly_accounted_for():
    from ate_sim.persistence_schema import RECORD_FIELDS
    assert {cls for cls in RECORD_FIELDS if cls.__dataclass_params__.frozen} == {Ref}


def test_shared_native_subtree_is_validated_by_unique_input_graph_not_every_placement(tmp_path, record_property):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        scalar = 999991
        shared = [scalar, Ref('person', 7), Layer.SOCIETY]
        visits = []
        encode = session.store.codec.encode
        def measured(value):
            if type(value) is int and value == scalar:
                visits.append(value)
            return encode(value)
        session.store.codec.encode = measured
        session.skills[1, 'craft'].provenance = [shared] * 48
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[-1]
        assert len(visits) <= 8
        record_property('sharing_placements', 48)
        record_property('incoming_scalar_codec_visits', len(visits))
        session.save()
        assert list(root[0]) == shared


def test_completed_native_validation_is_not_reused_after_caller_changes_source(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [Ref('person', 7)]
        session.skills[1, 'craft'].provenance = [shared] * 4
        root = session.skills[1, 'craft'].provenance
        session.save()
        shared.append(object())
        before = session._registry.next_incarnation
        with pytest.raises(TypeError):
            session.skills[1, 'craft'].provenance = [shared] * 4
        assert session.skills[1, 'craft'].provenance is root
        assert session._registry.next_incarnation == before
        assert session.save() == session.pin.captured_head
