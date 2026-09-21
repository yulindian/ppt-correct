import importlib.util
from pathlib import Path

from PIL import ImageFont


SCRIPT = Path(__file__).parents[1] / "scripts" / "match_text_style.py"
SPEC = importlib.util.spec_from_file_location("match_text_style", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_supported_text_ignores_whitespace_and_requires_every_visible_character():
    supported = {ord(char) for char in "集体生活，。"}

    assert MODULE.unsupported_characters("集体 生活。", supported) == []
    assert MODULE.unsupported_characters("集体成长。", supported) == ["成", "长"]


def test_size_search_matches_rendered_ink_height_instead_of_point_number():
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    if not font_path.exists():
        return
    reference_font = ImageFont.truetype(str(font_path), 42)
    reference_mask = MODULE.render_text_mask("Visual size", reference_font)

    result = MODULE.best_size_for_reference(
        text="Visual size",
        font_path=font_path,
        face_index=0,
        reference_mask=reference_mask,
        sizes=range(34, 50),
    )

    assert result["size_px"] == 42
    assert result["height_error"] == 0
    assert result["width_error"] == 0


def test_parse_bbox_accepts_pixel_crop_coordinates():
    assert MODULE.parse_bbox("10,20,110,80") == (10, 20, 110, 80)
