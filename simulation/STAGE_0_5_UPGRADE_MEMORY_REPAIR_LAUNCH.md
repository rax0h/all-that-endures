# Repaired complete-upgrade validation launch

Executing candidate:98a37c64514084879ef77c04825e47e1f6a4fabe.
Candidate tree:6de3392f6e70ccc0dde0f7ca28ac39f91d411785.
Source checkpoint product:2bc3c85389760ff12578857f7d2a849bc5cf9201.
Workflow SHA is independently recorded as GITHUB_SHA in every stage.
Implementation branch:sol/stage-0-5-complete-closeout.
Validation branch:sol/stage-0-5-final-release-validation.

## Readiness evidence

- Task1 source checks:70 passed22.08s, source values/aliases/bytes preserved.
- Task2 catalog staging:88 passed24.94s, reference rows/order and staging corruption checks.
- Task3 preparation/recovery:127 passed20.41s, including opted-in writer grouping and cleanup.
- Task4 copy/format/NaN/frozen/promotion/fault gates:152 passed49.39s.
- Final indexed-inventory/preparation/catalog gate:97 passed22.90s.
- Real harness:5 passed127.16s, including old source/new executing candidate checkpoint resume and exact1/2 continuation. CLI rejects source product override without explicit resume.
- Synthetic2000people/Events whole upgrade: baseline184160KiB peak RSS ->Task469020KiB, publication39.22s ->61.19s; exact restored World digest. VmSize separately reported in implementation progress; no fixed-memory or speed improvement claim.
- Independent Astra review of local97ec8ef (byte-identical tree to published98a37c6): no Critical or Important findings;44 passed,1 deselected2.93s; all five jobs/shell blocks parsed. Address-space subprocess deliberately excluded from this independent selection, covered in implementer gates.

## Independent review findings and rulings

Minor deferred: scale receipt announces128/512/2048 measurements but retains only2048. The first two were observed locally; their missing durable receipt rows do not block gated validation.

Rulings:
- Opted-in writer namespace grouping also uses disk because resident lists would defeat the preparation budget. Ordinary behavior remains unchanged. If wrong: conversion ordering/counts, covered by equivalence checks.
- Normalization keeps its resident objects and existing id(source) contract; only completed normalized outputs replay. If too large: the8GiB guard must identify the next allocation; no alias shortcut or universal bound is accepted.
- Actual year1000 headroom/disk/runtime, new-candidate full-suite/recovery and1001/1002/restore acceptance await their gates. If wrong: gate failure and a measured scoped repair; no acceptance claim from a partial checkpoint.
- Reviewer did not independently fetch the published tree or remote archive. Publisher checked local/remote tree SHA equality; connected GitHub verified artifact metadata. The large job verifies original ZIP, receipt and database bytes before conversion. If wrong: preflight rejection without source publication.
- Universal fixed-memory behavior for arbitrary imports is outside the claim. Resident normalization/maps and oversized rows remain disclosed costs. If an input exceeds those costs: allocation failure requiring measured repair.

## Five gated jobs

1. Fresh focused regressions and complete3+4+3 recovery on the exact candidate.
2. One full simulation/tests suite on the exact candidate with JUnit/stdout/stderr.
3. After1/2 pass, verify the retained lazy ZIP/receipt/database and upgrade only year1000 under8GiB Python RLIMIT_AS; retain phase/RSS/VmSize/disk evidence and a new complete checkpoint.
4. Resume that complete checkpoint, independently compare exact1001/1002, save/audit/reopen/backup/restore. Reuse old canonical1000 digest only as source-world evidence.
5. On a fresh runner download the final restore, verify original hash, open a disposable copy and check year/generation/format6/digest/counters and unchanged original.

Retained artifact11870590333 from run38508408370; origin workflow124c3215468a60862b7848086f00a8e768a6ed66. ZIP1339563957 bytes; SHA256409cf0230ff1606b7eddd587a69c22076c11447eb6497e642e584c4fd3b74ef9; expires2026-10-28. No bootstrap or canonical millennium rerun, RAM/swap increase, watchdog dump, main/PR14 merge, default checkpoint replacement, rank change or Stage1 work.

Status at publication: gated validation queued. Final Stage0.5 acceptance remains pending the exact candidate jobs; successful diagnostic/checkpoint stages alone are not final acceptance.
