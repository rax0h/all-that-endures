"""Growing knowledge claims and their exact semantic index remain point-backed."""
import pytest

from ate_sim.core import World
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session

RULES = 'stage-0-5-knowledge-authorities'
CLAIMS = 'world.knowledge.claims'
INDEX = 'world.knowledge.claim_index'


def converted(tmp_path, count=3):
    world = World(843000)
    for number in range(count):
        world.knowledge.claim(f'subject-{number}', f'proposition-{number}', number % 2 == 0)
    source, target = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('count', [1000, 10000])
def test_open_and_point_claim_lookup_do_not_load_the_knowledge_archive(tmp_path, count):
    target = converted(tmp_path, count)
    with open_lazy_world_session(target, rules_id=RULES) as s:
        knowledge = s.world.knowledge
        for table in (knowledge.claims, knowledge.claim_index):
            assert table.diagnostics()['payload_loads'] == 0
            assert table.diagnostics()['resident_records'] == 0
        assert knowledge.claim('subject-7', 'proposition-7') == 8
        assert knowledge.claim_index.diagnostics()['payload_loads'] == 1
        assert knowledge.claims.diagnostics()['payload_loads'] == 0
        assert knowledge.claims[8].truth is False
        assert knowledge.claims.diagnostics()['payload_loads'] == 1


def test_new_claim_reuses_exact_semantic_key_and_mutation_survives_reopen(tmp_path):
    target = converted(tmp_path)
    with open_lazy_world_session(target, rules_id=RULES) as s:
        knowledge = s.world.knowledge
        number = knowledge.claim('new', 'rain', None, 17)
        assert number == 4 and knowledge.next_claim == 5
        assert knowledge.claim('new', 'rain', True, 99) == number
        knowledge.claims[number].truth = True
        knowledge.teach(1, 2, number, .8)
        s.save()
    with open_lazy_world_session(target, rules_id=RULES) as s:
        knowledge = s.world.knowledge
        assert knowledge.claim('new', 'rain') == 4
        assert knowledge.claims[4].truth is True
        assert knowledge.claims[4].origin_event == 17
        assert knowledge.beliefs[2, 4] == .4
        assert knowledge.next_claim == 5


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_claim_and_index_publish_together_through_save_recovery(tmp_path, phase):
    target = converted(tmp_path)
    with open_lazy_world_session(target, rules_id=RULES) as s:
        knowledge = s.world.knowledge
        knowledge.claim('new', 'claim', True)
        def fail(at):
            if at == phase: raise OSError('knowledge-fault')
        s.store._phase_hook = fail
        with pytest.raises(OSError, match='knowledge-fault'):
            s.save()
        s.store._phase_hook = lambda _: None
        s.resolve_save()
        if phase == 'before_commit': s.save()
    with open_lazy_world_session(target, rules_id=RULES) as s:
        assert s.world.knowledge.claim_index['new', 'claim'] == 4
        assert s.world.knowledge.claims[4].truth is True


def test_knowledge_tables_materialize_on_explicit_detach(tmp_path):
    target = converted(tmp_path)
    with open_lazy_world_session(target, rules_id=RULES) as s:
        world = s.detach(materialize_history=True)
    # The standard portable record table retains standalone mutation callbacks.
    assert isinstance(world.knowledge.claims, dict)
    assert type(world.knowledge.claim_index) is dict
    assert world.knowledge.claim('subject-1', 'proposition-1') == 2


def test_loaded_claim_scalar_edit_is_saved_and_detached_record_remains_mutable(tmp_path):
    target = converted(tmp_path)
    with open_lazy_world_session(target, rules_id=RULES) as s:
        claim = s.world.knowledge.claims[2]
        claim.truth = True
        s.save()
    with open_lazy_world_session(target, rules_id=RULES) as s:
        assert s.world.knowledge.claims[2].truth is True
        world = s.detach(materialize_history=True)
    world.knowledge.claims[2].truth = False
    assert world.knowledge.claims[2].truth is False


def test_knowledge_point_edit_and_insert_have_fixed_archive_cost(tmp_path, record_property):
    measured = []
    for count in (1000, 10000):
        directory = tmp_path / str(count)
        directory.mkdir()
        target = converted(directory, count)
        with open_lazy_world_session(target, rules_id=RULES) as s:
            claims, index = s.world.knowledge.claims, s.world.knowledge.claim_index
            s.store.reset_diagnostics()
            claims[8].truth = True
            s.world.knowledge.claim('new', 'proposition', None)
            s.save()
            costs = s.store.diagnostics()
            measured.append(costs)
            record_property(f'H{count}_knowledge_edit', repr(costs))
            assert claims.diagnostics()['payload_loads'] == 1
            assert index.diagnostics()['payload_loads'] == 0
    assert measured[0].payload_reads == measured[1].payload_reads
    assert measured[0].payload_writes == measured[1].payload_writes
    assert measured[0].metadata_rows == measured[1].metadata_rows
    assert abs(measured[0].payload_read_bytes - measured[1].payload_read_bytes) < 128
    assert abs(measured[0].payload_write_bytes - measured[1].payload_write_bytes) < 128


def test_genuine_earlier_eager_knowledge_authority_remains_readable(tmp_path, monkeypatch):
    from ate_sim import persistence_lazy as module
    world = World(843000)
    world.knowledge.claim('old', 'claim', False)
    source, target = tmp_path / 'old-cold.sqlite', tmp_path / 'old-lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    # Construct the actual earlier conversion contract, leaving both ordinary
    # root records and their eager manifest markers in place.
    with monkeypatch.context() as legacy:
        legacy.setattr(module, 'SCALAR_RECORD_SPECS', {k:v for k,v in module.SCALAR_RECORD_SPECS.items() if k != CLAIMS})
        legacy.setattr(module, 'SCALAR_MAP_SPECS', {k:v for k,v in module.SCALAR_MAP_SPECS.items() if k != INDEX})
        legacy.setattr(module, 'SCALAR_NAMESPACES', tuple(k for k in module.SCALAR_NAMESPACES if k not in (CLAIMS, INDEX)))
        module.convert_cold_to_lazy(source, target, rules_id=RULES)
    with open_lazy_world_session(target, rules_id=RULES) as s:
        assert s.manifest['collections'][CLAIMS][0] == 'dict'
        assert CLAIMS not in s._scalar_tables and INDEX not in s._scalar_tables
        s.world.knowledge.claims[1].truth = True
        assert s.world.knowledge.claim('new', 'claim') == 2
        s.save()
    with open_lazy_world_session(target, rules_id=RULES) as s:
        assert s.world.knowledge.claims[1].truth is True
        assert s.world.knowledge.claim_index['new', 'claim'] == 2
        assert CLAIMS not in s._scalar_tables


def test_knowledge_uses_the_checked_coordinator_and_current_copy_lane(tmp_path):
    from ate_sim.persistence_catalog_copy import _copy_with_checked_catalog, _copy_current_checked_catalog
    from simulation.tests.test_stage_0_5_final_world_catalog_bridge import open_bridge, activate
    source = converted(tmp_path)
    target, copied = tmp_path / 'checked.sqlite', tmp_path / 'copied.sqlite'
    _copy_with_checked_catalog(source, target, rules_id=RULES)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        s.world.knowledge.claims[2].truth = True
        assert s.world.knowledge.claim('new', 'fact') == 4
        s.save()
    _copy_current_checked_catalog(target, copied, rules_id=RULES)
    with open_bridge(copied, rules_id=RULES) as s:
        activate(s)
        assert s.world.knowledge.claims[2].truth is True
        assert s.world.knowledge.claim('new', 'fact') == 4


def test_non_string_legacy_semantic_key_rejects_conversion_without_changing_source(tmp_path):
    import hashlib
    from ate_sim.incremental_store import StoreFormatError
    world = World(843000)
    world.knowledge.claim(17, 'imported-key')
    source, target = tmp_path / 'imported.sqlite', tmp_path / 'rejected.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(StoreFormatError, match='scalar map envelope'):
        convert_cold_to_lazy(source, target, rules_id=RULES)
    assert not target.exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
