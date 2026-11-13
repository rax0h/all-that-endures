# Retain ability bodies for one practice action

The current small-world profile spends 5.619 instrumented seconds under twelve
`agency._practice_path` calls. The function revisits a lazy ability list during
rank validation, candidate selection and progression. The canonical registry is
weak: a clean native body without a caller reference can be reconstructed on the
next pass. `RecordBacking._ensure` already checks the active lease on a live body.

Keep one local tuple of the path's actual canonical ability objects for the
duration of this existing action, before constructing its PracticeBatch. Use it
for ceiling and candidate selection. No tuple is added to World/session/cache
state. Canonical paths have at most twenty abilities; no historical list is
retained. Existing selection order, RNG draws, advancement and event code stay.

Alternatives considered: cache immutable proof nodes across operations (requires
new custody/byte-budget semantics); share nodes within an existing closed scope
(limited to a short owned operation);
retain the actual action operands (selected: existing object identity/lifetime
rules, one function, no new validation authority). This is the implementer's
bounded optimization choice under the user's instruction to continue Stage 0.6.

Acceptance: demonstrate repeated AbilityProgress header reconstruction in an
actual proof-backed fixture before the edit; afterwards each ability header is
loaded at most once during the same action. Check partial/full/ceiling paths,
rank transitions and RNG/event equivalence. Empty/partial/full/ceiling cases must save/reopen; rank-up fresh-child replacement is an existing unsupported publication boundary, reproduced on the unchanged baseline, and must retain its exact refusal/recovery rather than be claimed as supported. Compare two
direction-balanced raw pairs on the unchanged authenticated year-one input and
qualified runtime. Reject or preserve only as an experiment if no useful gain.
No mature restart, default activation, main merge or target acceptance follows.
