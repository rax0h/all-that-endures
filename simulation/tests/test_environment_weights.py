from simulation.ate_sim.magic_resources import _environment_weights,ESSENCE_IDS,ESSENCES


def test_cached_context_weights_exactly_match_catalog_and_remain_contextual():
    contexts=[(),('wood','plant','growth','beast'),('stone','earth','iron','metal'),('death','blood','fear'),('water','decay','dark','waste','vermin')]
    _environment_weights.cache_clear()
    for tags in contexts:
        expected=[]
        for key in ESSENCE_IDS:
            text=(key+' '+str(ESSENCES[key])).lower()
            hits=sum(1 for tag in tags if tag in text)
            if hits:expected.append((key,float(hits*hits)))
        actual=_environment_weights(tags)
        assert actual==tuple(expected)
        assert _environment_weights(tags) is actual
    assert _environment_weights(contexts[1])!=_environment_weights(contexts[2])
    assert _environment_weights.cache_info().maxsize==512
