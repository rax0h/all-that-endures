# Stage 0.5 closeout artifact manifest

Status: implementation in progress. This manifest is a checkpoint index, not
release acceptance. PR14 remains unmodified and unmerged.

Current code checkpoint:
- Public commit: `2b0c4672c15648c45f2c9cac4d86ad82bb5d7b39`.
- Local commit: `58eca6fe588e40b13cf6ecac65b7ba82c56a34e1`.
- Matching source tree: `20ee6634422e64177fca119a70e4624440d88986`.

| Artifact | Scope and authority |
| --- | --- |
| `STAGE_0_5_FINAL_ARCHITECTURE.md` | Controlling architecture |
| `STAGE_0_5_SOL_61_EXECUTION.md` | Complete implementation directive |
| `STAGE_0_5_FINAL_PROGRESS.md` | Exact source checkpoints, commands, results, limitations and next action |
| `STAGE_0_5_FINAL_SCHEMA_INVENTORY.md` | Exhaustive static schema classification; actual writer/guard refinement and implementation closure remain |
| `stage_0_5_final_identity_foundation_metrics.json` | Historical checked-catalog foundation measurements; use recorded source hashes |
| `stage_0_5_final_sequence_metrics.json` | Historical counted-sequence primitive measurements; not integrated World acceptance |
| `stage_0_5_final_retired_identity_metrics.json` | Historical checked retirement-directory measurements |
| `stage_0_5_final_maintenance_metrics.json` | Historical indexed, bounded maintenance measurements |
| `stage_0_5_final_history_budget_metrics.json` | Historical shared history-cache measurements |
| `stage_0_5_final_participants_metrics.json` | Historical immutable World save-participant measurements |
| `stage_0_5_final_record_budget_metrics.json` | Current concrete runtime/shared record-byte measurement; H1k/H10k, eight candidates, one edit, two placements |
| `stage_0_5_runtime_cache_p5.json` | Current compatibility P5 with independent eager control; exact digest/events, reopen/relocation/detach; source hashes embedded |
| `measure_stage_0_5_record_budget.py` | Current reproducible measurement harness |
| `tests/test_stage_0_5_final_runtime_families.py` | Cold record/child aliases and immutable concrete bindings |
| `tests/test_stage_0_5_final_record_budget.py` | Byte accounting, sidecars, retained aliases, dirty owner rehydration, step/query budgets, precommit/lost-ack recovery |
| `tests/test_stage_0_5_final_pressure_arithmetic.py` | Forced exact float.hex/RNG arithmetic regressions; duplicates, extinct occurrences, shared/replaced list and reopen; checked scalar/cache integration still pending |
| `stage_0_5_final_owner_retirement_gate.txt`, `stage_0_5_final_owner_retirement_fault_gate.txt` and `tests/test_stage_0_5_final_owner_retirement.py` | Checked metadata-only retirement; 59-pass affected gate and39-pass non-death fault gate, overlapping; subprocess-death completion outstanding |
| `stage_0_5_final_sequence_numeric_gate.txt` and `tests/test_stage_0_5_final_sequence_numeric_index.py` | 16-pass numeric-alias checked occurrence gate; no history scan, corruption, duplicates and old pins |
| `stage_0_5_final_sequence_error_gate.txt` and `tests/test_stage_0_5_final_sequence_errors.py` | Durable 58-pass primitive gate; iterator failures, self-extension, corruption rollback and reentrant freeze regressions |
| `ate_sim/persistence_lazy_identity_headers.py` and `tests/test_stage_0_5_final_identity_headers.py` | Compact checked lease/header encoding and coordinator peer comparison; zero history traversal at H1k/H10k, mismatch-before-install; ordinary World activation still pending |

Historical metrics are not silently promoted to evidence for the current source.
Runtime metrics retain their recorded compact-header checkpoint hashes. The
subsequent sequence repair has its own source checkpoint and affected gate;
those runtime metrics are not current integrated sequence acceptance.
The progress ledger records the 55-pass compact-header affected gate, preceding
194-pass runtime gate and historical92/96 gates with overlapping scopes,
intermediate REDs and repairs. Logs in scratch
are reproducible from those commands; this manifest does not claim their paths
are permanent artifacts.

Still required for final delivery: complete new-format migration documentation,
actual growth-writer/guard inventory, full integrated failure/corruption and
pressure evidence, final-source full-suite results, independent architecture
review, and retrievable restore/backup artifacts. P5's temporary SQLite files
were verified then deleted by its harness, so they are not restore artifacts.
No final-source endurance run or production promotion is authorized here.
