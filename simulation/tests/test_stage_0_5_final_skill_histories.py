"""Skill history edits publish compact headers and bounded typed pages."""
import pytest

from ate_sim.core import World, Settlement
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, PAGE_NAMESPACE

RULES = 'final-paged-skill-histories'


def converted(tmp_path, size=1000, *, alias=None):
    world = World(843000)
    values = list(range(size))
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', teachers=values, provenance=values)
    if alias == 'wallet':
        world.currency.wallets[1] = {'history': values}
    elif alias == 'eager':
        world.settlements[1] = Settlement(1, 0, 0, memory={'history': values})
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('size', [1000, 10000])
def test_skill_scalar_save_does_not_read_history_pages(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.skills[1, 'craft']
        history = skill.provenance
        assert isinstance(history, LazyHistoryList)
        assert skill.teachers is history
        assert len(history) == size
        assert history.diagnostics()['page_loads'] == 0
        skill.level = .75
        session.save()
        assert history.diagnostics()['page_loads'] == 0
        assert len(session.skills._baseline_payload[1, 'craft']) < 2048
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].level == .75
        assert session.skills[1, 'craft'].provenance[-1] == size - 1


@pytest.mark.parametrize('size', [1000, 10000])
def test_skill_append_publishes_only_tail_page_and_descriptor(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.skills[1, 'craft'].provenance
        assert isinstance(history, LazyHistoryList)
        history.append(size)
        plan = session._prepare_hybrid_save()
        pages = [change for change in plan.nested_history_version_changes if change.namespace == PAGE_NAMESPACE]
        assert len(pages) == 1
        assert sum(len(session.store.codec.encode(change.value)) for change in pages) < 8192
        assert history.diagnostics()['page_loads'] <= 1
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.skills[1, 'craft']
        assert skill.teachers is skill.provenance
        assert len(skill.provenance) == size + 1
        assert skill.provenance[-1] == size


@pytest.mark.parametrize('alias', ['wallet', 'eager'])
def test_cold_alias_routes_skill_append_without_breaking_sharing(tmp_path, alias):
    path = converted(tmp_path, alias=alias)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = (session.wallets[1]['history'] if alias == 'wallet'
                   else session.world.settlements[1].memory['history'])
        assert isinstance(history, LazyHistoryList)
        history.append(1000)
        assert session.skills[1, 'craft'].teachers is history
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.skills[1, 'craft'].provenance
        other = (session.wallets[1]['history'] if alias == 'wallet'
                 else session.world.settlements[1].memory['history'])
        assert other is history and history[-1] == 1000


def test_replacement_keeps_retained_shared_history_without_resurrecting_path(tmp_path):
    path = converted(tmp_path, alias='wallet')
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.skills[1, 'craft']
        old = skill.provenance
        assert isinstance(old, LazyHistoryList)
        skill.provenance = [7000]
        old.append(1000)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.skills[1, 'craft']
        assert skill.provenance == [7000]
        assert skill.teachers is session.wallets[1]['history']
        assert skill.teachers[-1] == 1000
        assert skill.provenance is not skill.teachers


def test_detach_materializes_skill_and_cross_family_alias_with_one_memo(tmp_path):
    path = converted(tmp_path, alias='wallet')
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert isinstance(session.skills[1, 'craft'].provenance, LazyHistoryList)
        detached = session.detach(materialize_history=True)
    history = detached.skills.skills[1, 'craft'].provenance
    assert type(history) is list
    assert detached.skills.skills[1, 'craft'].teachers is history
    assert detached.currency.wallets[1]['history'] is history


def test_new_skill_preserves_shared_teachers_and_provenance(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        values = [71, 72]
        session.skills[2, 'craft'] = SkillHistory(2, 'craft', teachers=values, provenance=values)
        skill = session.skills[2, 'craft']
        assert skill.teachers is skill.provenance
        skill.provenance.append(73)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.skills[2, 'craft']
        assert skill.teachers is skill.provenance and skill.provenance == [71, 72, 73]


def test_legacy_resident_skill_lists_stay_readable_without_open_migration(tmp_path, monkeypatch):
    import ate_sim.persistence_lazy as lazy
    with monkeypatch.context() as prior_encoder:
        prior_encoder.delitem(lazy.NESTED_RECORD_FIELDS, 'world.skills.skills')
        path = converted(tmp_path, size=4)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        before = session.pin.captured_head
        skill = session.skills[1, 'craft']
        assert isinstance(skill.teachers, list)
        assert skill.teachers is skill.provenance
        assert session.save() == before
        skill.provenance.append(4)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        skill = session.skills[1, 'craft']
        assert isinstance(skill.teachers, list)
        assert skill.provenance == [0, 1, 2, 3, 4]
        assert skill.teachers is skill.provenance


@pytest.mark.parametrize('phase', ['during_version_writes', 'before_commit'])
def test_skill_page_failed_publication_keeps_dirty_history_for_retry(tmp_path, phase):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.skills[1, 'craft'].provenance
        history.append(1000)
        generation = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError('skill page rollback')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='skill page rollback'):
            session.save()
        session.store._phase_hook = lambda _at: None
        assert session.resolve_save() == generation
        assert session.pin.captured_head == generation
        assert history[-1] == 1000 and history.pending_changes()
        assert session.save() == generation + 1
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance[-1] == 1000


def test_skill_page_lost_runtime_ack_resolves_exactly_once(tmp_path, monkeypatch):
    from ate_sim.incremental_store import StoreError
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.skills[1, 'craft'].provenance
        history.append(1000)
        generation = session.pin.captured_head
        original = session._publish_committed_hybrid
        def lost(*_args):
            raise OSError('skill page acknowledgement lost')
        monkeypatch.setattr(session, '_publish_committed_hybrid', lost)
        with pytest.raises(OSError, match='acknowledgement lost'):
            session.save()
        with pytest.raises(StoreError):
            history.append(1001)
        monkeypatch.setattr(session, '_publish_committed_hybrid', original)
        assert session.resolve_save() == generation + 1
        assert len(history) == 1001 and history[-1] == 1000
        assert session.save() == generation + 1


def test_skill_history_missing_descriptor_rejects_without_legacy_fallback(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        checked = session.store.read_version(session.pin, 'world.skills.skills', (1, 'craft'), expected_record_schema=1)
        incarnation = checked.value.provenance.incarnation
        session.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                                 (DESCRIPTOR_NAMESPACE, session.store.codec.encode(incarnation)))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.skills[1, 'craft']


def test_compound_cold_import_rejects_before_publication_and_preserves_source(tmp_path):
    from ate_sim.incremental_store import StoreFormatError
    import hashlib
    world = World(843000)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=[{'source': 71}])
    source, target = tmp_path / 'compound-source.sqlite', tmp_path / 'compound-target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(StoreFormatError, match='unsupported mutable descendants'):
        convert_cold_to_lazy(source, target, rules_id=RULES)
    assert not target.exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_new_compound_skill_history_preserves_legacy_values(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.skills[2, 'craft'] = SkillHistory(2, 'craft', provenance=[{'source': 71}])
        assert session.skills[2, 'craft'].provenance == [{'source': 71}]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[2, 'craft'].provenance == [{'source': 71}]
