import pytest

from ate_sim.incremental_store import Membership, StoreIntegrityError, TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange


def make_store(tmp_path):
    return LazyRecordStore.create(tmp_path / 'query.sqlite', codec=TypedCodec(), simulation_schema='query-tests', rules_id='query-tests')


def commit(store, pin, token, changes):
    return store.commit(pin, commit_token=token, version_changes=tuple(changes), changes=(), new_segments=(), metadata={'simulation_position': 0, 'seed': 7, 'next_ids': {}, 'namespaces': ('rows',)})


@pytest.mark.parametrize('history', [1000, 10000])
def test_limited_memberships_exclude_dirty_owners_in_sql(tmp_path, history):
    with make_store(tmp_path) as store:
        pin = store.capture_pin()
        pin = commit(store, pin, 'initial', (
            VersionChange('rows', key, key, memberships=(Membership('group', 'hot', key),))
            for key in range(history)
        )).pin
        before = store.diagnostics()
        result = store.query_memberships(pin, 'rows', 'group', 'hot', limit=5, exclude_keys=(0, 2))
        after = store.diagnostics()
        assert result == ((1, 1), (3, 3), (4, 4), (5, 5), (6, 6))
        assert after.query_rows - before.query_rows == 5
        assert after.payload_reads == before.payload_reads


def test_memberships_preserve_duplicate_occurrence_positions_and_old_pin(tmp_path):
    with make_store(tmp_path) as store:
        writer = store.capture_pin()
        writer = commit(store, writer, 'initial', [
            VersionChange('rows', 'a', 1, memberships=(Membership('group', 'hot', 2), Membership('group', 'hot', 7))),
            VersionChange('rows', 'b', 2, memberships=(Membership('group', 'hot', 4),)),
        ]).pin
        reader = store.capture_pin()
        writer = commit(store, writer, 'edit', [VersionChange('rows', 'a', 3, memberships=(Membership('group', 'cold', 2),))]).pin
        assert store.query_memberships(reader, 'rows', 'group', 'hot', limit=2) == (('a', 2), ('b', 4))
        assert store.query_memberships(writer, 'rows', 'group', 'hot', limit=5) == (('b', 4),)
        assert store.query_keys(reader, 'rows', 'group', 'hot') == ('a', 'b', 'a')
        assert store.query_memberships(reader, 'rows', 'group', 'hot', limit=0) == ()


@pytest.mark.parametrize('limit', [-1, True, 1.0, '5'])
def test_limit_requires_exact_nonnegative_int(tmp_path, limit):
    with make_store(tmp_path) as store:
        pin = store.capture_pin()
        with pytest.raises(ValueError):
            store.query_memberships(pin, 'rows', 'group', 'hot', limit=limit)


def test_limited_query_checks_returned_membership_checksum(tmp_path):
    with make_store(tmp_path) as store:
        pin = store.capture_pin()
        pin = commit(store, pin, 'initial', [VersionChange('rows', 1, 1, memberships=(Membership('group', 'hot', 0),))]).pin
        store.db.execute("UPDATE lazy_query_versions SET row_checksum='bad'")
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match='query checksum'):
            store.query_memberships(pin, 'rows', 'group', 'hot', limit=1)


def test_limited_boundary_cannot_hide_overlapping_visible_membership(tmp_path):
    from ate_sim.persistence_lazy_store import _query_checksum
    with make_store(tmp_path) as store:
        pin = store.capture_pin()
        pin = commit(store, pin, 'initial', [VersionChange('rows', 1, 1, memberships=(Membership('group', 'hot', 0),))]).pin
        value, key = store.codec.encode('hot'), store.codec.encode(1)
        store.db.execute('INSERT INTO lazy_query_versions VALUES (?,?,?,?,?,0,NULL,?)', ('rows', 'group', value, key, 0, _query_checksum('rows', 'group', value, key, 0, 0, None)))
        store.db.commit()
        with pytest.raises(StoreIntegrityError, match='overlapping|duplicate'):
            store.query_memberships(pin, 'rows', 'group', 'hot', limit=1)
