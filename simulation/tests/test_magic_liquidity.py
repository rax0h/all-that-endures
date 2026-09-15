from types import SimpleNamespace

import pytest

from ate_sim.currency import COIN_VALUE, RankedCurrencyState, value_of
from ate_sim.magic_economy import _source_iron_change


def _total_value(currency, institution, people):
    treasury = currency.treasuries.get(institution, {})
    return value_of(treasury) + sum(currency.balance_value(p.id) for p in people)


def test_treasury_exchange_requires_real_change_and_conserves_value():
    currency = RankedCurrencyState()
    institution = 7
    counterparty = 11
    currency.treasuries[institution] = {'bronze': 1}
    currency.wallets[counterparty] = {'iron': 10}
    before = value_of(currency.treasuries[institution]) + currency.balance_value(counterparty)

    give, receive = currency.treasury_exchange(
        institution, counterparty, {'bronze': 1}, {'iron': 10}
    )

    assert give == {'bronze': 1}
    assert receive == {'iron': 10}
    assert currency.treasuries[institution] == {'bronze': 0, 'iron': 10}
    assert currency.wallets[counterparty] == {'iron': 0, 'bronze': 1}
    assert value_of(currency.treasuries[institution]) + currency.balance_value(counterparty) == before


def test_treasury_exchange_cannot_create_missing_iron_change():
    currency = RankedCurrencyState()
    currency.treasuries[7] = {'bronze': 1}
    currency.wallets[11] = {'iron': 9}

    with pytest.raises(ValueError, match='unfunded exchange'):
        currency.treasury_exchange(7, 11, {'bronze': 1}, {'iron': 10})

    assert currency.treasuries[7] == {'bronze': 1}
    assert currency.wallets[11] == {'iron': 9}


def test_society_sources_iron_only_from_real_local_holder_and_preserves_value():
    currency = RankedCurrencyState()
    institution = SimpleNamespace(id=7)
    holder = SimpleNamespace(id=11, alive=True)
    poor_change = SimpleNamespace(id=12, alive=True)
    people = [holder, poor_change]
    currency.treasuries[institution.id] = {'bronze': 1}
    currency.wallets[holder.id] = {'iron': 10}
    currency.wallets[poor_change.id] = {'iron': 3}
    events = []
    world = SimpleNamespace(
        currency=currency,
        emit=lambda *args, **kwargs: events.append((args, kwargs)),
    )
    before = _total_value(currency, institution.id, people)

    assert _source_iron_change(world, institution, 2, people, needed=4)

    assert currency.treasuries[institution.id].get('iron') == 10
    assert currency.treasuries[institution.id].get('bronze') == 0
    assert currency.wallets[holder.id].get('bronze') == 1
    assert currency.wallets[holder.id].get('iron') == 0
    assert currency.wallets[poor_change.id] == {'iron': 3}
    assert _total_value(currency, institution.id, people) == before
    assert len(events) == 1
    assert events[0][0][0] == 'society_money_changed'
    assert events[0][1]['mechanism'] == 'local exact-value denomination exchange'


def test_society_cannot_source_iron_when_no_counterparty_has_exact_change():
    currency = RankedCurrencyState()
    institution = SimpleNamespace(id=7)
    people = [SimpleNamespace(id=11, alive=True), SimpleNamespace(id=12, alive=True)]
    currency.treasuries[institution.id] = {'bronze': 2}
    currency.wallets[11] = {'iron': 9}
    currency.wallets[12] = {'iron': 4}
    world = SimpleNamespace(currency=currency, emit=lambda *args, **kwargs: None)
    before = _total_value(currency, institution.id, people)

    assert not _source_iron_change(world, institution, 2, people, needed=4)

    assert currency.treasuries[institution.id] == {'bronze': 2}
    assert currency.wallets[11] == {'iron': 9}
    assert currency.wallets[12] == {'iron': 4}
    assert _total_value(currency, institution.id, people) == before
