from simulation.ate_sim.currency import COIN_VALUE,denomination_for_rank,ranked_reward,value_of
from simulation.ate_sim import generate_world


def test_ranked_coin_exchange_values_match_canon_ratios():
    assert COIN_VALUE=={
        'lesser':1,
        'iron':100,
        'bronze':1000,
        'silver':10000,
        'gold':100000,
        'diamond':1000000,
    }
    assert COIN_VALUE['iron']==100*COIN_VALUE['lesser']
    for lower,higher in (('iron','bronze'),('bronze','silver'),('silver','gold'),('gold','diamond')):
        assert COIN_VALUE[higher]==10*COIN_VALUE[lower]


def test_reward_denominations_follow_rank_without_overpaying_above_rank():
    order=('lesser','iron','bronze','silver','gold','diamond')
    for rank in range(6):
        reward=ranked_reward(rank,1.)
        assert denomination_for_rank(rank) in reward
        assert max(order.index(d) for d in reward)<=rank
        assert value_of(reward)>0


def test_ranked_currency_is_persistent_world_state():
    w=generate_world(37)
    coins=ranked_reward(3,1.25)
    w.currency.credit(1,coins)
    assert w.currency.wallets[1]==coins
    assert w.currency.balance_value(1)==value_of(coins)
