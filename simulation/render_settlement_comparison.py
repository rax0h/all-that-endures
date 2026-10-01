from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATION_DIR))

from ate_sim.engine import Simulation
from ate_sim.visual_compile import compile_settlement_visual_spec
from ate_sim.visual_preview import PreviewStyle, render_settlement_preview
from ate_sim.worldgen import generate_world


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main() -> int:
    parser = argparse.ArgumentParser(description="Render multiple seed-specific settlement layouts as one comparison image.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[843000, 843001, 731])
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument("--settlement", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    panel_w = 1200
    panel_h = 820
    header_h = 54
    gap = 22
    rendered = []

    work_dir = args.out.parent / "_comparison_parts"
    work_dir.mkdir(parents=True, exist_ok=True)

    for seed in args.seeds:
        world = generate_world(seed)
        Simulation(world).run(args.years)
        spec = compile_settlement_visual_spec(world, args.settlement)
        target = work_dir / f"seed_{seed}.png"
        render_settlement_preview(
            spec,
            target,
            style=PreviewStyle(width=panel_w, height=panel_h),
            show_people=False,
            show_labels=True,
        )
        rendered.append((seed, spec.metadata.get("site_archetype", "unknown"), target))

    canvas_h = header_h + len(rendered) * panel_h + (len(rendered) - 1) * gap
    canvas = Image.new("RGB", (panel_w, canvas_h), "#111315")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 16),
        f"ATE settlement seed comparison — year {args.years}, settlement {args.settlement}",
        fill="#f1ead9",
        font=_font(24),
    )

    y = header_h
    for seed, archetype, path in rendered:
        with Image.open(path) as panel:
            canvas.paste(panel.convert("RGB"), (0, y))
        draw.rounded_rectangle((18, y + 16, 330, y + 52), radius=8, fill="#171a1bdd")
        draw.text((32, y + 24), f"seed {seed} • {archetype}", fill="#f5dfb6", font=_font(19))
        y += panel_h + gap

    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out, "PNG")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
