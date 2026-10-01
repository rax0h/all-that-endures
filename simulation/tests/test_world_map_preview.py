from pathlib import Path

from PIL import Image

from ate_sim.engine import Simulation
from ate_sim.world_map_preview import render_world_overview
from ate_sim.worldgen import generate_world


def test_world_overview_renders_real_world_state(tmp_path):
    world = generate_world(843000)
    Simulation(world).run(5)
    target = tmp_path / "overview.png"

    render_world_overview(world, target, selected_settlement=1)

    assert target.exists()
    with Image.open(target) as image:
        assert image.format == "PNG"
        assert image.width > image.height


def test_world_overview_does_not_mutate_world(tmp_path):
    world = generate_world(843000)
    Simulation(world).run(5)
    before = world.digest()

    render_world_overview(world, tmp_path / "overview.png", selected_settlement=1)

    assert world.digest() == before
