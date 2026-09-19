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
 treasuries:dict[int,dict[str,int]]=field(default_factory=dict)
 consumed:dict[str,int]=field(default_factory=dict)
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
 def transfer(self,payer,payee,coins):
  """Transfer actual denominations; valuation alone never makes change."""
  coins=dict(coins)
  if any(d not in COIN_VALUE or type(n) is not int or n<0 for d,n in coins.items()):raise ValueError('invalid coin transfer')
  source=self.wallets.get(payer,{})
  if any(source.get(d,0)<n for d,n in coins.items()):raise ValueError('insufficient denomination balance')
  if not any(coins.values()):return coins
  if payer==payee:return coins
  destination=self.wallet(payee)
  for d,n in coins.items():
   if n:source[d]-=n;destination[d]=destination.get(d,0)+n
  return coins

 def treasury_transfer(self,institution,pid,coins,*,deposit=False):
  treasury=self.treasuries.setdefault(institution,{})
  source=self.wallets.get(pid,{}) if deposit else treasury
  if any(d not in COIN_VALUE or type(n) is not int or n<0 for d,n in coins.items()):raise ValueError('invalid treasury transfer')
  if any(source.get(d,0)<n for d,n in coins.items()):raise ValueError('unfunded treasury transfer')
  destination=treasury if deposit else self.wallet(pid)
  for d,n in coins.items():source[d]=source.get(d,0)-n;destination[d]=destination.get(d,0)+n
  return dict(coins)
 def consume(self,pid,coins):
  source=self.wallets.get(pid,{})
  if any(d not in COIN_VALUE or type(n) is not int or n<0 for d,n in coins.items()):raise ValueError('invalid consumption')
  if any(source.get(d,0)<n for d,n in coins.items()):raise ValueError('insufficient coins')
  for d,n in coins.items():source[d]-=n;self.consumed[d]=self.consumed.get(d,0)+n
  return dict(coins)
 def exchange(self,payer,counterparty,give,receive):
  if value_of(give)!=value_of(receive):raise ValueError('unequal exchange value')
  for owner,coins in ((payer,give),(counterparty,receive)):
   if any(d not in COIN_VALUE or type(n) is not int or n<0 for d,n in coins.items()):raise ValueError('invalid exchange')
   if any(self.wallets.get(owner,{}).get(d,0)<n for d,n in coins.items()):raise ValueError('unfunded exchange')
  self.transfer(payer,counterparty,give);self.transfer(counterparty,payer,receive)
 def treasury_exchange(self,institution,counterparty,give,receive):
  """Exact-value denomination exchange with a real wallet counterparty."""
  if value_of(give)!=value_of(receive):raise ValueError('unequal exchange value')
  treasury=self.treasuries.setdefault(institution,{})
  wallet=self.wallets.get(counterparty,{})
  for coins in (give,receive):
   if any(d not in COIN_VALUE or type(n) is not int or n<0 for d,n in coins.items()):raise ValueError('invalid exchange')
  if any(treasury.get(d,0)<n for d,n in give.items()) or any(wallet.get(d,0)<n for d,n in receive.items()):raise ValueError('unfunded exchange')
  destination=self.wallet(counterparty)
  for d,n in give.items():
   if n:treasury[d]-=n;destination[d]=destination.get(d,0)+n
  for d,n in receive.items():
   if n:destination[d]-=n;treasury[d]=treasury.get(d,0)+n
  return dict(give),dict(receive)

def denomination_for_rank(rank):return RANK_DENOMINATION[max(0,min(5,int(rank)))]
def value_of(coins):return sum(COIN_VALUE[d]*int(n) for d,n in coins.items())

def can_pay_tier(world,pid,denomination,count):
 return world.currency.wallets.get(pid,{}).get(denomination,0)>=count

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
