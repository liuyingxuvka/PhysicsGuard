"""PhysicsGuard-owned prevented-failure contracts and executable proof checks.

SkillGuard intentionally has no PhysicsGuard semantics here.  This module is
the target-native owner for both maintained family baseline regression and the
separate, target-local purpose contract of every concrete model.  A family
baseline can never close a current modeling task.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


# These verifier modules are copied into each maintained skill and loaded
# dynamically during validation.  Keep that read-only operation from creating
# runtime authority artifacts inside the governed skill tree.
sys.dont_write_bytecode = True


BASELINE_CONTRACT_SCHEMA = "physicsguard.family_baseline_contract.v1"
BASELINE_CANDIDATE_SCHEMA = "physicsguard.family_baseline_candidate.v1"
BASELINE_ORACLE_SCHEMA = "physicsguard.family_baseline_oracle_set.v1"
BASELINE_GOOD_SCHEMA = "physicsguard.family_baseline_known_good.v1"
BASELINE_BAD_SCHEMA = "physicsguard.family_baseline_known_bad_set.v1"
DYNAMIC_CONTRACT_SCHEMA = "physicsguard.model_purpose_contract.v1"
DYNAMIC_CANDIDATE_SCHEMA = "physicsguard.model_candidate_binding.v1"
DYNAMIC_ORACLE_SCHEMA = "physicsguard.model_native_oracle_set.v1"
DYNAMIC_GOOD_SCHEMA = "physicsguard.model_known_good_set.v1"
DYNAMIC_BAD_SCHEMA = "physicsguard.model_known_bad_set.v1"
DYNAMIC_PROOF_SCHEMA = "physicsguard.model_purpose_proof_set.v1"
NATIVE_ORACLE_RESULT_SCHEMA = "physicsguard.native_model_oracle_result.v1"
RESULT_SCHEMA = "physicsguard.guard_model_proof_result.v1"
BASELINE_ROLE = "family_baseline_regression"
DYNAMIC_ROLE = "current_model_purpose"
SEMANTIC_PROOF = "native_semantic_detection"
ADMISSION_PROOF = "native_obligation_admission_gate"


class GuardModelContractError(ValueError):
    """The PhysicsGuard-owned contract or proof bundle is invalid."""


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardModelContractError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GuardModelContractError(f"{path} must contain one object")
    return value


def _contract_bundle(
    skill_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    guard_root = skill_root / "guard-model"
    return (
        _load(guard_root / "contract.json"),
        _load(guard_root / "oracles.json"),
        _load(guard_root / "known-good.json"),
        _load(guard_root / "known-bad.json"),
    )


def _canonical_runtime_identity() -> dict[str, Any]:
    """Return the one package runtime used by every maintained skill.

    Missing package authority is a visible blocker.  There is deliberately no
    per-skill file lookup or bundled fallback.
    """

    from physicsguard import skill_execution_depth

    if not callable(getattr(skill_execution_depth, "evaluate_skill_execution_package", None)):
        raise GuardModelContractError("canonical_skill_execution_depth_entrypoint_missing")
    try:
        package_version = metadata.version("physicsguard")
    except metadata.PackageNotFoundError as exc:
        raise GuardModelContractError("canonical_physicsguard_package_missing") from exc
    return {
        "provider": "physicsguard-package",
        "package_name": "physicsguard",
        "package_version": package_version,
        "guard_model_entrypoint": "physicsguard.guard_model_contract",
        "execution_depth_entrypoint": "physicsguard.skill_execution_depth",
        "fallback": False,
    }


def validate_baseline_contract_bundle(skill_root: Path) -> dict[str, Any]:
    contract, oracle_set, good, bad_set = _contract_bundle(skill_root)
    target = str(contract.get("target_skill_id", ""))
    if (
        contract.get("schema_version") != BASELINE_CONTRACT_SCHEMA
        or contract.get("artifact_role") != BASELINE_ROLE
        or not target
    ):
        raise GuardModelContractError("invalid PhysicsGuard family baseline contract identity")
    if contract.get("authoring_order") != [
        "freeze_prevented_failure_contract",
        "build_candidate",
        "prove_known_good",
        "prove_every_known_bad",
        "issue_native_receipt",
    ]:
        raise GuardModelContractError("the fixed purpose-before-candidate proof chain is missing")
    if contract.get("candidate_requires_contract_fingerprint") is not True:
        raise GuardModelContractError("candidate admission must require the frozen contract fingerprint")
    if not str(contract.get("native_owner_id", "")) or not str(contract.get("native_route_id", "")):
        raise GuardModelContractError("native owner and route are required")
    if not str(contract.get("claim_boundary", "")):
        raise GuardModelContractError("bounded claim is required")

    failures = contract.get("prevented_failure_classes")
    if not isinstance(failures, list) or not failures:
        raise GuardModelContractError("at least one prevented failure class is required")
    failure_by_id: dict[str, Mapping[str, Any]] = {}
    for row in failures:
        if not isinstance(row, Mapping):
            raise GuardModelContractError("failure rows must be objects")
        failure_id = str(row.get("failure_id", ""))
        if not failure_id or failure_id in failure_by_id:
            raise GuardModelContractError("failure ids must be non-empty and unique")
        required = (
            "title",
            "block_when",
            "expected_finding_code",
            "proof_strength",
            "known_limit",
            "claim_boundary",
        )
        if any(not str(row.get(field, "")) for field in required):
            raise GuardModelContractError(f"failure declaration is incomplete: {failure_id}")
        proof_strength = str(row["proof_strength"])
        if proof_strength not in {SEMANTIC_PROOF, ADMISSION_PROOF}:
            raise GuardModelContractError(f"unsupported proof strength: {failure_id}")
        if proof_strength == ADMISSION_PROOF:
            if row.get("expected_finding_code") != "missing_target_obligation":
                raise GuardModelContractError(
                    f"admission proof must expose the actual obligation-gate finding: {failure_id}"
                )
            if "not proven" not in str(row["title"]).lower():
                raise GuardModelContractError(
                    f"admission proof title overclaims semantic detection: {failure_id}"
                )
            if "lacks current passing target-native obligation evidence" not in str(
                row["block_when"]
            ):
                raise GuardModelContractError(
                    f"admission proof block condition is not evidence-bounded: {failure_id}"
                )
            if "does not detect" not in str(row["known_limit"]).lower():
                raise GuardModelContractError(
                    f"admission proof known limit is incomplete: {failure_id}"
                )
        failure_by_id[failure_id] = row

    if (
        oracle_set.get("schema_version") != BASELINE_ORACLE_SCHEMA
        or oracle_set.get("artifact_role") != BASELINE_ROLE
        or oracle_set.get("target_skill_id") != target
    ):
        raise GuardModelContractError("oracle set does not match the target contract")
    obligations = oracle_set.get("required_obligation_ids")
    oracles = oracle_set.get("oracles")
    if not isinstance(obligations, list) or not obligations or len(obligations) != len(set(obligations)):
        raise GuardModelContractError("required obligation ids must be a non-empty set")
    if not isinstance(oracles, list) or not oracles:
        raise GuardModelContractError("native oracles are required")
    mapped_failures: set[str] = set()
    mapped_obligations: set[str] = set()
    for oracle in oracles:
        if not isinstance(oracle, Mapping):
            raise GuardModelContractError("oracle rows must be objects")
        if oracle.get("predicate_kind") not in {
            "native_obligation_admission_must_pass",
            "native_semantic_fixture_must_block",
        }:
            raise GuardModelContractError("unsupported native oracle predicate")
        obligation_id = str(oracle.get("obligation_id", ""))
        failure_id = str(oracle.get("failure_id", ""))
        if obligation_id not in obligations or failure_id not in failure_by_id:
            raise GuardModelContractError("oracle references an unknown obligation or failure")
        if str(oracle.get("expected_finding_code", "")) != str(
            failure_by_id[failure_id]["expected_finding_code"]
        ):
            raise GuardModelContractError("oracle finding code differs from the failure declaration")
        expected_predicate = (
            "native_semantic_fixture_must_block"
            if failure_by_id[failure_id]["proof_strength"] == SEMANTIC_PROOF
            else "native_obligation_admission_must_pass"
        )
        if oracle.get("predicate_kind") != expected_predicate:
            raise GuardModelContractError(
                f"oracle proof kind differs from the failure declaration: {failure_id}"
            )
        mapped_obligations.add(obligation_id)
        mapped_failures.add(failure_id)
    if mapped_obligations != set(obligations):
        raise GuardModelContractError("every required obligation must have a native oracle")
    if mapped_failures != set(failure_by_id):
        raise GuardModelContractError("every prevented failure must have a native oracle")

    if (
        good.get("schema_version") != BASELINE_GOOD_SCHEMA
        or good.get("artifact_role") != BASELINE_ROLE
        or good.get("target_skill_id") != target
    ):
        raise GuardModelContractError("known-good proof does not match the target")
    if set(good.get("covered_obligation_ids", [])) != set(obligations):
        raise GuardModelContractError("known-good proof must cover every required obligation")
    if good.get("expected_native_status") != "pass":
        raise GuardModelContractError("known-good proof must require native pass")

    if (
        bad_set.get("schema_version") != BASELINE_BAD_SCHEMA
        or bad_set.get("artifact_role") != BASELINE_ROLE
        or bad_set.get("target_skill_id") != target
    ):
        raise GuardModelContractError("known-bad proof set does not match the target")
    cases = bad_set.get("cases")
    if not isinstance(cases, list) or not cases:
        raise GuardModelContractError("known-bad cases are required")
    case_by_failure: dict[str, Mapping[str, Any]] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            raise GuardModelContractError("known-bad case rows must be objects")
        failure_id = str(case.get("failure_id", ""))
        if failure_id not in failure_by_id or failure_id in case_by_failure:
            raise GuardModelContractError("each declared failure requires exactly one known-bad case")
        if case.get("expected_native_status") != "blocked":
            raise GuardModelContractError("known-bad cases must require native blocking")
        if case.get("expected_finding_code") != failure_by_id[failure_id]["expected_finding_code"]:
            raise GuardModelContractError("known-bad expected finding does not match its declaration")
        if case.get("proof_strength") != failure_by_id[failure_id]["proof_strength"]:
            raise GuardModelContractError("known-bad proof strength does not match its declaration")
        if str(case.get("trigger_obligation_id", "")) not in obligations:
            raise GuardModelContractError("known-bad trigger obligation is not governed")
        if case.get("proof_strength") == SEMANTIC_PROOF:
            fixture = case.get("native_fixture")
            if not isinstance(fixture, Mapping) or any(
                not str(fixture.get(field, ""))
                for field in ("test_node_id", "assertion_kind", "expected_observation")
            ):
                raise GuardModelContractError(
                    f"semantic detection requires an exact target-native fixture/oracle: {failure_id}"
                )
        elif "native_fixture" in case:
            raise GuardModelContractError(
                f"obligation-admission proof cannot claim a semantic fixture: {failure_id}"
            )
        case_by_failure[failure_id] = case
    if set(case_by_failure) != set(failure_by_id):
        raise GuardModelContractError("every declared prevented failure must be proven")
    runtime = _canonical_runtime_identity()
    return {
        "target_skill_id": target,
        "native_owner_id": contract["native_owner_id"],
        "native_route_id": contract["native_route_id"],
        "contract_fingerprint": _fingerprint(contract),
        "required_obligation_ids": list(obligations),
        "failure_by_id": failure_by_id,
        "case_by_failure": case_by_failure,
        "good": good,
        "claim_boundary": contract["claim_boundary"],
        "runtime": runtime,
        "artifact_role": BASELINE_ROLE,
    }


def validate_baseline_candidate_binding(
    skill_root: Path, contract_bundle: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    bundle = dict(contract_bundle or validate_baseline_contract_bundle(skill_root))
    candidate_path = skill_root / "guard-model" / "candidate.json"
    try:
        candidate = _load(candidate_path)
    except GuardModelContractError as exc:
        raise GuardModelContractError(f"candidate_artifact_missing: {exc}") from exc
    target = str(bundle["target_skill_id"])
    if (
        candidate.get("schema_version") != BASELINE_CANDIDATE_SCHEMA
        or candidate.get("artifact_role") != BASELINE_ROLE
    ):
        raise GuardModelContractError("candidate_artifact_schema_invalid")
    if candidate.get("target_skill_id") != target:
        raise GuardModelContractError("candidate_artifact_target_mismatch")
    if not str(candidate.get("candidate_id", "")):
        raise GuardModelContractError("candidate_artifact_id_missing")
    if candidate.get("purpose_contract_ref") != "guard-model/contract.json":
        raise GuardModelContractError("candidate_contract_ref_invalid")
    fingerprint = str(bundle["contract_fingerprint"])
    if candidate.get("purpose_contract_fingerprint") != fingerprint:
        raise GuardModelContractError("candidate_contract_fingerprint_mismatch")
    expected_definition = {
        "native_owner_id": bundle["native_owner_id"],
        "native_route_id": bundle["native_route_id"],
        "protected_failure_ids": sorted(bundle["failure_by_id"]),
        "required_obligation_ids": list(bundle["required_obligation_ids"]),
        "claim_boundary": bundle["claim_boundary"],
    }
    definition = candidate.get("candidate_definition")
    if definition != expected_definition:
        raise GuardModelContractError("candidate_definition_not_complete_for_frozen_contract")
    events = candidate.get("authoring_events")
    if not isinstance(events, list) or len(events) != 2:
        raise GuardModelContractError("candidate_authoring_event_chain_invalid")
    purpose_event = {
        "event_id": f"event:{target}:purpose-contract-frozen",
        "sequence": 1,
        "event_kind": "purpose_contract_frozen",
        "purpose_contract_fingerprint": fingerprint,
    }
    candidate_event = {
        "event_id": f"event:{target}:candidate-built",
        "sequence": 2,
        "event_kind": "candidate_built",
        "purpose_contract_fingerprint": fingerprint,
        "previous_event_fingerprint": _fingerprint(purpose_event),
        "candidate_definition_fingerprint": _fingerprint(expected_definition),
    }
    if events[0] != purpose_event or events[1] != candidate_event:
        raise GuardModelContractError("candidate_built_before_purpose_or_event_chain_broken")
    return {
        **bundle,
        "candidate_id": candidate["candidate_id"],
        "candidate_fingerprint": _fingerprint(candidate),
    }


def validate_baseline_bundle(skill_root: Path) -> dict[str, Any]:
    return validate_baseline_candidate_binding(
        skill_root, validate_baseline_contract_bundle(skill_root)
    )


def _load_satellite_runtime(skill_root: Path):
    del skill_root
    from physicsguard import skill_execution_depth

    if not callable(getattr(skill_execution_depth, "evaluate_skill_execution_package", None)):
        raise GuardModelContractError("canonical_skill_execution_depth_entrypoint_missing")
    return skill_execution_depth


def _repository_root(skill_root: Path) -> Path:
    candidate = skill_root.parents[1]
    if (candidate / "pyproject.toml").is_file() and (candidate / "tests").is_dir():
        return candidate
    raise GuardModelContractError("source-only native proof requires the PhysicsGuard repository")


def _run_pytest(skill_root: Path, node_id: str) -> None:
    root = _repository_root(skill_root)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", node_id],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise GuardModelContractError(
            f"native proof failed: {node_id}\n{completed.stdout}\n{completed.stderr}"
        )


def prove_known_good(skill_root: Path, bundle: Mapping[str, Any]) -> dict[str, Any]:
    target = str(bundle["target_skill_id"])
    if target == "physicsguard-model-dataset-validation":
        _run_pytest(
            skill_root,
            "tests/test_validation_adequacy.py::test_current_fixture_has_target_owned_deep_adequacy_receipt",
        )
        status = "pass"
    else:
        runtime = _load_satellite_runtime(skill_root)
        payload = runtime.build_skill_execution_fixture(
            target, evidence_domain="capability_validation", run_id=f"proof:{target}:known-good"
        )
        receipt = runtime.evaluate_skill_execution_package(payload)
        status = str(receipt.get("status", ""))
        if status != "pass":
            raise GuardModelContractError(f"known-good native evaluator did not pass: {receipt}")
    return {"status": status, "covered_obligation_ids": bundle["required_obligation_ids"]}


def prove_known_bad(
    skill_root: Path, bundle: Mapping[str, Any], failure_id: str
) -> dict[str, Any]:
    cases = bundle["case_by_failure"]
    if failure_id not in cases:
        raise GuardModelContractError(f"undeclared or unproved failure: {failure_id}")
    case = cases[failure_id]
    target = str(bundle["target_skill_id"])
    suffix = failure_id.rsplit(":", 1)[-1]
    proof_strength = str(bundle["failure_by_id"][failure_id]["proof_strength"])
    if proof_strength == SEMANTIC_PROOF:
        fixture = case["native_fixture"]
        node_id = str(fixture["test_node_id"])
        _run_pytest(skill_root, node_id)
        native_status = "blocked"
        finding_code = str(case["expected_finding_code"])
    else:
        runtime = _load_satellite_runtime(skill_root)
        payload = runtime.build_skill_execution_fixture(
            target,
            evidence_domain="capability_validation",
            omitted_obligation_id=str(case["trigger_obligation_id"]),
            run_id=f"proof:{target}:known-bad:{suffix}",
        )
        receipt = runtime.evaluate_skill_execution_package(payload)
        native_status = str(receipt.get("status", ""))
        if native_status != "blocked":
            raise GuardModelContractError(f"known-bad native evaluator did not block: {receipt}")
        codes = {str(row.get("code", "")) for row in receipt.get("errors", [])}
        finding_code = str(case["expected_finding_code"])
        if finding_code not in codes:
            raise GuardModelContractError("known-bad did not block through its target-native obligation gate")
    return {
        "status": native_status,
        "failure_id": failure_id,
        "trigger_obligation_id": case["trigger_obligation_id"],
        "proof_strength": proof_strength,
        "finding_code": finding_code,
    }


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()
    except OSError as exc:
        raise GuardModelContractError(f"cannot fingerprint {path}: {exc}") from exc


def _resolve_inside(target_root: Path, value: Path | str, label: str) -> Path:
    root = target_root.resolve()
    path = Path(value)
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise GuardModelContractError(f"{label}_outside_target_root:{resolved}") from exc
    if not resolved.is_file():
        raise GuardModelContractError(f"{label}_missing:{resolved}")
    return resolved


def _target_ref(target_root: Path, path: Path) -> str:
    return path.resolve().relative_to(target_root.resolve()).as_posix()


def _validate_dynamic_authority_paths(
    target_root: Path, named_paths: Mapping[str, Path | str]
) -> tuple[Path, dict[str, Path]]:
    root = target_root.resolve()
    if not root.is_dir():
        raise GuardModelContractError(f"target_root_missing:{root}")
    expected_names = {
        "contract": "contract.json",
        "candidate": "candidate.json",
        "oracles": "oracles.json",
        "known_good": "known-good.json",
        "known_bad": "known-bad.json",
        "proofs": "proofs.json",
    }
    resolved: dict[str, Path] = {}
    for label, value in named_paths.items():
        path = _resolve_inside(root, value, label)
        expected_name = expected_names.get(label)
        if expected_name and path.name != expected_name:
            raise GuardModelContractError(
                f"{label}_filename_invalid:expected={expected_name}:actual={path.name}"
            )
        resolved[label] = path
    parents = {path.parent for path in resolved.values()}
    if len(parents) != 1:
        raise GuardModelContractError("current_model_authority_files_must_share_one_directory")
    authority_root = next(iter(parents))
    base = (root / ".physicsguard" / "model-purpose").resolve()
    try:
        relative = authority_root.relative_to(base)
    except ValueError as exc:
        raise GuardModelContractError(
            "current_model_authority_must_be_target_local_under_.physicsguard/model-purpose"
        ) from exc
    if len(relative.parts) != 1 or relative.parts[0] in {"", ".", ".."}:
        raise GuardModelContractError("current_model_authority_requires_one_model_id_directory")
    return authority_root, resolved


def _validate_dynamic_role(value: Mapping[str, Any], schema: str, label: str) -> None:
    if value.get("schema_version") != schema:
        raise GuardModelContractError(f"{label}_schema_invalid")
    if value.get("artifact_role") != DYNAMIC_ROLE:
        raise GuardModelContractError(f"{label}_is_not_current_model_purpose_authority")


def validate_dynamic_contract_bundle(
    target_root: Path,
    contract_path: Path | str,
    oracle_path: Path | str,
    known_good_path: Path | str,
    known_bad_path: Path | str,
) -> dict[str, Any]:
    authority_root, paths = _validate_dynamic_authority_paths(
        target_root,
        {
            "contract": contract_path,
            "oracles": oracle_path,
            "known_good": known_good_path,
            "known_bad": known_bad_path,
        },
    )
    contract = _load(paths["contract"])
    oracles_value = _load(paths["oracles"])
    good_value = _load(paths["known_good"])
    bad_value = _load(paths["known_bad"])
    _validate_dynamic_role(contract, DYNAMIC_CONTRACT_SCHEMA, "contract")
    if "selectable_modes" in contract:
        raise GuardModelContractError("selectable_modes_are_forbidden")
    required_text = (
        "model_id",
        "native_owner_id",
        "native_route_id",
        "prevented_failure_purpose",
        "claim_boundary",
    )
    if any(not str(contract.get(field, "")).strip() for field in required_text):
        raise GuardModelContractError("dynamic_contract_identity_or_purpose_incomplete")
    if contract.get("authoring_order") != [
        "freeze_current_model_purpose",
        "build_candidate",
        "prove_known_good",
        "prove_every_known_bad",
        "issue_current_model_receipt",
    ]:
        raise GuardModelContractError("dynamic_purpose_before_candidate_chain_missing")
    boundary = contract.get("physical_or_evidence_boundary")
    if not isinstance(boundary, list) or not boundary:
        raise GuardModelContractError("dynamic_physical_or_evidence_boundary_required")
    if any(not isinstance(row, Mapping) or not str(row.get("description", "")).strip() for row in boundary):
        raise GuardModelContractError("dynamic_boundary_row_incomplete")

    failures = contract.get("prevented_failure_classes")
    if not isinstance(failures, list) or not failures:
        raise GuardModelContractError("at_least_one_dynamic_prevented_failure_required")
    failure_by_id: dict[str, Mapping[str, Any]] = {}
    for row in failures:
        if not isinstance(row, Mapping):
            raise GuardModelContractError("dynamic_failure_rows_must_be_objects")
        failure_id = str(row.get("failure_id", "")).strip()
        required = (
            "title",
            "block_when",
            "expected_finding_code",
            "proof_strength",
            "known_limit",
            "claim_boundary",
        )
        if (
            not failure_id
            or failure_id in failure_by_id
            or any(not str(row.get(field, "")).strip() for field in required)
        ):
            raise GuardModelContractError(f"dynamic_failure_incomplete_or_duplicate:{failure_id}")
        if row.get("proof_strength") != SEMANTIC_PROOF:
            raise GuardModelContractError(
                f"current_model_failure_requires_native_semantic_detection:{failure_id}"
            )
        failure_by_id[failure_id] = row

    model_id = str(contract["model_id"])
    owner = str(contract["native_owner_id"])
    contract_fingerprint = _fingerprint(contract)
    _validate_dynamic_role(oracles_value, DYNAMIC_ORACLE_SCHEMA, "oracles")
    if (
        oracles_value.get("model_id") != model_id
        or oracles_value.get("purpose_contract_fingerprint") != contract_fingerprint
    ):
        raise GuardModelContractError("oracle_set_contract_identity_mismatch")
    oracle_rows = oracles_value.get("oracles")
    if not isinstance(oracle_rows, list) or not oracle_rows:
        raise GuardModelContractError("dynamic_native_oracles_required")
    oracle_by_failure: dict[str, Mapping[str, Any]] = {}
    oracle_by_id: dict[str, Mapping[str, Any]] = {}
    runner_paths: dict[str, Path] = {}
    for row in oracle_rows:
        if not isinstance(row, Mapping):
            raise GuardModelContractError("dynamic_oracle_rows_must_be_objects")
        oracle_id = str(row.get("oracle_id", "")).strip()
        failure_id = str(row.get("failure_id", "")).strip()
        if (
            not oracle_id
            or oracle_id in oracle_by_id
            or failure_id not in failure_by_id
            or failure_id in oracle_by_failure
        ):
            raise GuardModelContractError("every_dynamic_failure_requires_exactly_one_oracle")
        if row.get("native_owner_id") != owner:
            raise GuardModelContractError(f"dynamic_oracle_owner_mismatch:{oracle_id}")
        if row.get("expected_finding_code") != failure_by_id[failure_id]["expected_finding_code"]:
            raise GuardModelContractError(f"dynamic_oracle_finding_mismatch:{oracle_id}")
        runner = _resolve_inside(target_root, str(row.get("runner_ref", "")), "oracle_runner")
        if str(row.get("runner_fingerprint", "")).upper() != _sha256_file(runner):
            raise GuardModelContractError(f"dynamic_oracle_runner_stale:{oracle_id}")
        oracle_by_id[oracle_id] = row
        oracle_by_failure[failure_id] = row
        runner_paths[oracle_id] = runner
    if set(oracle_by_failure) != set(failure_by_id):
        raise GuardModelContractError("dynamic_oracle_failure_universe_incomplete")

    def validate_cases(
        value: Mapping[str, Any], schema: str, kind: str, expected_status: str
    ) -> tuple[dict[str, Mapping[str, Any]], dict[str, Path]]:
        _validate_dynamic_role(value, schema, kind)
        if (
            value.get("model_id") != model_id
            or value.get("purpose_contract_fingerprint") != contract_fingerprint
        ):
            raise GuardModelContractError(f"{kind}_contract_identity_mismatch")
        rows = value.get("cases")
        if not isinstance(rows, list) or not rows:
            raise GuardModelContractError(f"{kind}_cases_required")
        by_failure: dict[str, Mapping[str, Any]] = {}
        fixtures: dict[str, Path] = {}
        case_ids: set[str] = set()
        for row in rows:
            if not isinstance(row, Mapping):
                raise GuardModelContractError(f"{kind}_case_rows_must_be_objects")
            failure_id = str(row.get("failure_id", "")).strip()
            case_id = str(row.get("case_id", "")).strip()
            oracle_id = str(row.get("oracle_id", "")).strip()
            if (
                failure_id not in failure_by_id
                or failure_id in by_failure
                or not case_id
                or case_id in case_ids
                or oracle_id != oracle_by_failure[failure_id]["oracle_id"]
            ):
                raise GuardModelContractError(f"{kind}_must_cover_each_failure_exactly_once")
            if row.get("expected_native_status") != expected_status:
                raise GuardModelContractError(f"{kind}_expected_status_invalid:{case_id}")
            if row.get("self_reported_outcome_allowed") is not False:
                raise GuardModelContractError(f"{kind}_self_reported_outcome_forbidden:{case_id}")
            if kind == "known_bad" and row.get("expected_finding_code") != failure_by_id[failure_id]["expected_finding_code"]:
                raise GuardModelContractError(f"known_bad_finding_mismatch:{case_id}")
            fixture = _resolve_inside(target_root, str(row.get("fixture_ref", "")), f"{kind}_fixture")
            if str(row.get("fixture_fingerprint", "")).upper() != _sha256_file(fixture):
                raise GuardModelContractError(f"{kind}_fixture_stale:{case_id}")
            by_failure[failure_id] = row
            fixtures[case_id] = fixture
            case_ids.add(case_id)
        if set(by_failure) != set(failure_by_id):
            raise GuardModelContractError(f"{kind}_failure_universe_incomplete")
        return by_failure, fixtures

    good_by_failure, good_fixtures = validate_cases(
        good_value, DYNAMIC_GOOD_SCHEMA, "known_good", "pass"
    )
    bad_by_failure, bad_fixtures = validate_cases(
        bad_value, DYNAMIC_BAD_SCHEMA, "known_bad", "blocked"
    )
    return {
        "artifact_role": DYNAMIC_ROLE,
        "target_root": target_root.resolve(),
        "authority_root": authority_root,
        "paths": paths,
        "model_id": model_id,
        "native_owner_id": owner,
        "native_route_id": str(contract["native_route_id"]),
        "contract_fingerprint": contract_fingerprint,
        "failure_by_id": failure_by_id,
        "oracle_by_failure": oracle_by_failure,
        "oracle_by_id": oracle_by_id,
        "runner_paths": runner_paths,
        "good_by_failure": good_by_failure,
        "bad_by_failure": bad_by_failure,
        "good_fixtures": good_fixtures,
        "bad_fixtures": bad_fixtures,
        "claim_boundary": str(contract["claim_boundary"]),
    }


def validate_dynamic_candidate_binding(
    target_root: Path,
    candidate_path: Path | str,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    authority_root, paths = _validate_dynamic_authority_paths(
        target_root,
        {
            "contract": bundle["paths"]["contract"],
            "candidate": candidate_path,
            "oracles": bundle["paths"]["oracles"],
            "known_good": bundle["paths"]["known_good"],
            "known_bad": bundle["paths"]["known_bad"],
        },
    )
    candidate = _load(paths["candidate"])
    _validate_dynamic_role(candidate, DYNAMIC_CANDIDATE_SCHEMA, "candidate")
    model_id = str(bundle["model_id"])
    fingerprint = str(bundle["contract_fingerprint"])
    if candidate.get("model_id") != model_id or not str(candidate.get("candidate_id", "")):
        raise GuardModelContractError("dynamic_candidate_identity_invalid")
    if candidate.get("purpose_contract_ref") != _target_ref(
        target_root, bundle["paths"]["contract"]
    ):
        raise GuardModelContractError("dynamic_candidate_contract_ref_invalid")
    if candidate.get("purpose_contract_fingerprint") != fingerprint:
        raise GuardModelContractError("dynamic_candidate_contract_fingerprint_mismatch")
    failures = sorted(bundle["failure_by_id"])
    if candidate.get("protected_failure_ids") != failures:
        raise GuardModelContractError("dynamic_candidate_failure_universe_mismatch")
    artifact = _resolve_inside(
        target_root, str(candidate.get("candidate_artifact_ref", "")), "candidate_artifact"
    )
    try:
        artifact.relative_to(authority_root)
    except ValueError:
        pass
    else:
        raise GuardModelContractError("candidate_artifact_must_be_separate_from_authority_files")
    artifact_fingerprint = _sha256_file(artifact)
    if str(candidate.get("candidate_artifact_fingerprint", "")).upper() != artifact_fingerprint:
        raise GuardModelContractError("candidate_artifact_fingerprint_mismatch")
    candidate_id = str(candidate["candidate_id"])
    purpose_event = {
        "event_id": f"event:{model_id}:purpose-contract-frozen",
        "sequence": 1,
        "event_kind": "purpose_contract_frozen",
        "purpose_contract_fingerprint": fingerprint,
    }
    candidate_event = {
        "event_id": f"event:{model_id}:candidate-built",
        "sequence": 2,
        "event_kind": "candidate_built",
        "purpose_contract_fingerprint": fingerprint,
        "previous_event_fingerprint": _fingerprint(purpose_event),
        "candidate_id": candidate_id,
        "candidate_artifact_fingerprint": artifact_fingerprint,
        "protected_failure_ids": failures,
    }
    if candidate.get("authoring_events") != [purpose_event, candidate_event]:
        raise GuardModelContractError("candidate_built_before_dynamic_purpose_or_event_chain_broken")
    return {
        **dict(bundle),
        "candidate_path": paths["candidate"],
        "candidate_id": candidate_id,
        "candidate_artifact": artifact,
        "candidate_artifact_fingerprint": artifact_fingerprint,
        "candidate_fingerprint": _fingerprint(candidate),
    }


def _run_dynamic_oracle(
    bundle: Mapping[str, Any], case: Mapping[str, Any], fixture: Path
) -> dict[str, Any]:
    oracle_id = str(case["oracle_id"])
    runner = bundle["runner_paths"][oracle_id]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--candidate",
            str(bundle["candidate_artifact"]),
            "--fixture",
            str(fixture),
            "--oracle-id",
            oracle_id,
            "--case-id",
            str(case["case_id"]),
        ],
        cwd=bundle["target_root"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise GuardModelContractError(
            f"dynamic_native_oracle_execution_failed:{oracle_id}:{completed.stdout}:{completed.stderr}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise GuardModelContractError(f"dynamic_native_oracle_output_invalid:{oracle_id}") from exc
    if not isinstance(result, dict) or result.get("schema_version") != NATIVE_ORACLE_RESULT_SCHEMA:
        raise GuardModelContractError(f"dynamic_native_oracle_result_schema_invalid:{oracle_id}")
    if (
        result.get("native_owner_id") != bundle["native_owner_id"]
        or result.get("oracle_id") != oracle_id
        or result.get("case_id") != case["case_id"]
    ):
        raise GuardModelContractError(f"dynamic_native_oracle_result_identity_mismatch:{oracle_id}")
    expected = str(case["expected_native_status"])
    if result.get("status") != expected:
        raise GuardModelContractError(
            f"dynamic_native_oracle_status_mismatch:{case['case_id']}:expected={expected}:actual={result.get('status')}"
        )
    finding_codes = result.get("finding_codes")
    if not isinstance(finding_codes, list) or any(not isinstance(item, str) for item in finding_codes):
        raise GuardModelContractError(f"dynamic_native_oracle_findings_invalid:{case['case_id']}")
    expected_finding = case.get("expected_finding_code")
    if expected == "blocked" and expected_finding not in finding_codes:
        raise GuardModelContractError(f"dynamic_native_oracle_finding_missing:{case['case_id']}")
    return result


def execute_dynamic_proofs(
    bundle: Mapping[str, Any], proofs_path: Path | str
) -> dict[str, Any]:
    authority_root, paths = _validate_dynamic_authority_paths(
        bundle["target_root"],
        {
            "contract": bundle["paths"]["contract"],
            "candidate": bundle["candidate_path"],
            "oracles": bundle["paths"]["oracles"],
            "known_good": bundle["paths"]["known_good"],
            "known_bad": bundle["paths"]["known_bad"],
        },
    )
    raw_proofs_path = Path(proofs_path)
    resolved_proofs = (
        (bundle["target_root"] / raw_proofs_path).resolve()
        if not raw_proofs_path.is_absolute()
        else raw_proofs_path.resolve()
    )
    try:
        resolved_proofs.relative_to(bundle["target_root"])
    except ValueError as exc:
        raise GuardModelContractError(
            f"proofs_outside_target_root:{resolved_proofs}"
        ) from exc
    if resolved_proofs.name != "proofs.json" or resolved_proofs.parent != authority_root:
        raise GuardModelContractError("proofs_path_must_share_current_model_authority_directory")
    paths["proofs"] = resolved_proofs
    results: list[dict[str, Any]] = []
    for case_kind, case_map, fixtures in (
        ("known_good", bundle["good_by_failure"], bundle["good_fixtures"]),
        ("known_bad", bundle["bad_by_failure"], bundle["bad_fixtures"]),
    ):
        for failure_id in sorted(case_map):
            case = case_map[failure_id]
            fixture = fixtures[str(case["case_id"])]
            native_result = _run_dynamic_oracle(bundle, case, fixture)
            oracle = bundle["oracle_by_id"][str(case["oracle_id"])]
            results.append(
                {
                    "case_kind": case_kind,
                    "case_id": case["case_id"],
                    "failure_id": failure_id,
                    "oracle_id": case["oracle_id"],
                    "native_owner_id": bundle["native_owner_id"],
                    "native_status": native_result["status"],
                    "finding_codes": native_result["finding_codes"],
                    "runner_fingerprint": str(oracle["runner_fingerprint"]).upper(),
                    "fixture_fingerprint": str(case["fixture_fingerprint"]).upper(),
                    "candidate_artifact_fingerprint": bundle[
                        "candidate_artifact_fingerprint"
                    ],
                }
            )
    proof_set = {
        "schema_version": DYNAMIC_PROOF_SCHEMA,
        "artifact_role": DYNAMIC_ROLE,
        "model_id": bundle["model_id"],
        "native_owner_id": bundle["native_owner_id"],
        "purpose_contract_fingerprint": bundle["contract_fingerprint"],
        "candidate_fingerprint": bundle["candidate_fingerprint"],
        "candidate_artifact_fingerprint": bundle["candidate_artifact_fingerprint"],
        "results": results,
        "claim_boundary": "This proof set licenses only the exact current model, purpose, failure universe, native runners, fixtures, and candidate artifact fingerprints declared here.",
    }
    resolved_proofs.write_text(
        json.dumps(proof_set, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {**proof_set, "proof_set_fingerprint": _fingerprint(proof_set)}


def validate_dynamic_closure(
    bundle: Mapping[str, Any], proofs_path: Path | str
) -> dict[str, Any]:
    _, paths = _validate_dynamic_authority_paths(
        bundle["target_root"],
        {
            "contract": bundle["paths"]["contract"],
            "candidate": bundle["candidate_path"],
            "oracles": bundle["paths"]["oracles"],
            "known_good": bundle["paths"]["known_good"],
            "known_bad": bundle["paths"]["known_bad"],
            "proofs": proofs_path,
        },
    )
    proof_set = _load(paths["proofs"])
    _validate_dynamic_role(proof_set, DYNAMIC_PROOF_SCHEMA, "proof_set")
    if (
        proof_set.get("model_id") != bundle["model_id"]
        or proof_set.get("native_owner_id") != bundle["native_owner_id"]
        or proof_set.get("purpose_contract_fingerprint") != bundle["contract_fingerprint"]
        or proof_set.get("candidate_fingerprint") != bundle["candidate_fingerprint"]
        or proof_set.get("candidate_artifact_fingerprint")
        != bundle["candidate_artifact_fingerprint"]
    ):
        raise GuardModelContractError("dynamic_proof_set_identity_stale_or_mismatched")
    rows = proof_set.get("results")
    if not isinstance(rows, list):
        raise GuardModelContractError("dynamic_proof_results_missing")
    result_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise GuardModelContractError("dynamic_proof_result_rows_must_be_objects")
        key = (str(row.get("case_kind", "")), str(row.get("failure_id", "")))
        if key in result_by_key:
            raise GuardModelContractError("dynamic_proof_result_duplicate")
        result_by_key[key] = row
    expected_keys = {
        (kind, failure_id)
        for kind in ("known_good", "known_bad")
        for failure_id in bundle["failure_by_id"]
    }
    if set(result_by_key) != expected_keys:
        raise GuardModelContractError("dynamic_proof_result_universe_not_exhaustive")
    for kind, failure_id in sorted(expected_keys):
        case = (
            bundle["good_by_failure"][failure_id]
            if kind == "known_good"
            else bundle["bad_by_failure"][failure_id]
        )
        oracle = bundle["oracle_by_failure"][failure_id]
        row = result_by_key[(kind, failure_id)]
        expected_status = "pass" if kind == "known_good" else "blocked"
        if (
            row.get("case_id") != case["case_id"]
            or row.get("oracle_id") != oracle["oracle_id"]
            or row.get("native_owner_id") != bundle["native_owner_id"]
            or row.get("native_status") != expected_status
            or str(row.get("runner_fingerprint", "")).upper()
            != str(oracle["runner_fingerprint"]).upper()
            or str(row.get("fixture_fingerprint", "")).upper()
            != str(case["fixture_fingerprint"]).upper()
            or row.get("candidate_artifact_fingerprint")
            != bundle["candidate_artifact_fingerprint"]
        ):
            raise GuardModelContractError(f"dynamic_proof_result_identity_invalid:{kind}:{failure_id}")
        codes = row.get("finding_codes")
        if not isinstance(codes, list):
            raise GuardModelContractError(f"dynamic_proof_findings_invalid:{kind}:{failure_id}")
        if kind == "known_bad" and case["expected_finding_code"] not in codes:
            raise GuardModelContractError(f"dynamic_bad_proof_did_not_block_declared_failure:{failure_id}")
    return {
        **dict(bundle),
        "proof_set_fingerprint": _fingerprint(proof_set),
        "proof_result_count": len(rows),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "check-baseline-contract",
            "check-baseline-candidate",
            "prove-baseline-good",
            "prove-baseline-bad",
            "check-current-contract",
            "check-current-candidate",
            "prove-current",
            "check-current-closure",
        ),
    )
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--target-root")
    parser.add_argument("--contract")
    parser.add_argument("--candidate")
    parser.add_argument("--oracles")
    parser.add_argument("--known-good")
    parser.add_argument("--known-bad")
    parser.add_argument("--proofs")
    parser.add_argument("--failure-id")
    args = parser.parse_args(argv)
    skill_root = Path(args.skill_root).resolve()
    bundle: dict[str, Any] = {}
    try:
        if args.action == "check-baseline-contract":
            bundle = validate_baseline_contract_bundle(skill_root)
            detail: dict[str, Any] = {
                "status": "pass",
                "artifact_role": BASELINE_ROLE,
                "failure_count": len(bundle["failure_by_id"]),
                "runtime": bundle["runtime"],
            }
        elif args.action == "check-baseline-candidate":
            bundle = validate_baseline_bundle(skill_root)
            detail = {
                "status": "pass",
                "artifact_role": BASELINE_ROLE,
                "candidate_id": bundle["candidate_id"],
                "candidate_fingerprint": bundle["candidate_fingerprint"],
            }
        elif args.action == "prove-baseline-good":
            bundle = validate_baseline_bundle(skill_root)
            if args.failure_id:
                raise GuardModelContractError("baseline good proof does not take a failure id")
            detail = prove_known_good(skill_root, bundle)
            detail["artifact_role"] = BASELINE_ROLE
        elif args.action == "prove-baseline-bad":
            bundle = validate_baseline_bundle(skill_root)
            if not args.failure_id:
                raise GuardModelContractError("baseline bad proof requires --failure-id")
            detail = prove_known_bad(skill_root, bundle, args.failure_id)
            detail["artifact_role"] = BASELINE_ROLE
        else:
            required = {
                "--target-root": args.target_root,
                "--contract": args.contract,
                "--oracles": args.oracles,
                "--known-good": args.known_good,
                "--known-bad": args.known_bad,
            }
            missing = [flag for flag, value in required.items() if not value]
            if missing:
                raise GuardModelContractError(
                    f"current_model_explicit_arguments_required:{','.join(missing)}"
                )
            target_root = Path(args.target_root).resolve()
            bundle = validate_dynamic_contract_bundle(
                target_root,
                args.contract,
                args.oracles,
                args.known_good,
                args.known_bad,
            )
            if args.action == "check-current-contract":
                detail = {
                    "status": "pass",
                    "artifact_role": DYNAMIC_ROLE,
                    "failure_count": len(bundle["failure_by_id"]),
                }
            else:
                if not args.candidate:
                    raise GuardModelContractError(
                        "current_model_explicit_arguments_required:--candidate"
                    )
                bundle = validate_dynamic_candidate_binding(
                    target_root, args.candidate, bundle
                )
                if args.action == "check-current-candidate":
                    detail = {
                        "status": "pass",
                        "artifact_role": DYNAMIC_ROLE,
                        "candidate_id": bundle["candidate_id"],
                        "candidate_fingerprint": bundle["candidate_fingerprint"],
                    }
                else:
                    if not args.proofs:
                        raise GuardModelContractError(
                            "current_model_explicit_arguments_required:--proofs"
                        )
                    if args.action == "prove-current":
                        proof_set = execute_dynamic_proofs(bundle, args.proofs)
                        detail = {
                            "status": "pass",
                            "artifact_role": DYNAMIC_ROLE,
                            "proof_result_count": len(proof_set["results"]),
                            "proof_set_fingerprint": proof_set[
                                "proof_set_fingerprint"
                            ],
                        }
                    else:
                        bundle = validate_dynamic_closure(bundle, args.proofs)
                        detail = {
                            "status": "pass",
                            "artifact_role": DYNAMIC_ROLE,
                            "proof_result_count": bundle["proof_result_count"],
                            "proof_set_fingerprint": bundle[
                                "proof_set_fingerprint"
                            ],
                        }
        result = {
            "schema_version": RESULT_SCHEMA,
            "status": "pass",
            "action": args.action,
            "authority_id": bundle.get("model_id", bundle.get("target_skill_id")),
            "artifact_role": bundle["artifact_role"],
            "contract_fingerprint": bundle["contract_fingerprint"],
            "detail": detail,
            "claim_boundary": (
                "A family baseline result proves maintained PhysicsGuard checker capability only; it cannot close a current model. "
                if bundle["artifact_role"] == BASELINE_ROLE
                else "This proves only the exact current target-local purpose, candidate, native runners, fixtures, and failure universe. "
            )
            + "SkillGuard supplies no physical meaning.",
        }
    except (GuardModelContractError, KeyError, TypeError) as exc:
        result = {
            "schema_version": RESULT_SCHEMA,
            "status": "blocked",
            "action": args.action,
            "error": str(exc),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
