from __future__ import annotations

import argparse
from pathlib import Path
import sys

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATION_DIR))

from ate_sim.visual_preview import PreviewStyle, render_settlement_preview
from ate_sim.visual_spec_io import load_visual_spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an ATE visual specification as a debug PNG map.")
    parser.add_argument("spec", type=Path, help="Path to a SettlementVisualSpec JSON file.")
    parser.add_argument("--out", type=Path, required=True, help="PNG output path.")
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--no-people", action="store_true")
    parser.add_argument("--no-labels", action="store_true")
    args = parser.parse_args()

    spec = load_visual_spec(args.spec)
    style = PreviewStyle(width=args.width, height=args.height)
    output = render_settlement_preview(
        spec,
        args.out,
        style=style,
        show_people=not args.no_people,
        show_labels=not args.no_labels,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
