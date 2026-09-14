# Magic progression validation: audit and implementation increments

## First implementation increment

The owner has authorized an ATE design for unresolved higher-rank mechanics.
The source questions below are historical audit context. Configuration/body
gates, next-tier ability ceilings, milestone events and checkpoint schema 5 are
implemented; the higher-rank understanding/economy/longevity work is not complete.

Targeted advancement, progression-history, diagnostic and resource-eligibility
tests: **25 passed**. The new chronology test proves that the Bronze body
transition references twenty ability milestones and that those references
survive checkpoint restoration and archive export.

First full-suite run: **122 passed, 1 failed** in 70.87 seconds. The only failure
was the old 100-year golden in `test_current_people`: indexed and archive-scan
simulations agreed, but intentionally differed from the old world. That reference
is now `b1838563864e60a8782ed0d87d21996ec41a8f03828a31229bb2f55f3734a503`.
The change is caused by removing premature Iron biology from partial users,
requiring full ability readiness, enforcing ability ceilings, and recording
new progression state/events. It is not a new millennium golden.

No final millennium validation has been run. No claim is made yet about the
finished phase's performance, Diamond population or complete historical validity.

## Original pre-implementation audit

Status: **not a completed corrected-world validation**. See
[the source audit](MAGIC_PROGRESSION_CANON.md) for blocking primary-source questions.
Audited main: `9551c9c314b8cdbd15f5b6e0c22e95b203d848e2`.
No simulation code or reference digest was changed in this audit checkpoint.

## Reproduced defects

This small probe uses the existing public advancement API, without modifying an
ability's rank or setting the revelation counters directly:

```python
from ate_sim.advancement import AdvancementState

state = AdvancementState()
path, _ = state.absorb_essence(1, 'visage', 0)
for calls in range(1, 20001):
    state.practice(1, 0, 1., reflection=1.)
    if state.rank(1) == 5:
        break
print(calls, len(path.base_essences), path.confluence,
      len(path.abilities), state.rank(1))
```

Observed output: `596 1 None 1 5`. These are API calls, not simulated years.
This proves the missing-configuration gate defect without a millennium run.

`profile(5) is profile(4)` evaluates to `True`; both returned profiles carry rank
4. Diamond has no separate physical profile in current main.

`annual_mortality(108, 0)` is `0.0804`. Multiplying annual survival probabilities
for ages 18 through 107 at rank zero, with no scarcity or trauma, gives
`0.1431200757241516`. This is an isolated mortality-function calculation, not an
empirical cohort estimate or a claim of canonical lifespan. It explains why an
unranked survivor at 108 is possible and warns against diagnosing immortality
solely from one old survivor. Full engine environmental mortality and species
composition are additional considerations.

## Existing canonical archive inspected, without rerunning simulation

Archive metadata verified seed `843000`, year `1000`, world digest:

`1015bf0f8b0f4d38a376b5d18f2a9299259c400bb745b776eaecc48c743697a4`

| Recorded body rank | Living people |
| --- | ---: |
| Unranked (0) | 1,126 |
| Iron (1) | 106 |
| Bronze (2) | 77 |
| Silver (3) | 29 |
| Gold (4) | 31 |
| Diamond (5) | 18 |

All living Gold/Diamond final configurations were inspected for three base
essences, one confluence and five abilities per group (twenty total).

- Incomplete Diamonds: **7, 82, 84**.
- Incomplete Golds: **46, 74, 75, 119, 7682, 7767, 8204, 8727, 9062,
  9111, 9253, 9322**.

Completeness here is a structural snapshot check. It does not certify the other
individuals' progression chronology or any unsourced metaphysical requirements.

### Person 7

Runic, born -27, alive at 1000. The final snapshot has only Visage, no confluence,
one Diamond ability, wealth `94.05945705397887` and no ranked wallet record.

| Year | Age | Event ID | Recorded event | Recorded body transition |
| --- | ---: | ---: | --- | --- |
| 0 | 27 | 9 | Visage absorbed, resource 3 | Absorption; separate rank transition not recorded here |
| 32 | 59 | 1383 | Advancement, work context | Iron to Bronze |
| 96 | 123 | 8596 | Advancement, teach context | Bronze to Silver |
| 244 | 271 | 44324 | Advancement, teach context | Silver to Gold |
| 750 | 777 | 202167 | Advancement, teach context | Gold to Diamond |

These rank events have empty cause lists. The archive does not contain the
individual ability milestone evidence needed to prove their prerequisites.

### Person 164

Human, born 7, alive at 1000. Earth absorbed at 115 (event 12430), Hunger at 118
(13065), Renewal at 120 (13532). Confluence ability awakened at 120; the final
ability was awakened at 143. Final state contains twenty Diamond abilities.

| Year | Age | Event ID | Recorded event |
| --- | ---: | ---: | --- |
| 146 | 139 | 19463 | Iron to Bronze |
| 155 | 148 | 21542 | Bronze to Silver |
| 198 | 191 | 32138 | Silver to Gold |
| 443 | 436 | 100741 | Gold to Diamond |
| 819 | 812 | 225051 | Divine grant of Deep resource 10454 |
| 899 | 892 | 251884 | Divine grant of Light resource 12035 |

The two listed divine resources remain owned by Person 164 and unconsumed in
the archive. They are **not additional absorbed essences**. Resource origin
events link back to the corresponding grants. Removing these grants as illegal
absorption would fix a misinterpretation rather than a simulation defect.

Final ordinary wealth is `920.4435358746745`. The separate wallet contains:

| Denomination | Coins |
| --- | ---: |
| Lesser | 221 |
| Iron | 99 |
| Bronze | 185 |
| Silver | 1,640 |
| Gold | 7,065 |
| Diamond | 2,667 |

The wallet already records substantial tiered rewards. `RankedCurrencyState`
has credit and valuation methods but no debit/transfer method; resource-market
affordability uses ordinary `Person.wealth`. This disconnect requires actual
transaction semantics, not an arbitrary Diamond wealth bonus. Final balances
are not historical balances at each advancement; none have been invented here.

## Test status and remaining validation

Targeted baseline command:

```sh
PYTHONPATH=.:simulation python -m pytest -q simulation/tests/test_advancement.py simulation/tests/test_ranked_currency.py simulation/tests/test_rank_ontology.py simulation/tests/test_metaphysics_divinity.py
```

Result: **24 passed**. These are existing tests, including tests that currently
permit the single-ability Diamond. They are baseline evidence, not new canon
invariant coverage. An initial full-suite invocation without the workflow's
`PYTHONPATH` failed collection; it was corrected to use `PYTHONPATH=.:simulation`.

Full suite: `PYTHONPATH=.:simulation python -m pytest -q simulation/tests`:
**118 passed in 76.56 seconds**.

Both workflow smoke commands passed:

- `PYTHONPATH=.:simulation python simulation/specific_test.py --seed 843000 --years 10 --section all`:
  causal integrity true, no bad events; digest
  `f440671ecdb7ade3b142341082ae4e48c66cd160430c068cfa9e9268aa140bb7`.
- `PYTHONPATH=.:simulation python simulation/run_long_history.py 843000 100`:
  successful causal-order validation; digest
  `f6e25615b33e2203af1f9dda4c05079ec880c92fe3a418685ccc86e78d54d42e`.
  Instrumented simulation time `1.385672016999706` seconds; this short smoke is
  not a measurement of the millennium performance gate.

No corrected canonical millennium, new canonical digest or new archive export is reported.
The prior performance/export measurements remain historical reference values in
`PERSONHOOD_HISTORY_VALIDATION.md`. The one final millennium run is reserved for
the stable implementation after primary-source prerequisites are resolved.
