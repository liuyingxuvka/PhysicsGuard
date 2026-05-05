from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def system(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": module_type,
            "components": [{"id": "m", "type": module_type, "parameters": parameters}],
        }
    )


def record_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)[0]


def test_ohmic_relation_zero_residual() -> None:
    record = record_for(
        system("OhmicRelationModule", {"resistance_ohm": 0.1}),
        {"m.current_A": 100.0, "m.V_drop_V": 10.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "ohmic_relation_mismatch"
    assert record.role == "equation"


def test_ohmic_relation_invalid_resistance_fails() -> None:
    with pytest.raises(ValueError, match="resistance_ohm"):
        ResidualBuilder(system("OhmicRelationModule", {"resistance_ohm": -1.0})).build_registry()


def test_electrical_power_zero_residual_and_sign_behavior() -> None:
    spec = system("ElectricalPowerModule", {})
    record = record_for(spec, {"m.V_V": 400.0, "m.current_A": 10.0, "m.P_W": 4000.0})
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "electrical_power_mismatch"
    assert record.role == "equation"

    signed = record_for(spec, {"m.V_V": -10.0, "m.current_A": 5.0, "m.P_W": -50.0})
    assert signed.value == pytest.approx(0.0)


def test_electrical_power_invalid_residual_scale_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale_W"):
        ResidualBuilder(system("ElectricalPowerModule", {"residual_scale_W": 0.0})).build_registry()


@pytest.mark.parametrize("example", ["ohmic_relation.yaml", "electrical_power.yaml"])
def test_electrical_foundation_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
