# Native reader inventory and authority boundaries

The raw170literal SQL/interval sites are recorded in direct-read-sites.json.
AST collection detects literal table names; dynamically composed SQL must also
be traced through its consumer/helper. This is an owned-boundary inventory,
not an assertion that every fast-opening requirement is now closed.

| Consumer | Current authority and disposition |
|---|---|
| LazyRecordStore.generation / checked_head / head_metadata | Previously public bypasses; this group joins accepted head before decoding, with original snapshot/epoch checks. |
| _read_snapshot_start / private _checked_head_row | Checked native snapshot explicitly passes accepted manifest. Private construction/write/recovery callers retain their owned publisher/admission contract. Raw primitive is not a separate public proof reader. |
| read_record / read_records | Accepted ordinary content proof, namespace roster and lazy/ordinary declaration checks; head inventory supplies accepted counts. |
| read_segment_checked | Accepted event content root and bounded actual selected source. |
| SealedEventPrefix._load_segment / cached metadata | This group guards current admitted pin/epoch/source before warm output and after segment decoding. Iterator already calls self[index] per event, so the same guard closes paused resumes. |
| _read_event_descriptors / _read_descriptor | Checked ordinary record reads plus accepted head namespace inventory; three expected descriptor keys and event boundaries checked. |
| namespace_size / iter_keys / contains_lazy_key | Accepted collection-directory state/order and selected source; native_order wrappers already replace legacy SQL. |
| query_memberships / iter_query_memberships | Accepted ordinal-query scope and exact physical windows plus selected owner sources. |
| minimum rank_neighbor | Seven-root rank directory / physical rank window. Six-root compatibility remains explicitly audited; proof-only admission cannot accept missing rank authority as empty. |
| minimum _header / _node / _persisted_ordinal / checked_marker | Headers/nodes/owners use actual version proof; candidate and empty paths enter checked snapshot/rank helpers. |
| RetiredIdentityRanges.contains / add / remove / intervals | Contains/edits enter read_snapshot or mutation snapshot even on cache hits; header/node raw reads use checked read_version. intervals/scrub remain explicit enumeration. |
| identity state / owner/group occurrences | Accepted allocator and bidirectional scope roots, actual native physical windows. |
| persistence_lazy.py _validate_*_successor raw query probes | Existing immutable publication-plan postconditions, not user-facing independent query readers; scope/World publication owns new accepted authority. |
| _read_current_identity_links / _capture_cold_baseline_ordinals | Legacy/admission restoration inventory. Complete format check excludes legacy identity path. Still review restoration selection/absence before proof-only opening. |
| verify_all / catalog scrub / retirement scrub / backup / copy_current_head / constructors | Explicit audit/export/conversion paths; do not move these scans into ordinary open/save. |
| storage_metrics / query_plan | Explicit diagnostics, not semantic source-selection authority. |

Remaining opening gate: account for schema/rules/format compatibility, restore
inventory and selection/absence, pre-admission accesses before native authority
is live, six/seven-root gating, and corruption/recovery/fresh continuation on
an opening path that actually skips the full audit. None is authorized by this
inventory alone. Full audited opening remains mandatory.
