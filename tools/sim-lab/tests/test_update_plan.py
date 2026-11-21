from ate_lab.update_plan import plan_update


def test_offline_skips():
    decision = plan_update(fetch_ok=False, dirty=False, detached=False, local="a", upstream="b", local_is_ancestor=True)
    assert decision["action"] == "skip"
    assert "offline" in decision["reason"]


def test_dirty_skips_even_when_fast_forward_is_possible():
    decision = plan_update(fetch_ok=True, dirty=True, detached=False, local="a", upstream="b", local_is_ancestor=True)
    assert decision["action"] == "skip"
    assert "uncommitted" in decision["reason"]


def test_detached_skips():
    decision = plan_update(fetch_ok=True, dirty=False, detached=True, local="a", upstream="b", local_is_ancestor=True)
    assert decision["action"] == "skip"


def test_equal_is_up_to_date():
    decision = plan_update(fetch_ok=True, dirty=False, detached=False, local="abc", upstream="abc", local_is_ancestor=True)
    assert decision["action"] == "up_to_date"


def test_ancestor_fast_forwards():
    decision = plan_update(fetch_ok=True, dirty=False, detached=False, local="a", upstream="b", local_is_ancestor=True)
    assert decision["action"] == "fast_forward"


def test_divergence_does_not_merge():
    decision = plan_update(fetch_ok=True, dirty=False, detached=False, local="a", upstream="b", local_is_ancestor=False)
    assert decision["action"] == "skip"
    assert "fast-forward" in decision["reason"]
