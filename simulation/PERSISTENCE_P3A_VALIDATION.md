# P3A acceptance — complete component, including cache-bypass correction

Reviewed 2026-10-03. Live PR #14 was open/draft, branch
`sim/stage-0-5-stabilization`, head
`1093dfac2d395424fb148562d504c008855e6a0f`.

**P3A is accepted in its complete current form. No implementation blocker was
found.** P1/P2/P2C acceptance remains intact. This accepts the storage component
specified in `PERSISTENCE_P3A.md`; it does not accept World integration or permit
Stage 0.5 to merge.

## Evidence verified against GitHub

| Evidence | Exact candidate | Result |
| --- | --- | --- |
| Full P3A suite, Actions run 36386684998, job 108813413742 | `1c29807b1477e419b75180aec805161dee8f0252` | 352 passed in 390.66s |
| Final correction, Actions run 36390020898, job 108823582375 | `a20110b0417ca57bf1354573ea1d2926632c7fae` | 55 affected P1/P3A tests passed in 42.76s |

The workflow conclusions and actual job logs were fetched during this review.
Git tree/blob comparison confirms every file present at the reviewed head has
the same blob as the final affected-test candidate. Its temporary workflow was
not landed. Compared with the full-suite candidate, only
`ate_sim/persistence_events.py` and `tests/test_persistence_events.py` differ;
those are exactly the narrow correction and regression additions reviewed here.
The 352-test run predates that correction; it is not represented as a fresh
full-suite run at the final head.

The review read the complete prefix implementation and the final diff.
`verify_full()` calls `_read_segment_from_store()` for every captured ordinal,
which calls P1's `read_segment_checked()` and validates the decoded envelope,
IDs/counts, generation, frozen payload and chronology. It never uses the LRU
as verification evidence. Ordinary access still uses `_load_segment()` and its
four-segment LRU. Full verification does not fill an otherwise cold LRU.

Three additional direct Python probes were executed locally against the fetched
head without changing product code: healthy warmed verification, warmed payload
corruption, and warmed segment deletion. All passed. The healthy 8,192-event
prefix reread four segments / 2,747,171 payload bytes; cache occupancy remained
four. Both damaged cases raised `StoreIntegrityError` despite a warmed cache.
These are independent review probes, not a claim to have rerun pytest locally
(pytest was unavailable in this environment).

## Accepted boundary and next work

Immutable 2,048-event segments, bounded append preparation, fixed-prefix lazy
reads, checked storage, inclusive year queries, four-segment LRU, explicit full
verification and borrowed-store lifetime are accepted together. Existing P3A
tests retain stale-generation, atomic failure/lost-acknowledgement, writer-death,
backup/relocation and corruption coverage.

P3B is specified in `PERSISTENCE_P3B.md`. It must compose this component with
World, P2C identity tracking and EventLog's mutable tail. In particular, existing
full-history P2 bootstrap/detach traversal cannot simply be reused for a cold
session. No P3A redesign, millennium/endurance run, calibration, Stage 1,
checkpoint default replacement or merge is authorized by this acceptance.
