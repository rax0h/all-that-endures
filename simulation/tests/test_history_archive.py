import sqlite3
import pytest
from simulation.ate_sim.core import World, Person, Layer, Ref
from simulation.ate_sim.engine import Simulation
from simulation.ate_sim.worldgen import generate_world
from simulation.ate_sim.history_archive import export_archive, HistoryArchive, encode
from simulation.ate_sim.personhood import PersonhoodView, EntityIdentity, Embodiment, from_person
from simulation.ate_sim import checkpoint


def test_real_life_teaching_and_provenance_survive_export(tmp_path):
    w = Simulation(generate_world(843000)).run(100)
    before = w.digest()
    path = tmp_path / 'history.sqlite'
    export_archive(w, path)
    assert w.digest() == before
    with HistoryArchive(path) as a:
        birth = next(e for e in w.events if e.kind == 'birth')
        child = next(r.id for r in birth.actors if r.kind == 'person' and w.people[r.id].born == birth.year)
        life = a.person(child, limit=1000)
        assert a.record('person', child)['parents'] == list(w.people[child].parents)
        assert birth.id in [e['id'] for e in life['timeline']]
        for pid in w.people[child].parents:
            assert any(r['source_kind']=='person' and r['source_id']==str(child) and r['relation']=='parent' for r in a.links('person', pid, True))
        teaching = next(e for e in w.events if e.kind == 'skill_taught')
        student = teaching.actors[1].id
        assert teaching.id in [e['id'] for e in a.timeline('person', student, limit=1000)]
        item = next(iter(w.materials.items.values()))
        evidence = a.provenance('item', item.id)
        assert evidence['record']['materials'] == list(item.materials)
        chain = a.causal_chain(item.origin_event)
        assert not chain['truncated']
        for lotid in item.materials:
            assert w.materials.lots[lotid].origin_event in [e['id'] for e in chain['events']]
        for r in w.magic_resources.resources.values():
            assert a.record('magic_resource', r.id)['transfers'] == r.transfers
            if r.consumed_event:
                assert a.event(r.consumed_event)['data']['resource'] == r.id
        with pytest.raises(sqlite3.OperationalError): a.db.execute('DELETE FROM records')
        assert a.records('person', limit=1)[0]['id'] == '1'
        assert a.records('unmodeled_entity') == []
        assert a.person(999999)['unknown']
        assert a.causal_chain(999999)['unknown']
        assert a.metadata()['world_digest'] == before


def test_deterministic_archive_checkpoint_and_no_simulation_effect(tmp_path):
    w = Simulation(generate_world(5)).run(5)
    restored = checkpoint.loads(checkpoint.dumps(w))
    control = checkpoint.loads(checkpoint.dumps(w))
    # Reordering authoritative maps and populating caches cannot change export.
    restored.people = dict(reversed(list(restored.people.items())))
    for pid in restored.people: restored.social.relationships_for(pid)
    reports = [export_archive(x, tmp_path / str(n)) for n, x in enumerate((w, restored))]
    assert reports[0]['logical_sha256'] == reports[1]['logical_sha256']
    assert (tmp_path/'0').read_bytes() == (tmp_path/'1').read_bytes()
    assert Simulation(w).run(5).digest() == Simulation(control).run(5).digest()
    with pytest.raises(FileExistsError): export_archive(w, tmp_path/'0')


def test_long_chains_are_iterative_bounded_and_missing_causes_fail(tmp_path):
    w = World(1)
    for i in range(1200): w.emit('test', Layer.REALITY, causes=() if i==0 else (i,))
    export_archive(w, tmp_path/'chain')
    with HistoryArchive(tmp_path/'chain') as a:
        assert len(a.causal_chain(1200, limit=2000)['events']) == 1200
        assert a.causal_chain(1200, limit=10)['truncated']
        assert len(a.causal_chain(1, descendants=True, limit=2000)['events']) == 1200
    w.events[-1].causes = (9999,)
    with pytest.raises(ValueError): export_archive(w, tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_personhood_does_not_invent_mental_or_biological_facts():
    p = Person(7, 0, 1, 1, species='elf', curiosity=.8)
    view = from_person(p, [(3, .2)])
    assert view.capabilities.reasoning is None
    assert view.subjective.beliefs == ((3, .2),)
    assert view.subjective.memories == () and view.subjective.self_claims == ()
    assert view.dispositions.curiosity == .8
    spirit = PersonhoodView(EntityIdentity('future_spirit', 'example'), Embodiment())
    assert spirit.embodiment.species is None
    assert spirit.identity != view.identity
    assert 'World' not in encode(view)


def test_settlement_windows_and_explicit_uncertainty(tmp_path):
    w = World(1)
    w.people[1] = Person(1, -20, 3, 1)
    w.year = 10
    e = w.emit('observed_test', Layer.REALITY, (Ref('person',1),), Ref('settlement',3))
    claim = w.knowledge.claim('test', 'unverified rumor', None, e.id)
    w.knowledge.beliefs[(1,claim)] = .9
    export_archive(w, tmp_path/'window')
    with HistoryArchive(tmp_path/'window') as a:
        assert a.timeline('settlement',3,1,9) == []
        assert a.timeline('settlement',3,10,10)[0]['id'] == e.id
        assert a.record('claim',claim)['truth'] is None
        assert a.record('personhood',1)['subjective']['beliefs'] == [[claim,.9]]
        assert a.record('personhood',1)['subjective']['observations'] == []
        assert a.timeline('settlement',3,10,10,offset=1) == []
