import pytest

from ate_sim import checkpoint
from ate_sim.core import World
from ate_sim.persistence_lazy import (
    LazyCurrencyBucketTable,
    LazyTrackedDict,
    convert_cold_to_lazy,
    open_lazy_world_session,
)
from ate_sim.persistence_session import write_cold_snapshot


RULES = "stage-0.5-p4-lazy-currency-tests"


def currency_world(count, *, shared=True):
    world = World(843000)
    first = {"iron": 7, "lesser": 3}
    for pid in range(1, count + 1):
        if shared and pid in (1, 2):
            wallet = first
        else:
            wallet = {
                "iron": pid % 11,
                "lesser": pid % 17,
            }
        world.currency.wallets[pid] = wallet
    world.currency.treasuries[1] = {"silver": 4, "iron": 20}
    world.currency.treasuries[2] = {"bronze": 9}
    return world


def converted(tmp_path, count, *, shared=True, name="currency"):
    source = tmp_path / f"{name}-cold.sqlite"
    destination = tmp_path / f"{name}-lazy.sqlite"
    write_cold_snapshot(
        currency_world(count, shared=shared),
        source,
        rules_id=RULES,
    )
    result = convert_cold_to_lazy(
        source, destination, rules_id=RULES
    )
    assert result["source_preserved"] is True
    assert result["wallets"] == count
    assert result["treasuries"] == 2
    return destination


def test_currency_open_loads_zero_buckets_and_point_read_is_lazy(tmp_path):
    destination = converted(tmp_path, 400)
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.currency
        assert isinstance(state.wallets, LazyCurrencyBucketTable)
        assert isinstance(state.treasuries, LazyCurrencyBucketTable)
        assert state.wallets.diagnostics()["bucket_payload_loads"] == 0
        assert state.treasuries.diagnostics()["bucket_payload_loads"] == 0
        assert len(state.wallets) == 400
        assert len(state.treasuries) == 2

        wallet = state.wallets[300]
        assert isinstance(wallet, LazyTrackedDict)
        assert wallet["iron"] == 300 % 11
        assert state.wallets.diagnostics()["bucket_payload_loads"] == 1
        assert state.treasuries.diagnostics()["bucket_payload_loads"] == 0


def test_shared_wallet_identity_survives_lazy_load_save_and_reopen(tmp_path):
    destination = converted(tmp_path, 20, name="shared")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        wallets = session.world.currency.wallets
        first = wallets[1]
        second = wallets[2]
        assert first is second

        first["gold"] = 2
        assert second["gold"] == 2
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        first = reopened.world.currency.wallets[1]
        second = reopened.world.currency.wallets[2]
        assert first is second
        assert first["gold"] == 2


def test_retained_shared_wallet_rehydrates_both_evicted_owners(tmp_path):
    destination = converted(tmp_path, 400, name="retained-shared")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        wallets = session.world.currency.wallets
        shared = wallets[1]
        assert wallets[2] is shared
        for pid in range(3, 401):
            wallets[pid]
        assert not dict.__contains__(wallets, 1)
        assert not dict.__contains__(wallets, 2)

        shared["diamond"] = 1
        assert dict.__contains__(wallets, 1)
        assert dict.__contains__(wallets, 2)
        assert wallets[1] is shared
        assert wallets[2] is shared
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.currency.wallets[1] is (
            reopened.world.currency.wallets[2]
        )
        assert reopened.world.currency.wallets[1]["diamond"] == 1


def test_direct_wallet_dict_operations_are_tracked(tmp_path):
    destination = converted(tmp_path, 5, shared=False, name="direct")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        wallet = session.world.currency.wallets[3]
        wallet["gold"] = 2
        wallet.update({"silver": 3, "iron": 8})
        assert wallet.setdefault("bronze", 4) == 4
        wallet.pop("lesser")
        del wallet["iron"]
        session.save()

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        wallet = reopened.world.currency.wallets[3]
        assert wallet == {
            "gold": 2,
            "silver": 3,
            "bronze": 4,
        }


def test_real_currency_operations_match_expected_and_reopen(tmp_path):
    destination = converted(tmp_path, 6, shared=False, name="ops")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        state = session.world.currency
        state.credit(1, {"iron": 5})
        before_one = dict(state.wallets[1])
        before_two = dict(state.wallets[2])
        state.transfer(1, 2, {"iron": 3})
        assert state.wallets[1]["iron"] == before_one["iron"] - 3
        assert state.wallets[2]["iron"] == before_two["iron"] + 3

        state.consume(2, {"iron": 1})
        assert state.consumed["iron"] == 1

        state.treasury_transfer(
            1, 2, {"iron": 2}, deposit=True
        )
        assert state.treasuries[1]["iron"] == 22

        state.credit(2, {"lesser": 100})
        state.exchange(
            1,
            2,
            {"iron": 1},
            {"lesser": 100},
        )
        generation = session.save()
        before_writes = session.store.diagnostics().payload_writes
        assert session.save() == generation
        assert session.store.diagnostics().payload_writes == before_writes

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        state = reopened.world.currency
        assert state.treasuries[1]["iron"] == 22
        assert state.consumed["iron"] == 1


def test_wallet_outer_delete_reinsert_preserves_order_and_incarnation(tmp_path):
    destination = converted(tmp_path, 4, shared=False, name="reinsert")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        wallets = session.world.currency.wallets
        wallet = wallets[1]
        before = session.store.read_identity_occurrence(
            session.pin, "world.currency.wallets", 1, ()
        ).incarnation_id
        del wallets[1]
        wallets[1] = wallet
        assert tuple(wallets) == (2, 3, 4, 1)
        session.save()
        after = session.store.read_identity_occurrence(
            session.pin, "world.currency.wallets", 1, ()
        ).incarnation_id
        assert after == before

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert tuple(reopened.world.currency.wallets) == (2, 3, 4, 1)


@pytest.mark.parametrize("count", [1000, 10000])
def test_wallet_history_does_not_increase_ordinary_open_payload_loads(
    tmp_path, count
):
    destination = converted(
        tmp_path, count, shared=False, name=f"scale-{count}"
    )
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        wallets = session.world.currency.wallets
        assert len(wallets) == count
        assert wallets.diagnostics()["bucket_payload_loads"] == 0
        assert session.world.currency.treasuries.diagnostics()[
            "bucket_payload_loads"
        ] == 0

        assert session.world.currency.balance_value(7) >= 0
        assert wallets.diagnostics()["bucket_payload_loads"] == 1


def test_currency_precommit_failure_resolves_old_and_retries(tmp_path):
    destination = converted(tmp_path, 20, shared=False, name="failure")
    with open_lazy_world_session(destination, rules_id=RULES) as session:
        start = session.pin.captured_head
        wallet = session.world.currency.wallets[3]
        wallet["gold"] = 9

        def fail(phase):
            if phase == "during_version_writes":
                raise OSError("currency publication failed")

        session.store._phase_hook = fail
        with pytest.raises(OSError, match="currency publication failed"):
            session.save()
        assert session.diagnostics()["state"] == "recovery-required"

        session.store._phase_hook = lambda phase: None
        assert session.resolve_save() == start
        assert session.diagnostics()["state"] == "active"
        assert session.save() == start + 1

    with open_lazy_world_session(destination, rules_id=RULES) as reopened:
        assert reopened.world.currency.wallets[3]["gold"] == 9


def test_currency_materializing_detach_preserves_shared_alias_and_portability(
    tmp_path,
):
    destination = converted(tmp_path, 300, name="detach")
    session = open_lazy_world_session(destination, rules_id=RULES)
    shared = session.world.currency.wallets[1]
    assert session.world.currency.wallets[2] is shared
    for pid in range(3, 301):
        session.world.currency.wallets[pid]
    shared["gold"] = 11

    detached = session.detach(materialize_history=True)
    assert type(detached.currency.wallets) is dict
    assert type(detached.currency.treasuries) is dict
    assert type(detached.currency.wallets[1]) is dict
    assert detached.currency.wallets[1] is detached.currency.wallets[2]
    assert detached.currency.wallets[1]["gold"] == 11

    restored = checkpoint.loads(checkpoint.dumps(detached))
    assert restored.digest() == detached.digest()
    assert restored.currency.wallets[1] is restored.currency.wallets[2]
