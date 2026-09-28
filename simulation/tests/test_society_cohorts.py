from ate_sim.advancement import AdvancementState
from ate_sim.core import Layer, Ref
from ate_sim.currency import value_of
from ate_sim.magic_economy import apprenticeship_step, _trainee_resources
from ate_sim.magic_resources import MagicAspiration, MagicResourceState, absorb_essence_resource
from ate_sim.checkpoint import dumps, loads
from ate_sim.history_archive import export_archive, HistoryArchive
from test_high_rank_economy import economy_world


class Willing:
    def random(self): return 0.


def trainee_world():
    w,p,_,society=economy_world()
    w.advancement=AdvancementState();w.magic_resources=MagicResourceState();p.rank=0;p.wealth=0
    for q in w.people.values():
        w.magic_resources.aspirations[q.id]=MagicAspiration(0,0,0,'test',0)
    w.magic_resources.aspirations[p.id]=MagicAspiration(1,3,20,'test',0,
        completion_goal=True,compromise_tolerance=1,stone_selectiveness=0)
    asset=next(iter(w.infrastructure.assets.values()));asset.condition=.2
    branch=w.institutions.branch_for('adventure_society',p.settlement)
    return w,p,society,branch,asset


def resource(w,p,kind,key,owner='person',owner_id=None):
    e=w.emit('test_resource_origin',Layer.REALITY,location=Ref('settlement',p.settlement))
    return w.magic_resources.create(kind,key,'Common',w.year,p.settlement,
        owner,p.id if owner_id is None else owner_id,e.id)


def fund(w,p,society,n):
    w.currency.credit(p.id,{'iron':n})
    w.currency.treasury_transfer(society.id,p.id,{'iron':n},deposit=True)


def test_no_unfunded_enrollment_or_fake_graduation_and_continuing_places():
    w,p,s,b,asset=trainee_world()
    apprenticeship_step(w)
    assert not b.trainees and not w.currency.minted
    fund(w,p,s,12);apprenticeship_step(w)
    enrollment=b.trainees[p.id]
    assert w.advancement.rank(p.id)==0
    assert not any(e.kind=='society_trainee_graduated' for e in w.events)
    w.year+=1;asset.condition=.2;apprenticeship_step(w)
    assert b.trainees[p.id]==enrollment
    assert sum(e.kind=='society_trainee_enrolled' for e in w.events)==1
    p.alive=False;apprenticeship_step(w)
    assert p.id not in b.trainees
    assert w.events[-1].kind=='society_trainee_departed'


def test_real_twenty_ability_graduation_releases_place_and_survives_archive(tmp_path):
    w,p,s,b,asset=trainee_world();fund(w,p,s,8)
    for key in ('fire','water','wind'):resource(w,p,'essence',key)
    for _ in range(16):resource(w,p,'awakening_stone','eyes')
    apprenticeship_step(w)
    assert w.advancement.rank(p.id)==1 and len(w.advancement.path(p.id).abilities)==20
    assert p.id not in b.trainees
    graduation=next(e for e in w.events if e.kind=='society_trainee_graduated')
    assert [w.events[i-1].kind for i in graduation.causes]==['society_trainee_enrolled','rank_advanced']
    assert graduation.data['abilities']==20
    assert all(r.consumed_by==p.id for r in w.magic_resources.resources.values())
    q=next(q for q in w.people.values() if q.id!=p.id and q.age>=16 and q.settlement==p.settlement)
    w.magic_resources.aspirations[q.id]=MagicAspiration(1,3,20,'test',1,completion_goal=True)
    w.year=1;asset.condition=.2;apprenticeship_step(w)
    assert q.id in b.trainees and p.id not in b.trainees
    restored=loads(dumps(w));assert restored.digest()==w.digest()
    assert restored.institutions.branches[b.id].trainees==b.trainees
    path=tmp_path/'cohort.sqlite';export_archive(w,path)
    with HistoryArchive(path) as archive:
        assert archive.event(graduation.id)['causes']==list(graduation.causes)
        assert graduation.id in [e['id'] for e in archive.timeline('person',p.id,limit=1000)]


def test_broker_pays_real_owners_and_uses_all_affordable_stones_without_cap():
    w,p,s,b,asset=trainee_world()
    for key in ('fire','water','wind'):
        r=resource(w,p,'essence',key);absorb_essence_resource(w,p.id,r.id)
    seller=next(q for q in w.people.values() if q.id!=p.id and q.settlement==p.settlement)
    # Seller's own needed stock is not offered.
    w.magic_resources.aspirations[seller.id]=MagicAspiration(1,3,20,'test',0,completion_goal=True)
    held=resource(w,p,'essence','life',owner_id=seller.id)
    stones=[resource(w,p,'awakening_stone','eyes',owner_id=seller.id) for _ in range(16)]
    w.currency.credit(p.id,{'iron':64});before=dict(w.currency.minted)
    _trainee_resources(w,p,[p,seller],{},Willing())
    assert w.advancement.rank(p.id)==1
    assert all(r.consumed_by==p.id and r.transfers for r in stones)
    assert held.owner_id==seller.id and held.consumed_year is None
    assert w.currency.wallets[seller.id]['iron']==64 and w.currency.wallets[p.id]['iron']==0
    assert w.currency.minted==before


def test_public_stock_payment_conserves_coins_and_empty_stock_cannot_complete():
    w,p,s,b,asset=trainee_world()
    w.currency.credit(p.id,{'iron':21})
    stock=[resource(w,p,'essence',key,'settlement',p.settlement) for key in ('fire','water','wind')]
    _trainee_resources(w,p,[p],{},Willing())
    assert len(w.advancement.path(p.id).abilities)==4 and w.advancement.rank(p.id)==0
    assert all(r.consumed_by==p.id for r in stock)
    assert w.currency.treasuries[s.id]['iron']==21
    assert value_of(w.currency.wallets[p.id])+value_of(w.currency.treasuries[s.id])==value_of(w.currency.minted)
    _trainee_resources(w,p,[p],{},Willing())
    assert w.advancement.rank(p.id)==0


def test_cohort_checkpoint_resume_is_deterministic():
    w,p,s,b,asset=trainee_world();fund(w,p,s,12);apprenticeship_step(w)
    other=loads(dumps(w))
    for world in (w,other):
        world.year+=1;world.infrastructure.assets[asset.id].condition=.2
        resource(world,world.people[p.id],'essence','fire','settlement',p.settlement)
        apprenticeship_step(world)
    assert w.digest()==other.digest()
