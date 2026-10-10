"""World integration for counted household/settlement history authorities."""
import pytest

from ate_sim.core import Household, Person, Settlement, World
from ate_sim.household_queries import living_household_members
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session, LazyScalarRecordTable
from ate_sim.persistence_lazy_sequence import LazyOrderedSequence, NODE_NAMESPACE, LOCATOR_NAMESPACE
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-counted-household-histories'


def converted(tmp_path, size=1000, alias=False):
    world = World(843000)
    for pid in range(1, 10):
        world.people[pid] = Person(pid, 0, 1, 1, alive=pid < 9)
    values = [9] * (size - 8) + list(range(1, 9))
    world.households[1] = Household(1, 1, members=values)
    world.households[2] = Household(2, 1, members=[9], alive=False, preparedness=.9)
    world.settlements[1] = Settlement(1, 0, 0, households=[1, 2, 1])
    if alias:
        world.currency.wallets[1] = {'members': values}
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, counted_households=True)
    return target


@pytest.mark.parametrize('size', [1000, 10000])
def test_scalar_household_edit_loads_no_member_nodes(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert isinstance(session.world.households, LazyScalarRecordTable)
        assert dict.__len__(session.world.households) == 0
        before = session.store.diagnostics()
        household = session.world.households[1]
        assert isinstance(household.members, LazyOrderedSequence)
        assert len(household.members) == size
        assert all(namespace != NODE_NAMESPACE for namespace, _ in household.members._cache)
        household.food = 17.
        session.save()
        assert not household.members._cache
        assert session.store.diagnostics().payload_writes - before.payload_writes <= 3
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.households[1].food == 17.
        assert session.world.households[1].members[-1] == 8


@pytest.mark.parametrize('size', [1000, 10000])
def test_counted_member_middle_edit_and_living_order(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        members = session.world.households[1].members
        assert [p.id for p in living_household_members(session.world, 1)] == list(range(1, 9))
        members.insert(size // 2, 3)
        plan = session._prepare_hybrid_save()
        changes = plan.nested_history_version_changes
        assert sum(c.namespace == NODE_NAMESPACE for c in changes) < 15
        assert sum(c.namespace == LOCATOR_NAMESPACE for c in changes) <= 256
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert len(session.world.households[1].members) == size + 1
        assert [p.id for p in living_household_members(session.world, 1)] == [3] + list(range(1, 9))


def test_settlement_preserves_extinct_duplicates_and_first_removal(tmp_path):
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        members = session.world.settlements[1].households
        assert isinstance(members, LazyOrderedSequence)
        members.remove(1.)
        assert members == [2, 1]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.settlements[1].households == [2, 1]
        assert [h.id for h in session.world.active_households()] == [1]


def test_wallet_alias_and_detach_share_one_member_list(tmp_path):
    path = converted(tmp_path, size=16, alias=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.wallets[1]['members']
        assert isinstance(history, LazyOrderedSequence)
        history.insert(1, 4)
        assert session.world.households[1].members is history
        session.save()
        world = session.detach(materialize_history=True)
    assert type(world.households[1].members) is list
    assert world.households[1].members is world.currency.wallets[1]['members']


@pytest.mark.parametrize('phase', ['during_version_writes', 'before_commit'])
def test_sequence_rollback_thaws_after_checked_uncommitted_result(tmp_path, phase):
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        sequence = session.world.households[1].members
        sequence.insert(2, 1)
        def fail(at):
            if at == phase:
                raise OSError('sequence publication rollback')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='rollback'):
            session.save()
        session.store._phase_hook = lambda _at: None
        session.resolve_save()
        sequence.insert(3, 2)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.households[1].members[2:4] == [1, 2]


def test_sequence_lost_acknowledgement_resolves_once(tmp_path, monkeypatch):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        sequence = session.world.settlements[1].households
        sequence.insert(1, 2)
        generation = session.pin.captured_head
        publish = session._publish_committed_hybrid
        monkeypatch.setattr(session, '_publish_committed_hybrid', lambda *_args: (_ for _ in ()).throw(OSError('lost ack')))
        with pytest.raises(OSError, match='lost ack'):
            session.save()
        with pytest.raises(StoreError):
            sequence.append(1)
        monkeypatch.setattr(session, '_publish_committed_hybrid', publish)
        assert session.resolve_save() == generation + 1
        assert session.resolve_save() == generation + 1
        assert sequence == [1, 2, 2, 1]


def test_replacement_new_owner_and_unowned_sequence_reattachment(tmp_path):
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        old = session.world.households[1].members
        incarnation = old._incarnation
        session.world.households[1].members = [7, 8]
        session.world.settlements[1].households = [2, 2, 1]
        assert isinstance(session.world.settlements[1].households, LazyOrderedSequence)
        session.save()
        old.insert(0, 4)
        session.world.households[2].food += 1
        session.save()
        session.world.households[3] = Household(3, 1, members=old)
        assert session.world.households[3].members is old
        session.save()
        assert old._incarnation == incarnation
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.households[1].members == [7, 8]
        assert session.world.households[3].members[0] == 4
        assert session.world.settlements[1].households == [2, 2, 1]


def test_shared_new_households_bind_one_sequence(tmp_path):
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = [1, 2]
        session.world.households[3] = Household(3, 1, members=values)
        session.world.households[4] = Household(4, 1, members=values)
        assert session.world.households[3].members is session.world.households[4].members
        session.world.households[4].members.append(3)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.households[3].members is session.world.households[4].members


def test_unloaded_owner_deletion_does_not_read_sequence_nodes(tmp_path):
    path = converted(tmp_path, size=1000)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        before = session.store.diagnostics().payload_reads
        del session.world.households[1]
        session.save()
        assert session.store.diagnostics().payload_reads - before < 15
        assert 1 not in session.world.households


def test_failed_central_preparation_releases_sequence_freeze(tmp_path, monkeypatch):
    import ate_sim.persistence_lazy_participants as participants
    path = converted(tmp_path, size=16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        sequence = session.world.households[1].members
        sequence.insert(2, 1)
        original = participants.freeze_hybrid_publication
        monkeypatch.setattr(participants, 'freeze_hybrid_publication', lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('central preparation failed')))
        with pytest.raises(OSError, match='central preparation'):
            session.save()
        sequence.insert(3, 2)
        monkeypatch.setattr(participants, 'freeze_hybrid_publication', original)
        session.save()
        assert sequence[2:4] == [1, 2]
