"""Imported advancement topology uses checked recursive storage, without truncation."""
import pytest
from ate_sim.advancement import EssencePath, AbilityProgress
from ate_sim.mastery_training import ResponseModel
from ate_sim.persistence_lazy_nested_history import LazyHistoryList
from ate_sim.persistence_record_headers import record_reference
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy, module, opened, sha, RULES
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate

NS = 'world.advancement.paths'

def converted(tmp_path, count=3, configure=None):
    def configure_source(world):
        model = ResponseModel(samples=[{'event':n, 'inputs':[1., .2, .3], 'response':.5} for n in range(count)])
        ability = AbilityProgress('life', 'probe', 'probe-key', 'probe', 'control', 'craft', 0, response_model=model)
        world.advancement.paths[1] = EssencePath(abilities=[ability])
        world.advancement.paths[2] = EssencePath(abilities=[ability])
        if configure is not None:
            configure(world)
    source = legacy_lazy(tmp_path, configure=configure_source)
    target = tmp_path / 'recursive-advancement.sqlite'
    before = sha(source)
    module()._copy_with_checked_catalog(source, target, rules_id=RULES, normalize_advancement=True)
    assert sha(source) == before
    return target


def test_copy_uses_compact_root_and_preserves_shared_imported_samples(tmp_path):
    target = converted(tmp_path)
    with opened(target) as store:
        pin = store.capture_pin()
        assert record_reference(store.read_version(pin, NS, 1, expected_record_schema=1).value)
        store.release_pin(pin)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        first, second = s.advancement_paths[1], s.advancement_paths[2]
        assert isinstance(first.abilities, LazyHistoryList)
        assert first.abilities[0] is second.abilities[0]
        samples = first.abilities[0].response_model.samples
        assert isinstance(samples, LazyHistoryList)
        assert len(samples) == 3 and samples[-1]['event'] == 2
        first.core_fraction = .25
        samples[0]['response'] = .75
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert s.advancement_paths[1].core_fraction == .25
        assert s.advancement_paths[2].abilities[0].response_model.samples[0]['response'] == .75


def test_scalar_edit_does_not_read_or_write_imported_sample_history(tmp_path, record_property):
    costs = []
    for count in (1000, 10000):
        directory = tmp_path / str(count); directory.mkdir()
        target = converted(directory, count)
        with open_bridge(target, rules_id=RULES) as s:
            activate(s)
            s.store.reset_diagnostics()
            path = s.advancement_paths[1]
            path.core_fraction = .25
            s.save()
            measured = s.store.diagnostics(); costs.append(measured)
            record_property(f'H{count}_advancement_scalar', repr(measured))
            assert path.abilities.diagnostics()['page_loads'] == 0
    assert costs[0].payload_reads == costs[1].payload_reads
    # Allocator/namespace counts and related owner IDs gain decimal digits.
    # Their bounded header delta cannot hide a sample payload traversal.
    assert abs(costs[0].payload_read_bytes - costs[1].payload_read_bytes) < 128
    assert costs[0].payload_writes == costs[1].payload_writes
    assert abs(costs[0].payload_write_bytes - costs[1].payload_write_bytes) < 128
    assert max(row.payload_read_bytes for row in costs) < 65536
    assert max(row.payload_write_bytes for row in costs) < 65536
    assert costs[0].metadata_rows == costs[1].metadata_rows


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_recursive_advancement_recovery_keeps_exact_shared_model(tmp_path, phase):
    target = converted(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        model = s.advancement_paths[1].abilities[0].response_model
        model.samples.append({'event':9, 'inputs':[1., .2, .3], 'response':.75})
        def fail(at):
            if at == phase: raise OSError('advancement-fault')
        s.store._phase_hook = fail
        with pytest.raises(OSError, match='advancement-fault'): s.save()
        s.store._phase_hook = lambda _: None
        s.resolve_save()
        if phase == 'before_commit': s.save()
        assert s.advancement_paths[2].abilities[0].response_model is model
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert len(s.advancement_paths[1].abilities[0].response_model.samples) == 4


def test_recursive_advancement_detach_materializes_one_shared_native_graph(tmp_path):
    target = converted(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        world = s.detach(materialize_history=True)
    a, b = world.advancement.paths[1], world.advancement.paths[2]
    assert type(a.abilities) is list
    assert a.abilities[0] is b.abilities[0]
    assert type(a.abilities[0].response_model.samples) is list


def test_rank_scope_sees_direct_cold_ability_and_membership_edits(tmp_path):
    def configure(world):
        abilities = [AbilityProgress(essence, 'probe', f'ability-{i}', 'probe', 'control', 'craft', 0,
            rank=1 if i == 0 else 2) for i, essence in enumerate(e for e in ('fire','water','life','confluence') for _ in range(5))]
        world.advancement.paths[1] = EssencePath(base_essences=['fire','water','life'],
            confluence='confluence', abilities=abilities)
    target = converted(tmp_path, configure=configure)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        state = s.world.advancement
        with state.rank_scope():
            assert state.rank(1) == 1
            state.paths[1].abilities[0].rank = 2
            assert state.rank(1) == 2
            state.paths[1].base_essences.pop()
            assert state.rank(1) == 0
        s.save()


def test_rejected_replacement_preserves_original_root_and_routing(tmp_path):
    target = converted(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        original = s.advancement_paths[1]
        before = s._registry.next_incarnation
        with pytest.raises(TypeError):
            s.advancement_paths[1] = EssencePath(abilities=[object()])
        assert s.advancement_paths[1] is original
        assert s._registry.next_incarnation == before
        original.core_fraction = .4
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert s.advancement_paths[1].core_fraction == .4


def test_orphan_path_edits_do_not_resurrect_replaced_owner_and_can_be_reinserted(tmp_path):
    target = converted(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        old = s.advancement_paths[1]
        incarnation = s._registry.incarnation_for_object(old)
        s.advancement_paths[1] = EssencePath(core_fraction=.2)
        old.core_fraction = .9
        s.save()
        assert s.advancement_paths[1].core_fraction == .2
        s.advancement_paths[3] = old
        s.save()
        assert s._registry.incarnation_for_object(old) == incarnation
        del s.advancement_paths[1]
        s.advancement_paths[1] = old
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert s.advancement_paths[1] is s.advancement_paths[3]
        assert s.advancement_paths[1].core_fraction == .9
        assert list(s.advancement_paths) == [2, 3, 1]


@pytest.mark.parametrize('operation', ['reopen', 'detach', 'copy-input'])
def test_cross_family_record_alias_survives_advancement_normalization(tmp_path, operation):
    def configure(world):
        path = world.advancement.paths[1]
        world.currency.wallets[1] = {'path': path, 'ability': path.abilities[0]}
    target = converted(tmp_path, configure=configure)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        path = s.advancement_paths[1]
        s.skills[1, 'craft'].provenance = [path, path.abilities[0]]
        assert s.skills[1, 'craft'].provenance[0] is path
        assert s.wallets[1]['path'] is path
        path.abilities[0].level = 7
        s.save()
        if operation == 'copy-input':
            copied = s._recursive_histories.copy_input(s.wallets[1])
            assert copied['path'].abilities[0] is copied['ability']
            assert type(copied['path'].abilities) is list
        if operation == 'detach':
            world = s.detach(materialize_history=True)
            path = world.advancement.paths[1]
            assert world.skills.skills[1, 'craft'].provenance[0] is path
            assert world.currency.wallets[1]['path'] is path
            assert world.currency.wallets[1]['ability'] is path.abilities[0]
            assert type(path.abilities) is list
    if operation == 'reopen':
        with open_bridge(target, rules_id=RULES) as s:
            activate(s)
            path = s.advancement_paths[1]
            assert s.wallets[1]['path'] is s.skills[1, 'craft'].provenance[0] is path
            assert path.abilities[0].level == 7


def test_unsaved_recursive_children_close_without_weak_callback_iteration_failure(tmp_path):
    from ate_sim.incremental_store import StoreError
    target = converted(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        path = s.advancement_paths[1]
        path.abilities.append(AbilityProgress('water', 'probe', 'new', 'probe', 'control', 'craft', 0))
    with pytest.raises(StoreError, match='closed'):
        path.core_fraction = .5


def test_checked_current_copy_retains_compact_shared_advancement_graph(tmp_path):
    target = converted(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.advancement_paths[1].abilities[0].level = 9
        s.save()
    destination = tmp_path / 'checked-copy.sqlite'
    before = sha(target)
    module()._copy_current_checked_catalog(target, destination, rules_id=RULES)
    assert sha(target) == before
    with open_bridge(destination, rules_id=RULES) as s:
        activate(s)
        first, second = s.advancement_paths[1], s.advancement_paths[2]
        assert first.abilities[0] is second.abilities[0]
        assert first.abilities[0].level == 9
        first.abilities[0].response_model.samples.append({'event': 7})
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert len(s.advancement_paths[1].abilities[0].response_model.samples) == 3


def test_foreign_replacement_rejects_before_detaching_current_root(tmp_path):
    from ate_sim.incremental_store import StoreError
    left_dir, right_dir = tmp_path / 'left', tmp_path / 'right'
    left_dir.mkdir(); right_dir.mkdir()
    left, right = converted(left_dir), converted(right_dir)
    with open_bridge(left, rules_id=RULES) as a, open_bridge(right, rules_id=RULES) as b:
        activate(a); activate(b)
        original = a.advancement_paths[1]
        with pytest.raises(StoreError, match='cross-session'):
            a.advancement_paths[1] = b.advancement_paths[1]
        assert a.advancement_paths[1] is original
        original.core_fraction = .6
        a.save()
