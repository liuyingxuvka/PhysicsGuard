from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def make_system(parameters: dict | None = None) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": "thermal",
            "components": [
                {
                    "id": "coolant",
                    "type": "CoolantHeatBalanceModule",
                    "parameters": parameters or {},
                }
            ],
        }
    )


def test_coolant_heat_balance_zero_residual() -> None:
    builder = ResidualBuilder(make_system())
    registry = builder.build_registry()
    x = registry.dict_to_vector(
        {
            "coolant.m_dot_kg_s": 0.1,
            "coolant.T_in_K": 300.0,
            "coolant.T_out_K": 310.0,
            "coolant.Q_dot_W": 4180.0,
        }
    )
    record = builder.diagnostic_residual_records(x)[0]
    assert record.normalized_value == pytest.approx(0.0)
    assert record.role == "equation"
    assert record.diagnostic_key == "coolant_heat_balance_mismatch"


def test_coolant_heat_balance_nonzero_residual_sign() -> None:
    builder = ResidualBuilder(make_system())
    registry = builder.build_registry()
    high_q = registry.dict_to_vector(
        {
            "coolant.m_dot_kg_s": 0.1,
            "coolant.T_in_K": 300.0,
            "coolant.T_out_K": 310.0,
            "coolant.Q_dot_W": 5000.0,
        }
    )
    low_flow = registry.dict_to_vector(
        {
            "coolant.m_dot_kg_s": 0.05,
            "coolant.T_in_K": 300.0,
            "coolant.T_out_K": 310.0,
            "coolant.Q_dot_W": 4180.0,
        }
    )
    assert builder.diagnostic_residual_records(high_q)[0].value == pytest.approx(820.0)
    assert builder.diagnostic_residual_records(low_flow)[0].value == pytest.approx(2090.0)


def test_coolant_heat_balance_invalid_parameter_fails() -> None:
    builder = ResidualBuilder(make_system({"cp_J_kgK": 0.0}))
    with pytest.raises(ValueError, match="cp_J_kgK"):
        builder.build_registry()


def test_coolant_heat_balance_variable_overrides_work() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "thermal_override",
            "components": [
                {
                    "id": "coolant",
                    "type": "CoolantHeatBalanceModule",
                    "parameters": {},
                    "variable_overrides": {
                        "Q_dot_W": {
                            "lower_bound": -10.0,
                            "upper_bound": 10_000.0,
                            "initial_guess": 500.0,
                            "scale": 500.0,
                        }
                    },
                }
            ],
        }
    )
    record = ResidualBuilder(spec).build_registry().get_record("coolant.Q_dot_W")
    assert record.initial_guess == 500.0
    assert record.scale == 500.0


def test_coolant_heat_balance_yaml_example_solves() -> None:
    spec = load_system_spec(ROOT / "examples" / "physical_coolant_heat_balance.yaml")
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
    assert result.variables["coolant.Q_dot_W"] == pytest.approx(4180.0, rel=0, abs=1e-2)
