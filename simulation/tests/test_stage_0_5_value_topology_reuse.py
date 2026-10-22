"""Scalar value dirt must not repeatedly reconstruct unchanged ownership."""
from unittest.mock import patch
import sqlite3

import pytest

from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_final_identity_only_headers import complete, RULES
from simulation.tests.test_stage_0_5_indexed_assignment_routes import shared_motives


@pytest.mark.parametrize('family,key,field', [
    ('people',1,'wealth'), ('motives',1,'safety'), ('skills',(1,'craft'),'level'),
])
def test_repeated_scalar_edits_reuse_checked_topology_and_publish_exact_value(tmp_path, family, key, field):
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        table=getattr(session,family);record=table[key]
        bridge=session._identity_bridge
        with patch.object(session,'_shared_object_routes',wraps=session._shared_object_routes) as routes:
            with patch.object(bridge,'_synchronize_owner',wraps=bridge._synchronize_owner) as projections:
                for value in (.25,.5,.75):setattr(record,field,value)
        assert routes.call_count == 1
        assert projections.call_count <= 1
        assert key in table._dirty
        session.save()
    with open_lazy_world_session(path,rules_id=RULES) as session:
        assert getattr(getattr(session,family)[key],field) == .75


def test_scalar_edits_keep_unloaded_alias_and_do_not_recreate_deleted_owner(tmp_path):
    path=shared_motives(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        record=session.motives[1]
        record.safety=.4
        assert session.motives[2] is record
        with patch.object(session,'_shared_object_routes',wraps=session._shared_object_routes) as routes:
            record.safety=.5
            assert routes.call_count == 0
        del session.motives[2]
        record.safety=.75
        assert 2 not in session.motives
        session.save()
    with open_lazy_world_session(path,rules_id=RULES) as session:
        assert 2 not in session.motives and session.motives[1].safety == .75


@pytest.mark.parametrize('change',['write','rollback','external','save','structural'])
def test_changed_authority_forces_scalar_topology_revalidation(tmp_path,change):
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        record=session.people[1];record.wealth=.4
        if change=='write':session.store.db.execute("UPDATE store_metadata SET value=value WHERE key='codec_version'");session.store.db.commit()
        elif change=='rollback':
            session.store.db.execute('SAVEPOINT edit')
            session.store.db.execute("UPDATE store_metadata SET value=value WHERE key='codec_version'")
            session.store.db.execute('ROLLBACK TO edit');session.store.db.execute('RELEASE edit')
        elif change=='external':
            with sqlite3.connect(path) as other:other.execute('PRAGMA user_version=123')
        elif change=='save':session.save()
        else:session.skills[1,'craft'].provenance=[{'new':[1]}]
        with patch.object(session,'_shared_object_routes',wraps=session._shared_object_routes) as routes:
            record.wealth=.75
            assert routes.call_count >= 1
        session.save()


def test_repeated_nested_native_scalar_edits_reuse_topology(tmp_path):
    from simulation.tests.test_stage_0_5_assignment_route_reuse import install_record
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        record=install_record(session)
        with patch.object(session,'_shared_object_routes',wraps=session._shared_object_routes) as routes:
            for value in (.25,.5,.75):record.strength=value
            assert routes.call_count == 1
        session.save()
    with open_lazy_world_session(path,rules_id=RULES) as session:
        root=session.skills[1,'craft'].provenance
        assert root[0] is root[1]['record'] and root[0].strength == .75


def test_used_identity_group_corruption_cannot_borrow_warm_scalar_proof(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.persistence_lazy_identity_catalog import GROUP_NAMESPACE
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        record=session.people[1];record.wealth=.4
        inc=session._registry.incarnation_for_object(record).value
        session.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                                 (GROUP_NAMESPACE,session.store.codec.encode(inc)))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):record.wealth=.75
        assert record.wealth == .4


def test_value_proof_cache_respects_shared_budget_and_eviction(tmp_path):
    from dataclasses import replace
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        for key in range(2,6):session.people[key]=replace(session.people[1],id=key)
        session.save()
        cache=session._identity_coordinator.value_routes;cache.entry_limit=2
        for key in range(1,6):session.people[key].wealth=.25
        diag=cache.diagnostics()
        assert diag['entries'] <= 2 and diag['bytes'] <= diag['byte_limit'] <= 65536
        coord=session._identity_coordinator
        assert coord.diagnostics()['clean_python_bytes'] <= coord.byte_limit
        with patch.object(session,'_shared_object_routes',wraps=session._shared_object_routes) as routes:
            session.people[1].wealth=.75
            assert routes.call_count >= 1
        session.save()


def test_proof_memory_charge_covers_retained_metadata(tmp_path):
    import sys
    from ate_sim.persistence_lazy_budget import resident_bytes
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        record=session.people[1];record.wealth=.4
        cache=session._identity_coordinator.value_routes
        proof,charged=next(iter(cache._entries.values()))
        metadata=(proof.subject,proof.epoch,proof.routes,proof.hooks)
        owned=sys.getsizeof(proof)+sys.getsizeof(proof.__dict__)+resident_bytes(metadata,
            seen={id(table) for table,key in proof.routes})
        assert charged >= owned


def test_class_level_custom_notification_does_not_borrow_scalar_proof(tmp_path):
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        table=session.people;record=table[1];record.wealth=.4
        cls=type(table);original=cls.changed;notified=[]
        def changed(self,key,field=None):
            notified.append((key,field))
            return original(self,key,field)
        with patch.object(cls,'changed',changed):
            bridge=session._identity_bridge
            with patch.object(bridge,'_synchronize_owner',wraps=bridge._synchronize_owner) as projections:
                record.wealth=.75
                assert projections.call_count >= 1
        assert notified and record.wealth == .75
        session.save()


def test_class_custom_preflight_metadata_is_never_used_as_owner_routes(tmp_path):
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        table=session.people;record=table[1];original=type(table).preflight_shared_record
        def preflight(self,obj):
            original(self,obj)
            return ('application metadata',)
        with patch.object(type(table),'preflight_shared_record',preflight):record.wealth=.75
        session.save()
    with open_lazy_world_session(path,rules_id=RULES) as session:
        assert session.people[1].wealth == .75


def test_custom_native_assignment_hook_does_not_reuse_warm_routes(tmp_path):
    from ate_sim.persistence_tracking import _binding
    from simulation.tests.test_stage_0_5_assignment_route_reuse import install_record
    path=complete(tmp_path)
    with open_lazy_world_session(path,rules_id=RULES) as session:
        record=install_record(session);record.strength=.4
        binding=_binding(record);original=type(binding).after_assignment;notified=[]
        def after(self,*args):
            notified.append(args)
            return original(self,*args)
        with patch.object(type(binding),'after_assignment',after):
            with patch.object(session,'_shared_object_routes',wraps=session._shared_object_routes) as routes:
                record.strength=.75
                assert routes.call_count >= 1
        assert notified
        session.save()


@pytest.mark.parametrize('name', ['preflight_value', 'preflight_change'])
@pytest.mark.parametrize('placement', ['instance', 'class'])
def test_custom_assignment_preflight_cannot_reuse_scalar_proof(tmp_path, name, placement):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.people
        record = table[1]
        record.wealth = .4
        original = getattr(table, name)
        notified = []
        def callback(*args):
            notified.append(args)
            return original(*(args[1:] if placement == 'class' else args))
        target = type(table) if placement == 'class' else table
        with patch.object(target, name, callback):
            with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as routes:
                record.wealth = .75
                assert routes.call_count >= 1
        assert notified
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == .75
