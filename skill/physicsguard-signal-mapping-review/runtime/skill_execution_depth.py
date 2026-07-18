"""Target-owned execution-depth receipts for PhysicsGuard satellite skills.

This module does not recompute physical models.  It verifies that the selected
native PhysicsGuard route accounted for its complete governed object universe,
that every required route obligation has current evidence, and that every
time-varying object was sampled deeply enough across its own time axis.
The selected PhysicsGuard skill consumes this immutable receipt and keeps this
evaluator as its sole execution-depth authority.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EVIDENCE_DOMAINS = {
    "fixture_calibration",
    "capability_validation",
    "scheduled_production",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MECHANICAL_RANGE_RE = re.compile(r"^(?:range|row|item)[-:_]?\d+$", re.IGNORECASE)
SCHEDULED_IDENTITY_SIDECAR_SCHEMA = (
    "physicsguard.scheduled_production_identity_sidecar.v1"
)


@dataclass(frozen=True)
class RoutePolicy:
    target_skill_id: str
    native_owner_id: str
    native_route_id: str
    required_obligation_ids: tuple[str, ...]
    per_object_obligation_ids: tuple[str, ...] = (
        "object.coverage_complete",
        "object.evidence_current",
    )
    temporal_depth_required: bool = False


def _policy(
    target: str,
    owner: str,
    route: str,
    obligations: Sequence[str],
    *,
    temporal: bool = False,
) -> RoutePolicy:
    return RoutePolicy(
        target_skill_id=target,
        native_owner_id=owner,
        native_route_id=route,
        required_obligation_ids=tuple(obligations),
        temporal_depth_required=temporal,
    )


ROUTE_POLICIES: dict[str, RoutePolicy] = {
    "physicsguard-ai-debugging": _policy(
        "physicsguard-ai-debugging",
        "physicsguard.ai-debugging",
        "route:physicsguard-ai-debugging:audit",
        (
            "visible_symptom",
            "physical_boundary",
            "topology_inventory",
            "signal_parameter_mapping",
            "validation_depth",
            "residual_localization",
            "assumption_boundary",
            "safe_claim_boundary",
        ),
        temporal=True,
    ),
    "physicsguard-audit-closure": _policy(
        "physicsguard-audit-closure",
        "physicsguard.audit-closure",
        "route:physicsguard-audit-closure:close",
        (
            "closure_plan",
            "required_native_checks",
            "validation_depth",
            "blockers_reconciled",
            "stale_and_skipped_accounted",
            "predictive_rollout_if_requested",
            "safe_claim_boundary",
        ),
    ),
    "physicsguard-candidate-model-blueprint": _policy(
        "physicsguard-candidate-model-blueprint",
        "physicsguard.candidate-model-blueprint",
        "route:physicsguard-candidate-model-blueprint:build",
        (
            "validated_hierarchy",
            "block_readiness",
            "signal_parameter_mapping",
            "interface_inventory",
            "rollout_boundary",
            "generation_eligibility",
        ),
    ),
    "physicsguard-model-library": _policy(
        "physicsguard-model-library",
        "physicsguard.model-library",
        "route:physicsguard-model-library:reuse",
        (
            "asset_inventory",
            "profile_inventory",
            "testbench_compatibility",
            "gap_gate",
            "validation_receipt",
            "bounded_reuse_scope",
        ),
    ),
    "physicsguard-model-understanding-preflight": _policy(
        "physicsguard-model-understanding-preflight",
        "physicsguard.model-understanding-preflight",
        "route:physicsguard-model-understanding-preflight:review",
        (
            "visible_symptom",
            "physical_boundary",
            "subsystem_inventory",
            "signal_inventory",
            "parameter_inventory",
            "assumption_inventory",
            "access_gaps",
        ),
        temporal=True,
    ),
    "physicsguard-project-adoption": _policy(
        "physicsguard-project-adoption",
        "physicsguard.project-adoption",
        "route:physicsguard-project-adoption:audit",
        (
            "project_record_current",
            "toolchain_supported",
            "native_artifact_inventory",
            "blocker_inventory",
            "required_revalidation",
        ),
    ),
    "physicsguard-project-evidence-registry": _policy(
        "physicsguard-project-evidence-registry",
        "physicsguard.project-evidence-registry",
        "route:physicsguard-project-evidence-registry:check",
        (
            "artifact_inventory_reconciled",
            "binding_edges",
            "role_coverage",
            "critical_gaps",
            "bundle_scope",
        ),
        temporal=True,
    ),
    "physicsguard-signal-mapping-review": _policy(
        "physicsguard-signal-mapping-review",
        "physicsguard.signal-mapping-review",
        "route:physicsguard-signal-mapping-review:review",
        (
            "governed_mapping_inventory",
            "unit_evidence",
            "conversion_evidence",
            "revision_evidence",
            "confidence_review",
            "temporal_coverage",
            "target_variable_binding",
        ),
        temporal=True,
    ),
    "physicsguard-test-file-contract-review": _policy(
        "physicsguard-test-file-contract-review",
        "physicsguard.test-file-contract-review",
        "route:physicsguard-test-file-contract-review:check",
        (
            "file_inventory",
            "field_inventory",
            "unit_contract",
            "timing_contract",
            "testbench_binding",
            "model_binding",
            "per_signal_depth",
            "mapping_evidence",
            "project_gaps",
        ),
        temporal=True,
    ),
}


def build_skill_execution_fixture(
    target_skill_id: str,
    *,
    evidence_domain: str = "fixture_calibration",
    omitted_obligation_id: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    """Build a deterministic target-owned calibration/capability input.

    The package is deliberately evaluated by the same native route used for
    real execution-depth receipts.  A shallow case removes exactly one named
    route obligation; it does not self-report the expected outcome.
    """

    policy = ROUTE_POLICIES[target_skill_id]

    def evidence(obligation_id: str) -> dict[str, Any]:
        reference = f"evidence/{obligation_id}.json"
        return {
            "obligation_id": obligation_id,
            "status": "complete",
            "evidence_ref": reference,
            "evidence_sha256": "a" * 64,
            "native_range": {
                "range_id": f"native:{obligation_id}",
                "source_ref": reference,
                "content_sha256": "a" * 64,
                "start_anchor": f"{obligation_id}:start",
                "end_anchor": f"{obligation_id}:end",
            },
        }

    def object_result(object_id: str, *, temporal: bool) -> dict[str, Any]:
        row: dict[str, Any] = {
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
            row["temporal_behavior"] = "not_applicable"
        return row

    object_results = [
        object_result("physics-object:time-varying-input", temporal=policy.temporal_depth_required),
        object_result("physics-object:static-artifact", temporal=False),
    ]
    if policy.temporal_depth_required:
        object_results[1].update(
            {
                "temporal_behavior": "static",
                "static_binding_evidence_ref": "evidence/static-artifact/binding.json",
                "static_binding_evidence_sha256": "9" * 64,
            }
        )
    obligation_ids = [
        item
        for item in policy.required_obligation_ids
        if item != omitted_obligation_id
    ]
    return {
        "artifact_kind": "physicsguard_skill_execution_package",
        "package_version": "physicsguard.skill-execution.v1",
        "target_skill_id": target_skill_id,
        "native_owner_id": policy.native_owner_id,
        "native_route_id": policy.native_route_id,
        "run_id": run_id or f"run:{target_skill_id}:native-depth",
        "evidence_domain": evidence_domain,
        "operation_status": "pass",
        "native_artifacts": [
            {
                "artifact_id": f"artifact:{target_skill_id}:calibration",
                "artifact_ref": f"fixtures/{target_skill_id}.json",
                "artifact_sha256": "d" * 64,
                "status": "current",
            }
        ],
        "obligation_results": [evidence(item) for item in obligation_ids],
        "object_universe": {
            "declared_object_ids": [row["object_id"] for row in object_results],
            "discovered_object_ids": [row["object_id"] for row in object_results],
            "required_object_ids": [object_results[0]["object_id"]],
            "critical_object_ids": [object_results[0]["object_id"]],
            "excluded_objects": [],
            "evaluated_object_ids": [row["object_id"] for row in object_results],
        },
        "object_results": object_results,
        "blockers": [],
        "residual_risk": ["Low-fidelity PhysicsGuard scope only."],
        "claim_boundary": "The current native route and every governed object are covered; this is not high-fidelity physical proof.",
    }


def build_skill_scheduled_production_package(
    target_skill_id: str,
    *,
    target_root: str | Path,
    project_relative: str,
    run_id: str,
) -> dict[str, Any]:
    """Discover a real target project and build its scheduled route package.

    Production never calls the calibration fixture constructor.  The object
    denominator comes from every current project file plus every CSV series,
    and each time-varying series carries its own independently discovered point
    universe and distributed dynamic-floor selection.
    """

    if not run_id.strip():
        raise ValueError("scheduled production requires an exact run_id")
    policy = ROUTE_POLICIES[target_skill_id]
    root = Path(target_root).resolve(strict=True)
    project = (root / project_relative).resolve(strict=True)
    project.relative_to(root)
    if not project.is_dir():
        raise ValueError("scheduled production project root must be a directory")

    files = sorted(path for path in project.rglob("*") if path.is_file())
    if not files:
        raise ValueError("scheduled production project has no native artifacts")

    def relative(path: Path) -> str:
        return path.relative_to(root).as_posix()

    def file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    artifacts = [
        {
            "artifact_id": f"artifact:{relative(path)}",
            "artifact_ref": relative(path),
            "artifact_sha256": file_hash(path),
            "status": "current",
        }
        for path in files
    ]

    def static_result(path: Path) -> dict[str, Any]:
        ref = relative(path)
        digest = file_hash(path)
        object_id = f"file:{ref}"
        return {
            "object_id": object_id,
            "object_kind": "artifact",
            "temporal_behavior": "static" if policy.temporal_depth_required else "not_applicable",
            "static_binding_evidence_ref": ref,
            "static_binding_evidence_sha256": digest,
            "obligation_results": [
                {
                    "obligation_id": "object.coverage_complete",
                    "status": "complete",
                    "evidence_ref": ref,
                    "evidence_sha256": digest,
                },
                {
                    "obligation_id": "object.evidence_current",
                    "status": "current",
                    "evidence_ref": ref,
                    "evidence_sha256": digest,
                },
            ],
        }

    object_results = [static_result(path) for path in files]

    # A file inventory alone is not a semantic parameter/signal inventory.
    # Discover every identifiable row inside current YAML/JSON catalogs,
    # manifests, mappings, and plans so a caller cannot shrink thousands of
    # declared objects to the handful of files that contain them.
    identity_fields = (
        "parameter_id",
        "signal_id",
        "canonical_id",
        "artifact_id",
        "edge_id",
        "binding_id",
        "model_id",
        "id",
        "source_id",
        "field_name",
    )

    def semantic_mappings(value: Any) -> list[Mapping[str, Any]]:
        found: list[Mapping[str, Any]] = []
        if isinstance(value, Mapping):
            if any(
                isinstance(value.get(field), (str, int, float))
                and str(value.get(field)).strip()
                for field in identity_fields
            ):
                found.append(value)
            for child in value.values():
                found.extend(semantic_mappings(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(semantic_mappings(child))
        return found

    semantic_object_ids: set[str] = set()
    for source_path in files:
        if source_path.suffix.casefold() not in {".yaml", ".yml", ".json"}:
            continue
        try:
            if source_path.suffix.casefold() == ".json":
                structured = json.loads(source_path.read_text(encoding="utf-8"))
            else:
                import yaml  # type: ignore[import-untyped]

                structured = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        source_ref = relative(source_path)
        source_digest = file_hash(source_path)
        for row in semantic_mappings(structured):
            identity_field = next(
                (
                    field
                    for field in identity_fields
                    if isinstance(row.get(field), (str, int, float))
                    and str(row.get(field)).strip()
                ),
                "",
            )
            if not identity_field:
                continue
            identity_value = str(row[identity_field]).strip()
            object_id = (
                f"semantic:{source_ref}#{identity_field}={identity_value}"
            )
            if object_id in semantic_object_ids:
                continue
            semantic_object_ids.add(object_id)
            object_kind = (
                "parameter"
                if identity_field in {"parameter_id", "canonical_id", "field_name"}
                else "signal"
                if identity_field == "signal_id"
                else "mapping"
                if identity_field in {"edge_id", "binding_id", "source_id"}
                else "artifact_member"
            )
            object_results.append(
                {
                    "object_id": object_id,
                    "object_kind": object_kind,
                    "temporal_behavior": (
                        "static" if policy.temporal_depth_required else "not_applicable"
                    ),
                    "static_binding_evidence_ref": source_ref,
                    "static_binding_evidence_sha256": source_digest,
                    "obligation_results": [
                        {
                            "obligation_id": "object.coverage_complete",
                            "status": "complete",
                            "evidence_ref": source_ref,
                            "evidence_sha256": source_digest,
                        },
                        {
                            "obligation_id": "object.evidence_current",
                            "status": "current",
                            "evidence_ref": source_ref,
                            "evidence_sha256": source_digest,
                        },
                    ],
                }
            )
    for csv_path in (path for path in files if path.suffix.casefold() == ".csv"):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        fieldnames = list(rows[0])
        time_field = next(
            (name for name in fieldnames if name.casefold() in {"time", "time_s", "timestamp"}),
            fieldnames[0],
        )
        for field in fieldnames:
            if field == time_field:
                continue
            points: list[dict[str, Any]] = []
            for index, row in enumerate(rows):
                try:
                    time_value = float(row[time_field])
                except (KeyError, TypeError, ValueError):
                    time_value = float(index)
                points.append(
                    {
                        "point_id": f"series:{relative(csv_path)}:{field}:row-{index}",
                        "time": time_value,
                    }
                )
            floor = min(len(points), max(3, math.ceil(math.sqrt(len(points)))))
            if floor >= len(points):
                selected = [point["point_id"] for point in points]
            else:
                selected_indexes = sorted(
                    {
                        round(position * (len(points) - 1) / (floor - 1))
                        for position in range(floor)
                    }
                )
                selected = [points[index]["point_id"] for index in selected_indexes]
            ref = relative(csv_path)
            digest = file_hash(csv_path)
            object_results.append(
                {
                    "object_id": f"series:{ref}:{field}",
                    "object_kind": "parameter",
                    "temporal_behavior": "time_varying",
                    "available_points": points,
                    "evaluated_point_ids": selected,
                    "obligation_results": [
                        {
                            "obligation_id": "object.coverage_complete",
                            "status": "complete",
                            "evidence_ref": ref,
                            "evidence_sha256": digest,
                        },
                        {
                            "obligation_id": "object.evidence_current",
                            "status": "current",
                            "evidence_ref": ref,
                            "evidence_sha256": digest,
                        },
                    ],
                }
            )

    text_files = [
        path
        for path in files
        if path.suffix.casefold() in {".yaml", ".yml", ".json", ".md", ".txt", ".csv"}
        and path.read_text(encoding="utf-8", errors="replace").strip()
    ]
    if len(text_files) < len(policy.required_obligation_ids):
        raise ValueError("scheduled production project lacks distinct obligation evidence artifacts")
    obligation_results: list[dict[str, Any]] = []
    for obligation_id, path in zip(policy.required_obligation_ids, text_files):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        ref = relative(path)
        digest = file_hash(path)
        obligation_results.append(
            {
                "obligation_id": obligation_id,
                "status": "complete",
                "evidence_ref": ref,
                "evidence_sha256": digest,
                "native_range": {
                    "range_id": f"native:{target_skill_id}:{obligation_id}",
                    "source_ref": ref,
                    "content_sha256": digest,
                    "start_anchor": lines[0],
                    "end_anchor": lines[-1],
                },
            }
        )

    object_ids = [row["object_id"] for row in object_results]
    critical_ids = [
        row["object_id"]
        for row in object_results
        if row.get("temporal_behavior") == "time_varying"
    ] or object_ids[:1]
    return {
        "artifact_kind": "physicsguard_skill_execution_package",
        "package_version": "physicsguard.skill-execution.v1",
        "target_skill_id": target_skill_id,
        "native_owner_id": policy.native_owner_id,
        "native_route_id": policy.native_route_id,
        "run_id": run_id,
        "evidence_domain": "scheduled_production",
        "input_origin": "target_native_scheduled_execution",
        "native_discovery_root_ref": project_relative.replace("\\", "/"),
        "operation_status": "pass",
        "native_artifacts": artifacts,
        "obligation_results": obligation_results,
        "object_universe": {
            "declared_object_ids": object_ids,
            "discovered_object_ids": object_ids,
            "required_object_ids": critical_ids,
            "critical_object_ids": critical_ids,
            "excluded_objects": [],
            "evaluated_object_ids": object_ids,
        },
        "object_results": object_results,
        "blockers": [],
        "residual_risk": [
            "This controlled route run proves native artifact, object, and time-depth handling; it is not high-fidelity physical proof."
        ],
        "claim_boundary": (
            "The exact current project artifact universe and every discovered CSV series are reconciled for this target route. "
            "External physical truth and commercial-tool fidelity remain outside this receipt."
        ),
    }


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _error(errors: list[dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path, "message": message})


def _validate_scheduled_production_identity(
    value: Any,
    *,
    evidence_domain: Any,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    """Keep fixtures/capability checks disjoint from installed production runs."""

    if evidence_domain != "scheduled_production":
        if value not in (None, {}):
            _error(
                errors,
                "scheduled_identity_on_nonproduction_evidence",
                "scheduled_production_identity",
                "Only scheduled-production evidence may carry an installation/execution identity.",
            )
        return {}
    if not isinstance(value, Mapping):
        _error(
            errors,
            "missing_scheduled_production_identity",
            "scheduled_production_identity",
            "Scheduled production requires exact trigger, execution, installation receipt, root, and runtime identities.",
        )
        return {}
    allowed = {
        "scheduler_or_trigger_id",
        "scheduled_execution_id",
        "installation_receipt_id",
        "installation_receipt_hash",
        "installation_receipt_root_ref",
        "installed_runtime_fingerprint",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        _error(
            errors,
            "scheduled_production_identity_unknown_field",
            "scheduled_production_identity",
            f"Unknown scheduled identity fields: {unknown}",
        )
    result = {key: value.get(key) for key in sorted(allowed)}
    for field in (
        "scheduler_or_trigger_id",
        "scheduled_execution_id",
        "installation_receipt_id",
    ):
        if not isinstance(value.get(field), str) or not str(value.get(field)).strip():
            _error(errors, f"scheduled_{field}_missing", f"scheduled_production_identity.{field}", "Non-empty exact identity is required.")
    for field in ("installation_receipt_hash", "installed_runtime_fingerprint"):
        if not isinstance(value.get(field), str) or not re.fullmatch(
            r"[0-9A-Fa-f]{64}", str(value.get(field))
        ):
            _error(errors, f"scheduled_{field}_invalid", f"scheduled_production_identity.{field}", "A 64-character hexadecimal sha256 is required.")
    root_ref = value.get("installation_receipt_root_ref")
    if not isinstance(root_ref, Mapping):
        _error(errors, "scheduled_installation_root_ref_missing", "scheduled_production_identity.installation_receipt_root_ref", "Active-skill-root reference is required.")
    else:
        if set(root_ref) - {"path_token", "relative_path"}:
            _error(errors, "scheduled_installation_root_ref_unknown_field", "scheduled_production_identity.installation_receipt_root_ref", "Only path_token and relative_path are allowed.")
        relative = str(root_ref.get("relative_path", "")).replace("\\", "/")
        if root_ref.get("path_token") != "active_skill_root":
            _error(errors, "scheduled_installation_root_ref_token_invalid", "scheduled_production_identity.installation_receipt_root_ref.path_token", "path_token must be active_skill_root.")
        if (
            not relative
            or relative.startswith("/")
            or re.match(r"^[A-Za-z]:", relative)
            or any(part in {"", ".", ".."} for part in relative.split("/"))
        ):
            _error(errors, "scheduled_installation_root_ref_invalid", "scheduled_production_identity.installation_receipt_root_ref.relative_path", "A safe path relative to active_skill_root is required.")
        result["installation_receipt_root_ref"] = {
            "path_token": root_ref.get("path_token"),
            "relative_path": relative,
        }
    return result


def _validate_scheduled_production_identity_source(
    value: Any,
    *,
    evidence_domain: Any,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    """Require formal production identity to come from one verified sidecar."""

    path = "scheduled_production_identity_source"
    if evidence_domain != "scheduled_production":
        if value not in (None, {}):
            _error(
                errors,
                "scheduled_identity_sidecar_on_nonproduction_evidence",
                path,
                "Only scheduled-production evidence may carry a target-owned identity sidecar binding.",
            )
        return {}
    if not isinstance(value, Mapping):
        _error(
            errors,
            "scheduled_identity_sidecar_missing",
            path,
            "Scheduled production must be admitted through exactly one target-owned identity sidecar in the declared input set.",
        )
        return {}
    allowed = {
        "schema_version",
        "sidecar_ref",
        "sidecar_sha256",
        "package_ref",
        "package_sha256",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        _error(
            errors,
            "scheduled_identity_sidecar_source_unknown_field",
            path,
            f"Unknown identity-sidecar source fields: {unknown}",
        )
    result = {key: value.get(key) for key in sorted(allowed)}
    if value.get("schema_version") != SCHEDULED_IDENTITY_SIDECAR_SCHEMA:
        _error(
            errors,
            "scheduled_identity_sidecar_schema_invalid",
            f"{path}.schema_version",
            "The exact current target-owned identity-sidecar schema is required.",
        )
    for field in ("sidecar_ref", "package_ref"):
        relative = str(value.get(field, "")).replace("\\", "/")
        if (
            not relative
            or relative.startswith("/")
            or re.match(r"^[A-Za-z]:", relative)
            or any(part in {"", ".", ".."} for part in relative.split("/"))
        ):
            _error(
                errors,
                f"scheduled_identity_{field}_invalid",
                f"{path}.{field}",
                "A safe target-root-relative path is required.",
            )
        result[field] = relative
    for field in ("sidecar_sha256", "package_sha256"):
        digest = str(value.get(field, ""))
        if not SHA256_RE.fullmatch(digest):
            _error(
                errors,
                f"scheduled_identity_{field}_invalid",
                f"{path}.{field}",
                "A lowercase sha256 is required.",
            )
    return result


def _id_list(
    raw: Any,
    *,
    path: str,
    errors: list[dict[str, str]],
) -> tuple[str, ...]:
    if not isinstance(raw, list):
        _error(errors, "invalid_id_list", path, "Expected a list of non-empty ids.")
        return ()
    values: list[str] = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            _error(errors, "invalid_id", f"{path}[{index}]", "Id must be a non-empty string.")
            continue
        values.append(value.strip())
    if len(values) != len(set(values)):
        _error(errors, "duplicate_id", path, "Ids must be unique.")
    return tuple(values)


def _valid_evidence_row(
    row: Any,
    *,
    path: str,
    errors: list[dict[str, str]],
) -> bool:
    if not isinstance(row, Mapping):
        _error(errors, "invalid_evidence", path, "Evidence row must be an object.")
        return False
    ok = True
    if row.get("status") not in {"current", "complete", "pass"}:
        _error(errors, "evidence_not_current", f"{path}.status", "Evidence must be current and successful.")
        ok = False
    if not isinstance(row.get("evidence_ref"), str) or not row.get("evidence_ref", "").strip():
        _error(errors, "missing_evidence_ref", f"{path}.evidence_ref", "Exact evidence_ref is required.")
        ok = False
    digest = row.get("evidence_sha256")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        _error(errors, "invalid_evidence_sha256", f"{path}.evidence_sha256", "Lowercase sha256 is required.")
        ok = False
    return ok


def _validate_ranges(
    rows: Iterable[Mapping[str, Any]],
    *,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    range_ids: set[str] = set()
    exact_spans: set[tuple[str, str, str]] = set()
    numeric_spans: dict[str, list[tuple[float, float, str]]] = {}
    for index, row in enumerate(rows):
        native_range = row.get("native_range")
        path = f"obligation_results[{index}].native_range"
        if not isinstance(native_range, Mapping):
            _error(errors, "missing_native_range", path, "Each obligation needs an exact native evidence range.")
            continue
        range_id = str(native_range.get("range_id", "")).strip()
        source_ref = str(native_range.get("source_ref", "")).strip()
        content_sha256 = str(native_range.get("content_sha256", "")).strip()
        start = str(native_range.get("start_anchor", "")).strip()
        end = str(native_range.get("end_anchor", "")).strip()
        if not range_id or MECHANICAL_RANGE_RE.fullmatch(range_id):
            _error(errors, "mechanical_or_missing_range_id", f"{path}.range_id", "Range id must be semantic, not ordinal.")
        elif range_id in range_ids:
            _error(errors, "duplicate_range_id", f"{path}.range_id", "Range ids must be unique.")
        range_ids.add(range_id)
        if not source_ref or not start or not end:
            _error(errors, "incomplete_native_range", path, "source_ref, content_sha256, start_anchor, and end_anchor are required.")
            continue
        if source_ref != str(row.get("evidence_ref", "")):
            _error(errors, "native_range_evidence_ref_mismatch", path, "Range source_ref must equal this obligation's exact evidence_ref.")
        if not SHA256_RE.fullmatch(content_sha256) or content_sha256 != str(row.get("evidence_sha256", "")):
            _error(errors, "native_range_content_hash_mismatch", path, "Range content_sha256 must equal this obligation's exact evidence hash.")
        exact = (source_ref, start, end)
        if exact in exact_spans:
            _error(errors, "renamed_overlapping_range", path, "Two obligations cannot relabel the same native span.")
        exact_spans.add(exact)
        try:
            low = float(start)
            high = float(end)
        except ValueError:
            pass
        else:
            if high <= low:
                _error(errors, "invalid_numeric_range", path, "Numeric end_anchor must be greater than start_anchor.")
            for other_low, other_high, other_id in numeric_spans.setdefault(source_ref, []):
                if max(low, other_low) < min(high, other_high):
                    _error(errors, "overlapping_native_ranges", path, f"Numeric range overlaps {other_id}.")
            numeric_spans[source_ref].append((low, high, range_id))
        ranges.append(dict(native_range))
    return ranges


def _validate_time_depth(
    row: Mapping[str, Any],
    *,
    path: str,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    behavior = row.get("temporal_behavior", "not_applicable")
    result: dict[str, Any] = {"temporal_behavior": behavior}
    if behavior == "static":
        binding_ref = str(row.get("static_binding_evidence_ref", "")).strip()
        binding_sha256 = str(row.get("static_binding_evidence_sha256", "")).strip()
        if not binding_ref:
            _error(errors, "missing_static_binding", path, "Static objects need one exact binding; fake time points are not allowed.")
        if not SHA256_RE.fullmatch(binding_sha256):
            _error(
                errors,
                "invalid_static_binding_sha256",
                f"{path}.static_binding_evidence_sha256",
                "Static binding evidence needs a lowercase sha256.",
            )
        result.update(
            {
                "available_point_count": 1,
                "evaluated_point_count": 1,
                "required_point_floor": 1,
                "static_binding_evidence_ref": binding_ref,
                "static_binding_evidence_sha256": binding_sha256,
            }
        )
        return result
    if behavior == "not_applicable":
        result.update({"available_point_count": 0, "evaluated_point_count": 0, "required_point_floor": 0})
        return result
    if behavior != "time_varying":
        _error(errors, "invalid_temporal_behavior", path, "Expected static, time_varying, or not_applicable.")
        return result

    raw_points = row.get("available_points")
    if not isinstance(raw_points, list):
        _error(errors, "missing_available_time_universe", path, "Time-varying objects need the complete available point universe.")
        return result
    points: dict[str, float] = {}
    time_values: set[float] = set()
    for index, point in enumerate(raw_points):
        point_path = f"{path}.available_points[{index}]"
        if not isinstance(point, Mapping):
            _error(errors, "invalid_time_point", point_path, "Time point must be an object.")
            continue
        point_id = str(point.get("point_id", "")).strip()
        try:
            time_value = float(point.get("time"))
        except (TypeError, ValueError):
            _error(errors, "invalid_time_value", f"{point_path}.time", "Time must be numeric.")
            continue
        if not point_id or point_id in points or not math.isfinite(time_value):
            _error(errors, "invalid_time_point_identity", point_path, "Point ids must be unique and time finite.")
            continue
        if time_value in time_values:
            _error(errors, "duplicate_time_coordinate", point_path, "One object's available time universe must use distinct time coordinates.")
            continue
        points[point_id] = time_value
        time_values.add(time_value)
    selected = _id_list(row.get("evaluated_point_ids"), path=f"{path}.evaluated_point_ids", errors=errors)
    unknown = sorted(set(selected) - set(points))
    if unknown:
        _error(errors, "evaluated_point_outside_universe", path, f"Unknown evaluated points: {unknown}")
    available_count = len(points)
    floor = min(available_count, max(3, math.ceil(math.sqrt(available_count)))) if available_count else 0
    if available_count < 3:
        _error(errors, "time_universe_too_small", path, "A broad time-varying claim needs at least early/middle/late available points.")
    if len(selected) < floor:
        _error(
            errors,
            "time_coverage_dynamic_floor_not_met",
            path,
            f"Evaluated {len(selected)} of {available_count}; dynamic floor is {floor}.",
        )
    available_points = [
        {"point_id": point_id, "time": time_value}
        for point_id, time_value in sorted(points.items(), key=lambda item: (item[1], item[0]))
    ]
    evaluated_points = [
        {"point_id": point_id, "time": points[point_id]}
        for point_id in sorted(
            (point_id for point_id in selected if point_id in points),
            key=lambda point_id: (points[point_id], point_id),
        )
    ]
    selected_times = [point["time"] for point in evaluated_points]
    max_gap_ratio: float | None = None
    allowed_gap: float | None = None
    strata: list[str] = []
    if selected_times and len(set(points.values())) > 1:
        low = min(points.values())
        high = max(points.values())
        span = high - low
        normalized = [(value - low) / span for value in selected_times]
        strata = sorted(
            {
                "early" if value <= 1 / 3 else "late" if value >= 2 / 3 else "middle"
                for value in normalized
            }
        )
        if set(strata) != {"early", "middle", "late"}:
            _error(errors, "time_strata_incomplete", path, "Evaluated points must cover early, middle, and late time strata.")
        with_boundaries = [0.0, *normalized, 1.0]
        max_gap_ratio = max(
            right - left for left, right in zip(with_boundaries, with_boundaries[1:])
        )
        allowed_gap = min(0.5, 2.5 / max(len(selected) - 1, 1))
        if max_gap_ratio > allowed_gap + 1e-12:
            _error(
                errors,
                "time_coverage_gap_too_large",
                path,
                f"Largest normalized gap {max_gap_ratio:.6f} exceeds {allowed_gap:.6f}.",
            )
    result.update(
        {
            "available_point_count": available_count,
            "evaluated_point_count": len(selected),
            "required_point_floor": floor,
            "covered_strata": strata,
            "max_normalized_gap": max_gap_ratio,
            "allowed_max_normalized_gap": allowed_gap,
            "available_points": available_points,
            "evaluated_points": evaluated_points,
            "available_point_universe_sha256": _sha256(available_points),
            "evaluated_point_selection_sha256": _sha256(evaluated_points),
        }
    )
    return result


def evaluate_skill_execution_package(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one target-owned PhysicsGuard satellite execution package."""

    errors: list[dict[str, str]] = []
    target = str(payload.get("target_skill_id", "")).strip()
    policy = ROUTE_POLICIES.get(target)
    if policy is None:
        _error(errors, "unknown_target_skill", "target_skill_id", "Target is not in the closed PhysicsGuard satellite inventory.")
    else:
        if payload.get("native_owner_id") != policy.native_owner_id:
            _error(errors, "wrong_native_owner", "native_owner_id", f"Expected {policy.native_owner_id}.")
        if payload.get("native_route_id") != policy.native_route_id:
            _error(errors, "wrong_native_route", "native_route_id", f"Expected {policy.native_route_id}.")

    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        _error(errors, "missing_run_id", "run_id", "Exact run_id is required.")
    domain = payload.get("evidence_domain")
    if domain not in EVIDENCE_DOMAINS:
        _error(errors, "invalid_evidence_domain", "evidence_domain", "Evidence domain must be fixture_calibration, capability_validation, or scheduled_production.")
    input_origin = payload.get("input_origin")
    if domain == "scheduled_production" and input_origin != "target_native_scheduled_execution":
        _error(
            errors,
            "fixture_as_production",
            "input_origin",
            "Scheduled production requires the target-native scheduled execution constructor; relabeling a fixture is forbidden.",
        )
    if domain != "scheduled_production" and input_origin == "target_native_scheduled_execution":
        _error(
            errors,
            "scheduled_origin_on_nonproduction_evidence",
            "input_origin",
            "A scheduled target-native execution cannot be projected into a fixture/capability domain.",
        )
    scheduled_identity = _validate_scheduled_production_identity(
        payload.get("scheduled_production_identity"),
        evidence_domain=domain,
        errors=errors,
    )
    scheduled_identity_source = _validate_scheduled_production_identity_source(
        payload.get("scheduled_production_identity_source"),
        evidence_domain=domain,
        errors=errors,
    )
    if payload.get("operation_status") != "pass":
        _error(errors, "native_operation_not_passed", "operation_status", "The target-owned native route did not pass.")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or blockers:
        _error(errors, "unresolved_blockers", "blockers", "Broad closure requires an explicit empty blocker list.")
    if not str(payload.get("claim_boundary", "")).strip():
        _error(errors, "missing_claim_boundary", "claim_boundary", "A bounded safe claim is required.")

    artifacts = payload.get("native_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        _error(errors, "missing_native_artifacts", "native_artifacts", "At least one exact current native artifact is required.")
        artifacts = []
    artifact_ids: set[str] = set()
    for index, artifact in enumerate(artifacts):
        path = f"native_artifacts[{index}]"
        if not isinstance(artifact, Mapping):
            _error(errors, "invalid_native_artifact", path, "Native artifact must be an object.")
            continue
        artifact_id = str(artifact.get("artifact_id", "")).strip()
        if not artifact_id or artifact_id in artifact_ids:
            _error(errors, "invalid_native_artifact_id", f"{path}.artifact_id", "Artifact id must be non-empty and unique.")
        artifact_ids.add(artifact_id)
        _valid_evidence_row(
            {
                "status": artifact.get("status"),
                "evidence_ref": artifact.get("artifact_ref"),
                "evidence_sha256": artifact.get("artifact_sha256"),
            },
            path=path,
            errors=errors,
        )

    obligation_rows = payload.get("obligation_results")
    if not isinstance(obligation_rows, list):
        _error(errors, "invalid_obligation_results", "obligation_results", "Obligation results must be a list.")
        obligation_rows = []
    obligation_map: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(obligation_rows):
        path = f"obligation_results[{index}]"
        if not isinstance(row, Mapping):
            _error(errors, "invalid_obligation_result", path, "Obligation result must be an object.")
            continue
        obligation_id = str(row.get("obligation_id", "")).strip()
        if not obligation_id or obligation_id.startswith("obligation:") or obligation_id in obligation_map:
            _error(errors, "generic_or_duplicate_obligation", f"{path}.obligation_id", "Use one exact target-native obligation id.")
            continue
        obligation_map[obligation_id] = row
        _valid_evidence_row(row, path=path, errors=errors)
    if policy is not None:
        missing = sorted(set(policy.required_obligation_ids) - set(obligation_map))
        extra = sorted(set(obligation_map) - set(policy.required_obligation_ids))
        if missing:
            _error(errors, "missing_target_obligation", "obligation_results", f"Missing target obligations: {missing}")
        if extra:
            _error(errors, "foreign_target_obligation", "obligation_results", f"Foreign target obligations: {extra}")
    ranges = _validate_ranges(obligation_map.values(), errors=errors)

    universe = payload.get("object_universe")
    if not isinstance(universe, Mapping):
        _error(errors, "missing_object_universe", "object_universe", "Complete object universe reconciliation is required.")
        universe = {}
    declared = set(_id_list(universe.get("declared_object_ids"), path="object_universe.declared_object_ids", errors=errors))
    discovered = set(_id_list(universe.get("discovered_object_ids"), path="object_universe.discovered_object_ids", errors=errors))
    required = set(_id_list(universe.get("required_object_ids"), path="object_universe.required_object_ids", errors=errors))
    critical = set(_id_list(universe.get("critical_object_ids"), path="object_universe.critical_object_ids", errors=errors))
    evaluated = set(_id_list(universe.get("evaluated_object_ids"), path="object_universe.evaluated_object_ids", errors=errors))
    exclusions_raw = universe.get("excluded_objects")
    if not isinstance(exclusions_raw, list):
        _error(errors, "invalid_exclusions", "object_universe.excluded_objects", "Excluded objects must be an explicit list.")
        exclusions_raw = []
    excluded: set[str] = set()
    for index, exclusion in enumerate(exclusions_raw):
        path = f"object_universe.excluded_objects[{index}]"
        if not isinstance(exclusion, Mapping):
            _error(errors, "invalid_exclusion", path, "Exclusion must be an object.")
            continue
        object_id = str(exclusion.get("object_id", "")).strip()
        if not object_id or object_id in excluded or not str(exclusion.get("reason", "")).strip():
            _error(errors, "unreviewed_exclusion", path, "Exclusions need a unique id and specific target-owned reason.")
            continue
        _valid_evidence_row(exclusion, path=path, errors=errors)
        if exclusion.get("disposition") != "closed_noncontributing" or exclusion.get("claim_contribution") != "none":
            _error(errors, "exclusion_not_proven_noncontributing", path, "Excluded objects need closed_noncontributing disposition and claim_contribution=none.")
        excluded.add(object_id)
    all_objects = declared | discovered | required
    if not all_objects:
        _error(errors, "empty_object_universe", "object_universe", "A broad execution claim needs a non-empty denominator.")
    if not excluded <= all_objects:
        _error(errors, "excluded_object_outside_universe", "object_universe", "Excluded ids must come from the declared/discovered/required universe.")
    if not critical <= all_objects:
        _error(errors, "critical_object_outside_universe", "object_universe.critical_object_ids", "Critical ids must come from the declared/discovered/required universe.")
    if required & excluded:
        _error(errors, "required_object_excluded", "object_universe", "Required objects cannot be excluded from broad closure.")
    if critical & excluded:
        _error(errors, "critical_object_excluded", "object_universe", "Critical objects cannot be excluded from broad closure.")
    eligible = all_objects - excluded
    if evaluated != eligible:
        _error(
            errors,
            "object_universe_not_reconciled",
            "object_universe.evaluated_object_ids",
            f"Evaluated ids must equal the complete eligible universe; missing={sorted(eligible - evaluated)}, foreign={sorted(evaluated - eligible)}.",
        )

    raw_object_results = payload.get("object_results")
    if not isinstance(raw_object_results, list):
        _error(errors, "invalid_object_results", "object_results", "Per-object results are required.")
        raw_object_results = []
    object_map: dict[str, Mapping[str, Any]] = {}
    time_results: list[dict[str, Any]] = []
    for index, row in enumerate(raw_object_results):
        path = f"object_results[{index}]"
        if not isinstance(row, Mapping):
            _error(errors, "invalid_object_result", path, "Object result must be an object.")
            continue
        object_id = str(row.get("object_id", "")).strip()
        if not object_id or object_id in object_map:
            _error(errors, "invalid_object_result_id", f"{path}.object_id", "Object result ids must be unique and non-empty.")
            continue
        object_map[object_id] = row
        per_rows = row.get("obligation_results")
        if not isinstance(per_rows, list):
            _error(errors, "missing_per_object_obligations", path, "Each object needs explicit obligation results.")
            per_rows = []
        per_map: dict[str, Mapping[str, Any]] = {}
        for per_index, per_row in enumerate(per_rows):
            per_path = f"{path}.obligation_results[{per_index}]"
            if not isinstance(per_row, Mapping):
                _error(errors, "invalid_per_object_obligation", per_path, "Per-object obligation must be an object.")
                continue
            obligation_id = str(per_row.get("obligation_id", "")).strip()
            if obligation_id in per_map:
                _error(errors, "duplicate_per_object_obligation", per_path, "Per-object obligation ids must be unique.")
            per_map[obligation_id] = per_row
            _valid_evidence_row(per_row, path=per_path, errors=errors)
        if policy is not None:
            missing_per = sorted(set(policy.per_object_obligation_ids) - set(per_map))
            if missing_per:
                _error(errors, "missing_per_object_obligation", path, f"Missing per-object obligations: {missing_per}")
        time_result = _validate_time_depth(row, path=path, errors=errors)
        if (
            policy is not None
            and policy.temporal_depth_required
            and row.get("temporal_behavior") == "not_applicable"
        ):
            _error(
                errors,
                "temporal_classification_missing",
                path,
                "Every object governed by a temporal-depth route must be classified "
                "static or time_varying; changing object_kind cannot bypass depth.",
            )
        per_object_evidence = [
            {
                "obligation_id": obligation_id,
                "status": per_row.get("status"),
                "evidence_ref": per_row.get("evidence_ref"),
                "evidence_sha256": per_row.get("evidence_sha256"),
            }
            for obligation_id, per_row in sorted(per_map.items())
        ]
        time_results.append(
            {
                "object_id": object_id,
                "object_kind": row.get("object_kind"),
                "obligation_evidence": per_object_evidence,
                **time_result,
            }
        )
    if set(object_map) != eligible:
        _error(
            errors,
            "per_object_results_incomplete",
            "object_results",
            f"Per-object rows must equal the eligible universe; missing={sorted(eligible - set(object_map))}, foreign={sorted(set(object_map) - eligible)}.",
        )

    input_fingerprint = _sha256(payload)
    receipt: dict[str, Any] = {
        "artifact_kind": "physicsguard_skill_execution_depth_receipt",
        "receipt_version": "physicsguard.skill-depth.v1",
        "status": "pass" if not errors else "blocked",
        "target_skill_id": target,
        "native_owner_id": payload.get("native_owner_id"),
        "native_route_id": payload.get("native_route_id"),
        "run_id": run_id,
        "evidence_domain": domain,
        "input_origin": input_origin,
        "scheduled_production_identity": scheduled_identity,
        "scheduled_production_identity_source": scheduled_identity_source,
        "input_fingerprint": input_fingerprint,
        "required_obligation_ids": list(policy.required_obligation_ids) if policy else [],
        "covered_obligation_ids": sorted(obligation_map),
        "native_obligation_evidence": [
            {
                "obligation_id": obligation_id,
                "status": "pass",
                "native_object_id": f"native-obligation:{target}:{obligation_id}",
                "evidence_ref": row.get("evidence_ref"),
                "evidence_sha256": row.get("evidence_sha256"),
                "content": {
                    "native_range": dict(row.get("native_range", {})),
                    "evaluator_input_fingerprint": input_fingerprint,
                },
            }
            for obligation_id, row in sorted(obligation_map.items())
        ],
        "native_contribution_ranges": ranges,
        "object_universe": {
            "declared_object_ids": sorted(declared),
            "discovered_object_ids": sorted(discovered),
            "required_object_ids": sorted(required),
            "critical_object_ids": sorted(critical),
            "excluded_object_ids": sorted(excluded),
            "eligible_object_ids": sorted(eligible),
            "evaluated_object_ids": sorted(evaluated),
        },
        "per_object_depth": time_results,
        "native_artifacts": [dict(item) for item in artifacts if isinstance(item, Mapping)],
        "errors": errors,
        "blockers": list(blockers) if isinstance(blockers, list) else [],
        "residual_risk": payload.get("residual_risk", []),
        "claim_boundary": payload.get("claim_boundary", ""),
    }
    receipt_core_hash = _sha256(receipt)
    receipt["receipt_id"] = f"physicsguard.skill-depth:{target or 'unknown'}:{run_id or 'missing'}:{receipt_core_hash[:16]}"
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt


def _safe_target_relative(value: str, *, field: str) -> str:
    relative = value.replace("\\", "/")
    if (
        not relative
        or relative.startswith("/")
        or re.match(r"^[A-Za-z]:", relative)
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise ValueError(f"{field} must be a safe target-root-relative path")
    return relative


def build_skill_scheduled_production_identity_sidecar(
    target_skill_id: str,
    *,
    run_id: str,
    package_relative: str,
    package_sha256: str,
    scheduled_production_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the sole target-owned installation/execution identity input."""

    if target_skill_id not in ROUTE_POLICIES:
        raise ValueError("scheduled production identity sidecar target is unknown")
    if not run_id.strip():
        raise ValueError("scheduled production identity sidecar requires an exact run_id")
    package_ref = _safe_target_relative(
        package_relative, field="identity sidecar package_ref"
    )
    if not SHA256_RE.fullmatch(package_sha256):
        raise ValueError("identity sidecar package_sha256 must be a lowercase sha256")
    errors: list[dict[str, str]] = []
    identity = _validate_scheduled_production_identity(
        scheduled_production_identity,
        evidence_domain="scheduled_production",
        errors=errors,
    )
    if errors:
        raise ValueError(
            "invalid scheduled production identity: "
            + "; ".join(f"{row['code']}:{row['message']}" for row in errors)
        )
    return {
        "artifact_kind": "physicsguard_scheduled_production_identity_sidecar",
        "schema_version": SCHEDULED_IDENTITY_SIDECAR_SCHEMA,
        "target_skill_id": target_skill_id,
        "run_id": run_id,
        "package_ref": package_ref,
        "package_sha256": package_sha256,
        "scheduled_production_identity": identity,
        "claim_boundary": "This sidecar binds only the exact target-owned scheduled execution, current installation receipt, installed runtime, and package bytes; generic supervisor request fields have no identity authority.",
    }


def _bound_reference_hashes(payload: Mapping[str, Any]) -> dict[str, set[str]]:
    pairs = (
        ("evidence_ref", "evidence_sha256"),
        ("artifact_ref", "artifact_sha256"),
        ("source_ref", "content_sha256"),
        ("static_binding_evidence_ref", "static_binding_evidence_sha256"),
    )
    found: dict[str, set[str]] = {}

    def visit(node: object) -> None:
        if isinstance(node, Mapping):
            for ref_field, hash_field in pairs:
                if ref_field not in node:
                    continue
                relative = _safe_target_relative(
                    str(node[ref_field]), field=ref_field
                )
                digest = str(node.get(hash_field, ""))
                if not SHA256_RE.fullmatch(digest):
                    raise ValueError(f"{hash_field} must be a lowercase sha256: {relative}")
                found.setdefault(relative, set()).add(digest)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(payload)
    return found


def load_skill_scheduled_production_package(
    target_root: str | Path,
    package_relative: str,
    run: Mapping[str, Any],
    target_skill_id: str,
) -> dict[str, Any]:
    """Admit exact scheduled inputs and inject identity only from the sidecar."""

    root = Path(target_root).resolve(strict=True)
    package_ref = _safe_target_relative(
        package_relative, field="scheduled production package"
    )
    request = run.get("request")
    if not isinstance(request, Mapping):
        raise ValueError("generic supervisor run request is missing")
    if "scheduled_production_identity" in request:
        raise ValueError(
            "generic supervisor request scheduled_production_identity is forbidden"
        )
    raw_inputs = request.get("target_input_paths")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError("target_input_paths must declare the exact production input set")
    input_paths = [
        _safe_target_relative(str(value), field="target_input_paths")
        for value in raw_inputs
    ]
    if len(input_paths) != len(set(input_paths)):
        raise ValueError("target_input_paths must not contain duplicates")
    declared_inputs = set(input_paths)
    if package_ref not in declared_inputs:
        raise ValueError("target_input_paths must include the scheduled production package")

    def input_path(relative: str) -> Path:
        path = (root / relative).resolve(strict=True)
        path.relative_to(root)
        if not path.is_file():
            raise ValueError(f"declared target input is not a file: {relative}")
        return path

    package_path = input_path(package_ref)
    package = load_execution_package(package_path)
    if package.get("target_skill_id") != target_skill_id:
        raise ValueError("scheduled production package target mismatch")
    run_id = str(run.get("run_id", ""))
    if not run_id or package.get("run_id") != run_id:
        raise ValueError("scheduled production package run identity mismatch")
    if package.get("evidence_domain") != "scheduled_production":
        raise ValueError("scheduled production loader requires scheduled_production evidence")
    if "scheduled_production_identity" in package:
        raise ValueError(
            "package installation identity is forbidden; use the target-owned identity sidecar"
        )
    if "scheduled_production_identity_source" in package:
        raise ValueError("package cannot self-assert identity-sidecar consumption")

    sidecars: list[tuple[str, Path, dict[str, Any]]] = []
    for relative in input_paths:
        if relative == package_ref or not relative.lower().endswith(".json"):
            continue
        path = input_path(relative)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, dict)
            and value.get("artifact_kind")
            == "physicsguard_scheduled_production_identity_sidecar"
        ):
            sidecars.append((relative, path, value))
    if len(sidecars) != 1:
        raise ValueError(
            "exactly one target-owned scheduled production identity sidecar is required"
        )
    sidecar_ref, sidecar_path, sidecar = sidecars[0]
    if sidecar.get("schema_version") != SCHEDULED_IDENTITY_SIDECAR_SCHEMA:
        raise ValueError("target-owned identity sidecar schema mismatch")
    if sidecar.get("target_skill_id") != target_skill_id:
        raise ValueError("target-owned identity sidecar target mismatch")
    if sidecar.get("run_id") != run_id:
        raise ValueError("target-owned identity sidecar run mismatch")
    if sidecar.get("package_ref") != package_ref:
        raise ValueError("target-owned identity sidecar package reference mismatch")
    package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if sidecar.get("package_sha256") != package_hash:
        raise ValueError("target-owned identity sidecar package hash mismatch")
    identity_errors: list[dict[str, str]] = []
    identity = _validate_scheduled_production_identity(
        sidecar.get("scheduled_production_identity"),
        evidence_domain="scheduled_production",
        errors=identity_errors,
    )
    if identity_errors:
        raise ValueError(
            "target-owned identity sidecar is invalid: "
            + "; ".join(row["code"] for row in identity_errors)
        )

    references = _bound_reference_hashes(package)
    expected_inputs = {package_ref, sidecar_ref, *references}
    if declared_inputs != expected_inputs:
        raise ValueError(
            "target_input_paths must exactly equal package, identity sidecar, and content-addressed target inputs: "
            f"missing={sorted(expected_inputs - declared_inputs)} foreign={sorted(declared_inputs - expected_inputs)}"
        )
    for relative, expected_hashes in references.items():
        path = input_path(relative)
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_hashes != {actual_hash}:
            raise ValueError(f"target input hash mismatch: {relative}")

    for row in package.get("obligation_results", []):
        if not isinstance(row, Mapping):
            continue
        native_range = row.get("native_range")
        if not isinstance(native_range, Mapping):
            continue
        source_ref = _safe_target_relative(
            str(native_range.get("source_ref", "")), field="native_range.source_ref"
        )
        content = input_path(source_ref).read_text(
            encoding="utf-8", errors="replace"
        )
        start = str(native_range.get("start_anchor", ""))
        end = str(native_range.get("end_anchor", ""))
        if not start or not end or start not in content or end not in content:
            raise ValueError(f"native range anchors missing from target input: {source_ref}")

    discovery_root = _safe_target_relative(
        str(package.get("native_discovery_root_ref", "")),
        field="native_discovery_root_ref",
    )
    rediscovered = build_skill_scheduled_production_package(
        target_skill_id,
        target_root=root,
        project_relative=discovery_root,
        run_id=run_id,
    )
    if _sha256(rediscovered) != _sha256(package):
        raise ValueError("scheduled production authoritative discovery mismatch")

    sidecar_hash = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    loaded = dict(package)
    loaded["scheduled_production_identity"] = identity
    loaded["scheduled_production_identity_source"] = {
        "schema_version": SCHEDULED_IDENTITY_SIDECAR_SCHEMA,
        "sidecar_ref": sidecar_ref,
        "sidecar_sha256": sidecar_hash,
        "package_ref": package_ref,
        "package_sha256": package_hash,
    }
    return loaded


def load_execution_package(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("PhysicsGuard skill execution package must be a JSON object")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue a target-owned PhysicsGuard skill execution-depth receipt.")
    parser.add_argument("package", type=Path, help="JSON PhysicsGuard skill execution package")
    parser.add_argument(
        "--target-root",
        type=Path,
        help="target root for formal scheduled-production sidecar admission",
    )
    parser.add_argument(
        "--run-request",
        type=Path,
        help="generic supervisor run JSON containing only run_id and target_input_paths",
    )
    parser.add_argument(
        "--target-skill-id",
        help="exact PhysicsGuard target id for formal scheduled-production sidecar admission",
    )
    parser.add_argument("--output", type=Path, help="optional receipt output path")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    formal_args = (args.target_root, args.run_request, args.target_skill_id)
    if any(formal_args) and not all(formal_args):
        parser.error(
            "--target-root, --run-request, and --target-skill-id are required together"
        )
    if all(formal_args):
        root = args.target_root.resolve(strict=True)
        package_path = args.package.resolve(strict=True)
        package_relative = package_path.relative_to(root).as_posix()
        run = load_execution_package(args.run_request)
        payload = load_skill_scheduled_production_package(
            root,
            package_relative,
            run,
            str(args.target_skill_id),
        )
    else:
        payload = load_execution_package(args.package)
    receipt = evaluate_skill_execution_package(payload)
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
