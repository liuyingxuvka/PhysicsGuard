from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import hmac
import importlib
import inspect
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"

SCHEMA_ID = "physicsguard.module_semantics_ledger.v3"
CHECKER_IDENTITY = "physicsguard.module_semantics_ledger.checker.v3"
REVIEW_MANIFEST_SCHEMA = "physicsguard.module_semantics_review_manifest.v1"
REVIEW_REQUEST_SCHEMA = "physicsguard.module_semantics_review_request.v1"
REVIEW_RESULT_SCHEMA = "physicsguard.module_semantics_review_result.v1"
REVIEW_RECEIPT_SCHEMA = "physicsguard.module_semantics_review_receipt.v1"
REVIEW_PRODUCER_IDENTITY = "physicsguard.module_semantics_review_producer.v1"
REVIEW_PRODUCER_PATH = "scripts/module_semantics_review_producer.py"
BEHAVIOR_CONTRACT_SCHEMA = "physicsguard.module_behavior_contract.v1"
REVIEWER_PROVIDER_REGISTRY_SCHEMA = "physicsguard.module_semantics_reviewer_provider_registry.v1"
REVIEWER_PROVIDER_AUTHORITY_SCHEMA = "physicsguard.module_semantics_reviewer_provider_authority.v1"
REVIEWER_PROVIDER_EXECUTION_REQUEST_SCHEMA = "physicsguard.module_semantics_reviewer_provider_execution_request.v1"
REVIEWER_PROVIDER_RESULT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_result.v1"
REVIEWER_PROVIDER_RECEIPT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_receipt.v1"
REVIEWER_PROVIDER_TERMINAL_SUBJECT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_terminal_subject.v1"
REVIEWER_PROVIDER_ATTESTATION_SCHEMA = "physicsguard.module_semantics_reviewer_provider_attestation.v1"
REVIEWER_PROVIDER_SIGNATURE_ALGORITHM = "rsassa-pkcs1-v1_5-sha256"
REVIEWER_PROVIDER_REGISTRY_PATH = ".physicsguard/module_semantics_reviewer_provider_registry.json"
CASE_RUNNER_IDENTITY = "physicsguard.module_semantics_case_runner.v1"
ORACLE_RUNNER_IDENTITY = "physicsguard.module_semantics_restricted_oracle.v1"
RUNTIME_PORT_CONTRACT_IDENTITY = "physicsguard.module_runtime_port_contract.v1"
RUNTIME_PORT_REGISTRY_SCHEMA = "physicsguard.module_runtime_port_contract_registry.v2"
RUNTIME_PORT_REGISTRY_PATH = ".physicsguard/module_runtime_port_contracts.yaml"
UNIT_CONVENTION_SCHEMA = "physicsguard.project_unit_convention.v1"
UNIT_CONVENTION_REGISTRY_SCHEMA = "physicsguard.project_unit_convention_registry.v1"
UNIT_CONVENTION_REGISTRY_PATH = ".physicsguard/project_unit_conventions.yaml"
SOURCE_SEMANTIC_IR_SCHEMA = "physicsguard.module_source_semantic_ir.v1"
REGISTRY_OWNER = "physicsguard.modules.registry.default_module_registry"
FROZEN_REGISTRY_COUNT = 152
FROZEN_REGISTRY_FINGERPRINT = (
    "c57469d8a4095cd944978c1f58208834582b3ac183ea44ce1a510c542bd7252c"
)
DUMMY_MODULE_TYPE = "DummyResidualModule"
DEFAULT_JSON_BYTE_LIMIT = 80_000

DIMENSION_IDS = (
    "registry_inventory",
    "function_block",
    "equation_dependency",
    "unit",
    "constraint_valid_region",
    "behavioral_test",
    "counterexample",
    "independent_oracle",
    "independent_review",
)
SEMANTIC_DIMENSION_IDS = DIMENSION_IDS[1:]
BEHAVIOR_CONTRACT_DIMENSION_IDS = (
    "function_block",
    "equation_dependency",
    "unit",
    "constraint_valid_region",
    "behavioral_test",
    "counterexample",
    "independent_oracle",
)
# The public dummy module is deliberately retained as framework plumbing.  It
# still needs an independently reviewable software-behaviour record, but it is
# not a physical module and therefore must not be forced through physical-only
# equation, unit, region, or oracle obligations.  Keeping this denominator
# explicit prevents a framework fixture from either licensing a physical claim
# or falsely blocking the physical ledger with inapplicable questions.
SUPPORTING_FRAMEWORK_REQUIRED_DIMENSION_IDS = (
    "registry_inventory",
    "function_block",
    "behavioral_test",
    "counterexample",
    "independent_review",
)
SUPPORTING_FRAMEWORK_NON_APPLICABLE_DIMENSION_IDS = tuple(
    dimension
    for dimension in DIMENSION_IDS
    if dimension not in SUPPORTING_FRAMEWORK_REQUIRED_DIMENSION_IDS
)
SUPPORTING_FRAMEWORK_BEHAVIOR_CONTRACT_DIMENSION_IDS = (
    "function_block",
    "behavioral_test",
    "counterexample",
)

PREVIOUSLY_GROUPED_TYPES = frozenset(
    {
        "AggregateElectricalBusBalanceModule",
        "AggregateMassBalanceModule",
        "AggregatePowerBalanceModule",
        "AggregateThermalBalanceModule",
        "ControlErrorModule",
        "ConvectiveHeatTransferModule",
        "CoolantHeatBalanceModule",
        "DCDCConverterSimpleModule",
        "ElectricalPowerModule",
        "EfficiencyMap2DModule",
        "ElectrochemicalFaradayRateModule",
        "ElectrochemicalStackPowerModule",
        "ElectrolyzerGasProductionModule",
        "ElectrolyzerStackBalanceModule",
        "FuelCellCathodeAirSupplyModule",
        "FuelCellStackBalanceModule",
        "HVBusPowerBalanceModule",
        "IncompressibleOrificeModule",
        "IncompressiblePressureDropModule",
        "InverterSimpleModule",
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
    }
)

MECHANICALLY_DRAFTABLE_TYPES = frozenset(
    {
        "AggregateEfficiencyModule",
        "AirOxygenMolarFlowModule",
        "BooleanSwitchModule",
        "CellVoltageStackVoltageModule",
        "ChemicalPowerLHVModule",
        "ConservationSumModule",
        "CurrentDensityModule",
        "DensityMassVolumeModule",
        "DiscreteIntegratorModule",
        "EfficiencyModule",
        "FirstOrderLagModule",
        "ForceVelocityPowerModule",
        "GainBiasModule",
        "HysteresisStateCheckModule",
        "IdealGasDensityModule",
        "LinearRelationModule",
        "LinearSpringForceModule",
        "MapBoundsCheckModule",
        "MassBalanceRateModule",
        "MassMolarFlowConversionModule",
        "MoleFractionFlowModule",
        "PressureRatioModule",
        "ProductModule",
        "RangeCheckModule",
        "RatioModule",
        "RotationalInertiaTorqueModule",
        "SpecificEnthalpyFlowModule",
        "StackChemicalEfficiencyModule",
        "SumModule",
        "TankLevelVolumeModule",
        "TankVolumeRateModule",
        "ThresholdStateCheckModule",
        "TorqueSpeedPowerModule",
        "TranslationalInertiaForceModule",
        "ViscousDamperForceModule",
        "VolumetricMassFlowConversionModule",
        "WaterProductionFaradayModule",
    }
)

RETIRED_TOP_LEVEL_FIELDS = frozenset(
    {"ledger_version", "evidence_level", "entries", "inventory_disposition_groups"}
)
REQUIRED_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "project",
        "inventory_authority",
        "frozen_patch_baseline",
        "coverage_policy",
        "supporting_framework_baseline",
        "authoring_contract",
        "module_records",
    }
)
REQUIRED_RECORD_ENVELOPE = frozenset(
    {
        "module_type",
        "baseline_partition",
        "category",
        "physical_claim_licensed",
        "purpose",
        "function_block",
        "residual_definitions",
        "symbol_units",
        "constraints",
        "regions",
        "assumptions",
        "invariants",
        "diagnostic_keys",
        "bindings",
        "primary_owner",
        "provenance",
        "stale_triggers",
        "semantic_review",
    }
)
EXPRESSION_BUILTINS = frozenset(
    {
        "abs",
        "acos",
        "asin",
        "atan",
        "ceil",
        "clip",
        "cos",
        "e",
        "exp",
        "floor",
        "inf",
        "log",
        "max",
        "min",
        "nan",
        "pi",
        "pow",
        "sin",
        "sqrt",
        "tan",
        "True",
        "False",
        "None",
        "and",
        "or",
        "not",
        "if",
        "else",
        "is",
        "in",
        "hold",
        "decreasing",
        "increasing",
        "nondecreasing",
    }
)
GENERIC_TEXT_PATTERNS = (
    "equations_or_residuals and diagnostic_keys",
    "constructor/residual guards own",
    "inside declared variable bounds",
    "use outside the declared low-fidelity boundary",
)
EXPECTED_RESIDUAL_FIELDS = (
    "name",
    "value",
    "role",
    "scale",
    "diagnostic_key",
)
_PYTEST_COLLECTION_CACHE: dict[
    tuple[str, ...], tuple[set[str], str | None]
] = {}
_PYTEST_EXECUTION_CACHE: dict[tuple[str, ...], str | None] = {}
_RUNTIME_CONTRACT_CACHE: dict[tuple[str, ...], dict[str, Any]] = {}
_SOURCE_CONTRACT_CACHE: dict[tuple[str, ...], dict[str, Any]] = {}

_RESTRICTED_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "pow": pow,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "floor": math.floor,
    "ceil": math.ceil,
}
_CANONICAL_META_UNITS = frozenset({"1", "enum", "boolean", "index", "count"})
_CANONICAL_COMPOSITE_UNITS = frozenset(
    {
        "m^2",
        "m^3",
        "m/s^2",
        "m^3/s",
        "rad/s",
        "rad/s^2",
        "kg/m^3",
        "kg*m^2",
        "A/m^2",
        "W/m^2",
        "N*m",
        "N*s/m",
        "J/(kg*K)",
        "W/(m^2*K)",
        "kg^2/s^2",
        "1/s",
    }
)
_CANONICAL_UNIT_TOKEN = re.compile(
    r"^(?:1|kg|g|m|s|A|K|mol|cd|rad|Hz|N|Pa|J|W|C|V|F|Ohm|S|Wb|T|H)"
    r"(?:[*/^().0-9 +\-]*(?:kg|g|m|s|A|K|mol|cd|rad|Hz|N|Pa|J|W|C|V|F|Ohm|S|Wb|T|H))*$"
)


class _RestrictedExpressionError(ValueError):
    """Raised when a semantic predicate/oracle leaves the closed evaluator."""


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _finite_tree(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return _finite_number(value)
    if isinstance(value, list):
        return all(_finite_tree(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_tree(item) for key, item in value.items())
    return False


def _restricted_expression(value: Any, inputs: dict[str, Any]) -> Any:
    if not isinstance(value, str) or not value.strip():
        raise _RestrictedExpressionError("expression must be a non-empty string")
    if not _finite_tree(inputs):
        raise _RestrictedExpressionError("inputs contain NaN, infinity, or an unsupported value")
    try:
        node = ast.parse(value, mode="eval").body
    except SyntaxError as exc:
        raise _RestrictedExpressionError(f"expression is not parseable: {exc.msg}") from exc
    result = _eval_restricted_node(node, inputs)
    if not _finite_tree(result):
        raise _RestrictedExpressionError("expression result is NaN, infinity, or unsupported")
    return result


def _eval_restricted_node(node: ast.AST, inputs: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if not _finite_tree(node.value):
            raise _RestrictedExpressionError("non-finite or unsupported literal")
        return node.value
    if isinstance(node, ast.Name):
        if node.id in inputs:
            return inputs[node.id]
        if node.id == "pi":
            return math.pi
        if node.id == "e":
            return math.e
        raise _RestrictedExpressionError(f"unbound name: {node.id}")
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval_restricted_node(item, inputs) for item in node.elts]
    if isinstance(node, ast.Subscript):
        container = _eval_restricted_node(node.value, inputs)
        index = _eval_restricted_node(node.slice, inputs)
        if (
            not isinstance(container, (list, dict))
            or isinstance(index, bool)
            or not isinstance(index, (int, str))
        ):
            raise _RestrictedExpressionError(
                "subscript requires a finite list/integer or mapping/string pair"
            )
        if isinstance(container, list) and not isinstance(index, int):
            raise _RestrictedExpressionError("list subscript must be an integer")
        try:
            return container[index]
        except (IndexError, KeyError, TypeError) as exc:
            raise _RestrictedExpressionError(f"subscript failed: {exc}") from exc
    if isinstance(node, ast.UnaryOp):
        operand = _eval_restricted_node(node.operand, inputs)
        if isinstance(node.op, ast.UAdd) and _finite_number(operand):
            return +operand
        if isinstance(node.op, ast.USub) and _finite_number(operand):
            return -operand
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        raise _RestrictedExpressionError("unsupported unary operation")
    if isinstance(node, ast.BinOp):
        left = _eval_restricted_node(node.left, inputs)
        right = _eval_restricted_node(node.right, inputs)
        if not _finite_number(left) or not _finite_number(right):
            raise _RestrictedExpressionError("arithmetic operands must be finite numbers")
        operations = {
            ast.Add: lambda: left + right,
            ast.Sub: lambda: left - right,
            ast.Mult: lambda: left * right,
            ast.Div: lambda: left / right,
            ast.FloorDiv: lambda: left // right,
            ast.Mod: lambda: left % right,
            ast.Pow: lambda: left**right,
        }
        operation = operations.get(type(node.op))
        if operation is None:
            raise _RestrictedExpressionError("unsupported binary operation")
        try:
            result = operation()
        except (ArithmeticError, OverflowError, ValueError) as exc:
            raise _RestrictedExpressionError(f"arithmetic failed: {exc}") from exc
        if not _finite_number(result):
            raise _RestrictedExpressionError("arithmetic produced NaN or infinity")
        return result
    if isinstance(node, ast.BoolOp):
        values = [_eval_restricted_node(item, inputs) for item in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(item) for item in values)
        if isinstance(node.op, ast.Or):
            return any(bool(item) for item in values)
        raise _RestrictedExpressionError("unsupported boolean operation")
    if isinstance(node, ast.Compare):
        current = _eval_restricted_node(node.left, inputs)
        for operation, comparator in zip(node.ops, node.comparators, strict=True):
            other = _eval_restricted_node(comparator, inputs)
            if isinstance(operation, ast.Eq):
                passed = current == other
            elif isinstance(operation, ast.NotEq):
                passed = current != other
            elif isinstance(operation, ast.Lt):
                passed = current < other
            elif isinstance(operation, ast.LtE):
                passed = current <= other
            elif isinstance(operation, ast.Gt):
                passed = current > other
            elif isinstance(operation, ast.GtE):
                passed = current >= other
            elif isinstance(operation, ast.Is):
                passed = current is other
            elif isinstance(operation, ast.IsNot):
                passed = current is not other
            elif isinstance(operation, ast.In):
                passed = current in other
            elif isinstance(operation, ast.NotIn):
                passed = current not in other
            else:
                raise _RestrictedExpressionError("unsupported comparison")
            if not passed:
                return False
            current = other
        return True
    if isinstance(node, ast.IfExp):
        branch = node.body if bool(_eval_restricted_node(node.test, inputs)) else node.orelse
        return _eval_restricted_node(branch, inputs)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _RESTRICTED_FUNCTIONS:
            raise _RestrictedExpressionError("only registered pure functions may be called")
        if node.keywords:
            raise _RestrictedExpressionError("keyword arguments are not supported")
        arguments = [_eval_restricted_node(item, inputs) for item in node.args]
        if not all(_finite_number(item) for item in arguments):
            raise _RestrictedExpressionError("function arguments must be finite numbers")
        try:
            result = _RESTRICTED_FUNCTIONS[node.func.id](*arguments)
        except (ArithmeticError, OverflowError, TypeError, ValueError) as exc:
            raise _RestrictedExpressionError(f"pure function failed: {exc}") from exc
        if not _finite_number(result):
            raise _RestrictedExpressionError("pure function produced NaN or infinity")
        return result
    raise _RestrictedExpressionError(f"unsupported expression node: {type(node).__name__}")


def _canonical_unit_value(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return False
    if value in _CANONICAL_META_UNITS or value in _CANONICAL_COMPOSITE_UNITS:
        return True
    if value in {"caller_defined", "unknown", "unspecified", "-"}:
        return False
    return _CANONICAL_UNIT_TOKEN.fullmatch(value) is not None


def validate_ledger(root: Path = ROOT, ledger_path: Path = DEFAULT_LEDGER) -> list[str]:
    """Return every blocking finding from the sole current v3 review path."""

    return review_ledger(root, ledger_path)["errors"]


def review_ledger(
    root: Path = ROOT,
    ledger_path: Path = DEFAULT_LEDGER,
    *,
    review_scope: str = "full",
    module: str | None = None,
    execute_bound_tests: bool = False,
    execution_modules: set[str] | None = None,
    review_result_path: Path | None = None,
    review_receipt_path: Path | None = None,
) -> dict[str, Any]:
    if review_scope not in {"full", "module"}:
        raise ValueError("review_scope must be 'full' or 'module'")
    if review_scope == "module" and not _nonempty_string(module):
        raise ValueError("module review_scope requires one exact module type")
    if (review_result_path is None) != (review_receipt_path is None):
        raise ValueError("review_result_path and review_receipt_path must be supplied together")
    if review_result_path is not None and review_scope != "module":
        raise ValueError("external terminal review evidence is accepted only for one exact module scope")
    load_errors: list[str] = []
    data = _load_yaml(ledger_path, load_errors)
    registry_errors: list[str] = []
    registered_types = _registered_module_types(registry_errors)
    expected_partitions = _expected_partitions(registered_types, registry_errors)
    global_findings = _empty_findings()
    for message in load_errors + registry_errors:
        _add(global_findings, "registry_inventory", "inventory_authority_unavailable", message)

    if not isinstance(data, dict):
        _add(
            global_findings,
            "registry_inventory",
            "ledger_root_invalid",
            f"{_rel(ledger_path, root)}: root must be a mapping",
        )
        return _assemble_review(
            registered_types=registered_types,
            records_by_type={},
            record_results={},
            global_findings=global_findings,
            review_scope=review_scope,
            module=module,
        )

    retired = sorted(RETIRED_TOP_LEVEL_FIELDS & set(data))
    if retired:
        _add(
            global_findings,
            "registry_inventory",
            "retired_schema_present",
            "retired grouped navigation schema is not accepted: " + ", ".join(retired),
        )
    missing_top = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(data))
    for field in missing_top:
        _add(
            global_findings,
            "registry_inventory" if field != "authoring_contract" else "independent_review",
            "top_level_field_missing",
            f"missing required top-level field {field!r}",
        )
    if data.get("schema") != SCHEMA_ID:
        _add(
            global_findings,
            "registry_inventory",
            "schema_not_current",
            f"schema must be exactly {SCHEMA_ID}",
        )
    if data.get("project") != "PhysicsGuard":
        _add(
            global_findings,
            "registry_inventory",
            "project_identity_mismatch",
            "project must be PhysicsGuard",
        )

    _review_inventory_authority(data, registered_types, global_findings)
    _review_coverage_policy(data, global_findings)
    _review_frozen_baseline(data, expected_partitions, global_findings)
    _review_dummy_example_baseline(root, data, global_findings)
    _review_authoring_contract(root, data, global_findings)

    records = data.get("module_records")
    if not isinstance(records, list) or not records:
        _add(
            global_findings,
            "registry_inventory",
            "module_records_missing",
            "module_records must be a non-empty list",
        )
        records = []

    records_by_type: dict[str, dict[str, Any]] = {}
    owner_members: dict[str, list[str]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _add(
                global_findings,
                "registry_inventory",
                "record_not_mapping",
                f"module_records[{index}] must be a mapping",
            )
            continue
        module_type = record.get("module_type")
        if not isinstance(module_type, str) or not module_type.strip():
            _add(
                global_findings,
                "registry_inventory",
                "module_type_missing",
                f"module_records[{index}].module_type must be a non-empty string",
            )
            continue
        if module_type in records_by_type:
            _add(
                global_findings,
                "registry_inventory",
                "duplicate_module_record",
                f"{module_type}: duplicate per-module semantic record",
            )
            continue
        records_by_type[module_type] = record
        owner = record.get("primary_owner")
        if isinstance(owner, str):
            owner_members.setdefault(owner, []).append(module_type)

    missing = sorted(registered_types - set(records_by_type))
    extra = sorted(set(records_by_type) - registered_types)
    if missing:
        _add(
            global_findings,
            "registry_inventory",
            "registry_members_missing_records",
            "live public registry has members without records: " + ", ".join(missing),
        )
    if extra:
        _add(
            global_findings,
            "registry_inventory",
            "records_outside_registry",
            "ledger contains records outside the live registry: " + ", ".join(extra),
        )
    for owner, members in sorted(owner_members.items()):
        if len(members) > 1:
            _add(
                global_findings,
                "registry_inventory",
                "duplicate_primary_owner",
                f"primary_owner {owner!r} is shared by: {', '.join(sorted(members))}",
            )
    _review_dummy_public_contract(registered_types, global_findings)

    selected_records = (
        list(records_by_type.values())
        if review_scope == "full"
        else [records_by_type[module]]
        if module in records_by_type
        else []
    )
    test_paths = _bound_behavioral_test_paths(root, selected_records)
    execution_filter = execution_modules
    if review_scope == "module" and module is not None:
        execution_filter = {module}
    bound_nodeids = _bound_behavioral_test_nodeids(selected_records, execution_filter)
    collection_nodeids = bound_nodeids if review_scope == "module" else None
    collected_nodeids, collection_error = _collect_pytest_nodeids(
        root,
        test_paths,
        nodeids=collection_nodeids,
    )
    if collection_error:
        _add(global_findings, "behavioral_test", "pytest_collection_failed", collection_error)
        _add(global_findings, "counterexample", "pytest_collection_failed", collection_error)
    if execute_bound_tests:
        executed_nodeids, execution_error = _execute_pytest_nodeids(root, bound_nodeids)
        if execution_error:
            _add(global_findings, "behavioral_test", "pytest_batch_execution_failed", execution_error)
            _add(global_findings, "counterexample", "pytest_batch_execution_failed", execution_error)
    else:
        executed_nodeids, execution_error = set(), None

    external_review_evidence: dict[str, Any] | None = None
    if review_result_path is not None and review_receipt_path is not None:
        result_path = review_result_path if review_result_path.is_absolute() else root / review_result_path
        receipt_path = review_receipt_path if review_receipt_path.is_absolute() else root / review_receipt_path
        result_payload = _load_structured_file(result_path)
        receipt_payload = _load_structured_file(receipt_path)
        external_review_evidence = {
            "result": result_payload,
            "receipt": receipt_payload,
            "result_path": str(result_path.resolve()),
            "receipt_path": str(receipt_path.resolve()),
            "result_sha256": _sha256(result_path) if result_path.is_file() else None,
            "receipt_sha256": _sha256(receipt_path) if receipt_path.is_file() else None,
        }

    record_results: dict[str, dict[str, Any]] = {}
    owners: set[str] = set()
    for record in selected_records:
        module_type = str(record["module_type"])
        record_results[module_type] = _review_record(
            root,
            record,
            expected_partitions=expected_partitions,
            registered_types=registered_types,
            owners=owners,
            collected_nodeids=collected_nodeids,
            executed_nodeids=executed_nodeids,
            execution_requested=execute_bound_tests,
            ledger_path=ledger_path,
            external_review_evidence=external_review_evidence,
        )

    review = _assemble_review(
        registered_types=registered_types,
        records_by_type=records_by_type,
        record_results=record_results,
        global_findings=global_findings,
        review_scope=review_scope,
        module=module,
    )
    review["test_execution"] = {
        "requested": execute_bound_tests,
        "status": (
            "success"
            if execute_bound_tests and execution_error is None
            else "fail"
            if execute_bound_tests
            else "not_run"
        ),
        "bound_case_count": len(bound_nodeids),
        "executed_case_count": len(executed_nodeids),
        "error": execution_error,
        "module_scope": (
            [module]
            if review_scope == "module" and module is not None
            else sorted(execution_modules)
            if execution_modules is not None
            else "all"
        ),
    }
    return review


def _review_record(
    root: Path,
    record: dict[str, Any],
    *,
    expected_partitions: dict[str, set[str]],
    registered_types: set[str],
    owners: set[str] | None = None,
    collected_nodeids: set[str] | None = None,
    executed_nodeids: set[str] | None = None,
    execution_requested: bool = False,
    ledger_path: Path | None = None,
    external_review_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    findings = _empty_findings()
    module_type = str(record.get("module_type") or "<missing-module-type>")
    owners = owners if owners is not None else set()

    missing_fields = sorted(REQUIRED_RECORD_ENVELOPE - set(record))
    field_dimensions = {
        "physical_claim_licensed": "independent_review",
        "purpose": "function_block",
        "function_block": "function_block",
        "residual_definitions": "equation_dependency",
        "symbol_units": "unit",
        "constraints": "constraint_valid_region",
        "regions": "constraint_valid_region",
        "assumptions": "constraint_valid_region",
        "invariants": "constraint_valid_region",
        "diagnostic_keys": "equation_dependency",
        "bindings": "behavioral_test",
        "provenance": "independent_review",
        "stale_triggers": "independent_review",
        "semantic_review": "independent_review",
    }
    for field in missing_fields:
        _add(
            findings,
            field_dimensions.get(field, "registry_inventory"),
            "record_field_missing",
            f"{module_type}: missing required field {field!r}",
        )

    _review_record_inventory(
        record,
        module_type,
        expected_partitions,
        registered_types,
        owners,
        findings,
    )
    supporting_framework = record.get("category") == "supporting_framework_behavior"
    runtime = _runtime_contract(root, record, module_type)
    source_contract = _source_residual_contract(record, module_type)
    if supporting_framework:
        _review_supporting_framework_function_block(record, module_type, findings)
    else:
        _review_function_block(record, module_type, runtime, source_contract, findings)
        _review_equation_dependencies(record, module_type, runtime, source_contract, findings)
        _review_units(root, record, module_type, runtime, findings)
        _review_constraints_and_regions(record, module_type, source_contract, findings)
    behavioral_stages = _review_behavioral_evidence(
        root,
        record,
        module_type,
        findings,
        collected_nodeids=collected_nodeids,
        executed_nodeids=executed_nodeids,
        execution_requested=execution_requested,
    )
    oracle_stage = (
        {
            "status": "not_applicable",
            "producer_identity": ORACLE_RUNNER_IDENTITY,
            "reason": "supporting framework behaviour has no physical oracle obligation",
        }
        if supporting_framework
        else _review_independent_oracle(root, record, module_type, findings)
    )
    review_request, reviewer_stage = _review_semantic_review(
        root,
        record,
        module_type,
        findings,
        ledger_path=ledger_path,
        oracle_stage=oracle_stage,
        external_review_evidence=external_review_evidence,
    )
    behavior_contract = _project_behavior_contract(
        record,
        module_type,
        runtime=runtime,
        source_contract=source_contract,
        findings=findings,
    )
    first_gap = _first_record_gap(findings)

    return {
        "module_type": module_type,
        "category": record.get("category"),
        "physical_claim_licensed": record.get("physical_claim_licensed") is True,
        "behavior_contract": behavior_contract,
        "first_gap": first_gap,
        "dimensions": {
            dimension: _dimension_result(
                dimension,
                findings[dimension],
                applicability=(
                    "not_applicable"
                    if supporting_framework
                    and dimension in SUPPORTING_FRAMEWORK_NON_APPLICABLE_DIMENSION_IDS
                    else "applicable"
                ),
                claim_boundary=(
                    "framework-only; no physical meaning or physical claim is licensed"
                    if supporting_framework
                    and dimension in SUPPORTING_FRAMEWORK_NON_APPLICABLE_DIMENSION_IDS
                    else None
                ),
            )
            for dimension in DIMENSION_IDS
        },
        "execution_stages": {
            "import_and_instantiation": {
                "status": "success" if not runtime.get("error") else "fail",
                "isolation": "checker_process",
                "error": runtime.get("error"),
            },
            "test_collection": {
                "status": "success" if collected_nodeids is not None else "not_run",
                "collected_nodeid_count": len(
                    set(_bound_behavioral_test_nodeids([record], None))
                    & set(collected_nodeids or ())
                ),
            },
            **behavioral_stages,
            "oracle_execution": oracle_stage,
            "independent_review": reviewer_stage,
        },
        "review_request": review_request,
    }


def _review_supporting_framework_function_block(
    record: dict[str, Any],
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
) -> None:
    """Check the dummy's software contract without inventing physical meaning."""

    dimension = "function_block"
    if not _nonempty_string(record.get("purpose")):
        _add(findings, dimension, "purpose_missing", f"{module_type}: purpose must be a non-empty framework-behaviour statement")
    block = record.get("function_block")
    if not isinstance(block, dict):
        _add(findings, dimension, "function_block_missing", f"{module_type}: function_block must be a mapping")
        return
    if block.get("signature") != "Input × State -> Set(Output × State)":
        _add(findings, dimension, "function_block_signature_invalid", f"{module_type}: function_block.signature must be Input × State -> Set(Output × State)")

    declared = block.get("declared_variables")
    if not isinstance(declared, list) or len(declared) != 1 or not isinstance(declared[0], dict):
        _add(findings, dimension, "framework_declared_variables_invalid", f"{module_type}: framework record must declare exactly one input variable")
        declared_items: list[dict[str, Any]] = []
    else:
        declared_items = declared
    if declared_items:
        variable = declared_items[0]
        if variable.get("name") != "x" or variable.get("role") != "input":
            _add(findings, dimension, "framework_input_role_invalid", f"{module_type}: framework variable x must be the sole input")
        for field in ("unit", "lower_bound", "upper_bound", "initial_guess", "scale"):
            if field not in variable:
                _add(findings, dimension, "framework_variable_field_missing", f"{module_type}: framework input x must declare {field}")

    state = block.get("state")
    if not isinstance(state, dict) or any(
        state.get(slot) != [] for slot in ("previous", "current", "next")
    ) or state.get("hidden") is not False:
        _add(findings, dimension, "framework_state_contract_invalid", f"{module_type}: framework behaviour must declare no hidden or evolving state")

    outputs = block.get("outputs")
    if not isinstance(outputs, dict):
        _add(findings, dimension, "outputs_contract_missing", f"{module_type}: function_block.outputs must be a mapping")
    else:
        if outputs.get("declared_variables") != []:
            _add(findings, dimension, "framework_declared_output_invalid", f"{module_type}: x is an input; the framework output is the residual record")
        if outputs.get("residuals") != ["dummy_target"]:
            _add(findings, dimension, "framework_residual_output_invalid", f"{module_type}: framework output must be the dummy_target residual")

    residuals = record.get("residual_definitions")
    if not isinstance(residuals, list) or len(residuals) != 1 or not isinstance(residuals[0], dict):
        _add(findings, dimension, "framework_residual_definition_invalid", f"{module_type}: framework record must bind exactly one residual definition")
    else:
        residual = residuals[0]
        if residual.get("name") != "dummy_target" or residual.get("role") != "equation":
            _add(findings, dimension, "framework_residual_identity_invalid", f"{module_type}: residual identity must be dummy_target/equation")
        if residual.get("diagnostic_key") != "dummy_target_mismatch":
            _add(findings, dimension, "framework_diagnostic_key_invalid", f"{module_type}: residual diagnostic key must be dummy_target_mismatch")

    for field in ("effects", "failures", "preconditions", "postconditions"):
        values = block.get(field)
        if not isinstance(values, list) or not values:
            _add(findings, dimension, f"framework_{field}_missing", f"{module_type}: framework {field} must be an explicit non-empty list")
    if not _nonempty_string(block.get("termination")):
        _add(findings, dimension, "framework_termination_missing", f"{module_type}: framework termination must be explicit")


def _review_record_inventory(
    record: dict[str, Any],
    module_type: str,
    expected_partitions: dict[str, set[str]],
    registered_types: set[str],
    owners: set[str],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    if module_type not in registered_types:
        _add(
            findings,
            "registry_inventory",
            "module_not_registered",
            f"{module_type}: module type is not in the live public registry",
        )
    if "module_types" in record:
        _add(
            findings,
            "registry_inventory",
            "grouped_record_retired",
            f"{module_type}: grouped module_types rows are retired",
        )
    expected_partition = next(
        (name for name, members in expected_partitions.items() if module_type in members),
        None,
    )
    if record.get("baseline_partition") != expected_partition:
        _add(
            findings,
            "registry_inventory",
            "baseline_partition_mismatch",
            f"{module_type}: baseline_partition must be {expected_partition!r}",
        )
    is_dummy = module_type == DUMMY_MODULE_TYPE
    expected_category = "supporting_framework_behavior" if is_dummy else "physical_module"
    if record.get("category") != expected_category:
        _add(
            findings,
            "registry_inventory",
            "category_mismatch",
            f"{module_type}: category must be {expected_category}",
        )
    owner = record.get("primary_owner")
    expected_owner = f"physicsguard.module_semantics.{module_type}"
    if owner != expected_owner:
        _add(
            findings,
            "registry_inventory",
            "primary_owner_mismatch",
            f"{module_type}: primary_owner must be {expected_owner}",
        )
    elif owner in owners:
        _add(
            findings,
            "registry_inventory",
            "duplicate_primary_owner",
            f"{module_type}: duplicate primary_owner {owner}",
        )
    else:
        owners.add(owner)
    if is_dummy:
        _review_dummy_record(record, findings)


def _review_function_block(
    record: dict[str, Any],
    module_type: str,
    runtime: dict[str, Any],
    source_contract: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    dimension = "function_block"
    declaration_only = source_contract.get("declaration_only") is True
    if not _nonempty_string(record.get("purpose")):
        _add(findings, dimension, "purpose_missing", f"{module_type}: purpose must be a non-empty semantic statement")
    block = record.get("function_block")
    if not isinstance(block, dict):
        _add(findings, dimension, "function_block_missing", f"{module_type}: function_block must be a mapping")
        return
    if block.get("signature") != "Input × State -> Set(Output × State)":
        _add(
            findings,
            dimension,
            "function_block_signature_invalid",
            f"{module_type}: function_block.signature must be Input × State -> Set(Output × State)",
        )

    configuration = _mapping_list(
        block.get("configuration"),
        findings,
        dimension,
        "configuration_invalid",
        f"{module_type}: function_block.configuration",
        allow_empty=True,
    )
    config_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(configuration):
        name = item.get("name")
        label = f"{module_type}: function_block.configuration[{index}]"
        if not _nonempty_string(name):
            _add(findings, dimension, "configuration_name_missing", f"{label}.name must be non-empty")
            continue
        if name in config_by_name:
            _add(findings, dimension, "configuration_name_duplicate", f"{label}.name is duplicated: {name}")
        config_by_name[str(name)] = item
        if not isinstance(item.get("required"), bool):
            _add(findings, dimension, "configuration_required_not_boolean", f"{label}.required must be boolean")
        if "default" not in item:
            _add(findings, dimension, "configuration_default_missing", f"{label}.default must be explicit")
        if not _unit_value(item.get("unit")):
            _add(findings, dimension, "configuration_unit_missing", f"{label}.unit must be explicit")
        _require_string_list(
            item.get("constraints"),
            findings,
            dimension,
            "configuration_constraints_invalid",
            f"{label}.constraints",
            allow_empty=True,
        )

    declared = _mapping_list(
        block.get("declared_variables"),
        findings,
        dimension,
        "declared_variables_invalid",
        f"{module_type}: function_block.declared_variables",
        allow_empty=True,
    )
    variables_by_name: dict[str, dict[str, Any]] = {}
    roles = {"input", "output", "state_previous", "state_current", "state_next"}
    for index, item in enumerate(declared):
        label = f"{module_type}: function_block.declared_variables[{index}]"
        name = item.get("name")
        if not _nonempty_string(name):
            _add(findings, dimension, "declared_variable_name_missing", f"{label}.name must be non-empty")
            continue
        if name in variables_by_name:
            _add(findings, dimension, "declared_variable_duplicate", f"{label}.name is duplicated: {name}")
        variables_by_name[str(name)] = item
        if item.get("role") not in roles:
            _add(findings, dimension, "declared_variable_role_invalid", f"{label}.role is not current")
        for field in ("unit", "lower_bound", "upper_bound", "initial_guess", "scale"):
            if field not in item:
                _add(findings, dimension, "declared_variable_field_missing", f"{label}.{field} must be explicit")

    external_inputs = _mapping_list(
        block.get("external_inputs"),
        findings,
        dimension,
        "external_inputs_invalid",
        f"{module_type}: function_block.external_inputs",
        allow_empty=True,
    )
    external_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(external_inputs):
        label = f"{module_type}: function_block.external_inputs[{index}]"
        name = item.get("name")
        if not _nonempty_string(name):
            _add(findings, dimension, "external_input_name_missing", f"{label}.name must be non-empty")
            continue
        if name in external_by_name or name in variables_by_name:
            _add(findings, dimension, "external_input_name_duplicate", f"{label}.name is duplicated")
        external_by_name[str(name)] = item
        if item.get("role") != "input":
            _add(findings, dimension, "external_input_role_invalid", f"{label}.role must be input")
        if not _unit_value(item.get("unit")):
            _add(findings, dimension, "external_input_unit_missing", f"{label}.unit must be explicit")
        if not _nonempty_string(item.get("source_attribute")):
            _add(findings, dimension, "external_input_attribute_missing", f"{label}.source_attribute must be explicit")
        if not _nonempty_string(item.get("source_reference")) or "." not in str(item.get("source_reference")):
            _add(findings, dimension, "external_input_reference_missing", f"{label}.source_reference must be qualified")
        source_index = item.get("source_index")
        if source_index is not None and (
            not isinstance(source_index, int) or isinstance(source_index, bool) or source_index < 0
        ):
            _add(findings, dimension, "external_input_index_invalid", f"{label}.source_index must be a nonnegative integer or null")

    role_authority = block.get("role_authority")
    if runtime.get("port_contract_error"):
        _add(
            findings,
            dimension,
            "variable_role_authority_unresolved",
            f"{module_type}: {runtime['port_contract_error']}",
        )
    elif not isinstance(role_authority, dict):
        _add(findings, dimension, "variable_role_authority_missing", f"{module_type}: input/output/state roles have no independent authority")
    elif (
        role_authority.get("kind") != "runtime_port_contract"
        or role_authority.get("producer_identity") != RUNTIME_PORT_CONTRACT_IDENTITY
        or role_authority.get("contract_fingerprint") != runtime.get("port_contract_fingerprint")
    ):
        _add(findings, dimension, "variable_roles_unverified", f"{module_type}: declared port roles are not bound to the canonical runtime port contract")
    elif runtime.get("direction_scope") is not None and (
        role_authority.get("direction_scope") != runtime.get("direction_scope")
        or role_authority.get("relation_directionality")
        != runtime.get("relation_directionality")
        or role_authority.get("claim_boundary")
        != runtime.get("direction_claim_boundary")
        or role_authority.get("authority_evidence_fingerprint")
        != runtime.get("authority_evidence_fingerprint")
    ):
        _add(
            findings,
            dimension,
            "scenario_role_scope_unbound",
            (
                f"{module_type}: scenario roles must bind the exact direction scope, "
                "direction-neutral relation, claim boundary, and authority evidence"
            ),
        )

    state = block.get("state")
    state_groups: dict[str, list[str]] = {}
    if not isinstance(state, dict):
        _add(findings, dimension, "state_contract_missing", f"{module_type}: function_block.state must be a mapping")
    else:
        for slot in ("previous", "current", "next"):
            state_groups[slot] = _require_string_list(
                state.get(slot),
                findings,
                dimension,
                "state_slot_invalid",
                f"{module_type}: function_block.state.{slot}",
                allow_empty=True,
            )
        if not isinstance(state.get("hidden"), bool):
            _add(findings, dimension, "hidden_state_not_boolean", f"{module_type}: function_block.state.hidden must be boolean")
        elif state.get("hidden") is True:
            _add(findings, dimension, "hidden_state_unbound", f"{module_type}: hidden state is claimed without an independently bound state owner")
        for slot, role in (
            ("previous", "state_previous"),
            ("current", "state_current"),
            ("next", "state_next"),
        ):
            expected = {name for name, item in variables_by_name.items() if item.get("role") == role}
            actual = set(state_groups.get(slot, []))
            if actual != expected:
                _add(
                    findings,
                    dimension,
                    "state_role_mismatch",
                    f"{module_type}: function_block.state.{slot} must exactly match declared_variables role {role}",
                )

    outputs = block.get("outputs")
    if not isinstance(outputs, dict):
        _add(findings, dimension, "outputs_contract_missing", f"{module_type}: function_block.outputs must be a mapping")
    else:
        output_variables = _require_string_list(
            outputs.get("declared_variables"),
            findings,
            dimension,
            "output_variables_invalid",
            f"{module_type}: function_block.outputs.declared_variables",
            allow_empty=True,
        )
        output_residuals = _require_string_list(
            outputs.get("residuals"),
            findings,
            dimension,
            "output_residuals_invalid",
            f"{module_type}: function_block.outputs.residuals",
            allow_empty=declaration_only,
        )
        expected_output_variables = {
            name
            for name, item in variables_by_name.items()
            if item.get("role") in {"output", "state_next"}
        }
        if set(output_variables) != expected_output_variables:
            _add(
                findings,
                dimension,
                "declared_output_mismatch",
                f"{module_type}: outputs.declared_variables must exactly name output and state_next variables, not inputs",
            )
        residual_names = _residual_names(record)
        if set(output_residuals) != residual_names or len(output_residuals) != len(residual_names):
            _add(
                findings,
                dimension,
                "residual_output_mismatch",
                f"{module_type}: outputs.residuals must exactly name every residual definition",
            )
        if any(_generic_text(value) for value in output_variables + output_residuals):
            _add(
                findings,
                dimension,
                "placeholder_function_block_output",
                f"{module_type}: FunctionBlock outputs contain a placeholder rather than actual output names",
            )

    behavior_contract = record.get("behavior_contract")
    if declaration_only:
        declared_names = sorted(variables_by_name)
        if (
            not isinstance(behavior_contract, dict)
            or behavior_contract.get("kind") != "declaration_only"
            or behavior_contract.get("declared_variables") != declared_names
            or behavior_contract.get("mapped_variables") != declared_names
            or behavior_contract.get("residual_count") != 0
            or not isinstance(behavior_contract.get("effects"), list)
            or not behavior_contract["effects"]
            or behavior_contract.get("effects") != block.get("effects")
            or not isinstance(behavior_contract.get("postconditions"), list)
            or not behavior_contract["postconditions"]
            or behavior_contract.get("postconditions") != block.get("postconditions")
            or behavior_contract.get("termination") != block.get("termination")
        ):
            _add(
                findings,
                dimension,
                "declaration_only_behavior_contract_incomplete",
                (
                    f"{module_type}: zero residuals require the exact non-empty "
                    "declaration/mapping/effect/postcondition/termination contract"
                ),
            )
        if runtime.get("residuals") not in ([], None):
            _add(
                findings,
                dimension,
                "declaration_only_runtime_emitted_residual",
                f"{module_type}: declaration-only source unexpectedly emitted residuals",
            )
    elif not _residual_names(record):
        _add(
            findings,
            dimension,
            "ordinary_module_zero_residual_spoof",
            (
                f"{module_type}: only an implementation whose exact residuals() source "
                "returns the sole empty list may use a zero-residual FunctionBlock"
            ),
        )

    input_names = {name for name, item in variables_by_name.items() if item.get("role") == "input"}
    output_names = {name for name, item in variables_by_name.items() if item.get("role") == "output"}
    state_names = set().union(*(set(values) for values in state_groups.values())) if state_groups else set()
    semantic_sets = (input_names, output_names, state_names)
    if any(left & right for index, left in enumerate(semantic_sets) for right in semantic_sets[index + 1 :]):
        _add(findings, dimension, "variable_role_sets_overlap", f"{module_type}: input, output, and state role sets must be mutually exclusive")
    if set().union(*semantic_sets) != set(variables_by_name):
        _add(findings, dimension, "variable_role_partition_incomplete", f"{module_type}: input, output, and state roles must cover every declared variable exactly once")

    for field in ("effects", "failures", "preconditions", "postconditions"):
        _require_string_list(
            block.get(field),
            findings,
            dimension,
            f"function_block_{field}_invalid",
            f"{module_type}: function_block.{field}",
            allow_empty=True,
        )
    if not _nonempty_string(block.get("termination")):
        _add(findings, dimension, "termination_missing", f"{module_type}: function_block.termination must be explicit")

    if runtime.get("error"):
        _add(findings, dimension, "runtime_instantiation_unavailable", f"{module_type}: {runtime['error']}")
    elif runtime.get("declared_variables") is not None:
        actual_by_name = {item["name"]: item for item in runtime["declared_variables"]}
        if set(actual_by_name) != set(variables_by_name):
            _add(
                findings,
                dimension,
                "actual_declared_variables_mismatch",
                f"{module_type}: FunctionBlock declared_variables do not match runtime declare_variables() output",
            )
        for name in sorted(set(actual_by_name) & set(variables_by_name)):
            actual = actual_by_name[name]
            declared_item = variables_by_name[name]
            for field in ("unit", "lower_bound", "upper_bound", "initial_guess", "scale"):
                if not _same_scalar(actual.get(field), declared_item.get(field)):
                    _add(
                        findings,
                        dimension,
                        "actual_declared_variable_field_mismatch",
                        f"{module_type}: declared variable {name!r} field {field!r} differs from runtime output",
                    )
            actual_direction = actual.get("direction")
            if actual_direction is None:
                _add(
                    findings,
                    dimension,
                    "runtime_port_direction_unavailable",
                    f"{module_type}: runtime variable {name!r} carries no canonical input/output/state direction",
                )
            elif actual_direction != variables_by_name[name].get("role"):
                _add(
                    findings,
                    dimension,
                    "runtime_port_direction_mismatch",
                    f"{module_type}: declared role for {name!r} differs from the runtime port contract",
                )

    runtime_residuals = runtime.get("residuals")
    actual_residual_names = (
        {item["name"] for item in runtime_residuals}
        if isinstance(runtime_residuals, list) and runtime_residuals
        else source_contract.get("names")
    )
    if actual_residual_names:
        if residual_names := _residual_names(record):
            expected_runtime_names = {
                str(item.get("runtime_name", item.get("name")))
                for item in record.get("residual_definitions", [])
                if isinstance(item, dict) and _nonempty_string(item.get("name"))
            }
            if set(actual_residual_names) != expected_runtime_names:
                _add(
                    findings,
                    dimension,
                    "actual_residual_outputs_mismatch",
                    f"{module_type}: residual definitions do not match implementation ResidualRecord outputs",
                )
    elif source_contract.get("error"):
        runtime_detail = runtime.get("residual_error")
        suffix = f"; runtime replay also failed: {runtime_detail}" if runtime_detail else ""
        _add(findings, dimension, "actual_residual_outputs_unresolved", f"{module_type}: {source_contract['error']}{suffix}")


def _review_equation_dependencies(
    record: dict[str, Any],
    module_type: str,
    runtime: dict[str, Any],
    source_contract: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    dimension = "equation_dependency"
    declaration_only = source_contract.get("declaration_only") is True
    semantic_ir_binding = record.get("source_semantic_ir")
    if source_contract.get("semantic_ir_errors"):
        _add(
            findings,
            dimension,
            "source_semantic_ir_unresolved",
            f"{module_type}: " + "; ".join(source_contract["semantic_ir_errors"]),
        )
    if (
        not isinstance(semantic_ir_binding, dict)
        or semantic_ir_binding.get("schema") != SOURCE_SEMANTIC_IR_SCHEMA
        or semantic_ir_binding.get("fingerprint") != source_contract.get("semantic_ir_fingerprint")
    ):
        _add(
            findings,
            dimension,
            "source_semantic_ir_binding_missing",
            f"{module_type}: ledger equations are not bound to the current recursive source semantic IR",
        )
    declared_diagnostics = _require_string_list(
        record.get("diagnostic_keys"),
        findings,
        dimension,
        "diagnostic_keys_invalid",
        f"{module_type}: diagnostic_keys",
        allow_empty=declaration_only,
    )
    residuals = _mapping_list(
        record.get("residual_definitions"),
        findings,
        dimension,
        "residual_definitions_invalid",
        f"{module_type}: residual_definitions",
        allow_empty=declaration_only,
    )
    block = record.get("function_block") if isinstance(record.get("function_block"), dict) else {}
    configuration = block.get("configuration") if isinstance(block.get("configuration"), list) else []
    variables = block.get("declared_variables") if isinstance(block.get("declared_variables"), list) else []
    external_inputs = block.get("external_inputs") if isinstance(block.get("external_inputs"), list) else []
    base_symbols = {
        str(item.get("name"))
        for item in [*configuration, *variables, *external_inputs]
        if isinstance(item, dict) and _nonempty_string(item.get("name"))
    }
    names: set[str] = set()
    runtime_names: set[str] = set()
    any_piecewise = False
    implementation_projection_symbols = _source_projection_symbols(
        source_contract
    )
    for index, residual in enumerate(residuals):
        label = f"{module_type}: residual_definitions[{index}]"
        name = residual.get("name")
        if not _nonempty_string(name):
            _add(findings, dimension, "residual_name_missing", f"{label}.name must be non-empty")
        elif name in names:
            _add(findings, dimension, "residual_name_duplicate", f"{label}.name is duplicated: {name}")
        else:
            names.add(str(name))
        runtime_name = residual.get("runtime_name", name)
        if not _nonempty_string(runtime_name):
            _add(
                findings,
                dimension,
                "residual_runtime_name_invalid",
                f"{label}.runtime_name must be non-empty when provided",
            )
        elif runtime_name in runtime_names:
            _add(
                findings,
                dimension,
                "residual_runtime_name_duplicate",
                f"{label}.runtime_name is duplicated: {runtime_name}",
            )
        else:
            runtime_names.add(str(runtime_name))
        declared_role = residual.get("role")
        if not isinstance(declared_role, dict) and declared_role not in {"equation", "soft_check", "post_check"}:
            _add(findings, dimension, "residual_role_invalid", f"{label}.role must be a fixed role or an exact finite dynamic-role mapping")
        expression = residual.get("expression")
        if not _semantic_expression(expression):
            _add(findings, dimension, "residual_expression_invalid", f"{label}.expression must be a source-independent expression")
        dependencies = _require_string_list(
            residual.get("dependencies"),
            findings,
            dimension,
            "residual_dependencies_invalid",
            f"{label}.dependencies",
            allow_empty=False,
        )
        intermediates = _mapping_list(
            residual.get("intermediates"),
            findings,
            dimension,
            "intermediates_invalid",
            f"{label}.intermediates",
            allow_empty=True,
        )
        intermediate_names: set[str] = set()
        for intermediate_index, intermediate in enumerate(intermediates):
            intermediate_label = f"{label}.intermediates[{intermediate_index}]"
            symbol = intermediate.get("symbol")
            if not _nonempty_string(symbol):
                _add(findings, dimension, "intermediate_symbol_missing", f"{intermediate_label}.symbol must be non-empty")
                continue
            implementation_projection = (
                intermediate.get("binding_kind")
                == "implementation_source_projection"
            )
            if intermediate.get("binding_kind") not in {
                None,
                "implementation_source_projection",
            }:
                _add(
                    findings,
                    dimension,
                    "intermediate_binding_kind_invalid",
                    f"{intermediate_label}.binding_kind is not current",
                )
            if implementation_projection and (
                record.get("provenance", {}).get("authoring_mode")
                != "source_first_reconstruction_pending_independent_review"
            ):
                _add(
                    findings,
                    dimension,
                    "implementation_projection_scope_invalid",
                    f"{intermediate_label}: implementation projection is accepted only for source-first records",
                )
            if symbol in intermediate_names or (
                symbol in base_symbols and not implementation_projection
            ):
                _add(findings, dimension, "intermediate_symbol_duplicate", f"{intermediate_label}.symbol is duplicated: {symbol}")
            intermediate_names.add(str(symbol))
        allowed_symbols = base_symbols | intermediate_names
        for dependency in dependencies:
            if dependency not in allowed_symbols:
                _add(
                    findings,
                    dimension,
                    "undefined_equation_dependency",
                    f"{label}: dependency {dependency!r} has no configuration, declared-variable, or intermediate definition",
                )
        for intermediate_index, intermediate in enumerate(intermediates):
            intermediate_label = f"{label}.intermediates[{intermediate_index}]"
            if not _semantic_expression(intermediate.get("expression")):
                _add(findings, dimension, "intermediate_expression_invalid", f"{intermediate_label}.expression must be explicit")
            intermediate_dependencies = _require_string_list(
                intermediate.get("dependencies"),
                findings,
                dimension,
                "intermediate_dependencies_invalid",
                f"{intermediate_label}.dependencies",
                allow_empty=True,
            )
            for dependency in intermediate_dependencies:
                if dependency not in allowed_symbols:
                    _add(
                        findings,
                        dimension,
                        "undefined_intermediate_dependency",
                        f"{intermediate_label}: dependency {dependency!r} is undefined",
                    )
            _review_expression_closure(
                intermediate.get("expression"),
                set(intermediate_dependencies),
                allowed_symbols,
                findings,
                dimension,
                "intermediate_expression_dependency_missing",
                intermediate_label,
                implementation_projection=(
                    intermediate.get("binding_kind")
                    == "implementation_source_projection"
                ),
                implementation_symbols=implementation_projection_symbols,
            )
        _review_expression_closure(
            expression,
            set(dependencies),
            allowed_symbols,
            findings,
            dimension,
            "equation_expression_dependency_missing",
            label,
        )

        piecewise = residual.get("piecewise")
        branches = _mapping_list(
            residual.get("branches"),
            findings,
            dimension,
            "branches_invalid",
            f"{label}.branches",
            allow_empty=True,
        )
        if not isinstance(piecewise, bool):
            _add(findings, dimension, "piecewise_flag_missing", f"{label}.piecewise must be boolean")
        elif piecewise:
            any_piecewise = True
            if len(branches) < 2:
                _add(findings, dimension, "piecewise_branch_incomplete", f"{label}: piecewise residual requires at least two complete branches")
        elif branches:
            _add(findings, dimension, "non_piecewise_has_branches", f"{label}: branches require piecewise=true")
        for branch_index, branch in enumerate(branches):
            branch_label = f"{label}.branches[{branch_index}]"
            implementation_projection = (
                branch.get("binding_kind")
                == "implementation_source_projection"
            )
            if branch.get("binding_kind") not in {
                None,
                "implementation_source_projection",
            }:
                _add(
                    findings,
                    dimension,
                    "branch_binding_kind_invalid",
                    f"{branch_label}.binding_kind is not current",
                )
            if implementation_projection and (
                record.get("provenance", {}).get("authoring_mode")
                != "source_first_reconstruction_pending_independent_review"
            ):
                _add(
                    findings,
                    dimension,
                    "implementation_projection_scope_invalid",
                    f"{branch_label}: implementation projection is accepted only for source-first records",
                )
            if not _semantic_expression(branch.get("condition")):
                _add(findings, dimension, "branch_condition_invalid", f"{branch_label}.condition must be explicit")
            if not _semantic_expression(branch.get("expression")):
                _add(findings, dimension, "branch_expression_invalid", f"{branch_label}.expression must be explicit")
            _review_expression_closure(
                branch.get("condition"),
                set(dependencies),
                allowed_symbols,
                findings,
                dimension,
                "branch_dependency_missing",
                branch_label,
                implementation_projection=implementation_projection,
                implementation_symbols=implementation_projection_symbols,
            )
            _review_expression_closure(
                branch.get("expression"),
                set(dependencies),
                allowed_symbols,
                findings,
                dimension,
                "branch_dependency_missing",
                branch_label,
                implementation_projection=implementation_projection,
                implementation_symbols=implementation_projection_symbols,
            )

        scale = residual.get("scale")
        if not isinstance(scale, dict):
            _add(findings, dimension, "residual_scale_missing", f"{label}.scale must be a mapping")
        else:
            if not _semantic_expression(scale.get("expression")):
                _add(findings, dimension, "residual_scale_expression_invalid", f"{label}.scale.expression must be explicit")
            if not _unit_value(scale.get("unit")):
                _add(findings, dimension, "residual_scale_unit_missing", f"{label}.scale.unit must be explicit")
        for field in ("diagnostic_key", "description"):
            if not _nonempty_string(residual.get(field)):
                _add(findings, dimension, f"residual_{field}_missing", f"{label}.{field} must be non-empty")

        if _nonempty_string(name):
            source_expression = source_contract.get("expressions", {}).get(name)
            source_signature = source_contract.get("expression_signatures", {}).get(name)
            if source_signature is None:
                _add(findings, dimension, "implementation_expression_unresolved", f"{label}: implementation residual expression cannot be derived through a known pure source path")
            elif _expression_signature(expression) != source_signature:
                _add(findings, dimension, "implementation_expression_mismatch", f"{label}: ledger expression does not match implementation expression {source_expression!r}")

            source_scale = source_contract.get("scales", {}).get(name)
            source_scale_signature = source_contract.get("scale_signatures", {}).get(name)
            ledger_scale_signature = _expression_signature(scale.get("expression")) if isinstance(scale, dict) else None
            if source_scale_signature is None:
                _add(findings, dimension, "implementation_scale_unresolved", f"{label}: implementation residual scale cannot be derived through a known pure source path")
            elif ledger_scale_signature != source_scale_signature:
                _add(findings, dimension, "implementation_scale_mismatch", f"{label}: ledger scale expression does not match implementation scale {source_scale!r}")

            source_role_literal = source_contract.get("roles", {}).get(name)
            source_role_expression = source_contract.get("role_expressions", {}).get(name)
            declared_role = residual.get("role")
            if source_role_literal in {"equation", "soft_check", "post_check"}:
                if declared_role != source_role_literal:
                    _add(findings, dimension, "implementation_residual_role_mismatch", f"{label}: ledger role must match implementation role {source_role_literal!r}")
            elif source_role_expression:
                _review_dynamic_role_contract(declared_role, source_role_expression, findings, dimension, label)

    _review_source_branch_mapping(residuals, source_contract, module_type, findings, dimension)
    residual_diagnostics = {
        str(item.get("diagnostic_key"))
        for item in residuals
        if _nonempty_string(item.get("diagnostic_key"))
    }
    if set(declared_diagnostics) != residual_diagnostics:
        _add(
            findings,
            dimension,
            "diagnostic_key_set_mismatch",
            f"{module_type}: diagnostic_keys must exactly match residual_definitions",
        )
    runtime_residuals = runtime.get("residuals")
    if isinstance(runtime_residuals, list) and runtime_residuals:
        actual_roles = {item["name"]: item.get("role") for item in runtime_residuals}
        actual_diagnostics = {
            item["name"]: item.get("diagnostic_key") for item in runtime_residuals
        }
    else:
        actual_roles = source_contract.get("roles", {})
        actual_diagnostics = source_contract.get("diagnostics", {})
    for residual in residuals:
        name = residual.get("name")
        runtime_name = residual.get("runtime_name", name)
        if runtime_name in actual_roles and actual_roles[runtime_name] is not None:
            declared_role = residual.get("role")
            if isinstance(declared_role, dict):
                case_values = {
                    item.get("value")
                    for item in declared_role.get("cases", [])
                    if isinstance(item, dict)
                }
                if actual_roles[runtime_name] not in case_values:
                    _add(findings, dimension, "actual_residual_role_mismatch", f"{module_type}: runtime residual {name!r} role is outside the declared finite role cases")
            elif declared_role != actual_roles[runtime_name]:
                _add(findings, dimension, "actual_residual_role_mismatch", f"{module_type}: residual {name!r} role differs from implementation")
        if runtime_name in actual_diagnostics and residual.get("diagnostic_key") != actual_diagnostics[runtime_name]:
            _add(findings, dimension, "actual_diagnostic_key_mismatch", f"{module_type}: residual {name!r} diagnostic_key differs from implementation")


def _review_dynamic_role_contract(
    declared_role: Any,
    source_expression: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
    label: str,
) -> None:
    if not isinstance(declared_role, dict):
        _add(findings, dimension, "dynamic_role_cases_missing", f"{label}: dynamic implementation role {source_expression!r} requires expression plus the three finite role cases")
        return
    if _expression_signature(declared_role.get("expression")) != _expression_signature(source_expression):
        _add(findings, dimension, "implementation_residual_role_mismatch", f"{label}: dynamic role expression must match implementation {source_expression!r}")
    expected_cases = [
        {"when": "equation", "value": "equation"},
        {"when": "soft_check", "value": "soft_check"},
        {"when": "post_check", "value": "post_check"},
    ]
    if declared_role.get("cases") != expected_cases:
        _add(findings, dimension, "dynamic_role_cases_incomplete", f"{label}: dynamic role cases must exactly cover equation, soft_check, and post_check")


def _residual_symbol_closure(residual: dict[str, Any]) -> set[str]:
    symbols = {item for item in residual.get("dependencies", []) if isinstance(item, str)}
    expression = residual.get("expression")
    if isinstance(expression, str):
        symbols.update(_expression_identifiers(expression))
    intermediates = residual.get("intermediates")
    if isinstance(intermediates, list):
        for item in intermediates:
            if not isinstance(item, dict):
                continue
            if _nonempty_string(item.get("symbol")):
                symbols.add(str(item["symbol"]))
            symbols.update(dependency for dependency in item.get("dependencies", []) if isinstance(dependency, str))
            if isinstance(item.get("expression"), str):
                symbols.update(_expression_identifiers(item["expression"]))
    return symbols


def _review_source_branch_mapping(
    residuals: list[dict[str, Any]],
    source_contract: dict[str, Any],
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
) -> None:
    conditions = source_contract.get("conditions")
    if not isinstance(conditions, list):
        conditions = []
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        affected = {item for item in condition.get("affected_symbols", []) if isinstance(item, str)}
        # Conditions that affect only non-equation metadata (for example an
        # active-in-solver flag derived from the already-checked residual role)
        # do not belong in the equation branch map.
        if not affected:
            continue
        targets = [
            residual
            for residual in residuals
            if affected & _residual_symbol_closure(residual)
        ]
        target_symbols = set().union(
            *(_residual_symbol_closure(residual) for residual in targets)
        ) if targets else set()
        condition_symbols = (
            _expression_identifiers(str(condition.get("condition", "")))
            - EXPRESSION_BUILTINS
        )
        if condition_symbols - target_symbols:
            # The source class supports an optional branch that the bounded
            # exact-instantiation draft deliberately does not expose.
            continue
        branch_signatures: set[str] = set()
        for residual in targets:
            branches = residual.get("branches")
            if not isinstance(branches, list):
                continue
            for branch in branches:
                if isinstance(branch, dict):
                    signature = _expression_signature(branch.get("condition"))
                    if signature:
                        branch_signatures.add(signature)
        missing = [label for label, signature in (("true", condition.get("positive_signature")), ("false", condition.get("negative_signature"))) if signature not in branch_signatures]
        if missing:
            _add(findings, dimension, "implementation_branch_mapping_incomplete", f"{module_type}: source {condition.get('kind')} condition {condition.get('condition')!r} lacks structured {'/'.join(missing)} branch coverage")


def _review_units(
    root: Path,
    record: dict[str, Any],
    module_type: str,
    runtime: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    dimension = "unit"
    convention = record.get("unit_convention")
    convention_identity = convention.get("identity") if isinstance(convention, dict) else None
    registered_convention = _registered_unit_conventions(root).get(str(convention_identity))
    if (
        not isinstance(convention, dict)
        or convention.get("schema") != UNIT_CONVENTION_SCHEMA
        or registered_convention is None
        or convention != registered_convention
    ):
        _add(
            findings,
            dimension,
            "unit_convention_authority_unregistered",
            f"{module_type}: units are not bound to one registered independent project convention",
        )
    units = _mapping_list(
        record.get("symbol_units"),
        findings,
        dimension,
        "symbol_units_invalid",
        f"{module_type}: symbol_units",
        allow_empty=False,
    )
    unit_by_symbol: dict[str, dict[str, Any]] = {}
    allowed_kinds = {
        "configuration",
        "declared_variable",
        "declared_variable_residual",
        "external_input",
        "residual",
        "intermediate",
    }
    for index, item in enumerate(units):
        label = f"{module_type}: symbol_units[{index}]"
        symbol = item.get("symbol")
        if not _nonempty_string(symbol):
            _add(findings, dimension, "unit_symbol_missing", f"{label}.symbol must be non-empty")
            continue
        if symbol in unit_by_symbol:
            _add(findings, dimension, "unit_symbol_duplicate", f"{label}.symbol is duplicated: {symbol}")
        unit_by_symbol[str(symbol)] = item
        if not _canonical_unit_value(item.get("unit")):
            _add(findings, dimension, "unit_value_not_canonical", f"{label}.unit must use the canonical finite SI/meta-unit vocabulary")
        if item.get("kind") not in allowed_kinds:
            _add(findings, dimension, "unit_kind_invalid", f"{label}.kind is not current")
        reference = item.get("reference")
        if (
            not isinstance(reference, dict)
            or reference.get("convention_identity") != convention_identity
            or not _nonempty_string(reference.get("dimension"))
            or reference.get("unit") != item.get("unit")
        ):
            _add(findings, dimension, "unit_reference_not_explicit", f"{label}.reference must bind the exact registered convention, dimension, and unit")

    block = record.get("function_block") if isinstance(record.get("function_block"), dict) else {}
    for collection_name, expected_kind in (
        ("configuration", "configuration"),
        ("declared_variables", "declared_variable"),
        ("external_inputs", "external_input"),
    ):
        collection = block.get(collection_name) if isinstance(block.get(collection_name), list) else []
        for item in collection:
            if not isinstance(item, dict) or not _nonempty_string(item.get("name")):
                continue
            symbol = str(item["name"])
            authority = unit_by_symbol.get(symbol)
            if authority is None:
                _add(findings, dimension, "symbol_unit_authority_missing", f"{module_type}: symbol {symbol!r} has no symbol_units authority")
                continue
            if authority.get("kind") not in (
                {expected_kind, "declared_variable_residual"}
                if expected_kind == "declared_variable"
                else {expected_kind}
            ):
                _add(findings, dimension, "symbol_unit_kind_mismatch", f"{module_type}: symbol {symbol!r} has the wrong unit kind")
            if authority.get("unit") != item.get("unit"):
                _add(findings, dimension, "symbol_unit_mismatch", f"{module_type}: symbol {symbol!r} unit disagrees with its FunctionBlock declaration")

    if runtime.get("declared_variables") is not None:
        declared_runtime = {item["name"]: item for item in runtime["declared_variables"]}
        for name, actual in declared_runtime.items():
            authority = unit_by_symbol.get(name)
            if authority is not None and authority.get("unit") != _canonical_unit(actual.get("unit")):
                _add(findings, dimension, "runtime_unit_mismatch", f"{module_type}: symbol {name!r} unit disagrees with runtime declare_variables()")

    residuals = record.get("residual_definitions") if isinstance(record.get("residual_definitions"), list) else []
    for residual in residuals:
        if not isinstance(residual, dict) or not _nonempty_string(residual.get("name")):
            continue
        residual_name = str(residual["name"])
        scale = residual.get("scale") if isinstance(residual.get("scale"), dict) else {}
        authority = unit_by_symbol.get(residual_name)
        if authority is None:
            _add(findings, dimension, "residual_unit_authority_missing", f"{module_type}: residual {residual_name!r} has no symbol_units authority")
        elif authority.get("kind") not in {"residual", "declared_variable_residual"} or authority.get("unit") != scale.get("unit"):
            _add(findings, dimension, "residual_unit_mismatch", f"{module_type}: residual {residual_name!r} unit disagrees with its scale unit")


def _review_constraints_and_regions(
    record: dict[str, Any],
    module_type: str,
    source_contract: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    dimension = "constraint_valid_region"
    _require_string_list(
        record.get("assumptions"),
        findings,
        dimension,
        "assumptions_invalid",
        f"{module_type}: assumptions",
        allow_empty=False,
    )
    _require_string_list(
        record.get("invariants"),
        findings,
        dimension,
        "invariants_invalid",
        f"{module_type}: invariants",
        allow_empty=False,
    )
    constraints = record.get("constraints")
    if not isinstance(constraints, dict):
        _add(findings, dimension, "constraints_missing", f"{module_type}: constraints must be a mapping")
    else:
        total = 0
        for group in ("constructor", "evaluation"):
            items = _mapping_list(
                constraints.get(group),
                findings,
                dimension,
                "constraint_group_invalid",
                f"{module_type}: constraints.{group}",
                allow_empty=True,
            )
            total += len(items)
            for index, item in enumerate(items):
                label = f"{module_type}: constraints.{group}[{index}]"
                predicate = item.get("predicate")
                dependencies = item.get("dependencies")
                if not isinstance(predicate, str) or _expression_signature(predicate) is None:
                    _add(findings, dimension, "constraint_predicate_not_executable", f"{label}.predicate must be a restricted executable expression")
                if not isinstance(dependencies, list) or not dependencies or not all(_nonempty_string(value) for value in dependencies):
                    _add(findings, dimension, "constraint_symbol_closure_missing", f"{label}.dependencies must close the predicate symbol universe")
                elif isinstance(predicate, str) and (_expression_identifiers(predicate) - EXPRESSION_BUILTINS) != set(dependencies):
                    _add(findings, dimension, "constraint_symbol_closure_mismatch", f"{label}.dependencies do not exactly close the predicate")
                if not _nonempty_string(item.get("on_violation")):
                    _add(findings, dimension, "constraint_violation_missing", f"{label}.on_violation must be explicit")
                implementation = item.get("implementation_binding")
                if (
                    not isinstance(implementation, dict)
                    or implementation.get("source_semantic_ir_fingerprint") != source_contract.get("semantic_ir_fingerprint")
                    or not _nonempty_string(implementation.get("guard_signature"))
                    or not _nonempty_string(implementation.get("failure_type"))
                    or not _nonempty_string(implementation.get("message_selector"))
                ):
                    _add(findings, dimension, "constraint_implementation_binding_missing", f"{label} must bind the exact source guard and protected failure")
                _review_predicate_cases(item.get("cases"), predicate, module_type, label, findings, dimension)
        if total == 0:
            _add(findings, dimension, "constraints_empty", f"{module_type}: constructor/evaluation constraints cannot both be empty")

    regions = record.get("regions")
    if not isinstance(regions, dict):
        _add(findings, dimension, "regions_missing", f"{module_type}: regions must be a mapping")
    else:
        for group in ("valid", "invalid"):
            items = _mapping_list(
                regions.get(group),
                findings,
                dimension,
                "region_group_invalid",
                f"{module_type}: regions.{group}",
                allow_empty=False,
            )
            for index, item in enumerate(items):
                label = f"{module_type}: regions.{group}[{index}]"
                predicate = item.get("predicate")
                dependencies = item.get("dependencies")
                if not isinstance(predicate, str) or _expression_signature(predicate) is None:
                    _add(findings, dimension, "region_predicate_not_executable", f"{label}.predicate must be a restricted executable expression")
                if not isinstance(dependencies, list) or not dependencies or not all(_nonempty_string(value) for value in dependencies):
                    _add(findings, dimension, "region_symbol_closure_missing", f"{label}.dependencies must close the predicate symbol universe")
                if not _nonempty_string(item.get("meaning")) or _generic_text(str(item.get("meaning", ""))):
                    _add(findings, dimension, "region_meaning_invalid", f"{label}.meaning must be concrete")
                _review_predicate_cases(item.get("cases"), predicate, module_type, label, findings, dimension)


def _review_predicate_cases(
    cases: Any,
    predicate: Any,
    module_type: str,
    label: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
) -> None:
    if not isinstance(cases, list) or not cases or not all(isinstance(item, dict) for item in cases):
        _add(findings, dimension, "predicate_cases_missing", f"{label}.cases must contain executable inside/boundary/outside cases")
        return
    kinds = {item.get("kind") for item in cases}
    if kinds != {"inside", "boundary", "outside"}:
        _add(findings, dimension, "predicate_case_partition_incomplete", f"{label}.cases must exactly cover inside, boundary, and outside")
    for index, case in enumerate(cases):
        inputs = case.get("inputs")
        expected = case.get("expected")
        if not isinstance(inputs, dict) or expected not in {"pass", "fail"} or not _finite_tree(inputs):
            _add(findings, dimension, "predicate_case_invalid", f"{label}.cases[{index}] needs finite inputs and expected pass/fail")
            continue
        try:
            observed = _restricted_expression(predicate, inputs)
        except _RestrictedExpressionError as exc:
            _add(findings, dimension, "predicate_execution_failed", f"{label}.cases[{index}] cannot execute: {exc}")
            continue
        if not isinstance(observed, bool) or observed is not (expected == "pass"):
            _add(findings, dimension, "predicate_case_mismatch", f"{label}.cases[{index}] result differs from expected {expected}")


def _review_behavioral_evidence(
    root: Path,
    record: dict[str, Any],
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
    *,
    collected_nodeids: set[str] | None,
    executed_nodeids: set[str] | None,
    execution_requested: bool,
) -> dict[str, dict[str, Any]]:
    bindings = record.get("bindings")
    if not isinstance(bindings, dict):
        _add(findings, "behavioral_test", "bindings_missing", f"{module_type}: bindings must be a mapping")
        _add(findings, "counterexample", "bindings_missing", f"{module_type}: bindings must be a mapping")
        return {
            "behavioral_case_execution": {"status": "not_run", "reason": "bindings missing"},
            "counterexample_case_execution": {"status": "not_run", "reason": "bindings missing"},
        }
    implementation = bindings.get("implementation")
    _review_implementation_binding(root, implementation, module_type, findings)

    tests = bindings.get("behavioral_tests")
    if not isinstance(tests, dict):
        _add(findings, "behavioral_test", "behavioral_tests_missing", f"{module_type}: bindings.behavioral_tests must be a mapping")
        _add(findings, "counterexample", "behavioral_tests_missing", f"{module_type}: bindings.behavioral_tests must be a mapping")
        positive = counterexample = None
    else:
        positive = tests.get("positive")
        counterexample = tests.get("counterexample")
        _review_test_binding(
            root,
            positive,
            module_type,
            "positive",
            findings,
            "behavioral_test",
            collected_nodeids=collected_nodeids,
            executed_nodeids=executed_nodeids,
            execution_requested=execution_requested,
        )
        positive_stage = _review_structured_case_execution(
            root, positive, module_type, "positive", findings, "behavioral_test"
        )
        _review_test_binding(
            root,
            counterexample,
            module_type,
            "counterexample",
            findings,
            "counterexample",
            collected_nodeids=collected_nodeids,
            executed_nodeids=executed_nodeids,
            execution_requested=execution_requested,
        )
        counterexample_stage = _review_structured_case_execution(
            root,
            counterexample,
            module_type,
            "counterexample",
            findings,
            "counterexample",
        )
        positive_identity = _binding_identity(positive)
        counterexample_identity = _binding_identity(counterexample)
        if positive_identity is not None and positive_identity == counterexample_identity:
            _add(
                findings,
                "counterexample",
                "counterexample_not_distinct",
                f"{module_type}: positive and counterexample test selectors/cases must be distinct",
            )

    _review_instantiation(root, bindings.get("instantiation"), module_type, findings)
    if not isinstance(tests, dict):
        positive_stage = {"status": "not_run", "reason": "behavioral_tests missing"}
        counterexample_stage = {"status": "not_run", "reason": "behavioral_tests missing"}
    return {
        "behavioral_case_execution": positive_stage,
        "counterexample_case_execution": counterexample_stage,
    }


def _review_implementation_binding(
    root: Path,
    binding: Any,
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
) -> None:
    if not isinstance(binding, dict):
        _add(findings, "function_block", "implementation_binding_missing", f"{module_type}: bindings.implementation must be a mapping")
        return
    _review_bound_file(root, binding, module_type, "implementation", findings, "function_block")
    symbol = binding.get("python_symbol")
    resolved = _resolve_python_symbol(module_type, symbol)
    if resolved.get("error"):
        _add(findings, "function_block", "implementation_symbol_unresolved", f"{module_type}: {resolved['error']}")
    elif resolved.get("value") is not None:
        expected_path = Path(inspect.getsourcefile(resolved["value"]) or "")
        try:
            expected_rel = expected_path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            expected_rel = str(expected_path)
        if binding.get("path") != expected_rel:
            _add(findings, "function_block", "implementation_path_mismatch", f"{module_type}: implementation.path must match {expected_rel}")


def _review_test_binding(
    root: Path,
    binding: Any,
    module_type: str,
    role: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
    *,
    collected_nodeids: set[str] | None,
    executed_nodeids: set[str] | None = None,
    execution_requested: bool = False,
) -> None:
    disposition = _binding_disposition(binding)
    if disposition != "bound":
        reason = binding.get("reason") if isinstance(binding, dict) else None
        if disposition not in {"missing"} or not _nonempty_string(reason):
            _add(findings, dimension, "test_binding_disposition_invalid", f"{module_type}: {role} test must be bound or explicitly missing with a reason")
        else:
            _add(findings, dimension, f"{role}_test_missing", f"{module_type}: {role} behavioral test is missing: {reason}")
        return
    path = _review_bound_file(root, binding, module_type, f"behavioral_tests.{role}", findings, dimension)
    if path is None:
        return
    selector = binding.get("selector")
    case = binding.get("case")
    pytest_nodeid = binding.get("pytest_nodeid")
    if not _nonempty_string(case):
        _add(findings, dimension, "test_case_missing", f"{module_type}: {role} test case identity must be explicit")
    if not isinstance(selector, str) or re.fullmatch(r"test_[A-Za-z0-9_]+", selector) is None:
        _add(findings, dimension, "test_selector_not_exact", f"{module_type}: {role} selector must name one exact pytest test function")
        return
    selected = _python_function(path, selector)
    if selected is None:
        _add(findings, dimension, "test_selector_unresolved", f"{module_type}: {role} selector {selector!r} does not resolve to a test function")
        return
    relative_path = path.relative_to(root).as_posix()
    expected_nodeid = (
        f"{relative_path}::{selector}"
        if case == "unparameterized"
        else f"{relative_path}::{selector}[{case}]"
    )
    if pytest_nodeid != expected_nodeid:
        _add(
            findings,
            dimension,
            "pytest_nodeid_mismatch",
            f"{module_type}: {role} pytest_nodeid must be exactly {expected_nodeid}",
        )
    effective_collection = collected_nodeids
    if effective_collection is None:
        effective_collection, collection_error = _collect_pytest_nodeids(root, [path])
        if collection_error:
            _add(findings, dimension, "pytest_collection_failed", collection_error)
    if effective_collection is not None and expected_nodeid not in effective_collection:
        _add(
            findings,
            dimension,
            "pytest_nodeid_not_collectable",
            f"{module_type}: {role} pytest nodeid is not collectable: {expected_nodeid}",
        )

    module_parameter = binding.get("module_parameter")
    execution_source = _local_test_execution_source(path, selector)
    if module_parameter is None:
        if module_type not in execution_source:
            _add(
                findings,
                dimension,
                "test_module_not_bound",
                f"{module_type}: {role} test neither names the exact module nor binds a module_type parameter",
            )
    elif not isinstance(module_parameter, dict):
        _add(findings, dimension, "module_parameter_invalid", f"{module_type}: {role} module_parameter must be a mapping or null")
    else:
        if module_parameter != {"name": "module_type", "value": module_type}:
            _add(
                findings,
                dimension,
                "module_parameter_mismatch",
                f"{module_type}: {role} module_parameter must bind module_type to the exact module",
            )
        if not _parametrize_declares_module_case(path, selector, module_type, str(case)):
            _add(
                findings,
                dimension,
                "module_parameter_case_unverified",
                f"{module_type}: {role} decorator/constants do not bind this collected case to module_type",
            )

    _review_expected_outcome(binding, module_type, role, findings, dimension)
    _review_case_contract(binding, module_type, role, findings, dimension)
    if "execution_evidence" in binding:
        _add(
            findings,
            dimension,
            "caller_execution_evidence_unauthorized",
            f"{module_type}: {role} caller-authored execution_evidence cannot license behavior",
        )
    body = execution_source
    behavior_markers = (
        "ResidualBuilder",
        "record_for",
        "diagnostic_residual_records",
        ".residuals(",
        "load_system_spec",
        "BoundedSolver",
    )
    registry_only = "default_module_registry" in body or "registered_types" in body
    if registry_only and not any(marker in body for marker in behavior_markers):
        _add(
            findings,
            dimension,
            "registry_only_test_selector",
            f"{module_type}: {role} selector proves registry membership only, not behavior",
        )
    contract_evidence = _test_contract_evidence(body, module_type, binding.get("expected_outcome"))
    for code, message in contract_evidence:
        _add(findings, dimension, code, f"{module_type}: {role} {message}")
    if execution_requested:
        if executed_nodeids is None or expected_nodeid not in executed_nodeids:
            _add(findings, dimension, "pytest_case_execution_unverified", f"{module_type}: {role} exact pytest case lacks a terminal-success batch result")
    else:
        _add(findings, dimension, "test_execution_evidence_not_run", f"{module_type}: {role} test design is bound, but execution was not requested and no current terminal evidence is attached")


def _review_expected_outcome(
    binding: dict[str, Any],
    module_type: str,
    role: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
) -> None:
    outcome = binding.get("expected_outcome")
    if not isinstance(outcome, dict):
        _add(
            findings,
            dimension,
            "expected_outcome_missing",
            f"{module_type}: {role} binding must declare a typed expected_outcome",
        )
        return
    kind = outcome.get("kind")
    if role == "positive" and kind not in {
        "residual_record",
        "declaration_contract",
    }:
        _add(
            findings,
            dimension,
            "positive_outcome_invalid",
            (
                f"{module_type}: positive expected_outcome.kind must be "
                "residual_record or declaration_contract"
            ),
        )
        return
    if role == "positive" and kind == "declaration_contract":
        declarations = outcome.get("declared_variables")
        if (
            not isinstance(declarations, list)
            or not declarations
            or not all(
                isinstance(item, dict) and _nonempty_string(item.get("name"))
                for item in declarations
            )
            or outcome.get("residual_count") != 0
        ):
            _add(
                findings,
                dimension,
                "declaration_outcome_incomplete",
                (
                    f"{module_type}: declaration_contract needs exact non-empty "
                    "declarations and residual_count=0"
                ),
            )
        return
    if role == "positive" or kind == "residual_violation":
        if outcome.get("residual_fields") != list(EXPECTED_RESIDUAL_FIELDS):
            _add(
                findings,
                dimension,
                "expected_residual_fields_incomplete",
                f"{module_type}: {role} residual outcome must bind {list(EXPECTED_RESIDUAL_FIELDS)}",
            )
        if kind == "residual_violation" and not _nonempty_string(outcome.get("violation")):
            _add(
                findings,
                dimension,
                "residual_violation_missing",
                f"{module_type}: residual_violation must name the expected violation",
            )
        return
    if kind == "raises":
        exception_type = outcome.get("exception_type")
        message_selector = outcome.get("message_selector")
        if (
            not _nonempty_string(exception_type)
            or exception_type in {"Exception", "BaseException"}
            or not _nonempty_string(message_selector)
        ):
            _add(
                findings,
                dimension,
                "raises_outcome_incomplete",
                f"{module_type}: raises outcome needs an exact exception type and protected message selector",
            )
        return
    if kind == "audit_fail":
        if not _nonempty_string(outcome.get("status_field")) or not _nonempty_string(
            outcome.get("finding_or_diagnostic")
        ):
            _add(
                findings,
                dimension,
                "audit_fail_outcome_incomplete",
                f"{module_type}: audit_fail outcome needs status_field and finding_or_diagnostic",
            )
        return
    _add(
        findings,
        dimension,
        "counterexample_outcome_invalid",
        f"{module_type}: counterexample outcome must be raises, audit_fail, or residual_violation",
    )


def _review_case_contract(
    binding: dict[str, Any],
    module_type: str,
    role: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
) -> None:
    contract = binding.get("case_contract")
    outcome = binding.get("expected_outcome")
    if not isinstance(contract, dict):
        _add(findings, dimension, "test_case_contract_missing", f"{module_type}: {role} binding needs an executable case contract")
        return
    if not isinstance(contract.get("inputs"), dict) or not contract.get("inputs"):
        _add(findings, dimension, "test_case_inputs_missing", f"{module_type}: {role} case contract needs concrete inputs/configuration")
    if not _nonempty_string(contract.get("obligation")):
        _add(findings, dimension, "test_case_obligation_missing", f"{module_type}: {role} case contract needs a bounded behavioral obligation")
    expected_kind = outcome.get("kind") if isinstance(outcome, dict) else None
    if contract.get("assertion_kind") != expected_kind:
        _add(findings, dimension, "test_case_assertion_mismatch", f"{module_type}: {role} case assertion_kind must match expected_outcome")
    if contract.get("expected_fingerprint") != _canonical_hash(outcome):
        _add(findings, dimension, "test_case_expected_stale", f"{module_type}: {role} case contract must fingerprint the exact expected_outcome")


def _current_test_execution_evidence(binding: dict[str, Any], nodeid: str) -> bool:
    evidence = binding.get("execution_evidence")
    if not isinstance(evidence, dict):
        return False
    subject = {
        "pytest_nodeid": nodeid,
        "test_sha256": binding.get("sha256"),
        "case_contract": binding.get("case_contract"),
        "expected_outcome": binding.get("expected_outcome"),
    }
    return (
        evidence.get("terminal_status") == "success"
        and _nonempty_string(evidence.get("receipt_id"))
        and evidence.get("pytest_nodeid") == nodeid
        and evidence.get("test_sha256") == binding.get("sha256")
        and evidence.get("subject_fingerprint") == _canonical_hash(subject)
    )


def _review_structured_case_execution(
    root: Path,
    binding: Any,
    module_type: str,
    role: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
) -> dict[str, Any]:
    contract = binding.get("case_contract") if isinstance(binding, dict) else None
    outcome = binding.get("expected_outcome") if isinstance(binding, dict) else None
    if not isinstance(contract, dict) or not isinstance(outcome, dict):
        return {"status": "not_run", "producer_identity": CASE_RUNNER_IDENTITY, "reason": "structured case contract is incomplete"}
    inputs = contract.get("inputs")
    if not isinstance(inputs, dict):
        return {"status": "not_run", "producer_identity": CASE_RUNNER_IDENTITY, "reason": "structured inputs are missing"}
    component_id = inputs.get("component_id")
    parameters = inputs.get("parameters")
    variables = inputs.get("variables")
    external_variables = inputs.get("external_variables", [])
    if (
        contract.get("runner_identity") != CASE_RUNNER_IDENTITY
        or not _nonempty_string(component_id)
        or not isinstance(parameters, dict)
        or not isinstance(variables, dict)
        or not isinstance(external_variables, list)
        or any(
            not isinstance(item, dict)
            or not _nonempty_string(item.get("name"))
            or not _unit_value(item.get("unit"))
            for item in external_variables
        )
        or not _finite_tree(parameters)
        or not _finite_tree(variables)
        or not _finite_tree(external_variables)
    ):
        _add(
            findings,
            dimension,
            "structured_case_contract_unexecutable",
            f"{module_type}: {role} case must bind the canonical runner, component_id, finite parameters, and finite variables",
        )
        return {"status": "not_run", "producer_identity": CASE_RUNNER_IDENTITY, "reason": "structured inputs are not executable"}
    request = {
        "producer_identity": CASE_RUNNER_IDENTITY,
        "module_type": module_type,
        "component_id": component_id,
        "parameters": parameters,
        "variables": variables,
        "external_variables": external_variables,
    }
    observed = _execute_case_subprocess(root, request)
    comparison_error = _compare_case_observation(observed, contract, outcome)
    if comparison_error is not None:
        _add(
            findings,
            dimension,
            "structured_case_observation_mismatch",
            f"{module_type}: {role} {comparison_error}",
        )
        status = "fail"
    else:
        status = "success"
    return {
        "status": status,
        "producer_identity": CASE_RUNNER_IDENTITY,
        "request_fingerprint": _canonical_hash(request),
        "observation_fingerprint": _canonical_hash(observed),
        "observation": observed,
        "error": comparison_error,
        "isolation": "subprocess_temporary_working_directory",
    }


def _execute_case_subprocess(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    environment = os.environ.copy()
    import_roots = [str(root), str(root / "src")]
    if environment.get("PYTHONPATH"):
        import_roots.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(import_roots)
    try:
        with tempfile.TemporaryDirectory(prefix="physicsguard-case-") as working_directory:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--internal-run-case"],
                cwd=working_directory,
                input=json.dumps(request, separators=(",", ":"), ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=20,
                env=environment,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "runner_failure", "error": str(exc)}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "status": "runner_failure",
            "error": f"case subprocess returned invalid JSON (exit {completed.returncode}): {completed.stderr.strip()}",
        }
    if not isinstance(payload, dict):
        return {"status": "runner_failure", "error": "case subprocess result is not a mapping"}
    payload["exit_status"] = completed.returncode
    return payload


def _run_case_request(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("producer_identity") != CASE_RUNNER_IDENTITY:
        return {"status": "runner_failure", "error": "case runner identity mismatch"}
    module_type = request.get("module_type")
    component_id = request.get("component_id")
    parameters = request.get("parameters")
    values = request.get("variables")
    external_variables = request.get("external_variables", [])
    if not all((_nonempty_string(module_type), _nonempty_string(component_id))):
        return {"status": "runner_failure", "error": "module_type/component_id missing"}
    if (
        not isinstance(parameters, dict)
        or not isinstance(values, dict)
        or not isinstance(external_variables, list)
        or not _finite_tree(parameters)
        or not _finite_tree(values)
        or not _finite_tree(external_variables)
    ):
        return {"status": "runner_failure", "error": "parameters/variables are invalid or non-finite"}
    try:
        import numpy as np

        from physicsguard.core.registry import VariableRecord, VariableRegistry
        from physicsguard.modules.registry import default_module_registry

        registry_owner = default_module_registry()
        instance = registry_owner.create(str(module_type), str(component_id), parameters)
        if instance.__class__.__name__ != module_type:
            raise TypeError("registered factory returned a different module type")
        variable_registry = VariableRegistry()
        declared = instance.declare_variables()
        declaration_observations = [
            {
                "name": str(variable.name).rsplit(".", 1)[-1],
                "unit": variable.unit,
                "lower_bound": float(variable.lower_bound),
                "upper_bound": float(variable.upper_bound),
                "initial_guess": float(variable.initial_guess),
                "scale": float(variable.scale),
            }
            for variable in declared
        ]
        for variable in declared:
            variable_registry.add_variable(variable)
        external_names: set[str] = set()
        for item in external_variables:
            if (
                not isinstance(item, dict)
                or not _nonempty_string(item.get("name"))
                or not _unit_value(item.get("unit"))
            ):
                raise ValueError("external variable binding is malformed")
            name = str(item["name"])
            if name in external_names or name in variable_registry.names():
                raise ValueError(f"duplicate external variable binding: {name}")
            if name not in values or not _finite_number(values[name]):
                raise ValueError(f"external variable {name!r} lacks a finite case value")
            value = float(values[name])
            span = max(1.0, abs(value) * 2.0)
            variable_registry.add_variable(
                VariableRecord(
                    name=name,
                    unit=str(item["unit"]),
                    lower_bound=value - span,
                    upper_bound=value + span,
                    initial_guess=value,
                    scale=max(1.0, abs(value)),
                )
            )
            external_names.add(name)
        expected_names = set(variable_registry.names())
        normalized_values: dict[str, Any] = {}
        for name, value in values.items():
            qualified = name if "." in str(name) else f"{component_id}.{name}"
            normalized_values[qualified] = value
        if set(normalized_values) != expected_names:
            missing = sorted(expected_names - set(normalized_values))
            unknown = sorted(set(normalized_values) - expected_names)
            raise ValueError(f"case variables must exactly cover declarations; missing={missing}, unknown={unknown}")
        vector = variable_registry.dict_to_vector(normalized_values) if expected_names else np.array([], dtype=float)
        records = instance.residuals(vector, variable_registry)
        observations = [
            {
                "name": str(item.name).removeprefix(f"{component_id}."),
                "role": item.role,
                "value": float(item.value),
                "scale": float(item.scale),
                "diagnostic_key": item.diagnostic_key,
            }
            for item in records
        ]
        if not _finite_tree(observations) or any(item["scale"] <= 0 for item in observations):
            raise ValueError("registered module emitted a non-finite observation or non-positive scale")
        return {
            "status": "observed",
            "registered_module_type": instance.__class__.__name__,
            "declarations": declaration_observations,
            "observations": observations,
        }
    except Exception as exc:  # protected failures are observations, not runner crashes
        return {
            "status": "observed_exception",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }


def _compare_case_observation(
    observed: dict[str, Any],
    contract: dict[str, Any],
    outcome: dict[str, Any],
) -> str | None:
    if observed.get("status") == "runner_failure":
        return f"runner failed: {observed.get('error')}"
    kind = outcome.get("kind")
    if kind == "raises":
        if observed.get("status") != "observed_exception":
            return "expected a protected exception but the registered module returned normally"
        if observed.get("exception_type") != outcome.get("exception_type"):
            return "protected exception type differs"
        selector = outcome.get("message_selector")
        if not _nonempty_string(selector) or selector not in str(observed.get("message", "")):
            return "protected exception message does not contain the exact selector"
        return None
    if kind == "declaration_contract":
        if observed.get("status") != "observed":
            return f"expected declaration observation, got {observed.get('status')}"
        expected_declarations = contract.get("expected_declarations")
        if observed.get("declarations") != expected_declarations:
            return "declared variable contract differs"
        expected_residual_count = contract.get("expected_residual_count")
        if expected_residual_count != 0 or len(observed.get("observations", [])) != 0:
            return "declaration-only module emitted residuals"
        return None
    if kind not in {"residual_record", "residual_violation"}:
        return f"assertion kind {kind!r} has no canonical structured-case comparator"
    if observed.get("status") != "observed":
        return f"expected residual observation, got {observed.get('status')}"
    expected = contract.get("expected_observation")
    tolerance = contract.get("tolerance")
    if not isinstance(expected, dict) or set(expected) != set(EXPECTED_RESIDUAL_FIELDS):
        return "expected_observation must bind name, value, role, scale, and diagnostic_key"
    if not _finite_tree(expected) or not _finite_number(tolerance) or float(tolerance) < 0:
        return "expected observation and tolerance must be finite, with nonnegative tolerance"
    matches = [item for item in observed.get("observations", []) if item.get("name") == expected.get("name")]
    if len(matches) != 1:
        return "expected residual name is not uniquely present"
    actual = matches[0]
    for field in ("role", "diagnostic_key"):
        if actual.get(field) != expected.get(field):
            return f"observed {field} differs"
    for field in ("value", "scale"):
        if not _finite_number(expected.get(field)) or not _finite_number(actual.get(field)):
            return f"observed {field} is non-finite"
        if abs(float(actual[field]) - float(expected[field])) > float(tolerance):
            return f"observed {field} differs beyond tolerance"
    if float(actual["scale"]) <= 0:
        return "observed scale is not positive"
    return None


def _test_contract_evidence(
    execution_source: str,
    module_type: str,
    expected_outcome: Any,
) -> list[tuple[str, str]]:
    try:
        tree = ast.parse(execution_source)
    except SyntaxError:
        return [("test_assertion_graph_unresolved", "test/helper source cannot be parsed")]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    call_names = {_call_name(node.func) for node in calls}
    literal_strings = {
        str(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    registered_spec_selection = (
        module_type in literal_strings
        and bool(call_names & {"one_module", "SystemSpec", "model_validate"})
        and "ResidualBuilder" in call_names
    )
    module_constructor = any(
        _call_name(node.func) == module_type
        or (
            any(isinstance(argument, ast.Name) and argument.id == "module_type" for argument in node.args)
            and _call_name(node.func) not in {"approx", "raises", "param"}
        )
        for node in calls
    ) or registered_spec_selection
    residual_evaluation = bool(
        call_names
        & {
            "residuals",
            "record_for",
            "diagnostic_residual_records",
            "solver_residual_records",
            "evaluate",
        }
    )
    assertions = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    local_fake = any(
        isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == module_type
        for node in ast.walk(tree)
    )
    meaningful_assertions = [
        node
        for node in assertions
        if not (
            isinstance(node.test, ast.Constant)
            and bool(node.test.value) is True
        )
    ]
    raises = any(_call_name(node.func) == "raises" for node in calls)
    findings: list[tuple[str, str]] = []
    if local_fake:
        findings.append(("test_uses_same_named_local_fake", "test graph defines a same-named local fake instead of selecting the registered module"))
    if assertions and not meaningful_assertions:
        findings.append(("test_assertion_unconditional", "test assertions are unconditional and observe no behavioral result"))
    if not module_constructor:
        findings.append(("test_module_not_exercised", "test graph never constructs/selects the bound module"))
    if not residual_evaluation:
        findings.append(("test_behavior_not_exercised", "test graph never evaluates residual/audit behavior"))
    if not meaningful_assertions and not raises:
        findings.append(("test_assertion_graph_missing", "test graph contains no behavioral assertion or protected exception assertion"))
    kind = expected_outcome.get("kind") if isinstance(expected_outcome, dict) else None
    if kind == "raises" and not raises:
        findings.append(("test_expected_outcome_unbound", "raises outcome is not bound to pytest.raises in the assertion graph"))
    if kind in {"residual_record", "residual_violation"} and not meaningful_assertions:
        findings.append(("test_expected_outcome_unbound", "residual outcome is not bound to an assertion graph"))
    return findings


def _review_instantiation(
    root: Path,
    binding: Any,
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
) -> None:
    dimension = "behavioral_test"
    disposition = _binding_disposition(binding)
    if disposition != "bound":
        reason = binding.get("reason") if isinstance(binding, dict) else None
        if disposition == "missing" and _nonempty_string(reason):
            _add(findings, dimension, "instantiation_missing", f"{module_type}: instantiating example is missing: {reason}")
        else:
            _add(findings, dimension, "instantiation_disposition_invalid", f"{module_type}: instantiation must be bound or explicitly missing")
        return
    path = _review_bound_file(root, binding, module_type, "instantiation", findings, dimension)
    if path is None:
        return
    if binding.get("kind") not in {"yaml_component", "json_component", "python_constructor"}:
        _add(findings, dimension, "instantiation_kind_invalid", f"{module_type}: instantiation.kind is not current")
        return
    component_id = binding.get("component_id")
    parameters = binding.get("parameters")
    if not _nonempty_string(component_id) or not isinstance(parameters, dict):
        _add(findings, dimension, "instantiation_payload_invalid", f"{module_type}: instantiation requires component_id and parameters")
    if binding.get("kind") in {"yaml_component", "json_component"}:
        payload = _load_structured_file(path)
        components = _components_from_payload(payload)
        matches = [
            item
            for item in components
            if item.get("type") == module_type and item.get("id") == component_id
        ]
        if not matches:
            _add(findings, dimension, "instantiation_module_missing", f"{module_type}: selected example does not instantiate the exact module/component")
        elif isinstance(parameters, dict) and matches[0].get("parameters", {}) != parameters:
            _add(findings, dimension, "instantiation_parameters_mismatch", f"{module_type}: instantiation parameters do not match the selected component")
    else:
        selector = binding.get("selector")
        selected = _python_function(path, selector) if isinstance(selector, str) else None
        if selected is None or f"{module_type}(" not in selected["source"]:
            _add(findings, dimension, "instantiation_module_missing", f"{module_type}: selected Python example does not instantiate the exact module")


def _review_independent_oracle(
    root: Path,
    record: dict[str, Any],
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    dimension = "independent_oracle"
    bindings = record.get("bindings")
    if not isinstance(bindings, dict):
        _add(findings, dimension, "bindings_missing", f"{module_type}: bindings must be a mapping")
        return {"status": "not_run", "producer_identity": ORACLE_RUNNER_IDENTITY, "reason": "bindings missing"}
    implementation = bindings.get("implementation") if isinstance(bindings.get("implementation"), dict) else {}
    implementation_path = implementation.get("path")
    resources = bindings.get("resources")
    if not isinstance(resources, list) or not resources:
        _add(findings, dimension, "resources_missing", f"{module_type}: bindings.resources must be a non-empty typed list")
    else:
        for index, resource in enumerate(resources):
            label = f"{module_type}: bindings.resources[{index}]"
            if not isinstance(resource, dict):
                _add(findings, dimension, "resource_invalid", f"{label} must be a mapping")
                continue
            disposition = resource.get("disposition")
            if disposition == "bound":
                if resource.get("kind") in {None, "implementation", "source_code"}:
                    _add(findings, dimension, "resource_kind_not_independent", f"{label}.kind must name a typed physical/project/data resource")
                if not _nonempty_string(resource.get("identity")):
                    _add(findings, dimension, "resource_identity_missing", f"{label}.identity must be explicit")
                path = _review_bound_file(root, resource, module_type, f"resources[{index}]", findings, dimension)
                if path is not None and resource.get("path") == implementation_path:
                    _add(findings, dimension, "implementation_used_as_resource", f"{label} reuses the implementation as its own semantic resource")
            elif disposition == "not_applicable":
                kind = resource.get("kind")
                reason = resource.get("reason")
                applicability_kind = resource.get("applicability_kind")
                if not _nonempty_string(kind) or not _nonempty_string(reason):
                    _add(findings, dimension, "resource_not_applicable_unbounded", f"{label} not_applicable requires kind and reason")
                if applicability_kind != "analytic_relation_has_no_external_asset":
                    _add(
                        findings,
                        dimension,
                        "resource_not_applicable_unbounded",
                        f"{label} requires applicability_kind=analytic_relation_has_no_external_asset",
                    )
                if kind in {"map_data", "dataset", "testbench_data", "calibration_map"}:
                    _add(
                        findings,
                        dimension,
                        "data_authority_missing",
                        f"{label}: map/data/testbench resources require a bound data authority",
                    )
            elif disposition == "missing":
                if not _nonempty_string(resource.get("reason")):
                    _add(findings, dimension, "resource_missing_reason", f"{label} missing disposition requires a reason")
                _add(findings, dimension, "independent_resource_missing", f"{label} is missing and cannot license semantics")
            else:
                _add(findings, dimension, "resource_disposition_invalid", f"{label}.disposition must be bound, not_applicable, or missing")

    oracle = bindings.get("oracle")
    disposition = _binding_disposition(oracle)
    behavior_contract = record.get("behavior_contract")
    declaration_only = (
        isinstance(behavior_contract, dict)
        and behavior_contract.get("kind") == "declaration_only"
    )
    if declaration_only:
        if (
            not isinstance(oracle, dict)
            or disposition != "not_applicable"
            or oracle.get("kind") != "declaration_only_no_equation"
            or oracle.get("applicability_kind") != "declaration_only_no_equation"
            or not _nonempty_string(oracle.get("reason"))
            or oracle.get("behavior_contract_fingerprint")
            != _canonical_hash(behavior_contract)
            or record.get("residual_definitions") != []
        ):
            _add(
                findings,
                dimension,
                "declaration_only_oracle_boundary_invalid",
                (
                    f"{module_type}: a declaration-only module must bind the exact "
                    "non-applicable equation-oracle boundary"
                ),
            )
            return {
                "status": "fail",
                "producer_identity": ORACLE_RUNNER_IDENTITY,
                "reason": "declaration-only oracle boundary is invalid",
            }
        return {
            "status": "success",
            "producer_identity": ORACLE_RUNNER_IDENTITY,
            "applicability": "not_applicable",
            "reason": oracle["reason"],
            "behavior_contract_fingerprint": oracle[
                "behavior_contract_fingerprint"
            ],
        }
    if disposition != "bound":
        reason = oracle.get("reason") if isinstance(oracle, dict) else None
        if disposition == "missing" and _nonempty_string(reason):
            _add(findings, dimension, "independent_oracle_missing", f"{module_type}: source-independent oracle is missing: {reason}")
        else:
            _add(findings, dimension, "oracle_disposition_invalid", f"{module_type}: oracle must be bound or explicitly missing")
        return {"status": "not_run", "producer_identity": ORACLE_RUNNER_IDENTITY, "reason": "oracle is not bound"}
    assert isinstance(oracle, dict)
    if oracle.get("kind") != "analytic_expression":
        _add(findings, dimension, "oracle_kind_invalid", f"{module_type}: oracle.kind must be analytic_expression")
    if oracle.get("independent_from_implementation") is not True:
        _add(findings, dimension, "oracle_not_independent", f"{module_type}: oracle must be explicitly independent from implementation")
    owner = oracle.get("owner")
    implementation_symbol = implementation.get("python_symbol")
    author = record.get("provenance", {}).get("author_owner") if isinstance(record.get("provenance"), dict) else None
    forbidden_owners = {implementation_symbol, record.get("primary_owner"), author}
    if not _nonempty_string(owner) or owner in forbidden_owners or str(owner).startswith("physicsguard.modules."):
        _add(findings, dimension, "self_referential_oracle", f"{module_type}: oracle owner is the implementation or semantic author rather than an independent oracle")
    authority = oracle.get("authority")
    if not isinstance(authority, dict):
        _add(findings, dimension, "oracle_authority_unverified", f"{module_type}: oracle requires a typed, fingerprinted authority")
        authority = {}
    authority_kind = authority.get("kind")
    if authority_kind not in {"project_formula", "external_standard", "executable_oracle"}:
        _add(findings, dimension, "oracle_authority_unverified", f"{module_type}: oracle authority kind is not independently verifiable")
    elif authority_kind in {"project_formula", "executable_oracle"}:
        authority_path = _review_bound_file(root, authority, module_type, "oracle.authority", findings, dimension)
        if authority_path is not None and authority.get("path") == implementation_path:
            _add(findings, dimension, "self_referential_oracle", f"{module_type}: oracle authority cannot be the implementation source")
        if authority_kind == "executable_oracle" and not _nonempty_string(authority.get("selector")):
            _add(findings, dimension, "oracle_authority_unverified", f"{module_type}: executable oracle authority requires an exact selector")
    elif not _nonempty_string(authority.get("immutable_identity")):
        _add(findings, dimension, "oracle_authority_unverified", f"{module_type}: external standard authority requires an immutable identity")

    expressions = _mapping_list(
        oracle.get("expressions"),
        findings,
        dimension,
        "oracle_expressions_invalid",
        f"{module_type}: bindings.oracle.expressions",
        allow_empty=False,
    )
    residuals = {
        str(item.get("name")): item
        for item in record.get("residual_definitions", [])
        if isinstance(item, dict) and _nonempty_string(item.get("name"))
    }
    allowed_symbols = {
        str(item.get("name"))
        for item in [
            *(record.get("function_block", {}).get("configuration", []) if isinstance(record.get("function_block"), dict) else []),
            *(record.get("function_block", {}).get("declared_variables", []) if isinstance(record.get("function_block"), dict) else []),
            *(record.get("function_block", {}).get("external_inputs", []) if isinstance(record.get("function_block"), dict) else []),
        ]
        if isinstance(item, dict) and _nonempty_string(item.get("name"))
    }
    oracle_names: set[str] = set()
    for index, item in enumerate(expressions):
        label = f"{module_type}: bindings.oracle.expressions[{index}]"
        name = item.get("name")
        expression = item.get("expression")
        dependencies = _require_string_list(item.get("dependencies"), findings, dimension, "oracle_dependencies_invalid", f"{label}.dependencies", allow_empty=False)
        if not _nonempty_string(name) or name not in residuals:
            _add(findings, dimension, "oracle_residual_name_invalid", f"{label}.name must identify one residual exactly")
        else:
            oracle_names.add(str(name))
            residual_scale = residuals[str(name)].get("scale")
            if item.get("unit") != (residual_scale.get("unit") if isinstance(residual_scale, dict) else None):
                _add(findings, dimension, "oracle_unit_mismatch", f"{label}.unit must align with the residual scale unit")
            if _expression_signature(item.get("scale_expression")) != _expression_signature(residual_scale.get("expression") if isinstance(residual_scale, dict) else None):
                _add(findings, dimension, "oracle_scale_mismatch", f"{label}.scale_expression must align with the residual scale")
        if not _semantic_expression(expression) or _expression_signature(expression) is None:
            _add(findings, dimension, "oracle_expression_invalid", f"{label}.expression must be a parseable source-independent equation")
            continue
        lowered = str(expression).lower()
        if "residuals(" in lowered or "declare_variables(" in lowered:
            _add(findings, dimension, "self_referential_oracle", f"{label}: oracle expression calls implementation behavior")
        identifiers = _expression_identifiers(str(expression)) - EXPRESSION_BUILTINS
        if identifiers - set(dependencies):
            _add(findings, dimension, "oracle_expression_dependency_missing", f"{label}: every expression identifier must be a declared oracle dependency")
        if set(dependencies) - allowed_symbols:
            _add(findings, dimension, "oracle_dependency_unbound", f"{label}: oracle dependencies must close over record configuration/variables")
    if oracle_names != set(residuals):
        _add(findings, dimension, "oracle_residual_coverage_incomplete", f"{module_type}: oracle expressions must cover every residual exactly once")

    cases = _mapping_list(oracle.get("cases"), findings, dimension, "oracle_cases_invalid", f"{module_type}: bindings.oracle.cases", allow_empty=False)
    for index, case in enumerate(cases):
        label = f"{module_type}: bindings.oracle.cases[{index}]"
        if not _nonempty_string(case.get("case_id")) or not isinstance(case.get("inputs"), dict) or not isinstance(case.get("expected"), dict):
            _add(findings, dimension, "oracle_case_incomplete", f"{label} requires case_id, inputs, and expected residual values")
            continue
        expected = case["expected"]
        tolerance = case.get("tolerance")
        if (
            set(expected) != set(residuals)
            or not all(_finite_number(value) for value in expected.values())
            or not _finite_number(tolerance)
            or float(tolerance) < 0
            or not _finite_tree(case.get("inputs"))
        ):
            _add(findings, dimension, "oracle_case_expected_invalid", f"{label}.expected must give a finite numeric result for every residual")

    if "producer_receipt" in oracle:
        _add(
            findings,
            dimension,
            "embedded_oracle_receipt_unauthorized",
            f"{module_type}: an oracle receipt embedded by the ledger author cannot prove checker-owned execution",
        )
    stage = _execute_oracle_contract(oracle, residuals)
    if stage["status"] != "success":
        _add(
            findings,
            dimension,
            "oracle_execution_failed" if stage["status"] == "fail" else "oracle_execution_not_run",
            f"{module_type}: {stage.get('error') or stage.get('reason')}",
        )
    return stage


def _execute_oracle_contract(
    oracle: dict[str, Any],
    residuals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expressions = oracle.get("expressions")
    cases = oracle.get("cases")
    if not isinstance(expressions, list) or not expressions or not all(isinstance(item, dict) for item in expressions):
        return {"status": "not_run", "producer_identity": ORACLE_RUNNER_IDENTITY, "reason": "structured oracle expressions are missing"}
    if not isinstance(cases, list) or not cases or not all(isinstance(item, dict) for item in cases):
        return {"status": "not_run", "producer_identity": ORACLE_RUNNER_IDENTITY, "reason": "structured oracle cases are missing"}
    observations: list[dict[str, Any]] = []
    try:
        for case in cases:
            case_id = case.get("case_id")
            inputs = case.get("inputs")
            expected = case.get("expected")
            tolerance = case.get("tolerance")
            if (
                not _nonempty_string(case_id)
                or not isinstance(inputs, dict)
                or not isinstance(expected, dict)
                or not _finite_tree(inputs)
                or not _finite_tree(expected)
                or not _finite_number(tolerance)
                or float(tolerance) < 0
            ):
                raise _RestrictedExpressionError("every oracle case needs finite inputs/expected values and a finite nonnegative tolerance")
            if set(expected) != set(residuals):
                raise _RestrictedExpressionError("oracle expected values must cover every residual exactly")
            case_results: dict[str, dict[str, float]] = {}
            for expression in expressions:
                name = expression.get("name")
                dependencies = expression.get("dependencies")
                if not _nonempty_string(name) or name not in residuals:
                    raise _RestrictedExpressionError("oracle expression has an unknown residual name")
                if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
                    raise _RestrictedExpressionError("oracle dependencies must be an exact string list")
                if set(dependencies) - set(inputs):
                    raise _RestrictedExpressionError("oracle inputs do not cover the declared dependency set")
                result = _restricted_expression(expression.get("expression"), inputs)
                scale = _restricted_expression(expression.get("scale_expression"), inputs)
                if not _finite_number(result) or not _finite_number(scale) or float(scale) <= 0:
                    raise _RestrictedExpressionError("oracle result/scale must be finite and scale must be positive")
                expected_value = expected.get(name)
                if not _finite_number(expected_value):
                    raise _RestrictedExpressionError("oracle expected result must be finite")
                if abs(float(result) - float(expected_value)) > float(tolerance):
                    raise _RestrictedExpressionError(f"oracle case {case_id!r} residual {name!r} differs beyond tolerance")
                case_results[str(name)] = {
                    "result": float(result),
                    "expected": float(expected_value),
                    "scale": float(scale),
                }
            observations.append({"case_id": case_id, "residuals": case_results})
    except (_RestrictedExpressionError, TypeError, ValueError, ZeroDivisionError) as exc:
        subject = {key: value for key, value in oracle.items() if key != "producer_receipt"}
        return {
            "status": "fail",
            "producer_identity": ORACLE_RUNNER_IDENTITY,
            "input_fingerprint": _canonical_hash(subject),
            "error": str(exc),
        }
    subject = {key: value for key, value in oracle.items() if key != "producer_receipt"}
    return {
        "status": "success",
        "producer_identity": ORACLE_RUNNER_IDENTITY,
        "input_fingerprint": _canonical_hash(subject),
        "output_fingerprint": _canonical_hash(observations),
        "case_count": len(observations),
        "observations": observations,
    }


def _review_semantic_review(
    root: Path,
    record: dict[str, Any],
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
    *,
    ledger_path: Path | None = None,
    oracle_stage: dict[str, Any] | None = None,
    external_review_evidence: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dimension = "independent_review"
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        _add(findings, dimension, "provenance_missing", f"{module_type}: provenance must be a mapping")
        provenance = {}
    else:
        if not _nonempty_string(provenance.get("author_owner")):
            _add(findings, dimension, "author_owner_missing", f"{module_type}: provenance.author_owner must be non-empty")
        _require_string_list(
            provenance.get("inputs"), findings, dimension, "source_basis_missing",
            f"{module_type}: provenance.inputs", allow_empty=False,
        )
    _require_string_list(
        record.get("stale_triggers"), findings, dimension, "stale_triggers_missing",
        f"{module_type}: stale_triggers", allow_empty=False,
    )
    review = record.get("semantic_review")
    if not isinstance(review, dict):
        _add(findings, dimension, "semantic_review_missing", f"{module_type}: semantic_review must be a mapping")
        review = {}
    expected_fingerprint = _record_fingerprint(record)
    if review.get("subject_fingerprint") != expected_fingerprint:
        _add(findings, dimension, "review_subject_stale", f"{module_type}: semantic_review.subject_fingerprint must bind the exact current record")
    author = review.get("author_owner")
    if not _nonempty_string(author) or author != provenance.get("author_owner"):
        _add(findings, dimension, "review_author_owner_mismatch", f"{module_type}: semantic_review.author_owner must match provenance.author_owner")
    reviewer = review.get("reviewer_owner")
    if reviewer is not None and reviewer == author:
        _add(findings, dimension, "self_certified_review", f"{module_type}: semantic author cannot review its own record")

    request = _build_review_request(
        root,
        ledger_path,
        record,
        module_type,
        findings,
        oracle_stage or {
            "status": "not_run",
            "producer_identity": ORACLE_RUNNER_IDENTITY,
            "reason": "oracle stage was not supplied to the direct review helper",
        },
    )
    status = review.get("status")
    license_status = review.get("license")
    physical = record.get("category") == "physical_module"
    manifest_ref = review.get("review_manifest")
    if status == "pending":
        if license_status != "unlicensed":
            _add(findings, dimension, "pending_review_license_invalid", f"{module_type}: pending review must remain unlicensed")
        if record.get("physical_claim_licensed") is not False:
            _add(findings, dimension, "pending_physical_claim_promoted", f"{module_type}: pending record cannot set physical_claim_licensed=true")
        if reviewer is not None:
            _add(findings, dimension, "pending_reviewer_must_be_null", f"{module_type}: pending review cannot claim a reviewer owner")
        if isinstance(manifest_ref, dict) and any(
            manifest_ref.get(key) is not None for key in ("sha256", "result_id")
        ):
            _add(findings, dimension, "embedded_review_evidence_unauthorized", f"{module_type}: pending ledger content cannot embed terminal result identity")
        _add(findings, dimension, "independent_review_pending", f"{module_type}: independent semantic review has not completed")
        if external_review_evidence is not None:
            stage = _validate_external_review_evidence(
                request,
                external_review_evidence,
                root=root,
                author=author,
            )
            if stage["status"] == "fail":
                _add(findings, dimension, "independent_review_external_invalid", f"{module_type}: {stage.get('error')}")
            elif stage["status"] == "blocked":
                _add(findings, dimension, "independent_review_external_blocked", f"{module_type}: canonical producer completed but did not accept the review")
            else:
                _add(findings, dimension, "accepted_external_review_not_committed", f"{module_type}: external acceptance is valid but the ledger record remains pending/unlicensed")
            return request, stage
        return request, {
            "status": "not_run",
            "producer_identity": REVIEW_PRODUCER_IDENTITY,
            "request_fingerprint": request["request_fingerprint"],
            "reason": "no independent reviewer execution has completed",
        }
    if status != "accepted":
        _add(findings, dimension, "semantic_review_not_accepted", f"{module_type}: semantic_review.status must be pending or accepted")
    if license_status != "licensed":
        _add(findings, dimension, "accepted_review_unlicensed", f"{module_type}: accepted review must declare license=licensed")
    expected_claim = physical
    if record.get("physical_claim_licensed") is not expected_claim:
        _add(findings, dimension, "physical_claim_license_mismatch", f"{module_type}: physical_claim_licensed must be {str(expected_claim).lower()} after accepted review")
    if not _nonempty_string(reviewer) or reviewer == author:
        _add(findings, dimension, "self_certified_review", f"{module_type}: accepted review requires a distinct reviewer execution owner")
    if isinstance(manifest_ref, dict) and any(
        manifest_ref.get(key) is not None for key in ("sha256", "result_id")
    ):
        _add(findings, dimension, "embedded_review_evidence_unauthorized", f"{module_type}: ledger-embedded review result/receipt identity has no authority")
    if external_review_evidence is None:
        _add(findings, dimension, "independent_review_evidence_not_run", f"{module_type}: checker was not given an external terminal result and receipt")
        return request, {
            "status": "not_run",
            "producer_identity": REVIEW_PRODUCER_IDENTITY,
            "request_fingerprint": request["request_fingerprint"],
            "reason": "external result/receipt not supplied",
        }
    stage = _validate_external_review_evidence(
        request,
        external_review_evidence,
        root=root,
        author=author,
    )
    if stage["status"] == "blocked":
        _add(
            findings,
            dimension,
            "independent_review_external_blocked",
            f"{module_type}: canonical producer completed but did not accept the review",
        )
    elif stage["status"] != "success":
        _add(
            findings,
            dimension,
            "independent_review_external_invalid",
            f"{module_type}: {stage.get('error', 'external terminal review is not accepted')}",
        )
    elif reviewer != stage.get("reviewer_execution_owner"):
        _add(
            findings,
            dimension,
            "independent_review_owner_mismatch",
            f"{module_type}: accepted ledger reviewer differs from the frozen registered provider owner",
        )
    return request, stage


def _build_review_request(
    root: Path,
    ledger_path: Path | None,
    record: dict[str, Any],
    module_type: str,
    findings: dict[str, list[dict[str, str]]],
    oracle_stage: dict[str, Any],
) -> dict[str, Any]:
    dimensions: dict[str, dict[str, Any]] = {}
    for dimension_id in DIMENSION_IDS:
        if dimension_id == "independent_review":
            dimensions[dimension_id] = {
                "status": "not_run",
                "finding_count": 0,
                "findings_fingerprint": _canonical_hash([]),
            }
            continue
        dimension_findings = findings[dimension_id]
        dimensions[dimension_id] = {
            "status": "pass" if not dimension_findings else "blocked",
            "finding_count": len(dimension_findings),
            "findings_fingerprint": _canonical_hash(dimension_findings),
        }
    producer_path = root / REVIEW_PRODUCER_PATH
    body = {
        "schema": REVIEW_REQUEST_SCHEMA,
        "checker_identity": CHECKER_IDENTITY,
        "producer": {
            "identity": REVIEW_PRODUCER_IDENTITY,
            "path": REVIEW_PRODUCER_PATH,
            "sha256": _sha256(producer_path) if producer_path.is_file() else None,
        },
        "module_type": module_type,
        "record_subject": {key: value for key, value in record.items() if key != "semantic_review"},
        "record_fingerprint": _record_fingerprint(record),
        "input_fingerprints": _review_input_fingerprints(record),
        "observed_materials": _current_review_materials(root, record, ledger_path),
        "oracle_execution": oracle_stage,
        "dimensions": dimensions,
        "reviewer_provider_authority": _reviewer_provider_authority(root),
        "reviewer_requirement": {
            "provider_result_schema": REVIEWER_PROVIDER_RESULT_SCHEMA,
            "provider_receipt_schema": REVIEWER_PROVIDER_RECEIPT_SCHEMA,
            "must_be_distinct_from": [
                record.get("provenance", {}).get("author_owner")
                if isinstance(record.get("provenance"), dict)
                else None,
                REVIEW_PRODUCER_IDENTITY,
            ],
            "domain_findings_required": True,
        },
    }
    fingerprint = _canonical_hash(body)
    return {
        **body,
        "request_id": f"module-review-{module_type}-{fingerprint[:16]}",
        "request_fingerprint": fingerprint,
    }


def _current_review_materials(
    root: Path,
    record: dict[str, Any],
    ledger_path: Path | None,
) -> list[dict[str, Any]]:
    bindings = record.get("bindings") if isinstance(record.get("bindings"), dict) else {}
    tests = bindings.get("behavioral_tests") if isinstance(bindings.get("behavioral_tests"), dict) else {}
    resources = bindings.get("resources") if isinstance(bindings.get("resources"), list) else []
    candidates: list[tuple[str, Any]] = [
        ("ledger", {"path": _rel(ledger_path, root)} if ledger_path is not None else None),
        ("implementation", bindings.get("implementation")),
        ("positive_test", tests.get("positive")),
        ("counterexample", tests.get("counterexample")),
        ("instantiation", bindings.get("instantiation")),
        *[(f"resource[{index}]", item) for index, item in enumerate(resources)],
    ]
    authority = bindings.get("oracle", {}).get("authority") if isinstance(bindings.get("oracle"), dict) else None
    candidates.append(("oracle_authority", authority))
    materials: list[dict[str, Any]] = []
    for role, binding in candidates:
        if not isinstance(binding, dict) or not _nonempty_string(binding.get("path")):
            continue
        path = _repo_file(root, str(binding["path"]))
        materials.append(
            {
                "role": role,
                "path": binding["path"],
                "selector": binding.get("selector"),
                "declared_sha256": binding.get("sha256"),
                "observed_sha256": _sha256(path) if path is not None and path.is_file() else None,
            }
        )
    return materials


def _validate_external_review_evidence(
    request: dict[str, Any],
    evidence: dict[str, Any],
    *,
    root: Path = ROOT,
    author: Any,
) -> dict[str, Any]:
    result = evidence.get("result")
    receipt = evidence.get("receipt")
    if not isinstance(result, dict) or not isinstance(receipt, dict):
        return {"status": "fail", "producer_identity": REVIEW_PRODUCER_IDENTITY, "error": "external result/receipt cannot be parsed"}
    result_subject = {key: value for key, value in result.items() if key != "output_fingerprint"}
    result_fingerprint = _canonical_hash(result_subject)
    receipt_subject = {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}
    receipt_fingerprint = _canonical_hash(receipt_subject)
    errors: list[str] = []
    result_fields = {
        "schema",
        "producer_identity",
        "producer_tool",
        "module_type",
        "request_fingerprint",
        "input_fingerprints",
        "dimensions",
        "reviewer_provider_authority",
        "reviewer_provider_evidence",
        "reviewer_execution_owner",
        "reviewer_provider_execution_request_fingerprint",
        "reviewer_provider_terminal_subject_fingerprint",
        "reviewer_provider_result_fingerprint",
        "reviewer_provider_receipt_fingerprint",
        "domain_findings",
        "producer_findings",
        "replay",
        "disposition",
        "terminal_status",
        "output_fingerprint",
    }
    receipt_fields = {
        "schema",
        "producer_identity",
        "producer_tool",
        "execution_owner",
        "request_fingerprint",
        "result_fingerprint",
        "reviewer_provider_registry_fingerprint",
        "reviewer_provider_execution_request_fingerprint",
        "reviewer_provider_terminal_subject_fingerprint",
        "reviewer_provider_result_fingerprint",
        "reviewer_provider_receipt_fingerprint",
        "reviewer_execution_owner",
        "command",
        "exit_status",
        "terminal_status",
        "disposition",
        "receipt_id",
        "receipt_fingerprint",
    }
    if set(result) != result_fields or set(receipt) != receipt_fields:
        errors.append("external review result/receipt fields are not the sole current schema")
    if result.get("schema") != REVIEW_RESULT_SCHEMA or receipt.get("schema") != REVIEW_RECEIPT_SCHEMA:
        errors.append("external review schemas are not current")
    if result.get("producer_identity") != REVIEW_PRODUCER_IDENTITY or receipt.get("producer_identity") != REVIEW_PRODUCER_IDENTITY:
        errors.append("external review producer identity is not the sole registered producer")
    producer_path = root / REVIEW_PRODUCER_PATH
    producer_tool = {
        "path": REVIEW_PRODUCER_PATH,
        "sha256": _sha256(producer_path) if producer_path.is_file() else None,
    }
    if result.get("producer_tool") != producer_tool or receipt.get("producer_tool") != producer_tool:
        errors.append("external review is not bound to the current canonical producer bytes")
    if receipt.get("execution_owner") != REVIEW_PRODUCER_IDENTITY:
        errors.append("external review receipt has the wrong execution owner")
    if result.get("request_fingerprint") != request.get("request_fingerprint") or receipt.get("request_fingerprint") != request.get("request_fingerprint"):
        errors.append("external review does not bind the current frozen request")
    if result.get("module_type") != request.get("module_type"):
        errors.append("external review module identity differs")
    if result.get("input_fingerprints") != request.get("input_fingerprints") or result.get("dimensions") != request.get("dimensions"):
        errors.append("external review did not replay the exact inputs and nine dimension snapshot")
    frozen_provider_authority = request.get("reviewer_provider_authority")
    current_provider_authority = _reviewer_provider_authority(root)
    if frozen_provider_authority != current_provider_authority:
        errors.append("external review request does not bind the current closed reviewer provider registry")
    if result.get("reviewer_provider_authority") != frozen_provider_authority:
        errors.append("external review result does not bind the frozen reviewer provider authority")
    replay = result.get("replay")
    if (
        not isinstance(replay, dict)
        or replay.get("observed_materials_fingerprint")
        != _canonical_hash(request.get("observed_materials"))
        or replay.get("status") not in {"success", "fail"}
    ):
        errors.append("external review lacks exact machine replay evidence")
    disposition = result.get("disposition")
    reviewer_owner = result.get("reviewer_execution_owner")
    provider = (
        frozen_provider_authority.get("provider")
        if isinstance(frozen_provider_authority, dict)
        else None
    )
    expected_reviewer = provider.get("execution_owner") if isinstance(provider, dict) else None
    if disposition == "accepted":
        if not _nonempty_string(reviewer_owner) or reviewer_owner in {author, REVIEW_PRODUCER_IDENTITY} or reviewer_owner != expected_reviewer:
            errors.append("external review lacks the exact distinct reviewer execution owner")
    elif reviewer_owner is not None and (
        not _nonempty_string(reviewer_owner)
        or reviewer_owner in {author, REVIEW_PRODUCER_IDENTITY}
        or reviewer_owner != expected_reviewer
    ):
        errors.append("blocked external review carries an invalid reviewer execution owner")
    if not isinstance(result.get("domain_findings"), list):
        errors.append("external review lacks bound domain findings")
    provider_evidence_stage = _validate_reviewer_provider_evidence(
        request,
        result.get("reviewer_provider_evidence"),
        author=author,
    )
    if result.get("reviewer_provider_result_fingerprint") != provider_evidence_stage.get("result_fingerprint"):
        errors.append("external review result does not bind the provider result fingerprint")
    if result.get("reviewer_provider_execution_request_fingerprint") != provider_evidence_stage.get("execution_request_fingerprint"):
        errors.append("external review result does not bind the provider execution-request fingerprint")
    if result.get("reviewer_provider_terminal_subject_fingerprint") != provider_evidence_stage.get("terminal_subject_fingerprint"):
        errors.append("external review result does not bind the authenticated provider terminal subject")
    if result.get("reviewer_provider_receipt_fingerprint") != provider_evidence_stage.get("receipt_fingerprint"):
        errors.append("external review result does not bind the provider receipt fingerprint")
    registry_fingerprint = (
        frozen_provider_authority.get("registry", {}).get("fingerprint")
        if isinstance(frozen_provider_authority, dict)
        else None
    )
    if receipt.get("reviewer_provider_registry_fingerprint") != registry_fingerprint:
        errors.append("external review receipt does not bind the frozen provider registry")
    if receipt.get("reviewer_provider_execution_request_fingerprint") != provider_evidence_stage.get("execution_request_fingerprint"):
        errors.append("external review receipt does not bind the provider execution-request fingerprint")
    if receipt.get("reviewer_provider_terminal_subject_fingerprint") != provider_evidence_stage.get("terminal_subject_fingerprint"):
        errors.append("external review receipt does not bind the authenticated provider terminal subject")
    if receipt.get("reviewer_provider_result_fingerprint") != provider_evidence_stage.get("result_fingerprint"):
        errors.append("external review receipt does not bind the provider result fingerprint")
    if receipt.get("reviewer_provider_receipt_fingerprint") != provider_evidence_stage.get("receipt_fingerprint"):
        errors.append("external review receipt does not bind the provider receipt fingerprint")
    if receipt.get("reviewer_execution_owner") != reviewer_owner:
        errors.append("external review result and receipt reviewer owners differ")
    if provider_evidence_stage.get("reviewer_execution_owner") != reviewer_owner:
        errors.append("external review result and provider evidence owners differ")
    if provider_evidence_stage.get("domain_findings") != result.get("domain_findings"):
        errors.append("external review result and provider domain findings differ")
    if result.get("output_fingerprint") != result_fingerprint:
        errors.append("external review result fingerprint is invalid")
    if receipt.get("result_fingerprint") != result_fingerprint or receipt.get("receipt_fingerprint") != receipt_fingerprint:
        errors.append("external review receipt fingerprint is invalid")
    if receipt.get("exit_status") != 0 or receipt.get("terminal_status") != "success":
        errors.append("external review receipt is not terminal success")
    if (
        result.get("terminal_status") != "success"
        or disposition not in {"accepted", "blocked"}
        or receipt.get("disposition") != disposition
    ):
        errors.append("external review terminal disposition is invalid or inconsistent")
    command = receipt.get("command")
    if (
        not isinstance(command, list)
        or len(command) != 7
        or command[0] != "python"
        or command[1] != REVIEW_PRODUCER_PATH
        or command[3] != "--result"
        or command[5] != "--receipt"
        or not all(_nonempty_string(part) for part in command)
    ):
        errors.append("external review receipt does not bind the canonical producer command")
    if disposition == "accepted" and isinstance(replay, dict) and replay.get("status") != "success":
        errors.append("accepted external review did not complete machine replay")
    if disposition == "accepted" and result.get("domain_findings"):
        errors.append("accepted external review retains open domain findings")
    if disposition == "accepted":
        dimensions = request.get("dimensions")
        if not isinstance(dimensions, dict) or any(
            not isinstance(dimensions.get(identity), dict)
            or dimensions[identity].get("status") != "pass"
            for identity in DIMENSION_IDS[:-1]
        ):
            errors.append("accepted external review retains a blocked machine-decidable dimension")
        if (
            not isinstance(dimensions, dict)
            or not isinstance(dimensions.get("independent_review"), dict)
            or dimensions["independent_review"].get("status") != "not_run"
        ):
            errors.append("accepted external review request has an invalid independent-review entry state")
        if result.get("producer_findings") != []:
            errors.append("accepted external review retains producer findings")
        if not isinstance(frozen_provider_authority, dict) or frozen_provider_authority.get("status") != "ready":
            errors.append("accepted external review has no ready provider in the frozen registry")
        if provider_evidence_stage.get("status") != "success":
            provider_error = str(
                provider_evidence_stage.get("error")
                or "authenticated provider terminal evidence is unavailable"
            )
            errors.append(
                "accepted external review lacks valid terminal provider evidence: "
                f"{provider_error}"
            )
        else:
            expected_result, expected_receipt = _derive_accepted_external_review_artifacts(
                root,
                request,
                result.get("reviewer_provider_evidence"),
                provider_evidence_stage,
            )
            if result != expected_result or receipt != expected_receipt:
                errors.append("accepted external review is not the exact deterministic projection of the authenticated provider terminal subject")
    elif provider_evidence_stage.get("status") == "fail":
        errors.append(str(provider_evidence_stage.get("error") or "blocked external review carries invalid provider evidence"))
    return {
        "status": "fail" if errors else "success" if disposition == "accepted" else "blocked",
        "producer_identity": REVIEW_PRODUCER_IDENTITY,
        "request_fingerprint": request.get("request_fingerprint"),
        "result_fingerprint": result_fingerprint,
        "receipt_fingerprint": receipt_fingerprint,
        "reviewer_execution_owner": reviewer_owner,
        "disposition": disposition,
        "result_path": evidence.get("result_path"),
        "receipt_path": evidence.get("receipt_path"),
        "error": "; ".join(errors) if errors else None,
    }


def _validate_reviewer_provider_evidence(
    request: dict[str, Any],
    evidence: Any,
    *,
    author: Any,
) -> dict[str, Any]:
    authority = request.get("reviewer_provider_authority")
    provider = authority.get("provider") if isinstance(authority, dict) else None
    if evidence is None:
        return {
            "status": "blocked",
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "error": "reviewer provider evidence was not produced",
        }
    if not isinstance(provider, dict):
        return {
            "status": "fail",
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "error": "reviewer provider evidence exists without a ready frozen provider",
        }
    if not isinstance(evidence, dict) or not isinstance(evidence.get("result"), dict) or not isinstance(evidence.get("receipt"), dict):
        return {
            "status": "fail",
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "error": "reviewer provider result/receipt cannot be parsed",
        }
    result = evidence["result"]
    receipt = evidence["receipt"]
    result_subject = {key: value for key, value in result.items() if key != "output_fingerprint"}
    result_fingerprint = _canonical_hash(result_subject)
    receipt_subject = {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}
    receipt_fingerprint = _canonical_hash(receipt_subject)
    errors: list[str] = []
    result_fields = {
        "schema",
        "provider_id",
        "execution_owner",
        "provider_tool",
        "registry_fingerprint",
        "execution_request_fingerprint",
        "request_fingerprint",
        "domain_findings",
        "disposition",
        "terminal_status",
        "output_fingerprint",
    }
    receipt_fields = {
        "schema",
        "provider_id",
        "execution_owner",
        "provider_tool",
        "registry_fingerprint",
        "execution_request_fingerprint",
        "request_fingerprint",
        "result_fingerprint",
        "execution_request",
        "command",
        "exit_status",
        "terminal_status",
        "disposition",
        "receipt_id",
        "terminal_attestation",
        "receipt_fingerprint",
    }
    if set(result) != result_fields or set(receipt) != receipt_fields:
        errors.append("reviewer provider result/receipt fields are not the sole current schema")
    if result.get("schema") != REVIEWER_PROVIDER_RESULT_SCHEMA or receipt.get("schema") != REVIEWER_PROVIDER_RECEIPT_SCHEMA:
        errors.append("reviewer provider schemas are not current")
    expected_tool = {"path": provider.get("tool_path"), "sha256": provider.get("tool_sha256")}
    if result.get("provider_tool") != expected_tool or receipt.get("provider_tool") != expected_tool:
        errors.append("reviewer provider evidence is not bound to the registered tool")
    if result.get("provider_id") != provider.get("provider_id") or receipt.get("provider_id") != provider.get("provider_id"):
        errors.append("reviewer provider identity differs from the frozen registry")
    expected_owner = provider.get("execution_owner")
    owner = result.get("execution_owner")
    if owner != expected_owner or receipt.get("execution_owner") != expected_owner or owner in {author, REVIEW_PRODUCER_IDENTITY}:
        errors.append("reviewer provider execution owner is not the exact independent registered owner")
    registry_fingerprint = authority.get("registry", {}).get("fingerprint") if isinstance(authority, dict) else None
    if result.get("registry_fingerprint") != registry_fingerprint or receipt.get("registry_fingerprint") != registry_fingerprint:
        errors.append("reviewer provider evidence does not bind the frozen registry")
    if result.get("request_fingerprint") != request.get("request_fingerprint") or receipt.get("request_fingerprint") != request.get("request_fingerprint"):
        errors.append("reviewer provider evidence does not bind the frozen review request")
    execution_request = receipt.get("execution_request")
    execution_body = (
        {
            key: value
            for key, value in execution_request.items()
            if key != "execution_request_fingerprint"
        }
        if isinstance(execution_request, dict)
        else None
    )
    execution_fingerprint = (
        execution_request.get("execution_request_fingerprint")
        if isinstance(execution_request, dict)
        else None
    )
    provider_command = (
        execution_request.get("provider_command")
        if isinstance(execution_request, dict)
        else None
    )
    producer_command = (
        execution_request.get("producer_command")
        if isinstance(execution_request, dict)
        else None
    )
    if (
        not isinstance(execution_body, dict)
        or not _sha256_value(execution_fingerprint)
        or _canonical_hash(execution_body) != execution_fingerprint
        or execution_request.get("schema") != REVIEWER_PROVIDER_EXECUTION_REQUEST_SCHEMA
        or execution_request.get("review_request") != request
        or execution_request.get("provider_authority") != authority
        or result.get("execution_request_fingerprint") != execution_fingerprint
        or receipt.get("execution_request_fingerprint") != execution_fingerprint
    ):
        errors.append("reviewer provider execution-request fingerprint is invalid or inconsistent")
    findings = result.get("domain_findings")
    if not isinstance(findings, list):
        findings = []
        errors.append("reviewer provider result lacks an explicit domain_findings list")
    disposition = result.get("disposition")
    if disposition not in {"accepted", "blocked"} or receipt.get("disposition") != disposition:
        errors.append("reviewer provider disposition is invalid or inconsistent")
    if result.get("terminal_status") != "success" or receipt.get("terminal_status") != "success" or receipt.get("exit_status") != 0:
        errors.append("reviewer provider receipt is not terminal success with zero exit")
    if result.get("output_fingerprint") != result_fingerprint:
        errors.append("reviewer provider result fingerprint is invalid")
    if receipt.get("result_fingerprint") != result_fingerprint or receipt.get("receipt_fingerprint") != receipt_fingerprint:
        errors.append("reviewer provider receipt fingerprint is invalid")
    command = receipt.get("command")
    command_prefix = provider.get("command")
    if (
        not isinstance(command, list)
        or not isinstance(command_prefix, list)
        or command != provider_command
        or command[: len(command_prefix)] != command_prefix
        or len(command) != len(command_prefix) + 5
        or command[len(command_prefix) + 1] != "--result"
        or command[len(command_prefix) + 3] != "--receipt"
        or not all(_nonempty_string(part) for part in command)
    ):
        errors.append("reviewer provider receipt does not bind the registered execution command")
    receipt_body = {
        key: value
        for key, value in receipt.items()
        if key not in {"terminal_attestation", "receipt_fingerprint"}
    }
    terminal_subject = {
        "schema": REVIEWER_PROVIDER_TERMINAL_SUBJECT_SCHEMA,
        "execution_request": execution_request,
        "result": result,
        "receipt": receipt_body,
    }
    if not _verify_provider_attestation(
        terminal_subject,
        receipt.get("terminal_attestation"),
        provider.get("public_key"),
    ):
        errors.append("reviewer provider terminal subject signature is invalid")
    if disposition == "accepted" and findings:
        errors.append("accepted reviewer provider evidence retains domain findings")
    return {
        "status": "fail" if errors else "success" if disposition == "accepted" else "blocked",
        "result_fingerprint": result_fingerprint,
        "receipt_fingerprint": receipt_fingerprint,
        "reviewer_execution_owner": owner,
        "execution_request_fingerprint": execution_fingerprint,
        "terminal_subject_fingerprint": _canonical_hash(terminal_subject),
        "producer_command": producer_command,
        "domain_findings": findings,
        "disposition": disposition,
        "error": "; ".join(errors) if errors else None,
    }


def _derive_accepted_external_review_artifacts(
    root: Path,
    request: dict[str, Any],
    provider_evidence: Any,
    provider_stage: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    producer_path = root / REVIEW_PRODUCER_PATH
    producer_tool = {
        "path": REVIEW_PRODUCER_PATH,
        "sha256": _sha256(producer_path) if producer_path.is_file() else None,
    }
    authority = request.get("reviewer_provider_authority")
    registry_fingerprint = (
        authority.get("registry", {}).get("fingerprint")
        if isinstance(authority, dict)
        else None
    )
    result_body = {
        "schema": REVIEW_RESULT_SCHEMA,
        "producer_identity": REVIEW_PRODUCER_IDENTITY,
        "producer_tool": producer_tool,
        "module_type": request.get("module_type"),
        "request_fingerprint": request.get("request_fingerprint"),
        "input_fingerprints": request.get("input_fingerprints"),
        "dimensions": request.get("dimensions"),
        "reviewer_provider_authority": authority,
        "reviewer_provider_evidence": provider_evidence,
        "reviewer_execution_owner": provider_stage.get("reviewer_execution_owner"),
        "reviewer_provider_execution_request_fingerprint": provider_stage.get("execution_request_fingerprint"),
        "reviewer_provider_terminal_subject_fingerprint": provider_stage.get("terminal_subject_fingerprint"),
        "reviewer_provider_result_fingerprint": provider_stage.get("result_fingerprint"),
        "reviewer_provider_receipt_fingerprint": provider_stage.get("receipt_fingerprint"),
        "domain_findings": provider_stage.get("domain_findings"),
        "producer_findings": [],
        "replay": {
            "status": "success",
            "observed_materials_fingerprint": _canonical_hash(
                request.get("observed_materials")
            ),
        },
        "disposition": "accepted",
        "terminal_status": "success",
    }
    result_fingerprint = _canonical_hash(result_body)
    result = {**result_body, "output_fingerprint": result_fingerprint}
    receipt_body = {
        "schema": REVIEW_RECEIPT_SCHEMA,
        "producer_identity": REVIEW_PRODUCER_IDENTITY,
        "producer_tool": producer_tool,
        "execution_owner": REVIEW_PRODUCER_IDENTITY,
        "request_fingerprint": request.get("request_fingerprint"),
        "result_fingerprint": result_fingerprint,
        "reviewer_provider_registry_fingerprint": registry_fingerprint,
        "reviewer_provider_execution_request_fingerprint": provider_stage.get("execution_request_fingerprint"),
        "reviewer_provider_terminal_subject_fingerprint": provider_stage.get("terminal_subject_fingerprint"),
        "reviewer_provider_result_fingerprint": provider_stage.get("result_fingerprint"),
        "reviewer_provider_receipt_fingerprint": provider_stage.get("receipt_fingerprint"),
        "reviewer_execution_owner": provider_stage.get("reviewer_execution_owner"),
        "command": provider_stage.get("producer_command"),
        "exit_status": 0,
        "terminal_status": "success",
        "disposition": "accepted",
        "receipt_id": f"module-review-{str(request.get('module_type'))}-{result_fingerprint[:16]}",
    }
    receipt = {**receipt_body, "receipt_fingerprint": _canonical_hash(receipt_body)}
    return result, receipt


def _assemble_review(
    *,
    registered_types: set[str],
    records_by_type: dict[str, dict[str, Any]],
    record_results: dict[str, dict[str, Any]],
    global_findings: dict[str, list[dict[str, str]]],
    review_scope: str,
    module: str | None,
) -> dict[str, Any]:
    aggregate_results: dict[str, dict[str, Any]] = {}
    scope_type_set = (
        set(registered_types)
        if review_scope == "full"
        else {module}
        if module is not None
        else set()
    )
    physical_type_set = scope_type_set - {DUMMY_MODULE_TYPE}
    for dimension in DIMENSION_IDS:
        applicable = sorted(
            module_type
            for module_type in scope_type_set
            if not (
                records_by_type.get(module_type, {}).get("category")
                == "supporting_framework_behavior"
                and dimension in SUPPORTING_FRAMEWORK_NON_APPLICABLE_DIMENSION_IDS
            )
        )
        passed: list[str] = []
        blocked: list[str] = []
        not_applicable: list[str] = []
        for module_type in applicable:
            result = record_results.get(module_type)
            if result is not None and result["dimensions"][dimension]["status"] == "pass":
                passed.append(module_type)
            else:
                blocked.append(module_type)
        not_applicable = sorted(
            module_type
            for module_type in scope_type_set
            if module_type not in applicable
        )
        dimension_findings = list(global_findings[dimension])
        if not applicable and not dimension_findings:
            status = "not_applicable"
        else:
            status = "pass" if not dimension_findings and not blocked else "blocked"
        aggregate_results[dimension] = {
            "status": status,
            "applicable_record_count": len(applicable),
            "passed_record_count": len(passed),
            "blocked_record_count": len(blocked),
            "blocked_records": blocked,
            "not_applicable_record_count": len(not_applicable),
            "not_applicable_records": not_applicable,
            "physical_applicable_record_count": len(physical_type_set),
            "physical_passed_record_count": len(physical_type_set & set(passed)),
            "physical_blocked_record_count": len(physical_type_set & set(blocked)),
            "physical_blocked_records": sorted(physical_type_set & set(blocked)),
            "findings": dimension_findings,
        }

    inventory_pass = aggregate_results["registry_inventory"]["status"] == "pass"
    scope_semantics_pass = inventory_pass and all(
        record_results.get(module_type) is not None
        and all(
            record_results[module_type]["dimensions"][dimension]["status"] == "pass"
            for dimension in (
                SUPPORTING_FRAMEWORK_REQUIRED_DIMENSION_IDS
                if records_by_type.get(module_type, {}).get("category")
                == "supporting_framework_behavior"
                else SEMANTIC_DIMENSION_IDS
            )
        )
        and not any(
            global_findings[dimension]
            for dimension in (
                SUPPORTING_FRAMEWORK_REQUIRED_DIMENSION_IDS
                if records_by_type.get(module_type, {}).get("category")
                == "supporting_framework_behavior"
                else SEMANTIC_DIMENSION_IDS
            )
        )
        for module_type in scope_type_set
    )
    scope_physical_semantics_pass = scope_semantics_pass and all(
        records_by_type.get(module_type, {}).get("physical_claim_licensed") is True
        for module_type in physical_type_set
    )
    full_software_semantics_pass = (
        scope_semantics_pass if review_scope == "full" else None
    )
    full_physical_semantics_pass = (
        scope_physical_semantics_pass if review_scope == "full" else None
    )
    scope_licensed = scope_semantics_pass and scope_physical_semantics_pass
    status = "pass" if scope_licensed else ("blocked" if inventory_pass else "fail")
    all_findings: list[str] = []
    for dimension in DIMENSION_IDS:
        for finding in global_findings[dimension]:
            all_findings.append(f"[{dimension}:{finding['code']}] {finding['message']}")
    for module_type in sorted(record_results):
        for dimension in DIMENSION_IDS:
            for finding in record_results[module_type]["dimensions"][dimension]["findings"]:
                all_findings.append(f"[{module_type}:{dimension}:{finding['code']}] {finding['message']}")

    partition_counts = {
        "previously_grouped": 0,
        "mechanically_draftable": 0,
        "domain_judgment": 0,
        "supporting_framework_behavior": 0,
    }
    for record in records_by_type.values():
        partition = record.get("baseline_partition")
        if partition in partition_counts:
            partition_counts[partition] += 1
    return {
        "artifact_kind": "physicsguard_module_semantics_ledger_review",
        "schema": SCHEMA_ID,
        "checker_identity": CHECKER_IDENTITY,
        "review_scope": {
            "kind": review_scope,
            "module_type": module if review_scope == "module" else None,
            "global_coverage_evaluated": review_scope == "full",
            "global_coverage_licensed": (
                bool(full_software_semantics_pass and full_physical_semantics_pass)
                if review_scope == "full"
                else None
            ),
            "scope_semantic_coverage_licensed": scope_licensed,
            "claim_boundary": (
                "full scope evaluates global registry semantic coverage"
                if review_scope == "full"
                else "module scope evaluates only the named record and cannot authorize global coverage"
            ),
        },
        "status": status,
        "ok": status == "pass",
        "errors": all_findings,
        "record_results": [record_results[key] for key in sorted(record_results)],
        "aggregate_results": aggregate_results,
        "summary": {
            "registry_owner": REGISTRY_OWNER,
            "registered_type_count": len(registered_types),
            "registered_types_fingerprint": _registry_fingerprint(registered_types),
            "semantic_record_count": len(records_by_type),
            "scope_record_count": len(scope_type_set),
            "partition_counts": partition_counts,
            "physical_semantic_denominator": max(len(registered_types) - 1, 0),
            "supporting_framework_denominator": 1 if DUMMY_MODULE_TYPE in registered_types else 0,
            "registry_inventory_reconciled": inventory_pass,
            "software_registry_semantic_coverage_licensed": full_software_semantics_pass,
            "physical_semantic_coverage_licensed": full_physical_semantics_pass,
            "scope_semantic_coverage_licensed": scope_licensed,
            "first_blocked_dimension": next(
                (dimension for dimension in DIMENSION_IDS if aggregate_results[dimension]["status"] == "blocked"),
                None,
            ),
            "claim_boundary": (
                "registry inventory is structural reconciliation only; physical semantic coverage requires every "
                "FunctionBlock, equation/dependency/branch, unit, constraint/region, behavioral test, distinct "
                "counterexample, independent resource/oracle, and independent-review result for every physical member"
                if review_scope == "full"
                else "this module-scoped result does not evaluate or license whole-registry semantic coverage"
            ),
        },
    }


def _project_review(
    review: dict[str, Any],
    *,
    ledger: str,
    module: str | None = None,
    detail_limit: int = 0,
) -> dict[str, Any]:
    """Create the bounded CLI projection without creating another review path."""

    aggregate = {
        dimension: {
            "status": result["status"],
            "applicable_record_count": result["applicable_record_count"],
            "passed_record_count": result["passed_record_count"],
            "blocked_record_count": result["blocked_record_count"],
            "not_applicable_record_count": result.get("not_applicable_record_count", 0),
            "not_applicable_records": result.get("not_applicable_records", []),
            "physical_applicable_record_count": result[
                "physical_applicable_record_count"
            ],
            "physical_passed_record_count": result[
                "physical_passed_record_count"
            ],
            "physical_blocked_record_count": result[
                "physical_blocked_record_count"
            ],
            "global_finding_count": len(result["findings"]),
            "record_finding_count": sum(
                item["dimensions"][dimension]["finding_count"]
                for item in review["record_results"]
            ),
            "finding_count": len(result["findings"])
            + sum(
                item["dimensions"][dimension]["finding_count"]
                for item in review["record_results"]
            ),
        }
        for dimension, result in review["aggregate_results"].items()
    }
    global_finding_count = sum(
        result["global_finding_count"] for result in aggregate.values()
    )
    record_finding_count = sum(
        result["record_finding_count"] for result in aggregate.values()
    )
    base = {
        "artifact_kind": review["artifact_kind"],
        "schema": review["schema"],
        "checker_identity": review["checker_identity"],
        "review_scope": review["review_scope"],
        "review_ok": review["ok"],
        "review_status": review["status"],
        "projection_status": "pass",
        "ledger": ledger,
        "error_count": len(review["errors"]),
        "finding_count": global_finding_count + record_finding_count,
        "global_finding_count": global_finding_count,
        "record_finding_count": record_finding_count,
        "behavior_contract_schema": BEHAVIOR_CONTRACT_SCHEMA,
        "summary": review["summary"],
        "test_execution": review.get(
            "test_execution",
            {"requested": False, "status": "not_run", "bound_case_count": 0, "executed_case_count": 0, "error": None},
        ),
        "aggregate_results": aggregate,
    }
    if module is not None:
        selected = next(
            (item for item in review["record_results"] if item["module_type"] == module),
            None,
        )
        if selected is None:
            return {
                **base,
                "projection_status": "fail",
                "module": module,
                "projection_error": {
                    "code": "unknown_module",
                    "message": f"module {module!r} is not in the reviewed live registry",
                },
            }
        selected_projection = {
            **selected,
            "finding_count": sum(
                result["finding_count"] for result in selected["dimensions"].values()
            ),
        }
        return {**base, "module": module, "record_result": selected_projection}

    base["record_results"] = [
        {
            "module_type": item["module_type"],
            "category": item["category"],
            "physical_claim_licensed": item["physical_claim_licensed"],
            "behavior_contract_status": item["behavior_contract"]["verification"]["status"],
            "behavior_contract_fingerprint": item["behavior_contract"]["contract_fingerprint"],
            "status": (
                "pass"
                if all(
                    item["dimensions"][dimension]["status"] == "pass"
                    for dimension in (
                        SUPPORTING_FRAMEWORK_REQUIRED_DIMENSION_IDS
                        if item["category"] == "supporting_framework_behavior"
                        else DIMENSION_IDS
                    )
                )
                else "blocked"
            ),
            "finding_count": sum(
                result["finding_count"] for result in item["dimensions"].values()
            ),
            "first_blocked_dimension": next(
                (
                    dimension
                    for dimension, result in item["dimensions"].items()
                    if dimension
                    in (
                        SUPPORTING_FRAMEWORK_REQUIRED_DIMENSION_IDS
                        if item["category"] == "supporting_framework_behavior"
                        else DIMENSION_IDS
                    )
                    and result["status"] != "pass"
                ),
                None,
            ),
            "first_gap": (
                {
                    "dimension": item["first_gap"]["dimension"],
                    "code": item["first_gap"]["code"],
                }
                if item["first_gap"] is not None
                else None
            ),
        }
        for item in review["record_results"]
    ]
    if detail_limit:
        base["details"] = review["errors"][:detail_limit]
        base["details_truncated"] = len(review["errors"]) > detail_limit
    return base


def _detail_limit(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--details must be an integer from 1 through 200") from exc
    if not 1 <= parsed <= 200:
        raise argparse.ArgumentTypeError("--details must be bounded from 1 through 200")
    return parsed


def _review_inventory_authority(
    data: dict[str, Any],
    registered_types: set[str],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    authority = data.get("inventory_authority")
    if not isinstance(authority, dict):
        _add(findings, "registry_inventory", "inventory_authority_missing", "inventory_authority must be a mapping")
        return
    expected = {
        "owner": REGISTRY_OWNER,
        "live_registered_type_count": len(registered_types),
        "live_registered_types_fingerprint": _registry_fingerprint(registered_types),
        "frozen_patch_type_count": FROZEN_REGISTRY_COUNT,
        "frozen_patch_types_fingerprint": FROZEN_REGISTRY_FINGERPRINT,
    }
    for field, value in expected.items():
        if authority.get(field) != value:
            _add(findings, "registry_inventory", "inventory_authority_stale", f"inventory_authority.{field} must be {value!r}")
    if len(registered_types) != FROZEN_REGISTRY_COUNT or _registry_fingerprint(registered_types) != FROZEN_REGISTRY_FINGERPRINT:
        _add(findings, "registry_inventory", "frozen_registry_changed", "live registry membership changed during this patch")


def _review_coverage_policy(
    data: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    policy = data.get("coverage_policy")
    expected = {
        "software_registry_semantic_denominator": FROZEN_REGISTRY_COUNT,
        "physical_semantic_denominator": FROZEN_REGISTRY_COUNT - 1,
        "supporting_framework_denominator": 1,
        "dummy_excluded_from_physical_claims": True,
        "group_summaries_license_semantics": False,
    }
    if not isinstance(policy, dict):
        _add(findings, "registry_inventory", "coverage_policy_missing", "coverage_policy must be a mapping")
        return
    for field, value in expected.items():
        if policy.get(field) != value:
            _add(findings, "registry_inventory", "coverage_policy_stale", f"coverage_policy.{field} must be {value!r}")


def _review_frozen_baseline(
    data: dict[str, Any],
    expected_partitions: dict[str, set[str]],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    baseline = data.get("frozen_patch_baseline")
    partitions = baseline.get("partitions") if isinstance(baseline, dict) else None
    if not isinstance(partitions, dict):
        _add(findings, "registry_inventory", "frozen_baseline_missing", "frozen_patch_baseline.partitions must be a mapping")
        return
    if set(partitions) != set(expected_partitions):
        _add(findings, "registry_inventory", "frozen_partitions_mismatch", "frozen baseline must contain exactly four current partitions")
    for name, expected_members in expected_partitions.items():
        value = partitions.get(name)
        if not isinstance(value, dict):
            _add(findings, "registry_inventory", "frozen_partition_missing", f"frozen partition {name!r} is missing")
            continue
        members = value.get("module_types")
        if value.get("count") != len(expected_members) or not isinstance(members, list) or len(members) != len(set(members)) or set(members) != expected_members:
            _add(findings, "registry_inventory", "frozen_partition_stale", f"frozen partition {name!r} is stale")


def _review_dummy_example_baseline(
    root: Path,
    data: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    baseline = data.get("supporting_framework_baseline")
    if not isinstance(baseline, dict):
        _add(findings, "registry_inventory", "dummy_baseline_missing", "supporting_framework_baseline must be a mapping")
        return
    if baseline.get("module_type") != DUMMY_MODULE_TYPE:
        _add(findings, "registry_inventory", "dummy_baseline_identity_mismatch", f"supporting_framework_baseline.module_type must be {DUMMY_MODULE_TYPE}")
    for field in ("public_registry_required", "public_export_required"):
        if baseline.get(field) is not True:
            _add(findings, "registry_inventory", "dummy_public_contract_missing", f"supporting_framework_baseline.{field} must be true")
    bindings = baseline.get("allowed_existing_example_bindings")
    if not isinstance(bindings, list) or not bindings:
        _add(findings, "registry_inventory", "dummy_example_baseline_missing", "allowed_existing_example_bindings must be non-empty")
        return
    if baseline.get("allowed_existing_example_count") != len(bindings):
        _add(findings, "registry_inventory", "dummy_example_count_stale", "allowed_existing_example_count is stale")
    approved: set[str] = set()
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            _add(findings, "registry_inventory", "dummy_example_binding_invalid", f"dummy example binding {index} must be a mapping")
            continue
        path_value = binding.get("path")
        if not isinstance(path_value, str) or not path_value.startswith("examples/"):
            _add(findings, "registry_inventory", "dummy_example_path_invalid", f"dummy example binding {index} has an invalid path")
            continue
        path = _repo_file(root, path_value)
        if path is None or not path.is_file():
            _add(findings, "registry_inventory", "dummy_example_missing", f"dummy example does not exist: {path_value}")
            continue
        approved.add(path_value)
        if binding.get("sha256") != _sha256(path):
            _add(findings, "registry_inventory", "dummy_example_stale", f"dummy example requires review after byte changes: {path_value}")
    current: set[str] = set()
    examples_root = root / "examples"
    if examples_root.is_dir():
        for suffix in ("*.yaml", "*.json"):
            for path in examples_root.rglob(suffix):
                try:
                    if DUMMY_MODULE_TYPE in path.read_text(encoding="utf-8"):
                        current.add(path.relative_to(root).as_posix())
                except UnicodeDecodeError:
                    continue
    if current - approved:
        _add(findings, "registry_inventory", "new_dummy_examples_unreviewed", "new dummy-backed examples are not in the frozen baseline: " + ", ".join(sorted(current - approved)))
    if approved - current:
        _add(findings, "registry_inventory", "dummy_example_baseline_stale", "retired dummy examples remain in the baseline: " + ", ".join(sorted(approved - current)))


def _review_authoring_contract(
    root: Path,
    data: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    contract = data.get("authoring_contract")
    if not isinstance(contract, dict):
        _add(findings, "independent_review", "authoring_contract_missing", "authoring_contract must be a mapping")
        return
    if contract.get("review_manifest_schema") != REVIEW_MANIFEST_SCHEMA:
        _add(findings, "independent_review", "authoring_manifest_schema_invalid", f"authoring_contract.review_manifest_schema must be {REVIEW_MANIFEST_SCHEMA}")
    path_value = contract.get("review_manifest_path")
    if not _nonempty_string(path_value) or _repo_file(root, str(path_value)) is None:
        _add(findings, "independent_review", "authoring_manifest_path_invalid", "authoring_contract.review_manifest_path must be repository-relative")
    if contract.get("status") not in {"pending_external_review", "reviewed"}:
        _add(findings, "independent_review", "authoring_contract_status_invalid", "authoring_contract.status must be pending_external_review or reviewed")


def _review_dummy_record(
    record: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    if record.get("physical_claim_licensed") is not False:
        _add(findings, "registry_inventory", "dummy_physical_claim_licensed", f"{DUMMY_MODULE_TYPE}: physical_claim_licensed must be false")
    if not _nonempty_string(record.get("test_purpose")) or "framework" not in str(record.get("test_purpose", "")).lower():
        _add(findings, "registry_inventory", "dummy_test_purpose_invalid", f"{DUMMY_MODULE_TYPE}: test_purpose must state framework-only behavior")
    _require_string_list(record.get("allowed_consumers"), findings, "registry_inventory", "dummy_consumers_missing", f"{DUMMY_MODULE_TYPE}: allowed_consumers", allow_empty=False)
    prohibited = _require_string_list(record.get("prohibited_claims"), findings, "registry_inventory", "dummy_prohibited_claims_missing", f"{DUMMY_MODULE_TYPE}: prohibited_claims", allow_empty=False)
    required = {"physical_blueprint_support", "physical_validation_depth", "physical_semantic_coverage", "user_facing_physical_claim"}
    if not required <= set(prohibited):
        _add(findings, "registry_inventory", "dummy_claim_boundary_incomplete", f"{DUMMY_MODULE_TYPE}: prohibited_claims must block every physical claim surface")


def _review_dummy_public_contract(
    registered_types: set[str],
    findings: dict[str, list[dict[str, str]]],
) -> None:
    if DUMMY_MODULE_TYPE not in registered_types:
        _add(findings, "registry_inventory", "dummy_registry_export_missing", f"{DUMMY_MODULE_TYPE}: missing from default_module_registry")
    try:
        from physicsguard.modules import DummyResidualModule

        if DummyResidualModule.__name__ != DUMMY_MODULE_TYPE:
            raise AttributeError("public export identity differs")
    except Exception as exc:
        _add(findings, "registry_inventory", "dummy_public_export_missing", f"{DUMMY_MODULE_TYPE}: public export missing: {exc}")


def _runtime_contract(root: Path, record: dict[str, Any], module_type: str) -> dict[str, Any]:
    bindings = record.get("bindings") if isinstance(record.get("bindings"), dict) else {}
    registry_path = _repo_file(root, RUNTIME_PORT_REGISTRY_PATH)
    registry_fingerprint = (
        _sha256(registry_path)
        if registry_path is not None and registry_path.is_file()
        else None
    )
    key = (
        root.resolve().as_posix(),
        module_type,
        _canonical_hash(bindings.get("implementation")),
        _canonical_hash(bindings.get("instantiation")),
        registry_fingerprint,
    )
    cached = _RUNTIME_CONTRACT_CACHE.get(key)
    if cached is None:
        cached = _compute_runtime_contract(root, record, module_type)
        _RUNTIME_CONTRACT_CACHE[key] = copy.deepcopy(cached)
    return copy.deepcopy(cached)


def _compute_runtime_contract(root: Path, record: dict[str, Any], module_type: str) -> dict[str, Any]:
    bindings = record.get("bindings")
    implementation = bindings.get("implementation") if isinstance(bindings, dict) and isinstance(bindings.get("implementation"), dict) else {}
    resolved = _resolve_python_symbol(module_type, implementation.get("python_symbol"))
    if resolved.get("error"):
        return {"error": resolved["error"], "declared_variables": None}
    instantiation = bindings.get("instantiation") if isinstance(bindings, dict) else None
    if _binding_disposition(instantiation) != "bound" or not isinstance(instantiation, dict):
        return {"error": "no bound instantiation payload is available", "declared_variables": None}
    component_id = instantiation.get("component_id")
    parameters = instantiation.get("parameters")
    if not _nonempty_string(component_id) or not isinstance(parameters, dict):
        return {"error": "instantiation component_id/parameters are invalid", "declared_variables": None}
    try:
        instance = resolved["value"](component_id, parameters)
        variables = instance.declare_variables()
    except Exception as exc:
        return {"error": f"bound instantiation does not construct and declare variables: {exc}", "declared_variables": None}
    normalized = []
    for variable in variables:
        name = getattr(variable, "local_name", None) or str(getattr(variable, "name", "")).rsplit(".", 1)[-1]
        normalized.append(
            {
                "name": name,
                "unit": _canonical_unit(getattr(variable, "unit", None)),
                "lower_bound": getattr(variable, "lower_bound", None),
                "upper_bound": getattr(variable, "upper_bound", None),
                "initial_guess": getattr(variable, "initial_guess", None),
                "scale": getattr(variable, "scale", None),
                "direction": None,
            }
        )
    port_contract = _registered_runtime_port_contract(
        root,
        module_type,
        normalized,
        (
            record.get("function_block", {}).get("external_inputs", [])
            if isinstance(record.get("function_block"), dict)
            else []
        ),
    )
    port_directions = port_contract.get("directions", {})
    for item in normalized:
        item["direction"] = port_directions.get(str(item["name"]))
    residuals: list[dict[str, Any]] | None = None
    residual_error: str | None = None
    kind = instantiation.get("kind")
    path_value = instantiation.get("path")
    if kind in {"yaml_component", "json_component"} and isinstance(path_value, str):
        path = _repo_file(root, path_value)
        if path is not None and path.is_file():
            try:
                from physicsguard.core.residual import ResidualBuilder
                from physicsguard.io.yaml_loader import load_system_spec

                spec = load_system_spec(path)
                builder = ResidualBuilder(spec)
                registry = builder.build_registry()
                records = builder.diagnostic_residual_records(registry.initial_vector())
                residuals = [
                    {
                        "name": str(item.name).removeprefix(f"{component_id}."),
                        "role": item.role,
                        "diagnostic_key": item.diagnostic_key,
                    }
                    for item in records
                    if item.source == component_id
                ]
                if not residuals:
                    residual_error = "bound example produced no residual owned by the selected component"
            except Exception as exc:
                residual_error = str(exc)
    return {
        "error": None,
        "declared_variables": normalized,
        "port_contract_identity": RUNTIME_PORT_CONTRACT_IDENTITY,
        "port_contract_fingerprint": port_contract.get("contract_fingerprint"),
        "port_contract_error": port_contract.get("error"),
        "role_authority_basis": port_contract.get("role_authority_basis"),
        "direction_scope": port_contract.get("direction_scope"),
        "relation_directionality": port_contract.get("relation_directionality"),
        "direction_claim_boundary": port_contract.get("direction_claim_boundary"),
        "authority_evidence_fingerprint": port_contract.get(
            "authority_evidence_fingerprint"
        ),
        "residuals": residuals,
        "residual_error": residual_error,
    }


def _registered_runtime_port_contract(
    root: Path,
    module_type: str,
    declared_variables: list[dict[str, Any]],
    external_inputs: list[dict[str, Any]],
) -> dict[str, Any]:
    path = _repo_file(root, RUNTIME_PORT_REGISTRY_PATH)
    if path is None or not path.is_file():
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port registry is missing"}
    payload = _load_structured_file(path)
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != RUNTIME_PORT_REGISTRY_SCHEMA
        or payload.get("producer_identity") != RUNTIME_PORT_CONTRACT_IDENTITY
        or not isinstance(payload.get("modules"), list)
    ):
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port registry is invalid"}
    registry_subject = {
        key: value for key, value in payload.items() if key != "registry_fingerprint"
    }
    if payload.get("registry_fingerprint") != _canonical_hash(registry_subject):
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port registry fingerprint is stale"}
    matches = [
        item
        for item in payload["modules"]
        if isinstance(item, dict) and item.get("module_type") == module_type
    ]
    if len(matches) != 1:
        return {"directions": {}, "contract_fingerprint": None, "error": "module has no unique runtime port contract"}
    entry = matches[0]
    expected_declared = sorted(
        [
            {
                "name": item.get("name"),
                "unit": item.get("unit"),
                "lower_bound": item.get("lower_bound"),
                "upper_bound": item.get("upper_bound"),
                "initial_guess": item.get("initial_guess"),
                "scale": item.get("scale"),
            }
            for item in declared_variables
        ],
        key=lambda item: str(item["name"]),
    )
    expected_external = sorted(
        [
            {
                "name": item.get("name"),
                "unit": item.get("unit"),
                "direction": item.get("role"),
                "source_attribute": item.get("source_attribute"),
                "source_reference": item.get("source_reference"),
                **(
                    {"source_index": item.get("source_index")}
                    if item.get("source_index") is not None
                    else {}
                ),
            }
            for item in external_inputs
            if isinstance(item, dict)
        ],
        key=lambda item: str(item["name"]),
    )
    if (
        entry.get("declared_ports") != expected_declared
        or entry.get("declared_ports_fingerprint") != _canonical_hash(expected_declared)
        or entry.get("external_ports", []) != expected_external
        or entry.get("external_ports_fingerprint") != _canonical_hash(expected_external)
    ):
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port inventory does not match current live declarations"}
    if entry.get("disposition") == "unresolved":
        gap = entry.get("first_gap")
        if (
            not isinstance(gap, dict)
            or not _nonempty_string(gap.get("code"))
            or not _nonempty_string(gap.get("message"))
        ):
            return {"directions": {}, "contract_fingerprint": None, "error": "unresolved runtime port contract has no exact first gap"}
        return {
            "directions": {},
            "contract_fingerprint": None,
            "error": f"{gap['code']}: {gap['message']}",
            "first_gap": copy.deepcopy(gap),
        }
    if entry.get("disposition") != "resolved" or entry.get("first_gap") is not None:
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port contract disposition is invalid"}
    ports = entry.get("ports")
    zero_port_source_first = (
        entry.get("role_authority_basis") == "source_first_formula_role"
        and isinstance(ports, list)
        and not ports
    )
    if (
        not isinstance(ports, list)
        or (not ports and not zero_port_source_first)
        or not all(isinstance(item, dict) for item in ports)
    ):
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port contract ports are invalid"}
    directions: dict[str, str] = {}
    for item in ports:
        name = item.get("name")
        direction = item.get("direction")
        if (
            not _nonempty_string(name)
            or direction not in {"input", "output", "state_previous", "state_current", "state_next"}
            or name in directions
        ):
            return {"directions": {}, "contract_fingerprint": None, "error": "runtime port contract contains an invalid or duplicate port"}
        directions[str(name)] = str(direction)
    declared_names = {str(item["name"]) for item in expected_declared}
    external_names = {str(item["name"]) for item in expected_external}
    if set(directions) != declared_names | external_names or declared_names & external_names:
        return {"directions": {}, "contract_fingerprint": None, "error": "runtime port contract does not exactly cover current local and external ports"}
    subject = {
        "schema": RUNTIME_PORT_REGISTRY_SCHEMA,
        "producer_identity": RUNTIME_PORT_CONTRACT_IDENTITY,
        "module_type": module_type,
        "instantiation_fingerprint": entry.get("instantiation_fingerprint"),
        "declared_ports_fingerprint": entry.get("declared_ports_fingerprint"),
        "role_authority_basis": entry.get("role_authority_basis"),
        "ports": sorted(
            ({"name": name, "direction": direction} for name, direction in directions.items()),
            key=lambda item: item["name"],
        ),
    }
    if entry.get("role_authority_basis") in {
        "mechanical_draft_formula_role",
        "source_first_formula_role",
    }:
        subject["external_ports_fingerprint"] = entry.get("external_ports_fingerprint")
        subject["external_ports"] = expected_external
    authority_evidence = entry.get("authority_evidence")
    if authority_evidence is not None:
        known_bad = authority_evidence.get("known_bad") if isinstance(authority_evidence, dict) else None
        evidence_kind = (
            authority_evidence.get("kind")
            if isinstance(authority_evidence, dict)
            else None
        )
        evidence_valid = False
        if evidence_kind == "current_example_boundary_contract":
            evidence_valid = (
                _nonempty_string(authority_evidence.get("path"))
                and _nonempty_string(authority_evidence.get("sha256"))
                and _nonempty_string(authority_evidence.get("component_id"))
                and _nonempty_string(authority_evidence.get("instantiation_fingerprint"))
                and authority_evidence.get("instantiation_fingerprint")
                == entry.get("instantiation_fingerprint")
                and _nonempty_string(authority_evidence.get("subject_revision"))
                and isinstance(authority_evidence.get("boundary_variables"), list)
                and _nonempty_string(authority_evidence.get("derivation"))
                and _nonempty_string(authority_evidence.get("claim_boundary"))
                and isinstance(known_bad, dict)
                and known_bad.get("code")
                == "alternate_boundary_direction_not_reusable"
                and _nonempty_string(known_bad.get("message"))
                and entry.get("role_authority_basis")
                == "canonical_reviewed_scenario_role"
                and entry.get("direction_scope") == "exact_instantiation_scenario"
                and entry.get("relation_directionality") == "direction_neutral"
                and entry.get("direction_claim_boundary")
                == authority_evidence.get("claim_boundary")
            )
        elif evidence_kind == "project_formula_direction_contract":
            authority_path = _repo_file(root, str(authority_evidence.get("path") or ""))
            formula = (
                _load_structured_file(authority_path)
                if authority_path is not None and authority_path.is_file()
                else None
            )
            formula_inputs = formula.get("inputs") if isinstance(formula, dict) else None
            formula_outputs = formula.get("outputs") if isinstance(formula, dict) else None
            formula_input_names = (
                [str(item.get("name")) for item in formula_inputs]
                if isinstance(formula_inputs, list)
                and all(isinstance(item, dict) for item in formula_inputs)
                else []
            )
            formula_output_names = (
                [str(item.get("name")) for item in formula_outputs]
                if isinstance(formula_outputs, list)
                and all(isinstance(item, dict) for item in formula_outputs)
                else []
            )
            input_names = authority_evidence.get("input_names")
            output_names = authority_evidence.get("output_names")
            expected_revision = _canonical_hash(
                {
                    "module_type": module_type,
                    "resource_sha256": authority_evidence.get("sha256"),
                    "owner": authority_evidence.get("owner"),
                    "declared_ports_fingerprint": entry.get(
                        "declared_ports_fingerprint"
                    ),
                    "inputs": input_names,
                    "outputs": output_names,
                    "claim_boundary": authority_evidence.get("claim_boundary"),
                }
            )
            evidence_valid = (
                authority_path is not None
                and authority_path.is_file()
                and _sha256(authority_path) == authority_evidence.get("sha256")
                and isinstance(formula, dict)
                and formula.get("schema") == "physicsguard.project_formula.v1"
                and formula.get("module_type") == module_type
                and formula.get("owner") == authority_evidence.get("owner")
                and formula.get("claim_boundary")
                == authority_evidence.get("claim_boundary")
                and authority_evidence.get("schema")
                == "physicsguard.project_formula.v1"
                and authority_evidence.get("selector")
                == f"module_type: {module_type}"
                and isinstance(input_names, list)
                and isinstance(output_names, list)
                and input_names == formula_input_names
                and output_names == formula_output_names
                and set(input_names).isdisjoint(output_names)
                and set(input_names) | set(output_names) == set(directions)
                and {name for name, direction in directions.items() if direction == "input"}
                == set(input_names)
                and {name for name, direction in directions.items() if direction == "output"}
                == set(output_names)
                and authority_evidence.get("subject_revision") == expected_revision
                and _nonempty_string(authority_evidence.get("derivation"))
                and _nonempty_string(authority_evidence.get("claim_boundary"))
                and isinstance(known_bad, dict)
                and known_bad.get("code")
                == "intrinsic_formula_direction_reversal_unlicensed"
                and _nonempty_string(known_bad.get("message"))
                and entry.get("role_authority_basis")
                == "intrinsic_project_formula_contract"
                and entry.get("direction_scope") == "intrinsic_module_contract"
                and entry.get("relation_directionality") == "directed"
                and entry.get("direction_claim_boundary")
                == authority_evidence.get("claim_boundary")
            )
        elif evidence_kind in {
            "mechanical_draft_formula_role_contract",
            "source_first_formula_role_contract",
        }:
            authority_path = _repo_file(root, str(authority_evidence.get("path") or ""))
            formula = (
                _load_structured_file(authority_path)
                if authority_path is not None and authority_path.is_file()
                else None
            )
            formula_items: list[dict[str, Any]] = []
            if isinstance(formula, dict):
                for field in ("scenario_inputs", "scenario_outputs"):
                    items = formula.get(field)
                    if isinstance(items, list) and all(isinstance(item, dict) for item in items):
                        formula_items.extend(items)
                    else:
                        formula_items = []
                        break
            formula_ports = sorted(
                [
                    {
                        "name": str(item.get("name")),
                        "direction": str(
                            item.get(
                                "role",
                                "input"
                                if item in (formula.get("scenario_inputs") or [])
                                else "output",
                            )
                        ),
                    }
                    for item in formula_items
                ],
                key=lambda item: item["name"],
            ) if isinstance(formula, dict) else []
            expected_revision = _canonical_hash(
                {
                    "module_type": module_type,
                    "resource_sha256": authority_evidence.get("sha256"),
                    "owner": authority_evidence.get("owner"),
                    "declared_ports_fingerprint": entry.get("declared_ports_fingerprint"),
                    "external_ports_fingerprint": entry.get("external_ports_fingerprint"),
                    "ports": formula_ports,
                    "claim_boundary": authority_evidence.get("claim_boundary"),
                    "authoring_status": authority_evidence.get("authoring_status"),
                    **(
                        {"port_contract": authority_evidence.get("port_contract")}
                        if authority_evidence.get("port_contract") is not None
                        else {}
                    ),
                }
            )
            source_first = evidence_kind == "source_first_formula_role_contract"
            expected_authoring_status = (
                "source_first_reconstruction_pending_independent_review"
                if source_first
                else "mechanical_draft_pending_independent_review"
            )
            expected_basis = (
                "source_first_formula_role"
                if source_first
                else "mechanical_draft_formula_role"
            )
            expected_scope = (
                "exact_instantiation_source_first_reconstruction"
                if source_first
                else "exact_instantiation_mechanical_draft"
            )
            expected_known_bad = (
                "source_first_reconstruction_not_independently_reviewed"
                if source_first
                else "mechanical_draft_not_independently_reviewed"
            )
            formula_port_contract_valid = bool(formula_ports) or (
                source_first
                and isinstance(formula, dict)
                and formula.get("port_contract") == "configuration_only"
                and not directions
                and not expected_declared
                and not expected_external
            )
            evidence_valid = (
                authority_path is not None
                and authority_path.is_file()
                and _sha256(authority_path) == authority_evidence.get("sha256")
                and isinstance(formula, dict)
                and formula.get("schema") == "physicsguard.project_formula.v1"
                and formula.get("module_type") == module_type
                and formula.get("owner") == authority_evidence.get("owner")
                and formula.get("claim_boundary") == authority_evidence.get("claim_boundary")
                and formula.get("authoring_status") == expected_authoring_status
                and formula.get("separate_review_status") == "pending"
                and formula.get("physical_claim_licensed") is False
                and authority_evidence.get("schema")
                == "physicsguard.project_formula.v1"
                and authority_evidence.get("selector") == f"module_type: {module_type}"
                and authority_evidence.get("authoring_status")
                == expected_authoring_status
                and authority_evidence.get("separate_review_status") == "pending"
                and authority_evidence.get("physical_claim_licensed") is False
                and formula_port_contract_valid
                and formula_ports
                == sorted(
                    [
                        {"name": name, "direction": direction}
                        for name, direction in directions.items()
                    ],
                    key=lambda item: item["name"],
                )
                and authority_evidence.get("subject_revision") == expected_revision
                and _nonempty_string(authority_evidence.get("derivation"))
                and _nonempty_string(authority_evidence.get("claim_boundary"))
                and isinstance(known_bad, dict)
                and known_bad.get("code") == expected_known_bad
                and _nonempty_string(known_bad.get("message"))
                and entry.get("role_authority_basis") == expected_basis
                and entry.get("direction_scope") == expected_scope
                and entry.get("relation_directionality") == "direction_neutral"
                and entry.get("direction_claim_boundary")
                == authority_evidence.get("claim_boundary")
            )
        if not evidence_valid:
            return {"directions": {}, "contract_fingerprint": None, "error": "runtime port authority evidence is invalid"}
        subject["authority_evidence"] = authority_evidence
        subject["direction_scope"] = entry.get("direction_scope")
        subject["relation_directionality"] = entry.get("relation_directionality")
        subject["direction_claim_boundary"] = entry.get("direction_claim_boundary")
    return {
        "directions": directions,
        "contract_fingerprint": _canonical_hash(subject),
        "registry_fingerprint": payload.get("registry_fingerprint"),
        "role_authority_basis": entry.get("role_authority_basis"),
        "direction_scope": entry.get("direction_scope"),
        "relation_directionality": entry.get("relation_directionality"),
        "direction_claim_boundary": entry.get("direction_claim_boundary"),
        "authority_evidence_fingerprint": (
            _canonical_hash(authority_evidence)
            if isinstance(authority_evidence, dict)
            else None
        ),
        "error": None,
    }


def _registered_unit_conventions(root: Path) -> dict[str, dict[str, Any]]:
    path = _repo_file(root, UNIT_CONVENTION_REGISTRY_PATH)
    if path is None or not path.is_file():
        return {}
    payload = _load_structured_file(path)
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != UNIT_CONVENTION_REGISTRY_SCHEMA
        or not isinstance(payload.get("conventions"), list)
    ):
        return {}
    conventions: dict[str, dict[str, Any]] = {}
    for item in payload["conventions"]:
        if (
            not isinstance(item, dict)
            or item.get("schema") != UNIT_CONVENTION_SCHEMA
            or not _nonempty_string(item.get("identity"))
            or item["identity"] in conventions
        ):
            return {}
        conventions[str(item["identity"])] = item
    return conventions


def _source_residual_contract(record: dict[str, Any], module_type: str) -> dict[str, Any]:
    bindings = record.get("bindings") if isinstance(record.get("bindings"), dict) else {}
    key = (
        module_type,
        _canonical_hash(bindings.get("implementation")),
    )
    cached = _SOURCE_CONTRACT_CACHE.get(key)
    if cached is None:
        cached = _compute_source_residual_contract(record, module_type)
        _SOURCE_CONTRACT_CACHE[key] = copy.deepcopy(cached)
    return copy.deepcopy(cached)


def _compute_source_residual_contract(record: dict[str, Any], module_type: str) -> dict[str, Any]:
    bindings = record.get("bindings")
    implementation = bindings.get("implementation") if isinstance(bindings, dict) and isinstance(bindings.get("implementation"), dict) else {}
    resolved = _resolve_python_symbol(module_type, implementation.get("python_symbol"))
    if resolved.get("error"):
        return {"error": resolved["error"], "names": set(), "roles": {}, "diagnostics": {}, "conditional_expression_count": 0}
    implementation_class = resolved["value"]
    residual_function = getattr(implementation_class, "residuals", None)
    try:
        source = textwrap.dedent(inspect.getsource(residual_function))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError) as exc:
        return {"error": f"implementation source cannot be parsed: {exc}", "names": set(), "roles": {}, "diagnostics": {}, "conditional_expression_count": 0}
    residual_method = next(
        (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "residuals"),
        None,
    )
    if residual_method is None:
        return {"error": "implementation has no residuals method", "names": set(), "roles": {}, "diagnostics": {}, "conditional_expression_count": 0}
    attribute_parameters = _configuration_attribute_parameters(implementation_class)
    semantic_ir = _source_semantic_ir_for_callable(
        residual_function,
        implementation_class=implementation_class,
        attribute_parameters=attribute_parameters,
    )
    names: set[str] = set()
    roles: dict[str, str | None] = {}
    role_expressions: dict[str, str | None] = {}
    diagnostics: dict[str, str | None] = {}
    expressions: dict[str, str | None] = {}
    expression_signatures: dict[str, str | None] = {}
    scales: dict[str, str | None] = {}
    scale_signatures: dict[str, str | None] = {}
    namespace = getattr(residual_function, "__globals__", {})
    for node in ast.walk(residual_method):
        if not isinstance(node, ast.Call):
            continue
        for item in _expand_residual_call(
            node,
            namespace=namespace,
            implementation_class=implementation_class,
            attribute_parameters=attribute_parameters,
            seen=frozenset(),
        ):
            name = item.get("name")
            if not isinstance(name, str):
                continue
            names.add(name)
            roles[name] = item.get("role_literal")
            role_expressions[name] = item.get("role_expression")
            diagnostics[name] = item.get("diagnostic")
            expressions[name] = item.get("expression")
            expression_signatures[name] = item.get("expression_signature")
            scales[name] = item.get("scale")
            scale_signatures[name] = item.get("scale_signature")
    conditions = _residual_affecting_conditions(
        residual_method,
        attribute_parameters=attribute_parameters,
    )
    if not names:
        returns = [
            node
            for node in ast.walk(residual_method)
            if isinstance(node, ast.Return)
        ]
        declaration_only = (
            len(returns) == 1
            and isinstance(returns[0].value, (ast.List, ast.Tuple))
            and not returns[0].value.elts
            and not any(
                isinstance(node, ast.Call)
                and (
                    _call_name(node.func) == "ResidualRecord"
                    or (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "append"
                    )
                )
                for node in ast.walk(residual_method)
            )
        )
        return {
            "error": (
                None
                if declaration_only
                else "ResidualRecord outputs are not derivable through a known pure source helper"
            ),
            "declaration_only": declaration_only,
            "names": set(),
            "roles": {},
            "role_expressions": {},
            "diagnostics": {},
            "expressions": {},
            "expression_signatures": {},
            "scales": {},
            "scale_signatures": {},
            "conditions": conditions,
            "conditional_expression_count": len(conditions),
            "semantic_ir_fingerprint": semantic_ir.get("fingerprint"),
            "semantic_ir_errors": semantic_ir.get("errors", []),
            "semantic_ir_parts": semantic_ir.get("parts", []),
        }
    return {
        "error": None,
        "declaration_only": False,
        "names": names,
        "roles": roles,
        "role_expressions": role_expressions,
        "diagnostics": diagnostics,
        "expressions": expressions,
        "expression_signatures": expression_signatures,
        "scales": scales,
        "scale_signatures": scale_signatures,
        "conditions": conditions,
        "conditional_expression_count": len(conditions),
        "semantic_ir_fingerprint": semantic_ir.get("fingerprint"),
        "semantic_ir_errors": semantic_ir.get("errors", []),
        "semantic_ir_parts": semantic_ir.get("parts", []),
    }


def _source_semantic_ir_from_source(source: str) -> dict[str, Any]:
    """Return a position-independent semantic AST identity for audit fixtures."""

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as exc:
        return {"fingerprint": None, "errors": [f"source cannot be parsed: {exc.msg}"], "parts": []}
    normalized = _normalized_source_node(tree, {})
    part = ast.dump(normalized, include_attributes=False)
    return {
        "fingerprint": _canonical_hash({"schema": SOURCE_SEMANTIC_IR_SCHEMA, "parts": [part]}),
        "errors": [],
        "parts": [part],
    }


def _source_semantic_ir_for_callable(
    function: Any,
    *,
    implementation_class: type[Any],
    attribute_parameters: dict[str, str],
) -> dict[str, Any]:
    parts: dict[str, str] = {}
    errors: list[str] = []
    active: set[str] = set()
    visited: set[str] = set()

    def visit(current: Any) -> None:
        identity = f"{getattr(current, '__module__', '')}.{getattr(current, '__qualname__', repr(current))}"
        if identity in active:
            errors.append(f"permitted pure-helper cycle: {identity}")
            return
        if identity in visited:
            return
        visited.add(identity)
        active.add(identity)
        try:
            source = textwrap.dedent(inspect.getsource(current))
            tree = ast.parse(source)
        except (OSError, TypeError, SyntaxError) as exc:
            errors.append(f"unresolved pure helper {identity}: {exc}")
            active.remove(identity)
            return
        normalized = _normalized_source_node(tree, attribute_parameters)
        parts[identity] = ast.dump(normalized, include_attributes=False)
        namespace = getattr(current, "__globals__", {})
        for call in sorted(
            (node for node in ast.walk(tree) if isinstance(node, ast.Call)),
            key=lambda node: (getattr(node, "lineno", 0), getattr(node, "col_offset", 0)),
        ):
            target = _resolved_call_target(call, namespace, implementation_class)
            if not inspect.isfunction(target):
                continue
            target_module = getattr(target, "__module__", "")
            if target_module.startswith("physicsguard."):
                visit(target)
        active.remove(identity)

    visit(function)
    ordered_parts = [f"{identity}:{parts[identity]}" for identity in sorted(parts)]
    return {
        "fingerprint": (
            _canonical_hash({"schema": SOURCE_SEMANTIC_IR_SCHEMA, "parts": ordered_parts})
            if ordered_parts and not errors
            else None
        ),
        "errors": sorted(set(errors)),
        "parts": ordered_parts,
    }


def _configuration_attribute_parameters(implementation_class: type[Any]) -> dict[str, str]:
    """Map ``self`` attributes back to their public constructor parameter names."""

    try:
        source = textwrap.dedent(inspect.getsource(implementation_class))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return {}
    init = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "__init__"
        ),
        None,
    )
    if init is None:
        return {}
    result: dict[str, str] = {}
    for node in ast.walk(init):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        for target in targets:
            if not (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                continue
            candidates: list[str] = []
            for child in ast.walk(value):
                if isinstance(child, ast.Call) and _call_name(child.func) == "get":
                    literal = _literal_string(child.args[0] if child.args else None)
                    if literal:
                        candidates.append(literal)
            if not candidates:
                candidates = [
                    child.value
                    for child in ast.walk(value)
                    if isinstance(child, ast.Constant)
                    and isinstance(child.value, str)
                ]
            if candidates:
                exact = next((item for item in candidates if item == target.attr), None)
                result[target.attr] = exact or candidates[0]
            else:
                result[target.attr] = target.attr
    return result


class _SourceExpressionNormalizer(ast.NodeTransformer):
    def __init__(self, attribute_parameters: dict[str, str]) -> None:
        self.attribute_parameters = attribute_parameters

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "self":
                return ast.copy_location(
                    ast.Name(
                        id=self.attribute_parameters.get(node.attr, node.attr),
                        ctx=ast.Load(),
                    ),
                    node,
                )
            if node.value.id in {"math", "np", "numpy"}:
                return ast.copy_location(ast.Name(id=node.attr, ctx=ast.Load()), node)
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        if (
            isinstance(node, ast.Call)
            and _call_name(node.func) in {"float", "int"}
            and len(node.args) == 1
            and not node.keywords
        ):
            return ast.copy_location(node.args[0], node)
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        if not isinstance(node, ast.UnaryOp) or not isinstance(node.op, ast.Not):
            return node
        if isinstance(node.operand, ast.UnaryOp) and isinstance(node.operand.op, ast.Not):
            return node.operand.operand
        if isinstance(node.operand, ast.Compare) and len(node.operand.ops) == 1:
            inverse: dict[type[ast.cmpop], type[ast.cmpop]] = {
                ast.Eq: ast.NotEq,
                ast.NotEq: ast.Eq,
                ast.Lt: ast.GtE,
                ast.LtE: ast.Gt,
                ast.Gt: ast.LtE,
                ast.GtE: ast.Lt,
                ast.Is: ast.IsNot,
                ast.IsNot: ast.Is,
                ast.In: ast.NotIn,
                ast.NotIn: ast.In,
            }
            operator_type = inverse.get(type(node.operand.ops[0]))
            if operator_type is not None:
                return ast.Compare(
                    left=node.operand.left,
                    ops=[operator_type()],
                    comparators=node.operand.comparators,
                )
        return node


def _normalized_source_node(
    node: ast.AST,
    attribute_parameters: dict[str, str],
) -> ast.AST:
    normalized = _SourceExpressionNormalizer(attribute_parameters).visit(copy.deepcopy(node))
    return ast.fix_missing_locations(normalized)


def _source_expression_details(
    node: ast.AST | None,
    attribute_parameters: dict[str, str],
) -> tuple[str | None, str | None]:
    if node is None:
        return None, None
    normalized = _normalized_source_node(node, attribute_parameters)
    try:
        return ast.unparse(normalized), ast.dump(normalized, include_attributes=False)
    except (TypeError, ValueError):
        return None, None


def _expression_signature(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = ast.parse(value, mode="eval").body
    except SyntaxError:
        return None
    return _source_expression_details(parsed, {})[1]


def _substitute_ast(node: ast.AST | None, environment: dict[str, ast.AST]) -> ast.AST | None:
    if node is None:
        return None

    class _Substituter(ast.NodeTransformer):
        def visit_Name(self, current: ast.Name) -> ast.AST:  # noqa: N802
            replacement = environment.get(current.id)
            return copy.deepcopy(replacement) if replacement is not None else current

    return ast.fix_missing_locations(_Substituter().visit(copy.deepcopy(node)))


def _call_environment(call: ast.Call, function: Any) -> dict[str, ast.AST]:
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return {}
    parameters = list(signature.parameters.values())
    result: dict[str, ast.AST] = {}
    for parameter, argument in zip(parameters, call.args, strict=False):
        result[parameter.name] = argument
    for keyword in call.keywords:
        if keyword.arg:
            result[keyword.arg] = keyword.value
    for parameter in parameters:
        if parameter.name in result or parameter.default is inspect.Signature.empty:
            continue
        default = parameter.default
        if isinstance(default, (str, int, float, bool)) or default is None:
            result[parameter.name] = ast.Constant(value=default)
    return result


def _resolved_call_target(
    call: ast.Call,
    namespace: dict[str, Any],
    implementation_class: type[Any],
) -> Any:
    if isinstance(call.func, ast.Name):
        return namespace.get(call.func.id)
    if (
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "self"
    ):
        return getattr(implementation_class, call.func.attr, None)
    return None


def _expand_residual_call(
    call: ast.Call,
    *,
    namespace: dict[str, Any],
    implementation_class: type[Any],
    attribute_parameters: dict[str, str],
    seen: frozenset[str],
    environment: dict[str, ast.AST] | None = None,
) -> list[dict[str, Any]]:
    environment = environment or {}
    call = _substitute_ast(call, environment)
    assert isinstance(call, ast.Call)
    if _call_name(call.func) == "ResidualRecord":
        keywords = {item.arg: item.value for item in call.keywords if item.arg}
        name = _residual_local_name(keywords.get("name"))
        expression, expression_signature = _source_expression_details(
            keywords.get("value"), attribute_parameters
        )
        scale, scale_signature = _source_expression_details(
            keywords.get("scale"), attribute_parameters
        )
        role_expression, _ = _source_expression_details(
            keywords.get("role"), attribute_parameters
        )
        return [
            {
                "name": name,
                "expression": expression,
                "expression_signature": expression_signature,
                "scale": scale,
                "scale_signature": scale_signature,
                "role_literal": _literal_string(keywords.get("role")),
                "role_expression": role_expression,
                "diagnostic": _literal_string(keywords.get("diagnostic_key")),
            }
        ]
    target = _resolved_call_target(call, namespace, implementation_class)
    if not inspect.isfunction(target):
        return []
    module_name = getattr(target, "__module__", "")
    identity = f"{module_name}.{getattr(target, '__qualname__', repr(target))}"
    if not module_name.startswith("physicsguard.") or identity in seen:
        return []
    try:
        helper_source = textwrap.dedent(inspect.getsource(target))
        helper_tree = ast.parse(helper_source)
    except (OSError, TypeError, SyntaxError):
        return []
    helper = next(
        (
            node
            for node in helper_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        None,
    )
    if helper is None:
        return []
    helper_environment = _call_environment(call, target)
    helper_namespace = getattr(target, "__globals__", {})
    expanded: list[dict[str, Any]] = []
    for child in ast.walk(helper):
        if not isinstance(child, ast.Call):
            continue
        expanded.extend(
            _expand_residual_call(
                child,
                namespace=helper_namespace,
                implementation_class=implementation_class,
                attribute_parameters=attribute_parameters,
                seen=seen | {identity},
                environment=helper_environment,
            )
        )
    return expanded


def _assigned_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            for target in targets:
                names.update(
                    item.id
                    for item in ast.walk(target)
                    if isinstance(item, ast.Name)
                )
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if isinstance(child.func.value, ast.Name):
                names.add(child.func.value.id)
    return names


def _loaded_names(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }


def _condition_pair(
    node: ast.AST,
    attribute_parameters: dict[str, str],
) -> tuple[str | None, str | None, str | None]:
    normalized = _normalized_source_node(node, attribute_parameters)
    display, positive = _source_expression_details(normalized, {})
    negative_node = ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(normalized))
    _, negative = _source_expression_details(negative_node, {})
    return display, positive, negative


def _residual_affecting_conditions(
    residual_method: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    attribute_parameters: dict[str, str],
) -> list[dict[str, Any]]:
    assignments: dict[str, set[str]] = {}
    return_values = [node.value for node in ast.walk(residual_method) if isinstance(node, ast.Return)]
    relevant = set().union(*(_loaded_names(value) for value in return_values)) if return_values else set()
    for node in ast.walk(residual_method):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            dependencies = _loaded_names(node.value)
            for target in targets:
                for name in (
                    child.id
                    for child in ast.walk(target)
                    if isinstance(child, ast.Name)
                ):
                    assignments.setdefault(name, set()).update(dependencies)
    changed = True
    while changed:
        changed = False
        for name in tuple(relevant):
            before = len(relevant)
            relevant.update(assignments.get(name, set()))
            changed = changed or len(relevant) != before

    conditions: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None, tuple[str, ...]]] = set()
    for node in ast.walk(residual_method):
        affected: set[str] = set()
        condition_node: ast.AST | None = None
        kind: str | None = None
        if isinstance(node, ast.If):
            affected = _assigned_names(node) & relevant
            has_return = any(isinstance(child, ast.Return) for child in ast.walk(node))
            if affected or has_return:
                condition_node = node.test
                kind = "if"
        elif isinstance(node, ast.IfExp):
            for assignment in ast.walk(residual_method):
                if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
                    continue
                value = assignment.value
                if node not in list(ast.walk(value)):
                    continue
                targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
                target_names = {
                    child.id
                    for target in targets
                    for child in ast.walk(target)
                    if isinstance(child, ast.Name)
                }
                affected.update(target_names & relevant)
            if affected or any(node in list(ast.walk(value)) for value in return_values):
                condition_node = node.test
                kind = "if_expression"
        if condition_node is None or kind is None:
            continue
        display, positive, negative = _condition_pair(
            condition_node, attribute_parameters
        )
        key = (positive, negative, tuple(sorted(affected)))
        if key in seen:
            continue
        seen.add(key)
        conditions.append(
            {
                "kind": kind,
                "condition": display,
                "positive_signature": positive,
                "negative_signature": negative,
                "affected_symbols": sorted(affected),
            }
        )
    return conditions


def _review_expression_closure(
    expression: Any,
    declared_dependencies: set[str],
    allowed_symbols: set[str],
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
    code: str,
    label: str,
    *,
    implementation_projection: bool = False,
    implementation_symbols: set[str] | None = None,
) -> None:
    if not isinstance(expression, str):
        return
    identifiers = _expression_identifiers(expression)
    if implementation_projection:
        semantic_unresolved = (
            identifiers & allowed_symbols
        ) - declared_dependencies - EXPRESSION_BUILTINS
        source_unresolved = (
            identifiers
            - allowed_symbols
            - EXPRESSION_BUILTINS
            - set(implementation_symbols or ())
        )
        unresolved = semantic_unresolved | source_unresolved
    else:
        unresolved = identifiers - declared_dependencies - EXPRESSION_BUILTINS
    if unresolved:
        _add(findings, dimension, code, f"{label}: expression identifiers are not declared dependencies: {', '.join(sorted(unresolved))}")
    undeclared = declared_dependencies - allowed_symbols
    if undeclared:
        _add(findings, dimension, "undefined_equation_dependency", f"{label}: declared dependencies are undefined: {', '.join(sorted(undeclared))}")


def _source_projection_symbols(source_contract: dict[str, Any]) -> set[str]:
    """Return current-code symbols licensed only for implementation projections.

    Source-first implementation projections may retain Python runtime plumbing
    that is intentionally outside the physical FunctionBlock symbol universe.
    Every such name must still occur in the current recursive source IR.  The
    three additional names are the compiler's finite normalized operators, not
    arbitrary fallback vocabulary.
    """

    result = {"piecewise_update", "previous", "update", "total"}
    parts = source_contract.get("semantic_ir_parts")
    if not isinstance(parts, list):
        return result
    for part in parts:
        if not isinstance(part, str):
            continue
        result.update(
            re.findall(r"(?:Name\(id|arg|attr|value)='([A-Za-z_][A-Za-z0-9_]*)'", part)
        )
    return result


def _review_bound_file(
    root: Path,
    binding: dict[str, Any],
    module_type: str,
    label: str,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
) -> Path | None:
    path_value = binding.get("path")
    if not _nonempty_string(path_value):
        _add(findings, dimension, "binding_path_missing", f"{module_type}: {label}.path must be non-empty")
        return None
    path = _repo_file(root, str(path_value))
    if path is None:
        _add(findings, dimension, "binding_path_escapes_repository", f"{module_type}: {label}.path escapes the repository")
        return None
    if not path.is_file():
        _add(findings, dimension, "binding_file_missing", f"{module_type}: {label}.path does not exist: {path_value}")
        return None
    if binding.get("sha256") != _sha256(path):
        _add(findings, dimension, "binding_fingerprint_stale", f"{module_type}: {label}.sha256 is stale for {path_value}")
    selector = binding.get("selector")
    if not _nonempty_string(selector):
        _add(findings, dimension, "binding_selector_missing", f"{module_type}: {label}.selector must be non-empty")
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        if str(selector) not in text:
            _add(findings, dimension, "binding_selector_unresolved", f"{module_type}: {label}.selector is not present in {path_value}")
    return path


def _review_input_fingerprints(record: dict[str, Any]) -> dict[str, Any]:
    bindings = record.get("bindings") if isinstance(record.get("bindings"), dict) else {}
    tests = bindings.get("behavioral_tests") if isinstance(bindings.get("behavioral_tests"), dict) else {}
    resources = bindings.get("resources") if isinstance(bindings.get("resources"), list) else []
    return {
        "record": _record_fingerprint(record),
        "implementation": _binding_fingerprint(bindings.get("implementation")),
        "positive_test": _binding_fingerprint(tests.get("positive")),
        "counterexample": _binding_fingerprint(tests.get("counterexample")),
        "instantiation": _binding_fingerprint(bindings.get("instantiation")),
        "resources": [_canonical_hash(item) for item in resources],
        "oracle": _canonical_hash(bindings.get("oracle")),
    }


def _record_fingerprint(record: dict[str, Any]) -> str:
    subject = {key: value for key, value in record.items() if key != "semantic_review"}
    return _canonical_hash(subject)


def _project_behavior_contract(
    record: dict[str, Any],
    module_type: str,
    *,
    runtime: dict[str, Any],
    source_contract: dict[str, Any],
    findings: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    """Project one behavior contract from the existing semantic authorities.

    This is deliberately a derived view.  It never supplies missing state,
    effects, equations, cases, or oracle meaning, and therefore cannot become a
    second authoring path beside the ledger record and its bound authorities.
    """

    block = record.get("function_block") if isinstance(record.get("function_block"), dict) else {}
    declared = block.get("declared_variables") if isinstance(block.get("declared_variables"), list) else []
    external = block.get("external_inputs") if isinstance(block.get("external_inputs"), list) else []
    variables = [
        item
        for item in [*declared, *external]
        if isinstance(item, dict) and _nonempty_string(item.get("name"))
    ]
    state = block.get("state") if isinstance(block.get("state"), dict) else {}
    outputs = block.get("outputs") if isinstance(block.get("outputs"), dict) else {}
    bindings = record.get("bindings") if isinstance(record.get("bindings"), dict) else {}
    behavioral_tests = (
        bindings.get("behavioral_tests")
        if isinstance(bindings.get("behavioral_tests"), dict)
        else {}
    )
    oracle = bindings.get("oracle") if isinstance(bindings.get("oracle"), dict) else {}

    def variable_refs(roles: set[str]) -> list[dict[str, Any]]:
        refs = []
        for item in variables:
            role = item.get("role")
            if role not in roles:
                continue
            name = str(item["name"])
            refs.append(
                {
                    "port_id": f"physicsguard.module_behavior.{module_type}.port.{role}.{name}",
                    "name": name,
                    "role": role,
                    "unit": item.get("unit"),
                }
            )
        return sorted(refs, key=lambda item: (str(item["role"]), str(item["name"])))

    def state_refs(slot: str) -> list[dict[str, Any]]:
        names = state.get(slot) if isinstance(state.get(slot), list) else []
        refs = []
        by_name = {str(item["name"]): item for item in variables}
        for raw_name in names:
            if not _nonempty_string(raw_name):
                continue
            name = str(raw_name)
            variable = by_name.get(name, {})
            refs.append(
                {
                    "state_id": f"physicsguard.module_behavior.{module_type}.state.{slot}.{name}",
                    "name": name,
                    "slot": slot,
                    "unit": variable.get("unit"),
                }
            )
        return sorted(refs, key=lambda item: str(item["name"]))

    def statements(kind: str) -> list[dict[str, str]]:
        values = block.get(kind) if isinstance(block.get(kind), list) else []
        normalized = sorted(
            {str(value) for value in values if _nonempty_string(value)}
        )
        return [
            {
                "semantic_id": (
                    f"physicsguard.module_behavior.{module_type}.{kind}."
                    f"{_canonical_hash(value)[:16]}"
                ),
                "statement": value,
            }
            for value in normalized
        ]

    residual_names = outputs.get("residuals") if isinstance(outputs.get("residuals"), list) else []
    residual_refs = [
        {
            "output_id": f"physicsguard.module_behavior.{module_type}.residual.{name}",
            "name": str(name),
            "kind": "residual",
        }
        for name in sorted({str(value) for value in residual_names if _nonempty_string(value)})
    ]
    output_refs = [
        {
            "output_id": item["port_id"],
            "name": item["name"],
            "kind": "declared_variable",
            "unit": item.get("unit"),
        }
        for item in variable_refs({"output"})
    ]

    def case_ref(kind: str) -> dict[str, Any]:
        binding = behavioral_tests.get(kind)
        if not isinstance(binding, dict):
            return {
                "case_kind": kind,
                "disposition": "missing",
                "case_fingerprint": None,
            }
        case_contract = binding.get("case_contract")
        return {
            "case_kind": kind,
            "disposition": binding.get("disposition"),
            "pytest_nodeid": binding.get("pytest_nodeid"),
            "case_fingerprint": (
                _canonical_hash(case_contract)
                if isinstance(case_contract, dict)
                else None
            ),
        }

    oracle_authority = oracle.get("authority") if isinstance(oracle.get("authority"), dict) else None
    oracle_expressions = oracle.get("expressions") if isinstance(oracle.get("expressions"), list) else []
    oracle_cases = oracle.get("cases") if isinstance(oracle.get("cases"), list) else []
    oracle_projection = {
        "disposition": oracle.get("disposition", "missing"),
        "kind": oracle.get("kind"),
        "owner": oracle.get("owner"),
        "independent_from_implementation": oracle.get("independent_from_implementation") is True,
        "authority_fingerprint": (
            _canonical_hash(oracle_authority)
            if oracle_authority is not None
            else None
        ),
        "binding_fingerprint": _canonical_hash(oracle) if oracle else None,
        "expression_names": sorted(
            {
                str(item.get("name"))
                for item in oracle_expressions
                if isinstance(item, dict) and _nonempty_string(item.get("name"))
            }
        ),
        "case_ids": sorted(
            {
                str(item.get("case_id"))
                for item in oracle_cases
                if isinstance(item, dict) and _nonempty_string(item.get("case_id"))
            }
        ),
    }

    logical_contract = {
        "schema": BEHAVIOR_CONTRACT_SCHEMA,
        "contract_id": f"physicsguard.module_behavior.{module_type}",
        "module_type": module_type,
        "signature": "Input + PreState -> Output + PostState + Effect",
        "direction_model": {
            "role_authority_basis": runtime.get("role_authority_basis"),
            "scope": runtime.get("direction_scope"),
            "relation_directionality": runtime.get("relation_directionality"),
            "claim_boundary": runtime.get("direction_claim_boundary"),
            "authority_evidence_fingerprint": runtime.get(
                "authority_evidence_fingerprint"
            ),
        },
        "configuration": sorted(
            [
                {
                    "parameter_id": f"physicsguard.module_behavior.{module_type}.configuration.{item.get('name')}",
                    "name": item.get("name"),
                    "required": item.get("required"),
                    "default": item.get("default"),
                    "unit": item.get("unit"),
                }
                for item in block.get("configuration", [])
                if isinstance(item, dict) and _nonempty_string(item.get("name"))
            ],
            key=lambda item: str(item["name"]),
        ),
        "inputs": variable_refs({"input"}),
        "pre_state": {
            "previous": state_refs("previous"),
            "current": state_refs("current"),
            "source_declared": isinstance(block.get("state"), dict)
            and isinstance(state.get("previous"), list)
            and isinstance(state.get("current"), list),
        },
        "outputs": [*output_refs, *residual_refs],
        "post_state": {
            "next": state_refs("next"),
            "source_declared": isinstance(block.get("state"), dict)
            and isinstance(state.get("next"), list),
        },
        "effects": {
            "members": statements("effects"),
            "source_declared": isinstance(block.get("effects"), list),
        },
        "preconditions": statements("preconditions"),
        "postconditions": statements("postconditions"),
        "protected_failures": {
            "members": statements("failures"),
            "source_declared": isinstance(block.get("failures"), list),
        },
        "termination": (
            {
                "semantic_id": (
                    f"physicsguard.module_behavior.{module_type}.termination."
                    f"{_canonical_hash(str(block.get('termination')))[:16]}"
                ),
                "statement": str(block.get("termination")),
            }
            if _nonempty_string(block.get("termination"))
            else None
        ),
        "oracle": oracle_projection,
        "behavior_cases": [case_ref("positive"), case_ref("counterexample")],
        "source_fingerprints": {
            "record": _record_fingerprint(record),
            "runtime_port_contract": runtime.get("port_contract_fingerprint"),
            "source_semantic_ir": source_contract.get("semantic_ir_fingerprint"),
        },
    }
    contract_fingerprint = _canonical_hash(logical_contract)
    required_contract_dimensions = (
        SUPPORTING_FRAMEWORK_BEHAVIOR_CONTRACT_DIMENSION_IDS
        if record.get("category") == "supporting_framework_behavior"
        else BEHAVIOR_CONTRACT_DIMENSION_IDS
    )
    contract_gaps = [
        {
            "dimension": dimension,
            "code": item["code"],
            "message": item["message"],
        }
        for dimension in required_contract_dimensions
        for item in findings[dimension]
    ]
    return {
        **logical_contract,
        "contract_fingerprint": contract_fingerprint,
        "verification": {
            "status": "pass" if not contract_gaps else "blocked",
            "required_dimensions": list(required_contract_dimensions),
            "first_gap": contract_gaps[0] if contract_gaps else None,
            "gap_count": len(contract_gaps),
            "claim_boundary": (
                "derived framework-behaviour projection only; physical meaning and physical claims remain prohibited"
                if record.get("category") == "supporting_framework_behavior"
                else "derived projection only; physical meaning remains unlicensed until all required dimensions pass"
                if contract_gaps
                else "derived projection passed its machine dimensions; independent semantic licensing remains separate"
            ),
        },
    }


def _first_record_gap(
    findings: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    for dimension in DIMENSION_IDS:
        if findings[dimension]:
            first = findings[dimension][0]
            return {
                "dimension": dimension,
                "code": first["code"],
                "message": first["message"],
            }
    return None


def _binding_fingerprint(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    return _canonical_hash(value)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _b64url_decode(value: Any) -> bytes | None:
    if not _nonempty_string(value) or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in value
    ):
        return None
    try:
        return base64.urlsafe_b64decode(str(value) + "=" * (-len(str(value)) % 4))
    except (ValueError, TypeError):
        return None


def _valid_provider_public_key(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "algorithm",
        "key_id",
        "modulus_b64url",
        "exponent",
    }:
        return False
    modulus = _b64url_decode(value.get("modulus_b64url"))
    exponent = value.get("exponent")
    return (
        value.get("algorithm") == REVIEWER_PROVIDER_SIGNATURE_ALGORITHM
        and _nonempty_string(value.get("key_id"))
        and isinstance(modulus, bytes)
        and len(modulus) >= 256
        and isinstance(exponent, int)
        and not isinstance(exponent, bool)
        and exponent >= 3
        and exponent % 2 == 1
    )


def _verify_provider_attestation(
    subject: dict[str, Any],
    attestation: Any,
    public_key: Any,
) -> bool:
    if not _valid_provider_public_key(public_key):
        return False
    if not isinstance(attestation, dict) or set(attestation) != {
        "schema",
        "algorithm",
        "key_id",
        "subject_fingerprint",
        "signature_b64url",
    }:
        return False
    if (
        attestation.get("schema") != REVIEWER_PROVIDER_ATTESTATION_SCHEMA
        or attestation.get("algorithm") != public_key.get("algorithm")
        or attestation.get("key_id") != public_key.get("key_id")
        or attestation.get("subject_fingerprint") != _canonical_hash(subject)
    ):
        return False
    modulus_bytes = _b64url_decode(public_key.get("modulus_b64url"))
    signature = _b64url_decode(attestation.get("signature_b64url"))
    if modulus_bytes is None or signature is None or len(signature) != len(modulus_bytes):
        return False
    modulus = int.from_bytes(modulus_bytes, "big")
    signature_value = int.from_bytes(signature, "big")
    if signature_value >= modulus:
        return False
    digest = hashlib.sha256(
        json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).digest()
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    padding_length = len(modulus_bytes) - len(digest_info) - 3
    if padding_length < 8:
        return False
    expected = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info
    observed = pow(signature_value, int(public_key["exponent"]), modulus).to_bytes(
        len(modulus_bytes), "big"
    )
    return hmac.compare_digest(observed, expected)


def _reviewer_provider_registry_path(root: Path) -> Path:
    configured = Path(REVIEWER_PROVIDER_REGISTRY_PATH)
    return configured if configured.is_absolute() else root / configured


def _reviewer_provider_tool_path(root: Path, provider: dict[str, Any]) -> Path | None:
    value = provider.get("tool_path")
    if not _nonempty_string(value):
        return None
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _reviewer_provider_authority(root: Path) -> dict[str, Any]:
    registry_path = _reviewer_provider_registry_path(root)
    payload = _load_structured_file(registry_path)
    registry_fingerprint = (
        _canonical_hash(payload)
        if isinstance(payload, dict)
        else _sha256(registry_path)
        if registry_path.is_file()
        else None
    )
    findings: list[str] = []
    providers_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(payload, dict):
        findings.append("reviewer provider registry is missing or malformed")
    else:
        if set(payload) != {"schema", "active_provider_id", "providers"}:
            findings.append("reviewer provider registry fields are not the sole current schema")
        if payload.get("schema") != REVIEWER_PROVIDER_REGISTRY_SCHEMA:
            findings.append("reviewer provider registry schema is not current")
        providers = payload.get("providers")
        if not isinstance(providers, list):
            findings.append("reviewer provider registry providers must be a list")
            providers = []
        required_provider_fields = {
            "provider_id",
            "execution_owner",
            "tool_path",
            "tool_sha256",
            "command",
            "timeout_seconds",
            "public_key",
        }
        for index, item in enumerate(providers):
            if not isinstance(item, dict) or set(item) != required_provider_fields:
                findings.append(f"reviewer provider {index} fields are invalid")
                continue
            provider_id = item.get("provider_id")
            owner = item.get("execution_owner")
            command = item.get("command")
            timeout_seconds = item.get("timeout_seconds")
            if not _nonempty_string(provider_id) or provider_id in providers_by_id:
                findings.append(f"reviewer provider {index} has a missing or duplicate provider_id")
                continue
            if not _nonempty_string(owner) or owner == REVIEW_PRODUCER_IDENTITY:
                findings.append(f"reviewer provider {provider_id} has an invalid execution_owner")
            if not isinstance(command, list) or not command or not all(_nonempty_string(part) for part in command):
                findings.append(f"reviewer provider {provider_id} command is invalid")
            elif item.get("tool_path") not in command:
                findings.append(f"reviewer provider {provider_id} command does not execute its registered tool")
            if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= 300:
                findings.append(f"reviewer provider {provider_id} timeout_seconds is invalid")
            if not _valid_provider_public_key(item.get("public_key")):
                findings.append(f"reviewer provider {provider_id} public verification key is invalid")
            tool_path = _reviewer_provider_tool_path(root, item)
            if tool_path is None or not tool_path.is_file():
                findings.append(f"reviewer provider {provider_id} tool is missing")
            elif item.get("tool_sha256") != _sha256(tool_path):
                findings.append(f"reviewer provider {provider_id} tool fingerprint is stale")
            providers_by_id[str(provider_id)] = copy.deepcopy(item)
    active_provider_id = payload.get("active_provider_id") if isinstance(payload, dict) else None
    provider: dict[str, Any] | None = None
    status = "invalid" if findings else "no_provider"
    if active_provider_id is not None:
        if not _nonempty_string(active_provider_id) or active_provider_id not in providers_by_id:
            findings.append("active reviewer provider is not exactly registered")
            status = "invalid"
        elif not findings:
            provider = providers_by_id[str(active_provider_id)]
            status = "ready"
    return {
        "schema": REVIEWER_PROVIDER_AUTHORITY_SCHEMA,
        "registry": {
            "schema": REVIEWER_PROVIDER_REGISTRY_SCHEMA,
            "path": REVIEWER_PROVIDER_REGISTRY_PATH,
            "fingerprint": registry_fingerprint,
        },
        "status": status,
        "provider": provider,
        "findings": findings,
    }


def _registry_fingerprint(registered_types: set[str]) -> str:
    return _canonical_hash(sorted(registered_types))


def _expected_partitions(
    registered_types: set[str],
    errors: list[str],
) -> dict[str, set[str]]:
    overlap = PREVIOUSLY_GROUPED_TYPES & MECHANICALLY_DRAFTABLE_TYPES
    if overlap:
        errors.append("checker partition constants overlap: " + ", ".join(sorted(overlap)))
    partitions = {
        "previously_grouped": set(PREVIOUSLY_GROUPED_TYPES),
        "mechanically_draftable": set(MECHANICALLY_DRAFTABLE_TYPES),
        "domain_judgment": registered_types
        - PREVIOUSLY_GROUPED_TYPES
        - MECHANICALLY_DRAFTABLE_TYPES
        - {DUMMY_MODULE_TYPE},
        "supporting_framework_behavior": {DUMMY_MODULE_TYPE},
    }
    expected_counts = {
        "previously_grouped": 39,
        "mechanically_draftable": 37,
        "domain_judgment": 75,
        "supporting_framework_behavior": 1,
    }
    for name, expected in expected_counts.items():
        if len(partitions[name]) != expected:
            errors.append(f"checker partition {name} has {len(partitions[name])} members; expected {expected}")
    return partitions


def _registered_module_types(errors: list[str]) -> set[str]:
    try:
        from physicsguard.modules.registry import default_module_registry

        return set(default_module_registry().registered_types())
    except Exception as exc:
        errors.append(f"could not load PhysicsGuard module registry: {exc}")
        return set()


def _resolve_python_symbol(module_type: str, symbol: Any) -> dict[str, Any]:
    if not isinstance(symbol, str) or "." not in symbol:
        return {"value": None, "error": "implementation.python_symbol must be fully qualified"}
    module_name, _, attr_name = symbol.rpartition(".")
    if attr_name != module_type:
        return {"value": None, "error": "implementation.python_symbol must end with the module type"}
    try:
        module = importlib.import_module(module_name)
        value = getattr(module, attr_name)
    except (ImportError, AttributeError) as exc:
        return {"value": None, "error": f"implementation.python_symbol cannot be resolved: {exc}"}
    if not inspect.isclass(value):
        return {"value": None, "error": "implementation.python_symbol must resolve to a class"}
    return {"value": value, "error": None}


def _empty_findings() -> dict[str, list[dict[str, str]]]:
    return {dimension: [] for dimension in DIMENSION_IDS}


def _add(
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
    code: str,
    message: str,
) -> None:
    finding = {"code": code, "message": message}
    if finding not in findings[dimension]:
        findings[dimension].append(finding)


def _dimension_result(
    dimension: str,
    findings: list[dict[str, str]],
    *,
    applicability: str = "applicable",
    claim_boundary: str | None = None,
) -> dict[str, Any]:
    assurance = {
        "registry_inventory": "structural_inventory",
        "function_block": "author_completeness_plus_role_authority",
        "equation_dependency": "implementation_alignment",
        "unit": "author_completeness",
        "constraint_valid_region": "author_completeness",
        "behavioral_test": "executable_evidence",
        "counterexample": "executable_evidence",
        "independent_oracle": "independent_evidence",
        "independent_review": "independent_licensing",
    }[dimension]
    if applicability not in {"applicable", "not_applicable"}:
        raise ValueError("dimension applicability must be applicable or not_applicable")
    status = (
        "not_applicable"
        if applicability == "not_applicable" and not findings
        else "pass"
        if not findings
        else "blocked"
    )
    return {
        "status": status,
        "applicability": applicability,
        "assurance": assurance,
        "finding_count": len(findings),
        "findings": findings,
        "claim_boundary": claim_boundary,
    }


def _require_string_list(
    value: Any,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
    code: str,
    label: str,
    *,
    allow_empty: bool,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        _add(findings, dimension, code, f"{label} must be {'a list' if allow_empty else 'a non-empty list'}")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not _nonempty_string(item):
            _add(findings, dimension, code, f"{label}[{index}] must be a non-empty string")
        else:
            result.append(str(item))
    if len(result) != len(set(result)):
        _add(findings, dimension, code, f"{label} contains duplicate values")
    return result


def _mapping_list(
    value: Any,
    findings: dict[str, list[dict[str, str]]],
    dimension: str,
    code: str,
    label: str,
    *,
    allow_empty: bool,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not allow_empty and not value):
        _add(findings, dimension, code, f"{label} must be {'a list' if allow_empty else 'a non-empty list'}")
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            _add(findings, dimension, code, f"{label}[{index}] must be a mapping")
        else:
            result.append(item)
    return result


def _binding_disposition(binding: Any) -> str | None:
    return binding.get("disposition") if isinstance(binding, dict) else None


def _binding_identity(binding: Any) -> tuple[Any, ...] | None:
    if not isinstance(binding, dict) or binding.get("disposition") != "bound":
        return None
    case_contract = binding.get("case_contract")
    if not isinstance(case_contract, dict):
        return None
    return (
        binding.get("pytest_nodeid"),
        _canonical_hash(case_contract),
        _canonical_hash(binding.get("expected_outcome")),
    )


def _components_from_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    components = payload.get("components")
    if isinstance(components, list):
        return [item for item in components if isinstance(item, dict)]
    system = payload.get("system")
    if isinstance(system, dict) and isinstance(system.get("components"), list):
        return [item for item in system["components"] if isinstance(item, dict)]
    return []


def _python_function(path: Path, selector: str) -> dict[str, Any] | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (UnicodeDecodeError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == selector:
            segment = ast.get_source_segment(source, node) or ""
            return {"node": node, "source": segment}
    return None


def _bound_behavioral_test_paths(
    root: Path,
    records: list[Any],
) -> list[Path]:
    paths: dict[str, Path] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        bindings = record.get("bindings")
        tests = bindings.get("behavioral_tests") if isinstance(bindings, dict) else None
        if not isinstance(tests, dict):
            continue
        for role in ("positive", "counterexample"):
            binding = tests.get(role)
            if not isinstance(binding, dict) or binding.get("disposition") != "bound":
                continue
            path_value = binding.get("path")
            if not isinstance(path_value, str):
                continue
            path = _repo_file(root, path_value)
            if path is not None and path.is_file() and path.suffix == ".py":
                paths[path.resolve().as_posix()] = path
    return [paths[key] for key in sorted(paths)]


def _bound_behavioral_test_nodeids(
    records: list[Any],
    module_types: set[str] | None = None,
) -> list[str]:
    nodeids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        if module_types is not None and record.get("module_type") not in module_types:
            continue
        bindings = record.get("bindings")
        tests = bindings.get("behavioral_tests") if isinstance(bindings, dict) else None
        if not isinstance(tests, dict):
            continue
        for role in ("positive", "counterexample"):
            binding = tests.get(role)
            if isinstance(binding, dict) and binding.get("disposition") == "bound" and _nonempty_string(binding.get("pytest_nodeid")):
                nodeids.add(str(binding["pytest_nodeid"]))
    return sorted(nodeids)


def _collect_pytest_nodeids(
    root: Path,
    paths: list[Path],
    *,
    nodeids: list[str] | None = None,
) -> tuple[set[str], str | None]:
    if not paths:
        return set(), None
    relative_paths: list[str] = []
    cache_parts = [root.resolve().as_posix()]
    for path in paths:
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return set(), f"pytest collection path escapes the repository: {path}"
        relative_paths.append(relative)
        cache_parts.append(f"{relative}:{_sha256(path)}")
    collection_targets = relative_paths
    if nodeids:
        normalized_nodeids = sorted({nodeid.replace("\\", "/") for nodeid in nodeids})
        allowed_paths = set(relative_paths)
        invalid_paths = sorted(
            {
                nodeid.split("::", 1)[0]
                for nodeid in normalized_nodeids
                if "::" not in nodeid
                or nodeid.split("::", 1)[0] not in allowed_paths
            }
        )
        if invalid_paths:
            return (
                set(),
                "pytest nodeid path is not one of the bound repository test paths: "
                + ", ".join(invalid_paths),
            )
        collection_targets = normalized_nodeids
        cache_parts.extend(f"nodeid:{nodeid}" for nodeid in normalized_nodeids)
    cache_key = tuple(cache_parts)
    cached = _PYTEST_COLLECTION_CACHE.get(cache_key)
    if cached is not None:
        return cached
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
                *collection_targets,
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=55,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = (set(), f"pytest collection could not complete: {exc}")
        _PYTEST_COLLECTION_CACHE[cache_key] = result
        return result
    nodeids = {
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if "::" in line and line.strip().split("::", 1)[0].endswith(".py")
    }
    error = None
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        tail = detail[-1] if detail else f"exit {completed.returncode}"
        error = f"pytest collection failed with exit {completed.returncode}: {tail}"
    result = (nodeids, error)
    _PYTEST_COLLECTION_CACHE[cache_key] = result
    return result


def _execute_pytest_nodeids(
    root: Path,
    nodeids: list[str],
) -> tuple[set[str], str | None]:
    if not nodeids or os.environ.get("PHYSICSGUARD_LEDGER_BINDING_EXECUTION") == "1":
        return set(nodeids), None
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PHYSICSGUARD_LEDGER_BINDING_EXECUTION"] = "1"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *nodeids,
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=55,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return set(), f"bound pytest batch timed out after 55 seconds for {len(nodeids)} exact cases"
    except OSError as exc:
        return set(), f"bound pytest batch could not execute: {exc}"
    if completed.returncode != 0:
        lines = (completed.stderr or completed.stdout).strip().splitlines()
        tail = lines[-1] if lines else f"exit {completed.returncode}"
        return set(), f"bound pytest batch failed with exit {completed.returncode}: {tail}"
    return set(nodeids), None


def _execute_pytest_nodeid(root: Path, path: Path, nodeid: str) -> str | None:
    if os.environ.get("PHYSICSGUARD_LEDGER_BINDING_EXECUTION") == "1":
        return None
    cache_key = (root.resolve().as_posix(), nodeid, _sha256(path))
    if cache_key in _PYTEST_EXECUTION_CACHE:
        return _PYTEST_EXECUTION_CACHE[cache_key]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PHYSICSGUARD_LEDGER_BINDING_EXECUTION"] = "1"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                nodeid,
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=55,
            check=False,
        )
    except subprocess.TimeoutExpired:
        error = f"pytest nodeid timed out after 55 seconds: {nodeid}"
    except OSError as exc:
        error = f"pytest nodeid could not execute: {exc}"
    else:
        if completed.returncode == 0:
            error = None
        else:
            lines = (completed.stderr or completed.stdout).strip().splitlines()
            tail = lines[-1] if lines else f"exit {completed.returncode}"
            error = f"pytest nodeid failed with exit {completed.returncode}: {tail}"
    _PYTEST_EXECUTION_CACHE[cache_key] = error
    return error


def _local_test_execution_source(path: Path, selector: str) -> str:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return ""
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    methods = {
        child.name: child
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    imported: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        for alias in node.names:
            imported[alias.asname or alias.name] = (node.module, alias.name)
    pending = [selector]
    visited: set[str] = set()
    segments: list[str] = []
    while pending:
        name = pending.pop()
        if name in visited or name not in functions:
            continue
        visited.add(name)
        node = functions[name]
        segments.append(ast.get_source_segment(source, node) or "")
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in functions and child.func.id not in visited:
                    pending.append(child.func.id)
                elif child.func.id in imported:
                    module_name, imported_name = imported[child.func.id]
                    try:
                        imported_value = getattr(importlib.import_module(module_name), imported_name)
                        imported_path = Path(inspect.getsourcefile(imported_value) or "").resolve()
                        imported_path.relative_to(ROOT.resolve())
                        imported_source = textwrap.dedent(inspect.getsource(imported_value))
                    except (ImportError, AttributeError, OSError, TypeError, ValueError):
                        imported_source = ""
                    if imported_source and imported_source not in segments:
                        segments.append(imported_source)
            elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                method = methods.get(child.func.attr)
                method_key = f"<method>.{child.func.attr}"
                if method is not None and method_key not in visited:
                    visited.add(method_key)
                    segments.append(ast.get_source_segment(source, method) or "")
    return "\n".join(segments)


def _parametrize_declares_module_case(
    path: Path,
    selector: str,
    module_type: str,
    case: str,
) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return False
    constants: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = _literal_eval_with_constants(node.value, constants)
            if value is not _UNRESOLVED:
                constants[node.targets[0].id] = value
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == selector
        ),
        None,
    )
    if function is None:
        return False
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call) or _call_name(decorator.func) != "parametrize":
            continue
        if len(decorator.args) < 2:
            continue
        argnames = _literal_eval_with_constants(decorator.args[0], constants)
        values = _literal_eval_with_constants(decorator.args[1], constants)
        if isinstance(argnames, str):
            names = [item.strip() for item in argnames.split(",")]
        elif isinstance(argnames, (list, tuple)):
            names = [str(item) for item in argnames]
        else:
            continue
        if "module_type" not in names or not isinstance(values, (list, tuple)):
            continue
        module_index = names.index("module_type")
        ids_node = next((item.value for item in decorator.keywords if item.arg == "ids"), None)
        ids = _literal_eval_with_constants(ids_node, constants) if ids_node is not None else None
        for index, raw_row in enumerate(values):
            explicit_id = None
            if isinstance(raw_row, dict) and "__pytest_param__" in raw_row:
                row = tuple(raw_row["__pytest_param__"])
                explicit_id = raw_row.get("__id__")
            else:
                row = raw_row if isinstance(raw_row, (list, tuple)) else (raw_row,)
            if module_index >= len(row) or row[module_index] != module_type:
                continue
            row_case = None
            if explicit_id is not None:
                row_case = str(explicit_id)
            elif isinstance(ids, (list, tuple)) and index < len(ids):
                row_case = str(ids[index])
            elif len(row) == 1:
                row_case = str(row[0])
            else:
                row_case = "-".join(str(item) for item in row)
            if row_case == case:
                return True
    return False


class _UnresolvedLiteral:
    pass


_UNRESOLVED = _UnresolvedLiteral()


def _literal_eval_with_constants(node: ast.AST | None, constants: dict[str, Any]) -> Any:
    if node is None:
        return _UNRESOLVED
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.Call) and _call_name(node.func) == "param":
        values = [_literal_eval_with_constants(item, constants) for item in node.args]
        identifier_node = next(
            (item.value for item in node.keywords if item.arg == "id"),
            None,
        )
        identifier = _literal_eval_with_constants(identifier_node, constants)
        if any(value is _UNRESOLVED for value in values):
            return _UNRESOLVED
        return {
            "__pytest_param__": values,
            "__id__": None if identifier is _UNRESOLVED else identifier,
        }
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_literal_eval_with_constants(item, constants) for item in node.elts]
        if any(value is _UNRESOLVED for value in values):
            return _UNRESOLVED
        if isinstance(node, ast.Tuple):
            return tuple(values)
        if isinstance(node, ast.Set):
            return set(values)
        return values
    if isinstance(node, ast.Dict):
        keys = [_literal_eval_with_constants(item, constants) for item in node.keys]
        values = [_literal_eval_with_constants(item, constants) for item in node.values]
        if any(item is _UNRESOLVED for item in [*keys, *values]):
            return _UNRESOLVED
        return dict(zip(keys, values, strict=True))
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return _UNRESOLVED


def _load_structured_file(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text)
        return yaml.load(text, Loader=yaml.CSafeLoader)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        return None


def _load_yaml(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"{path}: ledger file does not exist")
        return None
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        errors.append(f"{path}: invalid YAML: {exc}")
        return None


def _repo_file(root: Path, path_value: str) -> Path | None:
    path = root / path_value
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_value(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unit_value(value: Any) -> bool:
    return _nonempty_string(value)


def _canonical_unit(value: Any) -> str:
    return "1" if value in {None, "", "dimensionless"} else str(value)


def _same_scalar(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= 1e-12 * max(1.0, abs(float(left)), abs(float(right)))
    return left == right


def _semantic_expression(value: Any) -> bool:
    return _nonempty_string(value) and not _generic_text(str(value)) and "self." not in str(value)


def _generic_text(value: str) -> bool:
    lowered = value.lower()
    return any(pattern in lowered for pattern in GENERIC_TEXT_PATTERNS)


def _expression_identifiers(expression: str) -> set[str]:
    return set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression))


def _residual_names(record: dict[str, Any]) -> set[str]:
    residuals = record.get("residual_definitions")
    if not isinstance(residuals, list):
        return set()
    return {
        str(item["name"])
        for item in residuals
        if isinstance(item, dict) and _nonempty_string(item.get("name"))
    }


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _literal_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _residual_local_name(node: ast.AST | None) -> str | None:
    literal = _literal_string(node)
    if literal:
        return literal.rsplit(".", 1)[-1]
    if isinstance(node, ast.JoinedStr):
        suffix_parts: list[str] = []
        for part in reversed(node.values):
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                suffix_parts.append(part.value)
                continue
            if (
                isinstance(part, ast.FormattedValue)
                and isinstance(part.value, ast.Constant)
                and isinstance(part.value.value, str)
            ):
                suffix_parts.append(part.value.value)
                continue
            break
        if suffix_parts:
            suffix = "".join(reversed(suffix_parts)).rsplit(".", 1)[-1]
            return suffix or None
        template_parts: list[str] = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                template_parts.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                value = part.value
                if isinstance(value, ast.Name):
                    template_parts.append("{" + value.id + "}")
                elif isinstance(value, ast.Attribute):
                    template_parts.append("{" + ast.unparse(value) + "}")
                elif isinstance(value, ast.JoinedStr):
                    nested = _residual_local_name(value)
                    if nested is None:
                        return None
                    template_parts.append(nested)
                else:
                    return None
            else:
                return None
        template = "".join(template_parts).rsplit(".", 1)[-1]
        return template or None
    return None


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if effective_argv == ["--internal-run-case"]:
        try:
            request = json.loads(sys.stdin.read())
        except json.JSONDecodeError as exc:
            print(json.dumps({"status": "runner_failure", "error": f"invalid request JSON: {exc}"}))
            return 2
        result = _run_case_request(request if isinstance(request, dict) else {})
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
        return 0 if result.get("status") in {"observed", "observed_exception"} else 2
    parser = argparse.ArgumentParser(
        description=(
            "Review the sole current PhysicsGuard per-module semantics ledger, keeping "
            "structural inventory separate from physical semantic licensing."
        )
    )
    parser.add_argument("ledger", nargs="?", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--json", action="store_true")
    projection = parser.add_mutually_exclusive_group()
    projection.add_argument(
        "--module",
        help="Show exact detailed findings for one live module type.",
    )
    projection.add_argument(
        "--details",
        type=_detail_limit,
        metavar="N",
        default=0,
        help="Include only the first N blocking findings (1-200).",
    )
    parser.add_argument(
        "--execute-bound-tests",
        action="store_true",
        help="Explicitly execute the unique exact bound pytest cases; ordinary review leaves execution not_run.",
    )
    parser.add_argument(
        "--review-result",
        type=Path,
        help="Validate one external terminal result from the sole canonical producer (requires --module and --review-receipt).",
    )
    parser.add_argument(
        "--review-receipt",
        type=Path,
        help="Validate the matching external terminal receipt (requires --module and --review-result).",
    )
    parser.add_argument(
        "--review-request-output",
        type=Path,
        help="Explicitly materialize the frozen review request for --module; ordinary review writes nothing.",
    )
    args = parser.parse_args(effective_argv)
    if (args.review_result is not None or args.review_receipt is not None or args.review_request_output is not None) and not args.module:
        parser.error("external review evidence/request materialization requires --module")
    ledger_path = args.ledger
    if not ledger_path.is_absolute():
        ledger_path = ROOT / ledger_path
    review = review_ledger(
        ROOT,
        ledger_path,
        review_scope="module" if args.module else "full",
        module=args.module,
        execute_bound_tests=args.execute_bound_tests,
        execution_modules={args.module} if args.execute_bound_tests and args.module else None,
        review_result_path=args.review_result,
        review_receipt_path=args.review_receipt,
    )
    if args.review_request_output is not None and review.get("record_results"):
        request_path = args.review_request_output
        if not request_path.is_absolute():
            request_path = ROOT / request_path
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps(
                review["record_results"][0]["review_request"],
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    output = _project_review(
        review,
        ledger=_rel(ledger_path, ROOT),
        module=args.module,
        detail_limit=args.details,
    )
    if args.json:
        indent = 2 if args.module or args.details else None
        separators = None if indent else (",", ":")
        rendered = json.dumps(
            output,
            indent=indent,
            separators=separators,
            ensure_ascii=False,
        )
        if (
            args.module is None
            and not args.details
            and len(rendered.encode("utf-8")) > DEFAULT_JSON_BYTE_LIMIT
        ):
            output = {
                "artifact_kind": review["artifact_kind"],
                "schema": review["schema"],
                "checker_identity": review["checker_identity"],
                "review_scope": review["review_scope"],
                "review_ok": review["ok"],
                "review_status": review["status"],
                "projection_status": "fail",
                "ledger": _rel(ledger_path, ROOT),
                "test_execution": review.get("test_execution"),
                "projection_error": {
                    "code": "compact_projection_budget_exceeded",
                    "message": (
                        "default JSON projection exceeded its hard byte budget; "
                        "use --module for exact affected detail"
                    ),
                },
                "byte_limit": DEFAULT_JSON_BYTE_LIMIT,
                "summary": review["summary"],
            }
            rendered = json.dumps(output, separators=(",", ":"), ensure_ascii=False)
        print(rendered)
    elif output.get("projection_error"):
        print(f"module semantic ledger projection failed: {output['projection_error']['message']}")
    elif args.module:
        record_result = output["record_result"]
        print(f"module semantic ledger detail: {args.module}")
        for dimension, result in record_result["dimensions"].items():
            print(f"- {dimension}: {result['status']} ({result['finding_count']} findings)")
            for finding in result["findings"]:
                print(f"  - [{finding['code']}] {finding['message']}")
    elif review["status"] == "pass":
        print(f"module semantic ledger review passed: {_rel(ledger_path, ROOT)}")
    else:
        print(
            "module semantic ledger review "
            f"{review['status']}: inventory={review['summary']['registry_inventory_reconciled']}, "
            f"physical_semantics={review['summary']['physical_semantic_coverage_licensed']}"
        )
        for dimension, result in output["aggregate_results"].items():
            print(
                f"- {dimension}: {result['status']} "
                f"({result['blocked_record_count']}/{result['applicable_record_count']} blocked)"
            )
        for detail in output.get("details", []):
            print(f"- {detail}")
        if output.get("details_truncated"):
            print("- additional findings omitted by the bounded --details projection")
    if output.get("projection_error"):
        return 2
    return 0 if review["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
