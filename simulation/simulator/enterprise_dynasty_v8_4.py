import math
import random


def simulate(seed=840000, years=1000, n_families=180):
    rng = random.Random(seed)
    fam = {}
    businesses = {}
    next_biz = 0
    events = []
    for i in range(n_families):
        old = rng.random() < .06
        wealth = rng.lognormvariate(4.0, .55) * (5 if old else 1)
        fam[i] = {
            "id": i, "surname": f"House-{i:03}", "wealth": wealth, "peak_wealth": wealth,
            "members": rng.randint(3, 9), "prestige": rng.uniform(0, .35) + (1.1 if old else 0),
            "lineage_attachment": min(1, rng.betavariate(2, 3) + (.32 if old else 0)),
            "records": rng.uniform(0, .3) + (.6 if old else 0), "estate": old and rng.random() < .8,
            "businesses": set(), "magic_rank": rng.choices([0, 1, 2, 3, 4], [82, 11, 5, 1.7, .3])[0] if old else 0,
            "alive": True, "founded": -rng.randint(20, 300) if old else 0, "dynasty_years": 0,
            "name_continuity": 1.0, "generation": 0, "old_house": old, "business_founded": 0,
            "business_failures": 0, "inheritance_losses": 0,
        }

    def found_business(f, y):
        nonlocal next_biz
        startup = max(18, rng.lognormvariate(3.5, .45))
        if f["wealth"] < startup:
            return
        f["wealth"] -= startup
        bid = next_biz
        next_biz += 1
        businesses[bid] = {
            "id": bid, "family": f["id"], "capital": startup, "debt": startup * rng.uniform(0, .55),
            "quality": rng.betavariate(2.3, 2), "management": rng.betavariate(2.2, 2), "reputation": .05,
            "age": 0, "alive": True, "employees": rng.randint(0, 3), "retained": 0, "founded": y,
            "peak_capital": startup,
        }
        f["businesses"].add(bid)
        f["business_founded"] += 1
        events.append((y, "business_founded", f["id"], bid))

    for f in fam.values():
        if f["old_house"] and rng.random() < .65:
            found_business(f, 0)

    yearly = []
    for y in range(years):
        for f in fam.values():
            if not f["alive"]:
                continue
            active = sum(businesses[b]["alive"] for b in f["businesses"])
            opportunity = .010 + .010 * (f["wealth"] > 120) + .006 * (f["prestige"] > .7)
            if active < 3 and rng.random() < opportunity:
                found_business(f, y)

        for b in list(businesses.values()):
            if not b["alive"]:
                continue
            f = fam[b["family"]]
            demand = max(.25, rng.lognormvariate(-.03, .28))
            shock = rng.random()
            shock_mult = .35 if shock < .012 else .68 if shock < .06 else 1.0
            scale = b["capital"]
            saturation = 1 / (1 + (scale / 650) ** .72)
            revenue = scale * (.13 + .28 * b["quality"] + .20 * b["reputation"]) * demand * shock_mult * saturation
            costs = b["employees"] * rng.uniform(2.0, 4.8) + b["capital"] * rng.uniform(.035, .085) + b["debt"] * rng.uniform(.035, .095)
            profit = revenue - costs
            retain = max(0, min(.82, .25 + .48 * b["management"]))
            if profit > 0:
                reinvest = profit * retain
                b["capital"] += reinvest
                b["capital"] *= .992
                f["wealth"] += profit - reinvest
                b["retained"] += reinvest
                b["reputation"] = min(1, b["reputation"] + .008 * b["quality"])
                if b["capital"] > 80 and rng.random() < .08:
                    b["employees"] += 1
            else:
                loss = -profit
                cover = min(f["wealth"] * .12, loss * .45)
                f["wealth"] -= cover
                b["capital"] -= loss - cover
                if b["capital"] < 8 or (b["debt"] > b["capital"] * 2.2 and rng.random() < .25):
                    b["alive"] = False
                    f["business_failures"] += 1
                    events.append((y, "business_failed", f["id"], b["id"]))
            if b["alive"]:
                b["debt"] = max(0, b["debt"] * (1 - rng.uniform(.01, .07)))
                if rng.random() < .025 and b["capital"] > 45:
                    b["debt"] += b["capital"] * rng.uniform(.05, .25)
                b["age"] += 1
                b["peak_capital"] = max(b["peak_capital"], b["capital"])

        for f in fam.values():
            if not f["alive"]:
                continue
            f["wealth"] = max(0, f["wealth"] - f["members"] * rng.uniform(.55, 1.15))
            if not f["estate"] and f["wealth"] > 500 and rng.random() < .025:
                f["wealth"] -= 180
                f["estate"] = True
                f["prestige"] += .12
                events.append((y, "estate_acquired", f["id"]))
            if rng.random() < .008:
                f["wealth"] *= rng.uniform(.55, .9)
            if f["magic_rank"] == 0:
                access = .00025 + min(.0012, f["wealth"] / 2_000_000) + .00035 * (f["prestige"] > 1)
                if rng.random() < access:
                    f["magic_rank"] = 1
                    events.append((y, "family_magic_entry", f["id"]))
            elif f["magic_rank"] < 4 and rng.random() < .00018 * (1 + f["magic_rank"] * .15):
                f["magic_rank"] += 1
                events.append((y, "exceptional_rank_advance", f["id"], f["magic_rank"]))
            if rng.random() < 1 / 31:
                f["generation"] += 1
                inherited = max(0, min(1, f["lineage_attachment"] + rng.gauss(0, .11) + (.035 if f["records"] > .55 else 0) + (.025 if f["estate"] else 0)))
                f["lineage_attachment"] = inherited
                continuity = .28 + .38 * inherited + .14 * f["estate"] + .12 * min(1, f["records"]) + .08 * min(1, f["prestige"] / 2)
                if f["magic_rank"] >= 3:
                    continuity += .10
                if f["magic_rank"] >= 4:
                    continuity += .12
                if rng.random() > min(.94, continuity):
                    f["name_continuity"] = max(0, f["name_continuity"] - rng.uniform(.18, .45))
                    f["inheritance_losses"] += 1
                    f["wealth"] *= rng.uniform(.45, .78)
                    for bid in list(f["businesses"]):
                        if businesses[bid]["alive"] and rng.random() < .28:
                            businesses[bid]["alive"] = False
                            f["business_failures"] += 1
                else:
                    f["records"] = min(1, f["records"] + rng.uniform(.02, .12))
                    f["name_continuity"] = min(1, f["name_continuity"] + rng.uniform(.02, .10))
                    f["lineage_attachment"] = min(1, f["lineage_attachment"] + rng.uniform(.01, .05))
                    f["prestige"] += rng.uniform(.01, .08)
                children = max(0, round(rng.gauss(2.08, .95)))
                f["members"] = max(0, round(f["members"] * .45 + children + rng.uniform(-1, 1)))
                if f["members"] <= 0:
                    f["alive"] = False
                    events.append((y, "line_extinct", f["id"]))
                    continue
            active = sum(businesses[b]["alive"] for b in f["businesses"])
            institutional = f["estate"] + (f["records"] > .55) + (active > 0)
            if f["lineage_attachment"] > .55 and institutional >= 2 and f["wealth"] > 180:
                f["dynasty_years"] += 1
            else:
                f["dynasty_years"] = max(0, f["dynasty_years"] - .15)
            f["prestige"] = max(0, f["prestige"] * .997 + .003 * math.log1p(max(0, f["wealth"])) / 5)
            f["peak_wealth"] = max(f["peak_wealth"], f["wealth"])
        if y % 50 == 0:
            living = [f for f in fam.values() if f["alive"]]
            dyn = [f for f in living if f["dynasty_years"] >= 75 and f["name_continuity"] > .35]
            yearly.append({"year": y, "living_families": len(living), "active_businesses": sum(b["alive"] for b in businesses.values()), "dynasties": len(dyn), "new_money_dynasties": sum(not f["old_house"] for f in dyn), "old_house_dynasties": sum(f["old_house"] for f in dyn)})

    living = [f for f in fam.values() if f["alive"]]
    dyn = [f for f in living if f["dynasty_years"] >= 75 and f["name_continuity"] > .35]
    newdyn = [f for f in dyn if not f["old_house"]]
    olddyn = [f for f in dyn if f["old_house"]]
    business_dyn = [f for f in newdyn if f["business_founded"] > 0 and f["peak_wealth"] > 600]
    collapsed = [f for f in fam.values() if f["peak_wealth"] > 1000 and (not f["alive"] or f["name_continuity"] < .25 or f["wealth"] < 150)]
    return {"seed": seed, "families": fam, "businesses": businesses, "events": events, "yearly": yearly,
            "summary": {"living_families": len(living), "businesses_ever": len(businesses), "active_businesses": sum(b["alive"] for b in businesses.values()), "dynasties": len(dyn), "new_money_dynasties": len(newdyn), "old_house_dynasties": len(olddyn), "business_created_dynasties": len(business_dyn), "collapsed_once_wealthy": len(collapsed), "highest_wealth": max((f["wealth"] for f in living), default=0), "longest_business": max((b["age"] for b in businesses.values()), default=0), "highest_rank": max((f["magic_rank"] for f in living), default=0), "new_dynasty_examples": [f["id"] for f in sorted(business_dyn, key=lambda x: x["peak_wealth"], reverse=True)[:5]], "collapse_examples": [f["id"] for f in sorted(collapsed, key=lambda x: x["peak_wealth"], reverse=True)[:5]]}}
