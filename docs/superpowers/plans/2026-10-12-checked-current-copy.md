# Checked Current Catalog Copy Plan

The complete Stage0.5 directive authorizes inline implementation.

Goal: explicitly copy an already backed checked-catalog store without relabeling
its identities, rebuilding retired IDs as individual empty groups, or changing
source bytes/held aliases/pins/pending overlays.

Capture with the existing current-head copier into an unpublished private file.
Preserve all current rows, physical paths, catalog commitments, order/high-water
counters, compact retired directory and immutable segments. Fully verify this
captured authority, then use one existing commit to replace destination backing
dependency tokens with empty rosters and advance its cold commit descriptor.
Fully verify before no-overwrite publication. The source UUID is not reused.

Private API: `_copy_current_checked_catalog`. The legacy catalog bootstrap remains
separate and refuses an existing catalog. No promotion/relabeling in this path.
No capability6 marker or complete-format claim until remaining contracts close.

Tasks:
- [x] RED for saved native recursive graph/catalog copy and preserved source state.
- [x] Implement existing capture/commit/publication and semantic verification.
- [x] Verify sharing/incarnations, readonly data, held overlays, dependency rosters,
      retired intervals, source advance, faults and corruption/no-overwrite.
- [x] Run focused/affected gates and checkpoint source/evidence.

Final15 focused passed in5.91s. Affected62 passed in13.19s before only the paired
unresolved-source-acknowledgement cases; production matches both gates. Existing
dependency11 passed in0.31s. Counts overlap. Four further RED corruption cases
exposed unreachable owner/retirement nodes, unindexed links and missing empty
physical owner witnesses. Shared explicit catalog verification now checks their
full inventories and scrubs the existing retirement directory.

Source rows/commitments/compact retirement and physical placements are preserved;
only destination dependency rosters and cold commit descriptor are published by
the existing commit. This remains a private format5 checked-current copy path.
