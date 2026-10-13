# Settlement Memory Root Closure Implementation Plan

> For agentic workers: use superpowers:executing-plans inline under the already approved complete Stage 0.5 directive.

Goal: close unrestricted imported Settlement.memory in the existing checked graph-copy/runtime lane without changing generated-world behavior.
Architecture: reuse HistoryReference map storage, the sole recursive registry, physical catalog, dependency pool and hybrid publication. Genuine legacy remains explicit compatibility. No new format claim is made by this task alone.
Spec: simulation/STAGE_0_5_SOL_61_EXECUTION.md and simulation/STAGE_0_5_FINAL_ARCHITECTURE.md.

Global constraints: source-preserving private copy, no hidden migration, no truncation, one transaction, exact values/order/sharing, rank issue17 deferred, PR14 unchanged, no endurance.

Review focus: shared memory map in another family; replacement preflight preserving original owner; raw NaN keys in imports; before/after commit recovery; scalar edit must not flatten unrelated imported memory.

- [x] RED: explicit normalized copy gives one checked map for memory and wallet alias; reopen and detach preserve sharing.
- [x] Normalize the concrete eager Settlement.memory field through the existing copy builder and field-assignment hook, gated by checked authority.
- [x] RED/GREEN: direct replacement rejects invalid/foreign values before detaching old memory; edit sharing and save faults preserve exact authority.
- [x] Measure H1k/H10k scalar edits and no-op saves with zero memory-entry traversal.
- [x] Run settlement, recursive-copy, root and recovery affected gates; update inventory/evidence; commit coherent checkpoint.
