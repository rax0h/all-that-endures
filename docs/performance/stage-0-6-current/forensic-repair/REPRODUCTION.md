# Reproduce the non-mature membership comparison

The November14 raw figures use a year1,26,206,208-byte fixture. They do not measure
the mature year1001 world. This procedure reproduces those engine sources and
records a new observation on the caller's host. Historical timings are not
guaranteed on another machine or runtime.

| Role | Public commit | Engine tree |
|---|---|---|
| Baseline | `1d46590bcd2725ebd75a39a5ab3170efca8e39b9` | `b45a0e4b15c7f6f2954d57776706eddda2d9c7de` |
| Candidate | `b66c2aa77f7a4e7282a4405a0f4a5d057727a9df` | `fd20cf1784a331de07f4979db71dda0f3d301771` |
| Current recovery repair, separately qualified | `4eadb66855289b9983677815f402af1ceb94b37e` | `84626841aa84b87a0564eda15200d83ea1478bb4` |

`public-source-map.json` maps preserved local head aliases to public engine
inventories by every Python file SHA256. It states where only engine equivalence
is established. Local02743cf4 and publicb66c2aa7 also have identical full Git trees.
Do not treat a local alias as a public checkout reference or rewrite historical
raw receipts. The current recovery repair is a separate engine candidate.

## Inputs and environment

Use the accepted complete-year qualified runtime. In this workspace it is
`/workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python` (Python3.13.5,
SQLite3.46.1); verify its full fingerprint with the repository's
`rank-up-publication/independent-review/check_runtime.py` before local acceptance.
Hosted qualification records its separate Python3.12.16/SQLite3.46.1 tuple.
The engine tests do not establish arbitrary Python/SQLite compatibility.

Reuse an existing closed input if its size and SHA256 match
`small-operation-profile/input.json`. Otherwise, with authenticated `gh` access
to private draft446184821, restore the original archive through the read-only
consumer from the current checkout:

```bash
python -m simulation.stage_0_6_preserved_transport --key small-year1 --output /absolute/path/small-original.zip
```

The ZIP must be7,400,318bytes/SHA256
`8844c45d2dac81515d5a8f2cdb072f03456515421849558d2f56e8712c6e9f32`.
It contains the single `candidate.sqlite` file. Extract only that member to a new
path; the DB must be26,206,208bytes/SHA256
`2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554`.
The runner independently checks the pinned database hash before any trial.
Preserved release parts avoid the original Actions carrier's expiry; they add no
authority to change source state, accepted commitments or deterministic digests.

## Explicit checkouts and invocation

Create detached, clean checkouts of the two public commits above. Choose their
locations and the input/output paths explicitly. The runner supplies each child
with its selected checkout's Python import path, verifies the exact HEAD, full
clean checkout, engine tree/file inventory, source hash, saved/fresh digests and
source/runtime preservation. No sibling workspace name is inferred.

Run this from the current repository, replacing the absolute paths:

```bash
python docs/performance/stage-0-6-current/membership-read-scope/run_pair.py \
  --source /absolute/path/candidate.sqlite \
  --baseline-root /absolute/path/baseline-checkout \
  --candidate-root /absolute/path/candidate-checkout \
  --baseline-commit 1d46590bcd2725ebd75a39a5ab3170efca8e39b9 \
  --candidate-commit b66c2aa77f7a4e7282a4405a0f4a5d057727a9df \
  --dry-run
```

After preflight succeeds, replace `--dry-run` with
`--output /absolute/path/new-results`. Each independent trial has a120second
outer bound and retains its closed report. A later failure does not erase earlier
reports. Use `run_confirmation.py` with the same explicit arguments and another
new output directory only when a concrete new question justifies confirmation.
No automatic repeat or millennium regeneration is part of this procedure.

The parent records host load/CPU/cgroup boundary observations. These samples do
not prove an idle or exclusive host. Earlier raw trials lacked independent load
records; their historical idleness cannot be verified retroactively.

## Save profile evidence

`baseline-save-profile-index.json` binds both archives and all six original
prepare/commit/acknowledgement call graphs. Baseline profiles are already in
`family-publication-scope/evidence.zip` under `candidate-profile/`; candidate
profiles are in `membership-read-scope/evidence.zip` under `save-profile/`.
All recorded work counts were recomputed and match both sides of
`membership-read-scope/save-work-comparison.json`.

Save latency was higher in three historical pairs and lower in one. The exact
cause remains unestablished. Equal operation counts do not establish equal CPU,
IO, scheduling or latency. New trials describe their own host/run; they cannot
retroactively identify unrecorded historical load. No save gain is claimed.
