# P3B cold World capture — architect review

Review date: 2026-10-04 UTC (2026-10-03 America/Chicago).
Reviewed live PR #14 head: `77c6ccd4ca8b7344e60d4e0ca78168bd45faf619`.
PR remains open, draft and unmerged.

## Decision

**Cold capture is not yet fully accepted.** Its architecture follows the approved
slice, and the two demonstrated typed-validation defects are corrected in this
review commit. Required evidence is still incomplete. The next bounded Sol
assignment is `PERSISTENCE_P3B_COLD_CAPTURE_FOLLOWUP.md`, not a new session/save
implementation tranche.

P1/P2/P3A and the accepted composite EventLog, identity enumeration/retirement,
and cold identity restoration remain accepted. No redesign or restart is needed.
Stage 0.5 remains decision B and is not ready to merge.

## Verified submitted evidence

CI run `37168195017`, job `111335498658`, tested candidate
`bbbd1d727ca95918d51c35c3bc1219fde01d9569`:

| Gate | Actual job-log result |
| --- | --- |
| focused | 76 passed in 75.17s |
| affected | 264 passed in 227.16s |
| full simulation/tests | 431 passed in 472.06s |

Every simulation Python product/test blob in that candidate matches reviewed
head `77c6ccd` exactly. The submitted validation document is not part of that
tested candidate. The 13 cold-capture cases were also rerun independently:
**13 passed in 20.14s**.

The reported 4/40/400-segment metrics were confirmed in the actual job log:
2,084 payload reads; 704,473 / 709,904 / 716,070 payload bytes; zero segment reads;
zero disk/pending cache segments; three tail Events; 87 projected groups/paths.
These observations support lazy capture but do not substitute for the missing
enforced SQL, retention and malformed-input gates below.

## Demonstrated defects and minimal correction

### 1. Typed event-layout counts were checked only with Python equality

`_capture_cold_world()` compared the event collection tuple directly to its
expected descriptor-derived tuple. In a one-event tail-only store, all these
invalid descriptions were accepted:

* `("EventLog-disk/v1", True, 0)`
* `("EventLog-disk/v1", 1, False)`
* `("EventLog-disk/v1", 1.0, 0)`
* `("EventLog-disk/v1", 1, 0.0)`

The check now requires an exact tuple and integer count/chunk fields before
comparing values. No stored format or accepted EventLog behavior changes.

### 2. World/head equality allowed differently typed metadata

A valid-checksum head with `simulation_position=77.0` matched restored integer
World year 77; `next_ids['next_person']=True` matched integer counter 1. P1's
generic metadata codec is deliberately not a World-schema validator.

The cold World boundary now requires an integer simulation position and an exact
dict of integer next-ID values before existing key/value equality checks. The
generic P1 contract is unchanged; seed is already typed by checked-head rules.

Six real-store adversarial cases failed against the submitted implementation
(`DID NOT RAISE`, 6 failed in 0.13s). All six passed after the correction
(6 passed, 13 deselected in 0.14s). They are now part of
`test_persistence_cold_capture.py`; the malformed stores were published using
P1 with valid checksums and a correctly advanced commit descriptor.

Final local full suite on the corrected product/test code:
**437 passed in 323.27s**, exit 0, Python 3.12.14. Command:

```sh
PYTHONPATH=/tmp/ate-review-deps:simulation python -m pytest -q simulation/tests
```

This is local review evidence, not a new Actions result. The local Python
snapshot was checked against the live tree: only the two intended modified
Python files differ (the fetched baseline has an extra trailing newline in
some local copies). This review commit publishes the exact tested files.

## Remaining acceptance gaps

These are requirements already present in section 5 of the capture spec, not
new architecture requirements:

* The new suite contains 13 cases, predominantly partition counts and happy
  paths. It does not exercise the specified suffix/descriptor/namespace/mode
  damage matrix, complete non-event/event value fidelity, or capture-generation
  consistency under competing publication.
* The forbidden-link test uses `pytest.raises(Exception)` and a comment claiming
  zero segment reads, without asserting that claim. It covers pending history,
  not all excluded historical endpoint classes.
* Failure ownership checks do not demonstrate reader closure after allocation;
  the complete successful close/store lifetime boundary is not tested here.
* The scaling cases print several metrics but do not enforce their cross-size
  bounds, detect SQL segment/header enumeration or prove zero pending decodes.
  The fixture retains its decoded `suffix` while measurements are made, contrary
  to the retention-measurement requirement.
* The lazy corruption test replaces a checksum's first character with `0`;
  this is not guaranteed to change it. Missing unread segments and explicit
  `verify_full()` after capture are not covered by this slice's tests.

Sol must close these evidence gaps, fixing only additional defects actually
demonstrated. Do not claim independent resumed simulation or durable session
save/recovery: those remain later P3B integration gates.

## Scope of this review commit

Only cold capture validation, its six regression cases and review/handoff
documentation change. No public API, binding, event transfer, save/recovery,
converter, export, gameplay, checkpoint default, workflow or merge change.
No millennium/endurance run occurred.
