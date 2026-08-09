from __future__ import annotations

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

MECHANICAL_DRAFT_MODULES = (
    "AggregateEfficiencyModule",
    "BooleanSwitchModule",
    "ConservationSumModule",
    "DiscreteIntegratorModule",
    "FirstOrderLagModule",
    "GainBiasModule",
    "HysteresisStateCheckModule",
    "MapBoundsCheckModule",
    "MassBalanceRateModule",
    "ProductModule",
    "RangeCheckModule",
    "RatioModule",
    "RotationalInertiaTorqueModule",
    "SumModule",
    "TankLevelVolumeModule",
    "TankVolumeRateModule",
    "ThresholdStateCheckModule",
    "TorqueSpeedPowerModule",
    "TranslationalInertiaForceModule",
    "ViscousDamperForceModule",
    "VolumetricMassFlowConversionModule",
    "WaterProductionFaradayModule",
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
        "mechanical_draft_expression_checker", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_case_builder(module_type: str, case_inputs: dict) -> tuple[ResidualBuilder, str, dict]:
    record = ledger_records()[module_type]
    binding = record["bindings"]["instantiation"]
    component_id = binding["component_id"]
    example_payload = yaml.load(
        (ROOT / binding["path"]).read_text(encoding="utf-8"),
        Loader=yaml.CSafeLoader,
    )
    # The binding inventory contains both direct SystemSpec examples and
    # hierarchy audit wrappers whose executable SystemSpec is nested under
    # ``system``.  Exercise the exact bound component in either source shape.
    spec = SystemSpec.model_validate(
        example_payload.get("system", example_payload)
    ).model_copy(deep=True)
    component = next(
        item
        for item in spec.components
        if item.id == component_id and item.type == module_type
    )
    config_names = {
        item["name"] for item in formula(module_type)["configuration"]
    }
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
    return vector


@pytest.mark.parametrize(
    "module_type",
    [
        "AggregateEfficiencyModule",
        "BooleanSwitchModule",
        "ConservationSumModule",
        "DiscreteIntegratorModule",
        "FirstOrderLagModule",
        "GainBiasModule",
        "HysteresisStateCheckModule",
        "MapBoundsCheckModule",
        "MassBalanceRateModule",
        "ProductModule",
        "RangeCheckModule",
        "RatioModule",
        "RotationalInertiaTorqueModule",
        "SumModule",
        "TankLevelVolumeModule",
        "TankVolumeRateModule",
        "ThresholdStateCheckModule",
        "TorqueSpeedPowerModule",
        "TranslationalInertiaForceModule",
        "ViscousDamperForceModule",
        "VolumetricMassFlowConversionModule",
        "WaterProductionFaradayModule",
    ],
)
def test_mechanical_draft_oracle_matches_current_runtime(module_type: str) -> None:
    payload = formula(module_type)
    assert payload["authoring_status"] == (
        "mechanical_draft_pending_independent_review"
    )
    assert payload["separate_review_status"] == "pending"
    assert payload["physical_claim_licensed"] is False
    record = ledger_records()[module_type]
    expected_role = record["residual_definitions"][0]["role"]
    expected_diagnostic = record["residual_definitions"][0]["diagnostic_key"]
    residual_formula = payload["residuals"][0]

    for case in payload["oracle_cases"]:
        builder, component_id, _ = exact_case_builder(module_type, case["inputs"])
        vector = apply_case_ports(builder, component_id, module_type, case["inputs"])
        actual = next(
            item
            for item in builder.diagnostic_residual_records(vector)
            if item.source == component_id
            and item.name == f"{component_id}.{residual_formula['name']}"
        )
        expected_value = case["expected"][residual_formula["name"]]
        expected_scale = checker()._restricted_expression(
            residual_formula["scale_expression"], case["inputs"]
        )
        assert actual.value == pytest.approx(
            float(expected_value), abs=float(case["tolerance"]), rel=0.0
        )
        assert actual.scale == pytest.approx(float(expected_scale))
        if isinstance(expected_role, dict):
            assert expected_role["expression"] == "role"
            assert actual.role == case["inputs"]["role"]
            assert actual.role in {
                item["value"] for item in expected_role["cases"]
            }
        else:
            assert actual.role == expected_role
        assert actual.diagnostic_key == expected_diagnostic


@pytest.mark.parametrize(
    "module_type",
    [
        "AggregateEfficiencyModule",
        "BooleanSwitchModule",
        "ConservationSumModule",
        "DiscreteIntegratorModule",
        "FirstOrderLagModule",
        "GainBiasModule",
        "HysteresisStateCheckModule",
        "MapBoundsCheckModule",
        "MassBalanceRateModule",
        "ProductModule",
        "RangeCheckModule",
        "RatioModule",
        "RotationalInertiaTorqueModule",
        "SumModule",
        "TankLevelVolumeModule",
        "TankVolumeRateModule",
        "ThresholdStateCheckModule",
        "TorqueSpeedPowerModule",
        "TranslationalInertiaForceModule",
        "ViscousDamperForceModule",
        "VolumetricMassFlowConversionModule",
        "WaterProductionFaradayModule",
    ],
)
def test_mechanical_draft_constructor_counterexample_still_fails(
    module_type: str,
) -> None:
    payload = formula(module_type)
    outside = next(
        case
        for case in payload["constraints"]["constructor"][0]["cases"]
        if case["kind"] == "outside"
    )
    record = ledger_records()[module_type]
    binding = record["bindings"]["instantiation"]
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


@pytest.mark.parametrize(
    "module_type", ("AggregateEfficiencyModule", "RatioModule")
)
def test_mechanical_draft_protected_denominator_counterexample_still_fails(
    module_type: str,
) -> None:
    payload = formula(module_type)
    outside = next(
        case
        for case in payload["constraints"]["evaluation"][0]["cases"]
        if case["kind"] == "outside"
    )
    case_inputs = dict(payload["oracle_cases"][0]["inputs"])
    case_inputs.update(outside["inputs"])
    builder, component_id, _ = exact_case_builder(module_type, case_inputs)
    vector = apply_case_ports(builder, component_id, module_type, case_inputs)

    with pytest.raises(ValueError):
        builder.diagnostic_residual_records(vector)
