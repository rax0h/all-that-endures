# Existing counted-sequence append proof: November 4 continuation

Previous branch `19c903f` is independently verified green in
[41251612123](https://github.com/rax0h/all-that-endures/actions/runs/41251612123):
both jobs successful; full suite 4,482 passed, one warning and two subtests in
6,568.05 seconds. This closes hosted validation of the existing-lease repair.

New published source checkpoint:
`08aee2bc02cfddb185c4690def3c799aa5fedd0f`. Its complete source tree
`537a8b36d9c20d3220a849597b32823dd37eac3a` exactly matches the locally tested
`0eb978f` checkpoint, including code, tests, runtime pin and plan/spec.
Runtime tree: `e6871ff5fcdd2727c12b5af31d02d8cbc4b1365d`.

## Implemented

Existing nonempty scalar sequence appends now use the existing counted-sequence
algorithm to generate an expected frozen delta in a private read-only replay.
Every predecessor presence/absence joins the accepted content root; metadata
preflight rejects overlap/oversized sources before body transfer. Exact raw
delta equality certifies main-tree, locator, membership AVL, radix directory,
type witness and descriptor changes. Changed backing/order facts, physical
child and sequence locator roots, content counts and leaf-owner source witnesses
compose in the original transaction. The replay is never registered in World
identity or added to publication participants.

Limits remain 512 semantic rows / 4 MiB. The replay additionally bounds the whole
request to 16 backings, 128 appended values, 512 distinct predecessor reads and
4 MiB old-plus-new encoded source bytes. Existing possible integer/lineage-pair
policies remain satisfied; empty and reference-bearing/nonappend/over-budget
shapes retain the checked fallback. No original source row is omitted.

## Evidence

- Actual native append first reproduced the full World audit (`initial-red.log`).
- Final **21 cases passed in 176.29s**: 3/128/4,096-value sequences, leaf and root
  splits, duplicates and membership order, multi-call append/extend, shared
  identities, mixed new owners/list tails, source/type/owner/descriptor corruption,
  before-head/before-commit/lost-ack recovery, explicit unsupported fallback,
  bounded frontier reads beside 10,000 unrelated history values and fresh
  interpreter digest/sharing restoration.
- **190 affected tests passed in 492.48s**, including complete generated years
  and fresh-process continuation. This batch began before the two final review
  fixes; final-source coverage comes from the 21 cases and controls below.
- **88 clean-source harness cases passed in 46.67s**, including actual workflow
  launchers. One deliberate duplicate-ZIP fixture warning.
- One independent review found one Medium bounded-read issue and one Minor
  malformed-input issue; both reproduced RED and closed in the final test run.
  Full consolidated register is `review.md`; no deferred findings.

## Complete small-world year: measured, target still open

The existing canonical real-year driver completed both raw and diagnostic passes
on this exact source. Seed 843000, 8x6, one settlement, eager years 1–2 followed
by a complete proof-backed year 3. Both fresh interpreter restores matched the
independent eager digest; accepted input hash remained unchanged. Command exit 0.
Construction/eager control 35.217s and copying are outside operational phases.

| Raw operation | Seconds |
|---|---:|
| Open plus full proof admission | 9.710 |
| Complete simulation year | 1.916 |
| Save | 26.409 |
| Fresh interpreter restore plus digest verification | 10.857 |

This is a small generated world, not the retained year-1001 fixture. Local CPU
load/cache and Python/SQLite differ from earlier observations; do not interpret
26.409 versus the earlier 20.824s as a controlled code regression or improvement.
Fresh restore includes digest verification, not isolated opening. Diagnostic
save 65.033s is instrumented and does not replace raw timing; its two World audit
spans are inclusive parts of that diagnostic save.

The diagnostic still records 1,202 version rows, 17 caller ordinary rows plus
the manifest control, 67 identity changes, no event segments and two full World
audits. 615 dependency rows include 18 fresh dependencies: excluding 597 accepted
existing leases would still leave 605 semantic rows. Thus current classification
retains the original batch and returns at the existing value/insertion row gates
before sequence certification. This is an observed integration boundary, not a
claim that the full simulated year uses the new append proof.

## Exact next group

Implement bounded whole-year composition of separately certified components:
source values, canonical catalog changes, leases, sequence/list frontiers and
fresh graph owners. Current total-row rejection must become bounded composition,
not an arbitrary larger cap. Certify existing map-entry growth and ownership
changes within that scheme, then rerun the same complete-year driver and require
eager/fresh-process equality. Component-only passes do not establish annual
performance. Preserve unsupported fallback until its replacement is certified.

One bundled full/proof CI is started by publication of this runtime package;
hosted completion on the new runtime remains pending at publication. Mature
10s open / 2s save / 1s warm year, default integration and final Stage 0.6
acceptance remain open. No mature benchmark, main merge, default activation or
endurance run was launched.

## Hosted regression and correction

The first published candidate's proof-map job failed in run 41878768574:
the final descriptor-key guard rejected valid fresh sequence incarnations
before checked fallback. This is a code defect, separate from the earlier
runner queue delay. The original failure and a new mixed existing-append/new
sequence case both reproduced locally before correction. Corrected source
checkpoint `8e58a5f0465dbb67bbd916f7e8a5d49e994757d6` passed 84 combined
native tests and 29 clean-source launcher tests. Details, raw RED/GREEN logs,
exact source mapping and remaining hosted gate are in `ci-repair/closure.md`.
Corrected hosted run 41891188691 is verified successful in both jobs on
`bc96009`: 4,504 full-suite passes plus two subtests and one deliberate warning.
This closes the sequence work group's hosted gate; whole-year composition and
mature target acceptance remain open.
