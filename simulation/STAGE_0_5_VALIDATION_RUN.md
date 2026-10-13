# Complete candidate acceptance: durable CI run

Candidate source commit: `5bf5c0192b307d15b9ab525cee20938584506ae6`, tree `4abd10073b17d3effcee36c31de005f13c84f0fc` (local equivalent `0ed4c2bb48bbb83f8ddaa9596173d632f4df707a`).

The local full-suite process stopped after roughly14% without a recorded failure. Local required complete-format P5 produced no final report. Both process sessions disappeared before completion, so neither is certification. This supersedes the earlier statement that those local acceptance processes were running asynchronously.

The same acceptance commands are now submitted to GitHub Actions on an isolated validation branch. Validation commit `ec9f8aef028da31c3ba31fe0f620abe8dd199280` differs from the candidate only by `.github/workflows/stage-0-5-complete-validation.yml`; both jobs explicitly check out the immutable candidate SHA above. It runs the full applicable simulation test suite and complete-format seed8430003+4+3 P5 in separate jobs. It retains logs/JUnit, P5 JSON and the relocated portable restore SQLite artifact for14days. No endurance or default-checkpoint change is included.

[Live validation run 38335872125](https://github.com/rax0h/all-that-endures/actions/runs/38335872125)

Observed status at submission: in_progress, candidate source pinned in both jobs.

[Validated component evidence](https://github.com/rax0h/all-that-endures/blob/5bf5c0192b307d15b9ab525cee20938584506ae6/simulation/stage_0_5_complete_candidate_validation.json)

Final acceptance remains pending until both jobs finish and their output is checked. Main, PR14 and rank issue17 are unchanged.
