import json

from simulation.persistence_p4_probe import (
    build_offer_fixture,
    build_people_fixture,
    independent_control,
    measure_offer_case,
    measure_people_case,
)


def test_people_fixture_keeps_active_set_fixed():
    small = build_people_fixture(10, active_count=4)
    large = build_people_fixture(100, active_count=4)

    assert [p.id for p in small.people.values() if p.alive] == [1, 2, 3, 4]
    assert [p.id for p in large.people.values() if p.alive] == [1, 2, 3, 4]
    assert len(small.people) == 14
    assert len(large.people) == 104
    assert small.currency.wallets[-1] is small.currency.wallets[-2]
    assert large.currency.wallets[-1] is large.currency.wallets[-2]


def test_offer_fixture_irrelevant_history_does_not_change_order_or_work():
    small = measure_offer_case(10)
    large = measure_offer_case(100)

    expected = {
        "essence": [1, 2],
        "awakening_stone": [3, 4],
    }
    assert small["first_query"]["offer_ids"] == expected
    assert large["first_query"]["offer_ids"] == expected
    assert small["repeat_query"]["offer_ids"] == expected
    assert large["repeat_query"]["offer_ids"] == expected

    # Current offer work follows the fixed owner_index, not the number of
    # consumed historical MagicResource rows.
    assert small["first_query"]["inventory_work"]["candidate_ids"] == 4
    assert large["first_query"]["inventory_work"]["candidate_ids"] == 4
    assert small["repeat_query"]["inventory_work"]["candidate_ids"] == 0
    assert large["repeat_query"]["inventory_work"]["candidate_ids"] == 0


def test_small_people_probe_reports_current_eager_growth(tmp_path):
    result = measure_people_case(tmp_path, 20, active_count=4)

    assert result["open"]["state"]["people_resident"] == 24
    assert result["open"]["io"]["payload_reads"] > 0

    noop = result["no_op_save"]
    assert noop["generation_before"] == noop["generation_after"]
    assert noop["io"]["payload_writes"] == 0

    first = result["first_current_query"]
    assert first["value"]["ids"] == [1, 2, 3, 4]
    assert first["source_rows_required_by_current_RecordTable"] == 24
    alive_index = first["state_after"]["people_indexes"]["alive"]
    assert alive_index["previous_entries"] == 24
    assert alive_index["bucket_members"] == 24
    assert alive_index["dirty_entries"] == 0

    repeat = result["repeat_current_query"]
    assert repeat["value"] == [1, 2, 3, 4]
    assert repeat["io"]["payload_reads"] == 0

    checked = result["checked_store_point_access"]
    assert checked["io"]["payload_reads"] == 1
    assert checked["value"] == 24

    reactivation = result["reactivation_query"]
    assert reactivation["reactivated_id"] == 5
    assert reactivation["value"] == [1, 2, 3, 4, 5]
    assert (
        reactivation["index_before_query"]["alive"]["dirty_entries"] == 1
    )

    edited = result["one_local_edit_save"]
    assert edited["generation_after"] == edited["generation_before"] + 1
    assert 1 <= edited["io"]["payload_writes"] < 10
    assert edited["dirty_after"] == []

    assert result["explicit_full_audit"]["io"]["payload_reads"] > 0
    assert result["explicit_archive"]["archive_bytes"] > 0
    assert result["close"]["store_closed"] is True
    assert result["close"]["session_active"] is False


def test_independent_control_short_continuation(tmp_path):
    result = independent_control(tmp_path)

    assert result["initial_years"] == 2
    assert result["continued_before_save"] == 1
    assert result["continued_after_reopen"] == 1
    assert result["event_count"] > 0
    assert result["next_event"] == result["event_count"] + 1
    assert len(result["final_digest"]) == 64


def test_probe_result_is_json_serializable(tmp_path):
    # The machine-readable baseline must stay plain JSON data.
    result = measure_offer_case(1)
    json.dumps(result, sort_keys=True)
