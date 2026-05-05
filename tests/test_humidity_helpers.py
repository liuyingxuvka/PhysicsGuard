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


def test_default_registry_includes_humidity_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "RelativeHumidityFromPartialPressureModule",
        "HumidityRatioFromPartialPressureModule",
        "WaterVaporMoleFractionModule",
    }.issubset(registered)


def test_relative_humidity_zero_residual_and_denominator_safety() -> None:
    record = record_for(
        one_module("RelativeHumidityFromPartialPressureModule", {}),
        {"m.p_vapor_Pa": 1000.0, "m.p_saturation_Pa": 2000.0, "m.relative_humidity": 0.5},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "relative_humidity_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="p_saturation_Pa"):
        record_for(
            one_module(
                "RelativeHumidityFromPartialPressureModule",
                {"p_saturation_lower_bound": -1.0, "p_saturation_initial_guess": 0.0},
            ),
            {"m.p_vapor_Pa": 1000.0, "m.p_saturation_Pa": 0.0, "m.relative_humidity": 0.5},
        )


def test_relative_humidity_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(
            one_module("RelativeHumidityFromPartialPressureModule", {"residual_scale": 0.0})
        ).build_registry()


def test_humidity_ratio_zero_residual_and_denominator_safety() -> None:
    expected = 0.62198 * 2000.0 / (101325.0 - 2000.0)
    record = record_for(
        one_module("HumidityRatioFromPartialPressureModule", {}),
        {"m.p_total_Pa": 101325.0, "m.p_vapor_Pa": 2000.0, "m.humidity_ratio_kg_kg": expected},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "humidity_ratio_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="safely positive"):
        record_for(
            one_module(
                "HumidityRatioFromPartialPressureModule",
                {
                    "p_total_lower_bound": -1.0,
                    "p_total_initial_guess": 0.0,
                    "p_vapor_lower_bound": -1.0,
                    "p_vapor_initial_guess": 0.0,
                },
            ),
            {"m.p_total_Pa": 1000.0, "m.p_vapor_Pa": 1000.0, "m.humidity_ratio_kg_kg": 0.0},
        )


def test_humidity_ratio_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(
            one_module("HumidityRatioFromPartialPressureModule", {"denominator_min_abs": 0.0})
        ).build_registry()


def test_water_vapor_mole_fraction_zero_residual_and_denominator_safety() -> None:
    record = record_for(
        one_module("WaterVaporMoleFractionModule", {}),
        {"m.p_total_Pa": 101325.0, "m.p_vapor_Pa": 2000.0, "m.x_vapor": 2000.0 / 101325.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "water_vapor_mole_fraction_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="p_total_Pa"):
        record_for(
            one_module(
                "WaterVaporMoleFractionModule",
                {"p_total_lower_bound": -1.0, "p_total_initial_guess": 0.0},
            ),
            {"m.p_total_Pa": 0.0, "m.p_vapor_Pa": 0.0, "m.x_vapor": 0.0},
        )


@pytest.mark.parametrize(
    "example",
    [
        "relative_humidity.yaml",
        "humidity_ratio.yaml",
        "water_vapor_mole_fraction.yaml",
    ],
)
def test_humidity_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
