#!/usr/bin/env python3
"""Build a reusable catalog of installed font faces for ppt-correct."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".otc"}


def _contains_cjk(codepoints: set[int]) -> bool:
    ranges = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))
    return any(start <= point <= end for point in codepoints for start, end in ranges)


def make_record(
    path: Path,
    face_index: int,
    names: dict[str, str],
    weight_class: int,
    italic: bool,
    codepoints: set[int],
) -> dict:
    """Return the stable, machine-readable metadata used by the matcher."""
    return {
        "path": str(path.resolve()),
        "face_index": face_index,
        "family": names.get("family", "") or path.stem,
        "subfamily": names.get("subfamily", "") or "Regular",
        "postscript": names.get("postscript", ""),
        "weight_class": int(weight_class or 400),
        "italic": bool(italic),
        "coverage_count": len(codepoints),
        "supports_cjk": _contains_cjk(codepoints),
    }


def _decode_name(record) -> str:
    try:
        return record.toUnicode().strip()
    except Exception:
        encoding = record.getEncoding() or "utf-16-be"
        return record.string.decode(encoding, errors="replace").strip()


def _font_names(font) -> dict[str, str]:
    name_ids = {1: "family", 2: "subfamily", 6: "postscript"}
    collected: dict[str, list[tuple[int, str]]] = {value: [] for value in name_ids.values()}
    if "name" not in font:
        return {}
    for record in font["name"].names:
        key = name_ids.get(record.nameID)
        if not key:
            continue
        priority = 0 if record.langID in {0x804, 0x409} else 1
        value = _decode_name(record)
        if value:
            collected[key].append((priority, value))
    return {
        key: sorted(values, key=lambda item: item[0])[0][1]
        for key, values in collected.items()
        if values
    }


def _codepoints(font) -> set[int]:
    if "cmap" not in font:
        return set()
    result: set[int] = set()
    for table in font["cmap"].tables:
        result.update(table.cmap)
    return result


def records_for_font(path: Path) -> list[dict]:
    from fontTools.ttLib import TTCollection, TTFont

    records = []
    if path.suffix.lower() in {".ttc", ".otc"}:
        collection = TTCollection(str(path), lazy=True)
        fonts = collection.fonts
    else:
        collection = None
        fonts = [TTFont(str(path), lazy=True)]
    try:
        for index, font in enumerate(fonts):
            os2 = font.get("OS/2")
            head = font.get("head")
            weight = getattr(os2, "usWeightClass", 400)
            italic = bool(getattr(head, "macStyle", 0) & 0x02)
            records.append(
                make_record(path, index, _font_names(font), weight, italic, _codepoints(font))
            )
    finally:
        if collection is not None:
            collection.close()
        else:
            fonts[0].close()
    return records


def discover_font_files(font_dirs: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for directory in font_dirs:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in FONT_SUFFIXES:
                files.add(path.resolve())
    return sorted(files, key=lambda item: str(item).lower())


def build_catalog(font_dirs: list[Path]) -> dict:
    records = []
    errors = []
    for path in discover_font_files(font_dirs):
        try:
            records.extend(records_for_font(path))
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    records.sort(key=lambda item: (item["family"].casefold(), item["weight_class"], item["path"], item["face_index"]))
    return {
        "schema_version": 1,
        "font_directories": [str(path.resolve()) for path in font_dirs],
        "font_file_count": len({record["path"] for record in records}),
        "face_count": len(records),
        "fonts": records,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font-dir", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    font_dirs = args.font_dir or [Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts"]
    catalog = build_catalog(font_dirs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: catalog[key] for key in ("font_file_count", "face_count", "errors")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
