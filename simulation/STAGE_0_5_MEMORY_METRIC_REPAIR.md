# Full-suite memory metric correction and scoped resume

Runtime product remains98a37c64514084879ef77c04825e47e1f6a4fabe; ate_sim tree00fd97c9690e26e83754473a5cc5e688ee042b76. No runtime/harness/simulation/codec/schema change is part of this correction.

Run38603776178, workflow5f0d2be10f8f4a4fc3f0ac1a24165f102ed7ca72:
- Recovery job115989332743 passed:95 focused tests243.95s and complete3+4+3, year10/control digest3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e.
- Full-suite job115993372980:2484 passed,2 subtests passed,1 failed3124.60s. Its original run remains failed.
- The only failure was `test_validation_only_fits_where_disposable_catalog_exhausts_address_space`:both reported ru_maxrss1426280KiB. Its old constructor still correctly failed under110MiB RLIMIT_AS and validation-only still correctly succeeded; only relative peak measurement failed.
- The large complete/continuation/restore jobs were skipped; the year1000 fixture was not rerun.

A parent holding220MiB reproduced the problem:both children inherited rusage peak265640KiB even though each executed image had much lower residency. Linux resource usage survives exec; `/proc/self/status` VmHWM/VmPeak measure the executed memory image. References: https://www.man7.org/linux/man-pages/man2/getrusage.2.html and https://www.kernel.org/doc/html/v6.8/filesystems/proc.html.

The corrected test reads child VmHWM and VmPeak, retains the rusage value as separate diagnostic evidence, asserts the exact unchanged110MiB address-space guard, and exercises both0/220MiB parent cases. RED:220MiB parent reproduced equal inherited peaks. GREEN:46 affected upgrade-memory/preparation tests passed19.56s. Warm case:old constructor peak82236KiB and fails; validation-only peak24664KiB and succeeds; rusage remained270656KiB for both. Their VmPeak112620/53124KiB is recorded separately. No limit increase, deleted guard or weakened memory comparison.

Evidence artifact11918576896:67445 ZIP bytes, SHA2567dbe7af7e6e838845849d9169aef6cc2f5ddf8ccf355b8b6575ad0736d1d60cc. Its JUnit summary counts2487 tests including2 subtests; the actual XML has2485 main-case rows:one named metric failure and2484 passing rows. The two passing subtests do not have separate testcase elements; there are zero errors or skips. Recovery artifact11914843405:5728 bytes, SHA256b111cd1dbe9e76c540aefd3fb711c823876d3cbabaeb063256aafaaa057ae3ab. Artifacts expire2026-10-28.

Scoped resume will keep product98a37c6 pinned and verify that the test correction changes only this one test function plus documentation, with all runtime/harness files and other test ASTs identical. A short hosted gate verifies the original artifact digests/JUnit/source/recovery receipt, runs both corrected subprocess cases, and records combined evidence honestly:the original full run was red; its unchanged passing tests are reused. This avoids repeating52minutes of unchanged test work. If there is another prior failure, source mismatch, unexpected test change, archive corruption or failed corrected case, the gate rejects and the large job remains blocked.

Only after that gate passes does the existing year1000 complete upgrade resume under8GiB RLIMIT_AS from artifact11870590333, followed by exact1001/1002 and a fresh-runner downloaded restore. Final acceptance remains pending those jobs. No main/PR14 merge or checkpoint promotion.

The first short reuse-gate run38625131330 rejected an XML count assumption before the large job:it expected2487 main rows instead of2485 because pytest includes2 passing subtests only in the summary. The parser now enforces both numbers separately and still rejects any unexpected failure/error/skip. This is a workflow evidence-reader correction; runtime and corrected metric-test code are unchanged.
