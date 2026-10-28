# CI duration attribution

Exact archived logs/XML were downloaded and SHA256-verified. Current run40633435258 reports4391 tests plus2 subtests; JUnit counts4393 cases. The previous run40591864732 reports4334 tests/4334 JUnit cases. JUnit case durations include setup/call/teardown; the retained slowest30 phase entries are calls, so separate complete fixture setup/teardown totals are unavailable. Do not invent them.

Current pytest elapsed: 7361.630s; prior: 7065.572s. JUnit case count growth: 59 (1.36%). Different hosted VMs/cache states; timing trends are observations, not isolated source regressions.

Current workflow concurrency wait before job creation:4488s (74m48s); runner assignment1s. Full-suite job7374s, actual pytest7361.630s. Runtime and queue are separate. The existing workflow already uses --durations=30; no expensive rerun is needed to add that flag.

| Test | Current total s | Prior total s | Ratio |
|---|---:|---:|---:|
| simulation.tests.test_persistence_history_operations.test_streaming_history_bounds_and_detach_cost_are_measured[400] | 1322.063 | 1284.42 | 1.029 |
| simulation.tests.test_stage_0_5_final_advancement_graph.test_scalar_edit_does_not_read_or_write_imported_sample_history | 465.309 | 475.891 | 0.978 |
| simulation.tests.test_persistence_cold_bootstrap.test_bootstrap_transfer_read_and_retention_bounds | 346.789 | 280.091 | 1.238 |
| simulation.tests.test_stage_0_5_final_aged_save_continuation.test_year_60_world_continues_exactly_through_two_saved_years | 216.432 | 223.421 | 0.969 |
| simulation.tests.test_persistence_history_operations.test_streaming_history_bounds_and_detach_cost_are_measured[40] | 125.461 | 130.113 | 0.964 |
| simulation.tests.test_stage_0_5_final_long_harness.test_long_harness_complete_lane_restores_exact_two_milestones | 108.836 | 113.816 | 0.956 |
| simulation.tests.test_persistence_cold_save_bounds.test_cold_save_allocation_bounds_exclude_fixture_and_reader_cache | 107.945 | 93.907 | 1.149 |
| simulation.tests.test_checkpointed_upgrade_validation.test_p5_bridge_emits_normal_receipt_and_exact_continuation | 106.994 | 101.887 | 1.05 |
| simulation.tests.test_stage_0_5_final_long_harness.test_staged_harness_resumes_checked_artifacts_without_rebuilding | 103.183 | 106.472 | 0.969 |
| simulation.tests.test_stage_0_5_final_identity_headers.test_identity_header_comparison_never_reads_sequence_history[10000] | 99.420 | 103.74 | 0.958 |
| simulation.tests.test_stage_0_5_final_history_type_admission.test_valid_paged_admission_reads_no_member_payload[10000-sequence] | 96.493 | 103.054 | 0.936 |
| simulation.tests.test_stage_0_5_final_event_id_exceptions.test_pop_skips_large_removed_suffix_and_clear_replaces_authority | 81.939 | 82.602 | 0.992 |
| simulation.tests.test_persistence_lazy_souls.test_soul_history_scaling_is_bounded_by_requested_access[10000] | 80.787 | 79.942 | 1.011 |
| simulation.tests.test_stage_0_5_final_sequence.test_delete_to_empty_root_and_failed_mutation_rollback | 72.840 | 73.58 | 0.99 |
| simulation.tests.test_persistence_session_open.test_open_close_event_history_bookkeeping_is_constant[400] | 64.883 | 60.547 | 1.072 |

The top test constructs a400-segment cold history under tracemalloc and performs streaming/detach work. Fixture building occurs inside the test call, so “call” time does not exclude fixture construction. Another test builds a long imported advancement history. Those are concrete bounded-profile candidates; sharing mutable SQLite fixtures or reducing coverage is not justified by duration alone. Use focused harness/transport checks for benchmark-only changes. Full-suite partitioning/caching requires a separate isolation-preserving change and measurement.
