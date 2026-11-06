# Native ordinary roster and catalog composition

Parent e423c94/run42226884633 is verified green: full suite 4,790 passed plus
two subtests in 8,916.04s, proof-map successful, one deliberate ZIP warning.

Ordinary namespace enumeration now checks the accepted manifest head's record
count against a namespace-indexed physical COUNT before selecting payloads.
The accepted lazy declaration is checked first; segment counts remain separate.
Every returned unique key/body still joins the accepted ordinary root, so equal
cardinality replacement cannot hide a missing accepted key. Final enumeration
count, source checks and cursor cleanup share the original checked snapshot.

The count parser uses the existing closed metadata codec and strict count schema,
with the existing 1MiB metadata bound. Only immutable accepted metadata may be
cached in an eligible operation scope. Physical counts and actual source checks
always repeat. Work scales with the selected namespace; this is not a constant
first-body or whole-archive scan claim.

Catalog runtime is unchanged. New public entrypoint tests cover descriptor,
retirement, owner/tree/group/link bytes, owner placements, exact membership and
the missing-header/source/placements fallback, including warmed owner caches.
The owner witness is deliberately metadata-only; its accepted payload commitment
does not authorize decoding an unchecked present body. The separate native
source read must still reject that corrupted body. See catalog-coverage.md for
the seam inventory and remaining direct-metadata-reader gate.

Initial RED seven failures/20 controls/31 deselected82.11s; first GREEN65cases
171.96s; extended22cases73.47s; refined physical controls3cases13.42s. Extra
catalog run initially eight valid tamper passes and one unregistered-owner
fixture failure; corrected nine cases pass25.53s. All historical evidence is
preserved. The 1k/10k controls each perform ten selected ordinary payload cursors
and ten empty cursors returning no bodies, with zero other ordinary/lazy/segment
payload accesses;0.020778/0.017109s are micro-controls, not world timings.

One independent whole-package review reports no actionable findings, including
Minor, with nothing deferred. Its eight focused final-file cases pass21.66s;
independent schema/budget, per-scope metadata-cache/physical-count and warmed
catalog missing-link-projection probes pass. The reviewer retained all author
source/generated-year/publication gates and the audited count/root/PK invariant.
Author fixture and instrumentation findings are closed in review.md.

Clean-source launcher/probe-driver33cases46.16s pass. Runtime pin, all existing
fingerprints, Python syntax, both workflow YAML documents/all21Bash blocks and
proof-job roster inclusion pass. Local53ed4842965ab250671aa7fc4a1626c7b52bce0a
and API403664d46eb88e34e5b75acfb8150e66501d0f11 have the identical complete
source tree6ac8e9eff6f0750646b99ecabf94b9b4264cf7ca, runtime
757c3c3f5ea0f876d4a48c75af83e88b5a241bb6. Source-map.json binds identities.

Both canonical raw/diagnostic passes now match the eager successor and fresh-process restore, preserve the accepted-source hash and record zero diagnostic full-save World audits. Raw open16.567/step13.880/save11.063/fresh34.621s on the shared host alongside correctness work; Python3.12.14/SQLite3.53.1. These are uncontrolled small-world observations, not a speed comparison or mature acceptance. Final runtime regression345cases1211.80s passes. It loaded before the three extra catalog cases were added; the nine final-file catalog cases25.53s and independent eight-case review21.66s cover those additions. Runtime bytes did not change. All4816simulation tests collect2.27s. One evidence-child publication carries this complete package to the bundled hosted full/proof gate; hosted completion remains pending. No full-audit removal, main/default/mature fixture
or endurance action. Mature targets remain open; no controlled speed claim.
