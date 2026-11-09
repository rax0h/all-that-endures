# Explicit proof-backed World opening

The user has authorized continued inline Stage0.6 implementation toward interactive
simulation speeds, with exact state/identity/causal history and corruption rejection
preserved. This package implements opening against an externally accepted World
commitment without a full historical audit. Existing audited/default paths remain.
No main merge, default activation, new format default or endurance run.

## Approach and trust boundary

Chosen implementation: authenticate the fixed head and composed World component
context first, activate existing bounded native proof readers, then reuse canonical
LazyWorldSession restoration. This reuses the single registry and publisher.
Retaining/optimizing a full audit remains history-sized. Whole-file checksums also
read the historical file, so neither meets the ordinary-opening goal.

The new explicit API is open_proof_world_session(path, *, rules_id,
expected_commitment, paged_household_members=None). The external commitment must
come from accepted audited construction or the checked World publisher. It is not
a promise that all unvisited cold bytes are healthy. Source bytes are authenticated
before use; dormant corruption can be discovered on access or explicit full audit.
No malformed selected data may be used to restore a World or acknowledge a save.

Require proof format7 and the complete seven-root scope/v4 context, including rank
selection. Reject six-root/legacy/unsupported snapshots on this API, without an
implicit full-audit fallback. open_audited_proof_world_session continues supporting
its current compatibility behavior. Accepted component envelopes/facts must compose
exactly to the external manifest roots; root presence alone is not World authority.

## Bootstrap and restoration

Create the same GuardedConnection/LazyRecordStore runtime with bounded fixed
metadata/schema checks. Within an owned transaction, read a bounded raw generation
manifest and verify its external digest and complete store/codec/schema/rules/head
context before any World head decoding. Protect every pre-admission head read with
that opening manifest and metadata budget, including pin capture and snapshot entry.
A concurrent generation advance must reject against the original external head.

After capturing the exact owned pin/read view, load and bind all accepted World
components without _audit_world, verify seven-root eligibility, and activate native
read authority before reading the cold manifest, household selector, event descriptors,
scalar selectors, baseline ordinals or resident root collections. Reuse the existing
complete-format contract, canonical reconstruction and identity catalog. Restore
current-tail aliases while the owned opening-read capability is still present.
Capture the original admission context and reject pin/epoch/component drift through
restoration and transaction cleanup. No active transaction may escape the API.

Opening scales with current materialized roots/tail and visited proof paths. It must
not enumerate unrelated archived bodies or run store.verify_all/catalog/full-World
scrubs. Metadata budgets and indexed physical completeness/absence checks remain.
Successful sessions use the existing frozen save/resolve publisher, including checked
fallback audits where the ordinary writer already requires them.

## Failure ownership

Failing opens close readers/registry/store and release only the opening operation's
owned pin, without history cleanup or an audit fallback. Cleanup must not decode a
forged head. An opaque exact-pin cleanup may touch only bounded operational rows,
checking original store/generation/checksum and refusing triggers/shadows or an
unresolved publication attempt. Preserve the primary error. Never reinterpret a
failed open as a successful admission or weaken normal public source guards.

## Validation and acceptance

Use the fingerprinted system-derived local Python runtime from AGENTS. First prove
red tests; then selected/failure/compatibility tests, ordinary-session regressions,
and current generated-year eager/fresh continuation. Test both explicit open modes,
source immutability, and zero audit calls on proof opening. Exercise a selected
coherently forged source and an unvisited damaged cold segment whose first access
must reject. Count actual cold body reads with larger unrelated history.

One independent whole-package review after integration; close all findings including
Minor in this group. One bundled hosted full/proof cycle after final local validation.
Do not infer mature10s opening/2s save/1s year acceptance from the small fixture.
