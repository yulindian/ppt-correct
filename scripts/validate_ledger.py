from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STATES = {"working", "candidate", "verified-final", "failed"}
ITEM_STATUSES = {"open", "closed", "accepted-exception"}
GATE_STATUSES = {"pending", "pass", "fail", "unavailable", "not-applicable"}


def validate_ledger(data: dict) -> list[str]:
    errors: list[str] = []
    state = data.get("state")
    if state not in STATES:
        errors.append(f"invalid state: {state!r}")

    items = data.get("items")
    if not isinstance(items, list):
        errors.append("items must be an array")
        items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"item {index} must be an object")
            continue
        status = item.get("status")
        if status not in ITEM_STATUSES:
            errors.append(f"item {item.get('id', index)!r} has invalid status: {status!r}")
        if status == "accepted-exception" and not item.get("exception"):
            errors.append(f"item {item.get('id', index)!r} is missing exception evidence")

    gates = data.get("gates")
    if not isinstance(gates, dict) or not gates:
        errors.append("gates must be a non-empty object")
        gates = {}
    for name, status in gates.items():
        if status not in GATE_STATUSES:
            errors.append(f"gate {name!r} has invalid status: {status!r}")

    output = data.get("outputPptx")
    output_name = Path(output).name if isinstance(output, str) and output else ""
    if state == "candidate" and not output_name.endswith("_动画版_候选.pptx"):
        errors.append("candidate output must end with _动画版_候选.pptx")
    if state == "verified-final":
        if not output_name.endswith("_动画版.pptx") or output_name.endswith("_动画版_候选.pptx"):
            errors.append("verified-final output must end with _动画版.pptx")
        if any(item.get("status") == "open" for item in items if isinstance(item, dict)):
            errors.append("verified-final cannot contain an open ledger item")
        blocking_gates = {
            name: status
            for name, status in gates.items()
            if status not in {"pass", "not-applicable"}
        }
        if blocking_gates:
            errors.append(f"verified-final has unresolved gates: {blocking_gates}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a ppt-correct correction ledger")
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()

    try:
        data = json.loads(args.ledger.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read ledger: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("ledger root must be an object", file=sys.stderr)
        return 2

    errors = validate_ledger(data)
    report = {"passed": not errors, "state": data.get("state"), "errorCount": len(errors)}
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
