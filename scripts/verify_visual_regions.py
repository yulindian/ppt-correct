#!/usr/bin/env python3
"""Verify text, background swash, and highlight regions between PDF and PPT renders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


DEFAULT_THRESHOLDS = {
    "width_error": 0.05,
    "height_error": 0.05,
    "centroid_distance_px": 4.0,
    "density_error": 0.12,
    "color_delta": 6.0,
    "contour_similarity": 0.55,
    "minimum_presence_ratio": 0.70,
}


def _rgb_to_lab(rgb) -> np.ndarray:
    values = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)
    xyz = np.array(
        [
            0.4124564 * linear[0] + 0.3575761 * linear[1] + 0.1804375 * linear[2],
            0.2126729 * linear[0] + 0.7151522 * linear[1] + 0.0721750 * linear[2],
            0.0193339 * linear[0] + 0.1191920 * linear[1] + 0.9503041 * linear[2],
        ]
    ) / np.array([0.95047, 1.0, 1.08883])
    delta = 6 / 29
    f = np.where(xyz > delta ** 3, np.cbrt(xyz), xyz / (3 * delta ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def color_delta_e(left_rgb, right_rgb) -> float:
    """Return CIE76 Delta E for two sRGB colors."""
    return float(np.linalg.norm(_rgb_to_lab(left_rgb) - _rgb_to_lab(right_rgb)))


def _crop(image: Image.Image, bbox) -> Image.Image:
    return image.convert("RGB").crop(tuple(int(value) for value in bbox))


def _color_mask(image: Image.Image, target_rgb, tolerance: float) -> np.ndarray:
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32)
    target = np.asarray(target_rgb, dtype=np.float32)
    return np.linalg.norm(pixels - target, axis=2) <= tolerance


def _geometry(mask: np.ndarray) -> dict:
    points = np.argwhere(mask)
    if not len(points):
        return {"present": False, "area": 0, "width": 0, "height": 0, "centroid": None, "density": 0.0}
    y0, x0 = points.min(axis=0)
    y1, x1 = points.max(axis=0) + 1
    height, width = mask.shape
    return {
        "present": True,
        "area": int(len(points)),
        "width": int(x1 - x0),
        "height": int(y1 - y0),
        "centroid": [float(points[:, 1].mean()), float(points[:, 0].mean())],
        "density": float(len(points) / max(width * height, 1)),
    }


def _normalized_similarity(left: np.ndarray, right: np.ndarray) -> float:
    from PIL import Image as PILImage

    def normalized(mask):
        points = np.argwhere(mask)
        if not len(points):
            return np.zeros((96, 192), dtype=np.float32)
        y0, x0 = points.min(axis=0)
        y1, x1 = points.max(axis=0) + 1
        crop = (mask[y0:y1, x0:x1].astype(np.uint8) * 255)
        return np.asarray(PILImage.fromarray(crop).resize((192, 96), PILImage.Resampling.NEAREST), dtype=np.float32) / 255.0

    a, b = normalized(left), normalized(right)
    return max(0.0, 1.0 - float(np.mean(np.abs(a - b))))


def compare_region(
    reference: Image.Image,
    candidate: Image.Image,
    reference_bbox,
    candidate_bbox,
    target_rgb,
    tolerance: float = 24.0,
    candidate_target_rgb=None,
) -> dict:
    reference_crop = _crop(reference, reference_bbox)
    candidate_crop = _crop(candidate, candidate_bbox)
    candidate_target_rgb = candidate_target_rgb or target_rgb
    reference_mask = _color_mask(reference_crop, target_rgb, tolerance)
    candidate_mask = _color_mask(candidate_crop, candidate_target_rgb, tolerance)
    ref = _geometry(reference_mask)
    cand = _geometry(candidate_mask)
    if ref["present"]:
        presence_ratio = cand["area"] / max(ref["area"], 1)
        width_error = abs(cand["width"] - ref["width"]) / max(ref["width"], 1)
        height_error = abs(cand["height"] - ref["height"]) / max(ref["height"], 1)
        density_error = abs(cand["density"] - ref["density"])
    else:
        presence_ratio = 1.0 if not cand["present"] else 0.0
        width_error = height_error = density_error = 0.0
    if ref["centroid"] is not None and cand["centroid"] is not None:
        centroid_distance = float(np.linalg.norm(np.asarray(ref["centroid"]) - np.asarray(cand["centroid"])))
    else:
        centroid_distance = 1_000_000_000.0 if ref["present"] != cand["present"] else 0.0
    if cand["present"]:
        pixels = np.asarray(candidate_crop, dtype=np.float32)[candidate_mask]
        mean_candidate = pixels.mean(axis=0)
        color_delta = color_delta_e(mean_candidate, target_rgb)
    else:
        color_delta = 1_000_000_000.0 if ref["present"] else 0.0
    return {
        "reference": ref,
        "candidate": cand,
        "presence_ratio": round(presence_ratio, 6),
        "width_error": round(width_error, 6),
        "height_error": round(height_error, 6),
        "centroid_distance_px": round(centroid_distance, 6),
        "density_error": round(density_error, 6),
        "color_delta": round(color_delta, 6),
        "contour_similarity": round(_normalized_similarity(reference_mask, candidate_mask), 6),
    }


def evaluate_metrics(metrics: dict, kind: str, thresholds: dict | None = None) -> dict:
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    failures = []
    if metrics["reference"]["present"] and metrics["presence_ratio"] < limits["minimum_presence_ratio"]:
        failures.append("required visual layer is missing")
    checks = (
        ("width_error", "ink/block width differs from PDF"),
        ("height_error", "ink/block height differs from PDF"),
        ("centroid_distance_px", "region position differs from PDF"),
        ("density_error", "apparent weight or fill density differs from PDF"),
        ("color_delta", "region color differs from PDF"),
    )
    for key, message in checks:
        if metrics[key] > limits[key]:
            failures.append(message)
    if kind == "text" and metrics["contour_similarity"] < limits["contour_similarity"]:
        failures.append("glyph contour similarity is below threshold")
    return {"passed": not failures, "failures": failures, "thresholds": limits}


def _rgb(value):
    if isinstance(value, str):
        value = value.strip().lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
    return tuple(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pages = manifest.get("pages", [manifest])
    results = []
    exceptions = []
    root = args.manifest.parent
    for page in pages:
        reference = Image.open((root / page["reference_image"]).resolve())
        candidate = Image.open((root / page["candidate_image"]).resolve())
        for region in page.get("regions", []):
            metrics = compare_region(
                reference,
                candidate,
                region["reference_bbox"],
                region.get("candidate_bbox", region["reference_bbox"]),
                _rgb(region["target_rgb"]),
                float(region.get("color_tolerance", 24.0)),
                _rgb(region["candidate_target_rgb"]) if region.get("candidate_target_rgb") else None,
            )
            thresholds = {**manifest.get("thresholds", {}), **region.get("thresholds", {})}
            verdict = evaluate_metrics(metrics, region.get("kind", "text"), thresholds)
            item = {"page": page.get("page"), "id": region["id"], "kind": region.get("kind", "text"), "metrics": metrics, **verdict}
            results.append(item)
            if not verdict["passed"]:
                exceptions.append({"page": page.get("page"), "id": region["id"], "failures": verdict["failures"]})
    report = {"schema_version": 1, "passed": not exceptions, "regions": results, "exception_ledger": exceptions}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
