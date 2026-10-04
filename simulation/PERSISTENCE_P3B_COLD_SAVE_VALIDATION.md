# P3B cold-save validation evidence

**Status:** implementation complete; stop for Astra review.  
**Scope:** `simulation/PERSISTENCE_P3B_COLD_SAVE.md` only.  
**PR branch baseline:** `19fe6c90bced632ac57e83d60822212a0b554491`.  
**Final tested candidate:** `b46a77da020752c6e346e4ab17691f6b4aacf3b1`.

## Validation

### Focused cold-save proof set

GitHub Actions run: 37230204473  
Candidate: `6d052cfc9ffc9d4ec43931c0a637bbe63b6df7b3`

- **237 passed in 308.04s (0:05:08)**
- No product-source changes were made after this run. Later candidate changes only corrected brittle test assertions and replaced the temporary validation workflow.

Measured bounded-save evidence:

| Old sealed segments | 4-chunk segment reads | 4-chunk payload reads | 4-chunk payload writes | 1-chunk segment reads | 1-chunk payload reads | 1-chunk payload writes | no-op writes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 4 | 12 | 7 | 1 | 9 | 4 | 0 |
| 40 | 4 | 12 | 7 | 1 | 9 | 4 | 0 |
| 400 | 4 | 12 | 7 | 1 | 9 | 4 | 0 |

Four-chunk transfer sizes were 8,192 events. One-chunk transfer sizes were 2,048 events. The plan never transferred more than four sealed chunks per save.

Local q=0 mutation stayed bounded at 7 payload reads / 3 payload writes / 3 record actions for 4, 40 and 400 old segments.

Alias scaling stayed flat:

| Unrelated alias groups | record actions | changed-member work | payload reads | payload writes |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 3 | 0 | 7 | 3 |
| 300 | 3 | 0 | 7 | 3 |
| 1000 | 3 | 0 | 7 | 3 |

Repeated append/seal/save reclamation returned to:

- batch 1: disk segments 1, memo 0, bindings 24, LOG occurrences 0
- batch 2: disk segments 2, memo 0, bindings 24, LOG occurrences 0
- batch 3: disk segments 3, memo 0, bindings 24, LOG occurrences 0

### Final affected persistence gate

GitHub Actions run: 37232510632  
Final candidate: `b46a77da020752c6e346e4ab17691f6b4aacf3b1`

- **440 passed in 727.40s (0:12:07)**

Command:

```text
python -m pytest -q   simulation/tests/test_incremental_store.py   simulation/tests/test_persistence*.py   simulation/tests/test_cold_history.py   simulation/tests/test_event_year_queries.py   simulation/tests/test_canonical_digest.py   simulation/tests/test_history_archive.py
```

### Final full simulation suite

Same run and same final candidate:

- **607 passed in 974.21s (0:16:14)**

Command:

```text
python -m pytest -q simulation/tests
```

## Contract proved by the focused and affected tests

The implementation proves the requested cold-session save boundary:

- exact D/F/N event authority partition and exact reopen coverage;
- at most four leading resident sealed chunks transferred per save;
- one P1 transaction for the successor generation;
- checked acknowledgement by generation, token, descriptors, counts, changed records and new segments;
- ambiguous/lost acknowledgement recovery without a second commit;
- foreign-writer/stale detection without rebasing;
- fail-before-mutation guards for supported World, tracked-container, EventLog, emit and simulation operations;
- idempotent recovery across runtime publication phases;
- independent restored continuation;
- no whole-history payload reads during ordinary save preparation/publication;
- bounded work independent of 4/40/400 old sealed segments;
- bounded local alias work independent of 100/300/1000 unrelated alias groups;
- reclamation of transferred LOG occurrences and save-plan/session retention.

## Landed product and test blobs

The PR branch should contain these exact blobs from the final tested candidate:

- `simulation/ate_sim/core.py` — `8aea2f2159c24c9397520ca905ff4544a9cd85c9`
- `simulation/ate_sim/engine.py` — `de927139a2fde8aacae5e9f15009378c73909250`
- `simulation/ate_sim/event_log.py` — `af7c4e4ab5afb3689419ede63e413383da6cad2d`
- `simulation/ate_sim/persistence_cold_save.py` — `d7055e48d0ceb8e45564aa58500c6f6aa381b02d`
- `simulation/ate_sim/persistence_session.py` — `87ba68fe924adfafb7014d3bf59eb27b0a91a110`
- `simulation/ate_sim/persistence_tracking.py` — `1d66cc568ce41d804d25e75556713e5c289f1bf8`
- `simulation/tests/test_persistence_cold_save.py` — `bc0e23d15fff3a157d1635aeb91d260800c7e3da`
- `simulation/tests/test_persistence_cold_save_bounds.py` — `c059ae63260346f149d201a746f4a5133a3bb64f`
- `simulation/tests/test_persistence_cold_save_failures.py` — `d35d298df58c79f8808d1968ad091979d9700545`
- `simulation/tests/test_persistence_session_open.py` — `62d9d75f26b4ed17304b5873f0b718e29fbe38c9`

The candidate-only workflow `.github/workflows/p3b-cold-save-focused.yml` is validation scaffolding and must not be landed.

## Scope exclusions preserved

No detach/export expansion, checkpoint-default replacement, millennium/endurance run, balance change, Stage 1 work, unrelated feature work or merge is included in this slice.
