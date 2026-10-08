# Event-ID storage integration checkpoint

Plan: `STAGE_0_5_EVENT_ID_DESIGN.md`. This is a repair checkpoint, not final architectural sign-off or full-suite evidence.

Explicit cold-to-lazy conversion proves a consecutive range from the actual set representatives, stores one checked `(0,(event-ids-range/v1,end))` row, updates logical layout and physical head counts in the private destination, and publishes reader capability 5. The source file is preserved. Normal lazy open retains no member ordinals or member baseline keys; append/save journals one descriptor. Exact legacy/member shapes stay resident and preserve representatives. A gap transitions the same public facade to checked stable ordinal rows; an explicit whole-set operation can recompact it.

The descriptor and EventLog use the existing frozen hybrid plan/commit. Rollback and lost acknowledgement tests cover both range and fallback at ordinary writes, before head, before commit and after commit. Normal acknowledgement now verifies changed event-ID bytes, compact layout and the exact physical authority row set before adoption. Valid-checksum wrong descriptors and extra rows are rejected without clearing the pending journal. Portable codec/canonical/detach preserve native sets. Sealing event data freezes the facade. Wallet/treasury authority references and eager set-field aliases preserve identity; nested shared-wallet detach uses one native set and retains containing-dictionary sharing.

Red evidence: initial integration tests exposed the eager `_RootSet`; normal acknowledgement accepted a wrong checked successor and an extra checked row; event freeze retained a live facade; exact fallback aliases and detach split their shared objects; conversion reported a hard-coded format 3. Each regression was run before its production fix.

Focused commands use `PYTHONPATH=.:simulation` and `/workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short`.

- Event-ID facade/integration: 81 passed in 7.03s, including 34 integration cases and 47 protocol cases.
- Cold save/failures/capture/session-open/identity-restore plus the integration cases then present: 211 passed in 134.79s.
- Codec/tracking/currency/lifecycle/unloaded alias plus facade/integration before the final nested-wallet case: 162 passed in 36.41s. A final combined run is recorded in the main ledger after it completes.
- P5 seed 843000, pre 3 / continuation 4 / reopen 3, paged households: passed; final year 10, 439 events; exact control final digest `3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`, total digest `b31c2272d220a1624ff5ee204e229ccaf95adf9a7eaff86643b350567b5e9387`. Portable detached checkpoint and relocated restore pass; conversion reports capability 5. Raw output: `continuous-repair-p5-event-ids.json` in scratch for final CI packaging.

Numerical assertions: H=0/1k/10k opens retain zero member ordinals, one persisted key, zero ID-member visits, and an empty acknowledged owner journal. Independently sealed EventLogs at H=2048/20480 plus a fixed three-event tail have zero resident ID members, facade/object dictionary <=8192 bytes, zero ID-member visits during open/emit/save/close, one descriptor action, and <=32 bytes descriptor growth. These bounds describe event-ID authority, not the entire World or residual identity discovery.

Remaining obligations: final stale/legacy compatibility matrix, all cross-family specialized lazy set-slot aliases, fixed-K whole-World measurements, and the combined architectural review. Generic child histories and identity discovery are still separate pending tasks. No production promotion, final full-suite launch, or long run is implied.
