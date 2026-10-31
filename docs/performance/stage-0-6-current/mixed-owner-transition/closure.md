# Stage0.6: mixed native value/tail and fresh-owner proofs

Green parent d80ceb80c6add545e1da0a87cf3cc26c8aff38e0 passed both jobs of
41077846816:4430 simulation tests plus2 subtests in6965.50s, with hosted proof
and insertion scaling. Both downloaded artifact ZIP digests and exact source
receipts were checked; the preceding package retains these in
`../scalar-owner-insertion/hosted-41077846816/`.

## Result and contract

The former value/tail and fresh-owner paths worked separately. Combining an
already supported existing edit and a new scalar owner unnecessarily selected
the full World audit. This group composes the same validators and one existing
catalog/publisher. It admits a fresh scalar owner alongside existing lazy or
ordinary value edits, query changes, fixed-shape shared backed records and
supported integer-list tails, including child-page growth/removal.

The insertion helper authenticates all source predecessors and partitions fresh
owners from the remaining transition. The existing value/tail proof checks that
complete remainder and its updated source witnesses. Canonical catalog
regeneration includes every concrete lazy and ordinary owner source. Its
metadata reader authenticates and charges even unchanged owner-tree nodes.
Structural sequence branch metadata is excluded from concrete owner sources.
Successor construction composes prepared tail facts and child root with exact
new owner/group semantic facts, checks actual scope roots, allocator and
content-count delta, and preserves the existing content, query, collection,
inventory, head and event checks. No alternate publisher or identity graph was
introduced. Unsupported topology retains the full checked fallback.

Budgets are per validator. The insertion helper limits the supplied transition
to512 rows and4MiB of frozen payload/key bytes plus its checked predecessor and
catalog dependencies. Reused value and tail validators retain their independent
limits. This is not one aggregate4MiB cap across duplicate/helper reads in the
entire composed call. Work stays explicitly bounded; no history-wide scan is
authorized by composition. Initial full admission and verification are separate.

## Measured mixed workload

Measured implementation ffe67b5, runtime tree
398fa5f0edf14e77ab48cff4871a626f8651ec8c; Python3.12.14, SQLite3.53.1.
The scenario inserts a Person, changes an existing skill value, appends to its
shared integer history, edits an ordinary Settlement value and advances year
and the Person counter. Raw timing includes those operations and save. Each
archive starts from the same fixture constructor on a separate database; the
baseline is the previous green d80ceb8. These are local observations with other
tests active, not controlled repeated hardware/cache measurements.

| Retained history values | Previous green save | Current save | Current SQLite VM steps | Unrelated history-body reads | Full World audits during save |
|---|---:|---:|---:|---:|---:|
| 1,000 | 0.473816s | 0.180920s | 417,296 | 0 | 0 |
| 10,000 | 0.945335s | 0.193044s | 417,836 | 0 | 0 |
| 100,000 | 5.236638s | 0.227141s | 421,173 | 0 | 0 |

Baseline invoked2 full World audits per save. At100k the observed saving is
about23x; current VM work rises0.93% across100x more retained values. SQL body
attribution permits only the exact changed tail page, not unrelated pages or
entries. Construction/admission, traced first save, raw second save and
third-save VM work are separate phases. Fresh full audited reopening checks all
three inserted people, skill value, history suffix/length and shared identity,
ordinary value and year. Exact source/driver hashes and phase receipts are in
`candidate/`, `baseline/` and `comparison.json`; `baseline-probe.py` reproduces
the baseline scenario. The existing hosted driver adds `--scenario mixed` and
the proof workflow retains it separately from scalar-only scaling.

These archives contain history values, not simulated years. This is not a
complete real-year workload or mature-world performance acceptance.

## Consolidated finding closure

One independent whole-package review, including the author fix in this group;
the original final report and source fingerprints are in `review.md`.

| ID | Origin / severity | Action | Evidence / status |
|---|---|---|---|
| MX-A1 | Author / Important: shared value validator accepted identical scalar-owner rewrites without a new catalog source witness; ordinary Event-ID rewrites had the same revision issue | Require exact source witnesses for authenticated unchanged registered owner bodies, preserving their accepted projection; keep sequence branches as structural metadata | Missing/present witness regressions for lazy partnership and ordinary Event-ID:4passed4.67s, rejection/recovery or bounded commit followed by audited reopening. Independently verified4passed4.45s; closed |
| MX-C1 | Reviewer / contract clarification: inherited helper budgets are independent | Document exact per-validator bounds; do not advertise one4MiB aggregate across repeated reads | Contract above, plan and original review agree; closed |

Independent checks also combined distinct backing growth and shrinkage with a
birth, existing lazy and ordinary edits, with full World audit forbidden, then
audited restored contents and aliases. A self-checksummed forgery in unchanged
catalog owner-tree membership bytes was rejected by accepted content proof;
rollback, original-generation recovery and normal retry passed. The reviewer
ran16 initial cases and9 final mixed/source-witness cases in11.93s. No open
actionable Critical, Important or Minor finding remains in this finite group.

## Remaining Stage0.6 gate

The observed1202-version/18-ordinary-row complete generated-world year from the
preceding package still exceeds this bounded slice and introduces new backing
graphs and ownership changes. It retains full-audit fallback. Raising the row
limit alone does not authenticate that transition. Next work must extend the
existing touched-source and scope proof machinery to those new backing and
ownership/retirement changes while preserving exact real-year continuation.
Initial mature admission and simulation selection cost remain separate blockers.

Mature targets remain open10s, warm year1s and incremental save2s; first year
and fresh restore lack separate numeric targets. No mature target is claimed
passed here. No new mature benchmark, millennium generation, endurance, default
activation or main merge was launched. This runtime group, including the shared
source-witness correctness repair, warrants one bundled full/proof CI after
final local validation. Long CI will not be busy-polled.

## Final local validation

186 affected tests passed in332.40s, including the complete generated-world
years3/4 with independent eager control and fresh-process restored digest
equality.88 benchmark/retained-fixture harness tests passed34.80s. The final
reviewed runtime and driver were remeasured after the witness repair; earlier
pre-repair partial gates and scaling are not substituted for these receipts.
All reviewed source fingerprints, workflow YAML, Bash blocks, runtime pin,
launch fingerprints and whitespace checks pass. See targeted/harness logs and
XML plus verification.json.
