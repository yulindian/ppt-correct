#!/usr/bin/env python3
"""Verify PPTX slide count, slide size, and embedded-font coverage.

Use this after ppt-correct has produced a corrected PPTX. It can verify a single
final deck, or compare a merged final deck against a directory of page-####.pptx
source decks.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
FONT_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"

DEFAULT_SYSTEM_FONTS = {
    "Arial",
    "Calibri",
    "Cambria",
    "Courier New",
    "Microsoft JhengHei",
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "Times New Roman",
}


def missing_characters(text: str, supported_codepoints: set[int]) -> list[str]:
    """Return unique visible characters that the selected font cannot draw."""
    missing = {
        char
        for char in text
        if not char.isspace()
        and unicodedata.category(char) not in {"Cc", "Cf"}
        and ord(char) not in supported_codepoints
    }
    return sorted(missing, key=ord)


def parse_font_file_args(values: list[str] | None) -> dict[str, Path]:
    """Parse repeatable FAMILY=PATH mappings used for glyph-coverage checks."""
    result: dict[str, Path] = {}
    for value in values or []:
        family, separator, raw_path = value.partition("=")
        family = family.strip()
        raw_path = raw_path.strip()
        if not separator or not family or not raw_path:
            raise ValueError(f"Invalid --font-file mapping: {value!r}; expected FAMILY=PATH")
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Font file for {family!r} does not exist: {path}")
        result[family] = path
    return result


def load_visual_report(path: Path) -> dict:
    """Load the region verifier output and expose stable summary fields."""
    if not path.is_file():
        raise FileNotFoundError(f"Visual verification report does not exist: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    regions = data.get("regions", [])
    exceptions = data.get("exception_ledger", [])
    passed = bool(data.get("passed")) and all(bool(item.get("passed")) for item in regions)
    return {
        "path": str(path.resolve()),
        "passed": passed,
        "region_count": len(regions),
        "exception_count": len(exceptions),
        "exception_ledger": exceptions,
    }


def load_font_codepoints(path: Path) -> set[int]:
    """Load the union of Unicode cmap entries from a TTF/OTF/TTC font file."""
    try:
        from fontTools.ttLib import TTCollection, TTFont
    except ImportError as exc:
        raise RuntimeError(
            "Glyph coverage checks require fontTools. Install it with: python -m pip install fonttools"
        ) from exc

    fonts = TTCollection(str(path)).fonts if path.suffix.lower() == ".ttc" else [TTFont(str(path))]
    codepoints: set[int] = set()
    try:
        for font in fonts:
            for table in font["cmap"].tables:
                codepoints.update(table.cmap)
    finally:
        for font in fonts:
            font.close()
    return codepoints


def _font_slot(char: str) -> str:
    """Choose the OOXML font slot normally used for this visible character."""
    if unicodedata.east_asian_width(char) in {"W", "F"}:
        return "ea"
    if unicodedata.bidirectional(char) in {"R", "AL", "AN"}:
        return "cs"
    name = unicodedata.name(char, "")
    if name.startswith(("DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "TAMIL", "TELUGU", "KANNADA", "MALAYALAM", "THAI")):
        return "cs"
    return "latin"


def _font_slots(properties: ET.Element | None) -> dict[str, str]:
    if properties is None:
        return {}
    return {
        slot: node.get("typeface")
        for slot in ("latin", "ea", "cs")
        if (node := properties.find(f"{{{A_NS}}}{slot}")) is not None and node.get("typeface")
    }


def inspect_run_font_assignments(path: Path) -> list[dict[str, str | None]]:
    """Resolve slide-local run, paragraph, and list-style fonts by script slot.

    Theme/master fonts cannot be resolved from slide XML alone and are returned
    with font=None so a required-mapping check cannot pass silently.
    """
    assignments: list[dict[str, str | None]] = []
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            (
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ),
            key=lambda name: int(re.search(r"(\d+)", Path(name).stem).group(1)),
        )
        for slide_name in slide_names:
            slide_number = int(re.search(r"slide(\d+)\.xml", slide_name).group(1))
            slide_root = ET.fromstring(archive.read(slide_name))
            for body in slide_root.iter():
                if body.tag not in {f"{{{P_NS}}}txBody", f"{{{A_NS}}}txBody"}:
                    continue
                list_style = body.find(f"{{{A_NS}}}lstStyle")
                for paragraph in body.findall(f"{{{A_NS}}}p"):
                    paragraph_properties = paragraph.find(f"{{{A_NS}}}pPr")
                    level = 0 if paragraph_properties is None else int(paragraph_properties.get("lvl", "0"))
                    style_properties = None if list_style is None else list_style.find(f"{{{A_NS}}}lvl{level + 1}pPr/{{{A_NS}}}defRPr")
                    paragraph_default = None if paragraph_properties is None else paragraph_properties.find(f"{{{A_NS}}}defRPr")
                    inherited = _font_slots(style_properties)
                    inherited.update(_font_slots(paragraph_default))
                    for run in paragraph:
                        if run.tag not in {f"{{{A_NS}}}r", f"{{{A_NS}}}fld"}:
                            continue
                        text = "".join(node.text or "" for node in run.findall(f"{{{A_NS}}}t"))
                        if not text:
                            continue
                        fonts = inherited | _font_slots(run.find(f"{{{A_NS}}}rPr"))
                        by_slot = {slot: "" for slot in ("latin", "ea", "cs")}
                        for char in text:
                            if not char.isspace() and unicodedata.category(char) not in {"Cc", "Cf"}:
                                by_slot[_font_slot(char)] += char
                        for slot, slot_text in by_slot.items():
                            if not slot_text:
                                continue
                            family = fonts.get(slot)
                            if family and family.startswith("+"):
                                family = None
                            assignments.append({"slide": str(slide_number), "font": family, "slot": slot, "text": slot_text})
    return assignments


def inspect_normal_autofit_textboxes(path: Path) -> list[dict[str, object]]:
    """List text shapes whose size is delegated to application-specific normAutofit."""
    findings: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            (
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ),
            key=lambda name: int(re.search(r"(\d+)", Path(name).stem).group(1)),
        )
        for slide_name in slide_names:
            slide_number = int(re.search(r"slide(\d+)\.xml", slide_name).group(1))
            slide_root = ET.fromstring(archive.read(slide_name))
            for shape in slide_root.findall(f".//{{{P_NS}}}sp"):
                body_properties = shape.find(f"{{{P_NS}}}txBody/{{{A_NS}}}bodyPr")
                if body_properties is None or body_properties.find(f"{{{A_NS}}}normAutofit") is None:
                    continue
                text = "".join(node.text or "" for node in shape.findall(f".//{{{A_NS}}}t")).strip()
                if not text:
                    continue
                shape_info = shape.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
                findings.append(
                    {
                        "slide": slide_number,
                        "shape_id": None if shape_info is None else shape_info.get("id"),
                        "shape_name": None if shape_info is None else shape_info.get("name"),
                        "text": text,
                    }
                )
    return findings


def verify_glyph_coverage(
    path: Path,
    font_files: dict[str, Path],
    require_font_files_for_used_fonts: bool,
) -> dict:
    assignments = inspect_run_font_assignments(path)
    used_fonts = {item["font"] for item in assignments if item["font"]}
    unmapped_fonts = sorted(used_fonts - set(font_files))
    unresolved_runs = [
        {"slide": int(item["slide"]), "slot": item["slot"], "text": item["text"]}
        for item in assignments if not item["font"]
    ]
    codepoints_by_font = {
        family: load_font_codepoints(font_path)
        for family, font_path in font_files.items()
    }
    missing_by_font: dict[str, dict[str, object]] = {}
    checked_runs = 0
    for item in assignments:
        family = item["font"]
        if not family or family not in codepoints_by_font:
            continue
        checked_runs += 1
        missing = missing_characters(item["text"], codepoints_by_font[family])
        if not missing:
            continue
        entry = missing_by_font.setdefault(family, {"characters": set(), "samples": []})
        entry["characters"].update(missing)
        if len(entry["samples"]) < 8:
            entry["samples"].append({"slide": int(item["slide"]), "text": item["text"]})

    serializable_missing = {
        family: {
            "characters": sorted(entry["characters"], key=ord),
            "samples": entry["samples"],
        }
        for family, entry in sorted(missing_by_font.items())
    }
    return {
        "font_files": {family: str(font_path) for family, font_path in font_files.items()},
        "checked_runs": checked_runs,
        "explicit_run_count": len(assignments),
        "unmapped_used_fonts": unmapped_fonts,
        "unresolved_runs": unresolved_runs,
        "missing_glyphs": serializable_missing,
        "all_used_fonts_have_font_files": not (unmapped_fonts or unresolved_runs) if require_font_files_for_used_fonts else True,
        "all_run_characters_supported": not (serializable_missing or unresolved_runs),
    }


def inspect_pptx(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        size = presentation.find(f"{{{P_NS}}}sldSz")
        if size is None:
            raise RuntimeError(f"Missing slide size in {path}")

        typefaces = []
        for embedded in presentation.findall(f".//{{{P_NS}}}embeddedFont"):
            font = embedded.find(f"{{{P_NS}}}font")
            if font is not None and font.get("typeface"):
                typefaces.append(font.get("typeface"))

        slides = sorted(
            name for name in names
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        used_typefaces = set()
        text_object_count = 0
        for slide_name in slides:
            slide_root = ET.fromstring(archive.read(slide_name))
            text_object_count += len(slide_root.findall(f".//{{{A_NS}}}t"))
            for tag in ("latin", "ea", "cs"):
                for node in slide_root.findall(f".//{{{A_NS}}}{tag}"):
                    family = node.get("typeface")
                    if family and not family.startswith("+"):
                        used_typefaces.add(family)

        font_payloads = [
            name for name in names
            if name.startswith("ppt/fonts/") and not name.endswith("/")
        ]
        rel_path = "ppt/_rels/presentation.xml.rels"
        font_relationship_count = 0
        if rel_path in names:
            rel_root = ET.fromstring(archive.read(rel_path))
            font_relationship_count = sum(
                1 for node in rel_root.findall(f"{{{REL_NS}}}Relationship")
                if node.get("Type") == FONT_REL
            )

        return {
            "path": str(path.resolve()),
            "slides": len(slides),
            "width": int(size.get("cx")),
            "height": int(size.get("cy")),
            "embedded_typefaces": sorted(typefaces),
            "used_typefaces": sorted(used_typefaces),
            "text_object_count": text_object_count,
            "font_payload_count": len(font_payloads),
            "font_relationship_count": font_relationship_count,
        }


def parse_font_list(value: str | None) -> set[str]:
    if not value:
        return set(DEFAULT_SYSTEM_FONTS)
    return {item.strip() for item in value.split(",") if item.strip()}


def unembedded_used_fonts(used: set[str], embedded: set[str], confirmed_available: set[str]) -> set[str]:
    """Return used faces neither embedded nor confirmed on the delivery machine."""
    return used - embedded - confirmed_available


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", type=Path, required=True, help="Corrected final PPTX")
    parser.add_argument("--report", type=Path, required=True, help="JSON report path")
    parser.add_argument("--source-dir", type=Path, help="Optional directory containing page-####.pptx source decks")
    parser.add_argument("--expected-slide-count", type=int, help="Expected final slide count, usually PDF page count")
    parser.add_argument("--system-fonts", help="Comma-separated font families allowed without embedding")
    parser.add_argument("--allow-unembedded-system-fonts", action="store_true", help="Ignore unembedded fonts listed in --system-fonts")
    parser.add_argument(
        "--allow-unembedded-font",
        action="append",
        default=[],
        metavar="FAMILY",
        help="Repeat for a font confirmed installed in the delivery environment",
    )
    parser.add_argument(
        "--font-file",
        action="append",
        default=[],
        metavar="FAMILY=PATH",
        help="Repeatable mapping used to verify that every run character exists in its assigned font",
    )
    parser.add_argument(
        "--require-font-files-for-used-fonts",
        action="store_true",
        help="Fail when a directly assigned run font has no --font-file mapping",
    )
    parser.add_argument("--visual-report", type=Path, help="JSON emitted by verify_visual_regions.py")
    parser.add_argument(
        "--require-visual-report",
        action="store_true",
        help="Fail unless a passing region-level visual report is supplied",
    )
    parser.add_argument(
        "--fail-on-normal-autofit",
        action="store_true",
        help="Fail when a text shape uses normAutofit, whose rendering can vary across PowerPoint, WPS, and headless renderers",
    )
    args = parser.parse_args()

    final = inspect_pptx(args.final)
    sources = []
    if args.source_dir:
        source_paths = sorted(args.source_dir.glob("page-*.pptx"))
        if not source_paths:
            raise SystemExit(f"No page-*.pptx files found in {args.source_dir}")
        sources = [inspect_pptx(path) for path in source_paths]

    expected_count = args.expected_slide_count
    if expected_count is None and sources:
        expected_count = len(sources)

    checks: dict[str, bool | None] = {
        "final_slide_count_matches_expected": None if expected_count is None else final["slides"] == expected_count,
        "final_has_slide_size": final["width"] > 0 and final["height"] > 0,
        "final_has_editable_text": final["text_object_count"] > 0,
        "embedded_font_relationships_present": (not final["embedded_typefaces"]) or final["font_relationship_count"] > 0,
    }

    source_fonts = Counter()
    missing_fonts = {}
    source_size = None
    if sources:
        source_size = (sources[0]["width"], sources[0]["height"])
        checks["source_slide_sizes_identical"] = all((item["width"], item["height"]) == source_size for item in sources)
        checks["final_slide_size_matches_source"] = (final["width"], final["height"]) == source_size
        source_fonts = Counter(font for item in sources for font in item["embedded_typefaces"])
        final_fonts = Counter(final["embedded_typefaces"])
        missing_fonts = {
            font: count - final_fonts[font]
            for font, count in source_fonts.items()
            if final_fonts[font] < count
        }
        checks["embedded_typefaces_preserved"] = not missing_fonts

    final_used = set(final["used_typefaces"])
    final_embedded = set(final["embedded_typefaces"])
    confirmed_available = set(args.allow_unembedded_font)
    if args.allow_unembedded_system_fonts:
        confirmed_available.update(parse_font_list(args.system_fonts))
    unembedded_used = unembedded_used_fonts(final_used, final_embedded, confirmed_available)
    checks["all_directly_used_typefaces_embedded"] = not unembedded_used

    normal_autofit_textboxes = inspect_normal_autofit_textboxes(args.final)
    if args.fail_on_normal_autofit:
        checks["no_application_dependent_normal_autofit"] = not normal_autofit_textboxes

    glyph_coverage = None
    if args.font_file or args.require_font_files_for_used_fonts:
        try:
            font_files = parse_font_file_args(args.font_file)
            glyph_coverage = verify_glyph_coverage(
                args.final,
                font_files,
                args.require_font_files_for_used_fonts,
            )
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise SystemExit(str(exc)) from exc
        checks["all_used_fonts_have_font_files"] = glyph_coverage["all_used_fonts_have_font_files"]
        checks["all_run_characters_supported_by_assigned_fonts"] = glyph_coverage["all_run_characters_supported"]

    visual_verification = None
    if args.visual_report:
        try:
            visual_verification = load_visual_report(args.visual_report)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise SystemExit(str(exc)) from exc
        checks["visual_regions_pass"] = visual_verification["passed"]
        checks["visual_regions_present"] = visual_verification["region_count"] > 0
    elif args.require_visual_report:
        checks["visual_regions_pass"] = False
        checks["visual_regions_present"] = False

    evaluated_checks = {key: value for key, value in checks.items() if value is not None}
    report = {
        "passed": all(evaluated_checks.values()),
        "checks": checks,
        "final": final,
        "expected_slide_count": expected_count,
        "source_count": len(sources),
        "source_slide_size": None if source_size is None else {"width": source_size[0], "height": source_size[1]},
        "source_embedded_typefaces": dict(source_fonts),
        "missing_embedded_typefaces": missing_fonts,
        "unembedded_used_typefaces": sorted(unembedded_used),
        "normal_autofit_textboxes": normal_autofit_textboxes,
        "glyph_coverage": glyph_coverage,
        "visual_verification": visual_verification,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
