#!/usr/bin/env python3
"""Audit repeated text peers and split-answer overlays in a PPTX.

The contract is deliberately explicit: shape IDs identify semantic peers and
answer/stem pairs, so the audit checks the intended teaching structure rather
than guessing roles from proximity.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


PATH_RE = re.compile(r"^/slide\[(\d+)\]/shape\[@id=(\d+)\]$")


def parse_length(value: Any) -> float:
    text = str(value or "0").strip()
    match = re.fullmatch(r"(-?[0-9.]+)(emu|pt|cm|in)?", text)
    if not match:
        return 0.0
    number = float(match.group(1))
    unit = match.group(2) or "emu"
    return number * {"emu": 1, "pt": 12700, "cm": 360000, "in": 914400}[unit]


def normalize_property(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"-?[0-9.]+pt", value):
            return round(parse_length(value) / 12700, 4)
    return value


def box(shape: dict[str, Any]) -> tuple[float, float, float, float]:
    fmt = shape.get("format", {})
    return (
        parse_length(fmt.get("x")),
        parse_length(fmt.get("y")),
        parse_length(fmt.get("width")),
        parse_length(fmt.get("height")),
    )


def contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float]) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh


def add_issue(issues: list[dict[str, Any]], code: str, **details: Any) -> None:
    issues.append({"code": code, **details})


def audit(query: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    results = query.get("results") or query.get("data", {}).get("results") or []
    shapes: dict[tuple[int, int], dict[str, Any]] = {}
    for shape in results:
        match = PATH_RE.match(shape.get("path", ""))
        if match:
            shapes[(int(match.group(1)), int(match.group(2)))] = shape

    issues: list[dict[str, Any]] = []
    checked_groups = 0
    checked_answers = 0

    for group in contract.get("peerGroups", []):
        checked_groups += 1
        slide = int(group["slide"])
        ids = [int(value) for value in group.get("shapeIds", [])]
        peers = [shapes.get((slide, shape_id)) for shape_id in ids]
        present = [peer for peer in peers if peer is not None]
        expected = int(group.get("expectedCount", len(ids)))
        if len(present) != expected:
            add_issue(
                issues,
                "peer_count_mismatch",
                slide=slide,
                group=group.get("name"),
                expected=expected,
                actual=len(present),
                missingShapeIds=[shape_id for shape_id, peer in zip(ids, peers) if peer is None],
            )
        for prop in group.get("equal", []):
            values = [normalize_property(peer.get("format", {}).get(prop)) for peer in present]
            if values and any(value != values[0] for value in values[1:]):
                add_issue(
                    issues,
                    f"peer_{prop.lower()}_mismatch",
                    slide=slide,
                    group=group.get("name"),
                    property=prop,
                    values={str(shape_id): value for shape_id, value in zip(ids, values)},
                )
        max_lines = group.get("maxLines")
        if max_lines is not None:
            for shape_id, peer in zip(ids, peers):
                if peer is None:
                    continue
                line_count = max(1, len(str(peer.get("text", "")).splitlines()))
                if line_count > int(max_lines):
                    add_issue(
                        issues,
                        "peer_line_count",
                        slide=slide,
                        group=group.get("name"),
                        shapeId=shape_id,
                        maxLines=int(max_lines),
                        actualLines=line_count,
                    )

    for answer in contract.get("answerOverlays", []):
        checked_answers += 1
        slide = int(answer["slide"])
        stem_id = int(answer["stemShapeId"])
        answer_id = int(answer["answerShapeId"])
        stem = shapes.get((slide, stem_id))
        overlay = shapes.get((slide, answer_id))
        if stem is None or overlay is None:
            add_issue(
                issues,
                "answer_shape_missing",
                slide=slide,
                stemShapeId=stem_id,
                answerShapeId=answer_id,
            )
            continue
        glyph = str(answer.get("answerGlyph", ""))
        actual_text = str(overlay.get("text", "")).strip()
        if actual_text != glyph:
            add_issue(
                issues,
                "answer_not_glyph_only",
                slide=slide,
                answerShapeId=answer_id,
                expected=glyph,
                actual=actual_text,
            )
        placeholder = str(answer.get("stemPlaceholder", ""))
        normalized_stem = re.sub(r"\s+", "", str(stem.get("text", "")))
        normalized_placeholder = re.sub(r"\s+", "", placeholder)
        if normalized_placeholder and normalized_placeholder not in normalized_stem:
            add_issue(
                issues,
                "stem_placeholder_missing",
                slide=slide,
                stemShapeId=stem_id,
                placeholder=placeholder,
                actual=stem.get("text", ""),
            )
        overlay_box = box(overlay)
        if answer.get("requireInsideStem") and not contains(box(stem), overlay_box):
            add_issue(
                issues,
                "answer_outside_stem",
                slide=slide,
                stemShapeId=stem_id,
                answerShapeId=answer_id,
            )
        if "safeRect" in answer:
            safe = tuple(float(value) for value in answer["safeRect"])
            if not contains(safe, overlay_box):
                add_issue(
                    issues,
                    "answer_outside_safe_rect",
                    slide=slide,
                    answerShapeId=answer_id,
                    safeRect=answer["safeRect"],
                )

    slide_size = contract.get("slideSize")
    if slide_size:
        canvas = (0.0, 0.0, float(slide_size["width"]), float(slide_size["height"]))
        checked_ids = set()
        for group in contract.get("peerGroups", []):
            checked_ids.update((int(group["slide"]), int(shape_id)) for shape_id in group.get("shapeIds", []))
        for answer in contract.get("answerOverlays", []):
            checked_ids.add((int(answer["slide"]), int(answer["stemShapeId"])))
            checked_ids.add((int(answer["slide"]), int(answer["answerShapeId"])))
        for key in checked_ids:
            shape = shapes.get(key)
            if shape and not contains(canvas, box(shape)):
                add_issue(issues, "shape_outside_slide", slide=key[0], shapeId=key[1])

    return {
        "passed": not issues,
        "checkedPeerGroups": checked_groups,
        "checkedAnswerOverlays": checked_answers,
        "issues": issues,
    }


def pptx_slide_size(path: Path) -> dict[str, int]:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
    ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
    size = root.find("p:sldSz", ns)
    if size is None:
        raise ValueError("PPTX presentation.xml has no slide size")
    return {"width": int(size.attrib["cx"]), "height": int(size.attrib["cy"])}


def query_pptx(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["officecli", "query", str(path), "shape", "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "officecli query failed")
    payload = json.loads(completed.stdout)
    if not payload.get("success"):
        raise RuntimeError("officecli query did not succeed")
    return payload["data"]


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pptx", type=Path)
    source.add_argument("--query-json", type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8-sig"))
    if args.pptx:
        query = query_pptx(args.pptx)
        contract.setdefault("slideSize", pptx_slide_size(args.pptx))
    else:
        query = json.loads(args.query_json.read_text(encoding="utf-8-sig"))
    report = audit(query, contract)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
