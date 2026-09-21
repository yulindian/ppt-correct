import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_pptx_fonts_pages_size.py"
SPEC = importlib.util.spec_from_file_location("ppt_verify", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_missing_characters_reports_only_uncovered_visible_glyphs():
    supported = {ord(char) for char in "答案：× "}

    assert MODULE.missing_characters("答案：× ✔ ✔\n", supported) == ["✔"]


def test_parse_font_file_args_keeps_family_names_with_spaces(tmp_path):
    font_file = tmp_path / "msyh.ttc"
    font_file.write_bytes(b"placeholder")

    result = MODULE.parse_font_file_args([f"Microsoft YaHei={font_file}"])

    assert result == {"Microsoft YaHei": font_file.resolve()}


def test_load_visual_report_requires_all_regions_to_pass(tmp_path):
    report = tmp_path / "visual.json"
    report.write_text(
        '{"passed": false, "regions": [{"id": "title", "passed": false}], '
        '"exception_ledger": [{"id": "title"}]}',
        encoding="utf-8",
    )

    result = MODULE.load_visual_report(report)

    assert result["passed"] is False
    assert result["region_count"] == 1
    assert result["exception_count"] == 1
