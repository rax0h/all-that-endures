from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class WorldMapStyle:
    width: int = 1500
    height: int = 1050
    margin: int = 72
    panel_width: int = 330
    background: str = "#171a1b"
    text: str = "#f1ead9"
    muted_text: str = "#c7beaa"
    panel: str = "#242829"
    settlement_fill: str = "#f0dfb5"
    settlement_outline: str = "#1b1c1a"
    selected: str = "#f5b942"
    trade: str = "#d7b67a"
    road: str = "#7a5e3c"
    forest: str = "#234d34"
    magic: str = "#7968c6"
    hazard: str = "#9c4b32"


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def _terrain_color(cell, shade: float = 0.0) -> tuple[int, int, int, int]:
    # Diagnostic color is derived only from elevation/moisture/forest.
    low = (150, 143, 104)
    wet = (88, 129, 86)
    high = (120, 112, 98)
    moisture = max(0.0, min(1.0, cell.moisture))
    elevation = max(0.0, min(1.0, cell.elevation))
    forest = max(0.0, min(1.0, cell.forest))
    mid = tuple(_lerp(low[i], wet[i], moisture * 0.72 + forest * 0.18) for i in range(3))
    rgb = tuple(_lerp(mid[i], high[i], max(0.0, (elevation - 0.42) / 0.58)) for i in range(3))
    factor = max(0.72, min(1.22, 1.0 + shade))
    return tuple(int(max(0, min(255, c * factor))) for c in rgb) + (255,)


def _hillshade(world, x: int, y: int) -> float:
    center = world.cells[(x, y)].elevation

    def elev(nx, ny):
        cell = world.cells.get((nx, ny))
        return center if cell is None else cell.elevation

    dx = elev(x + 1, y) - elev(x - 1, y)
    dy = elev(x, y + 1) - elev(x, y - 1)
    # Pretend light comes from northwest only as a map visualization.
    return max(-0.22, min(0.22, (-dx + dy) * 0.75))


def _dash_line(draw, a, b, fill, width=2, dash=11, gap=8):
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    if length <= 0:
        return
    ux, uy = (bx - ax) / length, (by - ay) / length
    pos = 0.0
    while pos < length:
        end = min(length, pos + dash)
        draw.line(
            (ax + ux * pos, ay + uy * pos, ax + ux * end, ay + uy * end),
            fill=fill,
            width=width,
        )
        pos += dash + gap


def render_world_overview(
    world,
    output_path: str | Path,
    *,
    selected_settlement: int | None = 1,
    style: WorldMapStyle | None = None,
) -> Path:
    style = style or WorldMapStyle()
    image = Image.new("RGB", (style.width, style.height), style.background)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = _font(30)
    label_font = _font(19)
    small_font = _font(16)
    tiny_font = _font(14)

    xs = [x for x, _ in world.cells]
    ys = [y for _, y in world.cells]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    map_left = style.margin
    map_top = 120
    map_right = style.width - style.panel_width - 42
    map_bottom = style.height - style.margin
    cell_w = (map_right - map_left) / (max_x - min_x + 1)
    cell_h = (map_bottom - map_top) / (max_y - min_y + 1)

    def cell_box(x, y):
        left = map_left + (x - min_x) * cell_w
        right = left + cell_w + 1
        bottom = map_bottom - (y - min_y) * cell_h
        top = bottom - cell_h - 1
        return (left, top, right, bottom)

    def point(x, y):
        px = map_left + (x - min_x + 0.5) * cell_w
        py = map_bottom - (y - min_y + 0.5) * cell_h
        return (px, py)

    # Terrain tiles without the spreadsheet-like hard grid.
    for (x, y), cell in sorted(world.cells.items()):
        draw.rectangle(cell_box(x, y), fill=_terrain_color(cell, _hillshade(world, x, y)))

    # Forest density texture: deterministic stippling, not exact tree positions.
    for (x, y), cell in sorted(world.cells.items()):
        count = int(max(0, min(9, round(cell.forest * 8))))
        if count <= 0:
            continue
        l, t, r, b = cell_box(x, y)
        for i in range(count):
            # integer hash -> stable fractional offsets
            h = (world.seed * 1103515245 + x * 2654435761 + y * 2246822519 + i * 3266489917) & 0xFFFFFFFF
            fx = 0.14 + ((h & 0xFFFF) / 65535.0) * 0.72
            fy = 0.14 + (((h >> 16) & 0xFFFF) / 65535.0) * 0.72
            px = l + (r - l) * fx
            py = t + (b - t) * fy
            rad = max(1.2, min(cell_w, cell_h) * 0.045)
            draw.ellipse((px - rad, py - rad, px + rad, py + rad), fill=style.forest + "80")

    # Physical roads are simulation infrastructure.
    road_pairs = {}
    for asset in world.infrastructure.assets.values():
        if asset.kind != "road" or len(asset.settlements) != 2:
            continue
        a, b = asset.settlements
        road_pairs[tuple(sorted((a, b)))] = asset
    for (a, b), asset in sorted(road_pairs.items()):
        sa, sb = world.settlements[a], world.settlements[b]
        pa, pb = point(sa.x, sa.y), point(sb.x, sb.y)
        draw.line((pa[0], pa[1], pb[0], pb[1]), fill=style.road, width=max(3, round(3 + 4 * asset.condition)))

    # Trade routes are social/economic connections; dashed so they are not mistaken for roads.
    for (a, b), route in sorted(world.trade_routes.items()):
        sa, sb = world.settlements[a], world.settlements[b]
        pa, pb = point(sa.x, sa.y), point(sb.x, sb.y)
        _dash_line(
            draw,
            pa,
            pb,
            style.trade,
            width=max(2, round(1 + route.strength * 6)),
            dash=13,
            gap=8,
        )

    living_by_settlement = {sid: 0 for sid in world.settlements}
    for person in world.people.values():
        if person.alive:
            living_by_settlement[person.settlement] += 1

    # Settlements, with ambient magic halo and size by living population.
    for sid, settlement in sorted(world.settlements.items()):
        px, py = point(settlement.x, settlement.y)
        population = living_by_settlement[sid]
        radius = 9 + min(16, math.sqrt(max(1, population)) * 0.75)
        ambient = world.ambient_magic.field(sid).level
        halo = radius + 8 + ambient * 12
        draw.ellipse(
            (px - halo, py - halo, px + halo, py + halo),
            outline=style.magic + "90",
            width=max(2, round(2 + ambient * 3)),
        )
        outline = style.selected if sid == selected_settlement else style.settlement_outline
        outline_w = 5 if sid == selected_settlement else 3
        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill=style.settlement_fill,
            outline=outline,
            width=outline_w,
        )
        draw.text((px + radius + 7, py - 12), f"S{sid}", font=label_font, fill=style.text)
        draw.text((px + radius + 7, py + 10), f"pop {population}", font=tiny_font, fill=style.muted_text)

    # Frame + title.
    draw.rounded_rectangle(
        (map_left - 16, map_top - 16, map_right + 16, map_bottom + 16),
        radius=18,
        outline="#5d625d",
        width=2,
    )
    draw.text((style.margin, 38), f"ATE world overview — seed {world.seed}, year {world.year}", font=title_font, fill=style.text)
    draw.text(
        (style.margin, 80),
        "simulation-derived geography, settlements, trade and roads • terrain styling is interpretive",
        font=small_font,
        fill=style.muted_text,
    )

    # Side panel.
    panel_x = style.width - style.panel_width + 8
    draw.rounded_rectangle(
        (panel_x, 120, style.width - 24, style.height - style.margin),
        radius=18,
        fill=style.panel,
        outline="#5d625d",
        width=2,
    )
    draw.text((panel_x + 22, 145), "World state", font=label_font, fill=style.text)

    routes = len(world.trade_routes)
    roads = len(road_pairs)
    population_total = sum(living_by_settlement.values())
    facts = [
        ("settlements", len(world.settlements)),
        ("living population", population_total),
        ("trade routes", routes),
        ("physical roads", roads),
    ]
    y = 184
    for key, value in facts:
        draw.text((panel_x + 22, y), key, font=tiny_font, fill=style.muted_text)
        draw.text((style.width - 50, y), str(value), font=tiny_font, fill=style.text, anchor="ra")
        y += 25

    if selected_settlement in world.settlements:
        s = world.settlements[selected_settlement]
        local = world.local[selected_settlement]
        ambient = world.ambient_magic.field(selected_settlement)
        cell = world.cells[(s.x, s.y)]
        y += 16
        draw.line((panel_x + 22, y, style.width - 46, y), fill="#5d625d", width=1)
        y += 18
        draw.text((panel_x + 22, y), f"Selected: settlement {selected_settlement}", font=label_font, fill=style.selected)
        y += 35
        selected_facts = [
            ("population", living_by_settlement[selected_settlement]),
            ("prosperity", f"{s.prosperity:.3f}"),
            ("food stock", f"{s.food_stock:.1f}"),
            ("defense", f"{s.defense:.3f}"),
            ("irrigation", f"{s.irrigation:.3f}"),
            ("roads index", f"{s.roads:.3f}"),
            ("rain", f"{local.rain:.3f}"),
            ("flood", f"{local.flood:.3f}"),
            ("scarcity", f"{local.scarcity:.3f}"),
            ("ambient magic", f"{ambient.level:.3f}"),
            ("forest", f"{cell.forest:.3f}"),
            ("hazard", f"{cell.hazard:.3f}"),
        ]
        for key, value in selected_facts:
            draw.text((panel_x + 22, y), key, font=tiny_font, fill=style.muted_text)
            draw.text((style.width - 50, y), str(value), font=tiny_font, fill=style.text, anchor="ra")
            y += 23

    # Legend.
    y = style.height - 214
    draw.text((panel_x + 22, y), "Legend", font=label_font, fill=style.text)
    y += 31
    legend = [
        ("forest density", style.forest),
        ("trade route", style.trade),
        ("physical road", style.road),
        ("ambient magic", style.magic),
        ("selected settlement", style.selected),
    ]
    for label, color in legend:
        draw.rectangle((panel_x + 24, y + 4, panel_x + 40, y + 16), fill=color)
        draw.text((panel_x + 50, y), label, font=tiny_font, fill=style.muted_text)
        y += 25

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, "PNG", optimize=False)
    return target
