# Stage 0.5 closeout artifact manifest

Status: implementation in progress. This manifest is a checkpoint index, not
release acceptance. PR14 remains unmodified and unmerged.

Current code checkpoint:
- Public commit: `0d06148e8f03a993b194ae7e24dc2644000f43d3`.
- Local commit: `23ee53eea937f14476fd38b726bd2849a051f5db`.
- Matching source tree: `f620d0f6c84d97dd453bed1b39a7e598a54b32e9`.

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

Historical metrics are not silently promoted to evidence for the current source.
Current metrics carry source SHA256 for every changed production module.
The progress ledger records final focused gate commands (92 and96 passes,
overlapping scopes), intermediate REDs and fixture corrections. Logs in scratch
are reproducible from those commands; this manifest does not claim their paths
are permanent artifacts.

Still required for final delivery: complete new-format migration documentation,
actual growth-writer/guard inventory, full integrated failure/corruption and
pressure evidence, final-source full-suite results, independent architecture
review, and retrievable restore/backup artifacts. P5's temporary SQLite files
were verified then deleted by its harness, so they are not restore artifacts.
No final-source endurance run or production promotion is authorized here.
