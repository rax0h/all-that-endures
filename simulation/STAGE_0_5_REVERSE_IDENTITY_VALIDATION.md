# Checked reverse identity lookup foundation

The current branch now provides an incarnation-leading covering index on explicit create/conversion/current-head copy, plus `identity_occurrences_for_incarnation(pin, incarnation_id)` returning checked `(owner_namespace, owner_key, occurrence_path)` placements.

Ordinary open does not construct the index. Missing or incorrectly shaped index authority requires an explicit source-preserving current-head copy. Exact backup retains the original physical store; explicit current-head copy creates the new index without modifying source bytes.

Each result checks allocator bounds, checksum, visible interval, canonical typed key/path encoding, legal path components and exact owner/path authority, including overlaps across incarnations. Old pins preserve old placements after a competitor replaces one current occurrence.

Red:9 tests failed in1.10s before the API/index existed. Additional semantically checked corruption tests exposed an unsupported path component accepted by the initial implementation (1 failed/2 passed in0.12s); path validation was added before completion.

Green: `PYTHONPATH=.:simulation python -m pytest -q --tb=short simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py`: **64 passed in5.86s**. These verify1k/10k fixed group lookup, SQL use of the covering index, zero payload bodies read,≤20 metadata rows, old-pin replacement, corruption, malformed path, allocator mismatch, overlap, invalid IDs, missing-index rejection and explicit copy-upgrade source preservation.

This is only a foundation. Pinned versioned P2C witnesses, bounded discovery/publication and elimination of eager global open/no-op save inventories remain pending. No full suite or long run was launched.
