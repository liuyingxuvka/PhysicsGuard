from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from physicsguard.workflow import (
    review_model_understanding_preflight,
)


ROOT = Path(__file__).resolve().parents[1]


def test_model_understanding_preflight_template_passes() -> None:
    report = review_model_understanding_preflight(ROOT / "skill" / "physicsguard" / "references" / "templates" / "model_understanding_preflight.yaml")

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


def test_cli_preflight_review_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "preflight",
            "review",
            str(ROOT / "skill" / "physicsguard" / "references" / "templates" / "model_understanding_preflight.yaml"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["artifact_kind"] == "model_understanding_preflight"


def test_preflight_audit_names_unknown_blocks_without_changing_unbound_behavior(tmp_path):
    data=yaml.safe_load((ROOT/'skill/physicsguard/references/templates/model_understanding_preflight.yaml').read_text())
    data['physicsguard_understanding']['subsystem_blocks']=[{'id':'not_in_the_model'}]
    path=tmp_path/'preflight.yaml';path.write_text(yaml.safe_dump(data))
    assert review_model_understanding_preflight(path).ok
    audit=ROOT/'examples/hierarchical/heated_tank/heated_tank.yaml'
    result=review_model_understanding_preflight(path,audit=audit)
    assert not result.ok and result.status=='fail'
    assert 'preflight_block_unknown' in {f.type for f in result.findings}
    run=subprocess.run([sys.executable,'-m','physicsguard.cli','preflight','review',str(path),'--audit',str(audit)],capture_output=True,text=True)
    assert run.returncode==1 and 'preflight_block_unknown' in run.stdout
