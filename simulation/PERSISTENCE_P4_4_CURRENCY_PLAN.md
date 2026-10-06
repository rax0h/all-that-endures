# P4.4 — currency wallet / treasury lazy migration plan

**Date:** 2026-10-05  
**Authority:** `STAGE_0_5_SOL_EXECUTION_HANDOFF.md` and P4 residual inventory.  
**Starting product head:** `ebe67ab4488f5fe0a1de36c5b159bd683bee7ddf`.

## Scope

Migrate only:

- `world.currency.wallets`
- `world.currency.treasuries`

Keep `minted` and `consumed` eager: both are denomination-keyed and bounded
by the fixed currency vocabulary rather than population/history.

No advancement, metaphysics, relationships, genealogy, institutions,
`event_ids`, checkpoint-default replacement, Stage 1, endurance run or merge
belongs to this slice.

## Required behavior

1. Wallet/treasury outer mappings remain canonical dictionaries with exact
   insertion/delete/reinsert order.
2. Each value remains a mutable `dict[str,int]`; all existing direct mapping
   operations remain legal.
3. Shared wallet dictionaries are real identity. If two owner keys point at the
   same dictionary, lazy load must return the same live object and mutation must
   dirty every current owner occurrence of that incarnation.
4. A retained wallet alias may outlive every outer-table cache entry. Mutating it
   must rehydrate/dirty each owning key required for a correct save.
5. Point reads load only the requested bucket. Ordinary open loads zero wallet or
   treasury payloads.
6. `wallet()`, `credit()`, `balance_value()`, `transfer()`,
   `treasury_transfer()`, `consume()`, `exchange()` and
   `can_pay_tier()` preserve exact behavior and ordering.
7. Save/recovery uses the existing single-generation atomic P4 publication.
   No-op save writes zero currency-bucket payloads.
8. P2C identity links and versioned occurrence labels remain sharing authority.
   One live mutable dict exists per incarnation even when it has multiple owner
   keys or cross-boundary eager aliases.
9. Explicit materializing detach returns ordinary dictionaries and preserves
   shared wallet identity. Close does not materialize currency history.
10. Conversion remains checked, source-preserving and no-overwrite.

## Representation

Use one versioned lazy namespace for wallets and one for treasuries. Bucket
payloads are plain denomination/count dictionaries. A multi-owner tracked-dict
wrapper records a set of owning table/key bindings instead of assuming one
owner. Its mutation preflight validates every attached lazy owner before changing
the dict; successful mutation dirties all attached owner keys.

Do not introduce a universal proxy layer.

## Focused gate

Prove:

- zero wallet/treasury payload loads at open;
- one point load on demand;
- shared wallet aliases across two keys are one object before and after reopen;
- retained shared alias after both owners are evicted mutates and saves correctly;
- direct dict set/delete/update/pop/clear/setdefault operations are tracked;
- real credit/transfer/exchange/consume/treasury operations match eager controls;
- outer insert/delete/reinsert preserves order and identity;
- save failure/lost acknowledgement preserves old-or-new atomicity;
- no-op save writes zero bucket payloads;
- materializing detach preserves shared aliases and checkpoint roundtrip digest;
- 1,000 -> 10,000 historical wallets with fixed active access adds zero ordinary
  open bucket loads and point/current work stays bounded by requested owners.

Run focused currency + affected P4 tests first. Run the full simulation suite only
after the product bytes for the tranche stabilize. No millennium/endurance run.
