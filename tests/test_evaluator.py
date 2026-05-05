from __future__ import annotations

from pathlib import Path

import pytest

import physicsguard.core.evaluator as evaluator_module
from physicsguard.core.evaluator import AuditEvaluator
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def coolant_system() -> SystemSpec:
    return load_system_spec(ROOT / "examples" / "physical_coolant_heat_balance.yaml")


def coolant_observed_clean() -> ObservedValuesSpec:
    return load_observed_values(
        ROOT / "examples" / "observed" / "physical_coolant_observed_clean.yaml"
    )


def coolant_observed_conflict() -> ObservedValuesSpec:
    return load_observed_values(
        ROOT / "examples" / "observed" / "physical_coolant_observed_conflict.yaml"
    )


def test_evaluate_observed_clean_coolant_case_passes() -> None:
    result = AuditEvaluator(coolant_system()).evaluate_observed(coolant_observed_clean())
    assert result.audit_pass
    assert result.max_abs_normalized_residual == pytest.approx(0.0)
    assert result.variables["coolant.Q_dot_W"] == 4180.0


def test_evaluate_observed_conflict_coolant_case_fails_audit() -> None:
    result = AuditEvaluator(coolant_system()).evaluate_observed(coolant_observed_conflict())
    assert not result.audit_pass
    assert result.top_residuals[0].diagnostic_key == "coolant_heat_balance_mismatch"
    assert result.top_residuals[0].role == "equation"


def test_evaluate_observed_does_not_call_solver(monkeypatch) -> None:
    class FailingSolver:
        def __init__(self, *args, **kwargs):
            raise AssertionError("solver must not be constructed in evaluate mode")

    monkeypatch.setattr(evaluator_module, "BoundedSolver", FailingSolver)
    result = AuditEvaluator(coolant_system()).evaluate_observed(coolant_observed_clean())
    assert result.audit_pass


def test_missing_required_observed_variable_fails_clearly() -> None:
    observed = ObservedValuesSpec.model_validate(
        {
            "variables": {
                "coolant.m_dot_kg_s": {"value": 0.1},
                "coolant.T_in_K": {"value": 300.0},
                "coolant.T_out_K": {"value": 310.0},
            }
        }
    )
    with pytest.raises(ValueError, match="missing required registered variables"):
        AuditEvaluator(coolant_system()).evaluate_observed(observed)


def test_unknown_observed_variable_is_reported() -> None:
    observed = ObservedValuesSpec.model_validate(
        {
            "variables": {
                "coolant.m_dot_kg_s": {"value": 0.1},
                "coolant.T_in_K": {"value": 300.0},
                "coolant.T_out_K": {"value": 310.0},
                "coolant.Q_dot_W": {"value": 4180.0},
                "coolant.extra": {"value": 99.0},
            }
        }
    )
    result = AuditEvaluator(coolant_system()).evaluate_observed(observed)
    assert result.audit_pass
    assert result.unknown_observed_variables == ["coolant.extra"]
    assert "unknown observed variables ignored: coolant.extra" in result.warnings


def test_unit_mismatch_is_reported_as_warning() -> None:
    observed = ObservedValuesSpec.model_validate(
        {
            "variables": {
                "coolant.m_dot_kg_s": {"value": 0.1, "unit": "kg/s"},
                "coolant.T_in_K": {"value": 300.0, "unit": "K"},
                "coolant.T_out_K": {"value": 310.0, "unit": "K"},
                "coolant.Q_dot_W": {"value": 4180.0, "unit": "kW"},
            }
        }
    )
    result = AuditEvaluator(coolant_system()).evaluate_observed(observed)
    assert result.audit_pass
    assert result.unit_warnings
    assert "coolant.Q_dot_W" in result.unit_warnings[0]


def test_post_check_residuals_are_reported_but_do_not_control_audit_pass() -> None:
    system = SystemSpec.model_validate(
        {
            "system_name": "range_observed",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": {
                        "a": 1.0,
                        "b": 0.0,
                        "x_lower_bound": -10.0,
                        "x_upper_bound": 10.0,
                        "x_initial_guess": 0.0,
                        "x_scale": 1.0,
                        "y_lower_bound": -10.0,
                        "y_upper_bound": 10.0,
                        "y_initial_guess": 0.0,
                        "y_scale": 1.0,
                        "residual_scale": 1.0,
                    },
                },
                {
                    "id": "range",
                    "type": "RangeCheckModule",
                    "parameters": {
                        "variable": "rel.x",
                        "upper_bound": 1.0,
                        "residual_scale": 1.0,
                    },
                },
            ],
        }
    )
    observed = ObservedValuesSpec.model_validate(
        {"variables": {"rel.x": {"value": 2.0}, "rel.y": {"value": 2.0}}}
    )
    result = AuditEvaluator(system).evaluate_observed(observed)
    assert result.audit_pass
    assert result.max_abs_normalized_residual == pytest.approx(0.0)
    assert result.top_residuals[0].diagnostic_key == "range_check_violation"
    assert result.top_residuals[0].role == "post_check"


def test_compare_to_reference_returns_reference_and_observed_variables() -> None:
    result = AuditEvaluator(coolant_system()).compare_to_reference(coolant_observed_clean())
    assert result.reference_optimization_success
    assert result.reference_audit_pass
    assert result.observed_audit_pass
    assert result.reference_variables["coolant.Q_dot_W"] == pytest.approx(4180.0, abs=1e-2)
    assert result.observed_variables["coolant.Q_dot_W"] == 4180.0


def test_compare_to_reference_ranks_variable_deviations() -> None:
    result = AuditEvaluator(coolant_system()).compare_to_reference(coolant_observed_conflict())
    assert not result.observed_audit_pass
    assert result.top_variable_deviations[0].variable == "coolant.Q_dot_W"
    assert result.top_variable_deviations[0].abs_normalized_delta > 20.0
    assert result.top_observed_residuals[0].diagnostic_key == "coolant_heat_balance_mismatch"
