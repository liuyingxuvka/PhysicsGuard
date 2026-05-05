from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "components" / "fluid_network"


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def solve_example(name: str):
    spec = load_system_spec(EXAMPLES / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result, top_n=50)
    return result, report


def test_registry_includes_fluid_network_modules() -> None:
    assert {
        "PipeSegmentSimpleModule",
        "DuctSegmentSimpleModule",
        "LumpedGasVolumeStepModule",
        "LumpedLiquidVolumeStepModule",
        "FlowSplitModule",
        "FlowMergeTemperatureModule",
        "CheckValveSimpleModule",
        "ThrottleValveSimpleModule",
        "PressureReliefValveCheckModule",
        "LeakOrBypassLinearModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "pipe_segment_simple.yaml",
        "duct_segment_simple.yaml",
        "lumped_gas_volume_step.yaml",
        "lumped_liquid_volume_step.yaml",
        "flow_split.yaml",
        "flow_merge_temperature.yaml",
        "check_valve_simple.yaml",
        "throttle_valve_simple.yaml",
        "pressure_relief_valve_check.yaml",
        "leak_or_bypass_linear.yaml",
    ],
)
def test_fluid_network_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.max_abs_normalized_residual)
    assert all(item.role in {"equation", "boundary", "post_check"} for item in report.top_residuals)


@pytest.mark.parametrize(
    ("name", "expected_key"),
    [
        ("conflict_flow_split.yaml", "flow_split_branch_1_mismatch"),
        ("conflict_throttle_valve_simple.yaml", "throttle_valve_flow_mismatch"),
    ],
)
def test_fluid_network_conflict_examples_fail_audit(name: str, expected_key: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == expected_key


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        ("PipeSegmentSimpleModule", {"rho_kg_m3": 0.0, "diameter_m": 0.1, "length_m": 1.0}, "rho_kg_m3"),
        ("PipeSegmentSimpleModule", {"rho_kg_m3": 1000.0, "diameter_m": 0.0, "length_m": 1.0}, "diameter_m"),
        ("DuctSegmentSimpleModule", {"rho_kg_m3": 1.2, "area_m2": 0.0, "K_total": 1.0}, "area_m2"),
        ("LumpedGasVolumeStepModule", {"volume_m3": 0.0, "dt_s": 1.0}, "volume_m3"),
        ("LumpedLiquidVolumeStepModule", {"dt_s": 0.0}, "dt_s"),
        ("ThrottleValveSimpleModule", {"CdA_max_m2": 0.0, "rho_kg_m3": 1000.0}, "CdA_max_m2"),
        ("LeakOrBypassLinearModule", {"conductance_kg_s_Pa": -1.0}, "conductance_kg_s_Pa"),
    ],
)
def test_fluid_network_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()


def test_check_valve_post_check_does_not_pull_solution() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "check_valve_violation",
            "components": [{"id": "v", "type": "CheckValveSimpleModule", "parameters": {}}],
            "boundaries": [
                {"variable": "v.p_upstream_Pa", "value": 100000.0},
                {"variable": "v.p_downstream_Pa", "value": 120000.0},
                {"variable": "v.m_dot_kg_s", "value": 0.1},
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "check_valve_backflow_violation"
    assert report.top_residuals[0].role == "post_check"
