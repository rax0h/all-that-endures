from __future__ import annotations
from dataclasses import dataclass,field

# Canon-inspired denomination ratios used by the simulation economy:
# 100 lesser = 1 iron; every higher rank is 10x the previous denomination.
DENOMINATIONS=('lesser','iron','bronze','silver','gold','diamond')
COIN_VALUE={'lesser':1,'iron':100,'bronze':1000,'silver':10000,'gold':100000,'diamond':1000000}
RANK_DENOMINATION={0:'lesser',1:'iron',2:'bronze',3:'silver',4:'gold',5:'diamond'}

@dataclass
class RankedCurrencyState:
 wallets:dict[int,dict[str,int]]=field(default_factory=dict)
 minted:dict[str,int]=field(default_factory=dict)
 def wallet(self,pid):
  return self.wallets.setdefault(pid,{})
 def credit(self,pid,coins):
  w=self.wallet(pid)
  for denom,count in coins.items():
   if denom not in COIN_VALUE:raise ValueError(f'unknown coin denomination: {denom}')
   count=int(count)
   if count<0:raise ValueError('cannot credit negative coins')
   if count:
    w[denom]=w.get(denom,0)+count;self.minted[denom]=self.minted.get(denom,0)+count
  return dict(coins)
 def balance_value(self,pid):
  return sum(COIN_VALUE[d]*n for d,n in self.wallets.get(pid,{}).items())

def denomination_for_rank(rank):return RANK_DENOMINATION[max(0,min(5,int(rank)))]
def value_of(coins):return sum(COIN_VALUE[d]*int(n) for d,n in coins.items())

def ranked_reward(rank,scale=1.,include_change=True):
 """Return a rank-appropriate reward package without ever paying above the recipient/job rank.

 The rank denomination carries the bulk of the reward. Lower-ranked coins provide ordinary change
 and incidental expenses. Exact reward size is simulation-specific; denomination exchange ratios are
 fixed by COIN_VALUE.
 """
 rank=max(0,min(5,int(rank)));primary=denomination_for_rank(rank);amount=max(1,int(round(4*max(.25,scale))))
 out={primary:amount}
 if include_change and rank>0:
  lower=denomination_for_rank(rank-1);out[lower]=max(1,int(round(10*max(.25,scale))))
 return out
