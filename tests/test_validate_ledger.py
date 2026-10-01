import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_ledger.py"


def run_validator(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger)],
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        check=False,
    )


def base_ledger() -> dict:
    return {
        "version": 1,
        "project": "示例",
        "state": "working",
        "sourcePdf": "C:/job/示例.pdf",
        "sourcePptx": "C:/job/示例.pptx",
        "outputPptx": None,
        "items": [],
        "gates": {
            "staticVisual": "pending",
            "fontPage": "pending",
            "animationTimeline": "pending",
            "deliveryApplication": "not-applicable",
        },
    }


def test_verified_final_requires_closed_items_and_passed_gates(tmp_path):
    payload = base_ledger()
    payload["state"] = "verified-final"
    payload["outputPptx"] = "C:/job/示例_动画版.pptx"
    payload["items"] = [{"id": "s1", "status": "open"}]
    payload["gates"]["staticVisual"] = "pass"
    payload["gates"]["fontPage"] = "pass"
    payload["gates"]["animationTimeline"] = "pass"

    result = run_validator(tmp_path, payload)

    assert result.returncode != 0
    assert "open ledger item" in result.stderr


def test_candidate_requires_candidate_filename(tmp_path):
    payload = base_ledger()
    payload["state"] = "candidate"
    payload["outputPptx"] = "C:/job/示例_动画版.pptx"

    result = run_validator(tmp_path, payload)

    assert result.returncode != 0
    assert "_动画版_候选.pptx" in result.stderr


def test_verified_final_valid_ledger_passes(tmp_path):
    payload = base_ledger()
    payload["state"] = "verified-final"
    payload["outputPptx"] = "C:/job/示例_动画版.pptx"
    payload["items"] = [{"id": "s1", "status": "closed"}]
    payload["gates"] = {
        "staticVisual": "pass",
        "fontPage": "pass",
        "animationTimeline": "pass",
        "deliveryApplication": "not-applicable",
    }

    result = run_validator(tmp_path, payload)

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report == {"passed": True, "state": "verified-final", "errorCount": 0}
