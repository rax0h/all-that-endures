# P2B repair review — three remaining R3/R6 blockers

> Review update: the repair at `dcf36a846e2f434a8f766b937d90530787d42a6c` passes the original reproductions below. Remaining identity-index cases and the current assignment are in [PERSISTENCE_P2B_IDENTITY_REVIEW.md](PERSISTENCE_P2B_IDENTITY_REVIEW.md).

Reviewed implementation: `90687da9c4e195b2b778a566007144fb0638539a`.
This supersedes the original six-item repair assignment where fixes are verified.
Do not restart R1–R6 from scratch and do not begin P3.

## Verified progress

The exact three product/test files match both successful isolated candidates:

* [Targeted 36349237502](https://github.com/rax0h/all-that-endures/actions/runs/36349237502),
  `acb3b7a5444821d6f38ffee09eb32ca894d6fa08`: 83 passed in 53.58s.
* [Full 36349333907](https://github.com/rax0h/all-that-endures/actions/runs/36349333907),
  `28fa438203b595826e85af749ca344d75c94f030`: 267 passed in 168.80s.

Independent direct reproductions verify that short-lived wallet insertions now
retain distinct identity and correct values, and a valid edit following a rejected
replacement persists. Exact baseline mismatch rejection and the mature year-5→6
bound/unbound control were also independently checked. The stable ordinal layouts
remove the former set insertion sort and dictionary deletion renumbering.

These are substantial repairs. The remaining failures below are part of the
existing identity and changed-state cost contract, not a new feature request.
Measured output: `persistence_p2b_followup_review.json`.

## F1 / R3 — a new same-owner alias is not recorded

Start with `world.currency.wallets = {1: {'left': {'value': 1}}}`, snapshot and bind.

```python
wallet = world.currency.wallets[1]
wallet['right'] = wallet['left']
session.save()
```

The live left/right references share one object; restored references do not.
After setting `left['value'] = 8` in each world, live `right['value']` is 8 while
restored `right['value']` remains 1.

Cause: `_bind_nested` detects additional owner *sets*, but an additional edge
within the same owner does not change that set. It therefore fails to invalidate
identity metadata. This also applies to same-owner repeated list entries and
nested dataclasses; test new sharing, not just sharing already present at bind.

Repair edge/occurrence tracking independently of owner membership. Removing one
of several same-owner edges must preserve tracking through the remaining edge.
Save/restore must preserve both values and the graph of mutable identity.

## F2 / R3 — cross-session tracked containers are accepted

Bind two distinct Worlds, each with wallet 1 containing `{'inner': {'value': 1}}`.

```python
a.currency.wallets[1]['foreign'] = b.currency.wallets[1]['inner']
```

This should reject before mutation, but succeeds. After saving both, changing
`a.currency.wallets[1]['foreign']['value'] = 8` changes World's B state to 8,
leaves A's dirty set empty, and dirties B's wallet. Both sessions happen to have
the same owner key; owner-key equality cannot substitute for session identity.

Check `_NestedMixin._session` ownership in every preflight, memo and binding path,
just as bound dataclass sessions are checked. Validate before attaching or
propagating ownership. Test cross-session dict/list/set references, both matching
and different owner keys, plus nested incoming values. Rejection must leave both
Worlds, their identities, dirty sets and subsequent tracking intact.

## F3 / R6 — saving a structural edit still walks the full archive

Delete an ordinary **unshared** wallet record, then save. Instrument
`EventLog.__iter__` during save only (after bootstrap/binding):

| Historical events | Events visited by save | Reported changed-member counter |
|---:|---:|---:|
| 100 | 100 | 1 |
| 1,000 | 1,000 | 1 |
| 5,000 | 5,000 | 1 |

`_remove_owner_recursive` sets `_identity_dirty` even for ordinary unshared removal;
`_changes` calls `_current_identity_links`, which recursively visits the entire
World, including EventLog. This moves history-sized cost from mutation to save.
The counter measures successful member operations, not actual work, so it misses
the regression. Genuine alias changes currently trigger the same full scan.

### Bounded architectural direction

Build the full identity occurrence index once at explicit bootstrap. Maintain
reverse references from mutable identity to its owning records/occurrence paths.
After mutation, repair only affected record occurrences and alias groups. An
unshared record deletion should remove that record's ownership information without
opening unrelated records or historical events.

It is acceptable in this tranche to rewalk an affected owning record's nested
tree when needed. It is not acceptable to rewalk World to discover the affected
records. Use the existing owner links/reverse identity index to find dependencies.
Ordered-list shifts legitimately affect shifted entries; ordinary wallet edits
and stable dictionary/set membership changes do not.

Preserve the P2A typed identity manifest or evolve its representation explicitly
if necessary. Canonical path anchors may change when their owning record is
removed; repair only the affected alias group. Do not leave links to deleted
paths, erase identity, or silently turn off identity validation.

Measure real iteration/decoding work independently of the implementation's own
counter. Test unshared deletion, new same-owner sharing, cross-owner sharing and
removal of an alias anchor with increasingly large *unrelated* event archives.
No-op and one-record saves must not walk that unrelated archive. Bind/full scrub
costs remain separate and may visit all state.

## Exact next assignment

Repair F1–F3 above only; preserve the passing R1/R2/R4/R5 and stable-layout work.
Add the specified identity/session/work regressions. Run focused persistence tests,
then one full suite after the fixes are stable, and stop for review. Include a
short independent bound/unbound/restored continuation control. No calibration,
P3, checkpoint replacement, lazy eviction, disk-backed EventLog, Stage 1, millennium
or merge. Do not perform a large history run to diagnose these small reproductions.
