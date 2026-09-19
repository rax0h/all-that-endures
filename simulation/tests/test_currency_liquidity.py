import pytest
from ate_sim.currency import RankedCurrencyState,value_of


def test_treasury_exchange_requires_real_change_and_conserves_value():
    c=RankedCurrencyState();c.treasuries[7]={'bronze':1};c.wallets[11]={'iron':10}
    before=value_of(c.treasuries[7])+c.balance_value(11)
    give,receive=c.treasury_exchange(7,11,{'bronze':1},{'iron':10})
    assert give=={'bronze':1} and receive=={'iron':10}
    assert c.treasuries[7].get('iron')==10 and c.wallets[11].get('bronze')==1
    assert value_of(c.treasuries[7])+c.balance_value(11)==before


def test_treasury_exchange_cannot_create_missing_change():
    c=RankedCurrencyState();c.treasuries[7]={'bronze':1};c.wallets[11]={'iron':9}
    with pytest.raises(ValueError):c.treasury_exchange(7,11,{'bronze':1},{'iron':10})
    assert c.treasuries[7]=={'bronze':1} and c.wallets[11]=={'iron':9}
