from ate_sim.rank import profile, annual_mortality, biological_age, sustenance, military_value

def test_rank_monotonic_capabilities():
    ps=[profile(i) for i in range(5)]
    assert all(a.injury_resilience < b.injury_resilience for a,b in zip(ps,ps[1:]))
    assert all(a.travel_capacity < b.travel_capacity for a,b in zip(ps,ps[1:]))
    assert all(a.magical_body < b.magical_body for a,b in zip(ps,ps[1:]))
    assert all(a.food_need > b.food_need for a,b in zip(ps,ps[1:]))

def test_rank_changes_life_risk_without_immunity():
    risks=[annual_mortality(80,i,.2) for i in range(5)]
    assert all(a>b for a,b in zip(risks,risks[1:]))
    assert risks[-1] > 0

def test_rank_changes_biology_and_sustenance():
    assert biological_age(100,4) < biological_age(100,0)
    assert sustenance(4)["spirit"] > sustenance(0)["spirit"]
    assert sustenance(4)["respiration"] < sustenance(0)["respiration"]

def test_rank_changes_force_projection():
    assert military_value(4) > military_value(0)
