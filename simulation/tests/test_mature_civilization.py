from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.core import Layer,Ref,RNG
from ate_sim.history_archive import export_archive,HistoryArchive
from validate_magic_progression import validate
from inspect_magic_economy import inspect
from ate_sim.magic_economy import society_change_step
from ate_sim.currency import value_of
from test_high_rank_economy import economy_world


def test_mature_initialization_has_real_consumed_resources_and_legal_paths(tmp_path):
    w=generate_world(843000,mature=True)
    adults=[p for p in w.people.values() if p.age>=16]
    users=[p for p in adults if w.advancement.path(p.id)]
    assert .65<len(users)/len(adults)<.9
    assert any(p.rank==1 for p in users)
    for p in users:
        path=w.advancement.path(p.id)
        assert p.rank==w.advancement.rank(p.id)
        assert p.rank==0 or len(path.abilities)==20
    assert all(r.origin_event for r in w.magic_resources.resources.values())
    out=tmp_path/'mature.sqlite';export_archive(w,out)
    with HistoryArchive(out) as archive:assert validate(archive)['valid']
    assert generate_world(843000,mature=True).digest()==w.digest()


def test_mature_checkpoint_resume():
    from ate_sim.checkpoint import dumps,loads
    direct=Simulation(generate_world(843001,mature=True)).run(30)
    staged=Simulation(generate_world(843001,mature=True)).run(15)
    assert Simulation(loads(dumps(staged))).run(15).digest()==direct.digest()


def test_exchange_keeps_real_coins_and_personal_reserve():
    w,p,_,adv=economy_world()
    w.currency.credit(p.id,{'iron':100,'bronze':8})
    w.currency.treasury_transfer(adv.id,p.id,{'bronze':8},deposit=True)
    supply=dict(w.currency.minted)
    society_change_step(w)
    assert w.currency.wallets[p.id]['iron']==20
    assert w.currency.wallets[p.id]['bronze']==8
    assert w.currency.treasuries[adv.id]['iron']==80
    assert w.currency.treasuries[adv.id]['bronze']==0
    assert w.currency.minted==supply
    e=next(e for e in w.events if e.kind=='society_change_exchanged')
    assert value_of(e.data['coin_deposit'])==value_of(e.data['coin_reward'])
    before=w.digest();society_change_step(w);assert w.digest()==before


def test_exchange_requires_counterparty_change():
    w,p,_,adv=economy_world()
    w.currency.credit(p.id,{'diamond':1})
    w.currency.treasury_transfer(adv.id,p.id,{'diamond':1},deposit=True)
    before=w.digest();society_change_step(w);assert w.digest()==before


def test_archive_rejects_incomplete_iron(tmp_path):
    from ate_sim.magic_resources import absorb_essence_resource
    w=generate_world(17)
    p=next(p for p in w.people.values() if w.advancement.path(p.id) is None)
    for key in ('fire','water','wind'):
        r=w.magic_resources.create('essence',key,'Common',0,p.settlement,'person',p.id)
        absorb_essence_resource(w,p.id,r.id)
    p.rank=1
    w.emit('rank_advanced',Layer.REALITY,(Ref('person',p.id),),from_rank=0,to_rank=1)
    out=tmp_path/'invalid.sqlite';export_archive(w,out)
    with HistoryArchive(out) as archive:
        report=validate(archive)
        assert not report['valid']
        assert any(v['issue']=='body prerequisites' for v in report['violations'])


def test_field_harvest_ownership_is_limited_to_actual_participants():
    from ate_sim.magical_civilization import _expedition_step
    from ate_sim.magic_resources import _aspiration
    w=generate_world(843000,mature=True)
    sid=min(w.settlements);people=[p for p in w.people.values() if p.settlement==sid and p.age>=16]
    for p in people:_aspiration(w,p).risk_tolerance=1.;_aspiration(w,p).desired_base_essences=3
    w.ambient_magic.field(sid).level=.9
    _expedition_step(w,RNG(83),sid,people,[p for p in people if w.advancement.path(p.id)],w.institutions.branch_for('adventure_society',sid),w.institutions.branch_for('magic_society',sid))
    trips={e.id:e for e in w.events if e.kind=='magical_expedition'}
    workers=[pid for e in trips.values() for pid in e.data['participants']]
    assert len(workers)==len(set(workers))
    recovered=[e for e in w.events if e.kind=='magical_expedition_resource_recovered']
    assert recovered
    for e in recovered:
        trip=trips[e.causes[0]];resource=w.magic_resources.resources[e.data['resource']]
        assert resource.owner_id in trip.data['participants']
        assert resource.origin_event in e.causes


def test_transfer_index_matches_full_scan_with_live_mutations():
    from unittest.mock import patch
    from ate_sim.magic_resources import _transfer_to_seeker
    indexed=Simulation(generate_world(843000,mature=True)).run(100)
    def full_scan(*args,**kwargs):
        kwargs.pop('market',None)
        return _transfer_to_seeker(*args,**kwargs)
    with patch('ate_sim.magical_civilization._transfer_to_seeker',full_scan):
        reference=Simulation(generate_world(843000,mature=True)).run(100)
    assert indexed.digest()==reference.digest()
