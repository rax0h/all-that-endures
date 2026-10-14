# Complete-upgrade memory repair progress

Implementation starts at90a055030b917d3462d52869fd5abc286c73655e on the existing closeout branch.

## Task1: validation-only source checks

The converter now validates the captured source without constructing the first discarded catalog when normalization/promotion will rebuild it. Initial and final source checks share validation, including physical body/placement agreement and owner path hash collisions. Unchanged catalog-only copies keep their existing publication behavior.

Baseline90a0550 small shared-Event/skill fixture: checked catalog digest5f74ee4b2cbe12a33326ac6212bdf0f758d652304e3fbd12cad3be97cdec65d4; World digeste72e6d203237ac5cac9f15d616e995b2af820e8e637349599624053694913e2b. These exact values remain covered after repair; aliases and unchanged source bytes are checked.

RED: validation-only API absent. GREEN:11 new tests including eight corruption inputs, pre-normalization rejection, digest preservation and bounded subprocess memory comparison. Old aggregate construction of12000 small owners/occurrences fails under110MiB RLIMIT_AS; validation-only succeeds. Before repair, unrestricted180MiB probe passed with130100KiB peak RSS;110MiB probe failed at82224KiB. RSS and address-space caps are distinct measurements. This fixture proves removal of one allocation site, not completion of the large upgrade.

Affected gate: `PYTHONPATH=.:simulation python -m pytest -q simulation/tests/test_stage_0_5_upgrade_memory.py simulation/tests/test_stage_0_5_final_catalog_copy.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_legacy_event_copy.py` —70 passed22.08s. Baseline copy/Event gate35 passed7.06s.

Tasks2–5 remain open: replayable final catalog, bounded commit preparation, downstream capture/normalization/scrub memory, provenance and GitHub acceptance. No large job launched and no final acceptance claimed.
