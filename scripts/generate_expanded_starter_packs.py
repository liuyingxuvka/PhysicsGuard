from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "hierarchical"
TESTS = ROOT / "tests"


def mapped_var(var_id: str, unit: str | None, value: float, scale: float | None = None) -> dict[str, Any]:
    if scale is None:
        if unit == "W":
            scale = max(abs(value), 1.0) / 10.0
        elif unit in {"kg/s", "mol/s"}:
            scale = max(abs(value), 1.0)
        elif unit == "Pa":
            scale = 1.0e5
        else:
            scale = 1.0
    if unit is None:
        lower, upper = 0.0, 10.0
    elif unit == "K":
        lower, upper = 200.0, 500.0
    elif unit == "Pa":
        lower, upper = 0.0, 1.0e9
    else:
        lower, upper = 0.0, 1.0e12
    return {
        "id": var_id,
        "type": "MappedSignalModule",
        "parameters": {
            "local_name": "value",
            "unit": unit,
            "lower_bound": lower,
            "upper_bound": upper,
            "initial_guess": value,
            "scale": scale,
            "external_signal": f"mapped_{var_id}",
            "mapping_confidence": "template",
        },
    }


def boundary(var_id: str, value: float, scale: float = 1.0e-6) -> dict[str, Any]:
    return {"variable": f"{var_id}.value", "value": value, "scale": scale}


def balance_component(block: dict[str, Any]) -> tuple[dict[str, Any], str]:
    kind = block["kind"]
    scale = block.get("residual_scale")
    if kind == "power":
        return (
            {
                "id": f"{block['id']}_power_balance",
                "type": "AggregatePowerBalanceModule",
                "parameters": {
                    "source_power_variables": [f"{name}.value" for name in block["sources"]],
                    "load_power_variables": [f"{name}.value" for name in block["outputs"]],
                    "residual_scale_W": scale or 100.0,
                },
            },
            "aggregate_power_balance_mismatch",
        )
    if kind == "thermal":
        return (
            {
                "id": f"{block['id']}_thermal_balance",
                "type": "AggregateThermalBalanceModule",
                "parameters": {
                    "heat_in_variables": [f"{name}.value" for name in block["sources"]],
                    "heat_out_variables": [f"{name}.value" for name in block["outputs"]],
                    "residual_scale_W": scale or 100.0,
                },
            },
            "aggregate_thermal_balance_mismatch",
        )
    if kind == "mass":
        return (
            {
                "id": f"{block['id']}_mass_balance",
                "type": "AggregateMassBalanceModule",
                "parameters": {
                    "mass_in_variables": [f"{name}.value" for name in block["sources"]],
                    "mass_out_variables": [f"{name}.value" for name in block["outputs"]],
                    "residual_scale_kg_s": scale or 0.01,
                },
            },
            "aggregate_mass_balance_mismatch",
        )
    raise ValueError(f"unknown block kind: {kind}")


def ratio_component(block: dict[str, Any]) -> dict[str, Any] | None:
    ratio = block.get("ratio")
    if not ratio:
        return None
    return {
        "id": f"{block['id']}_ratio_check",
        "type": "RatioModule",
        "parameters": {
            "numerator_variable": f"{ratio['numerator']}.value",
            "denominator_variable": f"{ratio['denominator']}.value",
            "output_variable": f"{ratio['output']}.value",
            "residual_scale": ratio.get("residual_scale", 0.01),
        },
    }


def range_component(block: dict[str, Any]) -> dict[str, Any] | None:
    check = block.get("range")
    if not check:
        return None
    return {
        "id": f"{check['variable']}_range",
        "type": "RangeCheckModule",
        "parameters": {
            "variable": f"{check['variable']}.value",
            "lower_bound": check["lower"],
            "upper_bound": check["upper"],
            "residual_scale": check.get("residual_scale", 1.0),
            "role": "post_check",
        },
    }


def block_components(block: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    components: list[dict[str, Any]] = []
    for var in block["variables"]:
        components.append(mapped_var(var["id"], var.get("unit"), var["value"], var.get("scale")))
    bal, diagnostic = balance_component(block)
    components.append(bal)
    ratio = ratio_component(block)
    if ratio:
        components.append(ratio)
    rng = range_component(block)
    if rng:
        components.append(rng)
    return components, diagnostic


def build_template(pack: dict[str, Any], *, conflict: bool = False, level: int = 0) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    bounds: list[dict[str, Any]] = []
    root_component_ids: list[str] = []
    child_blocks: list[dict[str, Any]] = []
    diagnostics: list[str] = []

    conflict_var = pack["conflict_variable"]
    for block in pack["blocks"]:
        block_comps, diagnostic = block_components(block)
        diagnostics.append(diagnostic)
        components.extend(block_comps)
        comp_ids = [component["id"] for component in block_comps]
        root_component_ids.extend(comp_ids)
        for var in block["variables"]:
            value = 0.0 if conflict and var["id"] == conflict_var else var["value"]
            scale = 1.0e-9 if (conflict and var["id"] == conflict_var) or var.get("unit") is None else 1.0e-6
            bounds.append(boundary(var["id"], value, scale))
        if level == 1:
            child_blocks.append(
                {
                    "id": block["id"],
                    "name": block["name"],
                    "level": 1,
                    "parent_id": pack["slug"],
                    "components": comp_ids,
                    "tags": block.get("tags", []),
                    "required_variables": [f"{name}.value" for name in block["sources"][:1]],
                }
            )

    if level == 0:
        blocks = [
            {
                "id": pack["slug"],
                "name": pack["title"],
                "level": 0,
                "components": root_component_ids,
                "tags": [pack["slug"], "level_0", *pack["tags"]],
                "required_variables": [f"{pack['blocks'][0]['sources'][0]}.value"],
                "refinement_template_ids": [f"{pack['slug']}/{pack['level1_file'][:-5]}"],
            }
        ]
        refinement_rules = [
            {
                "id": f"refine_{pack['slug']}_level_0",
                "block_id": pack["slug"],
                "trigger_diagnostic_keys": sorted(set(diagnostics + ["ratio_relation_mismatch", "range_check_violation"])),
                "score_threshold": 1.0,
                "next_template_ids": [f"{pack['slug']}/{pack['level1_file'][:-5]}"],
                "next_required_variables": pack["next_required_variables"],
                "next_required_parameters": pack["next_required_parameters"],
                "rationale": pack["rationale"],
                "priority": 10,
            }
        ]
    else:
        blocks = [{"id": pack["slug"], "name": pack["title"], "level": 0, "tags": [pack["slug"]]}, *child_blocks]
        refinement_rules = [
            {
                "id": f"refine_{block['id']}",
                "block_id": block["id"],
                "trigger_diagnostic_keys": [diagnostic, "ratio_relation_mismatch", "range_check_violation"],
                "score_threshold": 1.0,
                "next_template_ids": [f"{pack['slug']}/level_2_{block['id']}_placeholder"],
                "next_required_variables": [f"{name}.value" for name in block["sources"] + block["outputs"]],
                "next_required_parameters": block.get("next_required_parameters", pack["next_required_parameters"]),
                "rationale": block["rationale"],
                "priority": 10,
            }
            for block, diagnostic in zip(pack["blocks"], diagnostics, strict=True)
        ]

    audit_name = pack["slug"]
    if conflict:
        audit_name = f"{pack['slug']}_conflict_{pack['conflict_name']}"
    elif level == 1:
        audit_name = f"{pack['slug']}_level_1"
    else:
        audit_name = f"{pack['slug']}_level_0"

    assumptions = [
        pack["assumption"],
        "This template is a steady snapshot low-fidelity audit over mapped SI signals.",
        "All assumptions, sign conventions, and metering boundaries must be explicit before interpreting residuals.",
        "No high-fidelity simulator, calibrated performance map, or commercial-tool-equivalent behavior is implemented.",
    ]
    if conflict:
        assumptions.insert(0, pack["conflict_assumption"])

    return {
        "audit_name": audit_name,
        "description": pack["description"] if not conflict else pack["conflict_description"],
        "system": {
            "system_name": audit_name,
            "components": components,
            "boundaries": bounds,
            "solver": {"tolerance": 1.0e-8, "audit_threshold": 1.0},
        },
        "hierarchy": {
            "blocks": blocks,
            "refinement_rules": refinement_rules,
            "scoring": {"method": "max"},
        },
        "metadata": {
            "template_level": level,
            "domain": pack["slug"],
            "assumptions": assumptions,
        },
    }


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def v(var_id: str, unit: str | None, value: float, scale: float | None = None) -> dict[str, Any]:
    return {"id": var_id, "unit": unit, "value": value, "scale": scale}


PACKS: list[dict[str, Any]] = [
    {
        "slug": "oil_gas_pipeline_storage",
        "title": "Oil and gas pipeline storage",
        "tags": ["oil_gas", "pipeline", "storage"],
        "level0_file": "level_0_oil_gas_balance.yaml",
        "conflict_file": "conflict_level_0_unmetered_pipeline_leak.yaml",
        "level1_file": "level_1_pipeline_compression_storage.yaml",
        "conflict_name": "unmetered_pipeline_leak",
        "conflict_variable": "pipeline_leak_mass_flow",
        "description": "Level 0 coarse oil/gas audit for pipeline compression, gas mass accounting, and storage transfer.",
        "conflict_description": "Level 0 oil/gas audit with intentionally missing pipeline leak flow.",
        "assumption": "Gas streams are mapped as kg/s accounting streams; no gas-network hydraulics, compressor maps, reservoir physics, or multiphase flow is inferred.",
        "conflict_assumption": "This conflict intentionally maps pipeline leak flow to zero to represent an omitted loss term.",
        "rationale": "Coarse oil/gas residual is high; refine compression, pipeline mass, and storage transfer before adding hydraulic or equipment detail.",
        "next_required_variables": ["pipeline.inlet_kg_s", "pipeline.delivered_kg_s", "pipeline.leak_kg_s", "compressor.power_W"],
        "next_required_parameters": ["pipeline_meter_boundary", "leak_boundary", "compressor_power_grouping"],
        "blocks": [
            {
                "id": "pipeline_compression",
                "name": "Pipeline compression",
                "kind": "power",
                "sources": ["compressor_electric_power"],
                "outputs": ["gas_transport_power", "compressor_loss_power"],
                "variables": [v("compressor_electric_power", "W", 300000.0), v("gas_transport_power", "W", 240000.0), v("compressor_loss_power", "W", 60000.0), v("compressor_transfer_efficiency", None, 0.8)],
                "ratio": {"numerator": "gas_transport_power", "denominator": "compressor_electric_power", "output": "compressor_transfer_efficiency"},
                "tags": ["compression", "pipeline_power"],
                "rationale": "Compression residual is high; inspect electric-power grouping and transfer-power basis before adding compressor maps.",
            },
            {
                "id": "pipeline_mass_accounting",
                "name": "Pipeline mass accounting",
                "kind": "mass",
                "sources": ["pipeline_inlet_mass_flow"],
                "outputs": ["pipeline_delivered_mass_flow", "pipeline_leak_mass_flow"],
                "variables": [v("pipeline_inlet_mass_flow", "kg/s", 100.0), v("pipeline_delivered_mass_flow", "kg/s", 98.0), v("pipeline_leak_mass_flow", "kg/s", 2.0)],
                "tags": ["pipeline", "mass_balance", "leak"],
                "rationale": "Pipeline mass residual is high; inspect delivered flow, leak accounting, and boundary grouping before adding hydraulics.",
            },
            {
                "id": "terminal_storage_transfer",
                "name": "Terminal storage transfer",
                "kind": "mass",
                "sources": ["storage_inlet_mass_flow"],
                "outputs": ["storage_outlet_mass_flow", "storage_inventory_rate"],
                "variables": [v("storage_inlet_mass_flow", "kg/s", 20.0), v("storage_outlet_mass_flow", "kg/s", 18.0), v("storage_inventory_rate", "kg/s", 2.0)],
                "tags": ["storage", "inventory"],
                "rationale": "Storage residual is high; inspect inventory sign convention and tank boundary before adding tank detail.",
            },
        ],
    },
    {
        "slug": "water_supply_network",
        "title": "Water supply network",
        "tags": ["water_supply", "pump", "distribution"],
        "level0_file": "level_0_water_supply_balance.yaml",
        "conflict_file": "conflict_level_0_unmetered_leakage.yaml",
        "level1_file": "level_1_source_pump_distribution_storage.yaml",
        "conflict_name": "unmetered_leakage",
        "conflict_variable": "distribution_leakage_mass_flow",
        "description": "Level 0 coarse water-supply audit for treatment outflow, distribution leakage, storage, and pump power.",
        "conflict_description": "Level 0 water-supply audit with intentionally missing distribution leakage.",
        "assumption": "Water flows are mapped as kg/s; no EPANET-style hydraulics, pressure-zone simulation, or pump curves are inferred.",
        "conflict_assumption": "This conflict intentionally maps distribution leakage to zero.",
        "rationale": "Coarse water-supply residual is high; refine source, pump, distribution, and storage checks before adding network hydraulics.",
        "next_required_variables": ["plant.outflow_kg_s", "customer.demand_kg_s", "network.leakage_kg_s", "pump.power_W"],
        "next_required_parameters": ["district_meter_boundary", "leakage_boundary", "pump_meter_grouping"],
        "blocks": [
            {
                "id": "distribution_water_accounting",
                "name": "Distribution water accounting",
                "kind": "mass",
                "sources": ["treatment_outflow_mass_flow"],
                "outputs": ["customer_demand_mass_flow", "distribution_leakage_mass_flow", "reservoir_storage_rate"],
                "variables": [v("treatment_outflow_mass_flow", "kg/s", 100.0), v("customer_demand_mass_flow", "kg/s", 90.0), v("distribution_leakage_mass_flow", "kg/s", 5.0), v("reservoir_storage_rate", "kg/s", 5.0)],
                "tags": ["distribution", "leakage", "storage"],
                "rationale": "Distribution residual is high; inspect leakage and storage sign convention before adding network hydraulics.",
            },
            {
                "id": "pump_station_power",
                "name": "Pump station power",
                "kind": "power",
                "sources": ["pump_electric_power"],
                "outputs": ["delivered_hydraulic_power", "pump_loss_power"],
                "variables": [v("pump_electric_power", "W", 100000.0), v("delivered_hydraulic_power", "W", 80000.0), v("pump_loss_power", "W", 20000.0), v("pump_station_efficiency", None, 0.8)],
                "ratio": {"numerator": "delivered_hydraulic_power", "denominator": "pump_electric_power", "output": "pump_station_efficiency"},
                "range": {"variable": "pump_station_efficiency", "lower": 0.0, "upper": 1.0, "residual_scale": 0.01},
                "tags": ["pump", "power"],
                "rationale": "Pump residual is high; inspect pump meter grouping before adding pump curves.",
            },
        ],
    },
    {
        "slug": "manufacturing_thermal_process",
        "title": "Manufacturing thermal process",
        "tags": ["manufacturing", "furnace", "production_line"],
        "level0_file": "level_0_manufacturing_thermal_balance.yaml",
        "conflict_file": "conflict_level_0_missing_exhaust_loss.yaml",
        "level1_file": "level_1_furnace_line_material_balance.yaml",
        "conflict_name": "missing_exhaust_loss",
        "conflict_variable": "exhaust_heat_loss",
        "description": "Level 0 coarse manufacturing audit for furnace heat, production-line power, and material yield.",
        "conflict_description": "Level 0 manufacturing audit with intentionally missing exhaust heat loss.",
        "assumption": "Thermal and material flows are snapshot accounting terms; no furnace CFD, kinetics, process recipe, or equipment curve is inferred.",
        "conflict_assumption": "This conflict intentionally maps exhaust heat loss to zero.",
        "rationale": "Coarse manufacturing residual is high; refine furnace, line power, and material balance before adding process-specific detail.",
        "next_required_variables": ["furnace.heat_input_W", "furnace.exhaust_loss_W", "line.power_W", "material.feed_kg_s"],
        "next_required_parameters": ["heat_duty_boundary", "line_meter_grouping", "material_scrap_basis"],
        "blocks": [
            {
                "id": "furnace_heat_accounting",
                "name": "Furnace heat accounting",
                "kind": "thermal",
                "sources": ["furnace_heat_input"],
                "outputs": ["product_heat_gain", "exhaust_heat_loss", "wall_heat_loss"],
                "variables": [v("furnace_heat_input", "W", 1000000.0), v("product_heat_gain", "W", 700000.0), v("exhaust_heat_loss", "W", 200000.0), v("wall_heat_loss", "W", 100000.0)],
                "tags": ["furnace", "heat_balance"],
                "rationale": "Furnace residual is high; inspect exhaust and wall-loss boundaries before adding detailed heat transfer.",
            },
            {
                "id": "production_line_power",
                "name": "Production line power",
                "kind": "power",
                "sources": ["line_electric_power"],
                "outputs": ["machine_drive_power", "line_auxiliary_power"],
                "variables": [v("line_electric_power", "W", 200000.0), v("machine_drive_power", "W", 150000.0), v("line_auxiliary_power", "W", 50000.0), v("line_drive_fraction", None, 0.75)],
                "ratio": {"numerator": "machine_drive_power", "denominator": "line_electric_power", "output": "line_drive_fraction"},
                "tags": ["line_power", "drives"],
                "rationale": "Line-power residual is high; inspect motor and auxiliary meter grouping before adding machine detail.",
            },
            {
                "id": "material_yield_accounting",
                "name": "Material yield accounting",
                "kind": "mass",
                "sources": ["raw_material_feed_mass_flow"],
                "outputs": ["finished_product_mass_flow", "scrap_mass_flow"],
                "variables": [v("raw_material_feed_mass_flow", "kg/s", 50.0), v("finished_product_mass_flow", "kg/s", 45.0), v("scrap_mass_flow", "kg/s", 5.0)],
                "tags": ["material", "yield"],
                "rationale": "Material residual is high; inspect scrap and rework boundaries before adding process recipe detail.",
            },
        ],
    },
    {
        "slug": "mining_metallurgy",
        "title": "Mining and metallurgy",
        "tags": ["mining", "metallurgy", "slurry"],
        "level0_file": "level_0_mining_metallurgy_balance.yaml",
        "conflict_file": "conflict_level_0_missing_tailings.yaml",
        "level1_file": "level_1_ore_mill_slurry_balance.yaml",
        "conflict_name": "missing_tailings",
        "conflict_variable": "tailings_mass_flow",
        "description": "Level 0 coarse mining/metallurgy audit for ore balance, mill power, and slurry water.",
        "conflict_description": "Level 0 mining/metallurgy audit with intentionally missing tailings flow.",
        "assumption": "Ore, concentrate, tailings, and slurry water are accounting streams; no comminution model, flotation kinetics, or metallurgical recovery model is inferred.",
        "conflict_assumption": "This conflict intentionally maps tailings mass flow to zero.",
        "rationale": "Coarse mining residual is high; refine ore, mill power, and water accounting before adding process-specific correlations.",
        "next_required_variables": ["ore.feed_kg_s", "concentrate.output_kg_s", "tailings.output_kg_s", "mill.power_W"],
        "next_required_parameters": ["ore_meter_boundary", "tailings_basis", "mill_power_grouping"],
        "blocks": [
            {
                "id": "ore_mass_accounting",
                "name": "Ore mass accounting",
                "kind": "mass",
                "sources": ["ore_feed_mass_flow"],
                "outputs": ["concentrate_mass_flow", "tailings_mass_flow"],
                "variables": [v("ore_feed_mass_flow", "kg/s", 100.0), v("concentrate_mass_flow", "kg/s", 30.0), v("tailings_mass_flow", "kg/s", 70.0)],
                "tags": ["ore", "tailings", "mass_balance"],
                "rationale": "Ore residual is high; inspect concentrate and tailings boundaries before adding recovery models.",
            },
            {
                "id": "mill_power_accounting",
                "name": "Mill power accounting",
                "kind": "power",
                "sources": ["mill_electric_power"],
                "outputs": ["breakage_power", "mill_loss_power"],
                "variables": [v("mill_electric_power", "W", 500000.0), v("breakage_power", "W", 350000.0), v("mill_loss_power", "W", 150000.0), v("mill_useful_power_fraction", None, 0.7)],
                "ratio": {"numerator": "breakage_power", "denominator": "mill_electric_power", "output": "mill_useful_power_fraction"},
                "tags": ["mill", "power"],
                "rationale": "Mill residual is high; inspect electric-power grouping before adding comminution detail.",
            },
            {
                "id": "slurry_water_accounting",
                "name": "Slurry water accounting",
                "kind": "mass",
                "sources": ["process_water_mass_flow"],
                "outputs": ["concentrate_water_mass_flow", "tailings_water_mass_flow"],
                "variables": [v("process_water_mass_flow", "kg/s", 80.0), v("concentrate_water_mass_flow", "kg/s", 20.0), v("tailings_water_mass_flow", "kg/s", 60.0)],
                "tags": ["slurry", "water_balance"],
                "rationale": "Slurry-water residual is high; inspect concentrate/tailings water basis before adding dewatering detail.",
            },
        ],
    },
    {
        "slug": "combustion_boiler_furnace",
        "title": "Combustion boiler and furnace",
        "tags": ["combustion", "boiler", "furnace"],
        "level0_file": "level_0_combustion_boiler_balance.yaml",
        "conflict_file": "conflict_level_0_missing_stack_loss.yaml",
        "level1_file": "level_1_fuel_air_heat_draft_balance.yaml",
        "conflict_name": "missing_stack_loss",
        "conflict_variable": "stack_heat_loss",
        "description": "Level 0 coarse combustion audit for fuel heat, useful heat, stack/casing loss, air/flue mass, and draft power.",
        "conflict_description": "Level 0 combustion audit with intentionally missing stack heat loss.",
        "assumption": "Fuel heat and air/flue terms are mapped accounting signals; no combustion kinetics, emissions chemistry, or burner model is inferred.",
        "conflict_assumption": "This conflict intentionally maps stack heat loss to zero.",
        "rationale": "Coarse combustion residual is high; refine heat, air/flue, and draft power before adding combustion detail.",
        "next_required_variables": ["fuel.heat_input_W", "steam.useful_heat_W", "stack.loss_W", "air.flow_kg_s"],
        "next_required_parameters": ["fuel_lhv_basis", "stack_loss_boundary", "air_flue_metering"],
        "blocks": [
            {
                "id": "boiler_heat_accounting",
                "name": "Boiler heat accounting",
                "kind": "thermal",
                "sources": ["fuel_thermal_power"],
                "outputs": ["useful_steam_heat_power", "stack_heat_loss", "casing_heat_loss"],
                "variables": [v("fuel_thermal_power", "W", 2000000.0), v("useful_steam_heat_power", "W", 1600000.0), v("stack_heat_loss", "W", 300000.0), v("casing_heat_loss", "W", 100000.0), v("boiler_useful_heat_fraction", None, 0.8)],
                "ratio": {"numerator": "useful_steam_heat_power", "denominator": "fuel_thermal_power", "output": "boiler_useful_heat_fraction"},
                "tags": ["boiler", "heat_balance"],
                "rationale": "Boiler heat residual is high; inspect stack/casing loss and fuel basis before adding combustion detail.",
            },
            {
                "id": "air_flue_mass_accounting",
                "name": "Air and flue mass accounting",
                "kind": "mass",
                "sources": ["air_fuel_mass_flow"],
                "outputs": ["flue_gas_mass_flow", "ash_purge_mass_flow"],
                "variables": [v("air_fuel_mass_flow", "kg/s", 10.5), v("flue_gas_mass_flow", "kg/s", 10.0), v("ash_purge_mass_flow", "kg/s", 0.5)],
                "tags": ["air", "flue_gas"],
                "rationale": "Air/flue residual is high; inspect combined air/fuel basis before adding chemistry.",
            },
            {
                "id": "draft_fan_power",
                "name": "Draft fan power",
                "kind": "power",
                "sources": ["draft_fan_electric_power"],
                "outputs": ["air_movement_power", "fan_loss_power"],
                "variables": [v("draft_fan_electric_power", "W", 50000.0), v("air_movement_power", "W", 40000.0), v("fan_loss_power", "W", 10000.0)],
                "tags": ["fan", "draft"],
                "rationale": "Draft fan residual is high; inspect power grouping before adding fan curves.",
            },
        ],
    },
    {
        "slug": "geothermal_underground_wells",
        "title": "Geothermal underground wells",
        "tags": ["geothermal", "wells", "thermal"],
        "level0_file": "level_0_geothermal_well_balance.yaml",
        "conflict_file": "conflict_level_0_missing_brine_loss.yaml",
        "level1_file": "level_1_production_reinjection_heat_balance.yaml",
        "conflict_name": "missing_brine_loss",
        "conflict_variable": "steam_brine_loss_mass_flow",
        "description": "Level 0 coarse geothermal audit for production/reinjection mass, thermal extraction, and pump power.",
        "conflict_description": "Level 0 geothermal audit with intentionally missing brine/steam loss.",
        "assumption": "Well flows and heat extraction are mapped accounting terms; no reservoir simulator, wellbore model, or geochemistry is inferred.",
        "conflict_assumption": "This conflict intentionally maps steam/brine loss to zero.",
        "rationale": "Coarse geothermal residual is high; refine production, reinjection, heat extraction, and pump checks before adding subsurface detail.",
        "next_required_variables": ["well.production_kg_s", "reinjection.flow_kg_s", "thermal.output_W", "pump.power_W"],
        "next_required_parameters": ["well_flow_boundary", "heat_extraction_basis", "reinjection_metering"],
        "blocks": [
            {
                "id": "well_mass_accounting",
                "name": "Well mass accounting",
                "kind": "mass",
                "sources": ["production_mass_flow"],
                "outputs": ["reinjection_mass_flow", "steam_brine_loss_mass_flow"],
                "variables": [v("production_mass_flow", "kg/s", 50.0), v("reinjection_mass_flow", "kg/s", 49.0), v("steam_brine_loss_mass_flow", "kg/s", 1.0)],
                "tags": ["well", "reinjection"],
                "rationale": "Well mass residual is high; inspect production/reinjection and loss boundaries before adding wellbore detail.",
            },
            {
                "id": "geothermal_heat_accounting",
                "name": "Geothermal heat accounting",
                "kind": "thermal",
                "sources": ["reservoir_heat_output"],
                "outputs": ["plant_heat_use", "brine_heat_loss"],
                "variables": [v("reservoir_heat_output", "W", 1500000.0), v("plant_heat_use", "W", 1200000.0), v("brine_heat_loss", "W", 300000.0), v("thermal_use_fraction", None, 0.8)],
                "ratio": {"numerator": "plant_heat_use", "denominator": "reservoir_heat_output", "output": "thermal_use_fraction"},
                "tags": ["thermal", "plant"],
                "rationale": "Thermal residual is high; inspect heat-use and brine-loss basis before adding reservoir models.",
            },
            {
                "id": "reinjection_pump_power",
                "name": "Reinjection pump power",
                "kind": "power",
                "sources": ["reinjection_pump_power"],
                "outputs": ["injection_hydraulic_power", "reinjection_pump_loss"],
                "variables": [v("reinjection_pump_power", "W", 100000.0), v("injection_hydraulic_power", "W", 80000.0), v("reinjection_pump_loss", "W", 20000.0)],
                "tags": ["pump", "reinjection"],
                "rationale": "Pump residual is high; inspect pump power and hydraulic-power basis before adding pump curves.",
            },
        ],
    },
    {
        "slug": "cold_chain_logistics",
        "title": "Cold chain logistics",
        "tags": ["cold_chain", "logistics", "refrigeration"],
        "level0_file": "level_0_cold_chain_logistics_balance.yaml",
        "conflict_file": "conflict_level_0_missing_door_gain.yaml",
        "level1_file": "level_1_warehouse_truck_fleet_balance.yaml",
        "conflict_name": "missing_door_gain",
        "conflict_variable": "door_infiltration_heat_gain",
        "description": "Level 0 coarse cold-chain logistics audit for warehouse heat, truck cooling, and fleet power.",
        "conflict_description": "Level 0 cold-chain logistics audit with intentionally missing door infiltration heat gain.",
        "assumption": "Cold-chain heat gains and refrigeration powers are mapped accounting terms; no detailed cargo thermal model, route model, or refrigeration map is inferred.",
        "conflict_assumption": "This conflict intentionally maps door infiltration heat gain to zero.",
        "rationale": "Coarse cold-chain residual is high; refine warehouse, truck, and fleet-power checks before adding logistics or equipment detail.",
        "next_required_variables": ["warehouse.cooling_W", "warehouse.heat_gain_W", "truck.cooling_W", "fleet.power_W"],
        "next_required_parameters": ["door_opening_boundary", "cargo_heat_basis", "fleet_meter_grouping"],
        "blocks": [
            {
                "id": "warehouse_thermal_accounting",
                "name": "Warehouse thermal accounting",
                "kind": "thermal",
                "sources": ["warehouse_refrigeration_capacity"],
                "outputs": ["product_heat_gain", "door_infiltration_heat_gain", "envelope_heat_gain"],
                "variables": [v("warehouse_refrigeration_capacity", "W", 200000.0), v("product_heat_gain", "W", 120000.0), v("door_infiltration_heat_gain", "W", 50000.0), v("envelope_heat_gain", "W", 30000.0)],
                "tags": ["warehouse", "thermal"],
                "rationale": "Warehouse thermal residual is high; inspect door, product, and envelope heat-gain boundaries before adding thermal detail.",
            },
            {
                "id": "truck_cooling_accounting",
                "name": "Truck cooling accounting",
                "kind": "thermal",
                "sources": ["truck_cooling_capacity"],
                "outputs": ["cargo_heat_gain", "truck_ambient_heat_gain"],
                "variables": [v("truck_cooling_capacity", "W", 50000.0), v("cargo_heat_gain", "W", 30000.0), v("truck_ambient_heat_gain", "W", 20000.0)],
                "tags": ["truck", "cooling"],
                "rationale": "Truck cooling residual is high; inspect cargo and ambient heat-gain boundaries before adding route detail.",
            },
            {
                "id": "fleet_power_accounting",
                "name": "Fleet power accounting",
                "kind": "power",
                "sources": ["cold_chain_facility_power"],
                "outputs": ["refrigeration_electric_power", "auxiliary_logistics_power"],
                "variables": [v("cold_chain_facility_power", "W", 100000.0), v("refrigeration_electric_power", "W", 80000.0), v("auxiliary_logistics_power", "W", 20000.0)],
                "tags": ["fleet", "power"],
                "rationale": "Fleet power residual is high; inspect meter grouping before adding equipment maps.",
            },
        ],
    },
    {
        "slug": "robotics_mechatronics",
        "title": "Robotics and mechatronics",
        "tags": ["robotics", "mechatronics", "actuators"],
        "level0_file": "level_0_robotics_mechatronics_balance.yaml",
        "conflict_file": "conflict_level_0_missing_drive_loss.yaml",
        "level1_file": "level_1_power_joint_thermal_actuator_balance.yaml",
        "conflict_name": "missing_drive_loss",
        "conflict_variable": "drive_loss_power",
        "description": "Level 0 coarse robotics/mechatronics audit for DC-bus power, joint heat, and actuator air use.",
        "conflict_description": "Level 0 robotics/mechatronics audit with intentionally missing drive loss.",
        "assumption": "Robot power, heat, and actuator flow are mapped accounting terms; no robot dynamics, kinematics, contact model, or motor map is inferred.",
        "conflict_assumption": "This conflict intentionally maps drive loss power to zero.",
        "rationale": "Coarse robotics residual is high; refine bus power, joint thermal, and actuator checks before adding dynamics or motor maps.",
        "next_required_variables": ["dc_bus.power_W", "motor.mechanical_power_W", "drive.loss_W", "joint.temperature_K"],
        "next_required_parameters": ["dc_bus_meter_boundary", "drive_loss_basis", "joint_heat_boundary"],
        "blocks": [
            {
                "id": "robot_power_chain",
                "name": "Robot power chain",
                "kind": "power",
                "sources": ["dc_bus_power"],
                "outputs": ["motor_mechanical_power", "drive_loss_power", "controller_power"],
                "variables": [v("dc_bus_power", "W", 10000.0), v("motor_mechanical_power", "W", 7000.0), v("drive_loss_power", "W", 2000.0), v("controller_power", "W", 1000.0), v("motor_mechanical_fraction", None, 0.7)],
                "ratio": {"numerator": "motor_mechanical_power", "denominator": "dc_bus_power", "output": "motor_mechanical_fraction"},
                "tags": ["power_chain", "motor"],
                "rationale": "Power-chain residual is high; inspect DC-bus, motor, drive-loss, and controller boundaries before adding motor maps.",
            },
            {
                "id": "joint_thermal_accounting",
                "name": "Joint thermal accounting",
                "kind": "thermal",
                "sources": ["motor_heat_generation"],
                "outputs": ["joint_coolant_heat", "joint_casing_heat_loss"],
                "variables": [v("motor_heat_generation", "W", 2000.0), v("joint_coolant_heat", "W", 1500.0), v("joint_casing_heat_loss", "W", 500.0), v("joint_temperature", "K", 320.0)],
                "range": {"variable": "joint_temperature", "lower": 250.0, "upper": 370.0, "residual_scale": 1.0},
                "tags": ["joint", "thermal"],
                "rationale": "Joint thermal residual is high; inspect heat-generation and cooling boundaries before adding thermal detail.",
            },
            {
                "id": "pneumatic_actuator_accounting",
                "name": "Pneumatic actuator accounting",
                "kind": "mass",
                "sources": ["compressed_air_supply_mass_flow"],
                "outputs": ["actuator_air_use_mass_flow", "pneumatic_leak_mass_flow"],
                "variables": [v("compressed_air_supply_mass_flow", "kg/s", 1.0), v("actuator_air_use_mass_flow", "kg/s", 0.8), v("pneumatic_leak_mass_flow", "kg/s", 0.2)],
                "tags": ["pneumatic", "actuator"],
                "rationale": "Actuator air residual is high; inspect leak and actuator-use boundaries before adding pneumatic dynamics.",
            },
        ],
    },
    {
        "slug": "aerospace_satellite_thermal",
        "title": "Aerospace satellite thermal",
        "tags": ["aerospace", "satellite", "thermal"],
        "level0_file": "level_0_satellite_power_thermal_balance.yaml",
        "conflict_file": "conflict_level_0_missing_radiator_heat.yaml",
        "level1_file": "level_1_satellite_power_thermal_storage_balance.yaml",
        "conflict_name": "missing_radiator_heat",
        "conflict_variable": "radiator_heat_rejection",
        "description": "Level 0 coarse aerospace/satellite audit for solar power, internal heat, radiator rejection, and battery charging.",
        "conflict_description": "Level 0 satellite audit with intentionally missing radiator heat rejection.",
        "assumption": "Satellite power and heat terms are mapped accounting signals; no orbital mechanics, attitude, radiation environment, or spacecraft thermal solver is inferred.",
        "conflict_assumption": "This conflict intentionally maps radiator heat rejection to zero.",
        "rationale": "Coarse satellite residual is high; refine power, thermal, and battery storage checks before adding spacecraft detail.",
        "next_required_variables": ["solar.power_W", "payload.power_W", "radiator.heat_W", "battery.charge_W"],
        "next_required_parameters": ["solar_power_boundary", "thermal_radiator_boundary", "battery_meter_grouping"],
        "blocks": [
            {
                "id": "satellite_power_accounting",
                "name": "Satellite power accounting",
                "kind": "power",
                "sources": ["solar_array_power"],
                "outputs": ["payload_power", "avionics_power", "battery_charge_power", "power_conversion_loss"],
                "variables": [v("solar_array_power", "W", 5000.0), v("payload_power", "W", 2000.0), v("avionics_power", "W", 1000.0), v("battery_charge_power", "W", 1000.0), v("power_conversion_loss", "W", 1000.0)],
                "tags": ["solar", "power"],
                "rationale": "Satellite power residual is high; inspect solar, payload, avionics, battery, and loss boundaries before adding spacecraft power detail.",
            },
            {
                "id": "satellite_thermal_accounting",
                "name": "Satellite thermal accounting",
                "kind": "thermal",
                "sources": ["electronics_heat_generation", "absorbed_solar_heat"],
                "outputs": ["radiator_heat_rejection", "thermal_storage_rate"],
                "variables": [v("electronics_heat_generation", "W", 3000.0), v("absorbed_solar_heat", "W", 1000.0), v("radiator_heat_rejection", "W", 3500.0), v("thermal_storage_rate", "W", 500.0), v("bus_temperature", "K", 295.0)],
                "range": {"variable": "bus_temperature", "lower": 250.0, "upper": 330.0, "residual_scale": 1.0},
                "tags": ["thermal", "radiator"],
                "rationale": "Thermal residual is high; inspect radiator and storage sign convention before adding spacecraft thermal solvers.",
            },
        ],
    },
    {
        "slug": "medical_bioprocess_equipment",
        "title": "Medical and bioprocess equipment",
        "tags": ["medical", "bioprocess", "equipment"],
        "level0_file": "level_0_medical_bioprocess_equipment_balance.yaml",
        "conflict_file": "conflict_level_0_missing_ventilator_leak.yaml",
        "level1_file": "level_1_ventilator_dialysis_sterilizer_incubator.yaml",
        "conflict_name": "missing_ventilator_leak",
        "conflict_variable": "ventilator_leak_mass_flow",
        "description": "Level 0 coarse medical/bioprocess equipment audit for ventilator flow, dialysis flow, sterilizer heat, and incubator temperature.",
        "conflict_description": "Level 0 medical/bioprocess audit with intentionally missing ventilator leak flow.",
        "assumption": "Medical equipment templates are engineering signal audits only; they are not clinical guidance, safety certification, or device-performance models.",
        "conflict_assumption": "This conflict intentionally maps ventilator leak flow to zero.",
        "rationale": "Coarse medical-equipment residual is high; refine ventilator, dialysis, heat, and incubator checks before adding device-specific detail.",
        "next_required_variables": ["ventilator.supply_kg_s", "ventilator.patient_kg_s", "dialysis.flow_kg_s", "incubator.temperature_K"],
        "next_required_parameters": ["ventilator_flow_boundary", "dialysis_meter_boundary", "sterilizer_heat_boundary"],
        "blocks": [
            {
                "id": "ventilator_flow_accounting",
                "name": "Ventilator flow accounting",
                "kind": "mass",
                "sources": ["ventilator_supply_mass_flow"],
                "outputs": ["patient_delivery_mass_flow", "ventilator_leak_mass_flow"],
                "variables": [v("ventilator_supply_mass_flow", "kg/s", 0.1), v("patient_delivery_mass_flow", "kg/s", 0.09), v("ventilator_leak_mass_flow", "kg/s", 0.01)],
                "tags": ["ventilator", "flow"],
                "rationale": "Ventilator residual is high; inspect supply, delivered flow, and leak boundary before adding device detail.",
            },
            {
                "id": "dialysis_fluid_accounting",
                "name": "Dialysis fluid accounting",
                "kind": "mass",
                "sources": ["dialysate_inlet_mass_flow"],
                "outputs": ["dialysate_outlet_mass_flow"],
                "variables": [v("dialysate_inlet_mass_flow", "kg/s", 0.2), v("dialysate_outlet_mass_flow", "kg/s", 0.2)],
                "tags": ["dialysis", "flow"],
                "rationale": "Dialysis residual is high; inspect inlet/outlet metering before adding device-specific transport detail.",
            },
            {
                "id": "sterilizer_incubator_thermal",
                "name": "Sterilizer and incubator thermal",
                "kind": "thermal",
                "sources": ["heater_power"],
                "outputs": ["useful_chamber_heat", "wall_heat_loss"],
                "variables": [v("heater_power", "W", 500.0), v("useful_chamber_heat", "W", 400.0), v("wall_heat_loss", "W", 100.0), v("incubator_temperature", "K", 310.0)],
                "range": {"variable": "incubator_temperature", "lower": 290.0, "upper": 330.0, "residual_scale": 1.0},
                "tags": ["thermal", "incubator", "sterilizer"],
                "rationale": "Thermal residual is high; inspect heater/chamber/loss and temperature basis before adding device detail.",
            },
        ],
    },
]


def write_standard_pack(pack: dict[str, Any]) -> None:
    target = EXAMPLES / pack["slug"]
    write_yaml(target / pack["level0_file"], build_template(pack, level=0))
    write_yaml(target / pack["conflict_file"], build_template(pack, conflict=True, level=0))
    write_yaml(target / pack["level1_file"], build_template(pack, level=1))


def write_foundation_pack() -> None:
    target = EXAMPLES / "cross_domain_audit_primitives"
    common_blocks = [
        {
            "id": "cross_domain_audit_primitives",
            "name": "Cross-domain audit primitives",
            "level": 0,
            "components": [
                "temperature_c_to_k",
                "pressure_sensor_scale",
                "unmetered_loss_power",
                "sample_delay",
                "sample_delay_range",
            ],
            "tags": ["cross_domain", "unit_conversion", "sensor", "loss", "time_alignment"],
            "required_variables": ["temperature_c_to_k.x", "temperature_c_to_k.y", "pressure_sensor_scale.true_value"],
            "refinement_template_ids": ["cross_domain_audit_primitives/level_1_units_sensors_boundary_time"],
        }
    ]
    components = [
        {
            "id": "temperature_c_to_k",
            "type": "UnitScaleModule",
            "parameters": {
                "factor": 1.0,
                "offset": 273.15,
                "source_unit": "degC",
                "target_unit": "K",
                "x_initial_guess": 25.0,
                "y_initial_guess": 298.15,
                "x_scale": 10.0,
                "y_scale": 10.0,
                "residual_scale": 0.01,
            },
        },
        {
            "id": "pressure_sensor_scale",
            "type": "SensorScaleOffsetModule",
            "parameters": {
                "scale_factor": 1.0,
                "offset": 0.0,
                "true_initial_guess": 200000.0,
                "measured_initial_guess": 200000.0,
                "true_scale": 100000.0,
                "measured_scale": 100000.0,
                "residual_scale": 100.0,
            },
        },
        mapped_var("metered_source_power", "W", 100000.0),
        mapped_var("metered_load_power", "W", 80000.0),
        mapped_var("unmetered_loss_power", "W", 20000.0),
        mapped_var("sample_delay", "s", 0.2, 1.0),
        {
            "id": "boundary_loss_power_balance",
            "type": "AggregatePowerBalanceModule",
            "parameters": {
                "source_power_variables": ["metered_source_power.value"],
                "load_power_variables": ["metered_load_power.value", "unmetered_loss_power.value"],
                "residual_scale_W": 100.0,
            },
        },
        {
            "id": "sample_delay_range",
            "type": "RangeCheckModule",
            "parameters": {
                "variable": "sample_delay.value",
                "lower_bound": 0.0,
                "upper_bound": 1.0,
                "residual_scale": 0.1,
                "role": "post_check",
            },
        },
    ]
    bounds = [
        {"variable": "temperature_c_to_k.x", "value": 25.0, "scale": 1.0e-6},
        {"variable": "temperature_c_to_k.y", "value": 298.15, "scale": 1.0e-6},
        {"variable": "pressure_sensor_scale.true_value", "value": 200000.0, "scale": 1.0e-6},
        {"variable": "pressure_sensor_scale.measured_value", "value": 200000.0, "scale": 1.0e-6},
        boundary("metered_source_power", 100000.0),
        boundary("metered_load_power", 80000.0),
        boundary("unmetered_loss_power", 20000.0),
        boundary("sample_delay", 0.2),
    ]
    base = {
        "audit_name": "cross_domain_audit_primitives_level_0",
        "description": "Level 0 cross-domain primitive audit for explicit unit conversion, sensor scale/offset, unmetered loss, and sampling-delay checks.",
        "system": {
            "system_name": "cross_domain_audit_primitives_level_0",
            "components": components,
            "boundaries": bounds,
            "solver": {"tolerance": 1.0e-8, "audit_threshold": 1.0},
        },
        "hierarchy": {
            "blocks": common_blocks,
            "refinement_rules": [
                {
                    "id": "refine_cross_domain_audit_primitives_level_0",
                    "block_id": "cross_domain_audit_primitives",
                    "trigger_diagnostic_keys": [
                        "unit_scale_mismatch",
                        "sensor_scale_offset_mismatch",
                        "aggregate_power_balance_mismatch",
                        "range_check_violation",
                    ],
                    "score_threshold": 1.0,
                    "next_template_ids": ["cross_domain_audit_primitives/level_1_units_sensors_boundary_time"],
                    "next_required_variables": [
                        "unit.source_value",
                        "unit.target_value",
                        "sensor.true_value",
                        "sensor.measured_value",
                        "boundary.source_power_W",
                        "timing.sample_delay_s",
                    ],
                    "next_required_parameters": [
                        "explicit_unit_factor_offset",
                        "sensor_calibration_basis",
                        "meter_grouping",
                        "sample_alignment_basis",
                    ],
                    "rationale": "Primitive audit residual is high; refine unit, sensor, boundary, and timing checks before adding domain-specific physics.",
                    "priority": 10,
                }
            ],
            "scoring": {"method": "max"},
        },
        "metadata": {
            "template_level": 0,
            "domain": "cross_domain_audit_primitives",
            "assumptions": [
                "This template demonstrates reusable low-fidelity audit primitives, not a domain model.",
                "Unit conversion uses explicit caller-provided factor and offset; no hidden unit table is applied.",
                "Sensor, boundary-loss, and timing checks are algebraic sanity checks for mapped signals.",
            ],
        },
    }
    conflict = yaml.safe_load(yaml.safe_dump(base))
    conflict["audit_name"] = "cross_domain_audit_primitives_conflict_bad_temperature_offset"
    conflict["system"]["system_name"] = conflict["audit_name"]
    conflict["description"] = "Cross-domain primitive audit with intentionally wrong converted temperature."
    for item in conflict["system"]["boundaries"]:
        if item["variable"] == "temperature_c_to_k.y":
            item["value"] = 25.0
            item["scale"] = 1.0e-9
    conflict["metadata"]["assumptions"].insert(0, "This conflict intentionally maps a Celsius value as if it were already Kelvin.")
    level1 = yaml.safe_load(yaml.safe_dump(base))
    level1["audit_name"] = "cross_domain_audit_primitives_level_1_units_sensors_boundary_time"
    level1["system"]["system_name"] = level1["audit_name"]
    level1["description"] = "Level 1 cross-domain primitive audit split into unit, sensor, boundary-loss, and timing blocks."
    level1["hierarchy"]["blocks"] = [
        {"id": "cross_domain_audit_primitives", "name": "Cross-domain audit primitives", "level": 0, "tags": ["cross_domain"]},
        {"id": "explicit_unit_conversion", "name": "Explicit unit conversion", "level": 1, "parent_id": "cross_domain_audit_primitives", "components": ["temperature_c_to_k"], "tags": ["unit_conversion"]},
        {"id": "sensor_calibration", "name": "Sensor calibration", "level": 1, "parent_id": "cross_domain_audit_primitives", "components": ["pressure_sensor_scale"], "tags": ["sensor"]},
        {"id": "boundary_loss_accounting", "name": "Boundary loss accounting", "level": 1, "parent_id": "cross_domain_audit_primitives", "components": ["metered_source_power", "metered_load_power", "unmetered_loss_power", "boundary_loss_power_balance"], "tags": ["boundary_loss"]},
        {"id": "time_alignment", "name": "Time alignment", "level": 1, "parent_id": "cross_domain_audit_primitives", "components": ["sample_delay", "sample_delay_range"], "tags": ["time_alignment"]},
    ]
    level1["hierarchy"]["refinement_rules"] = []
    level1["metadata"]["template_level"] = 1
    write_yaml(target / "level_0_cross_domain_primitives.yaml", base)
    write_yaml(target / "conflict_level_0_bad_temperature_offset.yaml", conflict)
    write_yaml(target / "level_1_units_sensors_boundary_time.yaml", level1)


def write_tests() -> None:
    entries = [
        {
            "slug": "cross_domain_audit_primitives",
            "level0": "level_0_cross_domain_primitives.yaml",
            "conflict": "conflict_level_0_bad_temperature_offset.yaml",
            "level1": "level_1_units_sensors_boundary_time.yaml",
            "root": "cross_domain_audit_primitives",
            "diagnostic": "unit_scale_mismatch",
            "blocks": ["explicit_unit_conversion", "sensor_calibration", "boundary_loss_accounting", "time_alignment"],
        }
    ]
    for pack in PACKS:
        conflict_diag = None
        for block in pack["blocks"]:
            _, diagnostic = block_components(block)
            if any(var["id"] == pack["conflict_variable"] for var in block["variables"]):
                conflict_diag = diagnostic
                break
        if conflict_diag is None:
            raise ValueError(f"conflict variable not found in pack: {pack['slug']}")
        entries.append(
            {
                "slug": pack["slug"],
                "level0": pack["level0_file"],
                "conflict": pack["conflict_file"],
                "level1": pack["level1_file"],
                "root": pack["slug"],
                "diagnostic": conflict_diag,
                "blocks": [block["id"] for block in pack["blocks"]],
            }
        )

    content = '''from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples" / "hierarchical"

PACKS = %r


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
''' % (entries,)
    (TESTS / "test_expanded_domain_starter_packs.py").write_text(content, encoding="utf-8")


def main() -> None:
    write_foundation_pack()
    for pack in PACKS:
        write_standard_pack(pack)
    write_tests()


if __name__ == "__main__":
    main()
