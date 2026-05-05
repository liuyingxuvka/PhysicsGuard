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
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def test_registry_includes_component_map_modules() -> None:
    assert {"LookupTable2DModule", "EfficiencyMap2DModule"}.issubset(
        set(default_module_registry().registered_types())
    )


def test_lookup_table_2d_grid_and_bilinear_zero_residual() -> None:
    spec = one_module(
        "LookupTable2DModule",
        {
            "x_points": [0.0, 1.0],
            "y_points": [0.0, 1.0],
            "z_values": [[0.0, 1.0], [1.0, 2.0]],
        },
    )
    grid = records_for(spec, {"m.x": 1.0, "m.y": 1.0, "m.z": 2.0})[0]
    interp = records_for(spec, {"m.x": 0.5, "m.y": 0.5, "m.z": 1.0})[0]
    assert grid.value == pytest.approx(0.0)
    assert interp.value == pytest.approx(0.0)
    assert interp.diagnostic_key == "lookup_table_2d_mismatch"
    assert interp.role == "equation"


@pytest.mark.parametrize(
    ("parameters", "match"),
    [
        ({"x_points": [0.0], "y_points": [0.0, 1.0], "z_values": [[0.0], [1.0]]}, "x_points"),
        ({"x_points": [1.0, 0.0], "y_points": [0.0, 1.0], "z_values": [[0.0, 1.0], [1.0, 2.0]]}, "x_points"),
        ({"x_points": [0.0, 1.0], "y_points": [0.0, 1.0], "z_values": [[0.0, 1.0]]}, "z_values"),
    ],
)
def test_lookup_table_2d_invalid_map_fails(parameters: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ResidualBuilder(one_module("LookupTable2DModule", parameters)).build_registry()


def test_lookup_table_2d_extrapolation_behavior() -> None:
    params = {
        "x_points": [0.0, 1.0],
        "y_points": [0.0, 1.0],
        "z_values": [[0.0, 1.0], [1.0, 2.0]],
    }
    with pytest.raises(ValueError, match="outside table range"):
        records_for(one_module("LookupTable2DModule", params), {"m.x": 2.0, "m.y": 0.5, "m.z": 1.0})
    held = records_for(
        one_module("LookupTable2DModule", {**params, "extrapolation": "hold"}),
        {"m.x": 2.0, "m.y": 0.5, "m.z": 1.5},
    )[0]
    assert held.value == pytest.approx(0.0)


def test_efficiency_map_2d_interpolation_and_invalid_map() -> None:
    spec = one_module(
        "EfficiencyMap2DModule",
        {
            "x_points": [0.0, 1.0],
            "y_points": [0.0, 1.0],
            "efficiency_values": [[0.7, 0.8], [0.8, 0.9]],
        },
    )
    record = records_for(spec, {"m.x": 0.5, "m.y": 0.5, "m.efficiency": 0.8})[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "efficiency_map_2d_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="efficiency_values"):
        ResidualBuilder(
            one_module(
                "EfficiencyMap2DModule",
                {"x_points": [0.0, 1.0], "y_points": [0.0, 1.0], "efficiency_values": [[0.7]]},
            )
        ).build_registry()


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "examples" / "components" / "maps" / "lookup_table_2d.yaml",
        ROOT / "examples" / "components" / "maps" / "efficiency_map_2d.yaml",
    ],
)
def test_component_map_yaml_examples_solve(path: Path) -> None:
    spec = load_system_spec(path)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
