# Independent whole-package review: owned read-view epoch

Reviewed local base `1b6e770297aa018ea5ac8e6a9057b591c3a52462` against the frozen
working-tree candidate. The four engine files and new regression module are
bound by `reviewed-source.sha256`; all five hashes were rechecked after the
independent probes. The later test-only append adds four fallback-selection
cases and is bound by `final-reviewed-source.sha256`; all four engine hashes
remain identical. The append was inspected and its4passes/4.60s verified from
`../owner-fallbacks.log/xml`. No production file, index, HEAD or branch was changed by
this reviewer. This is the single independent whole-package review for this
group, including the existing setter repair.

## Strengths and plan alignment

- `persistence_validation_scope.py:41–86` captures actual admitted proof-only
  authority after original snapshot admission. Reuse is tied to exact store,
  guarded DB, codec, pin, manifest, accepted epoch, component identities, hook,
  owned read-view depth and monotonic mutation/transaction/callback history.
  A failed fence permanently invalidates the scope and clears transient facts.
- `persistence_sqlite_guard.py:100–108,136–138,235–246` distinguishes normal
  transaction control from descriptor SQL revision. Public setters, methods,
  scripts and conservative unknown SQL all invalidate an existing captured
  view. The retained autocommit RED and focused GREEN address the earlier
  release/reopen defect. Context-manager exits cannot restore an admitted
  legacy view without a tracked reopen; autocommit=False starts in a borrowed
  transaction and cannot initially mint this capability.
- `persistence_proof_world_session.py:27–33` changes only how an already
  admitted epoch is obtained. Public entry and established-view checks still
  perform the original validation. Source, metadata, count, commitment and
  physical proof implementations are unchanged.
- `persistence_lazy_identity_catalog.py:796–810` adds only eligible standalone
  proof-only owner admission. Its zero transient-cache budget cannot retain
  owner/node facts; existing shared descriptor/owner limits remain enforced.
  The original spool lifetime, transfer of returned ownership and error
  cleanup are retained. No extra authorizer, transaction or exit validator
  has been introduced.
- Inspected all existing checked-read callsites, original snapshot start/end,
  descriptor fact fences, native source entry and spill implementation.
  Borrowed, opening, audited, callback, uncertain and publisher paths preserve
  their prior full-check behavior.

## Independent verification

Used unchanged qualified Python3.13.5/GCC14.2.0/SQLite3.46.1 executable
`/workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python`, with
`PYTHONPATH=simulation:.`. No CPU probes ran until the coordinator explicitly
cleared raw timing.

`test_independent_read_view.py` has 13 distinct cases. The first batch retained
10 passing cases and two diagnostic failures in `independent.log/xml` (13.47s).
The two corrected cases passed in `corrected-probes.log/xml` (2.37s). One final
physical proof negative passed in `physical-proof.log/xml` (1.22s). Thus all13
have passing evidence on the same frozen engine; unchanged passing cases were
not rerun.

Coverage:

1. Isolation-level setter, successful/exceptional DB context-manager exit and
   cursor script release/reopen permanently clear warmed scope facts despite
   equal coarse SQLite epochs.
2. Pending DML RETURNING invalidates during execution before `total_changes`
   advances; a pre-admission pending RETURNING under autocommit cannot reuse a
   previously warmed descriptor.
3. Exception exit clears scope state; a public owner iterator never acquires
   the private scope and closes its snapshot on early close.
4. A 1-byte/1-entry catalog forces real owner spills. Both successful transfer
   and injected freeze failure leave scope state cleared; all nonreturned or
   explicitly closed spill files are removed, with zero transient LRU entries.
5. Removed trace callback history and an overridden codec prevent descriptor
   fact hits and preserve fallback rejection/checking.
6. Isolation-level release followed by an external writer and reopen rejects
   corruption and cannot restore the previous scope.
7. After warming descriptor facts, deleting a distinct owner's physical
   occurrences still fails the source proof even after test-only manual
   reacceptance of the coarse authority epoch.

The implementation's focused-v2 evidence independently inspected here records
42passes/20.38s (13 new regression controls plus29 existing descriptor controls).
These are separate from the independent probes, and not a claim of a full suite.
The coordinator affected log subsequently reports328passed/1deselected in327.84s.
The unchanged audited generated-two-save constructor is reserved for hosted
full validation. Four owner-selection tests appended after collection have their
separate passing receipt. The final one-line workflow addition explicitly runs
the read-view module in the existing proof job; its hash is included in the
final fence. No workflow triggers or mature requests change.

## Findings and disposition

Critical: none remaining. Important: none remaining. No production Minor found.

Minor diagnostic repair: the reviewer initially assumed executescript would not
perform its own legacy pre-script COMMIT and assumed this fixture owner had one
placement. Actual behavior is a pre-script COMMIT and three placements (root,
teachers, provenance). Preserved `initial-probes.py` and the original two
failures; changed the script to `BEGIN; SELECT 1;` and the exact expected count
to3. Both corrected cases pass. This is a review-test repair, not an engine fix.

Minor documentation precision: raw timing excluded tests/reviewer CPU probes,
but permitted static reviewer file reads. The package report and W7f now say
this explicitly. W7b names codec identity precisely. Both wording corrections
were read back and are CLOSED within this group.

## Measurement boundaries

Read the actual candidate, reverse-baseline and same-command reports. Historical
`baseline-raw` predates the interruption and is not the adjacent comparison.
The counterbalanced pairs give these observed first/warm results:

| Pair order | Baseline first/warm (s) | Candidate first/warm (s) |
|---|---:|---:|
| Candidate then reverse baseline | 11.448 / 9.091 | 8.287 / 7.309 |
| Same-command baseline then candidate | 12.055 / 9.224 | 8.381 / 7.271 |

Same-command save worsens7.722→8.152s; reverse save improves7.912→7.307s.
There is no consistent save improvement claim. Source/runtime preservation is
true in both final pair reports, the input database SHA256 matches, and fresh
saved state (`cebc2fcd...cc7451`) and warm continuation (`a46d627d...1686f3`)
match exactly between candidate and baseline. These are bounded small-input
observations. They do not close interactive/mature targets.

## Declined to judge

- Arbitrary Python mutation of private authority/counters, direct base-class
  sqlite3 API bypass or native-memory modification: outside the established
  normal guarded-API capability contract; this is not a Python sandbox.
- Mature-scale timing, endurance, default activation and main merge: explicitly
  outside the authorized group. Small-input timing cannot establish them.
- Hosted CI completion: a separate coordinator gate; not produced or inferred
  by this local review.

## Assessment

The frozen candidate is suitable for the planned bundled validation and
publication, with no remaining actionable finding. The consolidated W7a–f
closure register was read back: setter repair, diagnostic repair, documentation
precision, measured tradeoffs and review boundaries are all closed locally.
The executor explicitly accepted every declined-to-judge boundary above.
Independent whole-package review is complete. Hosted proof/full acceptance
remains a separate gate; this is not permission for main merge or a claim that
interactive/mature targets are met.
