from copy import deepcopy
import pickle
from simulation.ate_sim.materials import MaterialEconomy

def assert_selection_matches_archive(state, sid):
    available = state.available(sid)
    expected = max(available, key=lambda l:(l.quality+(.2 if l.magical_properties else 0.),-l.id)) if available else None
    assert state.best_available(sid) is expected
    assert state.magical_available_count(sid) == sum(bool(l.magical_properties) for l in available)
    assert state.has_available(sid) == bool(available)

def test_material_selection_survives_creation_consumption_rebuild_and_checkpoint():
    state = MaterialEconomy()
    for n in range(120):
        state.create_lot("timber",3.,(n % 9)*.1,n % 3,1,n,n,("growth",) if n % 2 else ())
    for sid in range(3):
        assert_selection_matches_archive(state,sid)
    for n in range(200):
        sid = n % 3
        lot = state.best_available(sid)
        if lot:
            state.consume(lot,.75)
            assert_selection_matches_archive(state,sid)
        if n % 7 == 0:
            state.create_lot("stone",2.,.9,sid,1,200+n,200+n,("earth",))
            assert_selection_matches_archive(state,sid)
    for copy in (deepcopy(state),pickle.loads(pickle.dumps(state))):
        for sid in range(3):
            assert_selection_matches_archive(copy,sid)
        copy.rebuild_active_index()
        for sid in range(3):
            assert_selection_matches_archive(copy,sid)
    assert len(state.lots) == 149

def test_selection_ties_partial_and_repeated_consumption():
    state = MaterialEconomy()
    a = state.create_lot("ore",1.,.5,1,1,0,1,("earth",))
    b = state.create_lot("ore",1.,.5,1,1,0,2,("earth",))
    assert state.best_available(1) is a
    state.consume(a,.5)
    assert state.best_available(1) is a
    state.consume(a,.5)
    assert state.best_available(1) is b
    state.consume(a,10.)
    assert state.magical_available_count(1) == 1
    state.consume(b,1.)
    assert_selection_matches_archive(state,1)
    assert a.id in state.lots and b.id in state.lots

def test_hot_selection_does_not_scan_archive_after_index_build():
    state = MaterialEconomy()
    for n in range(10000):
        state.create_lot("ore",1.,(n % 19)*.01,1,1,n,n)
    state.best_available(1)
    class NoIteration(dict):
        def values(self): raise AssertionError("archive scan")
        def items(self): raise AssertionError("archive scan")
        def __iter__(self): raise AssertionError("archive scan")
    state.lots = NoIteration(state.lots)
    for _ in range(100):
        lot = state.best_available(1)
        state.consume(lot,1.)
        state.magical_available_count(1)

def test_crafting_capacity_matches_original_sum_at_boundaries_and_after_consumption():
    state = MaterialEconomy()
    for quantity in (0.,.001,.01,.99,1.,7.999999999,8.,8.000000001,30.,80.):
        lot=state.create_lot("ore",quantity,.5,1,1,0,1)
        for amount in (0.,.1,.5,1.):
            state.consume(lot,amount)
            for limit in (1,2,3,10):
                units=sum(max(0.,l.quantity-l.consumed) for l in state.available(1))
                assert state.crafting_capacity(1,limit) == min(limit,max(0,int(units//8)))
    state.rebuild_active_index()
    for limit in (1,2,3,10):
        units=sum(max(0.,l.quantity-l.consumed) for l in state.available(1))
        assert state.crafting_capacity(1,limit) == min(limit,max(0,int(units//8)))

def test_saturated_crafting_capacity_never_scans_stock_after_index_build():
    state = MaterialEconomy()
    for n in range(10000):
        state.create_lot("ore",4.,.5,1,1,n,n)
    assert state.crafting_capacity(1,10) == 10
    state.available=lambda *args: (_ for _ in ()).throw(AssertionError("stock scan"))
    for _ in range(100):
        assert state.crafting_capacity(1,10) == 10

def test_selection_ids_tracks_exact_active_set_order_and_only_invalidates_on_membership_change():
    state = MaterialEconomy()
    for n in range(100):
        state.create_lot("ore",2.,.5,1,1,n,n)
    pool=state.selection_ids(1)
    assert list(pool) == [l.id for l in state.available(1)]
    state.consume(state.lots[pool[0]],.5)
    assert state.selection_ids(1) is pool
    state.consume(state.lots[pool[0]],2.)
    assert list(state.selection_ids(1)) == [l.id for l in state.available(1)]
    state.create_lot("stone",3.,.6,1,1,101,101)
    assert list(state.selection_ids(1)) == [l.id for l in state.available(1)]
