"""Native source/catalog composition retains exact original publication."""
from collections import Counter
import pytest

from ate_sim.core import Person
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def add_people(session, count=160):
    for person_id in range(100, 100+count):
        session.world.people[person_id] = Person(person_id, 0, 1, 1)
    session.world.next_person = 100+count


def test_native_source_and_catalog_components_compose_above_total_row_cap(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    path, pair = fixture(tmp_path)
    captured = Counter()
    with opened(path, pair) as session:
        original = manifests.commit_world_manifest
        def commit(*args, **kwargs):
            rows = kwargs['version_changes']
            captured.update(source=sum(c.namespace not in catalog.CATALOG_NAMESPACES for c in rows),
                catalog=sum(c.namespace in catalog.CATALOG_NAMESPACES for c in rows), ordinary=len(kwargs['changes'])+1)
            return original(*args, **kwargs)
        add_people(session)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', commit)
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('composed native save scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
        assert captured['source'] + captured['catalog'] > 512
        assert captured['source'] + captured['ordinary'] <= 512
        assert captured['catalog'] <= 512
        expected = session.world.digest()
    with opened(path, pair) as restored:
        assert list(restored.world.people) == list(range(100, 260))
        assert [p.id for p in restored.world.current_people()] == list(range(100, 260))
        assert restored.world.next_person == 260
        assert restored.world.digest() == expected


@pytest.mark.parametrize('kind', ['set', 'map'])
def test_existing_scalar_collection_growth_avoids_world_audit(tmp_path, monkeypatch, kind):
    from ate_sim.core import Settlement
    from ate_sim import persistence_proof_world as world
    def configure(w):
        values = {1, 2, 3} if kind == 'set' else {1: 'one', 2: 'two', 3: 'three'}
        w.settlements[1] = Settlement(1, 0, 0, memory={'values': values, 'same': values})
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        values = session.world.settlements[1].memory['values']
        if kind == 'set':values.update([7, 8])
        else:values.update({7: 'seven', 8: 'eight'})
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('scalar collection growth scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        memory = restored.world.settlements[1].memory
        assert memory['values'] is memory['same']
        assert sorted(memory['values']) == [1, 2, 3, 7, 8]
        if kind == 'map':assert dict(memory['values']) == {1:'one', 2:'two', 3:'three', 7:'seven', 8:'eight'}


def collection_fixture(tmp_path):
    from ate_sim.core import Settlement
    def configure(w):
        w.settlements[1] = Settlement(1, 0, 0, memory={'values': {1, 2, 3}})
    return fixture(tmp_path, configure=configure)


@pytest.mark.parametrize('limit', ['source', 'catalog', 'frontier', 'appended'])
def test_composed_budget_exhaustion_retains_checked_fallback(tmp_path, monkeypatch, limit):
    from ate_sim import persistence_proof_world as world
    from ate_sim import persistence_proof_world_components as components
    from ate_sim import persistence_proof_world_scalar_growth as growth
    path, pair = collection_fixture(tmp_path)
    with opened(path, pair) as session:
        add_people(session, 2)
        session.world.settlements[1].memory['values'].update([7, 8])
        original, calls = world._audit_world, []
        def audit(*args, **kwargs):
            calls.append(True)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            if limit == 'appended':patch.setattr(growth, 'MAX_APPENDED', 1)
            else:patch.setattr(components, {'source':'MAX_SOURCE_ROWS', 'catalog':'MAX_CATALOG_ROWS', 'frontier':'MAX_FRONTIER_ROWS'}[limit], 1)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        assert sorted(restored.world.settlements[1].memory['values']) == [1, 2, 3, 7, 8]
        assert list(restored.world.people) == [100, 101]


@pytest.mark.parametrize('damage', ['missing-entry', 'wrong-types', 'wrong-ordinal', 'wrong-membership', 'malformed-entry', 'missing-header', 'bad-header'])
def test_scalar_growth_rejects_inconsistent_frozen_authority(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim.incremental_store import Membership, StoreError
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_nested_history import ENTRY_NAMESPACE
    from ate_sim.persistence_history_types import NAMESPACE as TYPES
    path, pair = collection_fixture(tmp_path)
    with opened(path, pair) as session:
        values = session.world.settlements[1].memory['values']
        inc = values._incarnation
        values.add(7)
        original = manifests.commit_world_manifest
        def corrupt(*args, **kwargs):
            changes, altered = [], False
            for c in kwargs['version_changes']:
                if c.namespace == ENTRY_NAMESPACE and c.key[0] == inc:
                    if damage == 'missing-entry':altered = True;continue
                    if damage == 'malformed-entry':c = replace(c, value=(None,));altered = True
                    if damage == 'wrong-ordinal':c = replace(c, value=(9999, *c.value[1:]));altered = True
                    if damage == 'wrong-membership':c = replace(c, memberships=(Membership('incarnation', inc, 9999),));altered = True
                if c.namespace == TYPES and c.key == inc and damage == 'wrong-types':
                    c = replace(c, value=(c.value[0], c.value[1], (0, 0, 4)));altered = True
                if c.namespace == catalog.OWNER_NAMESPACE and c.key[0] == ENTRY_NAMESPACE and c.key[1][0] == inc:
                    if damage == 'missing-header':altered = True;continue
                    if damage == 'bad-header':c = replace(c, value=c.value[:5]+('0'*64,)+c.value[6:]);altered = True
                changes.append(c)
            assert altered
            kwargs['version_changes'] = tuple(changes)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (0,)
        assert session.resolve_save() == 0
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert sorted(restored.world.settlements[1].memory['values']) == [1, 2, 3, 7]


@pytest.mark.parametrize('phase', ['before_head', 'before_commit', 'after_commit'])
def test_composed_growth_recovers_original_frozen_save(tmp_path, phase):
    path, pair = collection_fixture(tmp_path)
    with opened(path, pair) as session:
        add_people(session, 160)
        session.world.settlements[1].memory['values'].add(7)
        def fault(at):
            if at == phase:raise RuntimeError('interrupted composed growth')
        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='interrupted composed'):session.save()
        session.store._phase_hook = lambda _:None
        assert session.resolve_save() == (1 if phase == 'after_commit' else 0)
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert sorted(restored.world.settlements[1].memory['values']) == [1, 2, 3, 7]
        assert list(restored.world.people) == list(range(100, 260))


def test_oversized_streamed_batch_is_not_materialized_for_routing():
    from ate_sim import persistence_proof_world_components as components
    class Stream:
        def __len__(self):return 100000
        def __iter__(self):pytest.fail('oversized prepared stream materialized')
    rows = Stream()
    assert components.semantic_versions(rows, {('lease', b'key')}) is rows
    assert components.frontier_versions(rows) == ()
    assert components.insertion_within_limits(rows, ()) is False


@pytest.mark.parametrize('kind', ['set', 'map'])
def test_scalar_growth_does_not_read_unrelated_old_history_bodies(tmp_path, monkeypatch, kind):
    from ate_sim.core import Settlement
    from ate_sim import persistence_proof_world as world, persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import ENTRY_NAMESPACE, PAGE_NAMESPACE
    def configure(w):
        value = {1, 2, 3} if kind == 'set' else {1:'one', 2:'two', 3:'three'}
        w.settlements[1] = Settlement(1, 0, 0, memory={'values':value})
    path, pair = fixture(tmp_path, size=10000, configure=configure)
    with opened(path, pair) as session:
        values = session.world.settlements[1].memory['values']
        inc = values._incarnation
        parent_inc = session.world.settlements[1].memory._incarnation
        original = content._source_version
        def source(store, generation, ns, key, *args, **kwargs):
            if ns in (ENTRY_NAMESPACE, PAGE_NAMESPACE):
                assert ns == ENTRY_NAMESPACE and store.codec.decode(key) in ((inc, 7), (parent_inc, 'values')), 'unrelated old history body read'
            return original(store, generation, ns, key, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(content, '_source_version', source)
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('bounded growth scanned World'))
            if kind == 'set':values.add(7)
            else:values[7] = 'seven'
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert sorted(restored.world.settlements[1].memory['values']) == [1, 2, 3, 7]
        assert len(restored.skills[1, 'craft'].provenance) == 10000


@pytest.mark.parametrize('kind', ['set', 'reference-map'])
def test_unsupported_scalar_growth_preserves_checked_fallback(tmp_path, monkeypatch, kind):
    from ate_sim.core import Settlement
    from ate_sim import persistence_proof_world as world
    def configure(w):
        w.settlements[1] = Settlement(1, 0, 0, memory={'values': set() if kind == 'set' else {1:'one'}})
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        values = session.world.settlements[1].memory['values']
        if kind == 'set':values.add(7)
        else:values[7] = [8, 9]
        original, calls = world._audit_world, []
        def audit(*args, **kwargs):
            calls.append(True)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        values = restored.world.settlements[1].memory['values']
        if kind == 'set':assert sorted(values) == [7]
        else:assert list(values[7]) == [8, 9]


def test_native_catalog_component_over_budget_is_not_partially_accepted(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        add_people(session, 180)
        original, calls = world._audit_world, []
        def audit(*args, **kwargs):
            calls.append(True)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        assert list(restored.world.people) == list(range(100, 280))


@pytest.mark.parametrize('pairs', [False, True])
def test_scalar_member_class_change_retains_checked_fallback(tmp_path, monkeypatch, pairs):
    from ate_sim.core import Settlement
    from ate_sim import persistence_proof_world as world
    before = {('person', 1), ('person', 2)} if pairs else {1, 2}
    new = 7 if pairs else ('person', 7)
    def configure(w):
        w.settlements[1] = Settlement(1, 0, 0, memory={'values':set(before)})
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        original, calls = world._audit_world, []
        def audit(*args, **kwargs):
            calls.append(True)
            return original(*args, **kwargs)
        session.world.settlements[1].memory['values'].add(new)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        assert set(restored.world.settlements[1].memory['values']) == before | {new}


def test_lineage_scalar_sequence_list_and_owner_compose_with_fresh_restore(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys
    from ate_sim.core import Household, Settlement
    from ate_sim import persistence_proof_world as world
    def configure(w):
        members = list(range(1, 129))
        w.households[1] = Household(1, 1, members=members)
        w.households[2] = Household(2, 1, members=members)
        pairs = {('person', 1)}
        w.settlements[1] = Settlement(1, 0, 0, memory={'pairs':pairs, 'same':pairs, 'map':{1:'one'}})
    path, pair = fixture(tmp_path, size=128, configure=configure)
    with opened(path, pair) as session:
        memory = session.world.settlements[1].memory
        memory['pairs'].add(('person', 2))
        memory['map'][2] = 'two'
        session.world.households[1].members.append(129)
        session.skills[1, 'craft'].provenance.append(42)
        add_people(session, 1)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('combined frontiers scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
        expected = session.world.digest()
    result = subprocess.run([sys.executable, '-c',
        "import json,sys;from ate_sim.persistence_proof_world_session import open_audited_proof_world_session;"
        "s=open_audited_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2]));"
        "m=s.world.settlements[1].memory;print(json.dumps([s.world.digest(),sorted(m['pairs']),m['pairs'] is m['same'],"
        "sorted(m['map'].items()),list(s.world.households[1].members),s.world.households[1].members is s.world.households[2].members,"
        "list(s.skills[1,'craft'].provenance),list(s.world.people)]));s.close()",
        str(path), pair[1].hex()], check=True, capture_output=True, text=True, timeout=90)
    assert json.loads(result.stdout) == [expected, [['person',1],['person',2]], True,
        [[1,'one'],[2,'two']], list(range(1,130)), True, list(range(128))+[42], [100]]


@pytest.mark.parametrize('damage', ['missing-header', 'bad-header'])
def test_above_total_cap_still_requires_exact_catalog_and_recovers(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim.incremental_store import StoreError
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        add_people(session)
        original = manifests.commit_world_manifest
        def corrupt(*args, **kwargs):
            rows = []
            for c in kwargs['version_changes']:
                if c.namespace == catalog.OWNER_NAMESPACE and c.key == ('world.people', 100):
                    if damage == 'missing-header':continue
                    c = replace(c, value=c.value[:5]+('0'*64,)+c.value[6:])
                rows.append(c)
            assert len(rows) > 512
            kwargs['version_changes'] = tuple(rows)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError, match='catalog differs'):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (0,)
        assert session.resolve_save() == 0
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert list(restored.world.people) == list(range(100, 260))
