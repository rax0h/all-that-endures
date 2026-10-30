"""Native scalar-owner insertion must authenticate only its changed paths."""
import pytest
from ate_sim.core import Person
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def test_native_new_person_uses_proofs_and_reopens_exactly(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('insertion scanned World'))
            session.world.people[99] = Person(99, 0, 1, 1)
            session.world.next_person = 100
            assert session.save() == 1
            child = session.proof_manifest
    with opened(path, child) as session:
        assert session.world.people[99].id == 99
        assert session.world.next_person == 100
        assert [p.id for p in session.world.current_people()] == [99]


def test_native_new_scalar_partnership_keeps_checked_query_order(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('insertion scanned World'))
            session.world.social.partner(5, 9, 1)
            session.world.social.partner(1, 9, 2)
            assert session.save() == 1
            child = session.proof_manifest
    with opened(path, child) as session:
        assert tuple(session.world.social.partnerships) == ((5, 9), (1, 9))


@pytest.mark.parametrize('namespace', ['aux.lazy.identity.catalog', 'aux.lazy.identity.retired'])
def test_allocation_free_insertion_authenticates_catalog_dependencies(tmp_path, monkeypatch, namespace):
    from ate_sim.incremental_store import StoreIntegrityError, _framed_sha
    from ate_sim.persistence_lazy_store import _version_checksum
    from ate_sim import persistence_proof_world_insert as insert
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original = insert.prepare

        def forged(store, *args):
            typed = store.codec.encode(0)
            row = store.db.execute('SELECT record_schema,codec_version,valid_from,valid_to,memberships,payload '
                                   'FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
                                   (namespace, typed)).fetchone()
            schema, codec, start, end, memberships, payload = row
            # Self-consistent physical checksums cannot replace accepted proof authority.
            payload = store.codec.encode(('forged-header',))
            checksum = _version_checksum(namespace, typed, schema, codec, start, end, memberships, payload)
            store.db.execute('UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? '
                             'WHERE namespace=? AND typed_key=? AND valid_to IS NULL',
                             (payload, _framed_sha(b'lazy-payload-v1', payload), checksum, namespace, typed))
            return original(store, *args)

        session.world.social.partner(5, 9, 1)
        with monkeypatch.context() as patch:
            patch.setattr(insert, 'prepare', forged)
            with pytest.raises(StoreIntegrityError, match='insertion predecessor lacks accepted content'):
                session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1


def test_eager_family_cannot_enter_lazy_insertion_slice(tmp_path, monkeypatch):
    from ate_sim.core import LocalState
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim import persistence_proof_world_insert as insert
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original, project = insert.prepare, world._project
        checked = []

        def capture(store, request, versions, ordinary, segments):
            source = next(v for v in versions if v['namespace'] == 'world.people')
            c = VersionChange('world.local', 99, LocalState())
            eager = dict(source, namespace=c.namespace, typed_key=store.codec.encode(c.key),
                         payload=store.codec.encode(c.value), memberships_blob=store.codec.encode(()), change=c)

            def lazy_projection(store, ns, *args):
                if ns == 'world.local':
                    pytest.fail('eager-only family reached native lazy projection')
                return project(store, ns, *args)

            with monkeypatch.context() as patch:
                patch.setattr(world, '_project', lazy_projection)
                assert original(store, request, (eager,), (), ()) is None
            checked.append(True)
            return original(store, request, versions, ordinary, segments)

        session.world.people[99] = Person(99, 0, 1, 1)
        with monkeypatch.context() as patch:
            patch.setattr(insert, 'prepare', capture)
            assert session.save() == 1
        assert checked


def test_mixed_new_scalar_families_and_later_insertions_restore_in_fresh_process(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys
    from ate_sim import persistence_proof_world as world
    from ate_sim.agency import MotiveState
    path, pair = fixture(tmp_path)
    for year in (1, 2):
        with opened(path, pair) as session:
            with monkeypatch.context() as patch:
                patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('insertion scanned World'))
                pid = 100 + year
                session.world.people[pid] = Person(pid, year, 1, 1)
                session.world.agency.motives[pid] = MotiveState(curiosity=.75)
                session.world.transmission.record(year, 'learning', 'practice', year,
                                                  'person', pid, 'person', pid)
                session.world.year = year
                session.world.next_person = pid + 1
                assert session.save() == year
                pair = session.proof_manifest
        result = subprocess.run([sys.executable, '-c',
            "import json,sys; from ate_sim.persistence_proof_world_session import open_audited_proof_world_session; "
            "s=open_audited_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2])); "
            "print(json.dumps([s.world.year,len(s.world.people),len(s.world.transmission.records),s.world.agency.motives[100+s.world.year].curiosity])); s.close()",
            str(path), pair[1].hex()], capture_output=True, text=True, check=True, timeout=60)
        assert json.loads(result.stdout) == [year, year, year, .75]


def test_new_owner_with_history_alias_retains_full_audit_fallback_and_identity(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    from ate_sim.skills import SkillHistory
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original, calls = world._audit_world, []

        def audit(*args, **kw):
            calls.append(True)
            return original(*args, **kw)

        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            session.world.skills.skills[3, 'craft'] = SkillHistory(
                3, 'craft', provenance=session.skills[1, 'craft'].provenance)
            assert session.save() == 1
            assert calls
            child = session.proof_manifest
    with opened(path, child) as restored:
        assert restored.skills[3, 'craft'].provenance is restored.skills[1, 'craft'].provenance


@pytest.mark.parametrize('size', [1000, 10000])
def test_person_insertion_never_reads_unrelated_history_bodies(tmp_path, monkeypatch, size):
    from ate_sim import persistence_proof_world as world
    from ate_sim import persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
    path, pair = fixture(tmp_path, size=size)
    with opened(path, pair) as session:
        read = session.store.read_version
        source = content._source_version

        def checked_read(pin, namespace, *args, **kw):
            assert namespace not in (PAGE_NAMESPACE, ENTRY_NAMESPACE), 'unrelated history read'
            return read(pin, namespace, *args, **kw)

        def checked_source(store, generation, namespace, *args, **kw):
            assert namespace not in (PAGE_NAMESPACE, ENTRY_NAMESPACE), 'unrelated proof body read'
            return source(store, generation, namespace, *args, **kw)

        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('insertion scanned World'))
            patch.setattr(session.store, 'read_version', checked_read)
            patch.setattr(content, '_source_version', checked_source)
            session.world.people[99] = Person(99, 0, 1, 1)
            session.world.next_person = 100
            assert session.save() == 1
            child = session.proof_manifest
    with opened(path, child) as restored:
        assert restored.world.people[99].id == 99
        assert len(restored.skills[1, 'craft'].provenance) == size


@pytest.mark.parametrize('phase', ['before_head', 'before_commit', 'after_commit'])
def test_new_person_recovers_original_frozen_attempt(tmp_path, phase):
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        session.world.people[99] = Person(99, 0, 1, 1)
        session.world.next_person = 100

        def fault(at):
            if at == phase:
                raise RuntimeError('interrupted insertion')

        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='interrupted'):
            session.save()
        session.store._phase_hook = lambda _: None
        assert session.resolve_save() == (1 if phase == 'after_commit' else 0)
        assert session.save() == 1
        child = session.proof_manifest
    with opened(path, child) as restored:
        assert restored.world.people[99].id == 99


@pytest.mark.parametrize('damage', ['group', 'catalog', 'query', 'missing-identity', 'extra-identity', 'layout', 'ordinary-owner'])
def test_insertion_rejects_inconsistent_frozen_authority(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim.incremental_store import Membership, StoreError, RecordChange
    from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_adapters import META, COLLECTION_LAYOUT
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original = manifests.commit_world_manifest

        def corrupt(*args, **kw):
            versions = list(kw['version_changes'])
            for index, change in enumerate(versions):
                if damage == 'group' and change.namespace == catalog.GROUP_NAMESPACE:
                    versions[index] = replace(change, value=change.value[:3] + ('0'*64,) + change.value[4:])
                elif damage == 'catalog' and change.namespace == catalog.CATALOG_NAMESPACE:
                    versions[index] = replace(change, value=change.value[:3] + (999,) + change.value[4:])
                elif damage == 'query' and change.namespace == 'world.people':
                    versions[index] = replace(change, memberships=(Membership('alive', False, 0),))
            kw['version_changes'] = tuple(versions)
            if damage == 'missing-identity':
                kw['identity_changes'] = ()
            elif damage == 'extra-identity':
                root = kw['identity_changes'][0]
                kw['identity_changes'] += (IdentityOccurrenceChange('world.people', 99,
                    (('field', 'parents'),), incarnation_id=root.incarnation_id),)
            elif damage == 'layout':
                changes = []
                for c in kw['changes']:
                    if c.namespace == META and c.key == COLLECTION_LAYOUT:
                        v = dict(c.value)
                        v['world.people'] = ('dict', 999, 0)
                        c = replace(c, value=v)
                    changes.append(c)
                kw['changes'] = tuple(changes)
            elif damage == 'ordinary-owner':
                value = session.store.read_record('world.settlements', 1, expected_record_schema=1)
                kw['changes'] += (RecordChange('world.settlements', 1, value, record_schema=1),)
            return original(*args, **kw)

        session.world.people[99] = Person(99, 0, 1, 1)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError):
                session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1
