"""Ordinary events/actions and native scalar replacements share one proof save."""
import pytest
from ate_sim.agency import MotiveState, ActionRecord
from ate_sim.core import Layer, Person
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def configured(tmp_path):
    def configure(w):
        w.agency.motives[1] = MotiveState(curiosity=.1)
        w.agency.actions.append(ActionRecord(0, 1, 'learn', 'curiosity', .1))
    return fixture(tmp_path, configure=configure)


@pytest.mark.parametrize('mode', ['event', 'action', 'replacement', 'mixed'])
def test_ordinary_native_transition_avoids_world_audit(tmp_path, monkeypatch, mode):
    from ate_sim import persistence_proof_world as world
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.year = 1
        if mode in ('event', 'mixed'):
            session.world.emit('proof-test', Layer.REALITY, answer=42)
        if mode in ('action', 'mixed'):
            session.world.agency.actions.append(ActionRecord(1, 1, 'work', 'wealth', .7))
        if mode in ('replacement', 'mixed'):
            session.world.agency.motives[1] = MotiveState(curiosity=.9)
        if mode == 'mixed':session.world.people[99] = Person(99, 0, 1, 1)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('ordinary native save scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
        expected = session.world.digest()
    with opened(path, pair) as restored:
        assert restored.world.digest() == expected
        if mode in ('event', 'mixed'):assert restored.world.events[-1].data['answer'] == 42
        if mode in ('action', 'mixed'):assert restored.world.agency.actions[-1].action == 'work'
        if mode in ('replacement', 'mixed'):assert restored.world.agency.motives[1].curiosity == .9
        if mode == 'mixed':assert restored.world.people[99].id == 99


@pytest.mark.parametrize('damage', ['event-id', 'event-gap', 'event-cause', 'tail-count', 'tail-year', 'event-ids', 'next-event', 'layout', 'action-prefix', 'missing-header', 'bad-header'])
def test_ordinary_composition_rejects_forged_frozen_sources(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim.incremental_store import StoreError
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_adapters import META, COLLECTION_LAYOUT, AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY
    from ate_sim.persistence_session import EVENT_STORAGE, TAIL_DESCRIPTOR_KEY
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.year = 1
        session.world.emit('proof-test', Layer.REALITY, answer=42)
        session.world.agency.actions.append(ActionRecord(1, 1, 'work', 'wealth', .7))
        session.world.agency.motives[1] = MotiveState(curiosity=.9)
        original = manifests.commit_world_manifest
        def corrupt(*args, **kwargs):
            altered = False
            records = []
            for c in kwargs['changes']:
                if c.namespace == 'world.events':
                    if damage == 'event-id':c = replace(c, value=(c.value[0], replace(c.value[1], id=999)));altered = True
                    if damage == 'event-gap':c = replace(c, key=c.key+1);altered = True
                    if damage == 'event-cause':c = replace(c, value=(c.value[0], replace(c.value[1], causes=(c.value[1].id,))));altered = True
                if c.namespace == EVENT_STORAGE and c.key == TAIL_DESCRIPTOR_KEY:
                    if damage == 'tail-count':c = replace(c, value=c.value[:3]+(999,)+c.value[4:]);altered = True
                    if damage == 'tail-year':c = replace(c, value=c.value[:4]+(999,));altered = True
                if c.namespace in ('world.event_ids', 'world.next_event') and damage == ('event-ids' if c.namespace == 'world.event_ids' else 'next-event'):
                    v = (c.value[1][0], 999) if c.namespace == 'world.event_ids' else 999
                    c = replace(c, value=(0, v));altered = True
                if c.namespace == META and c.key == COLLECTION_LAYOUT and damage == 'layout':
                    layout = dict(c.value);kind, size, chunks = layout['world.events'];layout['world.events'] = kind, size+1, chunks
                    c = replace(c, value=layout);altered = True
                if c.namespace == AGENCY_ACTIONS_NAMESPACE and c.key == PACKED_LIST_KEY and damage == 'action-prefix':
                    tag, actions = c.value[1]
                    c = replace(c, value=(0, (tag, (replace(actions[0], action='forged'),)+actions[1:])));altered = True
                records.append(c)
            versions = []
            for c in kwargs['version_changes']:
                if c.namespace == catalog.OWNER_NAMESPACE and c.key == ('world.events', 0):
                    if damage == 'missing-header':altered = True;continue
                    if damage == 'bad-header':c = replace(c, value=c.value[:5]+('0'*64,)+c.value[6:]);altered = True
                versions.append(c)
            assert altered
            kwargs['changes'], kwargs['version_changes'] = tuple(records), tuple(versions)
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
        assert restored.world.events[-1].data['answer'] == 42
        assert restored.world.agency.actions[-1].action == 'work'
        assert restored.world.agency.motives[1].curiosity == .9


@pytest.mark.parametrize('phase', ['before_head', 'before_commit', 'after_commit'])
def test_ordinary_composition_recovers_exact_frozen_attempt(tmp_path, phase):
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.year = 1
        session.world.emit('proof-test', Layer.REALITY, answer=42)
        session.world.agency.actions.append(ActionRecord(1, 1, 'work', 'wealth', .7))
        session.world.agency.motives[1] = MotiveState(curiosity=.9)
        def fault(at):
            if at == phase:raise RuntimeError('interrupted ordinary proof')
        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='interrupted ordinary'):session.save()
        session.store._phase_hook = lambda _:None
        assert session.resolve_save() == (1 if phase == 'after_commit' else 0)
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.events[-1].data['answer'] == 42
        assert restored.world.agency.actions[-1].action == 'work'
        assert restored.world.agency.motives[1].curiosity == .9


def test_replacing_one_shared_scalar_owner_keeps_other_alias_exact(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    def configure(w):
        motive = MotiveState(curiosity=.1)
        w.agency.motives[1] = motive
        w.agency.motives[2] = motive
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        assert session.world.agency.motives[1] is session.world.agency.motives[2]
        session.world.agency.motives[1] = MotiveState(curiosity=.9)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('shared root replacement scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.agency.motives[1] is not restored.world.agency.motives[2]
        assert restored.world.agency.motives[1].curiosity == .9
        assert restored.world.agency.motives[2].curiosity == .1


def test_existing_native_scalar_value_and_queries_use_proof(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    def configure(w):w.culture.adoption[1, 1] = .25
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.culture.adoption[1, 1] = .5
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('native scalar value scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.culture.adoption[1, 1] == .5


@pytest.mark.parametrize('operation', ['action-prefix', 'action-truncate', 'event-edit', 'id-exception'])
def test_unsupported_ordinary_shapes_retain_checked_fallback(tmp_path, monkeypatch, operation):
    from ate_sim import persistence_proof_world as world
    def configure(w):
        w.agency.actions.append(ActionRecord(0, 1, 'learn', 'curiosity', .1))
        w.emit('original', Layer.REALITY, answer=1)
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.year = 1
        if operation == 'action-prefix':
            session.world.agency.actions[0] = ActionRecord(0, 1, 'work', 'wealth', .5)
            session.world.agency.actions.append(ActionRecord(1, 1, 'learn', 'curiosity', .7))
        elif operation == 'action-truncate':session.world.agency.actions.pop()
        elif operation == 'event-edit':session.world.events[0].kind = 'edited'
        else:
            session.world.event_ids.remove(1)
            session.world.emit('new', Layer.REALITY, answer=2)
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
        if operation == 'action-prefix':assert restored.world.agency.actions[0].action == 'work'
        elif operation == 'action-truncate':assert list(restored.world.agency.actions) == []
        elif operation == 'event-edit':assert restored.world.events[0].kind == 'edited'
        else:assert 1 not in restored.world.event_ids and 2 in restored.world.event_ids


@pytest.mark.parametrize('budget', ['events', 'actions', 'bytes'])
def test_ordinary_budget_exhaustion_keeps_checked_fallback(tmp_path, monkeypatch, budget):
    from ate_sim import persistence_proof_world as world, persistence_proof_world_ordinary as ordinary
    from ate_sim import persistence_proof_world_insert as insert
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.year = 1
        session.world.emit('first', Layer.REALITY, answer=42)
        session.world.emit('second', Layer.REALITY, answer=43)
        session.world.agency.actions.append(ActionRecord(1, 1, 'work', 'wealth', .7))
        original, calls = world._audit_world, []
        def audit(*args, **kwargs):
            calls.append(True)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            if budget == 'events':patch.setattr(ordinary, 'MAX_EVENTS', 1)
            elif budget == 'actions':patch.setattr(ordinary, 'MAX_ACTIONS', 1)
            else:patch.setattr(insert, 'MAX_BYTES', 1)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        assert restored.world.events[-1].data['answer'] == 43
        assert restored.world.agency.actions[-1].action == 'work'


def test_scalar_query_projection_cannot_be_forged(tmp_path, monkeypatch):
    from dataclasses import replace
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim.incremental_store import StoreError
    def configure(w):w.culture.adoption[1, 1] = .25
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.culture.adoption[1, 1] = .5
        original = manifests.commit_world_manifest
        def corrupt(*args, **kwargs):
            kwargs['version_changes'] = tuple(replace(c, memberships=()) if c.namespace == 'world.culture.adoption'
                                              else c for c in kwargs['version_changes'])
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError, match='query projection'):session.save()
        assert session.resolve_save() == 0
        assert session.save() == 1


def test_consecutive_mixed_saves_compose_retirement_without_world_audit(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    path, pair = configured(tmp_path)
    for year in (1, 2, 3):
        with opened(path, pair) as session:
            session.world.year = year
            session.world.emit('next', Layer.REALITY, causes=(() if year == 1 else (year-1,)), answer=year)
            session.world.agency.actions.append(ActionRecord(year, 1, 'work', 'wealth', year/10))
            session.world.agency.motives[1] = MotiveState(curiosity=year/10)
            with monkeypatch.context() as patch:
                patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('consecutive save scanned World'))
                assert session.save() == year
                pair = session.proof_manifest
        with opened(path, pair) as restored:
            assert restored.world.events[-1].data['answer'] == year
            assert restored.world.agency.motives[1].curiosity == year/10


@pytest.mark.parametrize('reader', ['insertion', 'value'])
def test_composed_reader_rejects_overlapping_predecessors_before_transfer(tmp_path, monkeypatch, reader):
    from types import SimpleNamespace
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim import persistence_proof_world_insert as insert, persistence_proof_publication as content
    from ate_sim import persistence_proof_world_new_backings as backing
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api
    def configure(w):w.agency.motives[1] = MotiveState(curiosity=.1)
    store, pin, pair = _proof_store(tmp_path, configure=configure)
    try:
        result = manifest_api().commit_world_manifest(store, pin, *pair, commit_token='a'*32,
            version_changes=(), changes=(), new_segments=(), metadata=store.head_metadata(), checkpoint=True)
        pin = result.commit.pin
        ns, typed = 'world.agency.motives', store.codec.encode(1)
        store.db.execute('INSERT INTO lazy_record_versions SELECT namespace,typed_key,1,NULL,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (ns, typed))
        store.db.commit()
        request = SimpleNamespace(pin=pin, pairs=manifest_api()._pairs(store, pin.captured_head))
        c = VersionChange('world.people', 99, Person(99, 0, 1, 1))
        row = dict(namespace=c.namespace, typed_key=store.codec.encode(c.key), payload=store.codec.encode(c.value), memberships_blob=store.codec.encode(()), change=c)
        def probe(forest):forest.predecessor(ns, typed)
        def forbidden(*a, **k):raise RuntimeError('body fetched before overlap rejection')
        monkeypatch.setattr(backing.Forest, '_collect', probe)
        monkeypatch.setattr(content, '_source_version', forbidden)
        with store.read_snapshot(pin), pytest.raises(StoreIntegrityError, match='overlap'):
            if reader == 'insertion':insert.prepare(store, request, (row,), (), ())
            else:
                from ate_sim.persistence_proof_world_value import validate_value_transition
                row = dict(row, namespace=ns, typed_key=typed,
                    change=VersionChange(ns, 1, MotiveState(curiosity=.2)))
                validate_value_transition(store, request, (row,), (), ())
    finally:store.close()


@pytest.mark.parametrize('damage', ['missing', 'wrong', 'extra'])
def test_adoption_counter_delta_requires_all_and_only_derived_updates(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim.incremental_store import StoreError
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.persistence_lazy_adoption import BUCKET_NAMESPACE
    def configure(w):w.culture.adoption[1, 1] = .25
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.culture.adoption[1, 1] = .5
        original = manifests.commit_world_manifest
        def corrupt(store, pin, *args, **kwargs):
            changes, altered = [], False
            for c in kwargs['version_changes']:
                if c.namespace == BUCKET_NAMESPACE and not altered:
                    if damage == 'missing':altered = True;continue
                    if damage == 'wrong':c = replace(c, value=c.value+1);altered = True
                changes.append(c)
            if damage == 'extra':
                key = (1, .62)
                value = store.read_version(pin, BUCKET_NAMESPACE, key, expected_record_schema=1).value
                changes.append(VersionChange(BUCKET_NAMESPACE, key, value+1));altered = True
            assert altered
            kwargs['version_changes'] = tuple(changes)
            return original(store, pin, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError, match='bucket'):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (0,)
        assert session.resolve_save() == 0
        assert session.save() == 1


def test_catalog_retirement_rejects_missing_physical_query_witness(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world_insert as insert
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.incremental_store import StoreError
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.agency.motives[1] = MotiveState(curiosity=.2)
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as session:
        retired = session.store.query_memberships(session.pin, catalog.GROUP_NAMESPACE, 'retired', True)
        assert retired
        incarnation = retired[0][0]
        session.world.agency.motives[1] = MotiveState(curiosity=.3)
        original = insert.prepare
        def missing(store, request, *args):
            store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND record_key=?',
                (catalog.GROUP_NAMESPACE, store.codec.encode(incarnation)))
            return original(store, request, *args)
        with monkeypatch.context() as patch:
            patch.setattr(insert, 'prepare', missing)
            with pytest.raises(StoreError, match='retirement physical query'):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (1,)
        assert session.resolve_save() == 1
        assert session.save() == 2


def test_catalog_retirement_cannot_delete_a_live_unrelated_group(tmp_path, monkeypatch):
    from dataclasses import replace
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.incremental_store import StoreError
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.agency.motives[1] = MotiveState(curiosity=.2)
        session.save();pair = session.proof_manifest
    with opened(path, pair) as session:
        live = session.store.read_identity_occurrence(session.pin, 'world.skills.skills', (1, 'craft'), ()).incarnation_id
        session.world.agency.motives[1] = MotiveState(curiosity=.3)
        original = manifests.commit_world_manifest
        def corrupt(*args, **kwargs):
            altered = False
            result = []
            for c in kwargs['version_changes']:
                if not altered and c.namespace == catalog.GROUP_NAMESPACE and c.delete:
                    c = replace(c, key=live);altered = True
                result.append(c)
            assert altered
            kwargs['version_changes'] = tuple(result)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (1,)
        assert session.resolve_save() == 1
        assert session.save() == 2
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.agency.motives[1].curiosity == .3
        assert restored.skills[1, 'craft'].person == 1


@pytest.mark.parametrize('mode', ['budget', 'full-audit'])
def test_uncertified_adoption_cannot_commit_omitted_counters(tmp_path, monkeypatch, mode):
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_proof_world_adoption as adoption
    from ate_sim import persistence_proof_world_value as value, persistence_proof_world_insert as insert
    from ate_sim.persistence_lazy_adoption import BUCKET_NAMESPACE
    from ate_sim.incremental_store import StoreError
    def configure(w):w.culture.adoption[1, 1] = .25
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.culture.adoption[1, 1] = .5
        original = manifests.commit_world_manifest
        def omit(*args, **kwargs):
            kwargs['version_changes'] = tuple(c for c in kwargs['version_changes'] if c.namespace != BUCKET_NAMESPACE)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', omit)
            patch.setattr(adoption, 'MAX_READS', 1)
            if mode == 'full-audit':
                patch.setattr(value, 'validate_value_transition', lambda *a, **k:False)
                patch.setattr(insert, 'prepare', lambda *a, **k:None)
            with pytest.raises(StoreError):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (0,)
        assert session.resolve_save() == 0
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.culture.adoption[1, 1] == .5
        assert list(restored.world.culture.adoption.items_above(.35)) == [((1, 1), .5)]


@pytest.mark.parametrize('mode', ['budget', 'new-scope', 'delete'])
def test_valid_uncertified_adoption_uses_reconciled_full_audit(tmp_path, monkeypatch, mode):
    from ate_sim import persistence_proof_world_adoption as adoption
    from ate_sim import persistence_proof_world as world
    def configure(w):w.culture.adoption[1, 1] = .25
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        if mode == 'delete':del session.world.culture.adoption[1, 1]
        else:session.world.culture.adoption[2 if mode == 'new-scope' else 1, 1] = .5
        calls = []
        original = world._audit_world
        def audit(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(adoption, 'MAX_READS', 1)
            patch.setattr(world, '_audit_world', audit)
            assert session.save() == 1
        assert calls  # The full publisher checks both parent and successor.
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        expected = [] if mode == 'delete' else [((2 if mode == 'new-scope' else 1, 1), .5)]
        assert list(restored.world.culture.adoption.items_above(.35)) == expected


@pytest.mark.parametrize('full_audit', [False, True])
def test_genealogy_invalid_tuple_cannot_publish_with_matching_owner(tmp_path, monkeypatch, full_audit):
    from dataclasses import replace
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_proof_world_value as value, persistence_proof_world_insert as insert
    from ate_sim.incremental_store import StoreError
    ns = 'world.genealogy.parents'
    def configure(w):w.genealogy.parents[1] = (12,)
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.genealogy.parents[1] = (13,)
        original = manifests.commit_world_manifest
        def corrupt(store, pin, *args, **kwargs):
            source, = [c for c in kwargs['version_changes'] if c.namespace == ns and c.key == 1]
            bad = replace(source, value=('invalid-parent',))
            digest = catalog._source_commitment(store.codec, bad, 'lazy', pin.captured_head+1)
            kwargs['version_changes'] = tuple(bad if c is source else
                replace(c, value=c.value[:5]+(digest,)+c.value[6:])
                if c.namespace == catalog.OWNER_NAMESPACE and c.key == (ns, 1) else c
                for c in kwargs['version_changes'])
            return original(store, pin, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            if full_audit:
                patch.setattr(value, 'validate_value_transition', lambda *a, **k:False)
                patch.setattr(insert, 'prepare', lambda *a, **k:None)
            with pytest.raises(StoreError):session.save()
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (0,)
        assert session.resolve_save() == 0
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.genealogy.parents[1] == (13,)


@pytest.mark.parametrize('reader', ['insertion', 'value'])
@pytest.mark.parametrize('column', ['payload_checksum', 'codec_version', 'record_schema', 'last_changed_generation'])
def test_ordinary_reader_bounds_physical_metadata_before_transfer(tmp_path, monkeypatch, reader, column):
    from types import SimpleNamespace
    from ate_sim.incremental_store import RecordChange, StoreError
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim import persistence_proof_world_insert as insert, persistence_proof_world_ordinary as ordinary
    from ate_sim.persistence_proof_world_value import validate_value_transition
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api
    store, pin, pair = _proof_store(tmp_path)
    try:
        store.db.execute('UPDATE records SET '+column+'=? WHERE namespace=?', ('x'*1048576, 'world.year'))
        store.db.commit()
        request = SimpleNamespace(pin=pin, pairs=manifest_api()._pairs(store, pin.captured_head))
        def text(value):
            assert len(value) <= 8192, 'oversized physical metadata transferred'
            return value.decode()
        store.db.text_factory = text
        zero = store.codec.encode(0)
        c = VersionChange(catalog.CATALOG_NAMESPACE, 0, ())
        row = dict(namespace=c.namespace, typed_key=zero, payload=store.codec.encode(()),
            memberships_blob=store.codec.encode(()), change=c)
        def read_year(store, request, rows, read, forest):return read('world.year', zero)
        monkeypatch.setattr(ordinary, 'prepare', read_year)
        monkeypatch.setattr(insert, 'MAX_BYTES', 65536)
        with store.read_snapshot(pin), pytest.raises(StoreError):
            if reader == 'insertion':insert.prepare(store, request, (row,), (), ())
            else:
                c = RecordChange('world.year', 0, (0, 1))
                row = dict(namespace=c.namespace, typed_key=zero, payload=store.codec.encode(c.value), change=c)
                validate_value_transition(store, request, (), (row,), ())
    finally:store.close()


def test_packed_action_append_projects_only_new_suffix(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    from ate_sim.persistence_adapters import AGENCY_ACTIONS_NAMESPACE
    def configure(w):
        for i in range(40):w.agency.actions.append(ActionRecord(0, 1, 'learn', 'curiosity', .1))
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        session.world.agency.actions.append(ActionRecord(1, 1, 'work', 'wealth', .7))
        original = world._project
        projected = []
        def project(store, ns, *args, **kwargs):
            for item in original(store, ns, *args, **kwargs):
                if ns == AGENCY_ACTIONS_NAMESPACE:projected.append(item[0])
                yield item
        with monkeypatch.context() as patch:
            patch.setattr(world, '_project', project)
            patch.setattr(world, '_audit_world', lambda *a, **k:pytest.fail('action append audited World'))
            assert session.save() == 1
        assert len(projected) == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert len(restored.world.agency.actions) == 41
        assert restored.world.agency.actions[-1].action == 'work'


def test_ordinary_projection_stops_at_cumulative_budget_sentinel(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world, persistence_proof_world_insert as insert
    from ate_sim import persistence_proof_world_new_backings as backing
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        for i in range(5):session.world.emit('proof-test', Layer.REALITY, answer=i)
        original, original_prepare = world._project, insert.prepare
        active, consumed = [], []
        def prepare(*args, **kwargs):
            active.append(1)
            try:return original_prepare(*args, **kwargs)
            finally:active.clear()
        def project(store, ns, *args, **kwargs):
            for item in original(store, ns, *args, **kwargs):
                if active:
                    consumed.append(item)
                    assert len(consumed) <= 4, 'projection exceeded remaining budget plus one sentinel'
                yield item
        with monkeypatch.context() as patch:
            patch.setattr(backing, 'MAX_PROJECTIONS', 3)
            patch.setattr(world, '_project', project)
            patch.setattr(insert, 'prepare', prepare)
            assert session.save() == 1
        assert len(consumed) == 4


def test_scalar_replacement_stops_after_second_projection(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from ate_sim import persistence_proof_world as world, persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_proof_world_owner_edits import scalar_replacement
    from ate_sim.persistence_proof_world_new_backings import Unsupported
    from ate_sim.persistence_lazy_store import VersionChange
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        c = VersionChange('world.agency.motives', 1, MotiveState(curiosity=.2))
        typed = session.store.codec.encode((c.namespace, c.key, catalog.path_hash(session.store.codec, ())))
        consumed = []
        def many(*args, **kwargs):
            for i in range(100):
                consumed.append(i)
                assert len(consumed) <= 2, 'singleton recognition consumed a whole owner'
                yield (), None, 'record:agency.MotiveState', b'fingerprint'
        monkeypatch.setattr(world, '_project', many)
        with pytest.raises(Unsupported):
            scalar_replacement(session.store, None, c, MotiveState(),
                {(catalog.OWNER_TREE_NAMESPACE, typed):object()}, SimpleNamespace(header=None))


def test_ordinary_mixed_save_preserves_event_data_aliases_in_fresh_process(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys
    from ate_sim import persistence_proof_world as world
    def configure(w):w.agency.motives[1] = w.agency.motives[2] = MotiveState(curiosity=.1)
    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        shared = [1, 2]
        session.world.emit('proof-test', Layer.REALITY, a=shared, b=shared)
        session.world.agency.motives[1] = MotiveState(curiosity=.9)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k:pytest.fail('mixed alias save audited World'))
            assert session.save() == 1
        pair, expected = session.proof_manifest, session.world.digest()
    result = subprocess.run([sys.executable, '-c',
        "import json,sys;from ate_sim.persistence_proof_world_session import open_audited_proof_world_session;"
        "s=open_audited_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2]));"
        "d=s.world.events[-1].data;m=s.world.agency.motives;"
        "print(json.dumps([s.world.digest(),d['a'] is d['b'],list(d['a']),m[1] is m[2],m[1].curiosity,m[2].curiosity]));s.close()",
        str(path), pair[1].hex()], check=True, capture_output=True, text=True, timeout=60)
    assert json.loads(result.stdout) == [expected, True, [1, 2], False, .9, .1]


def test_ordinary_mixed_save_does_not_read_unrelated_history_or_archive_bodies(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world, persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
    def configure(w):
        w.agency.motives[1] = MotiveState(curiosity=.1)
        w.agency.actions.append(ActionRecord(0, 1, 'learn', 'curiosity', .1))
    path, pair = fixture(tmp_path, size=1000, configure=configure)
    with opened(path, pair) as session:
        session.world.emit('proof-test', Layer.REALITY, answer=42)
        session.world.agency.actions.append(ActionRecord(1, 1, 'work', 'wealth', .7))
        session.world.agency.motives[1] = MotiveState(curiosity=.9)
        original = content._source_version
        def source(store, generation, ns, *args, **kwargs):
            assert ns not in (PAGE_NAMESPACE, ENTRY_NAMESPACE), 'unrelated old history body read'
            return original(store, generation, ns, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k:pytest.fail('mixed save audited World'))
            patch.setattr(content, '_source_version', source)
            patch.setattr(content, '_source_event', lambda *a, **k:pytest.fail('sealed archive body read'))
            assert session.save() == 1


def test_retirement_rejects_oversized_interval_metadata_without_transfer(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world_insert as insert, persistence_lazy_identity_catalog as catalog
    from ate_sim.incremental_store import StoreError
    path, pair = configured(tmp_path)
    with opened(path, pair) as session:
        session.world.agency.motives[1] = MotiveState(curiosity=.2)
        session.save();pair = session.proof_manifest
    with opened(path, pair) as session:
        session.world.agency.motives[1] = MotiveState(curiosity=.3)
        original = insert.prepare
        def corrupt(store, request, *args):
            store.db.execute('UPDATE lazy_query_versions SET valid_to=? WHERE namespace=? AND index_name=?',
                ('x'*1048576, catalog.GROUP_NAMESPACE, 'retired'))
            def text(value):
                assert len(value) <= 8192, 'oversized retirement metadata transferred'
                return value.decode()
            store.db.text_factory = text
            return original(store, request, *args)
        with monkeypatch.context() as patch:
            patch.setattr(insert, 'prepare', corrupt)
            with pytest.raises(StoreError, match='retirement physical query'):session.save()
        session.store.db.text_factory = str
        # Physical commit diagnostic; public accepted reads require recovery.
        assert session.store.db.execute(
            'SELECT generation FROM main.save_head WHERE singleton=1').fetchone() == (1,)
        assert session.resolve_save() == 1
        assert session.save() == 2


def test_failed_event_alias_admission_releases_its_durable_pin(tmp_path, monkeypatch):
    import sqlite3
    from ate_sim import persistence_proof_world_session as native
    path, pair = configured(tmp_path)
    def pins():
        with sqlite3.connect(path) as db:return db.execute('SELECT count(*) FROM generation_pins').fetchone()[0]
    assert pins() == 0
    def fail(*args):raise ValueError('injected alias admission failure')
    with monkeypatch.context() as patch:
        patch.setattr(native, '_restore_current_event_aliases', fail)
        with pytest.raises(ValueError, match='injected alias admission failure'):opened(path, pair)
    assert pins() == 0
    with opened(path, pair) as session:assert session.save() == 0


@pytest.mark.parametrize('fail', [False, True])
def test_current_event_alias_admission_closes_spilled_occurrences(tmp_path, monkeypatch, fail):
    from dataclasses import replace
    from pathlib import Path
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_spill import CheckedSpool
    from ate_sim.core import Event
    def configure(w):
        shared = [1, 2]
        w.events.append(Event(1, 0, 'proof-test', Layer.REALITY, data={'a':shared, 'b':shared}))
        w.event_ids.add(1);w.next_event=2
    path, pair = fixture(tmp_path, configure=configure)
    original = catalog.IdentityCatalog.read_owner_identity
    spilled = []
    def read(self, pin, owner):
        accepted = original(self, pin, owner)
        if owner[0] != 'world.events':return accepted
        spool = CheckedSpool(self.codec, entry_limit=1)
        # Reverse depth order so restoration must visit parents first.
        for row in sorted(accepted.occurrences, key=lambda row:len(row[0]), reverse=True):spool.add(row)
        spool.freeze();assert spool.spilled
        spilled.append((spool, Path(spool.path)))
        return replace(accepted, occurrences=spool)
    with monkeypatch.context() as patch:
        patch.setattr(catalog.IdentityCatalog, 'read_owner_identity', read)
        if fail:
            from ate_sim import persistence_proof_world_session as native
            original_walk = native._event_occurrences_by_depth
            def partial(rows):
                for row in original_walk(rows):
                    yield row
                    raise ValueError('injected alias walk failure')
            patch.setattr(native, '_event_occurrences_by_depth', partial)
            with pytest.raises(ValueError, match='injected alias walk failure'):opened(path, pair)
        else:
            with opened(path, pair) as session:
                data = session.world.events[0].data
                assert data['a'] is data['b']
                assert session.save() == 0
    assert spilled
    assert all(spool._closed and not file.exists() for spool, file in spilled)
