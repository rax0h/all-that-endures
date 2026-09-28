# P2B identity-index review — finish F1 and F3

> Final review and repair results are recorded in [PERSISTENCE_P2B_VALIDATION.md](PERSISTENCE_P2B_VALIDATION.md). This assignment is retained as historical evidence.

Reviewed implementation: `dcf36a846e2f434a8f766b937d90530787d42a6c`.
Disposition: changes required. Preserve this implementation's verified repairs.
This narrows the remaining work from `PERSISTENCE_P2B_FOLLOWUP.md`; do not restart
the original six-item assignment or begin P3.

## Verified progress

* Targeted CI [36351123540](https://github.com/rax0h/all-that-endures/actions/runs/36351123540): **100 passed in 73.66s**.
* Full CI [36351573168](https://github.com/rax0h/all-that-endures/actions/runs/36351573168): **284 passed in 324.08s**.
* All three implementation/test files match both successful isolated candidates
  (`f9c6816e1f26f5338a2d77a7059a2471d269f178` and
  `397c3c523cd2d7d626a48b376d622d0fac141ed2`) byte-for-byte.
* Independent original reproductions now pass: new same-owner child sharing
  survives restore, cross-session containers reject, and one unshared wallet
  deletion visits zero events at archive sizes 100 / 1,000 / 5,000.
* Independent mature seed-843000 bound/unbound/restored continuations agree at
  years 6 and 8. These were short checks, not another full suite or millennium.

The remaining failures concern the new identity-index implementation itself.
They do not invalidate the progress above, but block P2B acceptance.

## I1 / F1 — simultaneous parent and descendant sharing cannot restore

Minimal reproduction, starting with a full snapshot of this World:

```python
world = World(1)
world.currency.wallets = {1: {'left': {'child': {'value': 1}}}}
write_snapshot(world, path, rules_id=RULES)
with bind_snapshot(world, path, rules_id=RULES) as session:
    row = world.currency.wallets[1]
    row['right'] = row['left']
    row['another'] = row['left']['child']
    session.save()  # succeeds
read_snapshot(path, rules_id=RULES)
```

Result: `StoreIntegrityError('identity manifest does not match restored graph')`.
The same graph passed through a fresh full P2A snapshot restores correctly, with
both parent and descendant sharing intact. This is supported acyclic identity,
not a request to support a previously forbidden graph.

`IdentityOccurrenceIndex._scan` expands occurrences below shared parents.
`_links_for` chooses anchors by encoded path ordering. `links()` removes a child
link only when its owner is exactly the parent owner's corresponding child.
Here the independently shared child chooses a different anchor. The emitted
manifest consequently disagrees with `_audit`, which stops traversing a repeated
parent. Flat path groups do not account for identity implied by ancestor sharing.

Repair the relationship between occurrence indexing, link representation,
restoration and verification coherently. Merely skipping the final graph audit,
suppressing child aliases or rejecting this supported graph is not a fix.
Restore must preserve the whole mutable identity graph, regardless of dictionary
insertion order or which encoded path sorts first. Check all payload copies
before relinking; keep corruption detection and legacy P2A reads intact.

Regressions: parent+descendant sharing within and across owners; different key
orders; anchor deletion/replacement; later mutation through each retained alias;
two consecutive save/restore cycles. Include the full-snapshot control above.

## I2 / F3 — alias saves still do quadratic global identity work

Fixture: N independent wallet records, each containing `{'a': shared, 'b': shared}`
with a different `shared = {'value': i}` per record. Snapshot and bind, then add
only `wallets[0]['c'] = wallets[0]['a']` and save.
Count actual calls to `IdentityOccurrenceIndex._suffix` during that edit/save:

| Existing alias groups | Prefix comparisons |
|---:|---:|
| 100 | 5,050 |
| 300 | 45,150 |
| 1,000 | 500,500 |

The event-history scan is fixed. But `links()` still collects all alias groups,
sorts them, and compares each link against every previously retained link.
The occurrence refresh is local; manifest reconstruction is not. Measuring
EventLog iteration alone misses this remaining historical scaling dependency.

Maintain indexed prefix/ancestor relationships and repair only affected identity
groups and their actual dependencies. Do not replace the event scan with an
all-pairs scan of historical aliases. The previous assignment already permits
explicit identity-format evolution if the monolithic manifest prevents bounded
updates; preserve legacy reads and atomically publish identity changes with their
owning records. Do not claim fully changed-state-bounded saves while rewriting
all unrelated identity links. If some whole-manifest serialization remains,
measure and disclose that limitation rather than hiding it behind zero event reads.

Regressions must count real prefix/group work and identity bytes/records written,
not only EventLog visits or the tracker's changed-member counter. Vary unrelated
alias groups as well as unrelated event count. Local alias creation, removal and
anchor replacement should follow affected ownership dependencies.

## Stop boundary

Finish I1/I2 only, preserving F2 and all earlier fixes. Run focused persistence
regressions, then one full suite when stable. Retain an independent short
bound/unbound/restored continuation control. Stop for review.

No simulation semantics, balance, default checkpoint replacement, eviction,
disk-backed EventLog, millennium, Stage 1 or merge. Stage 0.5 remains decision B.
