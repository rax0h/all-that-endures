"""Closed native NaN bodies and references; ordinary admission is still gated."""
import importlib
import json
import math
import struct

import pytest

from ate_sim.incremental_store import CodecError, StoreIntegrityError
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_identity_catalog import initial_catalog_delta, IdentityCatalog
from simulation.tests.test_stage_0_5_final_record_headers import store_at, metadata


def api():
    return importlib.import_module('ate_sim.persistence_nonreflexive_keys')


def test_native_nan_reference_has_a_closed_codec_tag():
    m = api()
    codec = WorldCodec(identity_links_recorded=True)
    ref = m.NonreflexiveKeyReference(7)
    assert m.nonreflexive_key_reference(ref)
    assert codec.decode(codec.encode((ref,))) == (ref,)
    assert json.loads(codec.encode(ref)) == [m.REFERENCE_TAG, 7]


@pytest.mark.parametrize('invalid', [True, 0, -1, 1.0, '1', None])
def test_reference_ids_are_positive_exact_integers(invalid):
    m = api()
    codec = WorldCodec(identity_links_recorded=True)
    with pytest.raises(ValueError):
        m.NonreflexiveKeyReference(invalid)
    forged = m.NonreflexiveKeyReference(7)
    object.__setattr__(forged, 'incarnation', invalid)
    assert not m.nonreflexive_key_reference(forged)
    with pytest.raises(CodecError):
        codec.encode(forged)
    with pytest.raises(CodecError):
        codec.decode(json.dumps([m.REFERENCE_TAG, invalid]).encode())


@pytest.mark.parametrize('bits', [0x7ff8000000000001, 0xfff8000000000002, 0x7ff0000000000001])
def test_header_preserves_exact_nan_bits_and_native_float_type(bits):
    m = api()
    raw = bits.to_bytes(8, 'big')
    source = struct.unpack('>d', raw)[0]
    header = m.nonreflexive_key_header(source)
    codec = WorldCodec(identity_links_recorded=True)
    restored = m.restore_nonreflexive_key_header(codec.decode(codec.encode(header)))
    assert type(restored) is float and math.isnan(restored)
    assert m.checked_nonreflexive_key_header(header) == raw
    assert struct.pack('>d', restored) == raw
    assert restored is not source


@pytest.mark.parametrize('value', [True, 1, 1.0, float('inf'), 'nan', None])
def test_native_header_admission_rejects_other_values(value):
    with pytest.raises(TypeError, match='native NaN'):
        api().nonreflexive_key_header(value)


@pytest.mark.parametrize('bad', ['tag', 'short', 'long', 'mutable', 'size', 'finite'])
def test_header_validation_fails_closed(bad):
    m = api()
    header = m.nonreflexive_key_header(float('nan'))
    if bad == 'tag':
        header = ('native-key/v999', header[1])
    elif bad == 'short':
        header = header[:1]
    elif bad == 'long':
        header += (None,)
    elif bad == 'mutable':
        header = (header[0], bytearray(header[1]))
    elif bad == 'size':
        header = (header[0], header[1][:-1])
    else:
        header = (header[0], struct.pack('>d', 1.0))
    with pytest.raises(StoreIntegrityError):
        m.restore_nonreflexive_key_header(header)


def test_atom_header_is_a_checked_physical_owner_with_no_children(tmp_path):
    m = api()
    from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
    adapter = AUXILIARY_OWNER_FAMILIES[m.NAMESPACE]
    change = VersionChange(m.NAMESPACE, (1, 0), m.nonreflexive_key_header(float('nan')))
    adapter.validate_source(change, 'lazy', WorldCodec())
    assert adapter.reference_placements(change.value) == ()
    with pytest.raises(StoreIntegrityError):
        adapter.validate_path((('index', 0),))
    with pytest.raises(StoreIntegrityError):
        adapter.validate_key((1, 1))
    with store_at(tmp_path / 'atoms.sqlite') as store:
        delta = initial_catalog_delta(store.codec, (change,), (), next_incarnation_id=2, generation=1)
        pin = store.commit(store.capture_pin(), commit_token='atom-catalog', changes=(),
            version_changes=(change,) + delta.decode(store.codec)[0], identity_changes=(),
            next_incarnation_id=2, new_segments=(), required_format_version=5, metadata=metadata(1)).pin
        assert IdentityCatalog(store).read_owner_identity(pin, (m.NAMESPACE, (1, 0))).occurrences == ()
        assert m.read_nonreflexive_key_header(store, pin, 1) == change.value


def test_missing_or_invalid_stored_atom_is_an_integrity_failure(tmp_path):
    m = api()
    with store_at(tmp_path / 'bad-atoms.sqlite') as store:
        pin = store.capture_pin()
        with pytest.raises(StoreIntegrityError, match='absent'):
            m.read_nonreflexive_key_header(store, pin, 1)
        invalid = (m.TAG, struct.pack('>d', 1.0))
        pin = store.commit(pin, commit_token='atom-invalid', changes=(),
            version_changes=(VersionChange(m.NAMESPACE, (1, 0), invalid),),
            next_incarnation_id=2, new_segments=(), required_format_version=5, metadata=metadata(1)).pin
        with pytest.raises(StoreIntegrityError):
            m.read_nonreflexive_key_header(store, pin, 1)


def test_copy_cannot_silently_skip_unbacked_atom_references():
    m = api()
    from ate_sim.persistence_catalog_copy import _check_reference_targets
    with pytest.raises(StoreIntegrityError, match='NaN.*backing'):
        _check_reference_targets(({'key': m.NonreflexiveKeyReference(1)},), ())


def test_atom_point_reads_and_pins_do_not_depend_on_history_size(tmp_path, record_property):
    m = api()
    metrics = []
    for size in (1000, 10000):
        with store_at(tmp_path / f'atom-{size}.sqlite') as store:
            header = m.nonreflexive_key_header(float('nan'))
            pin = store.commit(store.capture_pin(), commit_token='atom-base', changes=(),
                version_changes=tuple(VersionChange(m.NAMESPACE, (inc, 0), header) for inc in range(1, size + 1)),
                next_incarnation_id=size + 1, new_segments=(), required_format_version=5, metadata=metadata(1)).pin
            old = store.capture_pin()
            pin = store.commit(pin, commit_token='atom-unrelated', changes=(), version_changes=(),
                next_incarnation_id=size + 1, new_segments=(), required_format_version=5, metadata=metadata(2)).pin
            store.reset_diagnostics()
            assert m.read_nonreflexive_key_header(store, old, 1) == header
            assert m.read_nonreflexive_key_header(store, pin, 1) == header
            observed = store.diagnostics()
            metrics.append((observed.payload_reads, observed.metadata_rows))
            record_property(f'H{size}_payload_reads', observed.payload_reads)
            record_property(f'H{size}_metadata_rows', observed.metadata_rows)
            store.release_pin(old)
    assert metrics[0] == metrics[1]
