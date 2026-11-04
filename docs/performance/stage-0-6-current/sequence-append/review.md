# Independent sequence-append package review

Base: `19c903fb7ce4c2c2077214f05f9ba2bc707b74ec`.
One fresh Astra/high context reviewed AGENTS.md, spec/plan, all changed runtime,
new tests, predecessor authority, catalog/source witnesses, scope composition
and native commit/recovery. Read-only, no implementation delegation, no full
suite or duplicate large fixture run. No unsafe certificate acceptance found.

## Findings and closure

| ID / origin | Severity | Finding | Action and verification | Status |
|---|---|---|---|---|
| R1 / independent | Medium | Two overlapping predecessor rows could both transfer bodies before rejection, exceeding aggregate source-byte allowance | Reject overlap from the metadata size probe; real-store regression reproduced body fetch RED, now rejects before any body read | Closed |
| R2 / independent | Minor | Unvalidated key/leaf entries leaked Python indexing/unpacking/comparison errors | Reuse canonical scope-key validation and validate bounded leaf/occurrence shapes before extraction; two real frozen-save corruptions reproduced TypeError RED, now produce StoreError and recover/retry correctly | Closed |
| A1 / author | Implementation defect | Replay tried opening a nested transaction | Private read context inherits the manifest's owned transaction; all predecessor bytes still join accepted content; native append regression passes | Closed |
| A2 / author | Implementation defect | Scope update lacked the existing seek workspace | Initialize existing OrderedSeekMap workspace after complete replay validation; split/root/mixed cases pass | Closed |

All 21 final sequence cases passed in 176.29s after both independent findings
were fixed. The earlier 18-case candidate passed before those fixes; its raw log
is preserved separately. Broader 190-case affected run began before review fixes
and is supporting evidence, not an exact-final-source full-suite claim.
Clean-source harness and complete real-year eager/fresh-process controls also
passed on the final source. No second independent review is implied.

Replay remains a private expected-delta generator. Original publication rows
and commit ownership stay with the existing transaction. Exhaustion and
unsupported empty/reference-bearing/nonappend shapes retain full audit.
Full-year batch composition and mature latency remain separate open gates.
