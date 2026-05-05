from __future__ import annotations

import pytest

from physicsguard.core.assumptions import AssumptionManager
from physicsguard.core.residual import ResidualBuilder
from physicsguard.schema.system_spec import SystemSpec


def thermal_system(assumptions: list[dict], parameters: dict | None = None) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": "assumption_manager",
            "components": [
                {
                    "id": "conductor",
                    "type": "ThermalConductorModule",
                    "parameters": parameters or {"residual_scale_W": 1000.0},
                }
            ],
            "assumptions": assumptions,
        }
    )


def parameter_assumption(**extra) -> dict:
    data = {
        "id": "assume_G",
        "target_type": "parameter",
        "target": "conductor.G_W_K",
        "value": 50.0,
        "reason": "Missing conductance.",
        "impact": "low",
    }
    data.update(extra)
    return data


def test_active_variable_assumption_creates_applied_card() -> None:
    system = SystemSpec.model_validate(
        {
            "system_name": "variable_assumption",
            "components": [{"id": "d", "type": "DummyResidualModule", "parameters": {"target": 0.0}}],
            "assumptions": [
                {
                    "id": "assume_x",
                    "target_type": "variable",
                    "target": "d.x",
                    "value": 0.0,
                    "reason": "Signal is missing.",
                }
            ],
        }
    )
    manager = AssumptionManager(system)
    manager.apply_parameter_assumptions(system)
    card = manager.assumption_cards()[0]
    assert card.applied
    assert card.application == "boundary_residual"


def test_active_parameter_assumption_fills_missing_parameter() -> None:
    builder = ResidualBuilder(thermal_system([parameter_assumption()]))
    module = builder.build_modules()[0]
    card = builder.assumption_cards()[0]
    assert module.G_W_K == pytest.approx(50.0)
    assert card.applied
    assert card.application == "parameter_fill"


def test_explicit_parameter_is_not_overridden_without_allow_override() -> None:
    builder = ResidualBuilder(thermal_system([parameter_assumption(value=60.0)], {"G_W_K": 50.0}))
    module = builder.build_modules()[0]
    card = builder.assumption_cards()[0]
    assert module.G_W_K == pytest.approx(50.0)
    assert not card.applied
    assert card.application == "not_applied_existing_parameter"
    assert card.warnings


def test_explicit_parameter_override_requires_allow_override_and_warns() -> None:
    builder = ResidualBuilder(
        thermal_system([parameter_assumption(value=60.0, allow_override=True)], {"G_W_K": 50.0})
    )
    module = builder.build_modules()[0]
    summary = builder.assumption_summary()
    assert module.G_W_K == pytest.approx(60.0)
    assert summary.cards[0].application == "parameter_override"
    assert "one or more explicit parameters were overridden by assumptions" in summary.warnings


def test_proposed_assumption_is_not_applied() -> None:
    manager = AssumptionManager(thermal_system([parameter_assumption(status="proposed")], {"G_W_K": 50.0}))
    manager.apply_parameter_assumptions(manager.original_system)
    card = manager.assumption_cards()[0]
    assert not card.applied
    assert card.application == "not_applied_proposed"


def test_rejected_assumption_is_not_applied() -> None:
    manager = AssumptionManager(thermal_system([parameter_assumption(status="rejected")], {"G_W_K": 50.0}))
    manager.apply_parameter_assumptions(manager.original_system)
    card = manager.assumption_cards()[0]
    assert not card.applied
    assert card.application == "not_applied_rejected"


def test_context_assumption_is_reported_without_solver_input_change() -> None:
    system = SystemSpec.model_validate(
        {
            "system_name": "context_assumption",
            "components": [{"id": "d", "type": "DummyResidualModule", "parameters": {"target": 0.0}}],
            "assumptions": [
                {
                    "id": "ambient_context",
                    "target_type": "context",
                    "target": "lab_condition",
                    "value": "nominal",
                    "reason": "Context only.",
                    "impact": "medium",
                }
            ],
        }
    )
    builder = ResidualBuilder(system)
    assert builder.build_registry().names() == ["d.x"]
    summary = builder.assumption_summary()
    assert summary.cards[0].application == "context_only"
    assert summary.applied_count == 1


def test_default_confidence_penalties_by_impact() -> None:
    system = SystemSpec.model_validate(
        {
            "system_name": "penalties",
            "components": [{"id": "d", "type": "DummyResidualModule", "parameters": {"target": 0.0}}],
            "assumptions": [
                {"id": "low", "target_type": "context", "target": "a", "value": True, "reason": "A.", "impact": "low"},
                {"id": "medium", "target_type": "context", "target": "b", "value": True, "reason": "B.", "impact": "medium"},
                {"id": "high", "target_type": "context", "target": "c", "value": True, "reason": "C.", "impact": "high"},
            ],
        }
    )
    summary = ResidualBuilder(system).assumption_summary()
    assert summary.total_confidence_penalty == pytest.approx(0.37)
    assert summary.confidence_factor == pytest.approx(0.63)
