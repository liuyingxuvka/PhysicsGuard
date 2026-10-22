from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

import physicsguard
from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values


ROOT = Path(__file__).resolve().parents[1]
OBSERVED = ROOT / "examples" / "hierarchical" / "observed_debugging"


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _mapped_observation_file(tmp_path: Path) -> Path:
    payload = yaml.safe_load((OBSERVED / "pitch_feedback_observed_fault.yaml").read_text(encoding="utf-8"))
    payload["variables"]["controller_q_gain.x"].update(
        {
            "external_signal": "simout.q_rad_per_s",
            "mapping_confidence": "low",
            "mapping_status": "stale",
            "review_required": True,
            "stale_when": ["source model was regenerated after this mapping"],
        }
    )
    payload["variables"]["controller_q_gain.y"].update(
        {
            "external_signal": "simout.feedback_command_deg",
            "mapping_confidence": 0.95,
            "unit": "deg",
        }
    )
    path = tmp_path / "mapped_observed.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_signal_mapping_ledger_records_review_state_and_followups(tmp_path: Path) -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(_mapped_observation_file(tmp_path))

    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)

    ledger = {record.physics_variable: record for record in report.signal_mapping_ledger}
    assert ledger["controller_q_gain.x"].external_signal == "simout.q_rad_per_s"
    assert "low_confidence" in ledger["controller_q_gain.x"].issue_codes
    assert "review_required" in ledger["controller_q_gain.x"].issue_codes
    assert "stale_mapping" in ledger["controller_q_gain.x"].issue_codes
    assert "missing_conversion" in ledger["controller_q_gain.y"].issue_codes
    assert report.metadata["signal_mapping_summary"]["review_required_count"] == 2
    assert any("signal mapping needs review" in warning for warning in report.warnings)
    assert {item.family for item in report.bug_family_followups} >= {"signal_mapping", "gain_sign_or_direction", "unit_conversion"}


def test_hierarchy_plan_surfaces_mapping_ledger_and_followups(tmp_path: Path) -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(_mapped_observation_file(tmp_path))

    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    data = HierarchicalAuditRunner(spec).to_dict(report)

    assert data["signal_mapping_ledger"][0]["physics_variable"] == "controller_q_gain.x"
    assert data["bug_family_followups"][0]["recommended_action"]


def test_signal_mapping_cli_output_is_top_level_json(tmp_path: Path) -> None:
    observed_file = _mapped_observation_file(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "physicsguard.cli",
            "hierarchy",
            "evaluate",
            str(OBSERVED / "pitch_feedback_level_0.yaml"),
            str(observed_file),
            "--pretty",
            "--json",
        ],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert data["signal_mapping_ledger"]
    assert data["bug_family_followups"]
    assert data["metadata"]["signal_mapping_summary"]["semantics"].startswith("mapping ledger records")


def test_signal_mapping_public_api_is_exported() -> None:
    exported = set(physicsguard.__all__)
    assert "SignalMappingRecord" in exported
    assert "BugFamilyFollowUp" in exported
    assert "build_signal_mapping_ledger" in exported
    assert "derive_bug_family_followups" in exported


def test_clean_audit_has_no_gain_or_balance_followups() -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    observed = load_observed_values(OBSERVED / "pitch_feedback_observed_clean.yaml")
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    assert report.audit_pass is True
    families = {item.family for item in report.bug_family_followups}
    assert "gain_sign_or_direction" not in families
    assert "conservation_balance" not in families


def test_observed_value_without_a_unit_is_a_mapping_gap(tmp_path: Path) -> None:
    payload = yaml.safe_load((OBSERVED / "pitch_feedback_observed_clean.yaml").read_text(encoding="utf-8"))
    del payload["variables"]["controller_q_gain.x"]["unit"]
    path = tmp_path / "unitless.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")

    report = HierarchicalAuditRunner(spec).evaluate_observed(load_observed_values(path))

    ledger = {record.physics_variable: record for record in report.signal_mapping_ledger}
    assert ledger["controller_q_gain.x"].expected_unit == "rad/s"
    assert ledger["controller_q_gain.x"].issue_codes == ("missing_unit",)
    assert "Record the unit" in ledger["controller_q_gain.x"].recommended_action
    assert "controller_q_gain.x: signal mapping needs review (missing_unit)" in report.warnings
    assert [item.followup_id for item in report.bug_family_followups] == ["signal_mapping_review"]


def test_signal_mapping_ledger_review_ignores_a_retired_fingerprint(tmp_path: Path) -> None:
    ledger = {
        "artifact_kind": "physicsguard_signal_mapping_ledger",
        "ledger_id": "pump_loop_mapping",
        "target_system_id": "pump_loop",
        "subject_revision": "r1",
        "source_artifact_sha256": "a" * 64,
        "entries": [
            {
                "mapping_id": "m1",
                "physics_variable": "pump.flow",
                "external_signal": "FT_101",
                "expected_unit": "m^3/s",
                "observed_unit": "m^3/s",
                "mapping_status": "reviewed",
                "source_revision": "r1",
                "temporal_boundary": "whole run",
            }
        ],
        "status": "pass",
        "safe_mapping_claim": "FT_101 is pump.flow for run r1",
    }
    path = tmp_path / "ledger.yaml"
    for retired in ({}, {"ledger_fingerprint": "0" * 64}):
        path.write_text(yaml.safe_dump({**ledger, **retired}, sort_keys=False), encoding="utf-8")
        review = physicsguard.review_signal_mapping_ledger(path)
        assert review.status == "pass"
        assert review.summary["entry_count"] == 1
    blocked = {**ledger, "status": "blocked", "entries": [{**ledger["entries"][0], "issue_codes": ["missing_unit"]}]}
    path.write_text(yaml.safe_dump(blocked, sort_keys=False), encoding="utf-8")
    review = physicsguard.review_signal_mapping_ledger(path)
    assert review.status == "fail"
    assert [finding.type for finding in review.findings] == ["missing_unit"]


def test_stale_when_is_a_condition_until_mapping_status_is_stale(tmp_path: Path) -> None:
    spec = load_hierarchical_audit_spec(OBSERVED / "pitch_feedback_level_0.yaml")
    payload = yaml.safe_load((OBSERVED / "pitch_feedback_observed_clean.yaml").read_text(encoding="utf-8"))
    payload["variables"]["controller_q_gain.x"].update({
        "mapping_confidence": "high", "stale_when": ["controller retuned"],
    })
    path = tmp_path / "stale_condition.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    observed = load_observed_values(path)
    report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    row = next(item for item in report.signal_mapping_ledger if item.physics_variable == "controller_q_gain.x")
    assert report.audit_pass is True
    assert row.stale_when == ("controller retuned",)
    assert row.issue_codes == ()
    assert "signal_mapping_review" not in {item.followup_id for item in report.bug_family_followups}
    for status in ("stale", "StAlE"):
        payload["variables"]["controller_q_gain.x"]["mapping_status"] = status
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        report = HierarchicalAuditRunner(spec).evaluate_observed(load_observed_values(path))
        row = next(item for item in report.signal_mapping_ledger if item.physics_variable == "controller_q_gain.x")
        assert row.issue_codes == ("stale_mapping",)
        assert "signal_mapping_review" in {item.followup_id for item in report.bug_family_followups}
