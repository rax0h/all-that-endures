# Existing lease composition: finite repair and continuation

Recovered branch: `sol/durable-proof-map`, original head `0124dd8`.
That head was harness-only after the green `a21954a` runtime. Both jobs in
[41181438097](https://github.com/rax0h/all-that-endures/actions/runs/41181438097)
passed; the full suite logged 4,473 passed, one warning and two subtests in
6,649.94 seconds. This is the predecessor's correctness evidence.

Published runtime source checkpoint: `d9aa539cd01be986f0c23c7ea9fba8cdba5e951d`, whose complete tree matches the locally validated `e810158` checkpoint byte for byte; runtime tree
`15aec0749a88d1c20be9dd8897812390fb70b15a`.

## What changed

The mandatory lease validator now returns a finite set of authenticated existing
lease replacements. Only value/tail/insertion shape classification receives a
tuple excluding those rows. The original frozen rows, lease publication, content
proofs, inventory and recovery remain unchanged. Existing semantic limits stay
512 rows / 4 MiB. The exemption certificate has an independent 4,096-row / 4 MiB
old-plus-new byte budget; exhaustion clears all exemptions. This budget bounds
the exemption, not the already mandatory validation on the fallback path.

Fresh/deleted/reinserted dependencies, nonempty memberships or unsupported old
schema remain semantic input. Canonical new payload/schema/kind and active
publisher ownership are checked before any exemption, including after budget
exhaustion. Oversized semantic preparations retain the original buffer instead
of materializing a tuple merely to fail the existing cap.

## Verification

- Original scalar-save regression with over 512 borrowed backings reproduced the
  full-audit fallback before implementation (`initial-red.log`). The first fix
  passed; its 39.05-second pytest duration includes fixture construction,
  admission and restore and is **not save latency**.
- 168 affected value/tail/insertion/forest/native-session/continuation cases
  passed in 584.16 seconds. This includes two complete generated years and
  fresh-interpreter eager-digest checks. The run began before the final bounded
  allocation guard; it is broader supporting evidence rather than a claim that
  every case ran on the final source.
- Final exact-source 12 cases passed in 90.84 seconds, including scalar, tail and
  fresh-backing saves with more than 512 borrowed backings, actual persisted
  lease tokens, no full save audits, no unrelated predecessor history-body
  reads, exact reopened digest/sharing, budget exhaustion, foreign-token
  rejection and retained fresh/deleted/membership/reinsertion handling.
- Two additional final checkpoint/native sharing-save cases passed in 6.76s.
- All 88 benchmark/retained-transport harness cases passed in 63.54s on the clean
  source checkpoint; the one warning is the deliberate duplicate ZIP fixture.
- Runtime launch pin, every harness fingerprint, both workflow YAML documents,
  their Bash blocks and diff whitespace checks passed.
- One independent review: no runtime/security defects; one Minor test-call
  finding closed. Full disposition and author follow-ups are in `review.md`.

No new mature performance observation is claimed. The publication push starts one hosted full/proof validation on the new runtime.
Its completion is pending; use the existing workflow on this branch.

## Consolidated findings register

| Origin | Finding | Concrete action and evidence | Status |
|---|---|---|---|
| Independent R1, Minor | Three test reads omitted required schema | Pass schema 1; six narrow cases green, all final cases green | Closed |
| Author A1, test defect | Source-read sentinel rejected valid new-page checks | Allow absence and fresh allocated pages; retain unrelated old-body rejection; final fresh case passes | Closed |
| Author A2, bounded-work requirement | Filtering could materialize an oversized streamed input | Filter only when at most 512 semantic rows remain; final exact native/lease checks pass | Closed |
| Handoff boundary | Existing sequence, map/ownership and complete-year coverage | Preserve checked fallback and document the next owned implementation group below; no coverage or speed claim | Explicit boundary |

## Next implementation group

The completed diagnostic in `diagnostic-relaxed-caps.json` deliberately changed
the two classifier caps to 4,096 **in memory only** to find the next unsupported
shape. It is instrumented and is not a production speed measurement. It restored
the eager year-3 digest in a fresh interpreter and left its accepted input
unchanged. Its captured batch has 1,202 version rows: 615 dependencies, of which
18 are fresh. Exempting the 597 existing leases still leaves 605 semantic rows,
before ordinary changes, above the unchanged 512-row limit.

The insertion classifier next rejected new `aux.lazy.sequence.occurrences` at
its unsupported-family branch. Existing sequence incarnations 890 and 898 grow
4 to 5 and 3 to 4 members respectively. Their frozen deltas include the changed
leaf, locator, member and directory rows plus descriptors; these require exact
semantic backing/order, physical sequence-scope and owner-source certification.
Use the existing sequence commitment/extent and central catalog publishers.
Do not omit those rows or raise a cap as a substitute for certification.

Continue whole-year composition with independently bounded certified components,
then existing map growth and ownership changes. Measure the same full real-year
scenario again and retain eager/fresh-process checks before claiming end-to-end
improvement. The prior raw small-world save remains 20.824 seconds, not replaced
by this diagnostic or the component tests. Mature 10s open / 2s save / 1s warm
year and final Stage 0.6 acceptance remain open. No mature benchmark, endurance,
default activation or main merge was launched by this repair.
