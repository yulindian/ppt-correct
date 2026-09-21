import importlib.util
import math
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_visual_regions.py"
SPEC = importlib.util.spec_from_file_location("verify_visual_regions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _slide(with_highlight: bool) -> Image.Image:
    image = Image.new("RGB", (120, 80), "white")
    draw = ImageDraw.Draw(image)
    if with_highlight:
        draw.rounded_rectangle((15, 30, 105, 58), radius=8, fill=(221, 232, 176))
    draw.rectangle((35, 38, 85, 49), fill=(55, 82, 49))
    return image


def test_identical_highlight_region_passes_geometry_color_and_presence():
    metrics = MODULE.compare_region(
        reference=_slide(True),
        candidate=_slide(True),
        reference_bbox=(10, 25, 110, 65),
        candidate_bbox=(10, 25, 110, 65),
        target_rgb=(221, 232, 176),
        tolerance=8,
    )

    verdict = MODULE.evaluate_metrics(metrics, kind="background")

    assert verdict["passed"] is True
    assert verdict["failures"] == []


def test_color_delta_uses_perceptual_lab_distance():
    assert MODULE.color_delta_e((255, 255, 255), (255, 255, 255)) == 0
    assert MODULE.color_delta_e((0, 0, 0), (255, 255, 255)) > 90


def test_missing_highlight_is_a_hard_failure_even_when_text_remains():
    metrics = MODULE.compare_region(
        reference=_slide(True),
        candidate=_slide(False),
        reference_bbox=(10, 25, 110, 65),
        candidate_bbox=(10, 25, 110, 65),
        target_rgb=(221, 232, 176),
        tolerance=8,
    )

    verdict = MODULE.evaluate_metrics(metrics, kind="background")

    assert verdict["passed"] is False
    assert "required visual layer is missing" in verdict["failures"]
    assert math.isfinite(metrics["centroid_distance_px"])
    assert math.isfinite(metrics["color_delta"])
