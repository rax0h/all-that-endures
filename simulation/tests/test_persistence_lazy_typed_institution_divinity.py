import pytest

from ate_sim.core import World
from ate_sim.culture import Practice
from ate_sim.divinity import God, GreatAstralBeing, Church
from ate_sim.institutions import Institution, Branch
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session

RULES = 'typed-institution-divinity'


def converted(tmp_path, history, alias=False):
    world = World(843000)
    world.culture.practices[1] = Practice(1, 'construction', 'drainage', 0, 1,
        {str(key): .1 for key in range(history)})
    world.divinity.gods['knowledge'] = God('knowledge', 'Knowledge', ('knowledge',),
        manifestations=list(range(history)), relationships={key: .1 for key in range(history)})
    world.divinity.great_astral_beings['builder'] = GreatAstralBeing('builder', 'Builder', ('creation',),
        interventions=list(range(history)), relationships={key: .1 for key in range(history)})
    world.divinity.churches[1] = Church(1, 'knowledge', 1, 0, 1, followers=set(range(history)))
    world.institutions.institutions[1] = Institution(1, 'magic_society', 'Magic', 0, None, branches=[1], members=set(range(history)))
    world.institutions.branches[1] = Branch(1, 1, 1, 0, None, records=set(range(history)), notices=set(range(history)))
    if alias:
        world.institutions.institutions[1].members = world.divinity.churches[1].followers
        world.currency.wallets[11] = {'followers': world.divinity.churches[1].followers,
            'relationships': world.divinity.gods['knowledge'].relationships}
    source, path = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, path, rules_id=RULES)
    return path


@pytest.mark.parametrize('history', [1000, 10000])
def test_real_nested_histories_use_bounded_points_and_header_reads(tmp_path, history):
    path = converted(tmp_path, history)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        practice = session.world.culture.practices[1]
        god = session.world.divinity.gods['knowledge']
        being = session.world.divinity.great_astral_beings['builder']
        church = session.world.divinity.churches[1]
        institution = session.world.institutions.institutions[1]
        branch = session.world.institutions.branches[1]
        assert practice.traits.diagnostics()['entry_loads'] == 0
        assert god.relationships.diagnostics()['entry_loads'] == 0
        assert god.manifestations.diagnostics()['page_loads'] == 0
        assert church.followers & set(range(8)) == set(range(8))
        assert church.followers.diagnostics()['entry_loads'] == 8
        for key in range(8):
            god.relationships[key] += .002
        assert god.relationships.diagnostics()['entry_loads'] == 8
        before = session.store.diagnostics()
        practice.name = 'renamed'
        being.name = 'Renamed'
        institution.name = 'Renamed'
        branch.authority = .7
        session.save()
        after = session.store.diagnostics()
        assert after.payload_write_bytes - before.payload_write_bytes < 32768
        assert practice.traits.diagnostics()['entry_loads'] == 0
        assert being.relationships.diagnostics()['entry_loads'] == 0
        assert god.manifestations.diagnostics()['page_loads'] == 0
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.culture.practices[1].name == 'renamed'
        assert session.world.divinity.gods['knowledge'].relationships[7] == .10200000000000001


@pytest.mark.parametrize('first', ['wallet', 'church'])
def test_typed_set_map_aliases_save_replace_and_materialize_once(tmp_path, first):
    from ate_sim import checkpoint
    path = converted(tmp_path, 5, alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        followers = session.wallets[11]['followers'] if first == 'wallet' else session.world.divinity.churches[1].followers
        assert followers is session.world.institutions.institutions[1].members
        assert followers is session.world.divinity.churches[1].followers
        followers.add(8)
        relationships = session.wallets[11]['relationships']
        relationships[9] = .5
        assert relationships is session.world.divinity.gods['knowledge'].relationships
        session.world.divinity.churches[1].followers = {20}
        followers.add(10)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.divinity.churches[1].followers == {20}
        assert 10 in session.wallets[11]['followers']
        assert session.world.divinity.gods['knowledge'].relationships[9] == .5
        detached = session.detach(materialize_history=True)
        assert detached.currency.wallets[11]['followers'] is detached.institutions.institutions[1].members
        assert detached.currency.wallets[11]['relationships'] is detached.divinity.gods['knowledge'].relationships
        assert checkpoint.loads(checkpoint.dumps(detached)).digest() == detached.digest()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_nested_maps_sets_share_frozen_failure_plan_and_recover(tmp_path, phase):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path, 5, alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        relationships = session.world.divinity.gods['knowledge'].relationships
        followers = session.world.divinity.churches[1].followers
        relationships[9] = .5
        followers.add(8)
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        plan = session._pending_save
        with pytest.raises(StoreError):
            relationships.get(0)
        with pytest.raises(StoreError):
            followers.add(10)
        assert session._pending_save is plan
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.divinity.gods['knowledge'].relationships[9] == .5
        assert 8 in session.wallets[11]['followers']


def test_nested_map_set_noop_old_pin_and_closed_alias(tmp_path):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as writer, open_lazy_world_session(path, rules_id=RULES) as reader:
        relationships = writer.world.divinity.gods['knowledge'].relationships
        followers = writer.world.divinity.churches[1].followers
        old_map = reader.world.divinity.gods['knowledge'].relationships
        old_set = reader.world.divinity.churches[1].followers
        generation = writer.pin.captured_head
        relationships[0] = .2
        relationships[0] = .1
        followers.add(8)
        followers.remove(8)
        assert writer.save() == generation
        assert writer._nested_dirty == {}
        relationships[0] = .3
        followers.add(8)
        writer.save()
        assert old_map[0] == .1 and 8 not in old_set
    with pytest.raises(StoreError):
        relationships.get(0)
    with pytest.raises(StoreError):
        followers.clear()


def test_failed_detach_keeps_nested_map_set_routes(tmp_path, monkeypatch):
    from ate_sim import persistence_lifecycle as lifecycle
    path = converted(tmp_path, 5, alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        relationships = session.world.divinity.gods['knowledge'].relationships
        followers = session.world.divinity.churches[1].followers
        def fail(phase, _session):
            if phase == 'before_publish':
                raise OSError('failed detach')
        monkeypatch.setattr(lifecycle, '_lifecycle_phase', fail)
        with pytest.raises(OSError, match='failed detach'):
            session.detach(materialize_history=True)
        relationships[9] = .5
        followers.add(8)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.wallets[11]['relationships'][9] == .5
        assert 8 in session.wallets[11]['followers']


def test_normal_ack_checks_nested_entry_query_witness(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError
    path = converted(tmp_path, 5)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        relationships = session.world.divinity.gods['knowledge'].relationships
        relationships[9] = .5
        original = []
        def corrupt(phase):
            if phase != 'after_commit':
                return
            row = session.store.db.execute("SELECT * FROM lazy_query_versions WHERE namespace='aux.lazy.nested.entries' AND valid_to IS NULL ORDER BY valid_from DESC LIMIT 1").fetchone()
            original.append(row)
            session.store.db.execute("DELETE FROM lazy_query_versions WHERE namespace=? AND record_key=? AND ordinal=? AND valid_from=?", (row[0], row[3], row[4], row[5]))
            session.store.db.commit()
        session.store._phase_hook = corrupt
        with pytest.raises(StoreIntegrityError, match='nested scalar membership witness'):
            session.save()
        assert session._nested_dirty
        session.store.db.execute('INSERT INTO lazy_query_versions VALUES (?,?,?,?,?,?,?,?)', original[0])
        session.store.db.commit()
        session.store._phase_hook = lambda phase: None
        session.resolve_save()
        assert not session._nested_dirty
