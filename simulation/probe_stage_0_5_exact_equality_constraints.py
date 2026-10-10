"""Counterexamples for candidate equality-directory keys, not a feature gate.

Run with PYTHONPATH=.:simulation. These observations do not prove that every
bounded implementation is impossible; they reject payload-only and address-only
shortcuts while the full exact-key lifetime design remains open.
"""
import json
import platform
import weakref

from ate_sim.persistence_adapters import WorldCodec


def probe():
    codec = WorldCodec(identity_links_recorded=True)
    first, second = float('nan'), float('nan')
    native = {first}
    result = {
        'python': platform.python_version(),
        'implementation': platform.python_implementation(),
        'distinct_native_nan_entries': len({first, second}),
        'same_object_probe_present': first in native,
        'distinct_object_probe_present': second in native,
        'canonical_payloads_equal': codec.encode(first) == codec.encode(second),
        'decoded_representative_is_original': codec.decode(codec.encode(first)) is first,
    }
    try:
        weakref.ref(first)
    except TypeError:
        result['base_float_weakref_supported'] = False
    else:
        result['base_float_weakref_supported'] = True
    result['released_address_and_hash_reused'] = False
    for attempt in range(1000):
        old = float('nan')
        marker = id(old), hash(old)
        del old
        fresh = float('nan')
        if (id(fresh), hash(fresh)) == marker:
            result['released_address_and_hash_reused'] = True
            result['reuse_attempt'] = attempt + 1
            break
        del fresh
    # Distinct tuples whose common child is the same NaN are equal through the
    # native container identity shortcut; merely canonicalizing NaN bits cannot
    # classify both this case and distinct-child tuples correctly.
    same_child_a, same_child_b = (first,), tuple([first])
    different_child = (second,)
    result['tuple_same_child_equal'] = same_child_a == same_child_b
    result['tuple_distinct_nan_child_equal'] = same_child_a == different_child
    result['tuple_payloads_equal'] = codec.encode(same_child_a) == codec.encode(different_child)
    return result


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2, sort_keys=True))
