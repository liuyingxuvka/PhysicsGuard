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


LEGACY_BLOCKS = {'data_center_electronics_cooling': ['coolant_loop', 'cooling_plant_efficiency', 'data_center_electronics_cooling', 'facility_power_chain', 'it_load_rack_heat', 'room_air_cooling'], 'distribution_power_der': ['der_interface', 'distribution_power_der', 'feeder_section_a', 'feeder_section_b', 'power_quality_voltage', 'substation_transformer'], 'process_industry': ['heat_exchange_utility', 'process_industry', 'reactor_conversion', 'rotating_equipment', 'separator_split'], 'renewable_microgrid': ['battery_storage', 'load_dispatch', 'pv_system', 'renewable_microgrid', 'wind_system'], 'stormwater_sewer_drainage': ['catchment_runoff', 'detention_storage', 'pollutant_load', 'pump_station', 'sewer_conveyance', 'stormwater_sewer_drainage'], 'wastewater_treatment': ['aeration_energy', 'biological_reactor', 'secondary_clarifier', 'sludge_recycle', 'wastewater_plant']}


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
    # A flat partition observes every supplied signal; a coarse level still derives its own.
    assert 0 < len(observed.variables) <= len(solutions[0])
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
    blocks = {block.id: block for block in spec.hierarchy.blocks}
    root = next(block for block in blocks.values() if block.parent_id is None)
    if root.components:
        # Only a root with real system-level relations has a coarse level to refine and link to.
        assert any(connection["scope"] == "between_blocks" for connection in description["connections"])
    # Keep the original per-domain ownership checks inside the single discovered case.
    assert set(LEGACY_BLOCKS.get(pack, ())) <= blocks.keys()
    assert all(component.type != "DummyResidualModule" for component in spec.system.components)
    if pack in LEGACY_BLOCKS:
        assert any(component.type in {"MappedSignalModule", "UnitScaleModule"} for component in spec.system.components)
    assert all(block.own_audit_pass for block in reference.top_blocks)
    assert any(block.refines for block in blocks.values()) is bool(root.components)
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
        # Focused audit fixtures use their own model and snapshot names, outside the starter catalog.
        if not directory.is_dir() or directory.name in {"heated_tank", "observed_debugging", "shower_mix", "__pycache__"} or directory.name.startswith("."):
            continue
        assert (directory / "tree.yaml").is_file(), directory
        assert (directory / "nominal_observed.yaml").is_file(), directory
        assert not list(directory.rglob("level_*.yaml")), directory
        assert not list(directory.rglob("conflict_*.yaml")), directory


@pytest.mark.parametrize("pack", TREE_PACKS)
def test_no_copied_coarse_components(pack) -> None:
    import json

    spec = load_hierarchical_audit_spec(ROOT / pack / "tree.yaml")
    components = {component.id: component for component in spec.system.components}
    copies = [name for name, component in components.items()
              if name.startswith("coarse_") and name[len("coarse_"):] in components
              and component.type == components[name[len("coarse_"):]].type
              and json.dumps(component.parameters, sort_keys=True).replace("coarse_", "")
              == json.dumps(components[name[len("coarse_"):]].parameters, sort_keys=True)]
    assert copies == []
    root = next(block for block in spec.hierarchy.blocks if block.parent_id is None)
    if not root.components:
        assert not any(block.refines for block in spec.hierarchy.blocks)
        assert not any(rule.block_id == root.id for rule in spec.hierarchy.refinement_rules)
        assert "flat partition: no coarse level" in (ROOT / pack / "tree.yaml").read_text(encoding="utf-8").splitlines()[1].lower()


def _residual_values(spec, directory, observed):
    report = HierarchicalAuditRunner(spec, directory).evaluate_observed(
        observed, 100000, len(spec.hierarchy.blocks), skip_unobserved=True, _unit_factor_hints=False)
    values, seen = {}, {}
    for item in report.top_residuals:
        key = (item.name, item.source)
        seen[key] = seen.get(key, 0) + 1
        values[key + (seen[key],)] = item.normalized_value
    return values


@pytest.mark.parametrize("pack", TREE_PACKS)
def test_benign_change_is_sized_to_the_residual_scale(pack) -> None:
    directory = ROOT / pack
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    observed = load_observed_values(directory / "nominal_observed.yaml")
    before = _residual_values(spec, directory, observed)
    sized = []
    for variant in (variant for variant in spec.fault_variants if variant.kind == "benign"):
        changed = observed.model_copy(deep=True)
        for change in variant.changes:
            assert change.offset is not None, (variant.id, "a benign measurement error is an offset")
            item = changed.variables[change.variable]
            changed.variables[change.variable] = item.model_copy(update={"value": item.value + change.offset})
        after = _residual_values(spec, directory, changed)
        shift = max(abs(value - before.get(key, 0.0)) for key, value in after.items())
        assert max(abs(value) for value in after.values()) < spec.system.solver.audit_threshold
        if shift >= 0.1:
            sized.append(variant.id)
    # At least one benign change moves a checked residual to 0.1-0.5 of its scale and stays neutral;
    # a conserved change (building_hvac's 50 W fan step) may move none.
    assert sized


@pytest.mark.parametrize("pack", TREE_PACKS)
def test_pack_has_two_separable_faults(pack) -> None:
    directory = ROOT / pack
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    faults = [variant for variant in spec.fault_variants if variant.kind == "fault"]
    assert len(faults) >= 2
    assert len({tuple(sorted(variant.expect_blocks)) for variant in faults}) >= 2
    result = evaluate_fault_variants(spec, load_observed_values(directory / "nominal_observed.yaml"), pairs=True, base_dir=directory)
    assert result["pairwise"]
    assert all(row["detected"] and row["expect_blocks_met"] for row in result["variants"] if row["kind"] == "fault")
    assert all(row["pair_status"] in {"ok", "masked"} for row in result["pairs"])
