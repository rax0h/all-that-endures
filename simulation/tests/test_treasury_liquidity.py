import pytest
from ate_sim import generate_world
from ate_sim.currency import value_of
from ate_sim.institutions import ensure_core_societies


def test_treasury_exchange_requires_real_change_and_preserves_each_coin():
    w=generate_world(37)
    ensure_core_societies(w)
    society=w.institutions.institution_by_kind('adventure_society')
    counterparty=next(iter(w.people.values()))
    w.currency.credit(counterparty.id,{'bronze':1,'iron':10})
    w.currency.treasury_transfer(society.id,counterparty.id,{'bronze':1},deposit=True)
    before_minted=dict(w.currency.minted)
    before_consumed=dict(w.currency.consumed)
    before_total=value_of(w.currency.wallets[counterparty.id])+value_of(w.currency.treasuries[society.id])
    w.currency.treasury_exchange(society.id,counterparty.id,{'bronze':1},{'iron':10})
    assert w.currency.treasuries[society.id].get('bronze',0)==0
    assert w.currency.treasuries[society.id]['iron']==10
    assert w.currency.wallets[counterparty.id]['bronze']==1
    assert w.currency.wallets[counterparty.id]['iron']==0
    assert w.currency.minted==before_minted
    assert w.currency.consumed==before_consumed
    assert value_of(w.currency.wallets[counterparty.id])+value_of(w.currency.treasuries[society.id])==before_total


def test_treasury_exchange_cannot_create_missing_change_or_unequal_value():
    w=generate_world(38)
    ensure_core_societies(w)
    society=w.institutions.institution_by_kind('adventure_society')
    counterparty=next(iter(w.people.values()))
    w.currency.credit(counterparty.id,{'bronze':1,'iron':9})
    w.currency.treasury_transfer(society.id,counterparty.id,{'bronze':1},deposit=True)
    with pytest.raises(ValueError):
        w.currency.treasury_exchange(society.id,counterparty.id,{'bronze':1},{'iron':10})
    with pytest.raises(ValueError):
        w.currency.treasury_exchange(society.id,counterparty.id,{'bronze':1},{'iron':9})
