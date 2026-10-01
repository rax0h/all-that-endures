from __future__ import annotations

import argparse
from pathlib import Path
import sys

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATION_DIR))

from ate_sim.engine import Simulation
from ate_sim.visual_compile import compile_settlement_visual_spec
from ate_sim.visual_preview import PreviewStyle, render_settlement_preview
from ate_sim.visual_spec_io import save_visual_spec
from ate_sim.worldgen import generate_world


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate a world, compile one real settlement, and render a truth-only debug map."
    )
    parser.add_argument("--seed", type=int, default=843000)
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument("--settlement", type=int, default=1)
    parser.add_argument("--radius-cells", type=int, default=5)
    parser.add_argument("--out-spec", type=Path, required=True)
    parser.add_argument("--out-map", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    world = generate_world(args.seed)
    Simulation(world).run(args.years)
    spec = compile_settlement_visual_spec(world, args.settlement, args.radius_cells)
    save_visual_spec(spec, args.out_spec)
    render_settlement_preview(
        spec,
        args.out_map,
        style=PreviewStyle(width=args.width, height=args.height),
        show_people=False,
        show_labels=True,
    )
    print(f"spec={args.out_spec}")
    print(f"map={args.out_map}")
    print(f"digest={spec.digest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
