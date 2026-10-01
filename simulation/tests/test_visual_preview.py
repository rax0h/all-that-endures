from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from ate_sim.visual_preview import PreviewStyle, render_settlement_preview
from ate_sim.visual_spec_io import load_visual_spec, visual_spec_from_dict


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "visual" / "settlement_v0.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fixture_renders_png(tmp_path):
    spec = load_visual_spec(FIXTURE)
    target = tmp_path / "preview.png"

    render_settlement_preview(spec, target, style=PreviewStyle(width=800, height=600))

    assert target.exists()
    with Image.open(target) as image:
        assert image.format == "PNG"
        assert image.size == (800, 600)


def test_render_is_deterministic_for_same_spec(tmp_path):
    spec = load_visual_spec(FIXTURE)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    style = PreviewStyle(width=640, height=480)

    render_settlement_preview(spec, first, style=style)
    render_settlement_preview(spec, second, style=style)

    assert _sha(first) == _sha(second)


def test_optional_layers_can_be_hidden(tmp_path):
    spec = load_visual_spec(FIXTURE)
    target = tmp_path / "minimal.png"

    render_settlement_preview(
        spec,
        target,
        style=PreviewStyle(width=500, height=400),
        show_people=False,
        show_labels=False,
    )

    assert target.stat().st_size > 100


def test_invalid_schema_version_is_rejected():
    with pytest.raises(ValueError, match="unsupported visual specification schema version"):
        visual_spec_from_dict(
            {
                "schema_version": "ate.visual-spec.v999",
                "settlement_id": "x",
                "world_seed": 1,
                "visual_seed": 1,
                "time_slice_year": 1,
            }
        )


def test_render_does_not_mutate_spec(tmp_path):
    spec = load_visual_spec(FIXTURE)
    before = spec.canonical_json()

    render_settlement_preview(spec, tmp_path / "preview.png")

    assert spec.canonical_json() == before
