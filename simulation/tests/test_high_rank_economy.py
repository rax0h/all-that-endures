import pytest
from ate_sim.core import Layer,Ref
from ate_sim.currency import value_of
from ate_sim.institutions import ensure_core_societies
from ate_sim.magic_economy import spirit_economy_step,magical_service
from ate_sim.society_careers import society_career_step
from ate_sim.materials import _craft_once
from test_magic_understanding import configured_world
from test_magic_economy_and_lifespan import ResolutionRNG


def economy_world():
    w,p,path=configured_world();p.age=40;p.wealth=100
    for a in path.abilities:a.rank=5
    p.rank=5
    w.skills.get(p.id,'craft').level=.9
    w.ambient_magic.field(p.settlement).level=1.4
    ensure_core_societies(w)
    adv=w.institutions.institution_by_kind('adventure_society');adv.members.add(p.id)
    e=w.emit('test_construction',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement))
    w.infrastructure.create('spirit_coin_farm',(p.settlement,),1,1,0,e.id)
    return w,p,path,adv


def test_high_tier_supply_requires_working_farm_ambient_and_operator_and_funds_payment():
    w,p,path,adv=economy_world()
    spirit_economy_step(w,ResolutionRNG())
    assert w.currency.wallets[p.id]['diamond']==12
    assert w.currency.treasuries[adv.id]['diamond']==12
    assert w.currency.minted['diamond']==24
    # Diminished ambient cannot keep producing Diamond coins merely for a Diamond.
    w.ambient_magic.field(p.settlement).level=.1
    spirit_economy_step(w,ResolutionRNG())
    assert w.currency.minted['diamond']==24
    assert w.currency.consumed['diamond']==1
    assert w.currency.minted['iron']==24


def test_unfunded_contract_cannot_mint_reward_and_actual_solver_can_claim():
    w,p,path,adv=economy_world()
    w.infrastructure.assets.clear() # no farm, and no construction materials
    origin=w.emit('ranked_magic_manifested',Layer.REALITY,location=Ref('settlement',p.settlement),rank=5)
    resolution=w.emit('ranked_threat_resolved',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),(origin.id,),threat_rank=5)
    w.threat_ecology.resolutions[origin.id]=resolution.id
    b=w.institutions.branch_for('adventure_society',p.settlement)
    n=w.institutions.post_notice(b.id,0,'ranked_magic_manifested',p.settlement,origin.id);n.required_rank=5
    n.status='assigned';n.assigned_to=next(i for i in w.people if i!=p.id)
    society_career_step(w,ResolutionRNG())
    assert n.assigned_to==p.id and n.status=='assigned'
    assert not w.currency.minted
    w.currency.credit(p.id,{'diamond':4});w.currency.treasury_transfer(adv.id,p.id,{'diamond':4},deposit=True)
    # ResolutionRNG's first draw is .99; use an always-successful decision RNG.
    class Zero:
        def stream(self,*args):return self
        def random(self):return 0.
    society_career_step(w,Zero())
    assert n.status=='resolved'
    assert w.currency.wallets[p.id]['diamond']==4
    assert w.currency.treasuries[adv.id]['diamond']==0
    assert w.currency.minted=={'diamond':4}
    e=w.events[n.resolved_event-1]
    assert resolution.id in e.causes and e.data['reward_rank']==5


def test_diamond_material_purchase_retains_value_and_provenance():
    w,p,path,adv=economy_world()
    seller=next(q for q in w.people.values() if q.id!=p.id)
    origin=w.emit('monster_remains_harvested',Layer.REALITY,(Ref('person',seller.id),),Ref('settlement',p.settlement),material_rank=5)
    lot=w.materials.create_lot('monster_remains',1,.9,p.settlement,seller.id,0,origin.id,('test beast',),5)
    # Raw skill is capped at one; use the actual random selection branch.
    class Draws:
        def random(self):return 0.
        def uniform(self,a,b):return 0.
    assert not _craft_once(w,p.settlement,p,Draws(),Layer,Ref)
    w.currency.credit(p.id,{'diamond':20})
    assert _craft_once(w,p.settlement,p,Draws(),Layer,Ref)
    item=next(i for i in w.materials.items.values() if lot.id in i.materials)
    assert item.item_rank==5 and lot.consumed==1
    assert w.currency.wallets[seller.id]['diamond']>0
    assert sum(v.get('diamond',0) for v in w.currency.wallets.values())==20


def test_noncombat_healing_is_priced_relevant_work_not_event_exposure():
    w,p,path,adv=economy_world();a=path.abilities[0];a.function='recovery';a.rank=4
    client=next(q for q in w.people.values() if q.id!=p.id);client.health=.5
    w.currency.credit(client.id,{'gold':2})
    assert magical_service(w,p,client,a,kind='healing',difficulty=4,constraint='injury:gold:dry')
    assert client.health>.5 and a.understanding.evidence
    assert all(not b.understanding.evidence for b in path.abilities[1:])
    assert not magical_service(w,p,client,a,kind='healing',difficulty=4,constraint='another')


def test_exchange_needs_real_counterparty_change_and_preserves_value():
    w,p,_,_=economy_world();q=next(i for i in w.people if i!=p.id)
    w.currency.credit(p.id,{'diamond':1})
    with pytest.raises(ValueError):w.currency.exchange(p.id,q,{'diamond':1},{'gold':10})
    w.currency.credit(q,{'gold':10})
    w.currency.exchange(p.id,q,{'diamond':1},{'gold':10})
    assert w.currency.wallets[p.id]['gold']==10
    assert value_of(w.currency.wallets[p.id])==1000000


def test_remote_ranked_response_requires_a_real_road_and_retains_journey():
    from ate_sim.threat_ecology import MagicalThreat,threat_ecology_step
    w,p,path,adv=economy_world()
    target=next(s for s in w.settlements if s!=p.settlement)
    origin=w.emit('ranked_magic_manifested',Layer.REALITY,location=Ref('settlement',target),rank=5)
    t=MagicalThreat(100,'monster',5,target,0,1.4,origin_event=origin.id,form='test predator')
    w.threat_ecology.threats[100]=t
    b=w.institutions.branch_for('adventure_society',target)
    n=w.institutions.post_notice(b.id,0,'ranked_magic_manifested',target,origin.id);n.required_rank=5;n.status='assigned';n.assigned_to=p.id
    # Explicitly remove routes in this isolated dispatch test.
    w.infrastructure.assets.clear()
    threat_ecology_step(w,ResolutionRNG())
    assert t.status=='active'
    w.infrastructure.create('road',(p.settlement,target),1,1,0)
    threat_ecology_step(w,ResolutionRNG())
    assert t.status=='resolved'
    journey=next(e for e in w.events if e.kind=='ranked_response_journey')
    assert journey.data['destination']==target and journey.causes==(origin.id,)
    assert p.settlement!=target # temporary travel does not fabricate migration


def test_rank_selection_index_updates_and_new_state_survives_checkpoint():
    from ate_sim.checkpoint import dumps,loads
    w,p,path,adv=economy_world()
    origin=w.emit('test_material',Layer.REALITY)
    first=w.materials.create_lot('stone',1,.8,p.settlement,p.id,0,origin.id,(),4)
    assert w.materials.best_at_rank(p.settlement,4).id==first.id
    second=w.materials.create_lot('stone',1,.9,p.settlement,p.id,0,origin.id,(),4)
    assert w.materials.best_at_rank(p.settlement,4).id==second.id
    w.materials.consume(second,1)
    assert w.materials.best_at_rank(p.settlement,4).id==first.id
    spirit_economy_step(w,ResolutionRNG())
    restored=loads(dumps(w))
    assert restored.digest()==w.digest()
    assert restored.currency.treasuries==w.currency.treasuries
    restored.materials.rebuild_active_index()
    assert restored.materials.best_at_rank(p.settlement,4).id==first.id


def test_archive_economy_reconciles_supply_treasury_and_detects_unrecorded_credit(tmp_path):
    from ate_sim.history_archive import export_archive,HistoryArchive
    from inspect_magic_economy import inspect
    w,p,_,_=economy_world()
    spirit_economy_step(w,ResolutionRNG())
    path=tmp_path/'funded.sqlite';export_archive(w,path)
    with HistoryArchive(path) as archive:
        assert not any(inspect(archive)['currency_conservation_residual'].values())
        assert archive.record('treasury',1)['diamond']==12
    w.currency.credit(p.id,{'diamond':1}) # deliberate missing production event
    path=tmp_path/'unrecorded.sqlite';export_archive(w,path)
    with HistoryArchive(path) as archive:
        assert inspect(archive)['currency_conservation_residual']['diamond']==-1
