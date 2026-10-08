# Checked reverse occurrence lookup foundation

This slice is a prerequisite to bounded discovery, not that complete migration.

Add a covering incarnation-leading index during explicit store creation/conversion/current-head copy. Ordinary open must not build it. Add `identity_occurrences_for_incarnation(pin, incarnation_id)` returning checked `(namespace, key, path)` placements at the pin. Lookup must use the index or reject with an explicit upgrade requirement, never silently scan legacy metadata. Validate allocator, checksum, intervals, decoded path/key and duplicate visible placements; preserve old pins. Scalar lookup reads no payload bodies.

Tests before implementation:1k/10k independent groups with fixed two requested placements and≤20 checked metadata rows, SQL query-plan index assertion, old-pin replacement, checksum corruption, missing-index rejection, invalid IDs. Add malformed/overlap and explicit copy-upgrade regressions before completion. Existing identity/store/failure tests stay green. Versioned P2C witnesses and removal of global open/save inventories remain pending and must not be implied by this API.
