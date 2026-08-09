from __future__ import annotations

import copy
import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from physicsguard.core.residual import ResidualBuilder
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"
FORMULA_ROOT = ROOT / ".physicsguard" / "module_formulas"

SOURCE_FIRST_MODULES = (
    "AggregateElectricalBusBalanceModule",
    "AggregateMassBalanceModule",
    "AggregatePowerBalanceModule",
    "AggregateThermalBalanceModule",
    "ControlErrorModule",
    "ConvectiveHeatTransferModule",
    "CoolantHeatBalanceModule",
    "EfficiencyMap2DModule",
    "ElectricalPowerModule",
    "ElectrochemicalFaradayRateModule",
    "ElectrochemicalStackPowerModule",
    "ElectrolyzerGasProductionModule",
    "ElectrolyzerStackBalanceModule",
    "FuelCellCathodeAirSupplyModule",
    "FuelCellStackBalanceModule",
    "HVBusPowerBalanceModule",
    "IncompressibleOrificeModule",
    "IncompressiblePressureDropModule",
    "LookupTable1DModule",
    "LookupTable2DModule",
    "MapAxisBoundsCheckModule",
    "MapMonotonicityCheckModule",
    "MappedSignalModule",
    "OhmicRelationModule",
    "PIDAlgebraicModule",
    "PIDControllerStepModule",
    "PipeSegmentSimpleModule",
    "PumpHydraulicPowerModule",
    "PumpSimpleModule",
    "RadiativeHeatTransferModule",
    "RateLimiterModule",
    "SaturationModule",
    "SensorScaleOffsetModule",
    "ThermalCapacitanceRateModule",
    "ThermalConductorModule",
    "UnitConversionAuditModule",
    "UnitScaleModule",
)


@lru_cache(maxsize=1)
def ledger_records() -> dict[str, dict]:
    payload = yaml.load(LEDGER.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    return {item["module_type"]: item for item in payload["module_records"]}


@lru_cache(maxsize=None)
def formula(module_type: str) -> dict:
    return yaml.load(
        (FORMULA_ROOT / f"{module_type}.yaml").read_text(encoding="utf-8"),
        Loader=yaml.CSafeLoader,
    )


@lru_cache(maxsize=1)
def checker() -> ModuleType:
    path = ROOT / "scripts" / "check_module_equation_ledger.py"
    spec = importlib.util.spec_from_file_location(
        "source_first_expression_checker", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_case_builder(
    module_type: str, case_inputs: dict
) -> tuple[ResidualBuilder, str, dict]:
    record = ledger_records()[module_type]
    binding = record["bindings"]["instantiation"]
    component_id = binding["component_id"]
    example_payload = yaml.load(
        (ROOT / binding["path"]).read_text(encoding="utf-8"),
        Loader=yaml.CSafeLoader,
    )
    spec = SystemSpec.model_validate(
        example_payload.get("system", example_payload)
    ).model_copy(deep=True)
    component = next(
        item
        for item in spec.components
        if item.id == component_id and item.type == module_type
    )
    config_names = {item["name"] for item in formula(module_type)["configuration"]}
    component.parameters.update(
        {
            name: value
            for name, value in case_inputs.items()
            if name in config_names
        }
    )
    return ResidualBuilder(spec), component_id, record


def apply_case_ports(
    builder: ResidualBuilder,
    component_id: str,
    module_type: str,
    case_inputs: dict,
):
    registry = builder.build_registry()
    vector = registry.initial_vector()
    payload = formula(module_type)
    for item in [*payload["scenario_inputs"], *payload["scenario_outputs"]]:
        reference = (
            item["source_reference"]
            if item.get("source_kind") == "external"
            else f"{component_id}.{item['name']}"
        )
        vector[registry.get_index(reference)] = float(case_inputs[item["name"]])
    return registry, vector


def test_source_first_code_projections_keep_machine_contracts_closed() -> None:
    current_checker = checker()
    blocked: dict[str, list[str]] = {}

    for module_type in SOURCE_FIRST_MODULES:
        record = ledger_records()[module_type]
        formula_payload = formula(module_type)
        findings = current_checker._empty_findings()
        runtime = current_checker._runtime_contract(ROOT, record, module_type)
        source_contract = current_checker._source_residual_contract(
            record, module_type
        )
        current_checker._review_function_block(
            record, module_type, runtime, source_contract, findings
        )
        current_checker._review_equation_dependencies(
            record, module_type, runtime, source_contract, findings
        )
        current_checker._review_units(
            ROOT, record, module_type, runtime, findings
        )

        resource = record["bindings"]["resources"][0]
        assert resource["implementation_binding"][
            "source_semantic_ir_fingerprint"
        ] == record["source_semantic_ir"]["fingerprint"]
        for residual in record["residual_definitions"]:
            formula_residual = next(
                item
                for item in formula_payload["residuals"]
                if item["name"] == residual["name"]
            )
            assert residual.get("runtime_name") == formula_residual.get(
                "runtime_name"
            )
            expected_intermediate_binding = (
                None
                if "source_intermediates" in formula_residual
                else "implementation_source_projection"
            )
            assert all(
                item.get("binding_kind") == expected_intermediate_binding
                for item in residual.get("intermediates", [])
            )
            assert all(
                item.get("binding_kind")
                == "implementation_source_projection"
                for item in residual.get("branches", [])
            )

        machine_findings = [
            f"{dimension}:{item['code']}"
            for dimension in ("function_block", "equation_dependency", "unit")
            for item in findings[dimension]
        ]
        if machine_findings:
            blocked[module_type] = machine_findings

    assert blocked == {}


def test_source_first_code_projection_rejects_names_outside_current_source_ir() -> None:
    module_type = "AggregateElectricalBusBalanceModule"
    record = copy.deepcopy(ledger_records()[module_type])
    record["residual_definitions"][0]["intermediates"][0][
        "expression"
    ] += " + impossible_projection_typo"
    current_checker = checker()
    findings = current_checker._empty_findings()
    runtime = current_checker._runtime_contract(ROOT, record, module_type)
    source_contract = current_checker._source_residual_contract(
        record, module_type
    )

    current_checker._review_equation_dependencies(
        record, module_type, runtime, source_contract, findings
    )

    assert any(
        item["code"] == "intermediate_expression_dependency_missing"
        and "impossible_projection_typo" in item["message"]
        for item in findings["equation_dependency"]
    )


def test_source_first_runtime_residual_names_must_be_unique() -> None:
    module_type = "ElectrolyzerGasProductionModule"
    record = copy.deepcopy(ledger_records()[module_type])
    record["residual_definitions"][0]["runtime_name"] = "duplicate_runtime_name"
    record["residual_definitions"][1]["runtime_name"] = "duplicate_runtime_name"
    current_checker = checker()
    findings = current_checker._empty_findings()
    runtime = current_checker._runtime_contract(ROOT, record, module_type)
    source_contract = current_checker._source_residual_contract(
        record, module_type
    )

    current_checker._review_equation_dependencies(
        record, module_type, runtime, source_contract, findings
    )

    assert any(
        item["code"] == "residual_runtime_name_duplicate"
        for item in findings["equation_dependency"]
    )


@pytest.mark.parametrize(
    "module_type",
    [
        "AggregateElectricalBusBalanceModule",
        "AggregateMassBalanceModule",
        "AggregatePowerBalanceModule",
        "AggregateThermalBalanceModule",
        "ControlErrorModule",
        "ConvectiveHeatTransferModule",
        "CoolantHeatBalanceModule",
        "EfficiencyMap2DModule",
        "ElectricalPowerModule",
        "ElectrochemicalFaradayRateModule",
        "ElectrochemicalStackPowerModule",
        "ElectrolyzerGasProductionModule",
        "ElectrolyzerStackBalanceModule",
        "FuelCellCathodeAirSupplyModule",
        "FuelCellStackBalanceModule",
        "HVBusPowerBalanceModule",
        "IncompressibleOrificeModule",
        "IncompressiblePressureDropModule",
        "LookupTable1DModule",
        "LookupTable2DModule",
        "MapAxisBoundsCheckModule",
        "MapMonotonicityCheckModule",
        "MappedSignalModule",
        "OhmicRelationModule",
        "PIDAlgebraicModule",
        "PIDControllerStepModule",
        "PipeSegmentSimpleModule",
        "PumpHydraulicPowerModule",
        "PumpSimpleModule",
        "RadiativeHeatTransferModule",
        "RateLimiterModule",
        "SaturationModule",
        "SensorScaleOffsetModule",
        "ThermalCapacitanceRateModule",
        "ThermalConductorModule",
        "UnitConversionAuditModule",
        "UnitScaleModule",
    ],
)
def test_source_first_reconstruction_matches_current_runtime(
    module_type: str,
) -> None:
    payload = formula(module_type)
    assert payload["authoring_status"] == (
        "source_first_reconstruction_pending_independent_review"
    )
    assert payload["separate_review_status"] == "pending"
    assert payload["physical_claim_licensed"] is False

    if not payload["residuals"]:
        builder, component_id, record = exact_case_builder(module_type, {})
        registry = builder.build_registry()
        declared = [
            registry.get_record(name)
            for name in registry.names()
            if registry.get_record(name).source_component == component_id
        ]
        expected_names = {
            str(item) for item in payload["behavior_contract"]["declared_variables"]
        }
        assert {item.local_name for item in declared} == expected_names
        assert [
            item
            for item in builder.diagnostic_residual_records(registry.initial_vector())
            if item.source == component_id
        ] == []
        assert record["behavior_contract"]["kind"] == "declaration_only"
        return

    record = ledger_records()[module_type]
    definitions = {
        item["name"]: item for item in record["residual_definitions"]
    }
    for case in payload["oracle_cases"]:
        builder, component_id, _ = exact_case_builder(module_type, case["inputs"])
        _, vector = apply_case_ports(
            builder, component_id, module_type, case["inputs"]
        )
        actual = {
            item.name.removeprefix(f"{component_id}."): item
            for item in builder.diagnostic_residual_records(vector)
            if item.source == component_id
        }
        expected_runtime_names = {
            item.get("runtime_name", item["name"]): item
            for item in payload["residuals"]
        }
        assert set(actual) == set(expected_runtime_names)
        for runtime_name, residual_formula in expected_runtime_names.items():
            definition = definitions[residual_formula["name"]]
            current = actual[runtime_name]
            expected_value = case["expected"][residual_formula["name"]]
            expected_scale = checker()._restricted_expression(
                residual_formula["scale_expression"], case["inputs"]
            )
            assert current.value == pytest.approx(
                float(expected_value), abs=float(case["tolerance"]), rel=0.0
            )
            assert current.scale == pytest.approx(float(expected_scale))
            if isinstance(definition["role"], dict):
                assert current.role == case["inputs"]["role"]
            else:
                assert current.role == definition["role"]
            assert current.diagnostic_key == definition["diagnostic_key"]


@pytest.mark.parametrize(
    "module_type",
    [
        "AggregateElectricalBusBalanceModule",
        "AggregateMassBalanceModule",
        "AggregatePowerBalanceModule",
        "AggregateThermalBalanceModule",
        "ControlErrorModule",
        "ConvectiveHeatTransferModule",
        "CoolantHeatBalanceModule",
        "EfficiencyMap2DModule",
        "ElectricalPowerModule",
        "ElectrochemicalFaradayRateModule",
        "ElectrochemicalStackPowerModule",
        "ElectrolyzerGasProductionModule",
        "ElectrolyzerStackBalanceModule",
        "FuelCellCathodeAirSupplyModule",
        "FuelCellStackBalanceModule",
        "HVBusPowerBalanceModule",
        "IncompressibleOrificeModule",
        "IncompressiblePressureDropModule",
        "LookupTable1DModule",
        "LookupTable2DModule",
        "MapAxisBoundsCheckModule",
        "MapMonotonicityCheckModule",
        "MappedSignalModule",
        "OhmicRelationModule",
        "PIDAlgebraicModule",
        "PIDControllerStepModule",
        "PipeSegmentSimpleModule",
        "PumpHydraulicPowerModule",
        "PumpSimpleModule",
        "RadiativeHeatTransferModule",
        "RateLimiterModule",
        "SaturationModule",
        "SensorScaleOffsetModule",
        "ThermalCapacitanceRateModule",
        "ThermalConductorModule",
        "UnitConversionAuditModule",
        "UnitScaleModule",
    ],
)
def test_source_first_constructor_counterexample_still_fails(
    module_type: str,
) -> None:
    payload = formula(module_type)
    outside = next(
        case
        for case in payload["constraints"]["constructor"][0]["cases"]
        if case["kind"] == "outside"
    )
    binding = ledger_records()[module_type]["bindings"]["instantiation"]
    parameters = dict(binding["parameters"])
    config_names = {item["name"] for item in payload["configuration"]}
    parameters.update(
        {
            name: value
            for name, value in outside["inputs"].items()
            if name in config_names
        }
    )
    known_bad = SystemSpec.model_validate(
        {
            "system_name": f"known_bad_{module_type}",
            "components": [
                {
                    "id": "known_bad",
                    "type": module_type,
                    "parameters": parameters,
                }
            ],
        }
    )
    with pytest.raises(ValueError):
        ResidualBuilder(known_bad).build_registry()
