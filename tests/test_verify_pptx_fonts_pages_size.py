import importlib.util
import json
import sys
import zipfile
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


def _pptx_with_slide(tmp_path, paragraph_xml):
    path = tmp_path / "font-slots.pptx"
    slide = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f"<p:cSld><p:spTree><p:sp><p:txBody>{paragraph_xml}</p:txBody></p:sp></p:spTree></p:cSld>"
        "</p:sld>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide)
        archive.writestr(
            "ppt/presentation.xml",
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:sldSz cx="9144000" cy="5143500"/></p:presentation>',
        )
    return path


def test_paragraph_default_font_is_checked_for_run_without_font_slot(tmp_path):
    path = _pptx_with_slide(
        tmp_path,
        '<a:p><a:pPr><a:defRPr><a:ea typeface="Chinese Face"/></a:defRPr></a:pPr>'
        '<a:r><a:t>中文</a:t></a:r></a:p>',
    )

    assert MODULE.inspect_run_font_assignments(path) == [
        {"slide": "1", "font": "Chinese Face", "slot": "ea", "text": "中文"}
    ]


def test_mixed_script_run_uses_each_applicable_font_slot(tmp_path):
    path = _pptx_with_slide(
        tmp_path,
        '<a:p><a:r><a:rPr><a:latin typeface="Latin Face"/>'
        '<a:ea typeface="Chinese Face"/><a:cs typeface="Arabic Face"/></a:rPr>'
        '<a:t>A中ع</a:t></a:r></a:p>',
    )

    assert MODULE.inspect_run_font_assignments(path) == [
        {"slide": "1", "font": "Latin Face", "slot": "latin", "text": "A"},
        {"slide": "1", "font": "Chinese Face", "slot": "ea", "text": "中"},
        {"slide": "1", "font": "Arabic Face", "slot": "cs", "text": "ع"},
    ]


def test_glyph_coverage_checks_all_applicable_slots(tmp_path, monkeypatch):
    path = _pptx_with_slide(
        tmp_path,
        '<a:p><a:r><a:rPr><a:latin typeface="Latin Face"/>'
        '<a:ea typeface="Chinese Face"/></a:rPr><a:t>A中</a:t></a:r></a:p>',
    )
    monkeypatch.setattr(
        MODULE,
        "load_font_codepoints",
        lambda font_path: {ord("中")} if font_path.name == "chinese.ttf" else set(),
    )

    result = MODULE.verify_glyph_coverage(
        path,
        {"Latin Face": tmp_path / "latin.ttf", "Chinese Face": tmp_path / "chinese.ttf"},
        True,
    )

    assert result["missing_glyphs"]["Latin Face"]["characters"] == ["A"]
    assert "Chinese Face" not in result["missing_glyphs"]


def test_unresolved_theme_font_does_not_pass_required_font_mapping(tmp_path):
    path = _pptx_with_slide(
        tmp_path,
        '<a:p><a:r><a:rPr><a:ea typeface="+mn-ea"/></a:rPr>'
        '<a:t>中文</a:t></a:r></a:p>',
    )

    result = MODULE.verify_glyph_coverage(path, {}, True)

    assert result["all_used_fonts_have_font_files"] is False
    assert result["unresolved_runs"] == [
        {"slide": 1, "slot": "ea", "text": "中文"}
    ]


def test_confirmed_delivery_font_may_be_unembedded():
    assert MODULE.unembedded_used_fonts(
        {"Custom Face", "Missing Face"},
        set(),
        {"Custom Face"},
    ) == {"Missing Face"}


def test_cli_accepts_mapped_font_confirmed_on_delivery_machine(tmp_path, monkeypatch, capsys):
    path = _pptx_with_slide(
        tmp_path,
        '<a:p><a:r><a:rPr><a:latin typeface="Custom Face"/></a:rPr><a:t>A</a:t></a:r></a:p>',
    )
    font = tmp_path / "custom.ttf"
    font.write_bytes(b"test font loading is isolated")
    report = tmp_path / "report.json"
    monkeypatch.setattr(MODULE, "load_font_codepoints", lambda _: {ord("A")})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_pptx_fonts_pages_size.py",
            "--final", str(path), "--report", str(report),
            "--font-file", f"Custom Face={font}",
            "--require-font-files-for-used-fonts",
            "--allow-unembedded-font", "Custom Face",
        ],
    )

    MODULE.main()
    capsys.readouterr()

    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["unembedded_used_typefaces"] == []
