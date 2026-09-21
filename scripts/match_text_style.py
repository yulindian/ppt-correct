#!/usr/bin/env python3
"""Rank font faces and rendered sizes against a cropped PDF text reference."""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def unsupported_characters(text: str, supported_codepoints: set[int]) -> list[str]:
    missing = {
        char for char in text
        if not char.isspace()
        and unicodedata.category(char) not in {"Cc", "Cf"}
        and ord(char) not in supported_codepoints
    }
    return sorted(missing, key=ord)


def load_codepoints(path: Path, face_index: int) -> set[int]:
    from fontTools.ttLib import TTFont

    font = TTFont(str(path), fontNumber=face_index, lazy=True)
    try:
        points: set[int] = set()
        for table in font["cmap"].tables:
            points.update(table.cmap)
        return points
    finally:
        font.close()


def render_text_mask(text: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    probe = Image.new("L", (8, 8), 0)
    bbox = ImageDraw.Draw(probe).multiline_textbbox((0, 0), text, font=font, spacing=0)
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])
    image = Image.new("L", (width + 8, height + 8), 0)
    ImageDraw.Draw(image).multiline_text((4 - bbox[0], 4 - bbox[1]), text, font=font, fill=255, spacing=0)
    return trim_mask(image)


def trim_mask(mask: Image.Image) -> Image.Image:
    array = np.asarray(mask.convert("L"))
    points = np.argwhere(array > 16)
    if not len(points):
        return Image.new("L", (1, 1), 0)
    y0, x0 = points.min(axis=0)
    y1, x1 = points.max(axis=0) + 1
    return Image.fromarray(array[y0:y1, x0:x1])


def _mask_metrics(mask: Image.Image) -> dict[str, float]:
    array = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
    return {
        "width": float(mask.width),
        "height": float(mask.height),
        "density": float(array.mean()) if array.size else 0.0,
    }


def _shape_similarity(left: Image.Image, right: Image.Image) -> float:
    size = (192, 96)
    a = np.asarray(left.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    b = np.asarray(right.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    return max(0.0, 1.0 - float(np.mean(np.abs(a - b))))


def best_size_for_reference(
    text: str,
    font_path: Path,
    face_index: int,
    reference_mask: Image.Image,
    sizes,
) -> dict:
    reference_mask = trim_mask(reference_mask)
    reference = _mask_metrics(reference_mask)
    best = None
    for size in sizes:
        font = ImageFont.truetype(str(font_path), int(size), index=face_index)
        candidate_mask = render_text_mask(text, font)
        candidate = _mask_metrics(candidate_mask)
        width_error = abs(candidate["width"] - reference["width"]) / max(reference["width"], 1.0)
        height_error = abs(candidate["height"] - reference["height"]) / max(reference["height"], 1.0)
        density_error = abs(candidate["density"] - reference["density"])
        similarity = _shape_similarity(reference_mask, candidate_mask)
        score = 0.34 * width_error + 0.34 * height_error + 0.17 * density_error + 0.15 * (1.0 - similarity)
        result = {
            "size_px": int(size),
            "score": round(score, 6),
            "width_error": round(width_error, 6),
            "height_error": round(height_error, 6),
            "density_error": round(density_error, 6),
            "shape_similarity": round(similarity, 6),
            "rendered_width": int(candidate_mask.width),
            "rendered_height": int(candidate_mask.height),
        }
        if best is None or (result["score"], abs(int(size))) < (best["score"], abs(best["size_px"])):
            best = result
    if best is None:
        raise ValueError("sizes must not be empty")
    return best


def _parse_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError("RGB must be RRGGBB")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def parse_bbox(value: str) -> tuple[int, int, int, int]:
    parts = tuple(int(item.strip()) for item in value.split(","))
    if len(parts) != 4 or parts[2] <= parts[0] or parts[3] <= parts[1]:
        raise ValueError("bbox must be x0,y0,x1,y1 with positive width and height")
    return parts


def mask_from_reference(image: Image.Image, foreground_rgb: tuple[int, int, int] | None, tolerance: float) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    if foreground_rgb is None:
        border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)
        background = np.median(border, axis=0)
        selected = np.linalg.norm(rgb - background, axis=2) >= tolerance
    else:
        selected = np.linalg.norm(rgb - np.asarray(foreground_rgb, dtype=np.float32), axis=2) <= tolerance
    return trim_mask(Image.fromarray((selected.astype(np.uint8) * 255), mode="L"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True, help="Tight PDF crop containing the target text")
    parser.add_argument("--text", required=True)
    parser.add_argument("--font-catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--foreground-color", help="Reference text color as RRGGBB; recommended when a backing swash is present")
    parser.add_argument("--reference-bbox", help="Optional x0,y0,x1,y1 crop in reference-render pixels")
    parser.add_argument("--color-tolerance", type=float, default=40.0)
    parser.add_argument("--min-size", type=int, default=12)
    parser.add_argument("--max-size", type=int, default=120)
    parser.add_argument("--family", action="append", default=[], help="Optional family allow-list")
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args()

    catalog = json.loads(args.font_catalog.read_text(encoding="utf-8"))
    reference_image = Image.open(args.reference).convert("RGB")
    if args.reference_bbox:
        reference_image = reference_image.crop(parse_bbox(args.reference_bbox))
    color = _parse_rgb(args.foreground_color) if args.foreground_color else None
    reference_mask = mask_from_reference(reference_image, color, args.color_tolerance)
    allowed = {item.casefold() for item in args.family}
    rankings = []
    rejected = []
    for record in catalog.get("fonts", []):
        if allowed and record.get("family", "").casefold() not in allowed:
            continue
        path = Path(record["path"])
        face_index = int(record.get("face_index", 0))
        try:
            missing = unsupported_characters(args.text, load_codepoints(path, face_index))
            if missing:
                rejected.append({"family": record.get("family"), "path": str(path), "face_index": face_index, "missing_characters": missing})
                continue
            match = best_size_for_reference(args.text, path, face_index, reference_mask, range(args.min_size, args.max_size + 1))
            rankings.append({**record, **match, "coverage_ok": True})
        except Exception as exc:
            rejected.append({"family": record.get("family"), "path": str(path), "face_index": face_index, "error": str(exc)})
    rankings.sort(key=lambda item: (item["score"], abs(item.get("weight_class", 400) - 400), item.get("family", "")))
    report = {
        "schema_version": 1,
        "reference": str(args.reference.resolve()),
        "text": args.text,
        "reference_ink_bbox": {"width": reference_mask.width, "height": reference_mask.height},
        "rankings": rankings[: args.top],
        "rejected": rejected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
