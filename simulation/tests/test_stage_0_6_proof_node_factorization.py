"""SQL proof reads do one canonical parse while retaining both hash boundaries."""
import cProfile
import hashlib
import importlib
import pstats
import sqlite3
from types import SimpleNamespace

import pytest

from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_nodes import Branch, Root, decode_node, encode_node, node_digest
from ate_sim.persistence_proof_store import ProofNodeStore


def _factory(db, family):
    store = SimpleNamespace(db=db, store_identity='factorization-test',
                            codec=SimpleNamespace(version=1))
    name, *argument = family.split(':')
    module = importlib.import_module('ate_sim.persistence_proof_' + name)
    args = ([int(argument[0])] if name == 'scope' else
            [argument[0] == 'event'] if name == 'publication' else
            [b'factorization-test'] if name == 'world' else [])
    return module._map(store, *args)


@pytest.mark.parametrize('family', [
    'record', 'reference', 'scope:0', 'scope:3', 'scope:6',
    'publication:version', 'publication:event', 'world',
])
def test_sql_map_point_lookups_parse_each_fetched_node_once(family):
    # Reintroducing store+map parsing or decoder re-encoding repeats real work.
    with sqlite3.connect(':memory:') as db:
        ProofNodeStore(db).create_schema()
        mapping = _factory(db, family)
        root = mapping.empty
        db.execute('BEGIN')
        for i in range(96):
            root = mapping.set(root, str(i).encode(), hashlib.sha256(str(i).encode()).digest())
        db.commit()
        reads = []
        db.set_trace_callback(reads.append)
        profile = cProfile.Profile()
        profile.enable()
        try:
            assert mapping.get(root, b'7') == hashlib.sha256(b'7').digest()
            assert mapping.get(root, b'absent') is None
        finally:
            profile.disable()
            db.set_trace_callback(None)
        fetched = sum(sql.startswith('SELECT CASE WHEN typeof(node_bytes)') for sql in reads)
        stats = pstats.Stats(profile).stats
        calls = lambda name: sum(v[1] for (file, _, func), v in stats.items()
                                 if file.endswith('/persistence_proof_nodes.py') and func == name)
        assert fetched >= 3  # Real multi-level positive and negative paths.
        assert calls('decode_node') == fetched
        assert calls('encode_node') == 0


def test_branch_parser_checks_canonical_bytes_without_encoder_roundtrip():
    # Encoder calls on a valid branch are avoidable work, independent of timing.
    raw = (b'ATEP\x01B\x03\xab\xc0\x02'
           + b'\x02' + (1).to_bytes(8, 'big') + b'x' * 32
           + b'\x0f' + (4).to_bytes(8, 'big') + b'y' * 32)
    expected = Branch((10, 11, 12), ((2, Root(b'x' * 32, 1)), (15, Root(b'y' * 32, 4))))
    profile = cProfile.Profile()
    profile.enable()
    try:
        assert decode_node(raw) == expected
    finally:
        profile.disable()
    calls = sum(v[1] for (file, _, name), v in pstats.Stats(profile).stats.items()
                if file.endswith('/persistence_proof_nodes.py') and name == 'encode_node')
    assert calls == 0
    assert encode_node(expected) == raw


@pytest.mark.parametrize('family', ['query', 'version', 'occurrence'])
def test_checked_sql_readers_parse_each_fetched_node_once(tmp_path, family):
    # These three production readers construct SQL callbacks without _map.
    if family == 'query':
        from simulation.tests.proof_query_fixtures import make_store, construct_certificate
        from ate_sim.persistence_proof_query import read_query_page
        store, pin = make_store(tmp_path / 'source.sqlite', 8)
        cert, expected = construct_certificate(store, pin)
        def read():
            assert len(read_query_page(store, pin, cert, expected, limit=3).positions) == 3
            assert read_query_page(store, pin, cert, expected,
                                   after=(999, b'end')).positions == ()
    elif family == 'version':
        from simulation.tests.test_stage_0_5_proof_version import setup_source, read as version_read
        module, store, pin, cert, expected = setup_source(tmp_path)
        def read():
            assert version_read(module, store, pin, cert, expected).payload == store.codec.encode({'wealth': 2})
            assert version_read(module, store, pin, cert, expected, key=999) is None
    else:
        from simulation.tests.test_stage_0_5_proof_occurrence import setup_source
        module, store, pin, certs = setup_source(tmp_path)
        def read():
            assert len(module.read_occurrence_page(store, pin, *certs[0], limit=3).rows) == 3
            assert module.read_occurrence_page(store, pin, *certs[0], after=('zz', b'', b'')).rows == ()
    reads = []
    profile = cProfile.Profile()
    store.db.set_trace_callback(reads.append)
    profile.enable()
    try:
        read()
    finally:
        profile.disable()
        store.db.set_trace_callback(None)
        store.close()
    fetched = sum(sql.startswith('SELECT CASE WHEN typeof(node_bytes)') for sql in reads)
    stats = pstats.Stats(profile).stats
    calls = lambda name: sum(v[1] for (file, _, func), v in stats.items()
                             if file.endswith('/persistence_proof_nodes.py') and func == name)
    assert fetched > 0
    assert calls('decode_node') == fetched
    assert calls('encode_node') == 0


@pytest.mark.parametrize('outer_wrong', [False, True])
def test_sql_map_retains_physical_and_outer_domain_hashes(outer_wrong):
    # Dropping either hash permits a wrong-domain callback to authenticate a row.
    raw = b'ATEP\x01L' + b'k' * 32 + b'v' * 32
    correct, wrong = b'correct-domain', b'wrong-domain'
    digest = node_digest(correct, raw)
    physical, outer = (correct, wrong) if outer_wrong else (wrong, correct)
    with sqlite3.connect(':memory:') as db:
        nodes = ProofNodeStore(db)
        nodes.create_schema()
        db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)', (physical, digest, raw))
        mapping = ProofMap(outer, lambda d: nodes._read_bound_bytes(physical, d), None)
        message = '^proof node digest' if outer_wrong else '^stored proof node digest'
        with pytest.raises(StoreIntegrityError, match=message):
            mapping._read(Root(digest, 1))


@pytest.mark.parametrize('reader', ['public', 'map'])
def test_hash_consistent_noncanonical_sql_node_still_rejects(reader):
    # Factoring the fetch must leave canonical validation at each public boundary.
    raw = (b'ATEP\x01B\x00\x02'
           + b'\x01' + (1).to_bytes(8, 'big') + b'x' * 32
           + b'\x00' + (1).to_bytes(8, 'big') + b'y' * 32)
    domain = b'noncanonical-domain'
    digest = node_digest(domain, raw)
    with sqlite3.connect(':memory:') as db:
        nodes = ProofNodeStore(db)
        nodes.create_schema()
        db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)', (domain, digest, raw))
        with pytest.raises(StoreIntegrityError):
            if reader == 'public':
                nodes.read(domain, digest)
            else:
                ProofMap(domain, lambda d: nodes._read_bound_bytes(domain, d), None)._read(Root(digest, 2))


def test_public_sql_store_read_still_parses_once():
    raw = b'ATEP\x01L' + b'k' * 32 + b'v' * 32
    domain = b'public-domain'
    digest = node_digest(domain, raw)
    with sqlite3.connect(':memory:') as db:
        nodes = ProofNodeStore(db)
        nodes.create_schema()
        db.execute('INSERT INTO ate_proof_nodes VALUES(?,?,?)', (domain, digest, raw))
        profile = cProfile.Profile()
        profile.enable()
        try:
            assert nodes.read(domain, digest) == raw
        finally:
            profile.disable()
        calls = sum(v[1] for (file, _, name), v in pstats.Stats(profile).stats.items()
                    if file.endswith('/persistence_proof_nodes.py') and name == 'decode_node')
        assert calls == 1
        assert nodes.diagnostics()['read_nodes'] == 1
        assert nodes.diagnostics()['read_bytes'] == 70
