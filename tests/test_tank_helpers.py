from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def one_module(module_type: str, parameters: dict) -> SystemSpec:
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


def test_default_registry_includes_tank_helpers() -> None:
    registered = set(default_module_registry().registered_types())
    assert {"TankLevelVolumeModule", "TankVolumeRateModule"}.issubset(registered)


def test_tank_level_volume_zero_residual_and_invalid_area() -> None:
    record = record_for(
        one_module("TankLevelVolumeModule", {"area_m2": 3.0}),
        {"m.level_m": 2.0, "m.volume_m3": 6.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "tank_level_volume_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="area_m2"):
        ResidualBuilder(one_module("TankLevelVolumeModule", {"area_m2": 0.0})).build_registry()


def test_tank_volume_rate_zero_residual_and_invalid_dt() -> None:
    record = record_for(
        one_module("TankVolumeRateModule", {"dt_s": 10.0}),
        {
            "m.volume_previous_m3": 1.0,
            "m.V_dot_in_m3_s": 0.1,
            "m.V_dot_out_m3_s": 0.02,
            "m.volume_current_m3": 1.8,
        },
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "tank_volume_rate_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="dt_s"):
        ResidualBuilder(one_module("TankVolumeRateModule", {"dt_s": 0.0})).build_registry()


@pytest.mark.parametrize("example", ["tank_level_volume.yaml", "tank_volume_rate.yaml"])
def test_tank_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
