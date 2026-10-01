from __future__ import annotations

import argparse
from pathlib import Path
import sys

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATION_DIR))

from ate_sim.engine import Simulation
from ate_sim.world_map_preview import WorldMapStyle, render_world_overview
from ate_sim.worldgen import generate_world


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a simulation-derived ATE world overview.")
    parser.add_argument("--seed", type=int, default=843000)
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument("--settlement", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1500)
    parser.add_argument("--height", type=int, default=1050)
    args = parser.parse_args()

    world = generate_world(args.seed)
    Simulation(world).run(args.years)
    render_world_overview(
        world,
        args.out,
        selected_settlement=args.settlement,
        style=WorldMapStyle(width=args.width, height=args.height),
    )
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
