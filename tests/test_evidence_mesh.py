from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from physicsguard.core.evidence_mesh import check_evidence_mesh
from physicsguard.schema.evidence_mesh import EvidenceMeshReportSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
MESH = PUMP / "evidence_mesh.yaml"


def _write_mesh(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "evidence_mesh.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_clean_evidence_mesh_passes() -> None:
    report = check_evidence_mesh(MESH)

    assert report.ok
    assert report.status == "pass"
    assert report.route_status["model_mesh"] == "pass"
    assert report.route_status["model_test_alignment"] == "pass"
    assert EvidenceMeshReportSpec.model_validate(report.to_dict()).status == "pass"


def test_child_local_green_without_parent_consumption_blocks(tmp_path: Path) -> None:
    data = yaml.safe_load(MESH.read_text(encoding="utf-8"))
    data["parent_models"][0]["consumed_child_evidence_ids"].remove("child_pump_signal_map_current")
    path = _write_mesh(tmp_path, data)

    report = check_evidence_mesh(path)

    assert not report.ok
    assert report.status == "fail"
    assert any(item["type"] == "child_evidence_not_consumed_by_parent" for item in report.blocking_findings)


def test_required_obligation_without_bound_test_blocks(tmp_path: Path) -> None:
    data = yaml.safe_load(MESH.read_text(encoding="utf-8"))
    data["test_evidence"][1]["covers_obligation_ids"] = []
    path = _write_mesh(tmp_path, data)

    report = check_evidence_mesh(path)

    assert not report.ok
    assert any(item["type"] == "required_obligation_missing_external_test" for item in report.blocking_findings)


def test_progress_only_test_mesh_evidence_blocks(tmp_path: Path) -> None:
    data = yaml.safe_load(MESH.read_text(encoding="utf-8"))
    data["test_suites"][1]["progress_only"] = True
    path = _write_mesh(tmp_path, data)

    report = check_evidence_mesh(path)

    assert not report.ok
    assert any(item["type"] == "test_suite_not_current" for item in report.blocking_findings)


def test_cli_mesh_check_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "evidence",
            "mesh-check",
            str(MESH),
            "--pretty",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["artifact_kind"] == "physicsguard_evidence_mesh_report"
    assert data["status"] == "pass"
