# P3B Identity — cold-aware identity boundary and owner retirement

Status: architect-reviewed bounded implementation tranche, 2026-10-03.
Baseline: PR #14 composite EventLog acceptance. This file authorizes identity
work only; World/session save/open integration remains later P3B work.

## Goal

Make the accepted P2C identity machinery understand the EventLog value boundary
without enumerating sealed history. Mutable identity remains authoritative only
for current World state and mutable EventLog tail occurrences.

## Required boundary

For a composite EventLog with committed prefix D, pending sealed boundary F and
total N:

- [0,D) committed disk history is immutable value history and is never enumerated
  by identity discovery.
- [D,F) pending sealed chunks are immutable value history and are never decoded
  for identity discovery.
- [F,N) live tail is considered at its absolute logical indices.
- An individually sealed Event inside the live tail is value history and is
  excluded from LOG identity ownership.
- The EventLog root may remain an identity occurrence, but traversal through it
  must use the same mutable-tail-only boundary.
- No identity helper may populate the normal four-segment cold reader cache.

Legacy P2 behavior remains the default. Cold-aware traversal is explicit opt-in
until later session integration supplies it.

## Occurrence tracking

Extend IdentityOccurrenceIndex with an opt-in cold EventLog traversal mode.
Bootstrap and refresh use absolute mutable-tail paths and preserve ordinary
tracking for every non-log owner. The number of retained LOG owners/occurrences
must depend on mutable tail size, not historical prefix size.

Expose narrow internal diagnostics sufficient to measure owner rows, occurrence
rows and retirement work without traversing the World.

## Batched retirement

A semantic sealing transition retires LOG owners as a batch:

1. Remove all retiring owner occurrence rows before selecting replacement anchors.
2. Collect the union of identities affected by those owners.
3. Recompute explicit links once per affected identity from surviving occurrences.
4. Preserve aliases among surviving current World owners, including parent/child
   sharing and aliases that previously used a LOG occurrence as canonical anchor.
5. Remove obsolete LOG ownership/bindings/memo retention only after surviving
   owners are known.
6. Do not delete ownership for an object that still has a current non-log owner.

Retiring identity ownership is separate from durable record deletion; this
tranche does not implement P3B save/transfer.

Direct Event.seal() for a mutable tail Event must retire that Event's LOG
identity owner. EventLog.seal_before() must batch the full newly sealed range
rather than recomputing link groups once per Event.

A mutable child detached by Event.freeze() must no longer dirty the retired LOG
owner. If it remains reachable from current World state, later mutation dirties
that surviving owner normally.

## Entry points in scope

Adapt the existing identity/tracking graph walkers only as needed to respect the
opt-in boundary: IdentityOccurrenceIndex scanning, root owner enumeration,
binding/owner propagation, current-link inventory, owner lookup and unbinding.
Legacy full P2 snapshot audit/restore behavior must remain unchanged unless an
explicit cold-aware flag is supplied.

Do not add persistence_session.py, cold snapshot/open/save formats, commit tokens,
suffix-row transfer, detach, checkpoint changes or normal World restore in this
tranche.

## Tests and bounds

Required focused evidence:

- mutable tail paths use absolute indices with disk and pending history present;
- individually sealed tail Events are excluded;
- 4, 40 and 400 disk-segment fixtures with identical resident suffix retain the
  same LOG owner/occurrence counts and perform zero cold payload reads;
- aliases shared between mutable tail data and current World owners survive
  sealing with a valid reanchored current link;
- a frozen/detached old child cannot dirty its retired LOG owner while a child
  still current elsewhere dirties that current owner;
- parent/child alias groups remain correct after batched retirement;
- unrelated alias groups at 100, 300 and 1,000 groups do not increase retirement
  work for one local retired group;
- cross-session mutable alias rejection remains intact.

Run focused identity/EventLog/P2 persistence tests during development, then one
full simulation/tests suite on final code. No millennium/endurance run.
