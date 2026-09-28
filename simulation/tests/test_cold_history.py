import copy
import hashlib
import json
import pickle
from dataclasses import asdict

import pytest

from simulation.ate_sim.core import World, Person, Layer, Ref, _canonical
from simulation.ate_sim.event_log import EventLog
from simulation.ate_sim.record_index import RecordTable, indexed
from simulation.ate_sim.engine import Simulation
from simulation.ate_sim.worldgen import generate_world
from simulation.ate_sim.checkpoint import dumps, loads
from simulation.ate_sim.history_archive import export_archive, HistoryArchive


def legacy_digest(w):
    return hashlib.sha256(json.dumps(_canonical(w), sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def event_world():
    w = World(1)
    for i in range(6200):
        w.year = i // 20
        w.emit('record', Layer.REALITY, (Ref('person', 1),),
               causes=() if i == 0 else (i,), nested={'text': ['é', i]})
    return w


def test_cold_events_are_lossless_bounded_immutable_and_seekable():
    w = event_world()
    before = copy.deepcopy(w.events)
    digest = legacy_digest(w)
    w.events = EventLog(w.events)
    w.events.seal_before(w.year - 2)
    assert w.events.storage_stats()['sealed_events'] == 4096
    assert w.events == before
    assert w.digest() == digest == legacy_digest(w)
    for first, last in ((0, 0), (-1, 400), (50, 230), (400, 500), (260, 250)):
        assert w.events_between(first, last) == [e for e in before if first <= e.year <= last]
    assert w.events[::-7] == before[::-7]
    with pytest.raises(TypeError): w.events[0].kind = 'rewritten'
    with pytest.raises(TypeError): del w.events[0].kind
    with pytest.raises(TypeError): w.events[0].data['nested']['text'].append('rewrite')
    # A current-year query must not even decompress an old segment.
    w.events._chunk = lambda _: pytest.fail('read cold history for current work')
    assert w.events_between(w.year) == before[-20:]
    del w.events._chunk
    w.emit('next', Layer.REALITY, causes=(1,))
    assert w.events[-1].causes == (1,)
    assert len(w.events._cache) <= w.events.cache_size


def test_cold_checkpoint_and_archive_match_plain_history(tmp_path):
    w = event_world()
    plain = export_archive(w, tmp_path/'plain.sqlite')
    w.events = EventLog(w.events)
    w.events.seal_before(w.year - 2)
    restored = loads(dumps(w))
    assert restored.events == w.events
    assert restored.digest() == w.digest()
    assert restored.events._cache is not w.events._cache
    cold = export_archive(restored, tmp_path/'cold.sqlite')
    assert cold['logical_sha256'] == plain['logical_sha256']
    assert (tmp_path/'plain.sqlite').read_bytes() == (tmp_path/'cold.sqlite').read_bytes()
    with HistoryArchive(tmp_path/'cold.sqlite') as a:
        assert len(a.causal_chain(6200, limit=7000)['events']) == 6200


def test_record_index_tracks_edits_deletions_replacements_and_rebuilds():
    table = RecordTable({i: Person(i, 0, i % 2, 1) for i in range(20)})
    def check(t):
        for alive in (True, False):
            assert set(t.ids('alive', alive)) == {p.id for p in t.values() if p.alive == alive}
            for sid in (0, 1):
                assert set(t.ids(('alive', 'settlement'), alive, sid)) == {
                    p.id for p in t.values() if p.alive == alive and p.settlement == sid}
    check(table)
    for i in range(20):
        table[i].alive = bool(i % 3)
        table[i].settlement = (i + 1) % 2
        check(table)
    table[4] = Person(4, 0, 0, 1)
    del table[7]
    table.pop(8)
    table.popitem()
    table.update({30: Person(30, 0, 1, 1)})
    check(table)
    for cloned in (copy.deepcopy(table), pickle.loads(pickle.dumps(table))):
        check(cloned)
        cloned[4].alive = False
        check(cloned)
        assert table[4].alive
    table.clear()
    check(table)
    with pytest.raises(KeyError): table.popitem()


def test_restored_index_and_cold_history_resume_exactly():
    w = Simulation(generate_world(843000)).run(110)
    assert w.events.storage_stats()['sealed_events'] > 0
    assert w.digest() == legacy_digest(w)
    assert _canonical(asdict(w)) == _canonical(w)
    restored = loads(dumps(w))
    # All disposable indexes may be dropped/rebuilt without changing facts.
    restored.people = dict(restored.people)
    restored.households = dict(restored.households)
    restored.institutions.applications = dict(restored.institutions.applications)
    restored.events = list(restored.events)
    assert Simulation(w).run(15).digest() == Simulation(restored).run(15).digest()


def test_living_index_observes_external_changes_without_archive_iteration():
    w = World(1)
    w.people = {i: Person(i, 0, 1, 1, alive=i == 1) for i in range(10000)}
    assert [p.id for p in w.current_people()] == [1]
    w.people.values = lambda: pytest.fail('scanned historical people')
    w.people[9999].alive = True
    w.people[1].alive = False
    assert [p.id for p in w.current_people()] == [9999]


def test_indexed_inheritance_matches_archive_query_and_preserves_cause_order():
    from simulation.ate_sim.core import Household
    from simulation.ate_sim.households import inheritance_property_step
    w=World(1)
    for i in range(1,9):
        w.people[i]=Person(i,0,1,i,alive=i>4)
        w.households[i]=Household(i,1,members=[i],alive=i>4)
        w.economy.create('dwelling',1,'household',i,10,0)
    w.genealogy.birth(5,(1,2))
    w.genealogy.birth(6,(1,3))
    w.genealogy.birth(7,(4,))
    w.people[7].alive=False  # no living heir, estate must persist
    control=copy.deepcopy(w)
    for prop in control.economy.property.values():
        h=control.households[prop.owner_id]
        if h.alive:continue
        heirs=[pid for parent in h.members for pid in control.genealogy.children.get(parent,())
               if pid in control.people and control.people[pid].alive]
        if heirs:
            heir=min(heirs)
            e=control.emit('property_inherited',Layer.SOCIETY,(Ref('person',heir),),Ref('settlement',prop.settlement),property=prop.id)
            control.economy.transfer(prop.id,'person',heir,e.id,control.year)
    inheritance_property_step(w)
    assert w.digest()==control.digest()
    assert w.economy.property[4].owner_kind=='household'
    w.people[7].alive=True
    inheritance_property_step(w)
    assert w.economy.property[4].owner_id==7


def test_active_institution_queries_do_not_scan_completed_history():
    from simulation.ate_sim.institutions import InstitutionState, SocietyApplication, AdventureNotice
    state=InstitutionState()
    state.applications={i:SocietyApplication(i,'adventure_society',i,1,0,True,passed=True) for i in range(10000)}
    state.notices={i:AdventureNotice(i,1,0,'test',1,i,status='resolved') for i in range(10000)}
    assert state.has_application(9999,'adventure_society',qualified=True)
    assert state.active_notices()==[]
    for table in (state.applications,state.notices):
        table.values=lambda: pytest.fail('historical scan')
        table.items=lambda: pytest.fail('historical scan')
    state.applications[9999].passed=False
    assert not state.has_application(9999,'adventure_society',qualified=True)
    assert state.has_application(9999,'adventure_society')
    assert state.latest_application(9999,'adventure_society').id==9999
    state.notices[9999].status='open'
    assert [n.id for n in state.active_notices()]==[9999]


def test_church_rng_draw_order_survives_checkpoint_with_sparse_member_ids():
    from simulation.ate_sim.divinity import divine_step
    ids=[10611,4943,12937,21329,1582,2373,26911,17559,3084,11982,19096,1900]
    w=generate_world(7)
    w.people={i:Person(i,0,1,1,age=25) for i in ids}
    w.year=1
    e=w.emit('church_founded',Layer.SOCIETY)
    church=w.divinity.create_church('knowledge',1,1,e.id)
    for i in ids:
        church.followers.add(i)
        w.divinity.gods['knowledge'].relationships[i]=.9
    restored=loads(dumps(w))
    class Always:
        def stream(self,*args):return self
        def random(self):return 0.
    divine_step(w,Always());divine_step(restored,Always())
    assert w.digest()==restored.digest()
    assert [e.actors[0].id for e in w.events if e.kind=='divine_essence_granted']==sorted(ids)


def test_archive_set_membership_links_have_stable_ordinals(tmp_path):
    w=generate_world(7,mature=True)
    institution=next(iter(w.institutions.institutions.values()))
    ids=[10611,4943,12937,21329,1582,2373,26911,17559,3084,11982,19096,1900]
    for i in ids:
        w.people[i]=Person(i,0,1,1)
        institution.members.add(i)
    restored=loads(dumps(w))
    a=export_archive(w,tmp_path/'a.sqlite')
    b=export_archive(restored,tmp_path/'b.sqlite')
    assert a['logical_sha256']==b['logical_sha256']
    assert (tmp_path/'a.sqlite').read_bytes()==(tmp_path/'b.sqlite').read_bytes()
