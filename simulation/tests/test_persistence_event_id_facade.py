"""Native-set behavior and bounded normal event-ID representation."""

import importlib
import operator
import random
import sys

import pytest


def _type():
    return importlib.import_module("ate_sim.persistence_event_ids").EventIdSet


@pytest.mark.parametrize("size", [0, 1, 1_000, 10_000])
def test_checked_range_has_no_resident_members_or_ordinary_append_visits(size):
    ids = _type().from_checked_values(set(range(1, size + 1)))
    assert ids.range_end == size
    assert ids.diagnostics()["resident_members"] == 0
    assert len(ids) == size
    assert bool(ids) == bool(size)
    assert (size in ids) == bool(size)
    ids.add(size + 1)
    assert ids.range_end == size + 1
    assert ids.diagnostics()["member_visits"] == 0
    assert ids.diagnostics()["resident_members"] == 0
    assert sys.getsizeof(ids) + sys.getsizeof(ids.__dict__) < 8_192
    assert set(ids) == set(range(1, size + 2))
    assert frozenset(ids) == frozenset(range(1, size + 2))


@pytest.mark.parametrize("values", [{3, 9, 17}, {1, 3}, {-1, 1}, {True, 2}, {1.0, 2}])
def test_checked_values_never_assume_range_or_replace_representatives(values):
    ids = _type().from_checked_values(values)
    assert ids.range_end is None
    assert set(ids) == values
    assert sorted(map(type, ids), key=repr) == sorted(map(type, values), key=repr)


@pytest.mark.parametrize("name,args", [
    ("union", ([2, 4], [6])), ("intersection", ([1, 3, 5], [3, 5, 8])),
    ("difference", ([2, 4],)), ("symmetric_difference", ([2, 2, 4],)),
    ("isdisjoint", ([8, 9],)), ("copy", ()),
])
def test_named_methods_match_native_set_results(name, args):
    ids = _type().from_range_descriptor(3)
    expected = getattr({1, 2, 3}, name)(*args)
    actual = getattr(ids, name)(*args)
    assert type(actual) is type(expected)
    assert actual == expected


@pytest.mark.parametrize("op", [operator.or_, operator.and_, operator.sub, operator.xor])
@pytest.mark.parametrize("other", [{2, 4}, frozenset({2, 4})])
def test_forward_reflected_operations_preserve_native_result_type(op, other):
    ids = _type().from_range_descriptor(3)
    for actual, expected in ((op(ids, other), op({1, 2, 3}, other)),
                             (op(other, ids), op(other, {1, 2, 3}))):
        assert type(actual) is type(expected)
        assert actual == expected
    with pytest.raises(TypeError):
        op(ids, [1, 2])


@pytest.mark.parametrize("name,arg", [
    ("update", [2, 4, 4]), ("intersection_update", [1, 3]),
    ("difference_update", [2, 2]), ("symmetric_difference_update", [2, 2, 4, 4]),
])
def test_update_mutators_keep_facade_and_deduplicate_iterables(name, arg):
    ids = _type().from_range_descriptor(3)
    original = ids
    expected = {1, 2, 3}
    getattr(expected, name)(arg)
    assert getattr(ids, name)(arg) is None
    assert ids is original
    assert set(ids) == expected


def test_range_fallback_and_mutators_keep_exact_native_members():
    ids = _type().from_range_descriptor(4)
    alias = ids
    ids.remove(2)
    assert ids is alias and ids.range_end is None and set(ids) == {1, 3, 4}
    ids.add(9)
    ids.discard(99)
    popped = ids.pop()
    assert popped in {1, 3, 4, 9}
    ids.clear()
    assert set(ids) == set()
    ids.add(True)
    assert next(iter(ids)) is True
    ids.add(1)
    assert next(iter(ids)) is True
    with pytest.raises(TypeError):
        hash(ids)


def test_guard_runs_before_noop_and_changed_callback_only_after_change():
    ids = _type().from_range_descriptor(3)
    calls = []
    ids.bind(lambda: calls.append("guard"), lambda: calls.append("changed"))
    ids.add(3)
    assert calls == ["guard"]
    calls.clear()
    ids.add(4)
    assert calls == ["guard", "changed"]

    def stale():
        raise RuntimeError("stale")

    ids.bind(stale, lambda: calls.append("changed"))
    for mutate in (lambda: ids.add(3), lambda: ids.discard(99), lambda: ids.update(()),
                   lambda: ids.clear()):
        with pytest.raises(RuntimeError, match="stale"):
            mutate()
    assert ids.range_end == 4


@pytest.mark.parametrize("end", [True, 1.0, -1, "3", None])
def test_descriptor_rejects_nonexact_or_negative_end(end):
    with pytest.raises(ValueError):
        _type().from_range_descriptor(end)


@pytest.mark.parametrize("name", ["update", "difference_update", "intersection_update", "symmetric_difference_update"])
def test_failing_iterable_preserves_native_partial_mutation(name):
    def broken():
        yield 2
        yield 5
        raise ValueError("input failed")

    expected = {1, 2, 3}
    ids = _type().from_range_descriptor(3)
    for target in (expected, ids):
        with pytest.raises(ValueError, match="input failed"):
            getattr(target, name)(broken())
    assert set(ids) == expected


@pytest.mark.parametrize("started", [False, True])
def test_range_iterator_rejects_size_change_like_native_set(started):
    ids = _type().from_range_descriptor(3)
    iterator = iter(ids)
    if started:
        next(iterator)
    ids.add(4)
    with pytest.raises(RuntimeError, match="changed size"):
        next(iterator)


@pytest.mark.parametrize("op", [operator.ior, operator.iand, operator.isub, operator.ixor])
def test_inplace_operations_preserve_public_alias_and_native_values(op):
    ids = _type().from_range_descriptor(3)
    alias = ids
    expected = op({1, 2, 3}, {2, 4})
    assert op(ids, {2, 4}) is alias
    assert set(alias) == expected
    with pytest.raises(TypeError):
        op(ids, [2, 4])


def test_materialization_memo_preserves_aliases():
    ids = _type().from_range_descriptor(3)
    memo = {}
    first = ids.materialize(memo)
    assert type(first) is set and first == {1, 2, 3}
    assert ids.materialize(memo) is first


def test_deterministic_mixed_mutations_match_native_representatives():
    rng = random.Random(843000)
    expected, ids = {1, 2, 3}, _type().from_range_descriptor(3)
    operations = ("add", "discard", "update", "intersection_update",
                  "difference_update", "symmetric_difference_update")
    values = (-1, 0, 1, True, 2, 2.0, 3, 4, 4.0, 9)
    for _ in range(500):
        name = rng.choice(operations)
        operand = rng.choice(values) if name in ("add", "discard") else [
            rng.choice(values) for _ in range(rng.randrange(5))
        ]
        getattr(expected, name)(operand)
        getattr(ids, name)(operand)
        assert set(ids) == expected
        assert sorted((type(value).__name__, repr(value)) for value in ids) == sorted(
            (type(value).__name__, repr(value)) for value in expected
        )


def test_membership_matches_native_hash_equality_and_unhashable_probes():
    class Probe:
        def __init__(self, hashed, equal):
            self.hashed, self.equal = hashed, equal
        def __hash__(self): return self.hashed
        def __eq__(self, other): return other == self.equal

    ids = _type().from_range_descriptor(3)
    expected = {1, 2, 3}
    for probe in (True, 1.0, float("nan"), float("inf"), frozenset(), set(),
                  Probe(2, 2), Probe(1, 2), Probe(99, 2)):
        assert (probe in ids) == (probe in expected)
    for probe in ([], {}):
        with pytest.raises(TypeError):
            probe in ids
