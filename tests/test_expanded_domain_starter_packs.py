from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples" / "hierarchical"

PACKS = [{'slug': 'cross_domain_audit_primitives', 'level0': 'level_0_cross_domain_primitives.yaml', 'conflict': 'conflict_level_0_bad_temperature_offset.yaml', 'level1': 'level_1_units_sensors_boundary_time.yaml', 'root': 'cross_domain_audit_primitives', 'diagnostic': 'unit_scale_mismatch', 'blocks': ['explicit_unit_conversion', 'sensor_calibration', 'boundary_loss_accounting', 'time_alignment']}, {'slug': 'oil_gas_pipeline_storage', 'level0': 'level_0_oil_gas_balance.yaml', 'conflict': 'conflict_level_0_unmetered_pipeline_leak.yaml', 'level1': 'level_1_pipeline_compression_storage.yaml', 'root': 'oil_gas_pipeline_storage', 'diagnostic': 'aggregate_mass_balance_mismatch', 'blocks': ['pipeline_compression', 'pipeline_mass_accounting', 'terminal_storage_transfer']}, {'slug': 'water_supply_network', 'level0': 'level_0_water_supply_balance.yaml', 'conflict': 'conflict_level_0_unmetered_leakage.yaml', 'level1': 'level_1_source_pump_distribution_storage.yaml', 'root': 'water_supply_network', 'diagnostic': 'aggregate_mass_balance_mismatch', 'blocks': ['distribution_water_accounting', 'pump_station_power']}, {'slug': 'manufacturing_thermal_process', 'level0': 'level_0_manufacturing_thermal_balance.yaml', 'conflict': 'conflict_level_0_missing_exhaust_loss.yaml', 'level1': 'level_1_furnace_line_material_balance.yaml', 'root': 'manufacturing_thermal_process', 'diagnostic': 'aggregate_thermal_balance_mismatch', 'blocks': ['furnace_heat_accounting', 'production_line_power', 'material_yield_accounting']}, {'slug': 'mining_metallurgy', 'level0': 'level_0_mining_metallurgy_balance.yaml', 'conflict': 'conflict_level_0_missing_tailings.yaml', 'level1': 'level_1_ore_mill_slurry_balance.yaml', 'root': 'mining_metallurgy', 'diagnostic': 'aggregate_mass_balance_mismatch', 'blocks': ['ore_mass_accounting', 'mill_power_accounting', 'slurry_water_accounting']}, {'slug': 'combustion_boiler_furnace', 'level0': 'level_0_combustion_boiler_balance.yaml', 'conflict': 'conflict_level_0_missing_stack_loss.yaml', 'level1': 'level_1_fuel_air_heat_draft_balance.yaml', 'root': 'combustion_boiler_furnace', 'diagnostic': 'aggregate_thermal_balance_mismatch', 'blocks': ['boiler_heat_accounting', 'air_flue_mass_accounting', 'draft_fan_power']}, {'slug': 'geothermal_underground_wells', 'level0': 'level_0_geothermal_well_balance.yaml', 'conflict': 'conflict_level_0_missing_brine_loss.yaml', 'level1': 'level_1_production_reinjection_heat_balance.yaml', 'root': 'geothermal_underground_wells', 'diagnostic': 'aggregate_mass_balance_mismatch', 'blocks': ['well_mass_accounting', 'geothermal_heat_accounting', 'reinjection_pump_power']}, {'slug': 'cold_chain_logistics', 'level0': 'level_0_cold_chain_logistics_balance.yaml', 'conflict': 'conflict_level_0_missing_door_gain.yaml', 'level1': 'level_1_warehouse_truck_fleet_balance.yaml', 'root': 'cold_chain_logistics', 'diagnostic': 'aggregate_thermal_balance_mismatch', 'blocks': ['warehouse_thermal_accounting', 'truck_cooling_accounting', 'fleet_power_accounting']}, {'slug': 'robotics_mechatronics', 'level0': 'level_0_robotics_mechatronics_balance.yaml', 'conflict': 'conflict_level_0_missing_drive_loss.yaml', 'level1': 'level_1_power_joint_thermal_actuator_balance.yaml', 'root': 'robotics_mechatronics', 'diagnostic': 'aggregate_power_balance_mismatch', 'blocks': ['robot_power_chain', 'joint_thermal_accounting', 'pneumatic_actuator_accounting']}, {'slug': 'aerospace_satellite_thermal', 'level0': 'level_0_satellite_power_thermal_balance.yaml', 'conflict': 'conflict_level_0_missing_radiator_heat.yaml', 'level1': 'level_1_satellite_power_thermal_storage_balance.yaml', 'root': 'aerospace_satellite_thermal', 'diagnostic': 'aggregate_thermal_balance_mismatch', 'blocks': ['satellite_power_accounting', 'satellite_thermal_accounting']}, {'slug': 'medical_bioprocess_equipment', 'level0': 'level_0_medical_bioprocess_equipment_balance.yaml', 'conflict': 'conflict_level_0_missing_ventilator_leak.yaml', 'level1': 'level_1_ventilator_dialysis_sterilizer_incubator.yaml', 'root': 'medical_bioprocess_equipment', 'diagnostic': 'aggregate_mass_balance_mismatch', 'blocks': ['ventilator_flow_accounting', 'dialysis_fluid_accounting', 'sterilizer_incubator_thermal']}]


def run_template(slug: str, name: str):
    spec = load_hierarchical_audit_spec(BASE / slug / name)
    return HierarchicalAuditRunner(spec).run(top_n_residuals=20, top_n_blocks=10)


@pytest.mark.parametrize("pack", PACKS)
def test_expanded_domain_level_0_templates_pass(pack: dict[str, object]) -> None:
    report = run_template(pack["slug"], pack["level0"])
    assert report.optimization_success
    assert report.audit_pass
    assert report.top_blocks[0].block_id == pack["root"]


@pytest.mark.parametrize("pack", PACKS)
def test_expanded_domain_level_0_conflicts_recommend_refinement(pack: dict[str, object]) -> None:
    report = run_template(pack["slug"], pack["conflict"])
    assert report.optimization_success
    assert not report.audit_pass
    assert report.top_blocks[0].block_id == pack["root"]
    diagnostics = {residual.diagnostic_key for residual in report.top_residuals}
    assert pack["diagnostic"] in diagnostics
    assert report.recommended_refinements


@pytest.mark.parametrize("pack", PACKS)
def test_expanded_domain_level_1_templates_pass(pack: dict[str, object]) -> None:
    report = run_template(pack["slug"], pack["level1"])
    assert report.optimization_success
    assert report.audit_pass
    block_ids = {block.block_id for block in report.top_blocks}
    assert set(pack["blocks"]).issubset(block_ids)


@pytest.mark.parametrize("pack", PACKS)
def test_expanded_domain_templates_use_real_mapped_or_signal_modules(pack: dict[str, object]) -> None:
    for path in (BASE / pack["slug"]).glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "DummyResidualModule" not in text
        assert "MappedSignalModule" in text or "UnitScaleModule" in text
