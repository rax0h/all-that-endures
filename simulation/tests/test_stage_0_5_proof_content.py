"""Content proof preimages bind physical source identity and exact opaque bytes."""
import hashlib
import importlib
import tracemalloc

import pytest

from ate_sim.incremental_store import StoreIntegrityError


def content():
    return importlib.import_module('ate_sim.persistence_proof_content')


def frame(*parts):
    return b''.join(len(part).to_bytes(8, 'big') + part for part in parts)


def version_fields():
    return dict(valid_from=17, codec_version=1, record_schema=3,
                memberships=b'opaque\x00membership\xff', payload=b'\xffNaN:-0.0\x00')


def record_fields():
    return dict(last_changed_generation=17, codec_version=1, record_schema=3,
                payload=b'\xffNaN:-0.0\x00')


def segment_fields():
    return dict(created_generation=17, codec_version=1, element_count=2,
                first_id=b'\x00first', last_id=b'last\xff', payload=b'\xffNaN:-0.0\x00')


def test_key_and_content_vectors_use_independent_exact_framing():
    c = content(); ns = 'mémoire'; encoded = ns.encode('utf-8'); key = b'key\x00\xff'
    assert c.version_key(ns, key) == frame(b'ate-proof-key-version/1', encoded, key)
    assert c.record_key(ns, key) == frame(b'ate-proof-key-record/1', encoded, key)
    assert c.segment_key(ns, 4) == frame(b'ate-proof-key-segment/1', encoded, b'4')
    assert c.version_commitment(ns, key, **version_fields()) == hashlib.sha256(frame(
        b'ate-proof-content-version/1', encoded, key, b'17', b'1', b'3',
        b'opaque\x00membership\xff', b'\xffNaN:-0.0\x00')).digest()
    assert c.record_commitment(ns, key, **record_fields()) == hashlib.sha256(frame(
        b'ate-proof-content-record/1', encoded, key, b'17', b'1', b'3', b'\xffNaN:-0.0\x00')).digest()
    assert c.segment_commitment(ns, 4, **segment_fields()) == hashlib.sha256(frame(
        b'ate-proof-content-segment/1', encoded, b'4', b'17', b'1', b'2',
        b'\x00first', b'last\xff', b'\xffNaN:-0.0\x00')).digest()


@pytest.mark.parametrize('kind,fields', [('version', version_fields), ('record', record_fields), ('segment', segment_fields)])
def test_every_source_field_and_namespace_key_affects_commitment(kind, fields):
    c = content(); function = getattr(c, kind + '_commitment'); base = fields()
    key = 4 if kind == 'segment' else b'key'
    original = function('source', key, **base)
    assert original != function('other', key, **base)
    assert original != function('source', 5 if kind == 'segment' else b'other', **base)
    for name, field in base.items():
        changed = dict(base); changed[name] = field + 1 if type(field) is int else field + b'!'
        assert original != function('source', key, **changed), name


@pytest.mark.parametrize('namespace', ['', 'bad\x00name', b'bytes', True, '\ud800'])
def test_invalid_namespace_is_rejected(namespace):
    c = content()
    for function, key in [(c.version_key, b'k'), (c.record_key, b'k'), (c.segment_key, 0)]:
        with pytest.raises(StoreIntegrityError):
            function(namespace, key)


@pytest.mark.parametrize('kind,fields', [('version', version_fields), ('record', record_fields), ('segment', segment_fields)])
def test_invalid_types_and_negative_counters_are_rejected(kind, fields):
    c = content(); function = getattr(c, kind + '_commitment'); base = fields()
    key = 4 if kind == 'segment' else b'key'
    for name, field in base.items():
        invalid = [True, -1, 1.0] if type(field) is int else [bytearray(field), 'text', None]
        if name in ('codec_version', 'record_schema'):
            invalid.append(0)
        for bad in invalid:
            changed = dict(base); changed[name] = bad
            with pytest.raises(StoreIntegrityError):
                function('source', key, **changed)
    for bad in ([True, -1, 1.0] if kind == 'segment' else [bytearray(b'k'), 'k', None]):
        with pytest.raises(StoreIntegrityError):
            function('source', bad, **base)


def test_interval_close_preserves_immutable_content_but_is_not_a_selection_proof(tmp_path):
    from ate_sim.incremental_store import TypedCodec
    from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange
    c = content()
    with LazyRecordStore.create(tmp_path/'source.sqlite', codec=TypedCodec(),
                                simulation_schema='8', rules_id='proof-test') as store:
        pin = store.capture_pin()
        metadata = dict(simulation_position=1, seed=7, next_ids={}, namespaces=('people',))
        first = store.commit(pin, commit_token='first', version_changes=[VersionChange('people', 'key', {'wealth':3})],
                             changes=(), new_segments=(), metadata=metadata)
        old_pin = store.capture_pin()
        def source_row():
            row = store.db.execute('SELECT typed_key,valid_from,codec_version,record_schema,memberships,payload,'
                                   'valid_to,row_checksum FROM lazy_record_versions WHERE valid_from=1').fetchone()
            fields = dict(zip(('valid_from','codec_version','record_schema','memberships','payload'), row[1:6]))
            return row, c.version_commitment('people', row[0], **fields), fields
        old_row, before, _ = source_row()
        store.commit(first.pin, commit_token='second', version_changes=[VersionChange('people', 'key', {'wealth':4})],
                     changes=(), new_segments=(), metadata=dict(metadata, simulation_position=2))
        closed_row, after, fields = source_row()
        assert old_row[6] is None and closed_row[6] == 2
        assert old_row[7] != closed_row[7]  # mutable interval checksum changed
        assert after == before
        assert store.read_version(old_pin, 'people', 'key', expected_record_schema=1).value == {'wealth':3}
        with pytest.raises(TypeError):
            c.version_commitment('people', closed_row[0], valid_to=2, **fields)
        fields['valid_from'] = 2
        assert c.version_commitment('people', closed_row[0], **fields) != before


def test_large_payload_hash_does_not_copy_the_full_frame():
    c = content(); payload = b'x' * (2 * 1024 * 1024)
    expected = hashlib.sha256(frame(b'ate-proof-content-record/1', b'source', b'key', b'0', b'1', b'1', payload)).digest()
    tracemalloc.start()
    try:
        result = c.record_commitment('source', b'key', last_changed_generation=0,
                                     codec_version=1, record_schema=1, payload=payload)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert result == expected
    assert peak < 128 * 1024
