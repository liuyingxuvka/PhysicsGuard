from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
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


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def test_default_registry_includes_lookup_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {"LookupTable1DModule", "MapBoundsCheckModule"}.issubset(registered)


def test_lookup_table_zero_residual() -> None:
    spec = one_module(
        "LookupTable1DModule",
        {"x_points": [0.0, 1.0, 2.0], "y_points": [0.0, 10.0, 20.0]},
    )
    record = records_for(spec, {"m.x": 1.5, "m.y": 15.0})[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "lookup_table_1d_mismatch"
    assert record.role == "equation"


def test_lookup_table_invalid_points_fail() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        ResidualBuilder(
            one_module(
                "LookupTable1DModule",
                {"x_points": [0.0, 0.0], "y_points": [0.0, 1.0]},
            )
        ).build_registry()


def test_lookup_table_error_extrapolation_fails_clearly() -> None:
    spec = one_module(
        "LookupTable1DModule",
        {"x_points": [0.0, 1.0], "y_points": [0.0, 10.0]},
    )
    with pytest.raises(ValueError, match="outside table range"):
        records_for(spec, {"m.x": 2.0, "m.y": 20.0})


def test_lookup_table_hold_extrapolation() -> None:
    spec = one_module(
        "LookupTable1DModule",
        {"x_points": [0.0, 1.0], "y_points": [0.0, 10.0], "extrapolation": "hold"},
    )
    record = records_for(spec, {"m.x": 2.0, "m.y": 10.0})[0]
    assert record.value == pytest.approx(0.0)


def test_lookup_table_linear_extrapolation() -> None:
    spec = one_module(
        "LookupTable1DModule",
        {"x_points": [0.0, 1.0], "y_points": [0.0, 10.0], "extrapolation": "linear"},
    )
    record = records_for(spec, {"m.x": 2.0, "m.y": 20.0})[0]
    assert record.value == pytest.approx(0.0)


def test_map_bounds_check_zero_and_violation() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "map_bounds",
            "components": [
                {"id": "signal", "type": "DummyResidualModule", "parameters": {"target": 2.0}},
                {
                    "id": "bounds",
                    "type": "MapBoundsCheckModule",
                    "parameters": {"variable": "signal.x", "lower": 0.0, "upper": 1.0},
                },
            ],
        }
    )
    records = records_for(spec, {"signal.x": 2.0})
    record = [r for r in records if r.diagnostic_key == "map_bounds_violation"][0]
    assert record.value == pytest.approx(1.0)
    assert record.role == "post_check"


def test_map_bounds_invalid_parameters_fail() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "bad_bounds",
            "components": [
                {
                    "id": "bounds",
                    "type": "MapBoundsCheckModule",
                    "parameters": {"variable": "signal.x", "lower": 1.0, "upper": 1.0},
                }
            ],
        }
    )
    with pytest.raises(ValueError, match="lower"):
        ResidualBuilder(spec).build_modules()


@pytest.mark.parametrize("example", ["lookup_table_1d.yaml", "map_bounds_violation.yaml"])
def test_lookup_yaml_examples_run(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "control" / example)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_lookup_table_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "control" / "conflict_lookup_table_1d.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "lookup_table_1d_mismatch"


def test_map_bounds_post_check_does_not_pull_solution() -> None:
    spec = load_system_spec(ROOT / "examples" / "control" / "map_bounds_violation.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.audit_pass
    assert result.variables["signal.x"] == pytest.approx(2.0)
    assert report.top_residuals[0].diagnostic_key == "map_bounds_violation"
    assert report.top_residuals[0].role == "post_check"
