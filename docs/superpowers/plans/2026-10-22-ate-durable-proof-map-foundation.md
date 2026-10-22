# ATE Durable Proof Map Foundation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. The user authorized implementing Astra's architecture efficiently. Continue within that scope without repeating routine permission requests. Keep the currently running runtime candidate unchanged while executing this next package in a separate branch/worktree.

**Goal:** Build the bounded immutable map primitive needed for durable committed-state proofs, with real SQLite persistence and authenticated point/absence operations.

**Architecture:** A compressed radix tree commits to exact encoded-key locators and value hashes. Immutable content-addressed nodes use checked canonical bytes; path-copy updates reuse unaffected descendants. The map joins the existing caller transaction but is not yet a new World format or authority for bypassing existing checks.

**Tech Stack:** Python 3.12, hashlib, sqlite3, pytest; existing StoreIntegrityError and memory-budget conventions.

**Spec:** `docs/superpowers/specs/2026-10-22-ate-proof-node-contract.md`, subordinate to `docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md`.

## Global Constraints

- Preserve the existing World state, typed codec, identity, order, history, counters and RNG semantics.
- Do not select reader capability 7, change ordinary open/save, or disable a format-6 check in this package.
- No whole-map clean cache or second canonical object registry. Bound node bytes and in-flight path work explicitly.
- Use immutable node writes inside the caller-owned SQLite transaction. Never commit, acknowledge or garbage-collect roots independently.
- Targets remain warm year <=1 s, incremental save <=2 s, open <=10 s. Primitive scaling is not mature timing acceptance.

## Review Focus

- Malformed but hash-consistent node bytes must reject when fetched; successful checksum comparison alone is not structural admission.
- Parent/child path and count disagreement must reject even when each node separately has a valid hash.
- Failed or rolled-back writes must not leave a reusable in-memory authority for unpublished nodes.
- Old roots must remain usable after insertions, deletions and replacements; no removal of shared nodes before a retention contract exists.
- The source key's existing typed bytes must remain exact; do not coerce floats, NaNs, duplicate positions or numeric keys into new simulation semantics.

## Task 1: Canonical node encoding and validation

**Files:** Create `simulation/ate_sim/persistence_proof_nodes.py`; create `simulation/tests/test_stage_0_5_proof_nodes.py`.

**Interfaces:** Frozen `Root(digest: bytes, count: int)`, `Leaf(locator: bytes, commitment: bytes)` and `Branch(prefix: tuple[int, ...], children: tuple[tuple[int, Root], ...])`. `encode_node(node) -> bytes`, `decode_node(raw: bytes) -> Leaf | Branch`, `node_digest(map_domain: bytes, raw: bytes) -> bytes`, `empty_root(map_domain: bytes) -> Root`, `key_locator(map_domain: bytes, typed_key: bytes) -> bytes`. Use the spec's exact framing/tags and 696-byte node limit.

- [x] Write `test_known_canonical_bytes_and_domain_separation` using hand-constructed leaf/branch bytes and independent hashlib framing; assert different domains differ and malformed types reject.
- [x] Add parametrized `test_reject_noncanonical_nodes`: trailing bytes, bad tags, odd-prefix padding, bad depth, duplicate/unsorted slots, child count 0/1/17, zero child counts, wrong digest length and count overflow.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_nodes.py`; expected RED missing module/functions, not fixture/import setup errors.
- [x] Implement the interfaces and strict structural validation; source typed keys stay opaque bytes.
- [x] Run the same test file; expected all PASS. Commit `feat: define canonical bounded proof map nodes`.

## Task 2: Immutable authenticated point updates

**Files:** Create `simulation/ate_sim/persistence_proof_map.py`; create `simulation/tests/test_stage_0_5_proof_map.py`.

**Interfaces:** `ProofMap(map_domain: bytes, read_node: Callable[[bytes], bytes], write_node: Callable[[bytes, bytes], None])`; methods `get(root: Root, typed_key: bytes) -> bytes | None`, `set(root: Root, typed_key: bytes, commitment: bytes | None) -> Root`, `iter_leaves(root: Root) -> Iterator[tuple[bytes, bytes]]`. The leaf iterator returns locators/commitments, not a source-key enumeration. It does not claim SQL result order. Every fetched node is checked against its digest/count and inherited prefix constraint.

- [x] Write deterministic real-map tests: insert a key, replace it, preserve old root, prove missing-key absence, split a shared prefix, delete and compress the sole survivor, delete to empty. Assert same-value/absent-delete return the original root and write zero nodes; insertion permutations yield the same final root. A forged zero-count nonempty digest must reject.
- [x] Add forged-child count/path, missing-node and changed-bytes tests. Mutate separately stored canonical bytes while preserving a valid unrelated subtree and assert affected access rejects; unrelated access need not scrub untouched descendants.
- [x] Add independent reference-map comparison across a fixed seeded sequence of inserts/replacements/deletes. After each transition check every live key, selected absent keys, complete leaf count, and each retained old root. Keep the test bounded (e.g. 200 changes), no endurance simulation.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_map.py`; expected RED missing map implementation.
- [x] Implement checked iterative/path-bounded descent, prefix splitting and immutable path-copy updates. Do not materialize all leaves for a point update. Reject cycles/malformed depth instead of recursively overflowing.
- [x] Run both proof test files; expected all PASS. Commit `feat: update authenticated proof maps by affected path`.

## Task 3: Caller-transaction SQLite persistence and scale evidence

**Files:** Create `simulation/ate_sim/persistence_proof_store.py`; create `simulation/tests/test_stage_0_5_proof_store.py`; extend proof-map scaling tests.

**Interfaces:** `ProofNodeStore(db: sqlite3.Connection)`; `create_schema()` creates only the private node table, `read(map_domain: bytes, digest: bytes) -> bytes`, `write(map_domain: bytes, digest: bytes, raw: bytes) -> None`, `diagnostics() -> dict`. `write` requires an existing caller transaction; no commit, root selection or garbage collection. Table identity `(map_domain BLOB, digest BLOB)` is a primary key, canonical bytes stored as BLOB. Repeated node insertion must compare exact checked bytes, not overwrite.

- [x] Write real-SQLite tests for reopen, duplicate identical writes, conflicting same-digest bytes, missing/corrupt nodes, borrowed transaction rollback and transaction ownership. Assert adapters never commit the caller transaction; old roots work after new commits.
- [x] Establish RED, implement the adapter, then require all three proof test files GREEN. Retain no clean-node cache in this first adapter. Check canonical bytes/hash on each actual fetch; only the map operation's bounded in-flight path is retained. Report read/write node counts and bytes, with clean-cache bytes 0.
- [x] Build 1k/10k/100k unrelated map keys in a disposable SQLite database. Hold the edited key/value fixed and reset diagnostics before one point replacement. Assert zero unrelated **World payload** reads, <=66 old node fetches and <=65 new node writes (64-level locator path plus leaf and deletion-survivor allowance where relevant), no map-sized Python collection, unchanged old-root lookup and exact new value. Report node work separately from SQL/table bytes and measured process RSS.
- [x] Retain a JSON source/config/result receipt and logs under `docs/performance/proof-map-foundation/`. No mature download or simulation endurance run.
- [ ] Run proof tests plus existing store/copy/recovery regressions selected from actual changed imports; run the full suite in bounded CI before merge. Commit `feat: persist immutable proof nodes inside caller transactions`.

## Task 4: Whole-package review and integration handoff

- [x] Obtain one fresh whole-branch review through the executing-plans workflow. Fix Important findings with reproducing RED/GREEN cases; retain final verification logs.
- [x] Document measured path work, maximum node bytes, cache/scratch/dirty residency and explicit limitations. Do not call root production alone a speed fix.
- [ ] Define the next integration plan for content-leaf binding, complete topology/query/order proofs, root-bearing generation manifests, verified copy upgrade and atomic recovery publication. Resolve the five integration boundaries in the node contract before enabling any persistent capability or bypass.
- [ ] Publish only task-owned changes with a nonforced exact-parent lease. Leave the current runtime validation source identifiable; no main merge.

## Plan self-review

This plan covers only the immutable map portion of Astra's package C. It deliberately cannot pass the full generation/query/open acceptance gates yet. Input/output types agree across tasks, strict decode checks cover the five review risks, and the existing World codec and generation publisher remain outside the primitive. Later integration must supply complete ordered query authority rather than treating unordered membership as a range proof.

Measured and reviewed primitive results: docs/performance/proof-map-foundation-results.md. Full CI is pending. Integration handoff is written; the full follow-on integration plan is still required before capability selection.
