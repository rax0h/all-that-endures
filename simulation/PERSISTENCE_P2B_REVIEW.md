# P2B review — changes required before P3

Reviewed head: `c61a9e4aed40b75f210e4eb1bd557c3594f1f37f`.
The true PR #14 head was verified before review. This disposition does not approve
P2B for integration, default checkpoint replacement, Stage 0.5 freeze or merge.

## Evidence checked

The reported successful CI is genuine:

* [Targeted run 36330406323](https://github.com/rax0h/all-that-endures/actions/runs/36330406323):
  62 passed in 28.23 seconds, plus the continuation regression passed in five
  fresh processes.
* [Full run 36330406318](https://github.com/rax0h/all-that-endures/actions/runs/36330406318):
  246 passed in 199.64 seconds.
* The implementation and test files at isolated candidate
  `45bba2a4ded1030351e9914322b708d455294348` were compared directly with the
  reviewed product head and are byte-for-byte identical.

Independent direct Python reproductions below expose gaps those tests do not
cover. Raw measured results are in `persistence_p2b_review.json`. No redundant
full suite or millennium was run for this review. No simulation balance change
is requested.

## R1 — recycled object IDs create false sharing and change the live world

`_bind_nested` records `_memo[id(original_container)] = replacement` without
retaining/checking the original object. Once the original container is freed,
Python can reuse its address for an unrelated new container. The memo branch
then returns the old replacement. For tracked containers that branch also adds
owners without the rejection check used by other branches.

Reproduction inside a session bound to a snapshotted `World(4)`:

```python
for i in range(20):
    world.currency.wallets[i] = {'iron': i}
```

Observed: all twenty values became `{'iron': 0}`, and all twenty wallets were
one mutable object after detach. Restore preserved the wrong zeros but produced
independent objects because the identity manifest still contained no links.
This changes live canonical reality before saving; it is not a cosmetic cache.

Repair identity lookup so an address alone is never persistent proof of identity.
Retain/check the referenced source or use a sound identity/ownership handle with
an explicit lifetime. Apply new-sharing checks consistently in every lookup path.
Test many short-lived insertions and assert both distinct values and distinct
identity before save, after detach and after restore. Include dictionaries,
lists and nested values; do not depend on a lucky allocator layout.

Also require a real **bound versus unbound** control. Existing tests compare a
bound world with its own restored copy, which can agree after both inherit the
same corruption. On seed 843000, mature year 5 → 6, this review measured:

* bound and restored: `f8584c46558ba3b615dea881f915dc76fa0d36f40358ab4b57a93c1f45eb9498`
* unbound legacy-checkpoint control: `7bd8dc5cc0832cf5f817553c985e966114236a0a1de5853ef54b23c93b1dc0b7`
* both had 1,467 events.

Investigate every remaining difference after fixing identity lookup; the digest
comparison is a regression requirement, not proof that this is the only cause.

## R2 — rejected mutations can disable tracking of retained live data

Root/nested replacements detach the old value before validating/binding the new
one. A rejected replacement therefore changes tracking even when canonical data
was not replaced. Similar ordering exists in slice operations and scalar record
assignment; operations must not leave partially changed ownership on failure.

Reproduction: initial wallets `{1: {'iron': 3}, 2: {'iron': 5}}`:

```python
try:
    world.currency.wallets[2] = world.currency.wallets[1]
except StoreError:
    pass
world.currency.wallets[2]['iron'] = 9
session.save()
```

Observed: the replacement raises as intended, but `dirty` stays empty after the
valid edit. Live balance is 9, restored balance is 5.

Validate before changing authority, or roll back data and all tracking changes
on failure. Cover rejected root/nested replacements, failed extended slices and
new nested dataclass children. After a failure, a valid edit to every retained
old alias must still save correctly. Recursive detach must respect remaining
references rather than leaving orphan owners or removing live ones.

## R3 — ownership propagation stops before shared descendants

An already-seen parent receives additional owners, but its mutable descendants
do not. Example: two wallet roots refer to the same
`{'inner': {'value': 1}}`. After binding:

```python
world.currency.wallets[1]['inner']['value'] = 2
session.save()
```

Only wallet 1 is dirty. Restore fails with
`StoreIntegrityError: aliased payload copies disagree`.

Propagate ownership through the shared reachable mutable graph, with correct
multiplicity/lifetime when an edge is removed. Test shared dataclasses and deeply
nested containers, same-owner repeated references and changes to supported
sharing. Keep the identity manifest synchronized with legal structural changes.
Unsupported changes must fail before changing data or tracking. Current simulation
operations that create sharing must remain supported; do not prohibit them just
to make a storage test pass.

## R4 — binding accepts a different baseline and silently loses prior edits

`_validate_bound_identity` compares identity links; root binding checks sizes.
Neither establishes that values, keys, ordering, counters and position match the
snapshot to which the session claims to bind.

Reproduction: snapshot a wallet containing 3, change the live value to 99, then
bind and call `save()` without further mutation. Binding succeeds; the save
returns generation 1 with no dirty records. Live remains 99, restored remains 3.

Establish the initial baseline exactly. A full comparison is allowed at this
explicit bootstrap boundary, or bind from an exact restored generation with a
clear authority contract. Do not put a full history comparison into ordinary
saves. Capture the head/baseline through one pinned read generation. Mismatched
binding must fail without leaving wrappers/hooks attached to the caller's World.
Add same-sized value/key/order mismatch and failed-bind cleanup coverage.

## R5 — normal simulation operations are rejected by bound roots

Binding a normal founder World and then running `Simulation(world).run(1)` raises
`StoreError: bound root collections cannot be replaced in P2B`, because Simulation
normally converts its initial event list to EventLog. Other existing conversions
include dictionary → RecordTable. Independently, `agency_step` assigns a retained
slice back to `world.agency.actions` when it exceeds 50,000 entries; the blanket
root-assignment ban rejects this legal simulation operation.

Support these existing transitions at explicit persistence boundaries without
changing their simulation behavior. Bootstrap normalization may be appropriate
if exact equivalence is proved. Do not remove the agency retention operation or
change its threshold. Construct a short fixture near the retained-action boundary
rather than simulating thousands of years to reach it. Test founder/mature starts,
root normalization, action-tail replacement and a cold-event sealing transition
against an independent unbound control.

## R6 — every new event scans and sorts the complete historical ID set

`_RootSet._mutate` calls `_ordered()` before and after every mutation;
`_ordered()` sorts using codec encoding. World.emit adds to `event_ids` for every
event. This puts O(total historical events) work into each new event. The existing
payload read/write counters do not account for this in-memory scan.

Measured codec calls for **one** `world.event_ids.add(new_id)`:

| Existing event IDs | Codec calls | Local seconds |
|---:|---:|---:|
| 100 | 201 | 0.00176 |
| 1,000 | 2,001 | 0.00721 |
| 5,000 | 10,001 | 0.02435 |

Fix set membership tracking so insertion/deletion does not sort/re-encode all
unrelated historical members. A narrowly versioned adapter representation for
unordered set membership is permitted if needed; preserve logical set contents,
typed keys and old-snapshot compatibility or explicit version rejection. Ordered
lists/dictionaries must retain their order. Do not silently loosen P2A's ordinal
validation while still labelling the layout the same version.

Inspect ordinal maintenance similarly: deleting one dictionary row currently
renumbers every later row. Avoid carrying a second history-sized mutation path
forward merely because payload counters only test wallet value replacement.
Measure actual changed-member work at different archive sizes, including emitted
events, not only save-call payload counts. No millennium is necessary to expose
or verify this complexity.

## Bounded repair assignment and stop point

Repair **R1–R6 only**, preserving P1 transactions/checksums and P2A exact recovery.
The important existing hooks may be revised where ownership cannot be made sound
locally; this is not authorization for P3, gameplay systems or unrelated refactors.
Keep the existing disposal of query caches, but prove it does not erase authority
or disturb future evolution.

1. Add regressions for every reproduction above and the independent bound/unbound
   control. Keep snapshots/restores/continued worlds and canonical indexes exact.
2. Add short operation-sequence tests for insert/edit/delete/reject/retry, shared
   descendants and structural transitions. Check live truth as well as save output.
3. Run focused persistence tests first. Once fixed, run the full existing suite
   once. Repeat fresh-process continuation only as needed for the demonstrated
   allocator/lifetime defect; do not use repeats instead of the value/identity tests.
4. Report exact code SHA, tested blob equality if using an isolated branch, results,
   changed-member scaling counters, and remaining explicitly unsupported operations.
5. Stop for review. **No P3, default checkpoint replacement, lazy eviction,
   disk-backed EventLog, balance changes, Stage 1, millennium or merge.**

Stage 0.5 remains decision B. The prior unbound canonical millennium remains
historical evidence; it does not validate a newly bound incremental session.
