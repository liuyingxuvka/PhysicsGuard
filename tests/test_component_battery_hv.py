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
EXAMPLES = ROOT / "examples" / "components" / "battery_hv"


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def solve_example(name: str):
    spec = load_system_spec(EXAMPLES / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result, top_n=80)
    return result, report


def test_registry_includes_battery_hv_modules() -> None:
    assert {
        "BatterySOCStepModule",
        "BatteryOCVMapModule",
        "BatteryInternalResistanceModule",
        "BatteryPackPowerModule",
        "BatteryPowerLimitCheckModule",
        "HVBusPowerBalanceModule",
        "ChargerSimpleModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "battery_soc_step.yaml",
        "battery_ocv_map.yaml",
        "battery_internal_resistance.yaml",
        "battery_pack_power.yaml",
        "battery_power_limit_check.yaml",
        "hv_bus_power_balance.yaml",
        "charger_simple.yaml",
    ],
)
def test_battery_hv_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.residual_norm)
    assert all(item.role in {"equation", "boundary", "post_check"} for item in report.top_residuals)


def test_hv_bus_conflict_fails_audit() -> None:
    result, report = solve_example("conflict_hv_bus_power_balance.yaml")
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "hv_bus_power_balance_mismatch"


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        ("BatterySOCStepModule", {"capacity_C": 0.0, "dt_s": 1.0}, "capacity_C"),
        ("BatterySOCStepModule", {"capacity_C": 1.0, "dt_s": 0.0}, "dt_s"),
        ("BatterySOCStepModule", {"capacity_C": 1.0, "dt_s": 1.0, "sign_convention": "bad"}, "sign_convention"),
        ("BatteryOCVMapModule", {"SOC_points": [0.0, 0.0], "OCV_points_V": [300.0, 400.0]}, "SOC_points"),
        ("BatteryPowerLimitCheckModule", {"max_discharge_power_W": -1.0, "max_charge_power_W": 1.0}, "max_discharge_power_W"),
    ],
)
def test_battery_hv_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()


def test_battery_power_limit_post_check_does_not_pull_solution() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "battery_limit_violation",
            "components": [
                {
                    "id": "lim",
                    "type": "BatteryPowerLimitCheckModule",
                    "parameters": {"max_discharge_power_W": 1000.0, "max_charge_power_W": 1000.0},
                }
            ],
            "boundaries": [
                {"variable": "lim.power_W", "value": 2000.0},
                {"variable": "lim.SOC", "value": 0.5},
                {"variable": "lim.temperature_K", "value": 300.0},
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "battery_discharge_power_limit_violation"
    assert report.top_residuals[0].role == "post_check"
