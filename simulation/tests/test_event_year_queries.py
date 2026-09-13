from simulation.ate_sim.core import World, Layer

def test_year_queries_match_archive_and_include_new_events():
    world = World(1)
    for year in (0,0,1,1,3,3,10):
        world.year = year
        world.emit("test",Layer.REALITY)
    for first,last in ((0,0),(1,3),(2,9),(10,10),(-1,20),(4,2),(11,20)):
        assert world.events_between(first,last) == [e for e in world.events if first<=e.year<=last]
    world.emit("another",Layer.REALITY)
    assert len(world.events_between(10)) == 2
    assert len(world.events) == 8

def test_recent_query_does_not_iterate_historical_archive():
    world = World(1)
    for year in range(10000):
        world.year = year
        world.emit("test",Layer.REALITY)
    class NoIteration(list):
        def __iter__(self): raise AssertionError("historical event iteration")
    world.events = NoIteration(world.events)
    assert len(world.events_between(9998,9999)) == 2
