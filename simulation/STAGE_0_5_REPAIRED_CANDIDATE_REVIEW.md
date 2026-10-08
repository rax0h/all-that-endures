# Stage 0.5 repaired candidate: independent architect review

2026-10-08. **Decision: BLOCKED. No promotion or merge acceptance.**

This report supersedes earlier closure claims for the reviewed candidate. It
does not undo accepted P1/P2/P3 semantics or authorize a new broad migration.
Only the repair delta and concrete dependencies were inspected. No full suite,
millennium, or endurance simulation was launched by this review.

## Provenance and completed evidence

| Boundary | Verified value |
| --- | --- |
| Production PR #14 before this documentation | `4e3dd8269055129fb03c34385a2fe0bda2ce658c` |
| Production tree | `47b9f1f6751bb11ae72a799474818c6efb8c9141` |
| Frozen repair | `e8e216dd234f47dd2be9a96af1e8048798fa1ba0` |
| Frozen branch | `sim/stage-0-5-r3-final-frozen` |
| Reviewed tree | `be89be21b9289fef7dfafbdb783b47a61f05faa9` |
| Full-suite helper | `ff5e05ffb5203b51c44cbd3f8d82190ca3359942` |
| Helper delta | Only `.github/workflows/stage-0-5-final-full-suite.yml`; simulation sources and tests identical |
| Full-suite run | [37780238248](https://github.com/rax0h/all-that-endures/actions/runs/37780238248): **in_progress at the single check**; no conclusion asserted, no repeat polling |
| PR state | Draft, unmerged; frozen implementation not promoted |

The local production Python modules used for independent probes were compared
with every `simulation/ate_sim/*.py` Git blob in the frozen tree: no differences
(allowing a terminal newline added by retrieval).

Completed job logs were fetched, not inferred from handoff prose:

- [37779635125](https://github.com/rax0h/all-that-endures/actions/runs/37779635125),
  job `113319176285`, frozen SHA: 3 selected compatibility/closeout tests passed
  in 5.92s; 18 household/sharing/recovery tests passed in 82.97s.
- [37779635029](https://github.com/rax0h/all-that-endures/actions/runs/37779635029),
  job `113319175952`, frozen SHA: 3 selected tests passed in 2.43s and 18 passed
  in 55.54s. Job `113319175674`: 78 affected tests passed in 43.99s and the
  independent seed-843000 P5 3+4+3 continuation reported `passed: true`.
- The earlier 886/887 result remains an earlier, non-green suite; it is not
  substituted for the running final suite. A future green final result will
  not override the independently reproduced defects below.

## Disposition of the previous requests

| Request | Disposition | Reason |
| --- | --- | --- |
| R1 clean eviction and identity lifetime | **CONDITIONAL** | The original clean baseline/weak-occurrence leak is repaired. Independent 900-person traversal, retained-person mutation, save and reopen pass. But ordinary open still eagerly retains all current identity links across cold owners; see B4. Full archive-independent identity-memory acceptance is withheld. |
| R2 public lifecycle guards | **ACCEPTED within this boundary** | The public marker now uses the real operation guard, closed-store preflight and finally-based release; close rejects active operations/scopes/steps. Independent callbacks attempting pager mutation, nested digest, save and close reject, scope preflight rejects, and later digest succeeds. R3 ownership defects are not evidence that this wiring repair failed. |
| R3 household sequence integration | **BLOCKED** | Default checked paged conversion/open and simple bounded append work in completed gates. Sharing transitions, shrink membership, compatibility and ordinary gameplay bounds still fail. |

The accompanying `review_stage_0_5_r3_reproductions.py` is a standalone review
probe, deliberately outside test discovery. Run against the frozen product:

```sh
PYTHONPATH=simulation:. python simulation/review_stage_0_5_r3_reproductions.py
```

Observed: **6 cases in 1.231s: 2 pass, 2 assertion failures, 2 errors**.
Failures assert the required behavior. Do not turn them into expected failures
to claim completion. The probe can be copied onto the frozen repair branch;
this documentation commit itself does not promote that branch's product code.

## B1 — HIGH: successful save loses a surviving foreign owner's list

Reproduction: share `households[1].members` with
`currency.wallets[99]['members']` at conversion. Load the wallet alias, delete
household 1, append through the surviving wallet alias, save, close, reopen.
Save succeeds. The wallet subsequently raises:

`StoreIntegrityError: lazy currency nested persisted identity is not weak-referenceable`.

A smaller diagnostic with initial `[1, 2]` and append `3` found runtime wallet
`[1, 2, 3]` but checked persisted wallet payload `{'members': []}` after success.
This is a loss of durable value, not merely a missing convenience API.

Code path, frozen lines: `LazyHouseholdMembers.retire_related_owner` (212)
recognizes only household owners, and detaches when that set empties;
`_household_page_changes` (persistence_lazy.py:9652) deletes their storage.
`LazyCurrencyTable._plain` (7417) unconditionally compacts any pager to `[]`,
including a pager whose final household placement was retired. The synthetic
foreign identity anchor established during open does not implement all later
ownership transitions. `_bind_loaded_currency_bucket` (11631 onward) then
cannot restore the surviving value/label as a valid tracked mutable object.

Smallest correct repair: account for all current canonical owners before
retiring the sequence authority. Keep checked sequence storage for a surviving
incarnation, or atomically transition the foreign owner to a complete supported
representation and matching identity labels. Never store a placeholder with
no remaining checked logical authority. Preserve foreign dirty routing and
retained references. Test deleting/replacing the last household, deleting the
foreign owner first, both ownership directions, further mutation, failure,
lost acknowledgement, resolve, reopen and detach.

## B2 — HIGH: save splits an intentionally shared live list

Reproduction with two initially distinct households:

```python
right.members = left.members
assert right.members is left.members
session.save()
assert right.members is left.members  # FAILS
```

`_household_page_changes` treats every changed household field as a new list:
it copies to a tuple and `_make_paged_household_sequence` installs a new proxy
with `object.__setattr__`. It does not recognize that the assigned object is
already the current sequence of another household. A successful save changes
the live identity graph, so subsequent edits diverge even when value digests
immediately before/after save match.

Repair ownership reconciliation by actual live object/incarnation, not merely
household ID or equal values. Add placement to the existing sequence where
appropriate and publish necessary destination pages/labels/current links
atomically. Preserve source aliases and replacement-object identity. Save
preparation must not silently copy/split caller aliases on either successful
or failed attempts. Test runtime merge, split, new shared list, same-object
move/reinsert, equal-but-distinct replacement and multi-save reopen cycles.

## B3 — HIGH: shortening by replacement leaves observable stale membership

Reproduction: persisted members `list(range(1, 261))`; assign `[1]`; save/reopen.
`list(members) == [1]`, but **`259 in members` is True**. `store.verify_all()`
also succeeds. This is a logical completeness defect despite checked rows.

In `LazyHouseholdMembers.__init__`, replacement sets `_length = 0` while keeping
`_base_length`. `_replace_all` (371) counts old pages from `_length`, so only
the new first page is dirtied. `pending_changes` (409) visits those dirty pages
and never deletes obsolete baseline pages 1 and 2 or their memberships.
`__contains__` (278) then accepts an old indexed candidate beyond logical length.

Repair replacement retirement against the persisted baseline extent, not just
the current overlay length. Preserve old pinned generations; delete expired
current pages and memberships in the same generation as length/owner/identity.
Do not merely hide the stale query result. Test 0/1/127/128/129/260 boundaries,
shrink then append, repeated replacement, shared owners and fault resolution.
Verification must catch a logically orphaned current page/index when explicitly
scrubbing this sequence; normal open must remain lazy.

## B4 — HIGH: bounded ordinary session claims remain false

These are actual canonical structures restored by the fallback
`_restore_collection` path (`persistence_lazy.py:16164`), not hypothetical
future features. The fixture that enlarged migrated families did not enlarge
these independent residual fields.

### Event IDs and identity metadata

With a fully sealed disk prefix and **zero mutable tail events**:

| Disk events | Eager `_RootSet` event IDs | Shallow set bytes | Open payload bytes |
| --- | --- | --- | --- |
| 2,048 | 2,048 | 131,304 | 180,188 |
| 4,096 | 4,096 | 262,376 | 348,124 |

`World.emit` appends to `event_ids`; the lazy open restores the entire set.
The accepted EventLog prefix reader is not the source of this leak. Keep it.
Use the already specified exact compact/range representation for normal
consecutive IDs, with an exact checked fallback for supported edited/imported
sets. Never infer a contiguous set when the actual value contains holes/extras.

Separately, `_read_current_identity_links` (persistence_adapters.py:730) reads
all link records and `LazyWorldSession` (9363) retains `tuple(links)`:

| Cold wallet alias groups | Resident wallets after open | Eager current links | Open payload bytes |
| --- | --- | --- | --- |
| 100 | 0 | 100 | 30,998 |
| 1,000 | 0 | 1,000 | 161,101 |

This is not the repaired weak-registry leak and not accumulation of obsolete
P2C deltas. It is eager memory proportional to current sharing in cold history.
Keep P2C current links as authority; use checked indexed per-owner/group reads
and bounded runtime discovery instead of materializing all cold link paths.

### Residual canonical inventory

Fixed/capped classifications below describe existing normal simulation paths;
they are not blanket caps on arbitrary imported or directly edited Worlds.

| State | Actual classification / code evidence |
| --- | --- |
| Cells; local/ambient scalar state; trade routes; warfare tensions; currency minted/consumed; scalar counters | Fixed world geography/pairs, six currency denominations, or fixed-size logical scalar state under current simulation. Python integer magnitude can grow; this is not record-history retention. |
| `agency.actions` | Eager, explicitly trimmed to 50,000 records by agency.py:52 during ordinary stepping. An arbitrary imported oversized list is not automatically bounded by this fact. |
| `world.households`, `Settlement.households` | **History-growing.** households.py partnership/split creates household records, settlement IDs and dwellings. Old households remain, and paged open creates one wrapper per historical household. Outer row count was incorrectly described as fixed. |
| `Household.members` | Per-sequence clean pages are bounded (128 IDs/page, four-page cache), but B1–B3 and gameplay scan below remain. New/replaced lists and explicit whole-list edits have proportional cost. |
| `economy.property`, nested provenance/ownership | **History-growing.** household creation creates dwellings; economy.transfer appends provenance/ownership. Eager restore has no historical bound. |
| `knowledge.beliefs` | **History-growing.** civilization.trade_step stores person/claim beliefs for successive generations without historical removal. Trade-route claims/index are bounded by fixed route pairs on this normal path; general claim/teach APIs have no universal bound. |
| `culture.practices` and adoption | **History-growing/unproven bound.** cultural_step creates retained variants; adoption deletion/weight saturation is not a bound on retained practice history. Culture institutions/laws have normal-path limits of four/three per settlement; institution practice sets are initialized from at most four strong practices. |
| `institutions.institutions` / branches | Outer normal-path institutions/branches relate to fixed kinds/settlements, but nested **members, records, notices** retain history: institutions.py:37, 51, 100. Trainees represent active enrollment; that does not bound the other fields. |
| Divinity gods/GABs/churches | Outer seeded pantheon and one church per god/settlement are fixed. **God relationships/manifestations and church followers** retain history (divinity.py:85–103 explicitly says membership is historical). GAB interventions/relationships grow through the supported grant API. |
| `warfare.conflicts`, accountability inquiries | **History-growing** retained closed records. Limiting simultaneously active wars/inquiries is not a limit on archived rows. |
| `threat_ecology.threats` and resolutions | **History-growing** generated/resolved threats and origin-event mappings; no corresponding historical deletion found. |
| `metaphysics.resurrection_tokens` | Eager and uncapped under the supported grant/consume API. Do not assert an ordinary automatic grant rate not demonstrated by code. |
| `communities.communities` | Eager founder/diaspora records. Deduplication is per `(parent, destination)`, not a demonstrated global bound on possible ancestry. Treat as an unproven bound requiring targeted reachability evidence, not a quantified ordinary-growth result. |
| `infrastructure.assets` and provenance | Current development creates one road per route and seeded irrigation; normal maintain calls omit event IDs. API create/maintain-with-event can grow rows/provenance. State this compatibility cost without inventing a normal annual provenance append. |
| EventLog | Accepted disk prefix plus pending/live suffix; no redesign requested. Explicit export, digest, scrub, conversion and materializing detach remain proportional whole-history operations. |
| Migrated lazy families | Preserve accepted adapters. The clean cache repair does not prove every variable-size loaded child is bounded; distinguish genuine active/dirty/external working state from eager cold history. No independent replay of every family was attempted. |

One combined residual fixture kept eight active people, one settlement,
institution, branch, god and church, while increasing historical records:

| History | Eager households / pager wrappers | Settlement household IDs | Branch notice IDs | Institution member IDs | God relationships | Church followers | Open bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 100 / 100 | 100 | 100 | 100 | 100 | 100 | 101,573 |
| 1,000 | 1,000 / 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 851,294 |

Both opened with zero lazy Person payload loads. Branch notice-set shallow
size alone grew 4,328 -> 33,000 bytes. These are measured reachable fields,
not a claimed total heap measurement or allocation to one specific family.

### Ordinary household gameplay still traverses cold history

`civilization._household_living` comprehends the entire historical member
sequence and loads each Person before filtering alive. It is called by normal
migration. `households.household_split_step` has the analogous pattern.

| Historical members, eight alive | Returned living people | Person payload loads | Payload reads / bytes |
| --- | --- | --- | --- |
| 100 | 8 | 100 | 101 / 63,487 |
| 1,000 | 8 | 1,000 | 1,008 / 636,866 |

This is ordinary gameplay, not an explicit archive operation. A simulation-step
hot cache can consequently classify accessed dead history as a hot working set.
Use checked current-person/household selection while preserving the existing
member order and duplicates. Do not replace list order with global Person order
or drop supported duplicate semantics to get a faster result.

## B5 — MEDIUM: incomplete compatibility surface

- Paged conversion explicitly permits foreign household-list aliases only for
  nested wallet/treasury paths (`persistence_lazy.py:1029–1064`). A valid cold
  World sharing members with `genealogy.children[1]` is rejected. P3B open
  preserves this identity. A diagnostic legacy non-paged P4 open also failed
  weak-reference binding for this shape, so this is an uncovered P4 compatibility
  gap, **not proof that R3 newly broke a previously working P4 path**.
- On a pager containing `[1, 2]`, `pager + [3]` and `pager * 2` raise TypeError;
  `pager == (1, 2)` returns True whereas a native list returns False.
  The stated exact-list contract and repair plan include concatenation.

Implement the promised list-value operations and preserve supported P2C list
aliases through the common ownership bridge. No fail-open placeholder, silent
copy, implicit whole-history fallback during ordinary access, or newly invented
restriction is an acceptable compatibility repair. Test both operand directions,
in-place operators, native equality behavior, and cold/legacy/detach boundaries.

## Endurance artifact: not recovered

Run [37679777350](https://github.com/rax0h/all-that-endures/actions/runs/37679777350)
still exposes zero artifacts. No GitHub releases exist. Searches of accessible
Drive by `p5-long-restore`, `stage-0-5-final-endurance`, and hash prefix found no
matches. Library exact-title and broader restore/endurance title searches found
no candidate; the current workspace has no matching SQLite copy. Repository-wide
Actions artifact enumeration was unavailable through the connector, so this is
not an assertion that every possible independent storage location was searched.

No retrievable copy of the reported 5,124,976,640-byte file with SHA-256
`b775264dce1a202fdddfba4fa696455192906866bd9912673c9d26abcc797d63`
has been verified. The old run's deterministic/control evidence remains valid
for its old source, not for untested future repair bytes.

Storage-conscious recovery proposal, **not launch authorization**:

1. If the owner supplies another storage location, retrieve and hash that exact
   backup; validate restore and short continuation independently. Do not use a
   10-year dry-run file as the missing year-1000 fixture.
2. Otherwise, after corrected architecture/short gates, request one replacement
   capture on a frozen implementation. Reuse the independent-control harness;
   retain the final complete SQLite backup, not all intermediate large Worlds.
3. Prepare the durable target before compute. Check available quota and disk
   space against live working stores + backup + compressed output + independent
   restore space. Do not assume the old 5.125-GB size or a compression ratio is
   an upper bound. Use streaming compression and, if needed, bounded shards;
   avoid changing SQLite contents merely to preserve the old raw checksum.
4. Store the raw-backup SHA-256, per-shard hashes, raw/compressed sizes, seed,
   year, generation, rules/schema, implementation/tree/workflow SHAs and restore
   digest in a small manifest. Record a durable retrieval URL and explicit
   retention/expiry policy covering release review. Verify a fresh download and
   independent restore before considering retention complete. A replacement
   fixture is new provenance, not a recreation of the unavailable old bytes.

## Narrow Sol handoff and exact release gates

Start from frozen `e8e216d` on an isolated descendant; verify live branches and
preserve concurrent work. Do not overwrite PR #14 with the current candidate.

1. Convert the B1–B3 review probes into permanent failing regressions, then repair
   only the household sequence ownership/publication and replacement extent
   logic. One coherent ownership reconciliation must cover foreign surviving
   owners and dynamic merges; do not add another open-only special case.
2. Close B5's concrete list protocol and alias cases through the same adapter
   boundary. Preserve P2C authority, incarnation semantics, checked generations,
   exact events, RNG behavior and source-preserving legacy conversion.
3. Run those regressions plus affected household/currency/genealogy/identity,
   lifecycle and failure matrices. Include before-commit failure, stale writer,
   lost acknowledgement, idempotent resolve, backup and detach after each new
   ownership transition. Then run P5 short independent continuation once on
   stable repaired bytes. Record exact source and commands.
4. **Do not begin an omnibus residual-family migration.** Publish the corrected
   B4 inventory and bounded follow-up specifications first. Separate (a) exact
   event-ID authority, (b) cold current-link lookup, (c) household records,
   settlement IDs and ordered living-member access, and (d) the remaining
   demonstrated eager historical collections. Reuse accepted storage primitives.
   For each specify actual read/write consumers, identity/transaction boundaries,
   normal-path vs explicit-operation costs, and fixed-active 1k/10k gates.
   A fixture that grows only already-lazy families cannot close any of these.
   This review authorizes B1–B3/B5 corrections and B4 specification, not broad
   implementation of new family migrations.
5. Record the final suite's eventual conclusion when the owner resumes; do not
   poll. Do not rerun it just to restate the old evidence. Later product repairs
   require their own affected evidence and a deliberately selected integrated
   gate, with scope justified by shared-code impact.
6. Keep the durable late-fixture gap explicit and prepare retention before any
   newly authorized long capture. Consolidate stale review/status documents and
   PR summary when the candidate and evidence are coherent.

Remaining release blockers are **B1–B5**, unresolved final-suite evidence,
absence of a verified durable late-world fixture, and eventual verified promotion
of an accepted frozen implementation. The missing artifact is not the sole
reason for withholding architectural acceptance. No merge, Stage 1, balance,
magic progression, unrelated checkpoint default change or new endurance run
is authorized. No production repairs were made by this review.
