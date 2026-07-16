from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from physicsguard.skill_execution_depth import (
    ROUTE_POLICIES,
    build_skill_scheduled_production_identity_sidecar,
    build_skill_scheduled_production_package,
    evaluate_skill_execution_package,
    load_skill_scheduled_production_package,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "physicsguard_skill_execution_cases.json").read_text(encoding="utf-8")
)["cases"]


def _write_production_package(
    target_root: Path,
    package: dict,
    relative: str,
) -> list[str]:
    paths: set[str] = set()
    pairs = (
        ("evidence_ref", "evidence_sha256"),
        ("artifact_ref", "artifact_sha256"),
        ("source_ref", "content_sha256"),
        ("static_binding_evidence_ref", "static_binding_evidence_sha256"),
    )

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for ref_field, hash_field in pairs:
                if ref_field in node:
                    ref = str(node[ref_field])
                    paths.add(ref)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(package)
    for ref in paths:
        path = target_root / ref
        assert path.is_file(), ref
    package_path = target_root / relative
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(json.dumps(package), encoding="utf-8")
    return [relative, *sorted(paths)]


def _write_production_inputs(
    target_root: Path,
    package: dict,
    relative: str,
    *,
    target: str,
    run_id: str,
) -> list[str]:
    target_inputs = _write_production_package(target_root, package, relative)
    package_path = target_root / relative
    sidecar_relative = relative.removesuffix(".json") + "-identity.json"
    sidecar = build_skill_scheduled_production_identity_sidecar(
        target,
        run_id=run_id,
        package_relative=relative,
        package_sha256=hashlib.sha256(package_path.read_bytes()).hexdigest(),
        scheduled_production_identity=_scheduled_identity(),
    )
    sidecar_path = target_root / sidecar_relative
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    return [*target_inputs, sidecar_relative]


def _copy_production_project(target_root: Path) -> None:
    shutil.copytree(
        ROOT / "examples/testfile_contracts/pump_loop",
        target_root / "project",
    )


def _rewrite_bound_hash(package: dict, relative: str, digest: str) -> None:
    pairs = (
        ("evidence_ref", "evidence_sha256"),
        ("artifact_ref", "artifact_sha256"),
        ("source_ref", "content_sha256"),
        ("static_binding_evidence_ref", "static_binding_evidence_sha256"),
    )

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for ref_field, hash_field in pairs:
                if node.get(ref_field) == relative:
                    node[hash_field] = digest
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(package)


def _evidence(obligation_id: str) -> dict:
    return {
        "obligation_id": obligation_id,
        "status": "complete",
        "evidence_ref": f"evidence/{obligation_id}.json",
        "evidence_sha256": "a" * 64,
        "native_range": {
            "range_id": f"native:{obligation_id}",
            "source_ref": f"evidence/{obligation_id}.json",
            "content_sha256": "a" * 64,
            "start_anchor": f"{obligation_id}:start",
            "end_anchor": f"{obligation_id}:end",
        },
    }


def _object_result(object_id: str, *, temporal: bool) -> dict:
    row = {
        "object_id": object_id,
        "object_kind": "parameter" if temporal else "artifact",
        "obligation_results": [
            {
                "obligation_id": "object.coverage_complete",
                "status": "complete",
                "evidence_ref": f"evidence/{object_id}/coverage.json",
                "evidence_sha256": "b" * 64,
            },
            {
                "obligation_id": "object.evidence_current",
                "status": "current",
                "evidence_ref": f"evidence/{object_id}/current.json",
                "evidence_sha256": "c" * 64,
            },
        ],
    }
    if temporal:
        row.update(
            {
                "temporal_behavior": "time_varying",
                "available_points": [
                    {"point_id": f"{object_id}:t{index}", "time": float(index)}
                    for index in range(16)
                ],
                "evaluated_point_ids": [
                    f"{object_id}:t0",
                    f"{object_id}:t4",
                    f"{object_id}:t8",
                    f"{object_id}:t12",
                    f"{object_id}:t15",
                ],
            }
        )
    else:
        row.update({"temporal_behavior": "not_applicable"})
    return row


def _positive_package(target: str) -> dict:
    policy = ROUTE_POLICIES[target]
    object_results = [
        _object_result("object:a", temporal=policy.temporal_depth_required),
        _object_result("object:b", temporal=False),
    ]
    if policy.temporal_depth_required:
        object_results[1].update(
            {
                "temporal_behavior": "static",
                "static_binding_evidence_ref": "evidence/object-b/static-binding.json",
                "static_binding_evidence_sha256": "9" * 64,
            }
        )
    return {
        "artifact_kind": "physicsguard_skill_execution_package",
        "package_version": "physicsguard.skill-execution.v1",
        "target_skill_id": target,
        "native_owner_id": policy.native_owner_id,
        "native_route_id": policy.native_route_id,
        "run_id": f"run:{target}:positive",
        "evidence_domain": "fixture_calibration",
        "operation_status": "pass",
        "native_artifacts": [
            {
                "artifact_id": f"artifact:{target}",
                "artifact_ref": f"fixtures/{target}.json",
                "artifact_sha256": "d" * 64,
                "status": "current",
            }
        ],
        "obligation_results": [_evidence(item) for item in policy.required_obligation_ids],
        "object_universe": {
            "declared_object_ids": ["object:a", "object:b"],
            "discovered_object_ids": ["object:a", "object:b"],
            "required_object_ids": ["object:a"],
            "critical_object_ids": ["object:a"],
            "excluded_objects": [],
            "evaluated_object_ids": ["object:a", "object:b"],
        },
        "object_results": object_results,
        "blockers": [],
        "residual_risk": ["Low-fidelity PhysicsGuard scope only."],
        "claim_boundary": "Covers only the declared current PhysicsGuard route and its complete governed object universe.",
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["target_skill_id"])
def test_every_satellite_positive_and_genuinely_shallow_calibration(case: dict) -> None:
    package = _positive_package(case["target_skill_id"])
    positive = evaluate_skill_execution_package(package)
    assert positive["status"] == "pass", positive["errors"]
    assert positive["target_skill_id"] == case["target_skill_id"]
    assert positive["receipt_sha256"]

    shallow = copy.deepcopy(package)
    shallow["run_id"] = shallow["run_id"].replace("positive", "shallow")
    shallow["obligation_results"] = [
        row
        for row in shallow["obligation_results"]
        if row["obligation_id"] != case["shallow_missing_obligation_id"]
    ]
    blocked = evaluate_skill_execution_package(shallow)
    assert blocked["status"] == "blocked"
    assert "missing_target_obligation" in {item["code"] for item in blocked["errors"]}


def test_each_time_varying_parameter_uses_its_own_dynamic_floor_and_distribution() -> None:
    package = _positive_package("physicsguard-signal-mapping-review")
    package["object_results"][0]["evaluated_point_ids"] = ["object:a:t0", "object:a:t15"]
    receipt = evaluate_skill_execution_package(package)
    codes = {item["code"] for item in receipt["errors"]}
    assert receipt["status"] == "blocked"
    assert "time_coverage_dynamic_floor_not_met" in codes
    assert "time_strata_incomplete" in codes


def test_thousand_point_parameter_requires_distributed_dynamic_floor() -> None:
    package = _positive_package("physicsguard-signal-mapping-review")
    row = package["object_results"][0]
    row["available_points"] = [
        {"point_id": f"object:a:t{index}", "time": float(index)}
        for index in range(1000)
    ]
    row["evaluated_point_ids"] = [f"object:a:t{index}" for index in range(32)]
    shallow = evaluate_skill_execution_package(package)
    assert shallow["status"] == "blocked"
    assert "time_strata_incomplete" in {item["code"] for item in shallow["errors"]}

    row["evaluated_point_ids"] = [
        f"object:a:t{round(index * 999 / 31)}" for index in range(32)
    ]
    deep = evaluate_skill_execution_package(package)
    assert deep["status"] == "pass", deep["errors"]
    temporal = next(item for item in deep["per_object_depth"] if item["object_id"] == "object:a")
    assert temporal["required_point_floor"] == 32
    assert temporal["evaluated_point_count"] == 32
    assert temporal["covered_strata"] == ["early", "late", "middle"]
    assert len(temporal["available_points"]) == 1000
    assert [row["point_id"] for row in temporal["evaluated_points"]] == row["evaluated_point_ids"]
    assert temporal["available_point_universe_sha256"]
    assert temporal["evaluated_point_selection_sha256"]
    assert {row["obligation_id"] for row in temporal["obligation_evidence"]} == {
        "object.coverage_complete",
        "object.evidence_current",
    }


def test_static_object_requires_content_addressed_binding_evidence() -> None:
    package = _positive_package("physicsguard-signal-mapping-review")
    static_row = package["object_results"][1]
    static_row.pop("static_binding_evidence_sha256")
    static_row.update(
        {
            "temporal_behavior": "static",
            "static_binding_evidence_ref": "evidence/object-b/static-binding.json",
        }
    )
    blocked = evaluate_skill_execution_package(package)
    assert blocked["status"] == "blocked"
    assert "invalid_static_binding_sha256" in {
        item["code"] for item in blocked["errors"]
    }

    static_row["static_binding_evidence_sha256"] = "9" * 64
    receipt = evaluate_skill_execution_package(package)
    assert receipt["status"] == "pass", receipt["errors"]
    static_depth = next(
        item for item in receipt["per_object_depth"] if item["object_id"] == "object:b"
    )
    assert static_depth["static_binding_evidence_ref"].endswith("static-binding.json")
    assert static_depth["static_binding_evidence_sha256"] == "9" * 64


def test_object_kind_relabel_cannot_bypass_temporal_depth() -> None:
    package = _positive_package("physicsguard-signal-mapping-review")
    row = package["object_results"][0]
    row["object_kind"] = "artifact"
    row["temporal_behavior"] = "not_applicable"
    row.pop("available_points")
    row.pop("evaluated_point_ids")

    receipt = evaluate_skill_execution_package(package)

    assert receipt["status"] == "blocked"
    assert "temporal_classification_missing" in {
        item["code"] for item in receipt["errors"]
    }


def test_one_shallow_parameter_cannot_hide_behind_another_deep_parameter() -> None:
    package = _positive_package("physicsguard-signal-mapping-review")
    package["object_universe"]["declared_object_ids"].append("object:c")
    package["object_universe"]["discovered_object_ids"].append("object:c")
    package["object_universe"]["critical_object_ids"].append("object:c")
    package["object_universe"]["evaluated_object_ids"].append("object:c")
    second = _object_result("object:c", temporal=True)
    second["evaluated_point_ids"] = ["object:c:t0", "object:c:t15"]
    package["object_results"].append(second)
    receipt = evaluate_skill_execution_package(package)
    assert receipt["status"] == "blocked"
    assert "time_coverage_dynamic_floor_not_met" in {item["code"] for item in receipt["errors"]}


def test_duplicate_time_coordinates_cannot_inflate_depth() -> None:
    package = _positive_package("physicsguard-signal-mapping-review")
    package["object_results"][0]["available_points"][1]["time"] = 0.0
    receipt = evaluate_skill_execution_package(package)
    assert receipt["status"] == "blocked"
    assert "duplicate_time_coordinate" in {item["code"] for item in receipt["errors"]}


def test_critical_object_cannot_be_hidden_as_an_exclusion() -> None:
    package = _positive_package("physicsguard-ai-debugging")
    package["object_universe"]["evaluated_object_ids"] = ["object:b"]
    package["object_universe"]["excluded_objects"] = [
        {
            "object_id": "object:a",
            "reason": "attempted shallow escape",
            "status": "current",
            "evidence_ref": "evidence/object-a-exclusion.json",
            "evidence_sha256": "f" * 64,
            "disposition": "closed_noncontributing",
            "claim_contribution": "none",
        }
    ]
    package["object_results"] = [package["object_results"][1]]
    receipt = evaluate_skill_execution_package(package)
    assert receipt["status"] == "blocked"
    assert "required_object_excluded" in {item["code"] for item in receipt["errors"]}
    assert "critical_object_excluded" in {item["code"] for item in receipt["errors"]}


def _scheduled_identity() -> dict:
    return {
        "scheduler_or_trigger_id": "trigger:physicsguard:nightly",
        "scheduled_execution_id": "execution:physicsguard:2026-07-14",
        "installation_receipt_id": "install:physicsguard:current",
        "installation_receipt_hash": "1" * 64,
        "installation_receipt_root_ref": {
            "path_token": "active_skill_root",
            "relative_path": ".skillguard/installation-receipt.json",
        },
        "installed_runtime_fingerprint": "2" * 64,
    }


def test_capability_and_scheduled_production_evidence_are_typed_and_disjoint(tmp_path: Path) -> None:
    capability = _positive_package("physicsguard-ai-debugging")
    capability["evidence_domain"] = "capability_validation"
    assert evaluate_skill_execution_package(capability)["status"] == "pass"

    relabeled = copy.deepcopy(capability)
    relabeled["evidence_domain"] = "scheduled_production"
    blocked = evaluate_skill_execution_package(relabeled)
    assert "missing_scheduled_production_identity" in {item["code"] for item in blocked["errors"]}

    production = copy.deepcopy(relabeled)
    production["scheduled_production_identity"] = _scheduled_identity()
    result = evaluate_skill_execution_package(production)
    assert result["status"] == "blocked"
    assert "fixture_as_production" in {item["code"] for item in result["errors"]}
    assert "scheduled_identity_sidecar_missing" in {
        item["code"] for item in result["errors"]
    }

    _copy_production_project(tmp_path)
    production = build_skill_scheduled_production_package(
        "physicsguard-ai-debugging",
        target_root=tmp_path,
        project_relative="project",
        run_id="run:physicsguard-ai-debugging:scheduled-production",
    )
    relative = ".skillguard/physicsguard-ai-debugging-scheduled-production.json"
    target_inputs = _write_production_inputs(
        tmp_path,
        production,
        relative,
        target="physicsguard-ai-debugging",
        run_id="run:physicsguard-ai-debugging:scheduled-production",
    )
    loaded = load_skill_scheduled_production_package(
        tmp_path,
        relative,
        {
            "run_id": "run:physicsguard-ai-debugging:scheduled-production",
            "request": {"target_input_paths": target_inputs},
        },
        "physicsguard-ai-debugging",
    )
    result = evaluate_skill_execution_package(loaded)
    assert result["status"] == "pass", result["errors"]
    assert result["scheduled_production_identity"] == _scheduled_identity()
    assert result["scheduled_production_identity_source"]["sidecar_ref"].endswith(
        "-identity.json"
    )

    fixture_with_production_identity = _positive_package("physicsguard-ai-debugging")
    fixture_with_production_identity["scheduled_production_identity"] = _scheduled_identity()
    blocked = evaluate_skill_execution_package(fixture_with_production_identity)
    assert "scheduled_identity_on_nonproduction_evidence" in {item["code"] for item in blocked["errors"]}


def test_scheduled_production_adapter_binds_exact_target_files_and_sidecar(
    tmp_path: Path,
) -> None:
    target = "physicsguard-ai-debugging"
    _copy_production_project(tmp_path)
    package = build_skill_scheduled_production_package(
        target,
        target_root=tmp_path,
        project_relative="project",
        run_id="run:physicsguard:production",
    )
    relative = f".skillguard/{target}-scheduled-production.json"
    target_inputs = _write_production_inputs(
        tmp_path,
        package,
        relative,
        target=target,
        run_id="run:physicsguard:production",
    )
    run = {
        "run_id": "run:physicsguard:production",
        "request": {"target_input_paths": target_inputs},
    }
    loaded = load_skill_scheduled_production_package(tmp_path, relative, run, target)
    assert loaded["evidence_domain"] == "scheduled_production"
    assert loaded["scheduled_production_identity"] == _scheduled_identity()
    misplaced_run = copy.deepcopy(run)
    misplaced_run["request"]["target_input_paths"] = [
        item for item in target_inputs if not item.endswith("-identity.json")
    ]
    misplaced_run["request"]["scheduled_production_identity"] = _scheduled_identity()
    with pytest.raises(ValueError, match="generic supervisor request"):
        load_skill_scheduled_production_package(
            tmp_path, relative, misplaced_run, target
        )
    (tmp_path / "extra.json").write_text("{}", encoding="utf-8")
    extra_input_run = copy.deepcopy(run)
    extra_input_run["request"]["target_input_paths"].append("extra.json")
    with pytest.raises(ValueError, match="must exactly equal"):
        load_skill_scheduled_production_package(
            tmp_path, relative, extra_input_run, target
        )
    evidence_path = tmp_path / sorted(target_inputs[1:])[0]
    if evidence_path.name.endswith("-identity.json"):
        evidence_path = tmp_path / sorted(
            item
            for item in target_inputs
            if item != relative and not item.endswith("-identity.json")
        )[0]
    evidence_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_skill_scheduled_production_package(tmp_path, relative, run, target)


def test_scheduled_production_rediscovers_semantic_rows_and_blocks_synchronized_shrink(
    tmp_path: Path,
) -> None:
    target = "physicsguard-signal-mapping-review"
    _copy_production_project(tmp_path)
    package = build_skill_scheduled_production_package(
        target,
        target_root=tmp_path,
        project_relative="project",
        run_id="run:physicsguard:synchronized-shrink",
    )
    object_ids = package["object_universe"]["discovered_object_ids"]
    assert any(
        "#canonical_id=pump.commanded_speed" in object_id
        for object_id in object_ids
    )
    assert any(
        object_id.startswith("series:") and object_id.endswith(":cmd_speed_rad_s")
        for object_id in object_ids
    )
    shrunken = copy.deepcopy(package)
    retained = shrunken["object_results"][0]["object_id"]
    for field in (
        "declared_object_ids",
        "discovered_object_ids",
        "required_object_ids",
        "critical_object_ids",
        "evaluated_object_ids",
    ):
        shrunken["object_universe"][field] = [retained]
    shrunken["object_results"] = shrunken["object_results"][:1]
    relative = f".skillguard/{target}-scheduled-production.json"
    target_inputs = _write_production_inputs(
        tmp_path,
        shrunken,
        relative,
        target=target,
        run_id="run:physicsguard:synchronized-shrink",
    )
    run = {
        "run_id": "run:physicsguard:synchronized-shrink",
        "request": {"target_input_paths": target_inputs},
    }
    with pytest.raises(ValueError, match="authoritative discovery mismatch"):
        load_skill_scheduled_production_package(tmp_path, relative, run, target)


def test_scheduled_production_rejects_generic_placeholder_with_matching_hash(
    tmp_path: Path,
) -> None:
    target = "physicsguard-ai-debugging"
    _copy_production_project(tmp_path)
    package = build_skill_scheduled_production_package(
        target,
        target_root=tmp_path,
        project_relative="project",
        run_id="run:physicsguard:generic-placeholder",
    )
    evidence_ref = package["obligation_results"][0]["evidence_ref"]
    evidence_path = tmp_path / evidence_ref
    evidence_path.write_text("generic placeholder evidence", encoding="utf-8")
    _rewrite_bound_hash(
        package,
        evidence_ref,
        hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    )
    relative = f".skillguard/{target}-scheduled-production.json"
    target_inputs = _write_production_inputs(
        tmp_path,
        package,
        relative,
        target=target,
        run_id="run:physicsguard:generic-placeholder",
    )
    run = {
        "run_id": "run:physicsguard:generic-placeholder",
        "request": {"target_input_paths": target_inputs},
    }
    with pytest.raises(ValueError, match="range anchors missing"):
        load_skill_scheduled_production_package(tmp_path, relative, run, target)


def test_satellite_contracts_use_generic_supervision_for_native_guard_proofs() -> None:
    for case in CASES:
        target = case["target_skill_id"]
        source = json.loads(
            (
                ROOT / "skill" / target / ".skillguard" / "contract-source.json"
            ).read_text(encoding="utf-8")
        )
        checks = {row["check_id"]: row for row in source["checks"]}
        guard = json.loads(
            (ROOT / "skill" / target / "guard-model" / "contract.json").read_text(
                encoding="utf-8"
            )
        )
        assert not {
            "calibration",
        }.intersection(source)
        owner = str(guard["native_owner_id"])
        route = str(guard["native_route_id"])
        assert source["integration_mode"] == "native-integrated"
        assert source["native_route_owner"] == owner
        assert source["default_route_id"] == route
        assert source["native_route_bindings"] == [
            {
                "binding_id": f"native:{target}:current",
                "native_route_id": route,
                "required_before_closure": True,
                "source": "guard-model/contract.json",
            }
        ]
        assert source["may_define_parallel_execution_route"] is False
        assert source["may_define_skillguard_runtime_route"] is False
        assert source["native_check_bindings"] == [
            {
                "binding_id": f"native-check:{target}:{check_id.replace(':', '-')}",
                "evidence_source": "guard-model/verify.py",
                "native_check_id": check_id,
                "required": True,
            }
            for check_id in checks
        ]
        depth = source["depth_profile"]
        assert depth["native_owner_id"] == owner
        assert depth["native_route_ids"] == [route]
        assert depth["native_check_ids"] == list(checks)
        assert depth["integration_mode"] == "native-integrated"
        assert depth["enforcement_level"] == "enforced"
        assert depth["required_closure_profiles"] == ["enforced"]
        assert depth["skillguard_adds_domain_route"] is False
        contract_check = f"check:{target}:family-baseline-contract"
        candidate_check = f"check:{target}:family-baseline-candidate"
        good_check = f"check:{target}:family-baseline-good"
        assert checks[candidate_check]["depends_on_check_ids"] == [contract_check]
        assert checks[good_check]["depends_on_check_ids"] == [candidate_check]
        for failure in guard["prevented_failure_classes"]:
            suffix = failure["failure_id"].rsplit(":", 1)[-1]
            bad = checks[f"check:{target}:family-baseline-bad:{suffix}"]
            assert bad["depends_on_check_ids"] == [good_check]
            assert not {
                "depth_evidence_protocol",
                "calibration_evidence_protocol",
            }.intersection(bad)


@pytest.mark.parametrize(
    "mutation, expected_code",
    [
        (lambda package: package.update(target_skill_id="foreign-target"), "unknown_target_skill"),
        (lambda package: package.update(native_owner_id="generic.owner"), "wrong_native_owner"),
        (lambda package: package.update(evidence_domain="scheduled_production_fixture"), "invalid_evidence_domain"),
        (lambda package: package["object_universe"].update(evaluated_object_ids=["object:a"]), "object_universe_not_reconciled"),
        (lambda package: package["obligation_results"][0].update(obligation_id="obligation:one"), "generic_or_duplicate_obligation"),
        (lambda package: package["obligation_results"][0]["native_range"].update(range_id="range:1"), "mechanical_or_missing_range_id"),
        (lambda package: package["native_artifacts"][0].update(status="stale"), "evidence_not_current"),
    ],
)
def test_known_bad_identity_inventory_and_range_cases_fail_closed(mutation, expected_code: str) -> None:
    package = _positive_package("physicsguard-ai-debugging")
    mutation(package)
    receipt = evaluate_skill_execution_package(package)
    assert receipt["status"] == "blocked"
    assert expected_code in {item["code"] for item in receipt["errors"]}


def test_native_range_cannot_relabel_an_unrelated_evidence_ref_or_hash() -> None:
    package = _positive_package("physicsguard-ai-debugging")
    package["obligation_results"][0]["native_range"]["source_ref"] = "evidence/unrelated.json"
    package["obligation_results"][1]["native_range"]["content_sha256"] = "f" * 64
    receipt = evaluate_skill_execution_package(package)
    codes = {item["code"] for item in receipt["errors"]}
    assert "native_range_evidence_ref_mismatch" in codes
    assert "native_range_content_hash_mismatch" in codes
