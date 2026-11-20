# Isolated reconstruction diagnostic

The [budget investigation](mature-proof-audit-budget.md) identified two
complete repeat passes whose durations are hidden in the previous mature
trace. The diagnostic measures scope roots and collection directory
construction on the retained generation-zero, format-6 after-digest
databases. The [explicit request](reconstruction-probe-request.json) is
`retained-after-digest-root-pairs-2026-11-20-2`.

## Measurement

- Authentication uses the existing green engine gate, pinned after-digest
  and inherited catalog admission, exact archive/member hashes, and the
  full hosted software fingerprint. The mature jobs also reauthenticate
  small recovery run 44028694698.
- A fresh disposable copy enters `ProofGenesisTransaction`. This freezes
  the source with the same ownership and checked SQL used during genesis.
  Scope runs the existing seven-root constructor. Collection uses the
  existing per-namespace constructor, descriptor writer and ordered
  directory build. Scope root order is owner, group, query, query owner,
  child, sequence and rank.
- The first pass fills the relevant derived proof tables. The repeat pass
  checks previously derived bytes in the same owned snapshot. The report
  retains each pass's root digests and counts, wall/CPU time and resource
  counters. Both passes must agree. The repeat follows immediately, sharing
  cache and transaction state with only its lane's derived nodes present.
  The production calls are separated by other bootstrap and World work.
  Use these timings for attribution. Integrated timings and conservative
  whole-stage bounds still require separate evidence.
- The worker rolls back and verifies restoration of the complete main
  schema and release of transaction custody. It then checks the pristine
  parent's hash again. Diagnostics contain JSON only.
  They are outside checkpoint discovery and carry no publication authority.
  The isolated constructor timings exclude unrelated bootstrap work,
  complete World validation, the source-map scan and final physical audit.

## Launch and restart bounds

The dedicated workflow starts only on a change to its request file on
`sol/durable-proof-map`. The current operational resume request and
qualified engine remain intact. The short hosted gate deliberately stops
the scope trial after the first pass, verifies rollback and the parent
hash, restores the same archive in a fresh process and compares all its
roots. It checks the known small corpus counts in both lanes and downloads
the actual uploaded small evidence by immutable artifact ID. The gate
checks the uploader's ZIP SHA-256 before extraction, then compares the
downloaded files recursively with the originals. Both mature jobs depend
on that gate.

The [first hosted run](https://github.com/rax0h/all-that-endures/actions/runs/44696353813)
passed reconstruction, deliberate interruption and fresh restart. Upload
finalized artifact **14610723098**. Its immediate artifact list returned
zero results, so the file comparison and both mature jobs were skipped.
The [retained 40,201-byte ZIP](reconstruction-small-44696353813.zip) was
subsequently fetched by exact ID. Its SHA-256 is
`33d4d328c34748804948cf107b244b129752a3f867611f17862b5b4aff3ce886`.
All 51 members were retained. The two successful trials matched their first
and repeated roots, the interrupted trial matched the fresh scope run, and
all three receipts verified the same parent hash. The retry updates only
the workflow transport and request. The short gate still runs end to end.
The production proof engine, reconstruction probe and retained databases
are reused.

The [retry](https://github.com/rax0h/all-that-endures/actions/runs/44781897995)
passed the complete small gate. Job **136446481217** verified rollback,
fresh reconstruction, uploaded artifact **14652248017**, checked the
downloaded ZIP digest, and passed the recursive byte comparison.
Both mature jobs completed successfully.

## Verified mature results

| Component | First construction | Repeated construction | Repeat CPU | Root counts |
|---|---:|---:|---:|---|
| Scope | 1,195.76 s | 1,186.47 s | 1,186.24 s | 1,181,812 / 2,210,495 / 242,238 / 1,534,414 / 639,840 / 8,457 / 70 |
| Collection | 606.63 s | 762.54 s | 762.50 s | 70 |

Scope ran on AMD EPYC 9V74 and collection on Intel Xeon 6975P-C.
The two archives contain 18 unique JSON receipts each. Their admission
stamps match, and both pin the exact retained after-digest and rebase
inputs and qualified engine. Both used the same verified software
fingerprint as the small retry. All seven phases in each lane completed
within their recorded budgets, both root pairs match exactly, and both
lanes reverified the retained parent checksum after teardown.

| Raw evidence | Artifact | ZIP bytes | ZIP SHA-256 |
|---|---:|---:|---|
| [Scope](reconstruction-mature-scope-44781897995.zip) | 14655663996 | 15,918 | `f4193888043dacd941b9b79c17ada1c08c5e482404a897248585bc35cf386fa8` |
| [Collection](reconstruction-mature-collection-44781897995.zip) | 14654762607 | 14,939 | `6c7707d7cf3ee821f6befa7be511c09fb38f98f12ef295d87575b51bd6cfdc4e` |

Using the unrounded receipt values, the repeats total **1,949.00 seconds**
across the two isolated jobs.
That is **884.13 seconds** more than the **1,064.87-second historical
margin** after charging the prior pre-World and catalog intervals. The
sum compares isolated durations from different runners against a
historical budget. The full integrated production proof duration remains
unmeasured. Keep the production rerun on hold and use this evidence to
investigate avoiding repeated construction within owned source custody
while preserving exact checked roots and corruption detection.
[Historical budget and remaining audit phases](mature-proof-audit-budget.md)

| Mature budget per job | Limit |
|---|---:|
| Green/software and admission checks | 5 min |
| Archive restore and verification | 30 min |
| Private copy and verification | 7 min |
| Owned schema setup and source guards | 20 min |
| First pass | 45 min |
| Repeated pass | 45 min |
| Final parent verification | 5 min |
| Combined process cap, including cleanup | 165 min |
| Evidence upload | 5 min |
| Job cap, including runner setup | 185 min |

Each lane checks real archive/member and copy/journal disk headroom before
use. The independent jobs use separate runners so one failure leaves the
other lane's reports intact. The smallest restart unit is one lane on a
fresh disposable copy. A timeout can retain first-pass JSON and censored
phase data. Open/format/pin work and cleanup share the aggregate process
cap. If the outer watchdog terminates Python, the runner discards the
private copy and the surviving evidence may stop at a phase-start record.
The original checkpoints remain the reusable inputs.

Launch uses mature after-digest **14267625292**, data **14261110486** and
their inherited catalog refs. Small uses **14252280082** and **14252085073**.
The proof-map qualification is the first current dependency to expire,
**Dec 1 at 02:18:52 UTC**. Recheck compatibility and expiry on each restore.
Reuse green full/proof suites and all five completed precursor stages.

Local functional checks used the bundled unqualified Windows interpreter.
Three focused tests passed. Running the production constructors on the
authenticated small bytes also passed both root comparisons, the forced
scope rollback, the scope restart and all parent hash checks. The seven
scope root counts were 650/1369/243/775/420/8/2 and the collection directory
count was 69. All eight digests and counts matched the authenticated
closed small proof database from artifact **14304023790**. Timing acceptance
requires qualified hosted output.
