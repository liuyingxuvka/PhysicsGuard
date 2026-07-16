from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from physicsguard.guard_model_contract import (
    ADMISSION_PROOF,
    BASELINE_ROLE,
    SEMANTIC_PROOF,
    GuardModelContractError,
    validate_baseline_bundle,
    validate_baseline_contract_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
SKILLS = tuple(sorted((ROOT / "skill").glob("physicsguard-*")))
PRIMARY = ROOT / "skill" / "physicsguard-model-dataset-validation"


def _copy_guard_bundle(source: Path, target: Path, *, candidate: bool = True) -> None:
    target.mkdir()
    guard_root = target / "guard-model"
    guard_root.mkdir()
    names = ["contract", "oracles", "known-good", "known-bad"]
    if candidate:
        names.append("candidate")
    for name in names:
        shutil.copyfile(
            source / "guard-model" / f"{name}.json",
            guard_root / f"{name}.json",
        )


def test_every_physicsguard_skill_has_exact_native_family_baseline_proof() -> None:
    assert len(SKILLS) == 10
    for skill_root in SKILLS:
        bundle = validate_baseline_bundle(skill_root)
        assert bundle["artifact_role"] == BASELINE_ROLE
        assert bundle["target_skill_id"] == skill_root.name
        assert bundle["candidate_id"] == f"candidate:{skill_root.name}:guard-model-current"
        assert set(bundle["failure_by_id"]) == set(bundle["case_by_failure"])
        assert bundle["required_obligation_ids"]


def test_semantic_detection_and_admission_proofs_are_truthfully_disjoint() -> None:
    semantic_count = 0
    admission_count = 0
    for skill_root in SKILLS:
        bundle = validate_baseline_bundle(skill_root)
        for failure_id, failure in bundle["failure_by_id"].items():
            case = bundle["case_by_failure"][failure_id]
            if skill_root == PRIMARY:
                semantic_count += 1
                assert failure["proof_strength"] == SEMANTIC_PROOF
                assert failure["expected_finding_code"] != "missing_target_obligation"
                assert case["native_fixture"]["assertion_kind"] in {
                    "native_finding_type",
                    "native_finding_code",
                    "native_issue_code",
                }
                assert (
                    case["native_fixture"]["expected_observation"]
                    == failure["expected_finding_code"]
                )
                assert str(case["native_fixture"]["test_node_id"]).startswith("tests/")
            else:
                admission_count += 1
                assert failure["proof_strength"] == ADMISSION_PROOF
                assert failure["expected_finding_code"] == "missing_target_obligation"
                assert "not proven" in str(failure["title"]).lower()
                assert "does not detect" in str(failure["known_limit"]).lower()
                assert "native_fixture" not in case
    assert semantic_count == 5
    assert admission_count == 39


def test_every_declared_proof_executes_through_the_target_verifier() -> None:
    for skill_root in SKILLS:
        verifier = skill_root / "guard-model" / "verify.py"
        contract = json.loads(
            (skill_root / "guard-model" / "contract.json").read_text(encoding="utf-8")
        )
        actions = [("check-baseline-candidate", []), ("prove-baseline-good", [])]
        actions.extend(
            (
                "prove-baseline-bad",
                ["--failure-id", str(row["failure_id"])],
            )
            for row in contract["prevented_failure_classes"]
        )
        for action, extra in actions:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(verifier),
                    action,
                    "--skill-root",
                    str(skill_root),
                    *extra,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr
            result = json.loads(completed.stdout)
            assert result["status"] == "pass"
            assert result["artifact_role"] == BASELINE_ROLE


def test_unproved_failure_and_wrong_contract_authoring_order_fail_closed(
    tmp_path: Path,
) -> None:
    source = ROOT / "skill" / "physicsguard-ai-debugging"
    target = tmp_path / "unproved" / source.name
    target.parent.mkdir()
    _copy_guard_bundle(source, target)

    bad_path = target / "guard-model" / "known-bad.json"
    bad = json.loads(bad_path.read_text(encoding="utf-8"))
    bad["cases"] = bad["cases"][:-1]
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(GuardModelContractError, match="every declared prevented failure"):
        validate_baseline_bundle(target)

    ordered = tmp_path / "wrong-order" / source.name
    ordered.parent.mkdir()
    _copy_guard_bundle(source, ordered)
    contract_path = ordered / "guard-model" / "contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["authoring_order"] = contract["authoring_order"][1:]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(GuardModelContractError, match="purpose-before-candidate"):
        validate_baseline_contract_bundle(ordered)


def test_candidate_missing_mismatch_and_candidate_before_purpose_fail_closed(
    tmp_path: Path,
) -> None:
    source = ROOT / "skill" / "physicsguard-ai-debugging"

    missing = tmp_path / "missing" / source.name
    missing.parent.mkdir()
    _copy_guard_bundle(source, missing, candidate=False)
    with pytest.raises(GuardModelContractError, match="candidate_artifact_missing"):
        validate_baseline_bundle(missing)

    mismatch = tmp_path / "mismatch" / source.name
    mismatch.parent.mkdir()
    _copy_guard_bundle(source, mismatch)
    candidate_path = mismatch / "guard-model" / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["purpose_contract_fingerprint"] = "0" * 64
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    with pytest.raises(
        GuardModelContractError, match="candidate_contract_fingerprint_mismatch"
    ):
        validate_baseline_bundle(mismatch)

    premature = tmp_path / "premature" / source.name
    premature.parent.mkdir()
    _copy_guard_bundle(source, premature)
    candidate_path = premature / "guard-model" / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["authoring_events"] = list(reversed(candidate["authoring_events"]))
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    with pytest.raises(
        GuardModelContractError,
        match="candidate_built_before_purpose_or_event_chain_broken",
    ):
        validate_baseline_bundle(premature)


def test_primary_runtime_manifest_is_complete_and_every_check_fingerprints_it() -> None:
    runtime_root = PRIMARY / ".skillguard" / "runtime"
    manifest = json.loads(
        (runtime_root / "native-runtime-manifest.json").read_text(encoding="utf-8")
    )
    declared = {str(row["path"]): str(row["sha256"]) for row in manifest["files"]}
    expected_sources = {
        "skill_execution_depth.py": ROOT / "src/physicsguard/skill_execution_depth.py",
        **{
            f"physicsguard/{path.relative_to(ROOT / 'src/physicsguard').as_posix()}": path
            for path in sorted((ROOT / "src/physicsguard").rglob("*.py"))
            if "__pycache__" not in path.parts
        },
    }
    assert set(declared) == set(expected_sources)
    assert manifest["source_file_count"] == len(expected_sources)
    for relative, source in expected_sources.items():
        expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        assert declared[relative] == expected_hash
        assert hashlib.sha256((runtime_root / relative).read_bytes()).hexdigest() == expected_hash

    source_contract = json.loads(
        (PRIMARY / ".skillguard/contract-source.json").read_text(encoding="utf-8")
    )
    runtime_paths = {f".skillguard/runtime/{relative}" for relative in declared}
    runtime_paths.add(".skillguard/runtime/native-runtime-manifest.json")
    assert runtime_paths <= set(source_contract["implementation_paths"])
    for check in source_contract["checks"]:
        selectors = {
            str(row.get("path"))
            for row in check.get("input_selectors", [])
            if isinstance(row, dict) and row.get("kind") == "path"
        }
        assert runtime_paths <= selectors, check["check_id"]


def test_missing_bundled_primary_runtime_blocks_even_with_global_import(
    tmp_path: Path,
) -> None:
    __import__("physicsguard")
    target = tmp_path / PRIMARY.name
    shutil.copytree(PRIMARY, target)
    missing = target / ".skillguard/runtime/physicsguard/core/validation_depth.py"
    assert missing.is_file()
    missing.unlink()
    with pytest.raises(GuardModelContractError, match="bundled_runtime_inventory_mismatch"):
        validate_baseline_contract_bundle(target)


def test_generic_skillguard_contract_contains_only_target_owned_native_integration() -> None:
    forbidden = {
        "calibration",
        "purpose_contract_policy",
    }
    for skill_root in SKILLS:
        source = json.loads(
            (skill_root / ".skillguard" / "contract-source.json").read_text(
                encoding="utf-8"
            )
        )
        assert not forbidden.intersection(source)
        guard = json.loads(
            (skill_root / "guard-model" / "contract.json").read_text(encoding="utf-8")
        )
        assert guard["artifact_role"] == BASELINE_ROLE
        assert "selectable_modes" not in guard
        owner = str(guard["native_owner_id"])
        route = str(guard["native_route_id"])
        check_ids = [str(row["check_id"]) for row in source["checks"]]
        assert source["integration_mode"] == "native-integrated"
        assert source["native_route_owner"] == owner
        assert source["default_route_id"] == route
        assert source["native_route_bindings"] == [
            {
                "binding_id": f"native:{skill_root.name}:current",
                "native_route_id": route,
                "required_before_closure": True,
                "source": "guard-model/contract.json",
            }
        ]
        assert source["may_define_parallel_execution_route"] is False
        assert source["may_define_skillguard_runtime_route"] is False
        assert source["release_eligible"] is False
        assert source["native_check_bindings"] == [
            {
                "binding_id": (
                    f"native-check:{skill_root.name}:{check_id.replace(':', '-')}"
                ),
                "evidence_source": "guard-model/verify.py",
                "native_check_id": check_id,
                "required": True,
            }
            for check_id in check_ids
        ]
        depth = source["depth_profile"]
        assert depth["schema_version"] == "skillguard.depth_profile.v2"
        assert depth["target_skill_id"] == skill_root.name
        assert depth["integration_mode"] == "native-integrated"
        assert depth["native_owner_id"] == owner
        assert depth["native_route_ids"] == [route]
        assert depth["native_check_ids"] == check_ids
        assert depth["skillguard_adds_domain_route"] is False
        assert depth["enforcement_level"] == "enforced"
        assert depth["required_closure_profiles"] == ["enforced"]
        assert depth["provider_runtime"]["readiness_check_ids"] == [
            f"check:{skill_root.name}:family-baseline-contract"
        ]
        assert "calibration" not in depth
        compiled = json.loads(
            (skill_root / ".skillguard" / "compiled-contract.json").read_text(
                encoding="utf-8"
            )
        )
        assert compiled["depth_profile"] == depth
        required = [
            str(obligation_id)
            for check in source["checks"]
            for obligation_id in check["covers_obligation_ids"]
        ]
        assert source["closure_profiles"] == [
            {"profile_id": "enforced", "required_obligation_ids": required}
        ]
        for check in source["checks"]:
            assert not {
                "depth_evidence_protocol",
                "calibration_evidence_protocol",
                "depth_evidence_output",
                "calibration_evidence_output",
            }.intersection(check)
