"""Fetched source bytes need exact content authority as well as row checksums."""
from dataclasses import replace
import hashlib
import tracemalloc

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError, StoreConflictError
from ate_sim.persistence_lazy_store import VersionChange, _version_checksum
from ate_sim.incremental_store import _framed_sha
from simulation.tests.proof_query_fixtures import make_store, metadata
from simulation.tests.proof_version_fixtures import version_module, construct_version_certificate
from simulation.tests.test_stage_0_5_proof_order import frame


def setup_source(tmp_path):
    store, pin = make_store(tmp_path/'source.sqlite', 8)
    certificate, expected = construct_version_certificate(store, pin)
    return version_module(), store, pin, certificate, expected


def read(v, store, pin, cert, expected, key=2, **kwargs):
    return v.read_version_bytes(store, pin, cert, expected, 'people', store.codec.encode(key),
                                expected_record_schema=1, **kwargs)


def test_independent_content_certificate_framing(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    domain = hashlib.sha256(frame(b'ate-version-proof-domain/1', store.store_identity.encode(), b'1')).digest()
    assert v.version_domain(store.store_identity, 1) == domain
    assert expected == hashlib.sha256(frame(b'ate-version-certificate/1', domain,
        b'\x00'*7+b'\x01', cert.content.digest, cert.content.count.to_bytes(8, 'big'))).digest()
    store.close()


def test_exact_raw_bytes_no_decoding_or_unrelated_tables(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    sql = []
    store.reset_diagnostics()
    store.db.set_trace_callback(sql.append)
    raw = read(v, store, pin, cert, expected)
    assert raw.payload == store.codec.encode({'wealth': 2})
    assert raw.memberships == store.codec.encode((('cohort', 'active', 4), ('cohort', 'active', 5)))
    assert (raw.record_schema, raw.valid_from, raw.valid_to) == (1, 1, None)
    assert store._payload_check_reads == 1 and store._payload_reads == 0
    assert read(v, store, pin, cert, expected, 999) is None
    assert store._payload_check_reads == 1
    store.db.set_trace_callback(None)
    selects = [s for s in sql if s.lstrip().upper().startswith('SELECT')]
    assert not any('FROM '+t in s for s in selects for t in ('records', 'segments', 'lazy_query_versions', 'lazy_order_versions'))
    assert len([s for s in selects if 'FROM lazy_record_versions' in s]) == 2
    assert not store.db.in_transaction
    store.close()


@pytest.mark.parametrize('delete', [False, True])
def test_old_and_current_pin_bytes_after_change_or_delete(tmp_path, delete):
    v, store, pin, cert, expected = setup_source(tmp_path)
    old_pin = store.capture_pin()
    result = store.commit(pin, commit_token='change', version_changes=(VersionChange('people', 2,
        delete=True) if delete else VersionChange('people', 2, {'wealth': 22}),),
        changes=(), new_segments=(), metadata=metadata(2))
    current, current_expected = construct_version_certificate(store, result.pin)
    previous = read(v, store, old_pin, cert, expected)
    assert previous.payload == store.codec.encode({'wealth': 2})
    assert previous.valid_to == 2
    changed = read(v, store, result.pin, current, current_expected)
    if delete:
        assert changed is None
    else:
        assert changed.payload == store.codec.encode({'wealth': 22}) and changed.valid_from == 2
    with pytest.raises((StoreConflictError, StoreIntegrityError)):
        read(v, store, result.pin, cert, expected)
    store.release_pin(old_pin)
    with pytest.raises(StoreConflictError):
        read(v, store, old_pin, cert, expected)
    store.close()


@pytest.mark.parametrize('field', ['store', 'generation', 'codec', 'root', 'expected', 'schema'])
def test_wrong_context_or_authority_fails(tmp_path, field):
    v, store, pin, cert, expected = setup_source(tmp_path)
    if field == 'store': cert = replace(cert, store_identity='another')
    elif field == 'generation': cert = replace(cert, generation=0)
    elif field == 'codec': cert = replace(cert, codec_version=2)
    elif field == 'root': cert = replace(cert, content=replace(cert.content, digest=b'x'*32))
    elif field == 'schema':
        with pytest.raises(StoreIntegrityError):
            v.read_version_bytes(store, pin, cert, expected, 'people', store.codec.encode(2), expected_record_schema=2)
        store.close(); return
    else: expected = b'x'*32
    with pytest.raises((StoreConflictError, StoreIntegrityError)):
        read(v, store, pin, cert, expected)
    store.close()


@pytest.mark.parametrize('fault', ['payload', 'memberships', 'row_checksum', 'payload_checksum',
    'missing', 'surplus', 'coherent', 'overlap', 'proof'])
def test_physical_corruption_omission_surplus_and_overlap_rejected(tmp_path, fault):
    v, store, pin, cert, expected = setup_source(tmp_path)
    key = store.codec.encode(2)
    if fault in ('payload', 'memberships', 'row_checksum', 'payload_checksum'):
        value = b'bad' if fault in ('payload', 'memberships') else '0'*64
        store.db.execute('UPDATE lazy_record_versions SET '+fault+'=? WHERE typed_key=?', (value, key))
    elif fault == 'missing':
        store.db.execute('DELETE FROM lazy_record_versions WHERE typed_key=?', (key,))
    elif fault == 'proof':
        store.db.execute('DELETE FROM ate_proof_nodes WHERE digest=?', (cert.content.digest,))
    else:
        row = list(store.db.execute('SELECT namespace,typed_key,valid_from,valid_to,payload,payload_checksum,'
            'codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions WHERE typed_key=?', (key,)).fetchone())
        if fault == 'surplus': row[1] = store.codec.encode(999)
        elif fault == 'overlap': row[2] = 0
        else: row[4] = store.codec.encode({'wealth': 900})
        row[5] = _framed_sha(b'lazy-payload-v1', row[4])
        row[9] = _version_checksum(row[0], row[1], row[7], row[6], row[2], row[3], row[8], row[4])
        if fault == 'coherent':
            store.db.execute('DELETE FROM lazy_record_versions WHERE typed_key=?', (key,))
        store.db.execute('INSERT INTO lazy_record_versions VALUES(?,?,?,?,?,?,?,?,?,?)', row)
    store.db.commit()
    with pytest.raises(StoreIntegrityError):
        read(v, store, pin, cert, expected, 999 if fault == 'surplus' else 2)
    store.close()


@pytest.mark.parametrize('column,value', [('payload', 'text'), ('memberships', 'text'),
    ('row_checksum', b'x'*64), ('payload_checksum', 'short'), ('codec_version', 'bad'), ('record_schema', 'bad')])
def test_malformed_storage_types_are_rejected(tmp_path, column, value):
    v, store, pin, cert, expected = setup_source(tmp_path)
    store.db.execute('UPDATE lazy_record_versions SET '+column+'=? WHERE typed_key=?', (value, store.codec.encode(2)))
    store.db.commit()
    with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected)
    store.close()


@pytest.mark.parametrize('column,value,budget_error', [('payload', b'x'*(2*1024*1024), True),
    ('memberships', b'x'*(2*1024*1024), True), ('payload', 'x'*(2*1024*1024), False),
    ('row_checksum', 'x'*64+'\x00'+'x'*(2*1024*1024), False)],
    ids=['large-payload', 'large-memberships', 'large-text-payload', 'nul-checksum'])
def test_large_malformed_bodies_rejected_before_transfer(tmp_path, column, value, budget_error):
    v, store, pin, cert, expected = setup_source(tmp_path)
    store.db.execute('UPDATE lazy_record_versions SET '+column+'=? WHERE typed_key=?', (value, store.codec.encode(2)))
    store.db.commit()
    tracemalloc.start()
    try:
        with pytest.raises(v.VersionProofBudgetError if budget_error else StoreIntegrityError):
            read(v, store, pin, cert, expected)
        _, peak = tracemalloc.get_traced_memory()
    finally: tracemalloc.stop()
    assert peak < 128*1024
    store.close()


def test_owned_nested_and_arbitrary_transactions(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    with store.read_transaction():
        with store.read_snapshot(pin):
            assert read(v, store, pin, cert, expected).payload == store.codec.encode({'wealth': 2})
            with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, b'x'*32)
            assert store.db.in_transaction
        assert store.db.in_transaction
    store.db.execute('BEGIN')
    with pytest.raises(StoreError): read(v, store, pin, cert, expected)
    assert store.db.in_transaction
    store.db.rollback()
    store.close()


@pytest.mark.parametrize('budget', [0, -1, True, 1.0, 64*1024*1024+1])
def test_invalid_budget_rejected(tmp_path, budget):
    v, store, pin, cert, expected = setup_source(tmp_path)
    with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected, max_bytes=budget)
    store.close()


def test_unread_corruption_is_not_claimed_as_scrubbed(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    store.db.execute("UPDATE lazy_record_versions SET payload=X'00' WHERE typed_key=?", (store.codec.encode(3),))
    store.db.commit()
    assert read(v, store, pin, cert, expected).payload == store.codec.encode({'wealth': 2})
    with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected, 3)
    store.close()


def test_large_valid_record_requires_explicit_budget(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    value = b'large-valid-record' + b'x'*(1024*1024)
    result = store.commit(pin, commit_token='large', version_changes=(VersionChange('people', 2, value),),
                          changes=(), new_segments=(), metadata=metadata(2))
    cert, expected = construct_version_certificate(store, result.pin)
    with pytest.raises(v.VersionProofBudgetError): read(v, store, result.pin, cert, expected)
    assert read(v, store, result.pin, cert, expected, max_bytes=2*1024*1024).payload == store.codec.encode(value)
    store.close()


def test_snapshot_failure_keeps_owned_transaction_and_detects_external_edit(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    key = store.codec.encode(2)
    with store.read_transaction():
        store.db.execute("UPDATE lazy_record_versions SET row_checksum='bad' WHERE typed_key=?", (key,))
        with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected)
        assert store.db.in_transaction
    # The read transaction rolls back its caller's experimental edit.
    assert read(v, store, pin, cert, expected).payload == store.codec.encode({'wealth': 2})
    store.db.execute("UPDATE lazy_record_versions SET row_checksum='bad' WHERE typed_key=?", (key,))
    store.db.commit()
    with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected)
    assert not store.db.in_transaction
    store.close()


def test_foreign_and_moved_pin_fail_live_validation(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    other, foreign = make_store(tmp_path/'other.sqlite')
    with pytest.raises(StoreConflictError): read(v, store, foreign, cert, expected)
    store.commit(pin, commit_token='move', version_changes=(), changes=(), new_segments=(), metadata=metadata(2))
    with pytest.raises(StoreConflictError): read(v, store, pin, cert, expected)
    store.close(); other.close()


@pytest.mark.parametrize('table,column,blob', [
    ('save_head', 'head_checksum', False), ('generation_pins', 'row_checksum', False),
    ('pin_receipts', 'row_checksum', False), ('pin_attempts', 'row_checksum', False),
    ('save_head', 'next_ids', True), ('pin_receipts', 'commit_token', True),
    ('pin_attempts', 'commit_token', True)])
def test_operational_metadata_guard_precedes_materialization(tmp_path, table, column, blob):
    v, store, pin, cert, expected = setup_source(tmp_path)
    value = b'x'*(2*1024*1024) if blob else 'x'*64+'\x00'+'x'*(2*1024*1024)
    store.db.execute(f'UPDATE {table} SET {column}=?', (value,))
    store.db.commit()
    tracemalloc.start()
    try:
        with pytest.raises(v.VersionProofBudgetError if blob else StoreIntegrityError):
            read(v, store, pin, cert, expected)
        _, peak = tracemalloc.get_traced_memory()
    finally: tracemalloc.stop()
    assert peak < 128*1024
    assert not store.db.in_transaction
    store.close()


def test_oversized_metadata_guard_also_runs_in_nested_snapshot(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    with store.read_snapshot(pin):
        store.db.execute("UPDATE generation_pins SET row_checksum=?", ('x'*(2*1024*1024),))
        tracemalloc.start()
        try:
            with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected)
            _, peak = tracemalloc.get_traced_memory()
        finally: tracemalloc.stop()
        assert peak < 128*1024 and store.db.in_transaction
    assert read(v, store, pin, cert, expected).payload == store.codec.encode({'wealth': 2})
    store.close()


def test_metadata_row_capacity_checked_without_transferring_row_bodies(tmp_path):
    v, store, pin, cert, expected = setup_source(tmp_path)
    for i in range(70):
        store.db.execute('INSERT INTO generation_pins VALUES(?,?,?,?)',
                         (str(i), store.store_identity, 1, '0'*64))
    store.db.commit()
    tracemalloc.start()
    try:
        with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected)
        _, peak = tracemalloc.get_traced_memory()
    finally: tracemalloc.stop()
    assert peak < 128*1024
    store.close()


def test_legitimate_large_head_uses_explicit_metadata_budget(tmp_path):
    from ate_sim.persistence_lazy_store import _head_checksum
    v, store, pin, cert, expected = setup_source(tmp_path)
    row = list(store.db.execute('SELECT generation,parent_generation,simulation_position,seed,next_ids,'
        'namespace_inventory,namespace_counts FROM save_head WHERE singleton=1').fetchone())
    row[4] = store.codec.encode({'large-valid-counter-name'+'x'*(1024*1024): 17})
    store.db.execute('UPDATE save_head SET next_ids=?,head_checksum=? WHERE singleton=1',
                     (row[4], _head_checksum(*row)))
    store.db.commit()
    with pytest.raises(v.VersionProofBudgetError): read(v, store, pin, cert, expected)
    assert read(v, store, pin, cert, expected, max_metadata_bytes=4*1024*1024).payload == store.codec.encode({'wealth': 2})
    store.close()


@pytest.mark.parametrize('budget', [0, -1, True, 1.0, 64*1024*1024+1])
def test_invalid_metadata_budget_rejected(tmp_path, budget):
    v, store, pin, cert, expected = setup_source(tmp_path)
    with pytest.raises(StoreIntegrityError): read(v, store, pin, cert, expected, max_metadata_bytes=budget)
    store.close()
