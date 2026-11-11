# Historical source-control reuse — independent review

Recommendation: **reuse the authenticated historical year1001 canonical value as
the original-source expectation**. Keep a real current post-rebase digest and all
current source/catalog/proof/physical audits. This imports a value commitment,
not an SQL validation memo or permission to skip an audit.

Reviewed source:5b3ffbb5bfe536b7953034e41880e932b483dacb,
runtime94267bb00a219702a4bd1700a2fc0600a5c5aa56. The selected source comparisons
and original binding are recorded in independent-control-source-check.json.
This was static source/receipt/log inspection: no database was opened, no profile
was performed, and no expensive run or production edit was made.

## Authority and safe boundary

The digest result records
`57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed`
for the exact29,922,463,744-byte database with
SHA256`4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2`,
UUID`06d24556-2bb1-4086-93f7-448f23b7eb5a`, generation126 and year1001.
Its digest artifact12164423938 is embedded in accepted-year artifact12165934374.
The latter's actual year-verified.json is570001bytes with
SHA256`5e54ce0e4e27b6d3a17cb22ce4fda887e5f1ee9cde6c052ab2d270144367ef45`.

Use that actual member from the live authenticated retained carrier12849181590,
after existing prepare_retained/authenticate_staged validation. Keep the original
acceptance/digest producer references: the carrier is alternate transport, not a
new acceptance producer. Require the exact member size/hash, full
validate_year_acceptance, match_producer against the original acceptance ref,
and exact saved-binding equality. Compare the observed digest to the original
authority's year1001 control as well. The binding must agree with the current
source context on database hash/size, UUID, generation, year, seed, rules and format.
Neither a repository result summary nor a bare digest string grants this authority.

The existing validator checks the embedded digest's original producer, receipt
member hash, saved candidate binding, full original checkpoint/control, observed
year/generation/identity/counters and input-preserved flag. Reusing it is therefore
different from assuming a value from an old performance log.

Label the result `historical-control-reused`, with original member/proof hashes,
producer/runtime references and compatibility-manifest identity. Do not report a
current source digest computation or transfer historical timing into current
metrics. Preserve the read-only original database reference. Consumers should
bind the imported baseline to this exact authority, not merely accept any
64-character value from metadata.

## Compatibility fence

core.py and canonical_stream.py are byte-identical to historical
2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a/runtime76dee76973928dbce72860156feb32f2d7f02f86.
That alone is insufficient as a general compatibility policy: field definitions,
typed values and collection interpretation are also part of the canonical view.
Use an explicit reviewed compatibility pair for that historical runtime and
current94267, then reject unreviewed changes. Keep these dependencies fenced:

- Canonical encoder and field selection: core.py, canonical_stream.py; field/key
  repr ordering, enum values, JSON/UTF8/float representation and collection kinds.
- Schema/model definition: persistence_schema.py and every model module it imports,
  with dataclass names, decorators, inherited fields, field types/defaults/order
  and any attribute/repr behavior affecting the canonical view. All24 schema model
  modules are byte-identical except materials.py; its changes affect derived
  caches/methods, while stored class declarations remain unchanged.
- Typed codec and tags: incremental_store.py, WorldCodec/SCHEMA/RECORD_SCHEMA and
  registrations in persistence_adapters.py, event/frozen/EventId/history/reference
  representations and their tag/version constants. Selected primitive codec/schema/
  event/reference sources are unchanged. The adapter delta only adds _derived_lots
  to the excluded cache allowlist; it does not change stored fields.
- Current projection/copy/audit implementation: keep the entire current runtime
  tree at94267 and all current harness/authority dependencies fenced, including
  the new compatibility/control helper or manifest. Lazy iteration, IndexedRecord
  hooks and storage readers have intentionally changed since2cb; do not pretend
  their source is identical or approve arbitrary future changes automatically.
- Existing exact current worker software/binary/compile fingerprint, plus the
  historical producer/runtime identity. This is a reviewed compatibility pair,
  not a claim that all Python/SQLite versions or future canonical definitions agree.

It is unnecessary to prove the new decoder correct by recomputing this same
source control with it. The real current post-rebase digest compared to the frozen
historical commitment is the independent regression check. A common-mode reader
error could affect two newly computed digests equally; the historical expectation
does not share that error. Field/schema and algorithm changes must still reject
early rather than silently redefining what equality means.

## Required bounded controls

Extend ordinary helper/harness tests within this group:

1. Valid actual small accepted receipt derives the same value as a real fresh
   digest; smoke retains its real source/post-rebase digest path.
2. Wrong member hash/size, acceptance producer/ref, embedded digest proof, source
   hash/size/UUID/generation/year/rules/seed or original control is rejected.
3. Unknown historical/current runtime pair or changed canonical/schema/model/codec
   dependency fails before copy, rebase or proof work. Do not use a hand-maintained
   two-file comparison that ignores the model schema.
4. Mature reuse cannot call the fresh source digest, claim a current digest/audit,
   or promote synthetic smoke authority. Preserve exact baseline provenance in
   the sealed parent chain and reject a changed imported value on consumption.
5. A real changed post-rebase value still fails actual canonical equality; the
   existing chain continues to observe its three real generic source audits and
   mandatory final World/physical checks. Cached source control cannot skip them.

This removes the redundant original-source walk; it does not establish the
remaining actual post-rebase walk's duration. Keep that walk separately bounded
and preserve its completed rebase parent on failure. No further expensive prefix
should be repeated to diagnose it. If historical authority or compatibility is
missing, fail closed before preparation; do not silently use a summary, weaken
the comparison or substitute a noncanonical aggregate hash.

## Concrete finding: wrapped alarm is a censored timeout

The authenticated log explicitly shows BudgetExpired raised by the source_digest
alarm inside json.loads, followed by CodecError raised from that exception.
The phase lasted3600.639s; failure.json and phase-progress incorrectly call it
`error`. This is an actionable reporting finding in this same group. It is not
evidence of bad source bytes. Preserve those raw historical files and add a
reconciliation summary; do not rewrite authenticated evidence.

Fix only the new harness recorder/wrapper. Track its own fired alarm, normalize a
wrapped owned expiry to BudgetExpired before the existing recorder records the
outcome, and retain the outer CodecError/causal chain as diagnostics. If an
operation suppresses the alarm and returns, an observed owned expiry must still
prevent a successful receipt. Restore signal handler/timer custody on every exit;
do not replace an already active caller alarm. Avoid re-raising an exception in
a way that creates a cause cycle.

Ordinary controls should distinguish direct expiry, CodecError wrapping expiry,
normal CodecError with no expiry, a mere 'BudgetExpired' message, successful work,
and handler/timer restoration. Classify by actual owned expiry/exception identity,
not elapsed-time guessing or string matching. The runtime codec and shared old
recorder/trigger helpers remain unchanged. These changes need the normal bounded
harness tests and compatible hosted small smoke; engine94267 greens remain reusable.
