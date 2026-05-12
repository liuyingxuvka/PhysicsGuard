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


def system(components: list[dict]) -> SystemSpec:
    return SystemSpec.model_validate({"system_name": "control_signal", "components": components})


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return system([{"id": "m", "type": module_type, "parameters": parameters}])


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def referenced_system(module: dict) -> SystemSpec:
    return system(
        [
            {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            {"id": "out", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            module,
        ]
    )


def test_default_registry_includes_control_signal_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "GainBiasModule",
        "SumModule",
        "ProductModule",
        "RatioModule",
        "UnitScaleModule",
        "SaturationModule",
        "RateLimiterModule",
        "FirstOrderLagModule",
        "SensorScaleOffsetModule",
        "MappedSignalModule",
    }.issubset(registered)


def test_gain_bias_zero_residual() -> None:
    record = records_for(
        one_module("GainBiasModule", {"gain": 2.0, "bias": 1.0}),
        {"m.x": 2.0, "m.y": 5.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "gain_bias_mismatch"
    assert record.role == "equation"


def test_gain_bias_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(one_module("GainBiasModule", {"residual_scale": 0.0})).build_registry()


def test_sum_zero_residual() -> None:
    spec = referenced_system(
        {
            "id": "sum",
            "type": "SumModule",
            "parameters": {
                "input_variables": ["a.x", "b.x"],
                "weights": [2.0, 3.0],
                "output_variable": "out.x",
                "bias": 1.0,
            },
        }
    )
    record = [
        record
        for record in records_for(spec, {"a.x": 2.0, "b.x": 3.0, "out.x": 14.0})
        if record.diagnostic_key == "sum_relation_mismatch"
    ][0]
    assert record.value == pytest.approx(0.0)
    assert record.role == "equation"


def test_sum_invalid_weights_fail() -> None:
    spec = referenced_system(
        {
            "id": "sum",
            "type": "SumModule",
            "parameters": {
                "input_variables": ["a.x", "b.x"],
                "weights": [1.0],
                "output_variable": "out.x",
            },
        }
    )
    with pytest.raises(ValueError, match="weights length"):
        ResidualBuilder(spec).build_registry()


def test_product_zero_residual() -> None:
    spec = referenced_system(
        {
            "id": "product",
            "type": "ProductModule",
            "parameters": {
                "x1_variable": "a.x",
                "x2_variable": "b.x",
                "output_variable": "out.x",
            },
        }
    )
    record = [
        record
        for record in records_for(spec, {"a.x": 2.0, "b.x": 3.0, "out.x": 6.0})
        if record.diagnostic_key == "product_relation_mismatch"
    ][0]
    assert record.value == pytest.approx(0.0)
    assert record.role == "equation"


def test_product_invalid_variable_fails() -> None:
    spec = referenced_system(
        {
            "id": "product",
            "type": "ProductModule",
            "parameters": {
                "x1_variable": "bad",
                "x2_variable": "b.x",
                "output_variable": "out.x",
            },
        }
    )
    with pytest.raises(ValueError, match="component.variable"):
        ResidualBuilder(spec).build_registry()


def test_ratio_zero_residual() -> None:
    spec = referenced_system(
        {
            "id": "ratio",
            "type": "RatioModule",
            "parameters": {
                "numerator_variable": "a.x",
                "denominator_variable": "b.x",
                "output_variable": "out.x",
            },
        }
    )
    record = [
        record
        for record in records_for(spec, {"a.x": 6.0, "b.x": 3.0, "out.x": 2.0})
        if record.diagnostic_key == "ratio_relation_mismatch"
    ][0]
    assert record.value == pytest.approx(0.0)
    assert record.role == "equation"


def test_ratio_near_zero_denominator_fails() -> None:
    spec = referenced_system(
        {
            "id": "ratio",
            "type": "RatioModule",
            "parameters": {
                "numerator_variable": "a.x",
                "denominator_variable": "b.x",
                "output_variable": "out.x",
                "denominator_min_abs": 0.1,
            },
        }
    )
    with pytest.raises(ValueError, match="denominator"):
        records_for(spec, {"a.x": 1.0, "b.x": 0.0, "out.x": 1.0})


def test_unit_scale_zero_residual_and_metadata() -> None:
    spec = one_module(
        "UnitScaleModule",
        {"factor": 1000.0, "offset": 1.0, "source_unit": "kW", "target_unit": "W"},
    )
    record = records_for(spec, {"m.x": 2.0, "m.y": 2001.0})[0]
    metadata = ResidualBuilder(spec).build_modules()[0].metadata()
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "unit_scale_mismatch"
    assert metadata["source_unit"] == "kW"
    assert metadata["target_unit"] == "W"


def test_unit_scale_requires_factor() -> None:
    with pytest.raises(ValueError, match="factor"):
        ResidualBuilder(one_module("UnitScaleModule", {})).build_registry()


def test_saturation_zero_residual() -> None:
    record = records_for(
        one_module("SaturationModule", {"lower": 0.0, "upper": 1.0}),
        {"m.u": 2.0, "m.y": 1.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "saturation_mismatch"
    assert record.role == "equation"


def test_saturation_invalid_bounds_fail() -> None:
    with pytest.raises(ValueError, match="lower"):
        ResidualBuilder(one_module("SaturationModule", {"lower": 1.0, "upper": 1.0})).build_registry()


def test_rate_limiter_zero_and_violation_post_check() -> None:
    spec = one_module(
        "RateLimiterModule",
        {"dt_s": 1.0, "rising_rate_limit": 1.0, "falling_rate_limit": -1.0},
    )
    ok = records_for(spec, {"m.y_previous": 0.0, "m.y_current": 0.5})[0]
    bad = records_for(spec, {"m.y_previous": 0.0, "m.y_current": 10.0})[0]
    assert ok.value == pytest.approx(0.0)
    assert bad.value == pytest.approx(9.0)
    assert bad.diagnostic_key == "rate_limit_violation"
    assert bad.role == "post_check"


def test_rate_limiter_invalid_parameters_fail() -> None:
    with pytest.raises(ValueError, match="dt_s"):
        ResidualBuilder(
            one_module("RateLimiterModule", {"dt_s": 0.0, "rising_rate_limit": 1.0, "falling_rate_limit": -1.0})
        ).build_registry()


def test_first_order_lag_zero_residual() -> None:
    record = records_for(
        one_module("FirstOrderLagModule", {"tau_s": 2.0, "dt_s": 1.0}),
        {"m.u_current": 10.0, "m.y_previous": 0.0, "m.y_current": 10.0 / 3.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "first_order_lag_mismatch"
    assert record.role == "equation"


def test_first_order_lag_invalid_parameters_fail() -> None:
    with pytest.raises(ValueError, match="tau_s"):
        ResidualBuilder(one_module("FirstOrderLagModule", {"tau_s": 0.0, "dt_s": 1.0})).build_registry()


def test_sensor_scale_offset_zero_residual() -> None:
    record = records_for(
        one_module("SensorScaleOffsetModule", {"scale_factor": 2.0, "offset": 1.0}),
        {"m.true_value": 10.0, "m.measured_value": 21.0},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "sensor_scale_offset_mismatch"
    assert record.role == "equation"


def test_sensor_scale_offset_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(one_module("SensorScaleOffsetModule", {"residual_scale": 0.0})).build_registry()


def test_mapped_signal_declares_variable_without_residuals() -> None:
    spec = one_module(
        "MappedSignalModule",
        {
            "local_name": "cod_load_kg_s",
            "unit": "kg/s",
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "initial_guess": 0.2,
            "scale": 0.1,
            "external_signal": "plant/COD_in",
            "mapping_confidence": "medium",
        },
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    records = builder.diagnostic_residual_records(registry.initial_vector())
    metadata = builder.build_modules()[0].metadata()

    variable = registry.get_record("m.cod_load_kg_s")
    assert variable.unit == "kg/s"
    assert variable.initial_guess == pytest.approx(0.2)
    assert records == []
    assert metadata["external_signal"] == "plant/COD_in"
    assert metadata["mapping_confidence"] == "medium"


def test_mapped_signal_invalid_variable_bounds_fail() -> None:
    with pytest.raises(ValueError, match="lower_bound"):
        ResidualBuilder(
            one_module(
                "MappedSignalModule",
                {"lower_bound": 1.0, "upper_bound": 1.0, "initial_guess": 1.0},
            )
        ).build_registry()


def test_mapped_signal_invalid_local_name_fails() -> None:
    with pytest.raises(ValueError, match="local_name"):
        ResidualBuilder(one_module("MappedSignalModule", {"local_name": "bad.name"})).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "gain_bias.yaml",
        "saturation.yaml",
        "first_order_lag.yaml",
    ],
)
def test_control_signal_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "control" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_saturation_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "control" / "conflict_saturation.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "saturation_mismatch"


def test_rate_limiter_post_check_does_not_pull_solution() -> None:
    spec = load_system_spec(ROOT / "examples" / "control" / "rate_limiter_violation.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.audit_pass
    assert result.variables["rate.y_current"] == pytest.approx(10.0)
    assert report.top_residuals[0].diagnostic_key == "rate_limit_violation"
    assert report.top_residuals[0].role == "post_check"
