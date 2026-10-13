"""Successive guarded edits reconcile newly notified owners, not prior dirty work."""
from ate_sim.core import Person
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy,RULES


def test_successive_scalar_edits_do_not_resynchronize_prior_dirty_owners(tmp_path,monkeypatch):
    count=24
    def configure(world):
        world.people.update({pid:Person(pid,0,1,1) for pid in range(1,count+1)})
        world.next_person=count+1
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'complete.sqlite'
    upgrade_lazy_snapshot(source,target,rules_id=RULES)
    with open_lazy_world_session(target,rules_id=RULES) as s:
        bridge=s._identity_bridge;original=bridge._synchronize_owner;calls=[]
        def measured(owner,visible):
            if owner[0]=='world.people':calls.append(owner[1])
            return original(owner,visible)
        monkeypatch.setattr(bridge,'_synchronize_owner',measured)
        for pid in range(1,count+1):s.people[pid].wealth=float(pid)
        bridge.synchronize_lazy_placements()
        assert len(calls)<=count*4, f'{len(calls)} synchronizations for {count} local edits'
        s.save()
    with open_lazy_world_session(target,rules_id=RULES) as s:
        assert all(s.people[pid].wealth==float(pid) for pid in range(1,count+1))


def test_checked_new_owner_cancellation_after_synchronization_remains_absent(tmp_path):
    source=legacy_lazy(tmp_path);target=tmp_path/'complete.sqlite'
    upgrade_lazy_snapshot(source,target,rules_id=RULES)
    with open_lazy_world_session(target,rules_id=RULES) as s:
        s.people[77]=Person(77,0,1,1)
        s._identity_bridge.synchronize_lazy_placements()
        del s.people[77]
        s._identity_bridge.synchronize_lazy_placements()
        s.save()
        assert 77 not in s.people
    with open_lazy_world_session(target,rules_id=RULES) as s:assert 77 not in s.people


def test_successive_history_edits_do_not_rescan_prior_dirty_backings(tmp_path,monkeypatch):
    from ate_sim.metaphysics import SoulState
    count=24
    def configure(world):
        for pid in range(1,count+1):world.metaphysics.souls[pid]=SoulState(pid,transformations=[0])
    source=legacy_lazy(tmp_path,configure=configure);target=tmp_path/'complete.sqlite'
    upgrade_lazy_snapshot(source,target,rules_id=RULES)
    with open_lazy_world_session(target,rules_id=RULES) as s:
        runtime=s._recursive_histories;original=runtime._changes;calls=[]
        def measured(proxy):
            calls.append(proxy._incarnation)
            yield from original(proxy)
        monkeypatch.setattr(runtime,'_changes',measured)
        for pid in range(1,count+1):s.souls[pid].transformations.append(pid)
        runtime.synchronize()
        assert len(calls)<=count*5,f'{len(calls)} backing scans for {count} local edits'
        s.save()
    with open_lazy_world_session(target,rules_id=RULES) as s:
        assert all(list(s.souls[pid].transformations)==[0,pid] for pid in range(1,count+1))
