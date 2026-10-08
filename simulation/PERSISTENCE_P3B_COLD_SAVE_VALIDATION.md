# P3B cold-save validation evidence

**Status:** architect-accepted at `2fe72cb7b84a487b3c5adc0c8475be614e616816`.
See `PERSISTENCE_P3B_COLD_SAVE_REVIEW.md` for independent CI/blob verification,
five passing review probes and acceptance boundaries. Next assignment:
`PERSISTENCE_P3B_LIFECYCLE.md`.  
**Scope:** `simulation/PERSISTENCE_P3B_COLD_SAVE.md` plus bounded corrections R1/R2/R2.1 in `PERSISTENCE_P3B_COLD_SAVE_REVIEW.md`.  
**PR documentation head before landing:** `eaafbfe234603b6d678df9d40e11076e6f075049`.  
**Final validated correction candidate:** `a93907ecfe7bc49176c04b0d5b1d19597cc6c413`.

## Correction validation

### R2.1 targeted gate

GitHub Actions run: 37245584222  
Candidate: `a2faa25777f615382b4e5f6e56dd4571c3cbdd75`

- **11 passed in 4.66s**
- Covers pending identity deletion before apply, mixed insert/update/delete identity cleanup, repeated `resolve_save()`, subsequent real save and reopen, and preservation of earlier R1/R2 regressions.

### Focused cold-save correction gate

GitHub Actions run: 37245662547  
Candidate: `63fff49780137aa42eebf8362f759cfce7dd3429`

- **54 passed in 143.67s (0:02:23)**

Persisted-key work for a fixed local wallet edit:

| Unrelated alias groups | prep key iterations | prep membership probes | save key iterations | save membership probes |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 0 | 3 | 0 | 3 |
| 300 | 0 | 3 | 0 | 3 |
| 1,000 | 0 | 3 | 0 | 3 |

This directly closes R1's whole-population key-copy failure. Work is bounded by changed keys rather than unrelated persisted population.

Allocation measurements use `tracemalloc` started/reset after fixture creation and cold open. They therefore measure save preparation/publication work rather than total World construction memory.

| Old sealed segments | selected encoded bytes | prep peak bytes | prep retained bytes | released-plan retained bytes | publication peak bytes | publication retained bytes | reader cache segments/events |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 2,560,922 | 20,703,021 | 10,550,535 | 1,436 | 13,587,148 | 326,253 | 0 / 0 |
| 40 | 2,564,539 | 20,710,254 | 10,555,962 | 1,436 | 13,587,148 | 326,253 | 0 / 0 |
| 400 | 2,580,929 | 20,747,300 | 10,580,661 | 1,390 | 13,595,314 | 326,069 | 0 / 0 |

The selected transfer remains four chunks. Prep peak changes by only 44,279 bytes from 4 to 400 old segments, publication peak by 8,166 bytes, and released-plan retention remains about 1.4 KiB. Reader cache remains separately reported at zero resident segments/events after publication measurement.

Local-key allocation after the R1 correction:

| Alias groups | key iterations | membership probes | record actions | peak bytes | retained bytes | released-plan retained bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0 | 3 | 3 | 50,885 | 30,249 | 2,393 |
| 300 | 0 | 3 | 3 | 50,885 | 30,249 | 2,393 |
| 1,000 | 0 | 3 | 3 | 50,893 | 30,253 | 2,393 |

The 100-to-1,000-group peak changes by 8 bytes.

### Final affected gate

GitHub Actions run: 37247381494  
Final candidate: `a93907ecfe7bc49176c04b0d5b1d19597cc6c413`

- **448 passed in 819.25s (0:13:39)**

Command:

```text
python -m pytest -q
  simulation/tests/test_incremental_store.py
  simulation/tests/test_persistence*.py
  simulation/tests/test_cold_history.py
  simulation/tests/test_event_year_queries.py
  simulation/tests/test_canonical_digest.py
  simulation/tests/test_history_archive.py
```

### Final full simulation suite

Same run and candidate:

- **615 passed in 1081.89s (0:18:01)**

Command:

```text
python -m pytest -q simulation/tests
```

## Corrected contracts

The validated correction preserves the accepted cold-save architecture and closes the review blockers:

- R1: namespace-count preparation performs membership checks only for final changed typed keys; it does not clone or iterate unrelated persisted-key populations.
- R2: publication records a bounded `bookkeeping` phase before destructive journal cleanup so recovery can resume idempotently after partial cleanup.
- R2.1: pending identity deletion is distinguished from an absent pending entry by dictionary membership, so the stored `_MISSING` deletion marker cannot be mistaken for already-applied cleanup.
- Initial publication validation remains strict.
- Retry validation allows only states consistent with a prefix of this acknowledged plan's own idempotent cleanup after durable successor evidence is re-proved.
- Mixed current-link insertion/update/deletion cleanup can be interrupted after an early action and later resolved repeatedly.
- A subsequent real save and reopen preserve exact alias topology and values.
- Existing foreign-token, changed-record/new-segment corruption, mutation guards, exact event partitioning, bounded transfer, stale-writer handling and checked acknowledgement behavior remain covered by the affected/full gates.

## Historical pre-correction validation

The original cold-save candidate `b46a77da020752c6e346e4ab17691f6b4aacf3b1` previously passed:

- focused proof run 37230204473: **237 passed in 308.04s**;
- affected run 37232510632: **440 passed in 727.40s**;
- full simulation suite in the same run: **607 passed in 974.21s**.

Those results remain historical evidence for their tested source. The corrected source is validated by the new 448/615 gates above.

## Corrected product/test blobs

The final tested correction candidate supplies these exact changed blobs:

- `simulation/ate_sim/persistence_cold_save.py` — `37843b508d4554d1296ea97b20594cdc0e3c5e96`
- `simulation/tests/test_persistence_cold_save_bounds.py` — `d3bd4a32feb8bf9e7879fa1ee05d82c8ba523dbe`
- `simulation/tests/test_persistence_cold_save_failures.py` — `fc985217bb0c9ceaecc8797b159d71ac5f87fbfa`

All other product/test files remain the accepted PR versions. The candidate-only workflow `.github/workflows/p3b-cold-save-review-fixes.yml` is validation scaffolding and must not be landed.

## Scope exclusions preserved

No architecture restart, detach/export expansion, checkpoint-default replacement, millennium/endurance run, balance change, Stage 1 work, unrelated feature work or merge is included. Cold save/recovery is accepted. Lifecycle completion and P3B integration review
remain pending; Stage 0.5 stays unmerged.
