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
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def comp_expected(pr: float = 2.0, t_in: float = 300.0, m_dot: float = 0.1, cp: float = 1000.0, gamma: float = 1.4, eta: float = 0.7):
    rise = pr ** ((gamma - 1.0) / gamma) - 1.0
    return t_in * (1.0 + rise / eta), m_dot * cp * t_in * rise / eta


def test_registry_includes_component_fluid_machine_modules() -> None:
    assert {"CompressorSimpleModule", "CompressorMapSimpleModule", "PumpSimpleModule", "PumpMapSimpleModule"}.issubset(
        set(default_module_registry().registered_types())
    )


def test_compressor_simple_zero_residual_and_invalid_parameters() -> None:
    t_out, power = comp_expected()
    records = records_for(
        one_module("CompressorSimpleModule", {"cp_J_kgK": 1000.0, "gamma": 1.4}),
        {
            "m.p_in_Pa": 100000.0,
            "m.p_out_Pa": 200000.0,
            "m.T_in_K": 300.0,
            "m.T_out_K": t_out,
            "m.m_dot_kg_s": 0.1,
            "m.P_shaft_W": power,
            "m.pressure_ratio": 2.0,
            "m.efficiency": 0.7,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    assert {r.diagnostic_key for r in records} == {
        "compressor_pressure_ratio_mismatch",
        "compressor_temperature_rise_mismatch",
        "compressor_power_mismatch",
    }
    with pytest.raises(ValueError, match="gamma"):
        ResidualBuilder(one_module("CompressorSimpleModule", {"gamma": 1.0})).build_registry()


def test_compressor_map_simple_zero_residual_and_invalid_map() -> None:
    pr = 1.75
    eta = 0.75
    t_out, power = comp_expected(pr=pr, eta=eta)
    records = records_for(
        one_module(
            "CompressorMapSimpleModule",
            {
                "speed_points": [0.0, 2.0],
                "flow_points": [0.0, 2.0],
                "pressure_ratio_values": [[1.0, 2.0], [1.5, 2.5]],
                "efficiency_values": [[0.7, 0.75], [0.75, 0.8]],
                "cp_J_kgK": 1000.0,
            },
        ),
        {
            "m.corrected_speed": 1.0,
            "m.corrected_mass_flow": 1.0,
            "m.p_in_Pa": 100000.0,
            "m.p_out_Pa": 175000.0,
            "m.T_in_K": 300.0,
            "m.T_out_K": t_out,
            "m.m_dot_kg_s": 0.1,
            "m.P_shaft_W": power,
            "m.pressure_ratio": pr,
            "m.efficiency": eta,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in records)
    with pytest.raises(ValueError, match="pressure_ratio_values"):
        ResidualBuilder(
            one_module(
                "CompressorMapSimpleModule",
                {"speed_points": [0.0, 1.0], "flow_points": [0.0, 1.0], "pressure_ratio_values": [[1.0]], "efficiency_values": [[0.7, 0.8], [0.8, 0.9]]},
            )
        ).build_registry()


def test_pump_simple_and_map_zero_residuals_and_invalid_parameters() -> None:
    simple = records_for(
        one_module("PumpSimpleModule", {"rho_kg_m3": 1000.0}),
        {"m.p_in_Pa": 100000.0, "m.p_out_Pa": 200000.0, "m.m_dot_kg_s": 1.0, "m.P_shaft_W": 125.0, "m.efficiency": 0.8},
    )[0]
    assert simple.value == pytest.approx(0.0)
    assert simple.diagnostic_key == "pump_power_mismatch"
    mapped = records_for(
        one_module(
            "PumpMapSimpleModule",
            {
                "speed_points": [100.0, 200.0],
                "flow_points": [1.0, 2.0],
                "delta_p_values": [[100000.0, 200000.0], [150000.0, 300000.0]],
                "efficiency_values": [[0.8, 0.82], [0.78, 0.8]],
                "rho_kg_m3": 997.0,
            },
        ),
        {"m.speed_rad_s": 100.0, "m.m_dot_kg_s": 1.0, "m.delta_p_Pa": 100000.0, "m.efficiency": 0.8, "m.P_shaft_W": 100000.0 / 997.0 / 0.8},
    )
    assert all(record.value == pytest.approx(0.0) for record in mapped)
    with pytest.raises(ValueError, match="rho_kg_m3"):
        ResidualBuilder(one_module("PumpSimpleModule", {"rho_kg_m3": 0.0})).build_registry()


@pytest.mark.parametrize("name", ["compressor_simple.yaml", "compressor_map_simple.yaml", "pump_simple.yaml", "pump_map_simple.yaml"])
def test_component_fluid_machine_yaml_examples_solve(name: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "fluid_machines" / name)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_compressor_simple_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "fluid_machines" / "conflict_compressor_simple.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key in {
        "compressor_pressure_ratio_mismatch",
        "compressor_temperature_rise_mismatch",
        "compressor_power_mismatch",
    }
