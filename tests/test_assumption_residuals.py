from __future__ import annotations

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.schema.system_spec import SystemSpec


def dummy_system(assumptions: list[dict], boundaries: list[dict] | None = None) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": "assumption_residuals",
            "components": [{"id": "d", "type": "DummyResidualModule", "parameters": {"target": 5.0}}],
            "boundaries": boundaries or [],
            "assumptions": assumptions,
        }
    )


def test_variable_assumption_creates_active_assumption_residual() -> None:
    spec = dummy_system(
        [
            {
                "id": "assume_x",
                "target_type": "variable",
                "target": "d.x",
                "value": 5.0,
                "reason": "Missing signal.",
            }
        ]
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    x = registry.dict_to_vector({"d.x": 5.0})
    records = builder.diagnostic_residual_records(x)
    assumption = next(record for record in records if record.source == "assumption")
    assert assumption.role == "assumption"
    assert assumption.participates_in_solver
    assert assumption.diagnostic_key == "assumed_variable_value"


def test_assumption_residual_is_active_in_solver() -> None:
    spec = dummy_system(
        [
            {
                "id": "assume_x",
                "target_type": "variable",
                "target": "d.x",
                "value": 5.0,
                "reason": "Missing signal.",
            }
        ]
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.audit_pass
    assert result.variables["d.x"] == pytest.approx(5.0)


def test_explicit_boundary_preferred_over_variable_assumption_without_override() -> None:
    spec = dummy_system(
        [
            {
                "id": "assume_x",
                "target_type": "variable",
                "target": "d.x",
                "value": 6.0,
                "reason": "Missing signal.",
            }
        ],
        boundaries=[{"variable": "d.x", "value": 5.0}],
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    records = builder.diagnostic_residual_records(registry.dict_to_vector({"d.x": 5.0}))
    assert [record.source for record in records].count("assumption") == 0
    assert [record.source for record in records].count("boundary") == 1
    assert builder.assumption_summary().cards[0].application == "not_applied_existing_boundary"


def test_variable_assumption_override_skips_duplicate_boundary() -> None:
    spec = dummy_system(
        [
            {
                "id": "assume_x",
                "target_type": "variable",
                "target": "d.x",
                "value": 6.0,
                "reason": "Temporary override.",
                "allow_override": True,
            }
        ],
        boundaries=[{"variable": "d.x", "value": 5.0}],
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    records = builder.diagnostic_residual_records(registry.dict_to_vector({"d.x": 6.0}))
    assert [record.source for record in records].count("assumption") == 1
    assert [record.source for record in records].count("boundary") == 0
    assert builder.assumption_summary().cards[0].warnings


def test_missing_component_for_parameter_assumption_fails_clearly() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "missing_component",
            "components": [{"id": "d", "type": "DummyResidualModule", "parameters": {"target": 0.0}}],
            "assumptions": [
                {
                    "id": "assume_parameter",
                    "target_type": "parameter",
                    "target": "missing.target",
                    "value": 1.0,
                    "reason": "Missing parameter.",
                }
            ],
        }
    )
    with pytest.raises(ValueError, match="unknown component"):
        ResidualBuilder(spec)


def test_missing_variable_for_variable_assumption_fails_when_residuals_are_built() -> None:
    spec = dummy_system(
        [
            {
                "id": "assume_missing",
                "target_type": "variable",
                "target": "d.missing",
                "value": 1.0,
                "reason": "Missing signal.",
            }
        ]
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    with pytest.raises(KeyError, match="unknown variable"):
        builder.diagnostic_residual_records(registry.dict_to_vector({"d.x": 5.0}))
