# Native source proof reads

Parent df624e9 is verified green in run41977203078: both hosted jobs passed,
4,592 full-suite tests plus two subtests in7,792.94s, with one intentional
duplicate-ZIP warning. This closes the annual ordinary package's hosted gate.

The existing native lazy-version, ordinary-record and event-segment fetch seams
now join fetched bytes and point absence to the externally accepted World roots
before decoding. The adapter uses the existing store, authority/pin, proof maps,
raw source validators and canonical decoder. Current-generation reads require
matching SQLite/outer snapshot context and a checked epoch. Operational metadata
is bounded before inherited reads. Row-wide typed metadata preflights/SQL body
gates prevent transfer of already-invalid bodies. Impossible future interval
closure is rejected. Verified original checksum fields are reused rather than
rehashed solely to reconstruct native tuples.

Only the exact authority-owned publisher capability outside read-only/SQLite
callbacks may read transient staging rows. Being busy is not an exemption.
Callbacks cannot expose an unaccepted child value that might roll back. Normal
commit, original-parent recovery, current aliases and legacy stores are covered.
Limits:64MiB encoded bodies and1MiB locator/operational metadata or segment IDs.
No source cache, clean flag, new registry, second publisher or content framing.

One independent package review found six Important and two Minor issues; all
are corrected and verified in the consolidated `review.md` register. Raw probes,
historical failures and test-assumption corrections remain preserved. Initial
source tamper tests:8failed/3passed15.93s then11passed16.06s. Expanded source
tests:30passed38.63s; final pre-review35passed58.22s. Review regressions first
reproduce12failures14.71s; the race test subsequently uses an actual independent
write because this SQLite elides no-op UPDATEs. Guard-disabled RED1.64s and
guard-enabled GREEN1.76s are retained separately.

Initial related run365passed401.35s. Post-review broad run432passed/1failed
443.35s. Its sole failure is the existing no-op test's obsolete fixed second-
epoch injection, which moved into a locked reader under the new boundary checks.
Its correction preserves the original no-op generation0 and stale-authority
assertions, but injects once at an actual transaction boundary. That case passes
2.74s. This broad run is supporting evidence, not labeled a green whole suite.
Final source/session and clean-source results are appended after completion.

The1k/10k retained-history controls read exactly20 selected lazy source bodies,
zero unrelated version bodies and zero unexpected physical ordinary/segment or
off-path version body selections. The physical SQL trace supplements actual
source locators; no constant zero is inferred solely from one adapter. These
small point-read controls are not years, mature performance or fast-open evidence.

## Next admission gate

Full audited admission is intentionally retained. This adapter authenticates
the existing named native byte-fetch seams, including each fetched ordinary
enumeration body; it does not certify ordinary roster completeness or every raw
SQL consumer. Ordering, query and identity relation completeness still need
native proof integration and an explicit consumer-coverage gate before the full
opening audit may be removed. Mature10s open/2s save/1s warm-year targets remain
unproven. No default activation, main merge, mature fixture or endurance launch.

## Final verification/source

- Final **77 native-source/session tests passed131.07s**, covering every
  review correction, epoch work bound, original-parent recovery and native saves.
  The earlier432-pass/one-failure run is qualified above; its runtime core is
  retained, and the obsolete no-op injection is corrected and verified in77.
- Final physical-selection test refinement **2 passed7.16s**. SQLite column
  authorization observes ordinary/segment payload access even through quoted,
  schema-qualified or cached statements; SQL trace and actual version source
  locators supplement it. Both1k/10k controls fetch exactly20 selected source
  bodies with no observed unrelated version bodies/ordinary/segment selection.
  This test-only refinement changes no application runtime or launch fingerprint.
- Final clean-source **29 launcher tests passed21.65s**. All launch fingerprints,
  runtime pin, Python compilation, workflow YAML/bash and product whitespace
  checks pass. Historical raw failure output is preserved unedited.
- Final clean canonical year: raw open**11.183s**, step**5.852s**, save**7.494s**,
  fresh restore+digest**18.540s**. Diagnostic save**18.246s** is not substituted
  for the raw operation. Both raw/diagnostic fresh processes match independent
  eager control; accepted source is unchanged; diagnostic full-save audit count
  is**zero**. The broader regression also covers consecutive generated years3/4.
- Source join cost remains material. The initial bridge's raw step6.124/save7.446s
  and final5.852/7.494s are not a controlled wall-time improvement comparison.
  Deduplication proves a physical work improvement (6/8epoch checks down to at
  most3 per point), without source/path caching or a trust bypass. No new latency
  improvement is claimed. The previous annual package's4.558s result is
  historical, not the current runtime's measured save time. None of these small
  World values establish mature targets or fast opening.

Runtime `b2a02f301e08bfda3bea51d76624a8e17e9c2aac`. Local validated source
`70aaf3dc0c9d0223c66888f53ceb916d97466c5c` and API source
`6a6cfc9a5c51a6c164acd8b1f0465cf0ad86f04b` share exact complete tree
`9b9eaf59bc21cc60e19205d858e458695c41cd4e`. Source-map retains the mapping.
The evidence child changes no runtime. One branch update publishes the whole
package; full/proof hosted success remains open until that exact commit passes.

## Hosted gate closed

Verified e3d5df9/run42042165724: both jobs successful,4,641 tests plus two
subtests passed in6,575.83s, one intentional duplicate-ZIP warning. Receipt:
`green-42042165724.json`. Continue native collection state/order proof integration.
