# Memory metric correction: verified-evidence resume

Runtime/harness product remains98a37c64514084879ef77c04825e47e1f6a4fabe (ate_sim tree00fd97c9690e26e83754473a5cc5e688ee042b76). Test correction:e2fea2d8172c31e618841d49916630d1326ea89c; documented source:0883e37b03d737c5a9d196274e3486f54642d711. The executing runtime stays pinned; the corrected test is fetched separately and its isolated function change is verified before running it. Every receipt names both identities and the workflow SHA.

Original run38603776178 stays failed:2484 main tests and2 subtests passed; one inherited-rusage measurement assertion failed. Recovery95 focused tests and complete3+4+3 passed. No large year1000 job ran. This resume does not declare the original whole suite green.

Local proof:220MiB parent reproduces the old equal-peak failure; corrected child-image VmHWM/VmPeak and unchanged110MiB guard pass in both parent cases.46 affected tests passed19.56s. The exact new gate's source-scope check and two guarded cases also passed on a detached original product checkout (2 passed10.18s), recording separate inherited rusage metrics and new image peaks. Complete-scope archive SHA/JUnit and recovery archive SHA/95-test XML/year10 digest were verified locally.

Hosted gate strictly checks:
- Original run/job conclusions, both original archive digests/provenance and source.txt SHAs.
- Original XML summary2487 including2 subtests;2485 main-case rows with2484 passing rows and exactly the named inherited-peak failure; no errors/skips.
- Original recovery receipt/95-test XML and exact year10 digest.
- Byte-identical runtime/harness and all other test AST nodes. The only changed function is the measurement regression; only that test file and two documentation files may differ between product and correction.
- Both corrected subprocess cases, strict lower measured validation peak, unchanged110MiB guard and old-fails/new-succeeds behavior.

If any check fails, the complete upgrade stays blocked. Successful composed evidence is labeled as reused passing tests plus the corrected test; original_full_suite_passed remains false in receipts. This is a disclosed verification ruling to avoid repeating52minutes of unchanged passing work, not a runtime change or skipped memory requirement. Cost if the ruling is wrong:a checked gate rejects or remaining large acceptance fails; no overwrite/promotion occurs.

After the short gate:resume only the retained year1000 lazy checkpoint11870590333 under8GiB RLIMIT_AS, then exact1001/1002 continuation and fresh-runner downloaded restore. All prior checkpoint/ZIP/database/source configuration checks and no-overwrite publication remain. Acceptance remains pending those jobs. No bootstrap rebuild, main/PR14 merge or default checkpoint replacement.

First reuse-gate run38625131330 stopped before large conversion because the validator initially expected2487 XML rows. Actual pytest XML has2485 main rows;2 passing subtests are summary-only. The corrected parser enforces both counts separately. Actual retained XML/receipt verification now passes locally. Runtime and corrected test code are unchanged.
