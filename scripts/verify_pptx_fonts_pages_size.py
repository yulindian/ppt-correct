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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", type=Path, required=True, help="Corrected final PPTX")
    parser.add_argument("--report", type=Path, required=True, help="JSON report path")
    parser.add_argument("--source-dir", type=Path, help="Optional directory containing page-####.pptx source decks")
    parser.add_argument("--expected-slide-count", type=int, help="Expected final slide count, usually PDF page count")
    parser.add_argument("--system-fonts", help="Comma-separated font families allowed without embedding")
    parser.add_argument("--allow-unembedded-system-fonts", action="store_true", help="Ignore unembedded fonts listed in --system-fonts")
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
    unembedded_used = final_used - final_embedded
    if args.allow_unembedded_system_fonts:
        unembedded_used -= parse_font_list(args.system_fonts)
    checks["all_directly_used_typefaces_embedded"] = not unembedded_used

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
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
