from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnosability import evaluate_fault_variants
from physicsguard.core.hierarchy import HierarchicalAuditRunner, RefinementPlanner, describe_hierarchy
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values


ROOT = Path(__file__).resolve().parents[1] / "examples" / "hierarchical"


TREE_PACKS = tuple(path.parent.name for path in sorted(ROOT.glob("*/tree.yaml")))


LEGACY_BLOCKS = {'cross_domain_audit_primitives': ['boundary_loss_accounting', 'cross_domain_audit_primitives', 'explicit_unit_conversion', 'sensor_calibration', 'time_alignment'], 'oil_gas_pipeline_storage': ['oil_gas_pipeline_storage', 'pipeline_compression', 'pipeline_mass_accounting', 'terminal_storage_transfer'], 'water_supply_network': ['distribution_water_accounting', 'pump_station_power', 'water_supply_network'], 'manufacturing_thermal_process': ['furnace_heat_accounting', 'manufacturing_thermal_process', 'material_yield_accounting', 'production_line_power'], 'mining_metallurgy': ['mill_power_accounting', 'mining_metallurgy', 'ore_mass_accounting', 'slurry_water_accounting'], 'combustion_boiler_furnace': ['air_flue_mass_accounting', 'boiler_heat_accounting', 'combustion_boiler_furnace', 'draft_fan_power'], 'geothermal_underground_wells': ['geothermal_heat_accounting', 'geothermal_underground_wells', 'reinjection_pump_power', 'well_mass_accounting'], 'cold_chain_logistics': ['cold_chain_logistics', 'fleet_power_accounting', 'truck_cooling_accounting', 'warehouse_thermal_accounting'], 'robotics_mechatronics': ['joint_thermal_accounting', 'pneumatic_actuator_accounting', 'robot_power_chain', 'robotics_mechatronics'], 'aerospace_satellite_thermal': ['aerospace_satellite_thermal', 'satellite_power_accounting', 'satellite_thermal_accounting'], 'medical_bioprocess_equipment': ['dialysis_fluid_accounting', 'medical_bioprocess_equipment', 'sterilizer_incubator_thermal', 'ventilator_flow_accounting'], 'agriculture_food_bioprocess': ['agriculture_food_bioprocess', 'cold_chain_storage', 'drying_process', 'fermentation_bioreactor', 'greenhouse_climate', 'greenhouse_co2', 'irrigation_crop_water'], 'data_center_electronics_cooling': ['coolant_loop', 'cooling_plant_efficiency', 'data_center_electronics_cooling', 'facility_power_chain', 'it_load_rack_heat', 'room_air_cooling'], 'distribution_power_der': ['der_interface', 'distribution_power_der', 'feeder_section_a', 'feeder_section_b', 'power_quality_voltage', 'substation_transformer'], 'industrial_utilities': ['compressed_air', 'cooling_water', 'industrial_utilities', 'refrigeration_chilled_water', 'steam_condensate', 'utility_power'], 'mobility_extensions': ['aviation_power', 'charging_infrastructure', 'marine_propulsion', 'mobility_extensions', 'offroad_hydraulics', 'rail_traction'], 'process_industry': ['heat_exchange_utility', 'process_industry', 'reactor_conversion', 'rotating_equipment', 'separator_split'], 'renewable_microgrid': ['battery_storage', 'load_dispatch', 'pv_system', 'renewable_microgrid', 'wind_system'], 'stormwater_sewer_drainage': ['catchment_runoff', 'detention_storage', 'pollutant_load', 'pump_station', 'sewer_conveyance', 'stormwater_sewer_drainage'], 'wastewater_treatment': ['aeration_energy', 'biological_reactor', 'secondary_clarifier', 'sludge_recycle', 'wastewater_plant']}


@pytest.mark.parametrize("pack", TREE_PACKS)
def test_connected_starter_tree_has_a_measurable_consistent_reference_and_real_faults(pack, monkeypatch) -> None:
    directory = ROOT / pack
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    observed = load_observed_values(directory / "nominal_observed.yaml")
    original_inputs = spec.model_dump(mode="json"), observed.model_dump(mode="json")
    solutions = []
    original_solve = BoundedSolver.solve

    def capture_reference(solver):
        result = original_solve(solver)
        solutions.append(result.variables)
        return result

    monkeypatch.setattr(BoundedSolver, "solve", capture_reference)
    runner = HierarchicalAuditRunner(spec, directory)
    reference = runner.run()
    assert reference.optimization_success and reference.audit_pass
    assert len(solutions) == 1
    assert 0 < len(observed.variables) < len(solutions[0])
    for name, value in observed.variables.items():
        assert value.value == pytest.approx(solutions[0][name], rel=1e-8, abs=1e-8)
        assert value.unit and value.external_signal and value.source

    monkeypatch.setattr(BoundedSolver, "solve", lambda *args, **kwargs: pytest.fail("observed audits must not reference-solve"))
    evaluated = runner.evaluate_observed(observed, skip_unobserved=True)
    assert evaluated.audit_pass and evaluated.checked_residuals
    assert not evaluated.unchecked_residuals and not evaluated.missing_required_variables
    assert all(row["consistent"] is True for row in evaluated.refinement_checks)
    variants = evaluate_fault_variants(spec, observed, base_dir=directory)
    assert variants["nominal_audit_pass"] and variants["ok"]
    declarations = {variant.id: variant for variant in spec.fault_variants}
    assert any(variant.kind == "fault" for variant in declarations.values())
    assert any(variant.kind == "benign" for variant in declarations.values())
    for row in variants["variants"]:
        if declarations[row["id"]].kind == "fault":
            assert row["detected"] and row["expect_blocks_met"] and not row["audit_pass"]
        else:
            assert row["neutral"] and row["audit_pass"]

    description = describe_hierarchy(spec)
    assert not description["unassigned_components"]
    assert len(description["blocks"]) == len(spec.hierarchy.blocks)
    assert any(connection["scope"] == "between_blocks" for connection in description["connections"])
    blocks = {block.id: block for block in spec.hierarchy.blocks}
    # Keep the original per-domain ownership checks inside the single discovered case.
    assert set(LEGACY_BLOCKS.get(pack, ())) <= blocks.keys()
    assert all(component.type != "DummyResidualModule" for component in spec.system.components)
    if pack in LEGACY_BLOCKS:
        assert any(component.type in {"MappedSignalModule", "UnitScaleModule"} for component in spec.system.components)
    assert all(block.own_audit_pass for block in reference.top_blocks)
    assert any(block.refines for block in blocks.values())
    for block in blocks.values():
        if block.refines:
            assert set(block.refines) <= set(blocks[block.parent_id].components)
    assert (spec.model_dump(mode="json"), observed.model_dump(mode="json")) == original_inputs

    if pack == "building_hvac":
        assert reference.top_blocks[0].block_id == "building_hvac"
        assert {"zone_loads", "chilled_water_loop", "chiller_condenser", "air_handler",
                "plant_electrical", "district_energy_interface"} <= {block.block_id for block in reference.top_blocks}
        text = (directory / "tree.yaml").read_text(encoding="utf-8")
        assert "MappedSignalModule" in text and "DummyResidualModule" not in text
        # Preserve the old unmet-load magnitude in the unified tree's actual fault.
        row = next(row for row in variants["variants"] if row["id"] == "unmet_cooling_load")
        assert row["generated_values"]["zone_cooling_coil_load.value"] == 22000.0
        assert sum(observed.variables[name].value for name in (
            "zone_envelope_gain.value", "zone_internal_gain.value", "zone_ventilation_gain.value")) == 25000.0
        assert not row["audit_pass"] and "zone_loads" in row["failed_blocks"]
        fault = observed.model_copy(deep=True)
        fault.variables["zone_cooling_coil_load.value"].value = 22000.0
        report = runner.evaluate_observed(fault, skip_unobserved=True)
        assert not report.audit_pass
        assert any(item.diagnostic_key == "aggregate_thermal_balance_mismatch" for item in report.top_residuals)
        rule = next(rule for rule in spec.hierarchy.refinement_rules if rule.block_id == "building_hvac")
        assert set(rule.next_template_ids) == {"zone_loads", "chilled_water_loop", "chiller_condenser",
                                               "air_handler", "plant_electrical", "district_energy_interface"}


@pytest.mark.parametrize("pack", TREE_PACKS)
def test_starter_pack_rules_resolve(pack) -> None:
    directory = ROOT / pack
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    planner = RefinementPlanner(directory)
    for rule in spec.hierarchy.refinement_rules:
        for target in rule.next_template_ids:
            assert planner._template_status(target, spec.hierarchy) == "block", (pack, rule.id, target)


def test_every_starter_pack_is_one_tree() -> None:
    for directory in ROOT.iterdir():
        if not directory.is_dir() or directory.name in {"heated_tank", "observed_debugging", "__pycache__"} or directory.name.startswith("."):
            continue
        assert (directory / "tree.yaml").is_file(), directory
        assert (directory / "nominal_observed.yaml").is_file(), directory
        assert not list(directory.rglob("level_*.yaml")), directory
        assert not list(directory.rglob("conflict_*.yaml")), directory
