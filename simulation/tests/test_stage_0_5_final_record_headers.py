"""Closed record backing primitives; these do not enable ordinary World admission."""
from dataclasses import dataclass
import json
import pytest

from ate_sim.core import Ref, Layer, Event
from ate_sim.skills import SkillHistory
from ate_sim.agency import ActionRecord
from ate_sim.incremental_store import CodecError, StoreIntegrityError, RecordChange
from ate_sim.persistence_adapters import WorldCodec, SCHEMA
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange, IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference
from ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta, IdentityCatalog
from ate_sim.persistence_schema import RECORD_FIELDS
from ate_sim.persistence_record_headers import (
    RecordReference, record_reference, record_header, checked_record_header,
    restore_record_header, read_record_header, NAMESPACE,
)


def test_closed_record_fields_and_concrete_values_round_trip():
    codec = WorldCodec(identity_links_recorded=True)
    source = SkillHistory(1, 'craft', provenance=[Ref('person', 7)])
    values = tuple(HistoryReference('list', 11) if f == 'teachers' else
                   HistoryReference('list', 12) if f == 'provenance' else getattr(source, f)
                   for f in RECORD_FIELDS[SkillHistory])
    header = record_header(source, values=values)
    restored = restore_record_header(codec.decode(codec.encode(header)))
    assert type(restored) is SkillHistory
    assert restored.person == 1 and restored.domain == 'craft'
    assert restored.teachers == HistoryReference('list', 11)
    assert restored.provenance == HistoryReference('list', 12)
    assert source.provenance == [Ref('person', 7)]
    action = ActionRecord(1, 2, 'work', 'wealth', .5, Ref(Layer.SOCIETY, 3))
    assert restore_record_header(record_header(action)) == action


@pytest.mark.parametrize('cls', [cls for cls in RECORD_FIELDS if not cls.__dataclass_params__.frozen])
def test_each_declared_mutable_record_has_exact_header_field_coverage(cls):
    source = object.__new__(cls)
    for field in RECORD_FIELDS[cls]:
        object.__setattr__(source, field, None)
    header = record_header(source)
    restored = restore_record_header(header)
    assert type(restored) is cls
    assert tuple(vars(restored)) == RECORD_FIELDS[cls]
    assert checked_record_header(header)[0] is cls


@pytest.mark.parametrize('state', ['absent', False, True])
def test_event_header_preserves_exact_seal_metadata(state):
    event = Event(1, 0, 'birth', Layer.SOCIETY, (), None, (), {})
    if state != 'absent':
        object.__setattr__(event, '_sealed', state)
    values = tuple(HistoryReference('map', 7) if f == 'data' else getattr(event, f)
                   for f in RECORD_FIELDS[Event])
    restored = restore_record_header(record_header(event, values=values))
    assert ('_sealed' in vars(restored)) == (state != 'absent')
    if state != 'absent':
        assert vars(restored)['_sealed'] is state


@pytest.mark.parametrize('bad', ['frozen', 'foreign', 'missing', 'extra', 'mutable_child'])
def test_unclassified_or_unprojected_record_input_fails_closed(bad):
    @dataclass
    class Foreign:
        year: int
    value = ActionRecord(1, 2, 'work', 'wealth', .5)
    if bad == 'frozen': value = Ref('person', 7)
    elif bad == 'foreign': value = Foreign(1)
    elif bad == 'missing': del vars(value)['year']
    elif bad == 'extra': object.__setattr__(value, 'extra', 1)
    else: value.motive = ['unprojected']
    with pytest.raises((TypeError, CodecError)):
        record_header(value)


@pytest.mark.parametrize('bad', ['tag', 'class', 'short', 'long', 'mutable', 'metadata', 'event_metadata'])
def test_malformed_stored_headers_fail_with_integrity_error(bad):
    base = record_header(ActionRecord(1, 2, 'work', 'wealth', .5))
    tag, name, values, state = base
    if bad == 'tag': tag = 'recursive-record/v999'
    elif bad == 'class': name = 'os.system/v1'
    elif bad == 'short': values = values[:-1]
    elif bad == 'long': values = values + (None,)
    elif bad == 'mutable': values = ([],) + values[1:]
    elif bad == 'metadata': state = (False, False)
    else:
        base = record_header(Event(1, 0, 'birth', Layer.SOCIETY, (), None, (), {}),
            values=(1, 0, 'birth', Layer.SOCIETY, (), None, (), HistoryReference('map', 7)))
        tag, name, values, state = base
        state = (False, True)
    with pytest.raises(StoreIntegrityError):
        checked_record_header((tag, name, values, state))


def test_record_references_use_closed_codec_tag_and_reject_forged_ids():
    codec = WorldCodec(identity_links_recorded=True)
    ref = RecordReference(7)
    assert record_reference(ref)
    assert codec.decode(codec.encode((ref,))) == (ref,)
    for invalid in (0, -1, True, 1.0, '1'):
        with pytest.raises(ValueError): RecordReference(invalid)
        forged = RecordReference(7)
        object.__setattr__(forged, 'incarnation', invalid)
        assert not record_reference(forged)
        with pytest.raises(CodecError): codec.encode(forged)
        with pytest.raises(CodecError): codec.decode(json.dumps(['typed-record/v1', invalid]).encode())


def store_at(path):
    return LazyRecordStore.create(path, codec=WorldCodec(identity_links_recorded=True),
        simulation_schema=SCHEMA, rules_id='record-headers')


def metadata(year):
    return {'simulation_position': year, 'seed': 7, 'next_ids': {}, 'namespaces': ()}


def test_record_physical_owner_requires_exact_complete_child_placements(tmp_path):
    source = ActionRecord(1, 2, 'work', 'wealth', .5)
    values = tuple((RecordReference(2), HistoryReference('list', 3)) if f == 'motive'
                   else getattr(source, f) for f in RECORD_FIELDS[ActionRecord])
    change = VersionChange(NAMESPACE, (1, 0), record_header(source, values=values))
    paths = ((('field', 'motive'), ('index', 0)), (('field', 'motive'), ('index', 1)))
    placements = tuple(IdentityOccurrenceChange(NAMESPACE, (1, 0), p, inc)
                       for p, inc in zip(paths, (2, 3)))
    with store_at(tmp_path / 'catalog.sqlite') as store:
        for omitted in ((), placements[:1]):
            with pytest.raises(StoreIntegrityError, match='references disagree'):
                initial_catalog_delta(store.codec, (change,), omitted,
                    next_incarnation_id=4, generation=1)
        delta = initial_catalog_delta(store.codec, (change,), placements,
            next_incarnation_id=4, generation=1)
        pin = store.commit(store.capture_pin(), commit_token='record-catalog', changes=(),
            version_changes=(change,) + delta.decode(store.codec)[0], identity_changes=placements,
            next_incarnation_id=4, new_segments=(), required_format_version=5, metadata=metadata(1)).pin
        cat = IdentityCatalog(store)
        assert cat.read_owner_identity(pin, (NAMESPACE, (1, 0))).occurrences == tuple(zip(paths, (2, 3)))
        assert cat.read_identity_group(pin, 2).occurrences == ((NAMESPACE, (1, 0), paths[0]),)
        from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
        adapter = AUXILIARY_OWNER_FAMILIES[NAMESPACE]
        assert adapter.resolve_path(change.value, paths[0]) == RecordReference(2)
        replacement = adapter.replace_path(change.value, paths[0], RecordReference(3))
        assert adapter.resolve_path(replacement, paths[0]) == RecordReference(3)
        store.release_pin(pin)


@pytest.mark.parametrize('history', [1000, 10000])
def test_record_point_reads_and_old_generation_are_independent_of_unrelated_headers(tmp_path, history, record_property):
    with store_at(tmp_path / 'records.sqlite') as store:
        source = ActionRecord(1, 2, 'work', 'wealth', .5)
        header = record_header(source)
        pin = store.commit(store.capture_pin(), commit_token='record-base', changes=(),
            version_changes=tuple(VersionChange(NAMESPACE, (i, 0), header) for i in range(1, history + 1)),
            next_incarnation_id=history + 1, new_segments=(), required_format_version=5, metadata=metadata(1)).pin
        old = store.capture_pin()
        source.strength = .75
        pin = store.commit(pin, commit_token='record-edit', changes=(),
            version_changes=(VersionChange(NAMESPACE, (1, 0), record_header(source)),),
            next_incarnation_id=history + 1, new_segments=(), metadata=metadata(2)).pin
        store.reset_diagnostics()
        assert restore_record_header(read_record_header(store, pin, 1)).strength == .75
        now = store.diagnostics()
        assert now.payload_reads == 1 and now.metadata_rows <= 20
        record_property('history', history)
        record_property('payload_reads', now.payload_reads)
        record_property('metadata_rows', now.metadata_rows)
        record_property('payload_read_bytes', now.payload_read_bytes)
        assert restore_record_header(read_record_header(store, old, 1)).strength == .5
        with pytest.raises(StoreIntegrityError): read_record_header(store, pin, history + 1)
        store.release_pin(old)
        store.release_pin(pin)


@pytest.mark.parametrize('key,path', [
    ((0, 0), ()),
    ((True, 0), ()),
    ((1, True), ()),
    ((1, 1), ()),
    (1, ()),
    ((1, 0), (('index', 0),)),
    ((1, 0), (('field', ''),)),
    ((1, 0), (('field', 'motive'), ('index', -1))),
])
def test_record_physical_paths_reject_invalid_owner_addresses(key, path):
    from ate_sim.persistence_lazy_identity_catalog import placement_path
    with pytest.raises(StoreIntegrityError): placement_path(NAMESPACE, key, path)


def test_record_physical_path_must_belong_to_its_declared_record():
    from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    adapter = AUXILIARY_OWNER_FAMILIES[NAMESPACE]
    header = record_header(ActionRecord(1, 2, 'work', 'wealth', .5))
    with pytest.raises(StoreIntegrityError, match='undeclared field'):
        adapter.resolve_path(header, (('field', 'provenance'),))
    with pytest.raises(StoreIntegrityError, match='absent'):
        adapter.resolve_path(header, (('field', 'motive'), ('index', 99)))


@pytest.mark.parametrize('kind', ['ordinary', 'schema', 'membership'])
def test_record_physical_source_cannot_acquire_incompatible_authority(tmp_path, kind):
    from ate_sim.incremental_store import Membership
    header = record_header(ActionRecord(1, 2, 'work', 'wealth', .5))
    with store_at(tmp_path / 'bad-source.sqlite') as store:
        args = {'ordinary_changes': (RecordChange(NAMESPACE, (1, 0), header),)} if kind == 'ordinary' else {}
        versions = () if kind == 'ordinary' else (VersionChange(NAMESPACE, (1, 0), header,
            record_schema=2 if kind == 'schema' else 1,
            memberships=(Membership('unexpected', 1, 0),) if kind == 'membership' else ()),)
        with pytest.raises(StoreIntegrityError):
            initial_catalog_delta(store.codec, versions, (), next_incarnation_id=2, generation=1, **args)


@pytest.mark.parametrize('node', [['typed-record/v1'], ['typed-record/v1', 1, 2], ['typed-record/v1', None]])
def test_record_reference_wire_shape_is_closed(node):
    with pytest.raises(CodecError): WorldCodec().decode(json.dumps(node).encode())


def test_record_header_reads_after_fresh_store_open_without_bootstrap(tmp_path):
    path = tmp_path / 'reopened.sqlite'
    source = ActionRecord(1, 2, 'work', 'wealth', .5, Ref('event', 3))
    with store_at(path) as store:
        pin = store.commit(store.capture_pin(), commit_token='record-reopen', changes=(),
            version_changes=(VersionChange(NAMESPACE, (1, 0), record_header(source)),),
            next_incarnation_id=2, new_segments=(), required_format_version=5, metadata=metadata(1)).pin
        store.release_pin(pin)
    with LazyRecordStore.open(path, codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA, expected_rules_id='record-headers') as store:
        pin = store.capture_pin()
        store.reset_diagnostics()
        restored = restore_record_header(read_record_header(store, pin, 1))
        assert type(restored) is ActionRecord and restored == source
        assert type(restored.event_id) is Ref
        assert store.diagnostics().payload_reads == 1
        store.release_pin(pin)
