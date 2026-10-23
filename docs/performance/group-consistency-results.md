# Root-bound group consistency results

The reconstructed package joins the complete requested raw group to accepted content, group/owner occurrence and link-query roots, existing owner radix witnesses, allocator and retirement metadata. It remains inactive in World paths.

Temporary workspace cleanup removed three unpublished commits. Restored from published c4cfe473, reconstructed against the recorded contract and earned fresh verification. Query and group checkpoints were published progressively; historical local test claims were not reused.

## Verification

- Parent CI39981711210 accepted for5da5505/runtime c7c8721:3450 tests plus2subtests,356 dedicated proof cases; both ZIP digests, source and XML authenticated. Raw artifacts in ../run-39981711210/.
- Reconstructed query20 and group41 cases first failed with missing modules. Shared projection regressions stayed covered.
- Three Python bool/int typed-identity aliases reproduced RED, then fixed using canonical typed bytes and exact leaf path hashes.
- Independent fresh-context review ran111 focused cases and found one Important embedded retirement-header alias, no Critical/Minor issues. Four additional typed directory/root cases reproduced RED, then passed after validating both headers and comparing encoded bytes.
- Final affected suite:521 passed in53.71s. Full candidate suite remains a separate CI gate.
- Syntax/YAML and scoped whitespace checks passed; raw pytest logs excluded from whitespace checks.

## Measured raw group reads

One instrumented sample per phase. Times in milliseconds, including tracemalloc/SQL trace/VM counters; initial construction and genuine transitions are excluded and separately reported in receipts.

| Unrelated archive records | Current ms | Retained ms | Successor ms | Owner/archive body reads |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 28.91 | 22.72 | 15.38 | 0 |
| 10000 | 24.87 | 23.84 | 18.86 | 0 |
| 100000 | 29.67 | 28.67 | 18.71 | 0 |

At every size, current/retained/successor reads fetched8/8/5 checked catalog metadata bodies, with zero store World-payload decodes. Retained query scopes were measured against genuine newer active/empty populations ofN/N+1, including closed old positions. Nonempty/empty old pages used at most999/799 SQLite VM steps and zero payload bodies. All literal current/retained/successor results matched. Complete source/hash/environment/construction/heap/VM/SQL receipts: group-consistency/scaling/.

SQLite main/temp cache2MiB each, temp_store FILE, no retained clean proof cache. Raw encoded aggregate budget is distinct from general decoded Python object size; the matrix's fixed closure separately enforces peak<2MiB.

Two discarded local repeats under primary runtime SQLite3.53.1 failed in fixture construction (readonly database; invalid seek-table rootpage beyond file page count). Reopened first database was intact/writable; second remained corrupt. Root cause is unresolved. Final complete matrix uses system SQLite3.45.1 matching hosted CI; failed runs are retained as diagnostic logs and are not accepted evidence. No speculative production workaround was added.

## Remaining gates

This establishes raw affected-group consistency, not World admission, target existence/kind, complete topology or namespace/allocator inventory. Unselected physical surplus still requires full audit. Historical ordinary overwritten bodies remain unavailable; only their retained metadata is proved. Accepted generation manifests, retention/reachability, fencing, atomic publication and canonical object admission remain subsequent integration work. No new full World startup/save/year timing or target acceptance is claimed.

Independent review and all scope rulings: group-consistency-review.md and group-consistency-ledger.md.
