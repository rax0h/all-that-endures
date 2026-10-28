# Integer list-page shrinking implementation plan

> Execute inline with superpowers:executing-plans; one fresh whole-package Astra/high review.

Goal: bounded integer-list truncation including zero, preserving history semantics, aliases and original publication/recovery.
Spec: docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md.
Architecture: authenticate exact removed-page payloads and active empty owner witnesses; approve exact frozen inactive successor headers. Independently compute child-directory deletion root and semantic descriptor/type facts. Classifier admits deletion only for approved page keys, with separate removed-row cardinality delta; all existing gates retained.
Constraints:512 rows/4MiB/128 removed pages; references/nonintegers and unsupported structures retain checked audit; no default activation/main/endurance. Broad suites hosted, local related/native tests and matrix.
Review focus: omitted/extra deleted pages; false empty owner over references; deletion-to-empty namespace-directory behavior; mixed growth and shrink parents; interrupted publication.

Task1:
- [x] Write and run shrink boundary/zero/fault tests forbidding full audit, expecting RED.
- [x] Implement bounded exact deletion classifier and frozen source/header approval; run shrink module GREEN, update previous deletion fallback test to noninteger case.
- [x] Run related/native regression suites and new mixed-parent tests; extend native1k/10k/100k driver to measure page shrink with zero unrelated reads/VM budget.
- [x] One independent whole-package review; one Important/Critical RED→GREEN pass, defer Minors. Record hashes/evidence.
- [ ] Publish dedicated-branch candidate; full/proof/all28 hosted gates pending, no long polling.
