from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"


def _semantic_ir_cycle_a() -> int:
    return _semantic_ir_cycle_b()


def _semantic_ir_cycle_b() -> int:
    return _semantic_ir_cycle_a()


@lru_cache(maxsize=1)
def _load_checker() -> ModuleType:
    path = ROOT / "scripts" / "check_module_equation_ledger.py"
    spec = importlib.util.spec_from_file_location("check_module_equation_ledger", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _base_payload() -> dict:
    payload = yaml.load(
        LEDGER.read_text(encoding="utf-8"),
        Loader=yaml.CSafeLoader,
    )
    assert isinstance(payload, dict)
    return payload


def _payload() -> dict:
    return copy.deepcopy(_base_payload())


@lru_cache(maxsize=1)
def _full_review() -> dict:
    return _load_checker().review_ledger(ROOT, LEDGER)


@lru_cache(maxsize=1)
def _actuator_module_review() -> dict:
    return _load_checker().review_ledger(
        ROOT,
        LEDGER,
        review_scope="module",
        module="ActuatorDeadZoneModule",
    )


@lru_cache(maxsize=1)
def _collected_nodeids() -> frozenset[str]:
    checker = _load_checker()
    paths = checker._bound_behavioral_test_paths(
        ROOT, _base_payload()["module_records"]
    )
    nodeids, error = checker._collect_pytest_nodeids(ROOT, paths)
    assert error is None
    return frozenset(nodeids)


def _record(payload: dict, module_type: str) -> dict:
    return next(
        record
        for record in payload["module_records"]
        if record["module_type"] == module_type
    )


def _write(tmp_path: Path, payload: dict, name: str = "ledger.yaml") -> Path:
    path = tmp_path / name
    path.write_text(
        yaml.dump(payload, Dumper=yaml.CSafeDumper, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _review_record(checker: ModuleType, record: dict) -> dict:
    registry_errors: list[str] = []
    registered = checker._registered_module_types(registry_errors)
    assert registry_errors == []
    partitions = checker._expected_partitions(registered, registry_errors)
    assert registry_errors == []
    return checker._review_record(
        ROOT,
        record,
        expected_partitions=partitions,
        registered_types=registered,
        owners=set(),
        collected_nodeids=set(_collected_nodeids()),
        executed_nodeids=set(),
    )


def _codes(result: dict, dimension: str) -> set[str]:
    return {
        finding["code"]
        for finding in result["dimensions"][dimension]["findings"]
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _shared_residual_contract_assertions(record: dict) -> None:
    assert record["name"]
    assert isinstance(record["value"], float)
    assert record["role"]
    assert record["scale"] > 0
    assert record["diagnostic_key"]


@pytest.mark.parametrize("module_type", ["RatioModule"], ids=["RatioModule"])
def test_parameterized_helper_contract_fixture(module_type: str) -> None:
    assert module_type == "RatioModule"
    _shared_residual_contract_assertions(
        {
            "name": "ratio_relation",
            "value": 0.0,
            "role": "equation",
            "scale": 1.0,
            "diagnostic_key": "ratio_relation_mismatch",
        }
    )


@pytest.mark.parametrize(
    "module_type,scenario",
    [
        pytest.param("RatioModule", "positive", id="RatioModule-positive"),
        pytest.param("RatioModule", "violation", id="RatioModule-violation"),
    ],
)
def test_parameterized_shared_positive_counter_fixture(
    module_type: str,
    scenario: str,
) -> None:
    assert module_type == "RatioModule"
    assert scenario in {"positive", "violation"}


def test_committed_v3_ledger_reconciles_inventory_without_promoting_semantics() -> None:
    checker = _load_checker()

    review = _full_review()

    assert review["schema"] == checker.SCHEMA_ID
    assert review["status"] == "blocked"
    assert not review["ok"]
    assert review["summary"]["registry_inventory_reconciled"]
    assert not review["summary"]["software_registry_semantic_coverage_licensed"]
    assert not review["summary"]["physical_semantic_coverage_licensed"]
    assert review["aggregate_results"]["registry_inventory"]["status"] == "pass"
    assert review["aggregate_results"]["independent_review"]["status"] == "blocked"
    assert len(review["record_results"]) == 152


def test_checker_derives_all_nine_per_record_and_aggregate_dimensions() -> None:
    checker = _load_checker()

    review = _full_review()

    assert tuple(review["aggregate_results"]) == checker.DIMENSION_IDS
    for record_result in review["record_results"]:
        assert tuple(record_result["dimensions"]) == checker.DIMENSION_IDS
        for result in record_result["dimensions"].values():
            assert result["status"] in {"pass", "blocked"}
            assert result["finding_count"] == len(result["findings"])


def test_default_cli_projection_is_compact_and_omits_detailed_findings() -> None:
    checker = _load_checker()
    review = _full_review()

    projected = checker._project_review(
        review,
        ledger=".physicsguard/module_equation_ledger.yaml",
    )
    encoded = json.dumps(projected, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )

    assert len(encoded) < checker.DEFAULT_JSON_BYTE_LIMIT
    assert "errors" not in projected
    assert "findings" not in projected["aggregate_results"]["function_block"]
    assert "blocked_records" not in projected["aggregate_results"]["function_block"]
    assert projected["review_status"] == review["status"]
    assert projected["review_ok"] == review["ok"]
    assert projected["projection_status"] == "pass"
    assert projected["test_execution"]["status"] == "not_run"
    for result in projected["aggregate_results"].values():
        assert result["finding_count"] == (
            result["global_finding_count"] + result["record_finding_count"]
        )
    assert "dimensions" not in projected["record_results"][0]
    assert {
        "status",
        "finding_count",
        "first_blocked_dimension",
    } <= set(projected["record_results"][0])
    assert projected["behavior_contract_schema"] == checker.BEHAVIOR_CONTRACT_SCHEMA
    assert projected["record_results"][0]["behavior_contract_status"] in {
        "pass",
        "blocked",
    }
    assert len(
        projected["record_results"][0]["behavior_contract_fingerprint"]
    ) == 64
    assert "behavior_contract" not in projected["record_results"][0]
    assert set(projected["record_results"][0]["first_gap"]) == {
        "dimension",
        "code",
    }


def test_deep_module_projects_exact_behavior_contract_without_second_authority() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "BrakeSimpleModule"))

    result = _review_record(checker, record)
    contract = result["behavior_contract"]

    assert contract["schema"] == checker.BEHAVIOR_CONTRACT_SCHEMA
    assert contract["signature"] == (
        "Input + PreState -> Output + PostState + Effect"
    )
    assert {item["name"] for item in contract["inputs"]} == {
        "brake_force_N",
        "vehicle_speed_m_s",
    }
    assert contract["pre_state"] == {
        "previous": [],
        "current": [],
        "source_declared": True,
    }
    assert contract["post_state"] == {"next": [], "source_declared": True}
    assert {(item["name"], item["kind"]) for item in contract["outputs"]} == {
        ("brake_power_W", "declared_variable"),
        ("brake_power", "residual"),
    }
    assert contract["effects"]["source_declared"]
    assert contract["effects"]["members"]
    assert contract["protected_failures"]["source_declared"]
    assert contract["protected_failures"]["members"]
    assert contract["termination"] is not None
    assert contract["oracle"]["owner"] == (
        "physicsguard.project_formula.low_fidelity_brake_power.v1"
    )
    assert contract["oracle"]["expression_names"] == ["brake_power"]
    assert contract["oracle"]["case_ids"] == ["balanced", "under_reported_power"]
    assert contract["source_fingerprints"]["runtime_port_contract"]
    assert contract["source_fingerprints"]["source_semantic_ir"]
    assert contract["contract_fingerprint"] == checker._canonical_hash(
        {
            key: value
            for key, value in contract.items()
            if key not in {"contract_fingerprint", "verification"}
        }
    )
    assert contract["verification"]["status"] == "blocked"
    assert contract["verification"]["first_gap"]["dimension"] == (
        "behavioral_test"
    )


def test_reversible_relation_projects_scenario_roles_without_global_direction_claim() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "PressureRatioModule"))

    result = _review_record(checker, record)
    contract = result["behavior_contract"]

    assert contract["direction_model"] == {
        "role_authority_basis": "canonical_reviewed_scenario_role",
        "scope": "exact_instantiation_scenario",
        "relation_directionality": "direction_neutral",
        "claim_boundary": (
            "canonical reviewed scenario roles only; the module relation remains "
            "direction-neutral and another legal boundary set may solve it in "
            "another direction"
        ),
        "authority_evidence_fingerprint": (
            record["function_block"]["role_authority"][
                "authority_evidence_fingerprint"
            ]
        ),
    }
    assert {item["name"] for item in contract["inputs"]} == {
        "p_in_Pa",
        "p_out_Pa",
    }
    assert {
        item["name"]
        for item in contract["outputs"]
        if item["kind"] == "declared_variable"
    } == {"pressure_ratio"}


def test_behavior_contract_preserves_explicit_state_and_does_not_invent_missing_post_state() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "BrakeSimpleModule"))
    del record["function_block"]["state"]["next"]

    result = _review_record(checker, record)
    contract = result["behavior_contract"]

    assert contract["pre_state"]["source_declared"]
    assert not contract["post_state"]["source_declared"]
    assert contract["post_state"]["next"] == []
    assert contract["verification"]["status"] == "blocked"
    assert "state_slot_invalid" in _codes(result, "function_block")


def test_behavior_contract_does_not_invent_missing_protected_failures() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "BrakeSimpleModule"))
    del record["function_block"]["failures"]

    result = _review_record(checker, record)
    contract = result["behavior_contract"]

    assert contract["protected_failures"] == {
        "members": [],
        "source_declared": False,
    }
    assert contract["verification"]["status"] == "blocked"
    assert "function_block_failures_invalid" in _codes(result, "function_block")


def test_behavior_contract_cannot_pass_with_a_blocked_unit_or_validity_dimension() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "BrakeSimpleModule"))
    unit = next(
        item for item in record["symbol_units"] if item["symbol"] == "brake_power_W"
    )
    unit["unit"] = "N"

    result = _review_record(checker, record)
    contract = result["behavior_contract"]

    assert contract["verification"]["required_dimensions"] == list(
        checker.BEHAVIOR_CONTRACT_DIMENSION_IDS
    )
    assert contract["verification"]["status"] == "blocked"
    assert contract["verification"]["first_gap"]["dimension"] == "unit"
    assert "symbol_unit_mismatch" in _codes(result, "unit")


def test_behavior_contract_identity_is_deterministic_for_identical_sources() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "BrakeSimpleModule"))

    first = _review_record(checker, copy.deepcopy(record))["behavior_contract"]
    second = _review_record(checker, copy.deepcopy(record))["behavior_contract"]

    assert first == second
    assert first["contract_fingerprint"] == second["contract_fingerprint"]


def test_exact_module_projection_returns_only_affected_detailed_findings() -> None:
    checker = _load_checker()
    review = _actuator_module_review()
    module_type = "ActuatorDeadZoneModule"

    projected = checker._project_review(
        review,
        ledger=".physicsguard/module_equation_ledger.yaml",
        module=module_type,
    )

    assert projected["module"] == module_type
    assert projected["record_result"]["module_type"] == module_type
    assert projected["record_result"]["finding_count"] == sum(
        result["finding_count"]
        for result in projected["record_result"]["dimensions"].values()
    )
    assert "record_results" not in projected
    assert "findings" in projected["record_result"]["dimensions"]["function_block"]


def test_module_scope_cannot_authorize_global_coverage() -> None:
    review = _actuator_module_review()

    assert review["checker_identity"] == _load_checker().CHECKER_IDENTITY
    assert review["review_scope"] == {
        "kind": "module",
        "module_type": "ActuatorDeadZoneModule",
        "global_coverage_evaluated": False,
        "global_coverage_licensed": None,
        "scope_semantic_coverage_licensed": False,
        "claim_boundary": (
            "module scope evaluates only the named record and cannot authorize global coverage"
        ),
    }
    assert review["summary"]["registered_type_count"] == 152
    assert review["summary"]["semantic_record_count"] == 152
    assert review["summary"]["scope_record_count"] == 1
    assert review["summary"]["software_registry_semantic_coverage_licensed"] is None
    assert review["summary"]["physical_semantic_coverage_licensed"] is None
    assert len(review["record_results"]) == 1
    assert "does not evaluate or license whole-registry" in review["summary"][
        "claim_boundary"
    ]


def test_module_scope_target_result_is_identical_to_full_review() -> None:
    full_result = next(
        item
        for item in _full_review()["record_results"]
        if item["module_type"] == "ActuatorDeadZoneModule"
    )
    module_result = _actuator_module_review()["record_results"][0]

    assert module_result == full_result


def test_projection_exposes_total_global_and_record_finding_counts() -> None:
    checker = _load_checker()
    projected = checker._project_review(
        _actuator_module_review(),
        ledger=".physicsguard/module_equation_ledger.yaml",
        module="ActuatorDeadZoneModule",
    )

    assert projected["finding_count"] == (
        projected["global_finding_count"] + projected["record_finding_count"]
    )
    assert projected["finding_count"] == projected["error_count"]
    assert projected["review_scope"]["global_coverage_evaluated"] is False


def test_unknown_module_projection_is_visible_failure() -> None:
    checker = _load_checker()
    review = checker.review_ledger(
        ROOT,
        LEDGER,
        review_scope="module",
        module="DefinitelyMissingModule",
    )

    projected = checker._project_review(
        review,
        ledger=".physicsguard/module_equation_ledger.yaml",
        module="DefinitelyMissingModule",
    )

    assert projected["review_scope"]["kind"] == "module"
    assert projected["review_scope"]["global_coverage_evaluated"] is False
    assert projected["review_scope"]["global_coverage_licensed"] is None
    assert projected["projection_status"] == "fail"
    assert projected["projection_error"]["code"] == "unknown_module"


def test_frozen_partition_and_live_registry_denominators_remain_exact() -> None:
    checker = _load_checker()
    payload = _payload()
    partitions = payload["frozen_patch_baseline"]["partitions"]
    records = payload["module_records"]

    assert {name: value["count"] for name, value in partitions.items()} == {
        "previously_grouped": 39,
        "mechanically_draftable": 37,
        "domain_judgment": 75,
        "supporting_framework_behavior": 1,
    }
    frozen_members = [
        module_type
        for value in partitions.values()
        for module_type in value["module_types"]
    ]
    assert len(frozen_members) == len(set(frozen_members)) == 152
    assert set(frozen_members) == checker._registered_module_types([])
    assert len(records) == len({record["module_type"] for record in records}) == 152
    assert len({record["primary_owner"] for record in records}) == 152


def test_caller_cannot_shrink_the_live_registry_denominator(tmp_path: Path) -> None:
    checker = _load_checker()
    payload = _payload()
    omitted = payload["module_records"].pop()["module_type"]

    review = checker.review_ledger(ROOT, _write(tmp_path, payload))

    assert review["status"] == "fail"
    assert review["aggregate_results"]["registry_inventory"]["status"] == "blocked"
    assert omitted in review["aggregate_results"]["registry_inventory"]["blocked_records"]
    assert any("registry_members_missing_records" in error for error in review["errors"])


def test_duplicate_module_record_is_structural_failure(tmp_path: Path) -> None:
    checker = _load_checker()
    payload = _payload()
    payload["module_records"].append(copy.deepcopy(payload["module_records"][0]))

    review = checker.review_ledger(ROOT, _write(tmp_path, payload))

    assert review["status"] == "fail"
    assert any("duplicate_module_record" in error for error in review["errors"])


def test_retired_grouped_navigation_schema_has_no_compatibility_reader(tmp_path: Path) -> None:
    checker = _load_checker()
    old = {
        "ledger_version": 1,
        "evidence_level": "navigation",
        "entries": [{"id": "group", "module_types": ["DummyResidualModule"]}],
    }

    review = checker.review_ledger(ROOT, _write(tmp_path, old, "old.yaml"))

    assert review["status"] == "fail"
    assert any("retired_schema_present" in error for error in review["errors"])
    assert any("schema_not_current" in error for error in review["errors"])


def test_malformed_yaml_remains_a_visible_structural_failure(tmp_path: Path) -> None:
    checker = _load_checker()
    path = tmp_path / "malformed.yaml"
    path.write_text("module_records: [unterminated", encoding="utf-8")

    review = checker.review_ledger(ROOT, path)

    assert review["status"] == "fail"
    assert review["aggregate_results"]["registry_inventory"]["status"] == "blocked"
    assert any("invalid YAML" in error for error in review["errors"])


def test_non_mapping_yaml_root_remains_a_visible_structural_failure(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    path = tmp_path / "sequence.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    review = checker.review_ledger(ROOT, path)

    assert review["status"] == "fail"
    assert any("ledger_root_invalid" in error for error in review["errors"])


def test_pending_review_is_valid_authoring_state_but_never_a_semantic_pass() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_payload()["module_records"][0])

    result = _review_record(checker, record)

    assert "independent_review_pending" in _codes(result, "independent_review")
    assert result["dimensions"]["independent_review"]["status"] == "blocked"
    assert record["physical_claim_licensed"] is False


def test_different_owner_strings_and_empty_findings_cannot_self_license_review(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    author = record["provenance"]["author_owner"]
    reviewer = "different-string-reviewer"
    result_id = "fake-accepted-result"
    record["physical_claim_licensed"] = True
    record["semantic_review"] = {
        "status": "accepted",
        "license": "licensed",
        "author_owner": author,
        "reviewer_owner": reviewer,
        "review_manifest": {
            "path": "review.yaml",
            "schema": checker.REVIEW_MANIFEST_SCHEMA,
            "sha256": None,
            "result_id": result_id,
            "status": "accepted",
            "record_id": "ActuatorDeadZoneModule",
        },
        "subject_fingerprint": None,
    }
    fingerprint = checker._record_fingerprint(record)
    record["semantic_review"]["subject_fingerprint"] = fingerprint
    record["semantic_review"]["review_manifest"]["sha256"] = "0" * 64
    findings = checker._empty_findings()

    checker._review_semantic_review(
        ROOT, record, "ActuatorDeadZoneModule", findings
    )

    codes = {item["code"] for item in findings["independent_review"]}
    assert "embedded_review_evidence_unauthorized" in codes
    assert "independent_review_evidence_not_run" in codes


def test_wrong_unit_mutation_is_blocked() -> None:
    checker = _load_checker()
    payload = _payload()
    record = next(
        copy.deepcopy(item)
        for item in payload["module_records"]
        if item["function_block"]["declared_variables"]
    )
    variable = record["function_block"]["declared_variables"][0]
    authority = next(
        item for item in record["symbol_units"] if item["symbol"] == variable["name"]
    )
    authority["unit"] = "definitely_wrong_unit"

    result = _review_record(checker, record)

    assert "symbol_unit_mismatch" in _codes(result, "unit")


def test_missing_equation_definition_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_payload()["module_records"][0])
    record["residual_definitions"][0]["dependencies"].append("undefined_expected")

    result = _review_record(checker, record)

    assert "undefined_equation_dependency" in _codes(result, "equation_dependency")


def test_missing_piecewise_branch_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = next(
        copy.deepcopy(item)
        for item in _payload()["module_records"]
        if any(residual["piecewise"] for residual in item["residual_definitions"])
    )
    residual = next(
        residual for residual in record["residual_definitions"] if residual["piecewise"]
    )
    residual["branches"] = residual["branches"][:1]

    result = _review_record(checker, record)

    assert "piecewise_branch_incomplete" in _codes(result, "equation_dependency")


def test_actuator_source_contract_expands_helper_and_both_control_decisions() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))

    contract = checker._source_residual_contract(record, "ActuatorDeadZoneModule")

    assert contract["error"] is None
    assert contract["names"] == {"actuator_dead_zone"}
    assert contract["expressions"]["actuator_dead_zone"] == "output - expected"
    assert contract["scales"]["actuator_dead_zone"] == "residual_scale"
    assert contract["conditional_expression_count"] == 2
    assert contract["semantic_ir_fingerprint"]
    assert contract["semantic_ir_errors"] == []
    assert any("residual_record" in part for part in contract["semantic_ir_parts"])
    assert {item["condition"] for item in contract["conditions"]} == {
        "abs(command) <= dead_zone",
        "command > 0",
    }


def test_actuator_missing_outer_dead_zone_branch_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    residual = record["residual_definitions"][0]
    residual["piecewise"] = True
    residual["branches"] = [
        {"condition": "command > 0", "expression": "1.0"},
        {"condition": "not (command > 0)", "expression": "-1.0"},
    ]

    result = _review_record(checker, record)

    assert "implementation_branch_mapping_incomplete" in _codes(
        result, "equation_dependency"
    )


def test_actuator_operator_flip_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    record["residual_definitions"][0]["expression"] = "output + expected"

    result = _review_record(checker, record)

    assert "implementation_expression_mismatch" in _codes(
        result, "equation_dependency"
    )


def test_actuator_wrong_scale_expression_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    record["residual_definitions"][0]["scale"]["expression"] = "999999.0"

    result = _review_record(checker, record)

    assert "implementation_scale_mismatch" in _codes(
        result, "equation_dependency"
    )


def test_actuator_role_swap_cannot_pass_without_independent_role_authority() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    runtime = checker._runtime_contract(ROOT, record, "ActuatorDeadZoneModule")
    assert runtime["port_contract_identity"] == checker.RUNTIME_PORT_CONTRACT_IDENTITY
    assert runtime["port_contract_fingerprint"] is None
    assert all("direction" in item for item in runtime["declared_variables"])
    by_name = {
        item["name"]: item for item in record["function_block"]["declared_variables"]
    }
    by_name["command"]["role"], by_name["output"]["role"] = (
        by_name["output"]["role"],
        by_name["command"]["role"],
    )

    result = _review_record(checker, record)

    assert "variable_role_authority_unresolved" in _codes(
        result, "function_block"
    )


def test_actuator_fixed_equation_role_cannot_hide_role_override_cases() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    record["residual_definitions"][0]["role"] = "equation"

    result = _review_record(checker, record)

    assert "dynamic_role_cases_missing" in _codes(result, "equation_dependency")


def test_bananas_self_declared_oracle_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    record["bindings"]["resources"] = [
        {
            "disposition": "not_applicable",
            "kind": "physical_formula",
            "reason": "No external resource obligation because I say so.",
        }
    ]
    record["bindings"]["oracle"] = {
        "disposition": "bound",
        "kind": "analytic_expression",
        "owner": "definitely.not.a.real.owner",
        "independent_from_implementation": True,
        "expressions": ["bananas"],
    }
    findings = checker._empty_findings()

    checker._review_independent_oracle(
        ROOT, record, "ActuatorDeadZoneModule", findings
    )

    codes = {item["code"] for item in findings["independent_oracle"]}
    assert "oracle_authority_unverified" in codes
    assert "oracle_expressions_invalid" in codes
    assert "resource_not_applicable_unbounded" in codes


def test_missing_declared_input_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = None
    dependency = None
    for item in _payload()["module_records"]:
        block_names = {
            entry["name"]
            for entry in [
                *item["function_block"]["configuration"],
                *item["function_block"]["declared_variables"],
            ]
        }
        for residual in item["residual_definitions"]:
            candidate = next(
                (name for name in residual["dependencies"] if name in block_names),
                None,
            )
            if candidate is not None:
                record = copy.deepcopy(item)
                dependency = candidate
                break
        if record is not None:
            break
    assert record is not None
    assert dependency is not None
    residual = next(
        item
        for item in record["residual_definitions"]
        if dependency in item["dependencies"]
    )
    block = record["function_block"]
    block["configuration"] = [
        item for item in block["configuration"] if item["name"] != dependency
    ]
    block["declared_variables"] = [
        item for item in block["declared_variables"] if item["name"] != dependency
    ]
    block["outputs"]["declared_variables"] = [
        name for name in block["outputs"]["declared_variables"] if name != dependency
    ]
    residual["intermediates"] = [
        item for item in residual["intermediates"] if item["symbol"] != dependency
    ]

    result = _review_record(checker, record)

    assert "undefined_equation_dependency" in _codes(result, "equation_dependency")


def test_false_state_transition_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = next(
        copy.deepcopy(item)
        for item in _payload()["module_records"]
        if any(
            variable["role"] == "input"
            for variable in item["function_block"]["declared_variables"]
        )
    )
    input_variable = next(
        variable["name"]
        for variable in record["function_block"]["declared_variables"]
        if variable["role"] == "input"
    )
    record["function_block"]["state"]["next"].append(input_variable)

    result = _review_record(checker, record)

    assert "state_role_mismatch" in _codes(result, "function_block")


def test_registry_only_selector_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "PressureRatioModule"))
    test_path = ROOT / "tests" / "test_additional_physical_relations.py"
    record["bindings"]["behavioral_tests"]["positive"] = {
        "disposition": "bound",
        "path": test_path.relative_to(ROOT).as_posix(),
        "selector": "test_default_registry_includes_additional_physical_modules",
        "sha256": _sha256(test_path),
        "case": "unparameterized",
        "pytest_nodeid": (
            "tests/test_additional_physical_relations.py::"
            "test_default_registry_includes_additional_physical_modules"
        ),
        "module_parameter": None,
        "expected_outcome": {
            "kind": "residual_record",
            "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
        },
    }

    result = _review_record(checker, record)

    assert "registry_only_test_selector" in _codes(result, "behavioral_test")


def test_parameterized_noop_helper_binding_is_rejected_despite_collectable_nodeid() -> None:
    checker = _load_checker()
    path = ROOT / "tests" / "test_module_equation_ledger.py"
    nodeid = (
        "tests/test_module_equation_ledger.py::"
        "test_parameterized_helper_contract_fixture[RatioModule]"
    )
    binding = {
        "disposition": "bound",
        "path": path.relative_to(ROOT).as_posix(),
        "selector": "test_parameterized_helper_contract_fixture",
        "sha256": _sha256(path),
        "case": "RatioModule",
        "pytest_nodeid": nodeid,
        "module_parameter": {"name": "module_type", "value": "RatioModule"},
        "expected_outcome": {
            "kind": "residual_record",
            "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
        },
    }
    findings = checker._empty_findings()
    collected, error = checker._collect_pytest_nodeids(ROOT, [path])
    assert error is None

    checker._review_test_binding(
        ROOT,
        binding,
        "RatioModule",
        "positive",
        findings,
        "behavioral_test",
        collected_nodeids=collected,
    )

    codes = {item["code"] for item in findings["behavioral_test"]}
    assert "test_case_contract_missing" in codes
    assert "test_module_not_exercised" in codes
    assert "test_behavior_not_exercised" in codes


def test_real_parameterized_helper_graph_reaches_module_and_residual_assertions() -> None:
    checker = _load_checker()
    path = ROOT / "tests" / "test_component_control_sensor_actuator.py"
    source = checker._local_test_execution_source(
        path, "test_piecewise_control_relations_zero_residual"
    )

    findings = checker._test_contract_evidence(
        source,
        "ActuatorDeadZoneModule",
        {
            "kind": "residual_record",
            "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
        },
    )

    assert findings == []


def test_exact_literal_system_spec_helper_graph_binds_registered_module_behavior() -> None:
    checker = _load_checker()
    path = ROOT / "tests" / "test_domain_judgment_module_behaviors.py"
    source = checker._local_test_execution_source(
        path, "test_chiller_simple_behavior_and_failure"
    )

    findings = checker._test_contract_evidence(
        source,
        "ChillerSimpleModule",
        {
            "kind": "residual_record",
            "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
        },
    )

    assert findings == []


def test_explicit_exact_node_execution_does_not_license_noop_behavior() -> None:
    checker = _load_checker()
    path = ROOT / "tests" / "test_module_equation_ledger.py"
    nodeid = (
        "tests/test_module_equation_ledger.py::"
        "test_parameterized_helper_contract_fixture[RatioModule]"
    )
    assert checker._execute_pytest_nodeid(ROOT, path, nodeid) is None
    source = checker._local_test_execution_source(
        path, "test_parameterized_helper_contract_fixture"
    )
    codes = {
        code
        for code, _ in checker._test_contract_evidence(
            source,
            "RatioModule",
            {
                "kind": "residual_record",
                "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
            },
        )
    }
    assert {"test_module_not_exercised", "test_behavior_not_exercised"} <= codes


def test_distinct_nodeids_without_behavioral_case_contracts_are_not_evidence() -> None:
    checker = _load_checker()
    path = ROOT / "tests" / "test_module_equation_ledger.py"
    common = {
        "disposition": "bound",
        "path": path.relative_to(ROOT).as_posix(),
        "selector": "test_parameterized_shared_positive_counter_fixture",
        "sha256": _sha256(path),
        "module_parameter": {"name": "module_type", "value": "RatioModule"},
    }
    positive = {
        **common,
        "case": "RatioModule-positive",
        "pytest_nodeid": (
            "tests/test_module_equation_ledger.py::"
            "test_parameterized_shared_positive_counter_fixture[RatioModule-positive]"
        ),
        "expected_outcome": {
            "kind": "residual_record",
            "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
        },
    }
    counterexample = {
        **common,
        "case": "RatioModule-violation",
        "pytest_nodeid": (
            "tests/test_module_equation_ledger.py::"
            "test_parameterized_shared_positive_counter_fixture[RatioModule-violation]"
        ),
        "expected_outcome": {
            "kind": "residual_violation",
            "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
            "violation": "nonzero ratio residual",
        },
    }

    assert checker._binding_identity(positive) is None
    assert checker._binding_identity(counterexample) is None


@pytest.mark.parametrize(
    ("outcome", "expected_code"),
    [
        (
            {"kind": "raises", "exception_type": "Exception", "message_selector": ""},
            "raises_outcome_incomplete",
        ),
        (
            {"kind": "audit_fail", "status_field": "", "finding_or_diagnostic": ""},
            "audit_fail_outcome_incomplete",
        ),
        (
            {"kind": "residual_violation", "residual_fields": [], "violation": ""},
            "expected_residual_fields_incomplete",
        ),
    ],
)
def test_incomplete_counterexample_outcome_is_blocked(
    outcome: dict,
    expected_code: str,
) -> None:
    checker = _load_checker()
    findings = checker._empty_findings()

    checker._review_expected_outcome(
        {"expected_outcome": outcome},
        "RatioModule",
        "counterexample",
        findings,
        "counterexample",
    )

    assert expected_code in {
        finding["code"] for finding in findings["counterexample"]
    }


@pytest.mark.parametrize(
    "outcome",
    [
        {
            "kind": "raises",
            "exception_type": "ValueError",
            "message_selector": "denominator_min_abs",
        },
        {
            "kind": "audit_fail",
            "status_field": "audit_pass",
            "finding_or_diagnostic": "ratio_relation_mismatch",
        },
        {
            "kind": "residual_violation",
            "residual_fields": ["name", "value", "role", "scale", "diagnostic_key"],
            "violation": "nonzero ratio residual",
        },
    ],
)
def test_typed_counterexample_outcomes_are_structurally_valid(outcome: dict) -> None:
    checker = _load_checker()
    findings = checker._empty_findings()

    checker._review_expected_outcome(
        {"expected_outcome": outcome},
        "RatioModule",
        "counterexample",
        findings,
        "counterexample",
    )

    assert findings["counterexample"] == []


def test_positive_and_counterexample_selectors_must_be_distinct() -> None:
    checker = _load_checker()
    record = next(
        copy.deepcopy(item)
        for item in _payload()["module_records"]
        if item["bindings"]["behavioral_tests"]["positive"].get("disposition")
        == "bound"
    )
    positive = record["bindings"]["behavioral_tests"]["positive"]
    positive["case_contract"] = {
        "inputs": {"case": positive.get("case")},
        "obligation": "same exact behavioral obligation",
        "assertion_kind": positive["expected_outcome"]["kind"],
        "expected_fingerprint": checker._canonical_hash(
            positive["expected_outcome"]
        ),
    }
    record["bindings"]["behavioral_tests"]["counterexample"] = copy.deepcopy(positive)

    result = _review_record(checker, record)

    assert "counterexample_not_distinct" in _codes(result, "counterexample")


def test_self_referential_oracle_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_payload()["module_records"][0])
    implementation_symbol = record["bindings"]["implementation"]["python_symbol"]
    record["bindings"]["oracle"] = {
        "disposition": "bound",
        "kind": "analytic_expression",
        "owner": implementation_symbol,
        "expressions": ["residuals(x, registry)"],
        "independent_from_implementation": False,
    }

    result = _review_record(checker, record)

    assert "self_referential_oracle" in _codes(result, "independent_oracle")
    assert "oracle_not_independent" in _codes(result, "independent_oracle")


def test_self_certified_review_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_payload()["module_records"][0])
    record["semantic_review"]["reviewer_owner"] = record["semantic_review"][
        "author_owner"
    ]

    result = _review_record(checker, record)

    assert "self_certified_review" in _codes(result, "independent_review")


def test_non_instantiating_example_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "RatioModule"))
    example = ROOT / "examples" / "additional" / "conflict_pressure_ratio.yaml"
    record["bindings"]["instantiation"] = {
        "disposition": "bound",
        "kind": "yaml_component",
        "path": example.relative_to(ROOT).as_posix(),
        "selector": "PressureRatioModule",
        "sha256": _sha256(example),
        "component_id": "pr",
        "parameters": {"residual_scale": 0.1},
    }

    result = _review_record(checker, record)

    assert "instantiation_module_missing" in _codes(result, "behavioral_test")


def test_placeholder_function_block_outputs_mutation_is_blocked() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_payload()["module_records"][0])
    record["function_block"]["outputs"]["residuals"] = [
        f"{record['module_type']} equations_or_residuals and diagnostic_keys"
    ]

    result = _review_record(checker, record)

    codes = _codes(result, "function_block")
    assert "placeholder_function_block_output" in codes
    assert "residual_output_mismatch" in codes


def test_not_applicable_resource_cannot_replace_independent_oracle() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_payload()["module_records"][0])
    record["bindings"]["resources"] = [
        {
            "disposition": "not_applicable",
            "kind": "physical_formula",
            "reason": "No external resource obligation because this bounded algebraic relation is fully stated in the project contract.",
        }
    ]
    record["bindings"]["oracle"] = {
        "disposition": "missing",
        "reason": "No independent oracle has been authored.",
    }

    result = _review_record(checker, record)

    assert "independent_oracle_missing" in _codes(result, "independent_oracle")


def test_same_named_fake_module_and_assert_true_are_not_behavior_evidence() -> None:
    checker = _load_checker()
    source = """
class RatioModule:
    def residuals(self):
        return []

def test_fake():
    module = RatioModule()
    module.residuals()
    assert True
"""

    codes = {
        code
        for code, _ in checker._test_contract_evidence(
            source,
            "RatioModule",
            {
                "kind": "residual_record",
                "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
            },
        )
    }

    assert "test_uses_same_named_local_fake" in codes
    assert "test_assertion_unconditional" in codes
    assert "test_expected_outcome_unbound" in codes


def test_caller_authored_execution_evidence_never_licenses_test_binding() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "RatioModule"))
    binding = record["bindings"]["behavioral_tests"]["positive"]
    binding["execution_evidence"] = {
        "terminal_status": "success",
        "receipt_id": "caller-made",
        "pytest_nodeid": binding["pytest_nodeid"],
        "test_sha256": binding["sha256"],
        "subject_fingerprint": "0" * 64,
    }
    findings = checker._empty_findings()

    checker._review_test_binding(
        ROOT,
        binding,
        "RatioModule",
        "positive",
        findings,
        "behavioral_test",
        collected_nodeids=set(_collected_nodeids()),
    )

    codes = {item["code"] for item in findings["behavioral_test"]}
    assert "caller_execution_evidence_unauthorized" in codes
    assert "test_execution_evidence_not_run" in codes


def test_structured_case_runner_observes_actual_registered_module() -> None:
    checker = _load_checker()
    expected_outcome = {
        "kind": "residual_record",
        "residual_fields": list(checker.EXPECTED_RESIDUAL_FIELDS),
    }
    binding = {
        "expected_outcome": expected_outcome,
        "case_contract": {
            "runner_identity": checker.CASE_RUNNER_IDENTITY,
            "inputs": {
                "component_id": "m",
                "parameters": {
                    "dead_zone": 0.1,
                    "gain": 1.0,
                    "residual_scale": 1.0,
                },
                "variables": {"command": 0.5, "output": 0.4},
            },
            "expected_observation": {
                "name": "actuator_dead_zone",
                "value": 0.0,
                "role": "equation",
                "scale": 1.0,
                "diagnostic_key": "actuator_dead_zone_mismatch",
            },
            "tolerance": 1e-12,
            "obligation": "registered actuator dead-zone relation",
            "assertion_kind": "residual_record",
            "expected_fingerprint": checker._canonical_hash(expected_outcome),
        },
    }
    findings = checker._empty_findings()

    stage = checker._review_structured_case_execution(
        ROOT,
        binding,
        "ActuatorDeadZoneModule",
        "positive",
        findings,
        "behavioral_test",
    )

    assert stage["status"] == "success"
    assert stage["observation"]["registered_module_type"] == "ActuatorDeadZoneModule"
    assert findings["behavioral_test"] == []

    bad = copy.deepcopy(binding)
    bad["case_contract"]["expected_observation"]["value"] = 1.0
    comparison_error = checker._compare_case_observation(
        stage["observation"],
        bad["case_contract"],
        bad["expected_outcome"],
    )
    assert comparison_error == "observed value differs beyond tolerance"

    raises_binding = {
        "expected_outcome": {
            "kind": "raises",
            "exception_type": "ValueError",
            "message_selector": "dead_zone must be nonnegative",
        },
        "case_contract": {
            "runner_identity": checker.CASE_RUNNER_IDENTITY,
            "inputs": {
                "component_id": "m",
                "parameters": {"dead_zone": -0.1},
                "variables": {},
            },
            "obligation": "protected constructor failure",
            "assertion_kind": "raises",
            "expected_fingerprint": "unused-by-runner",
        },
    }
    raises_observation = checker._run_case_request(
        {
            "producer_identity": checker.CASE_RUNNER_IDENTITY,
            "module_type": "ActuatorDeadZoneModule",
            **raises_binding["case_contract"]["inputs"],
        }
    )
    assert raises_observation["status"] == "observed_exception"
    assert checker._compare_case_observation(
        raises_observation,
        raises_binding["case_contract"],
        raises_binding["expected_outcome"],
    ) is None


def test_restricted_oracle_executes_finite_cases_and_rejects_nan_receipt_payload() -> None:
    checker = _load_checker()
    oracle = {
        "expressions": [
            {
                "name": "relation",
                "expression": "output - gain * command",
                "dependencies": ["output", "gain", "command"],
                "scale_expression": "scale",
            }
        ],
        "cases": [
            {
                "case_id": "zero",
                "inputs": {
                    "output": 2.0,
                    "gain": 2.0,
                    "command": 1.0,
                    "scale": 1.0,
                },
                "expected": {"relation": 0.0},
                "tolerance": 1e-12,
            }
        ],
        "producer_receipt": {
            "terminal_status": "success",
            "subject_fingerprint": "caller-authored",
        },
    }

    stage = checker._execute_oracle_contract(oracle, {"relation": {}})
    assert stage["status"] == "success"
    assert stage["case_count"] == 1

    oracle["cases"][0]["expected"]["relation"] = float("nan")
    failed = checker._execute_oracle_contract(oracle, {"relation": {}})
    assert failed["status"] == "fail"
    assert "finite" in failed["error"]


@pytest.mark.parametrize(
    "mutated",
    [
        "def residuals(x):\n    expected = x + 1\n    return expected\n",
        "def residuals(x):\n    if x >= 0:\n        expected = 1\n    else:\n        expected = -1\n    return expected\n",
        "def residuals(x):\n    sign = -1 if x > 0 else 1\n    return sign\n",
        "def residuals(x):\n    scale = 2.0\n    return x / scale\n",
        "def residuals(x):\n    role = 'post_check'\n    return role\n",
        "def residuals(x):\n    diagnostic = 'changed'\n    return diagnostic\n",
    ],
)
def test_source_semantic_ir_detects_local_branch_scale_role_and_diagnostic_mutations(
    mutated: str,
) -> None:
    checker = _load_checker()
    baseline = "def residuals(x):\n    expected = x - 1\n    return expected\n"

    baseline_ir = checker._source_semantic_ir_from_source(baseline)
    mutated_ir = checker._source_semantic_ir_from_source(mutated)

    assert baseline_ir["errors"] == []
    assert mutated_ir["errors"] == []
    assert mutated_ir["fingerprint"] != baseline_ir["fingerprint"]


def test_record_must_bind_the_exact_current_recursive_source_semantic_ir() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    current = checker._source_residual_contract(record, "ActuatorDeadZoneModule")
    record["source_semantic_ir"] = {
        "schema": checker.SOURCE_SEMANTIC_IR_SCHEMA,
        "fingerprint": "0" * 64,
    }

    result = _review_record(checker, record)

    assert current["semantic_ir_fingerprint"] != "0" * 64
    assert "source_semantic_ir_binding_missing" in _codes(
        result, "equation_dependency"
    )


def test_recursive_source_semantic_ir_blocks_permitted_helper_cycles() -> None:
    checker = _load_checker()
    old_a = _semantic_ir_cycle_a.__module__
    old_b = _semantic_ir_cycle_b.__module__
    _semantic_ir_cycle_a.__module__ = "physicsguard.audit_fixture"
    _semantic_ir_cycle_b.__module__ = "physicsguard.audit_fixture"
    try:
        result = checker._source_semantic_ir_for_callable(
            _semantic_ir_cycle_a,
            implementation_class=object,
            attribute_parameters={},
        )
    finally:
        _semantic_ir_cycle_a.__module__ = old_a
        _semantic_ir_cycle_b.__module__ = old_b

    assert result["fingerprint"] is None
    assert any("cycle" in error for error in result["errors"])


def test_arbitrary_constraint_region_prose_is_not_executable_evidence() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    result = _review_record(checker, record)

    codes = _codes(result, "constraint_valid_region")
    assert "constraint_predicate_not_executable" in codes
    assert "constraint_implementation_binding_missing" in codes
    assert "predicate_cases_missing" in codes


def test_coherent_fake_unit_declaration_and_authority_is_rejected() -> None:
    checker = _load_checker()
    record = copy.deepcopy(_record(_payload(), "ActuatorDeadZoneModule"))
    fake_identity = "physicsguard.project_unit_convention.fabricated"
    record["unit_convention"] = {
        "schema": checker.UNIT_CONVENTION_SCHEMA,
        "identity": fake_identity,
    }
    for item in record["symbol_units"]:
        item["reference"] = {
            "convention_identity": fake_identity,
            "dimension": "fabricated",
            "unit": item["unit"],
        }

    result = _review_record(checker, record)

    assert "unit_convention_authority_unregistered" in _codes(result, "unit")


def test_self_authored_external_review_result_is_rejected_even_when_hashes_cohere() -> None:
    checker = _load_checker()
    record_result = _actuator_module_review()["record_results"][0]
    request = record_result["review_request"]
    author = request["record_subject"]["provenance"]["author_owner"]
    result_body = {
        "schema": checker.REVIEW_RESULT_SCHEMA,
        "producer_identity": checker.REVIEW_PRODUCER_IDENTITY,
        "module_type": "ActuatorDeadZoneModule",
        "request_fingerprint": request["request_fingerprint"],
        "input_fingerprints": request["input_fingerprints"],
        "dimensions": request["dimensions"],
        "reviewer_execution_owner": author,
        "reviewer_execution_fingerprint": "fake",
        "domain_findings": [],
        "producer_findings": [],
        "disposition": "accepted",
        "terminal_status": "success",
    }
    result = {
        **result_body,
        "output_fingerprint": checker._canonical_hash(result_body),
    }
    receipt_body = {
        "schema": checker.REVIEW_RECEIPT_SCHEMA,
        "producer_identity": checker.REVIEW_PRODUCER_IDENTITY,
        "request_fingerprint": request["request_fingerprint"],
        "result_fingerprint": result["output_fingerprint"],
        "reviewer_execution_owner": author,
        "command": ["self-authored"],
        "exit_status": 0,
        "terminal_status": "success",
        "disposition": "accepted",
        "receipt_id": "fake",
    }
    receipt = {
        **receipt_body,
        "receipt_fingerprint": checker._canonical_hash(receipt_body),
    }

    stage = checker._validate_external_review_evidence(
        request,
        {"result": result, "receipt": receipt},
        root=ROOT,
        author=author,
    )

    assert stage["status"] == "fail"
    assert "distinct reviewer execution owner" in stage["error"]


def test_dummy_remains_supporting_framework_behavior_only() -> None:
    payload = _payload()
    dummy = _record(payload, "DummyResidualModule")

    assert dummy["baseline_partition"] == "supporting_framework_behavior"
    assert dummy["category"] == "supporting_framework_behavior"
    assert dummy["physical_claim_licensed"] is False
    assert set(dummy["prohibited_claims"]) == {
        "physical_blueprint_support",
        "physical_validation_depth",
        "physical_semantic_coverage",
        "user_facing_physical_claim",
    }
    from physicsguard.modules import DummyResidualModule

    assert DummyResidualModule.__name__ == "DummyResidualModule"
