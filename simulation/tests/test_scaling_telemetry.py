from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world
from scaling_telemetry import ScalingTelemetry, bucket_end

def test_telemetry_preserves_deterministic_world_and_restores_engine():
    plain = generate_world(843000)
    measured = generate_world(843000)
    original = Simulation._people
    Simulation(plain).run(3)
    with ScalingTelemetry(measured) as telemetry:
        Simulation(measured).run(3)
        report = telemetry.report(1, 1.0)
        assert report["subsystem_calls"]["_people"] == 3
        assert report["subsystem_calls"]["magic_ecology_step"] == 3
        assert report["collections"]["events"] == len(measured.events)
    assert Simulation._people is original
    assert plain.digest() == measured.digest()

def test_bucket_boundaries():
    assert [bucket_end(y) for y in (1,100,101,250,251,500,501,750,751,1000,1001)] == [100,100,250,250,500,500,750,750,1000,1000,1250]

def test_telemetry_restores_after_exception():
    original = Simulation._people
    try:
        with ScalingTelemetry(generate_world(843000)):
            raise RuntimeError("test")
    except RuntimeError:
        pass
    assert Simulation._people is original
