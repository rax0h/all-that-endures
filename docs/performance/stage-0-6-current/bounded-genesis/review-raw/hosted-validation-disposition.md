# Finding6: permitted next validation, still open

Independent review of available isolation evidence confirms:

- Candidate legacy upgrade fails with `_CONVERSION_AUDITS` bothFalse andTrue.
  The preserved isolation log reports malformed scratch databases in both cases.
- Untouched BASE `7df089ff2b347ae8e36bb535291591a5bb6dfb82` executes the unchanged
  complete driver through construction, raw proof open, real year, save, close,
  and fresh-process digest restoration, then fails diagnostic save with source
  epoch disagreement and diagnostic close with exact-recovery required.
- Baseline complete construction took35.38seconds; the complete driver remains
  failed. Neither its raw partial success nor candidate targeted successes count
  as current complete local acceptance.

Evidence: `legacy-isolation-red.log`, `baseline-generated-year-red.{json,log}`,
and the earlier `generated-year-construction-red.{json,log}`. The implementer also
reports cross-source baseline/candidate reproduction; that comparison needs its
exact command/source-fingerprint matrix preserved in the group evidence.

Cause remains unresolved. These observations do not isolate a SQLite engine
cause, establish an unchanged runtime as currently qualified for complete local
acceptance, or exonerate application code. The previously recorded runtime tuple
qualification is historical evidence; current complete-scenario failure must be
recorded beside it. Do not weaken checks or label the whole group complete.

The repository working agreement requires findings to close before their group
is marked complete. It does not prevent collecting hosted evidence while a
finding remains open. One already authorized bundled hosted candidate validation
can therefore advance investigation under these conditions:

1. Preserve exact baseline/candidate commands, clean baseline source identity,
   driver/runtime hashes, full matching local runtime tuple, input database hashes
   and source preservation observations, isolation matrix and raw failure logs.
2. Update the plan/qualification observation to state current local complete
   acceptance is unavailable; keep finding6 and the overall group open.
3. Final request runtime-tree/file fingerprints match the exact committed
   candidate. Do not bypass, skip, cache or shorten unchanged integrity checks.
4. The proof job's unchanged complete generated-year scenario and full suite must
   both pass on that same SHA before the gated mature construction/continuation
   job runs. Any failure or censoring keeps acceptance and finding6 open.
5. A hosted result is authoritative only for its independently recorded runtime
   and source. Hosted success does not diagnose the unresolved local failure.

This permits validation evidence collection only. It does not approve group
completion, mature acceptance, merge, default format activation or endurance.
