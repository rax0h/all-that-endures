# P3B Composite EventLog — architect acceptance record

Reviewed baseline: be5283c0d59ce9bf595ab1e2acd611503a781f4b.

The composite EventLog component is accepted subject to the architect-reviewed
corrections carried with this record:

- replacement-prefix comparison uses exact typed persisted-value semantics rather
  than Python's lossy equality rules;
- a replacement reader may not regress the captured store generation;
- iterator lifetime, same-store authority, bounded four-chunk adoption and
  pre-retirement source validation from the prior correction remain required.

Five focused regressions cover persisted NaN equality, bool/int distinction,
signed-zero distinction, nested numeric type distinction and generation
regression. The reviewed patched state was reported green at 378 tests.

This acceptance does not authorize later P3B World/session integration. The next
bounded tranche is PERSISTENCE_P3B_IDENTITY.md.
