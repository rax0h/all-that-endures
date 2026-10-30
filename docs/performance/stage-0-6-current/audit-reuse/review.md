# Independent whole-package review: conditional postcommit audit reuse

Review target: `/workspace/scratch/69c9a0951946/ate`, `32268ac..82d8af6`.
Reviewer: independent review agent `/root/review_audit_epoch_reuse`.
Date: 2026-10-30.

Verdict on the reviewed revision: changes required. Four actionable findings: two Medium / P2 runtime regressions and two Minor / P3 diagnostic defects. All belong to the current work group and should be entered in its consolidated closure register. No full suite or hosted workflow was launched by this review. Runtime source and tests were not edited by the reviewer; the only authored file is this report.

## R1 — Medium / P2: equal epoch bypasses the explicit closed-codec guard

Location at reviewed SHA: `simulation/ate_sim/persistence_proof_world_session.py:103-106`.

`_epoch()` retains the codec object, not its mutable methods or registries. After the first postcommit audit, acknowledgment can change the existing codec instance in place without changing any tuple component. The new reuse branch then accepts the audit receipt and returns success. The former second audit rechecked `_require_closed_codec()` and rejected such caller hooks. This is a concrete loss of an explicit proof-source admission condition, independent of whether the delegating hook changes decoded values.

Real-fixture reproduction, using the existing `fixture` / `opened` helpers:

```python
path, pair = fixture(tmp_path)
s = opened(path, pair)
a = s.store._world_proof_authority
original_audit = a._audit
original_decode = s.store.codec.decode
calls = []

def audited_then_hooked(pin):
    epoch = original_audit(pin)
    calls.append(epoch)
    if len(calls) == 1:
        s.store.codec.decode = lambda payload: original_decode(payload)
    return epoch

a._audit = audited_then_hooked
s.world.settlements[1].memory['new'] = [1, 2, 3]
assert s.save() == 1  # incorrectly accepted at 82d8af6
```

Observed: save accepted generation 1 with one authority audit. Returning a deliberately mismatching receipt from that same wrapper forces the unchanged second-audit path and produces `StoreError: proof source requires a closed codec without caller hooks`. The method hook delegates exactly to the original decoder, so the comparison isolates guard enforcement rather than unrelated decoding errors.

Recommended bounded fix: recheck the existing closed-codec invariant before accepting a reused receipt; do not add a second full audit for the matching case. Regression should require rejection after a real post-audit in-place method mutation and preserve normal matching-epoch call counts.

## R2 — Medium / P2: equal epoch accepts an acknowledgment that leaked an open transaction

Location at reviewed SHA: `simulation/ate_sim/persistence_proof_world_session.py:100-108`.

A read-only `BEGIN` after the postcommit audit changes none of the epoch components. The new branch can therefore return a successful save while the connection still owns an acknowledgment transaction. Native operations require an owned transaction boundary, and `_settle()` explicitly rejects this condition. Before reuse, the second audit also rejected the leaked transaction instead of returning success.

Real-fixture reproduction:

```python
path, pair = fixture(tmp_path)
s = opened(path, pair)
original_publish = s._publish_committed_hybrid

def leaked_acknowledgment(plan, result):
    generation = original_publish(plan, result)
    s.store.db.execute('BEGIN')
    s.store.db.execute('SELECT payload_checksum FROM records').fetchone()
    return generation

s._publish_committed_hybrid = leaked_acknowledgment
s.world.settlements[1].memory['new'] = [1, 2, 3]
assert s.save() == 1  # incorrectly accepted at 82d8af6
assert s.store.db.in_transaction
```

Observed: generation 1 is returned with one authority audit and `in_transaction=True`; the next save raises `StoreError: native proof operation requires an owned transaction boundary`. Forcing a mismatching receipt instead reaches the old audit and raises `OperationalError: cannot start a transaction within a transaction`, so it does not return success. This can also block another writer under the supported DELETE journal mode. No claim is made that unsupported WAL mode permits hidden corruption: the native opener correctly rejects WAL, and the supported journal's read lock blocked the attempted concurrent writer.

Recommended bounded fix: require the same closed transaction boundary before receipt reuse and reject an open acknowledgment transaction. Regression should require save failure and explicitly clean the injected transaction before teardown.

## R3 — Minor / P3: timeout drops all accumulated attribution evidence

Locations at reviewed SHA: `docs/performance/stage-0-6-current/audit_probe.py:153-174`; `.github/workflows/stage-0-6-audit-attribution.yml:52-70`.

The tracker accumulates completed-case evidence only in memory, and `--output` is written only after `pytest.main()` returns. The workflow deliberately sends TERM/KILL on a ten-minute timeout. A stalled or timed-out selector therefore loses every previously completed case's attribution and epoch observations. The `always()` upload can preserve the source receipt, but it cannot preserve the missing attribution JSON. Ordinary pytest failures that return normally are preserved; the defect is interruption/timeout evidence.

Controlled reproduction: execute the reviewed `main()` with a fake `pytest.main` that records a completed case and then blocks, under `timeout --signal=TERM 0.2s`, using `/dev/stdout` as output so no file is created. Observed exit 124 with only the marker emitted inside fake pytest and no JSON. The same control flow is used when a real selected test hangs after previous cases complete.

Recommended fix: write an atomic initial/in-progress report, checkpoint completed cases and active-node state, and preserve a separate workflow process-exit/timeout receipt. Clearly distinguish incomplete evidence from a completed pytest result. Do not fabricate a successful exit code after interruption.

## R4 — Minor / P3: recovery epoch checks include unrelated admission audits

Location at reviewed SHA: `docs/performance/stage-0-6-current/audit_probe.py:45,57,76-96`.

Audit epochs are aggregated by `save_N` / `outside_save` bucket. All audited opens and `resolve_save()` executions in one test share `outside_save`. Consequently an execution's `authority_audit_count`, first-audit equality fields and first-audit deltas can include earlier admissions or earlier recoveries, rather than only audits belonging to that execution. This misattributes focused recovery evidence. The documented within-save fallback counts are unaffected because each save has its own bucket.

Deterministic synthetic reproduction using the actual `CallAttribution` class and functions compiled with filename `persistence_proof_world_session.py`:

1. Profile `_audit(('db', 'codec', 1, 10, 1, 1))` outside any save, representing admission.
2. Profile one `execute()` that calls `_audit(('db', 'codec', 1, 20, 1, 1))`, sets both `observed` and `verified` to that second epoch, and returns.

Observed execution report:

```json
{"bucket":"outside_save","authority_audit_count":2,
 "first_audit_equals_observed":false,"first_audit_equals_final":false,
 "last_audit_equals_observed":true,"observed_equals_final":true,
 "first_audit_to_final_epoch_delta":{"total_changes":[10,20]}}
```

That execution actually contains exactly one matching audit. Recommended fix: capture the audit-list index on each `proof.execute` call and compare only epochs added during that execution; retain the bucket aggregate separately if useful. Add a small synthetic regression with admission followed by multiple recovery executions.

## Other reviewed semantics and limits

- The receipt is reset at execute entry and in `finally`, and is set only for a committed, reaudited manifest result. It cannot intentionally survive an unsuccessful call or cross-save retry.
- `resolve()` does not populate the receipt, so recovery retains its independent audits. Pending original-parent/token context is preserved across uncertain publication.
- External commits alter `data_version`; same-connection DML alters `total_changes`; main/TEMP DDL changes the recorded schema versions. A differing observed epoch still reaches the original audit path. A database/codec object replacement also compares unequal with the normal closed types. No extra actionable defect in these checks was established.
- The existing spoofed-receipt regression only proves branch selection; it is not a direct external mutation test. The parent reports adding actual benign-schema and corrupt-body post-audit mutations, plus public recovery after restoring the injected checksum, to close that evidence gap.
- The post-observation race remains guarded on subsequent access by the recorded old epoch, as in the prior implementation. This review does not claim a global atomicity or arbitrary-Python sandbox guarantee.
- Profiling overhead is disclosed, nested inclusive spans are not incorrectly added in the gates document, and historical full-suite evidence is correctly identified as covering the older runtime. Small-fixture audit-count evidence does not establish mature-world latency or authorize an endurance/full-suite dispatch.

## Disposition

All four findings were delivered to the parent during this review. The parent reports implementing all four bounded fixes in the working tree, with seven targeted regression cases, and is running affected-path and fresh-process continuation validation. This report records the findings against `82d8af6`; final author verification and closure evidence belong in the current group's closure register. No finding should be silently deferred to the next group.
