from __future__ import annotations

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.schema.system_spec import SystemSpec


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": module_type,
            "components": [
                {"id": "m", "type": module_type, "parameters": parameters}
            ],
        }
    )


def record_for(
    module_type: str,
    parameters: dict,
    values: dict[str, float],
    residual_name: str,
):
    builder = ResidualBuilder(one_module(module_type, parameters))
    vector = builder.build_registry().dict_to_vector(
        {f"m.{name}": value for name, value in values.items()}
    )
    return next(
        record
        for record in builder.diagnostic_residual_records(vector)
        if record.name == f"m.{residual_name}"
    )


def assert_zero_residual(
    module_type: str,
    parameters: dict,
    values: dict[str, float],
    residual_name: str,
    scale: float,
    diagnostic_key: str,
) -> None:
    record = record_for(module_type, parameters, values, residual_name)
    assert record.name == f"m.{residual_name}"
    assert record.value == pytest.approx(0.0)
    assert record.role == "equation"
    assert record.scale == pytest.approx(scale)
    assert record.diagnostic_key == diagnostic_key


def linear_parameters(**overrides: float) -> dict[str, float]:
    parameters = {
        "a": 2.0,
        "b": 1.0,
        "x_lower_bound": -10.0,
        "x_upper_bound": 10.0,
        "x_initial_guess": 0.0,
        "x_scale": 1.0,
        "y_lower_bound": -20.0,
        "y_upper_bound": 20.0,
        "y_initial_guess": 0.0,
        "y_scale": 1.0,
        "residual_scale": 1.0,
    }
    parameters.update(overrides)
    return parameters


def test_air_oxygen_molar_flow_dna_positive() -> None:
    n_air = 0.1 / 0.21
    assert_zero_residual(
        "AirOxygenMolarFlowModule",
        {"oxygen_mole_fraction": 0.21, "molar_mass_air_kg_mol": 0.0289652},
        {
            "n_dot_O2_mol_s": 0.1,
            "n_dot_air_mol_s": n_air,
            "m_dot_air_kg_s": n_air * 0.0289652,
        },
        "air_oxygen_molar_flow",
        0.001,
        "air_oxygen_molar_flow_mismatch",
    )


def test_air_oxygen_molar_flow_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="oxygen_mole_fraction"):
        ResidualBuilder(
            one_module("AirOxygenMolarFlowModule", {"oxygen_mole_fraction": 0.0})
        ).build_registry()


def test_cell_stack_voltage_dna_positive() -> None:
    assert_zero_residual(
        "CellVoltageStackVoltageModule",
        {"n_cells": 400.0},
        {"V_cell_V": 0.7, "V_stack_V": 280.0},
        "cell_stack_voltage",
        1.0,
        "cell_stack_voltage_mismatch",
    )


def test_cell_stack_voltage_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="n_cells"):
        ResidualBuilder(
            one_module("CellVoltageStackVoltageModule", {"n_cells": 0.0})
        ).build_registry()


def test_chemical_power_lhv_dna_positive() -> None:
    assert_zero_residual(
        "ChemicalPowerLHVModule",
        {"LHV_J_kg": 120_000_000.0},
        {"m_dot_fuel_kg_s": 0.001, "P_chemical_W": 120_000.0},
        "chemical_power_lhv",
        1000.0,
        "chemical_power_lhv_mismatch",
    )


def test_chemical_power_lhv_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="LHV_J_kg"):
        ResidualBuilder(
            one_module("ChemicalPowerLHVModule", {"LHV_J_kg": 0.0})
        ).build_registry()


def test_current_density_dna_positive() -> None:
    assert_zero_residual(
        "CurrentDensityModule",
        {"active_area_m2": 0.1},
        {"current_A": 100.0, "current_density_A_m2": 1000.0},
        "current_density",
        100.0,
        "current_density_mismatch",
    )


def test_current_density_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="active_area_m2"):
        ResidualBuilder(
            one_module("CurrentDensityModule", {"active_area_m2": 0.0})
        ).build_registry()


def test_density_mass_volume_dna_positive() -> None:
    assert_zero_residual(
        "DensityMassVolumeModule",
        {},
        {"mass_kg": 100.0, "rho_kg_m3": 1000.0, "volume_m3": 0.1},
        "density_mass_volume",
        1.0,
        "density_mass_volume_mismatch",
    )


def test_density_mass_volume_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="residual_scale_kg"):
        ResidualBuilder(
            one_module("DensityMassVolumeModule", {"residual_scale_kg": 0.0})
        ).build_registry()


def test_efficiency_dna_positive() -> None:
    assert_zero_residual(
        "EfficiencyModule",
        {},
        {
            "input_power_W": 1000.0,
            "useful_output_power_W": 800.0,
            "efficiency": 0.8,
        },
        "efficiency",
        0.01,
        "efficiency_mismatch",
    )


def test_efficiency_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(
            one_module("EfficiencyModule", {"denominator_min_abs": 0.0})
        ).build_registry()


def test_force_velocity_power_dna_positive() -> None:
    assert_zero_residual(
        "ForceVelocityPowerModule",
        {},
        {"force_N": 100.0, "velocity_m_s": 2.0, "P_W": 200.0},
        "force_velocity_power",
        1000.0,
        "force_velocity_power_mismatch",
    )


def test_force_velocity_power_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="residual_scale_W"):
        ResidualBuilder(
            one_module("ForceVelocityPowerModule", {"residual_scale_W": 0.0})
        ).build_registry()


def test_ideal_gas_density_dna_positive() -> None:
    density = 101325.0 * 0.0289652 / (8.314462618 * 300.0)
    assert_zero_residual(
        "IdealGasDensityModule",
        {"molar_mass_kg_mol": 0.0289652},
        {"p_Pa": 101325.0, "T_K": 300.0, "rho_kg_m3": density},
        "ideal_gas_density",
        0.1,
        "ideal_gas_density_mismatch",
    )


def test_ideal_gas_density_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="molar_mass_kg_mol"):
        ResidualBuilder(
            one_module("IdealGasDensityModule", {"molar_mass_kg_mol": 0.0})
        ).build_registry()


def test_linear_relation_dna_positive() -> None:
    assert_zero_residual(
        "LinearRelationModule",
        linear_parameters(),
        {"x": 2.0, "y": 5.0},
        "linear_relation",
        1.0,
        "linear_relation_mismatch",
    )


def test_linear_relation_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(
            one_module(
                "LinearRelationModule", linear_parameters(residual_scale=0.0)
            )
        ).build_registry()


def test_linear_spring_force_dna_positive() -> None:
    assert_zero_residual(
        "LinearSpringForceModule",
        {"stiffness_N_m": 1000.0},
        {"displacement_m": 0.01, "force_N": 10.0},
        "linear_spring_force",
        1.0,
        "linear_spring_force_mismatch",
    )


def test_linear_spring_force_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="stiffness_N_m"):
        ResidualBuilder(
            one_module("LinearSpringForceModule", {"stiffness_N_m": -1.0})
        ).build_registry()


def test_mass_molar_flow_conversion_dna_positive() -> None:
    assert_zero_residual(
        "MassMolarFlowConversionModule",
        {"molar_mass_kg_mol": 0.002},
        {"n_dot_mol_s": 2.0, "m_dot_kg_s": 0.004},
        "mass_molar_flow_conversion",
        0.001,
        "mass_molar_flow_conversion_mismatch",
    )


def test_mass_molar_flow_conversion_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="molar_mass_kg_mol"):
        ResidualBuilder(
            one_module("MassMolarFlowConversionModule", {"molar_mass_kg_mol": 0.0})
        ).build_registry()


def test_mole_fraction_flow_dna_positive() -> None:
    assert_zero_residual(
        "MoleFractionFlowModule",
        {},
        {
            "total_n_dot_mol_s": 10.0,
            "species_n_dot_mol_s": 2.1,
            "mole_fraction": 0.21,
        },
        "mole_fraction_flow",
        0.001,
        "mole_fraction_flow_mismatch",
    )


def test_mole_fraction_flow_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="residual_scale_mol_s"):
        ResidualBuilder(
            one_module("MoleFractionFlowModule", {"residual_scale_mol_s": 0.0})
        ).build_registry()


def test_pressure_ratio_dna_positive() -> None:
    assert_zero_residual(
        "PressureRatioModule",
        {},
        {"p_in_Pa": 100000.0, "p_out_Pa": 200000.0, "pressure_ratio": 2.0},
        "pressure_ratio",
        0.1,
        "pressure_ratio_mismatch",
    )


def test_pressure_ratio_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(
            one_module("PressureRatioModule", {"denominator_min_abs": 0.0})
        ).build_registry()


def test_specific_enthalpy_flow_dna_positive() -> None:
    assert_zero_residual(
        "SpecificEnthalpyFlowModule",
        {"cp_J_kgK": 4180.0, "T_ref_K": 300.0},
        {"m_dot_kg_s": 0.1, "T_K": 310.0, "H_dot_W": 4180.0},
        "specific_enthalpy_flow",
        1000.0,
        "specific_enthalpy_flow_mismatch",
    )


def test_specific_enthalpy_flow_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="cp_J_kgK"):
        ResidualBuilder(
            one_module("SpecificEnthalpyFlowModule", {"cp_J_kgK": 0.0})
        ).build_registry()


def test_stack_chemical_efficiency_dna_positive() -> None:
    assert_zero_residual(
        "StackChemicalEfficiencyModule",
        {},
        {"P_stack_W": 500.0, "P_chemical_W": 1000.0, "efficiency": 0.5},
        "stack_chemical_efficiency",
        0.01,
        "stack_chemical_efficiency_mismatch",
    )


def test_stack_chemical_efficiency_dna_counterexample() -> None:
    with pytest.raises(ValueError, match="denominator_min_abs"):
        ResidualBuilder(
            one_module(
                "StackChemicalEfficiencyModule", {"denominator_min_abs": 0.0}
            )
        ).build_registry()
