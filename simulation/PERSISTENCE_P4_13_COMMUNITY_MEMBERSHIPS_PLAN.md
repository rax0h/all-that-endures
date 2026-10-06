# P4.13 — lazy community memberships

Post-P4.12 residual run 37496826152 shows the next unbounded eager family is
`world.communities.memberships`: 10,000 rows / 568,890 bytes.

`world.agency.actions` is larger by bytes but is explicitly capped at 50,000
rows. `world.lineage.children` is a single growing row at 438,927 bytes and
will be reconsidered after this migration.

Each membership is one scalar row keyed by `(person_id, community_id)` with a
float strength. Persist a checked `person` membership index so
`memberships_for(person_id)` loads only that person's memberships and does not
rebuild the archive-wide `_membership_index`.

Preserve exact join, inherit, community_step, migration/diaspora behavior,
dictionary order, insert/replace/delete/reinsert, no-op save, atomic hybrid
save/reopen, history export, and materializing detach.

Acceptance:

- ordinary lazy open decodes zero community-membership payloads;
- `memberships_for(pid)` decodes only rows indexed to that person;
- unsaved join/replace/delete changes are reflected by the indexed query;
- one changed membership has bounded save work from 1k to 10k;
- clean cache <=256 rows;
- materializing detach restores a plain dict;
- existing history-network, civilization, transmission and persistence
  regressions stay green.

After focused + scaling + affected gates, rerun residual eager inventory.
