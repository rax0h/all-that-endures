# Compressed proof-batch range jumps

The sorted updater previously walked every virtual hash position between an
actual node and its compressed prefix, repeatedly scanning16slots while carrying
an already checked node. It now processes the shared compressed range directly
and loops at the original boundary for subsequent deltas. Physical node/hash/
count/path checks and untouched sibling-promotion reads remain. No new cache,
SQL, authority, transaction, format or final-exit validator is introduced.

## Final actual small-save comparison

Base is hosted-green runtime4654b019; source candidate352751a/runtime7347092a.
The same qualified313 runtime and actual immutable year1 input were used for
both versions, with exact pinned Git-file hashes and saved/continued state. The
reviewed bounded trial runner executes A-B then B-A in one command session on
AMD EPYC9V74, with no concurrent tests or reviewer CPU probes during raw runs.

| Phase | Pair1 baseline | Pair1 candidate | Pair2 baseline | Pair2 candidate |
|---|---:|---:|---:|---:|
| Open | 1.328 | 1.123 | 1.201 | 1.275 |
| First step | 5.881 | 5.607 | 5.801 | 5.625 |
| Save | 5.163 | 4.587 | 5.280 | 4.824 |
| Warm step | 4.770 | 4.994 | 4.884 | 5.464 |
| Fresh restore and step | 12.416 | 13.336 | 12.487 | 13.363 |

Save decreases11.2% and8.6% in these observations; warm increases4.7% and11.9%,
and fresh restore+step is also slower in both. These tradeoffs are retained
explicitly. The source change targets update CPU work; these four trials do not
establish overall simulation speed or a latency distribution. Interactive and
mature open10/save2/warm1s targets remain OPEN. No mature constructor was run.

The profile attributes save merge61122→5277calls, includes1005848→41900 and
_nibbles91147→35315. It ran with tests and its elapsed times are not substituted
for raw measurements. Actual save diagnostics are identical, including3062body
reads,11805checked reads,1146payload writes,24929metadata rows and36449pin rows.
No I/O/proof work reduction is claimed. Complete reports, source/import/input
fences, machine context and failure/restart units are in raw-pairs/ and plan.md.

All runs preserve source and input SHA256
2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554.
Saved year2/generation1 digest is
cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451;
independent fresh continued year3 digest is
a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3.

## Verification

Single compressed-leaf update merge work was RED65calls and is now2 (bound≤4),
with exactly one actual read/write. New long-prefix seeded transitions and4095
absent deletions plus existing map/batch/node controls pass56cases0.99s.
Independent whole-package probes pass4096exhaustive state/delta cases,
320seeded transitions across prefix depths0/1/20/57/58/60/62/63,
1209corruption differential cases and6realSQLite rollback faults. Canonical roots,
noop root identity, exact baseline touched-node reads, one read per digest,
unique final-reachable writes and late-failure rollback agree with baseline.
These are separate probe-case counts, not a sum of full-suite test coverage.

No actionable engine finding was identified by the independent review; its
report/source fences and probe output are in review-raw. Final affected result
is appended before publication. Hosted proof/full validation is required for the
new engine; previous green43281031469 covers only the preceding runtime.
No main merge, default activation, endurance or mature request is included.

Final affected suite:391passed105.23s,1deliberate deselection of the unchanged
audited generated-world two-save constructor. The full hosted suite retains it;
actual proof-mode saved/fresh/continued equality was checked by all raw/profile
runs. Suite/probe counts overlap and are not added. Independent review found no
unresolved Critical/Important/Minor finding. Its limits are accepted: mature/
endurance/default/main remain outside this group, hosted correctness remains
pending, and no causal explanation of warm/fresh increases is asserted.

Existing hosted bounds remain proof90minutes/full180minutes+15reserve. Original
mature request files are unchanged, so no mature conversion is triggered.
