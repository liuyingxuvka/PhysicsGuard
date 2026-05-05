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


def test_default_registry_includes_thermodynamic_conversion_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "MassMolarFlowConversionModule",
        "MoleFractionFlowModule",
        "VolumetricMassFlowConversionModule",
        "DensityMassVolumeModule",
        "IdealGasDensityModule",
        "SpecificEnthalpyFlowModule",
    }.issubset(registered)


def test_mass_molar_flow_conversion_zero_residual_and_invalid() -> None:
    record = record_for(
        one_module("MassMolarFlowConversionModule", {"molar_mass_kg_mol": 0.002}),
        {"m.n_dot_mol_s": 2.0, "m.m_dot_kg_s": 0.004},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "mass_molar_flow_conversion_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="molar_mass_kg_mol"):
        ResidualBuilder(
            one_module("MassMolarFlowConversionModule", {"molar_mass_kg_mol": 0.0})
        ).build_registry()


def test_mole_fraction_flow_zero_residual_and_invalid() -> None:
    record = record_for(
        one_module("MoleFractionFlowModule", {}),
        {"m.total_n_dot_mol_s": 10.0, "m.species_n_dot_mol_s": 2.1, "m.mole_fraction": 0.21},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "mole_fraction_flow_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="residual_scale_mol_s"):
        ResidualBuilder(one_module("MoleFractionFlowModule", {"residual_scale_mol_s": 0.0})).build_registry()


def test_volumetric_mass_flow_conversion_zero_residual_and_invalid_density() -> None:
    record = record_for(
        one_module("VolumetricMassFlowConversionModule", {"rho_kg_m3": 1000.0}),
        {"m.m_dot_kg_s": 10.0, "m.V_dot_m3_s": 0.01},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "volumetric_mass_flow_conversion_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="rho_kg_m3"):
        ResidualBuilder(
            one_module("VolumetricMassFlowConversionModule", {"rho_kg_m3": 0.0})
        ).build_registry()


def test_density_mass_volume_zero_residual_and_invalid() -> None:
    record = record_for(
        one_module("DensityMassVolumeModule", {}),
        {"m.mass_kg": 100.0, "m.rho_kg_m3": 1000.0, "m.volume_m3": 0.1},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "density_mass_volume_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="residual_scale_kg"):
        ResidualBuilder(one_module("DensityMassVolumeModule", {"residual_scale_kg": 0.0})).build_registry()


def test_ideal_gas_density_zero_residual_and_invalid_inputs() -> None:
    expected = 101325.0 * 0.0289652 / (8.314462618 * 300.0)
    record = record_for(
        one_module("IdealGasDensityModule", {"molar_mass_kg_mol": 0.0289652}),
        {"m.p_Pa": 101325.0, "m.T_K": 300.0, "m.rho_kg_m3": expected},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "ideal_gas_density_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="molar_mass_kg_mol"):
        ResidualBuilder(one_module("IdealGasDensityModule", {"molar_mass_kg_mol": 0.0})).build_registry()

    spec = one_module(
        "IdealGasDensityModule",
        {"molar_mass_kg_mol": 0.0289652, "T_lower_bound": -1.0, "T_initial_guess": 0.0},
    )
    with pytest.raises(ValueError, match="T_K"):
        record_for(spec, {"m.p_Pa": 101325.0, "m.T_K": 0.0, "m.rho_kg_m3": 1.0})


def test_specific_enthalpy_flow_zero_residual_and_invalid_cp() -> None:
    record = record_for(
        one_module("SpecificEnthalpyFlowModule", {"cp_J_kgK": 4180.0, "T_ref_K": 300.0}),
        {"m.m_dot_kg_s": 0.1, "m.T_K": 310.0, "m.H_dot_W": 4180.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "specific_enthalpy_flow_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="cp_J_kgK"):
        ResidualBuilder(
            one_module("SpecificEnthalpyFlowModule", {"cp_J_kgK": 0.0})
        ).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "mass_molar_flow_conversion.yaml",
        "mole_fraction_flow.yaml",
        "volumetric_mass_flow_conversion.yaml",
        "density_mass_volume.yaml",
        "ideal_gas_density.yaml",
        "specific_enthalpy_flow.yaml",
    ],
)
def test_thermodynamic_conversion_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
