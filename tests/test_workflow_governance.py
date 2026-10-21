from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from physicsguard.workflow import (
    review_external_model_intake,
    review_model_understanding_preflight,
)


ROOT = Path(__file__).resolve().parents[1]








def test_model_understanding_preflight_template_passes() -> None:
    report = review_model_understanding_preflight(ROOT / "templates" / "model_understanding_preflight.yaml")

    assert report.ok
    assert report.status == "pass"


def test_model_understanding_preflight_reports_missing_fields(tmp_path: Path) -> None:
    path = tmp_path / "preflight.yaml"
    path.write_text(
        yaml.safe_dump({"physicsguard_understanding": {"visible_symptom": "too hot"}}),
        encoding="utf-8",
    )

    report = review_model_understanding_preflight(path)

    assert not report.ok
    assert "physical_boundary" in report.missing_inputs
    assert "external_model.model_name" in report.missing_inputs


def test_external_model_intake_template_passes() -> None:
    report = review_external_model_intake(ROOT / "templates" / "external_model_intake.yaml")

    assert report.ok
    assert report.status == "pass"


def test_external_model_intake_flags_review_required_mapping(tmp_path: Path) -> None:
    path = tmp_path / "intake.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "external_model_snapshot": {
                    "model_name": "m",
                    "tool": "tool",
                    "model_version": "1",
                    "scenario": "fault",
                    "export_time": "2026-06-08T00:00:00Z",
                    "observed_file": "observed.yaml",
                    "signals": [
                        {
                            "external_signal": "x",
                            "physicsguard_variable": "a.b",
                            "unit_from_source": "bar",
                            "expected_si_unit": "Pa",
                            "mapping_confidence": "low",
                            "review_required": True,
                            "stale_when": ["source changed"],
                        }
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = review_external_model_intake(path)

    assert report.ok
    assert report.status == "partial"
    assert report.summary["review_required_count"] >= 1
    assert any(finding.type == "signal_mapping_review_required" for finding in report.findings)


def test_cli_preflight_review_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "preflight",
            "review",
            str(ROOT / "templates" / "model_understanding_preflight.yaml"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["artifact_kind"] == "model_understanding_preflight"
