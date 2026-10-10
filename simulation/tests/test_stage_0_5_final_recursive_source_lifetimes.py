"""Input alias leases must not retain the committed recursive archive."""
import gc
import weakref

import pytest

from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    converted_catalog, open_bridge, activate, RULES,
)


@pytest.mark.parametrize('size', [1000, 10000])
def test_unheld_native_sources_do_not_pin_all_recursive_children_after_save(tmp_path, size, record_property):
    target = converted_catalog(tmp_path, size=size)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [[number] for number in range(64)]
        root = session.skills[1, 'craft'].provenance
        first = weakref.ref(root[0])
        session.save()
        gc.collect()
        assert first() is None
        assert sum(1 for _source, proxy in session._eager_tracker._memo.values()
                   if getattr(proxy, '_recursive_runtime', None) is session._recursive_histories) == 0
        assert list(root[-1]) == [63]
        assert session._recursive_histories.source_diagnostics()['source_memo_leases'] == 0
        record_property(f'H{size}_source_leases_after_save', 0)


def test_held_native_source_reuses_its_exact_proxy_and_releases_after_caller_drops_it(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        source = [7]
        session.skills[1, 'craft'].provenance = [source]
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        session.save()
        root.append(source)
        assert root[1] is child
        session.save()
        source_id = id(source)
        assert source_id in session._eager_tracker._memo
        del source
        session.save()
        assert source_id not in session._eager_tracker._memo
        assert root[0] is root[1] is child


def test_recursive_save_routes_one_complete_dirty_projection_instead_of_rescanning_it_per_child(tmp_path, record_property):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [[number] for number in range(24)]
        runtime = session._recursive_histories
        dirty_count = len(session._nested_dirty)
        source_visits = []
        changes = runtime._changes
        def counted(proxy):
            source_visits.append(proxy._incarnation)
            yield from changes(proxy)
        runtime._changes = counted
        session.save()
        assert len(source_visits) <= 8 * dirty_count
        record_property('dirty_histories', dirty_count)
        record_property('projection_visits', len(source_visits))


def test_released_input_aliases_are_collected_with_a_fixed_noop_save_budget(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        source = [[number] for number in range(300)]
        session.skills[1, 'craft'].provenance = source
        root = session.skills[1, 'craft'].provenance
        session.save()
        runtime = session._recursive_histories
        assert runtime.source_diagnostics()['source_memo_leases'] == 301
        del source
        generation = session.pin.captured_head
        session.store.reset_diagnostics()
        for _ in range(3):
            before = runtime.source_diagnostics()['source_release_checks']
            assert session.save() == generation
            assert runtime.source_diagnostics()['source_release_checks'] - before <= 256
        gc.collect()
        assert runtime.source_diagnostics()['source_memo_leases'] == 0
        assert runtime.source_diagnostics()['source_release_queue'] == 0
        assert session.store.diagnostics().payload_writes == 0
        assert list(root[-1]) == [299]
