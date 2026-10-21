from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_closure_script() -> ModuleType:
    path = ROOT / "skill" / "physicsguard-ai-debugging" / "scripts" / "physicsguard_closure_check.py"
    spec = importlib.util.spec_from_file_location("physicsguard_closure_check", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_closure_flags_signal_mapping_issue_codes(tmp_path: Path) -> None:
    closure = _load_closure_script()
    ledger = tmp_path / "ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "signal_mapping_ledger": [
                    {
                        "physics_variable": "controller_q_gain.x",
                        "issue_codes": ["low_confidence", "missing_conversion"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = closure.check(argparse.Namespace(ledger=ledger, audit=None, observed=None))

    assert result["closure_status"] == "partial"
    assert any(item["type"] == "signal_mapping_review_required" for item in result["findings"])
    assert any(item["action"] == "review_signal_mapping_confidence_units_and_staleness" for item in result["next_actions"])


def test_closure_flags_skipped_checks(tmp_path: Path) -> None:
    closure = _load_closure_script()
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"skipped_checks": ["same-family unit review"]}), encoding="utf-8")

    result = closure.check(argparse.Namespace(ledger=ledger, audit=None, observed=None))

    assert any(item["type"] == "skipped_physicsguard_checks" for item in result["findings"])
    assert any(item["action"] == "run_or_scope_skipped_physicsguard_checks" for item in result["next_actions"])


@pytest.mark.parametrize("state", ["clean", "fault", "no_gap"])
def test_closure_consumes_full_native_observed_audit_without_reference_solve(tmp_path: Path, state: str) -> None:
    closure = _load_closure_script()
    audit = ROOT / "examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml"
    observed = audit.parent / f"pitch_feedback_observed_{state}.yaml"
    if state == "no_gap":
        # A real existing native relation with exact observed SI values and no followup family.
        system = yaml.safe_load((ROOT / "examples/foundation/ohmic_relation.yaml").read_text(encoding="utf-8"))
        system.pop("boundaries")
        audit = tmp_path / "ohmic-audit.yaml"
        audit.write_text(yaml.safe_dump({"audit_name": "ohmic_observed", "system": system,
            "hierarchy": {"blocks": [{"id": "resistor_block", "name": "Resistor", "level": 0, "components": ["resistor"],
                "required_variables": ["resistor.current_A", "resistor.V_drop_V"], "required_parameters": ["resistor.resistance_ohm"]}]}}), encoding="utf-8")
        observed = tmp_path / "ohmic-observed.yaml"
        observed.write_text(yaml.safe_dump({"observation_name": "ohmic_clean", "variables": {
            "resistor.current_A": {"value": 100.0, "unit": "A", "source": "test_snapshot"},
            "resistor.V_drop_V": {"value": 10.0, "unit": "V", "source": "test_snapshot"}}}), encoding="utf-8")
    before = observed.read_bytes()
    ledger = tmp_path / "ledger.json"
    # A caller's clean fields and status must not erase native fault details.
    ledger.write_text(json.dumps({"closure_status": "passed", "audit_pass": True,
        "recommended_refinements": [], "bug_family_followups": [], "signal_mapping_ledger": []}), encoding="utf-8")
    result = closure.check(argparse.Namespace(ledger=ledger, audit=audit, observed=observed))
    assert len(result["command_results"]) == 1
    assert "hierarchy evaluate" in result["command_results"][0]["command"]
    assert result["command_results"][0]["returncode"] == 0
    assert observed.read_bytes() == before
    codes = {item["type"] for item in result["findings"]}
    assert "physicsguard_invalid_evaluate_result" not in codes
    if state == "fault":
        assert len(result["command_results"][0]["stdout"]) == 6000
        assert result["closure_status"] == "blocked"
        assert {"audit_failed", "recommended_refinements", "bug_family_followups"} <= codes
    elif state == "clean":
        # A clean audit (all residuals within the audit threshold) raises no family followup.
        assert result["closure_status"] == "passed", result["findings"]
        assert "bug_family_followups" not in codes
    else:
        assert result["closure_status"] == "passed", result["findings"]


def test_caller_pass_cannot_upgrade_missing_inputs(tmp_path: Path) -> None:
    closure = _load_closure_script()
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"closure_status": "passed", "safe_claim": "everything passed"}), encoding="utf-8")
    result = closure.check(argparse.Namespace(ledger=ledger, audit=None, observed=None))
    assert result["closure_status"] == "partial"
    assert result["missing_inputs"]
    assert "everything passed" not in result["safe_claim"]


@pytest.mark.parametrize("stdout", ["", "not JSON", "[]", "{}", '{"audit_pass": "true"}', '{"audit_pass": true, "missing_required_variables": {}}'])
def test_invalid_native_output_never_passes(monkeypatch, stdout: str) -> None:
    closure = _load_closure_script()
    monkeypatch.setattr(closure, "_run", lambda command: {"command": " ".join(command), "returncode": 0, "stdout": stdout, "stderr": ""})
    result = closure.check(argparse.Namespace(ledger=None, audit=Path("audit.yaml"), observed=Path("observed.yaml")))
    assert result["closure_status"] == "blocked"
    assert "physicsguard_invalid_evaluate_result" in {item["type"] for item in result["findings"]}
