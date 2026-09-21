import importlib.util
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
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


def _make_test_font(path: Path) -> None:
    blank = TTGlyphPen(None).glyph()
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.lineTo((500, 0))
    pen.lineTo((500, 700))
    pen.lineTo((50, 700))
    pen.closePath()

    font = FontBuilder(1000, isTTF=True)
    font.setupGlyphOrder([".notdef", "space", "block"])
    font.setupCharacterMap({ord(char): "block" for char in "Visualsize"} | {32: "space"})
    font.setupGlyf({".notdef": blank, "space": blank, "block": pen.glyph()})
    font.setupHorizontalMetrics({".notdef": (600, 0), "space": (300, 0), "block": (600, 50)})
    font.setupHorizontalHeader(ascent=800, descent=-200)
    font.setupNameTable({"familyName": "PptCorrectTest", "styleName": "Regular"})
    font.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    font.setupPost()
    font.save(path)


def test_size_search_matches_rendered_ink_height_instead_of_point_number(tmp_path):
    font_path = tmp_path / "test-font.ttf"
    _make_test_font(font_path)
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
