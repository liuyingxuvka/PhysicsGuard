from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.physical.constants import UNIVERSAL_GAS_CONSTANT
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def make_system(parameters: dict | None = None) -> SystemSpec:
    params = {"volume_m3": 0.01}
    if parameters:
        params.update(parameters)
    return SystemSpec.model_validate(
        {
            "system_name": "gas",
            "components": [
                {
                    "id": "gas",
                    "type": "IdealGasStateModule",
                    "parameters": params,
                }
            ],
        }
    )


def test_ideal_gas_state_zero_residual() -> None:
    builder = ResidualBuilder(make_system())
    registry = builder.build_registry()
    pressure = UNIVERSAL_GAS_CONSTANT * 300.0 / 0.01
    x = registry.dict_to_vector(
        {
            "gas.p_Pa": pressure,
            "gas.T_K": 300.0,
            "gas.n_mol": 1.0,
        }
    )
    record = builder.diagnostic_residual_records(x)[0]
    assert record.normalized_value == pytest.approx(0.0)
    assert record.role == "equation"
    assert record.diagnostic_key == "ideal_gas_state_mismatch"


def test_ideal_gas_invalid_volume_fails() -> None:
    builder = ResidualBuilder(make_system({"volume_m3": 0.0}))
    with pytest.raises(ValueError, match="volume_m3"):
        builder.build_registry()


def test_ideal_gas_yaml_example_solves_pressure() -> None:
    spec = load_system_spec(ROOT / "examples" / "physical_ideal_gas.yaml")
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    expected_pressure = UNIVERSAL_GAS_CONSTANT * 300.0 / 0.01
    assert result.optimization_success
    assert result.audit_pass
    assert result.variables["gas.p_Pa"] == pytest.approx(expected_pressure, rel=0, abs=1e-2)
