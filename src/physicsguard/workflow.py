"""Workflow governance helpers for PhysicsGuard AI debugging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
from typing import Any

import yaml

from physicsguard import __version__


PHYSICSGUARD_REPOSITORY = "https://github.com/liuyingxuvka/PhysicsGuard"
PHYSICSGUARD_WORKFLOW_SCHEMA_VERSION = "1.0"
DEFAULT_PROJECT_RECORD = Path(".physicsguard") / "project.yaml"
DEFAULT_ADOPTION_LOG = Path("docs") / "physicsguard_adoption_log.md"
DEFAULT_MODULE_LEDGER = Path(".physicsguard") / "module_equation_ledger.yaml"


@dataclass(frozen=True)
class WorkflowFinding:
    severity: str
    type: str
    message: str
    field: str | None = None
    count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "severity": self.severity,
            "type": self.type,
            "message": self.message,
        }
        if self.field is not None:
            result["field"] = self.field
        if self.count is not None:
            result["count"] = self.count
        return result


@dataclass(frozen=True)
class WorkflowReview:
    artifact_kind: str
    status: str
    ok: bool
    findings: tuple[WorkflowFinding, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "status": self.status,
            "ok": self.ok,
            "findings": [finding.to_dict() for finding in self.findings],
            "missing_inputs": list(self.missing_inputs),
            "next_actions": list(self.next_actions),
            "summary": self.summary,
        }


def installed_physicsguard_version() -> str:
    try:
        return importlib.metadata.version("physicsguard")
    except importlib.metadata.PackageNotFoundError:
        return __version__


def project_record_payload(root: Path) -> dict[str, Any]:
    version = installed_physicsguard_version()
    return {
        "physicsguard": {
            "repository": PHYSICSGUARD_REPOSITORY,
            "adopted_package_version": version,
            "schema_version": PHYSICSGUARD_WORKFLOW_SCHEMA_VERSION,
            "last_verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "last_verified_by": "PhysicsGuard project-adopt",
            "rules_path": "AGENTS.md",
        },
        "paths": {
            "adoption_log": DEFAULT_ADOPTION_LOG.as_posix(),
            "module_equation_ledger": DEFAULT_MODULE_LEDGER.as_posix(),
            "main_skill": "skill/physicsguard-ai-debugging/SKILL.md",
            "installed_skill_root": "~/.codex/skills",
        },
        "policy": {
            "require_model_understanding_preflight": True,
            "require_external_model_intake_for_observed_debugging": True,
            "require_test_file_contract_for_test_data": True,
            "require_project_evidence_registry_for_project_maps": True,
            "require_project_profile_for_project_evidence": True,
            "require_binding_expectations_for_project_evidence": True,
            "require_model_dataset_validation_for_validated_reuse": True,
            "require_database_catalog_for_multi_project_queries": True,
            "require_project_registry_reference_for_catalog_projects": True,
            "database_catalog_must_not_store_raw_data": True,
            "require_catalog_gap_check_before_cross_project_claims": True,
            "require_explicit_scope_before_cross_project_comparison": True,
            "require_signal_mapping_review_before_fault_claims": True,
            "require_closure_before_localization_claim": True,
            "require_project_closure_before_broad_claims": True,
            "ledger_is_navigation_not_physics_proof": True,
        },
        "skill_routes": [
            "physicsguard-ai-debugging",
            "physicsguard-project-adoption",
            "physicsguard-model-understanding-preflight",
            "physicsguard-test-file-contract-review",
            "physicsguard-project-evidence-registry",
            "physicsguard-model-dataset-validation",
            "physicsguard-database-catalog",
            "physicsguard-signal-mapping-review",
            "physicsguard-audit-closure",
            "physicsguard-candidate-model-blueprint",
            "physicsguard-model-library",
        ],
    }


def adopt_project(root: Path, action: str = "adopt") -> dict[str, Any]:
    root = root.resolve()
    record_path = root / DEFAULT_PROJECT_RECORD
    record_path.parent.mkdir(parents=True, exist_ok=True)
    payload = project_record_payload(root)
    if action == "upgrade":
        payload["physicsguard"]["last_verified_by"] = "PhysicsGuard project-upgrade"
    record_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    log_path = root / DEFAULT_ADOPTION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(
            "# PhysicsGuard Adoption Log\n\n"
            "This log records project-level PhysicsGuard workflow adoption, audits, "
            "closure evidence, and validation notes. It does not replace runtime "
            "PhysicsGuard CLI reports, FlowGuard checks, pytest, or closure evidence.\n",
            encoding="utf-8",
        )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n"
            f"## physicsguard-project-{action}\n\n"
            f"- Version: {payload['physicsguard']['adopted_package_version']}\n"
            f"- Schema: {payload['physicsguard']['schema_version']}\n"
            f"- Record: {DEFAULT_PROJECT_RECORD.as_posix()}\n"
            "- Boundary: workflow adoption only; not runtime audit proof.\n"
        )

    audit = audit_project(root)
    return {
        "artifact_type": "physicsguard_project_adoption",
        "action": action,
        "status": audit["status"],
        "written_files": [
            str(record_path),
            str(log_path),
        ],
        "record": DEFAULT_PROJECT_RECORD.as_posix(),
        "audit": audit,
    }


def audit_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    record_path = root / DEFAULT_PROJECT_RECORD
    if not record_path.exists():
        return {
            "artifact_type": "physicsguard_project_audit",
            "status": "fail",
            "ok": False,
            "errors": [f"missing project record: {DEFAULT_PROJECT_RECORD.as_posix()}"],
            "warnings": [],
        }
    data = _load_yaml(record_path)
    if not isinstance(data, dict):
        errors.append("project record root must be a mapping")
        data = {}

    section = data.get("physicsguard")
    if not isinstance(section, dict):
        errors.append("missing physicsguard section")
        section = {}
    if section.get("repository") != PHYSICSGUARD_REPOSITORY:
        errors.append("physicsguard.repository is missing or unexpected")
    if section.get("schema_version") != PHYSICSGUARD_WORKFLOW_SCHEMA_VERSION:
        errors.append("physicsguard.schema_version is missing or unexpected")
    adopted_version = section.get("adopted_package_version")
    installed_version = installed_physicsguard_version()
    if adopted_version != installed_version:
        warnings.append(
            f"project version {adopted_version!r} differs from installed version {installed_version!r}"
        )

    paths = data.get("paths") if isinstance(data.get("paths"), dict) else {}
    for key in ("adoption_log", "main_skill"):
        value = paths.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"paths.{key} must be a non-empty path")
        elif not (root / value).exists():
            errors.append(f"paths.{key} does not exist: {value}")
    ledger = paths.get("module_equation_ledger")
    if isinstance(ledger, str) and ledger.strip() and not (root / ledger).exists():
        warnings.append(f"module equation ledger not found yet: {ledger}")

    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("missing policy section")
    else:
        for key in (
            "require_model_understanding_preflight",
            "require_external_model_intake_for_observed_debugging",
            "require_test_file_contract_for_test_data",
            "require_project_evidence_registry_for_project_maps",
            "require_project_profile_for_project_evidence",
            "require_binding_expectations_for_project_evidence",
            "require_model_dataset_validation_for_validated_reuse",
            "require_database_catalog_for_multi_project_queries",
            "require_project_registry_reference_for_catalog_projects",
            "database_catalog_must_not_store_raw_data",
            "require_catalog_gap_check_before_cross_project_claims",
            "require_explicit_scope_before_cross_project_comparison",
            "require_signal_mapping_review_before_fault_claims",
            "require_closure_before_localization_claim",
            "require_project_closure_before_broad_claims",
        ):
            if policy.get(key) is not True:
                errors.append(f"policy.{key} must be true")

    status = "fail" if errors else "pass_with_gaps" if warnings else "pass"
    return {
        "artifact_type": "physicsguard_project_audit",
        "status": status,
        "ok": not errors,
        "record": DEFAULT_PROJECT_RECORD.as_posix(),
        "installed_package_version": installed_version,
        "adopted_package_version": adopted_version,
        "schema_version": PHYSICSGUARD_WORKFLOW_SCHEMA_VERSION,
        "errors": errors,
        "warnings": warnings,
    }


def review_model_understanding_preflight(path: Path) -> WorkflowReview:
    data = _load_yaml(path)
    missing: list[str] = []
    findings: list[WorkflowFinding] = []
    if not isinstance(data, dict):
        return _invalid_yaml_review("model_understanding_preflight")
    root = data.get("physicsguard_understanding")
    if not isinstance(root, dict):
        missing.append("physicsguard_understanding")
        root = {}

    _require_text(root, "visible_symptom", missing)
    _require_text(root, "physical_boundary", missing)
    _require_text(root, "first_audit_level", missing)
    _require_list(root, "subsystem_blocks", missing)
    _require_list(root, "conserved_quantities", missing)
    _require_list(root, "key_interfaces", missing)
    _require_list(root, "stop_conditions", missing)
    _require_mapping_or_list(root, "expected_units", missing)
    _require_list(root, "known_assumptions", missing)
    _require_list(root, "uncertain_mappings", missing, allow_empty=True)

    external = root.get("external_model")
    if not isinstance(external, dict):
        missing.append("external_model")
        external = {}
    for field_name in ("model_name", "tool", "source_of_truth"):
        _require_text(external, field_name, missing, prefix="external_model")

    uncertain = root.get("uncertain_mappings")
    if isinstance(uncertain, list) and uncertain:
        findings.append(
            WorkflowFinding(
                "warning",
                "uncertain_mappings_present",
                "Preflight contains uncertain mappings that must be reviewed before fault claims.",
                "uncertain_mappings",
                len(uncertain),
            )
        )

    status = "partial" if missing or findings else "pass"
    return WorkflowReview(
        artifact_kind="model_understanding_preflight",
        status=status,
        ok=not missing,
        findings=tuple(findings),
        missing_inputs=tuple(missing),
        next_actions=tuple(_preflight_next_actions(missing, findings)),
        summary={
            "visible_symptom": root.get("visible_symptom"),
            "physical_boundary": root.get("physical_boundary"),
            "subsystem_count": len(root.get("subsystem_blocks", []) if isinstance(root.get("subsystem_blocks"), list) else []),
            "safe_claim": "Preflight captures low-fidelity understanding only; it is not residual validation.",
        },
    )


def review_external_model_intake(path: Path) -> WorkflowReview:
    data = _load_yaml(path)
    missing: list[str] = []
    findings: list[WorkflowFinding] = []
    if not isinstance(data, dict):
        return _invalid_yaml_review("external_model_intake")
    root = data.get("external_model_snapshot")
    if not isinstance(root, dict):
        missing.append("external_model_snapshot")
        root = {}

    for field_name in ("model_name", "tool", "model_version", "scenario", "export_time", "observed_file"):
        _require_text(root, field_name, missing)
    signals = root.get("signals")
    if not isinstance(signals, list) or not signals:
        missing.append("signals")
        signals = []

    review_required = 0
    stale_count = 0
    for index, signal in enumerate(signals):
        label = f"signals[{index}]"
        if not isinstance(signal, dict):
            missing.append(label)
            continue
        for field_name in (
            "external_signal",
            "physicsguard_variable",
            "unit_from_source",
            "expected_si_unit",
            "mapping_confidence",
        ):
            _require_text(signal, field_name, missing, prefix=label)
        _require_list(signal, "stale_when", missing, prefix=label)
        if signal.get("review_required") is True:
            review_required += 1
        confidence = str(signal.get("mapping_confidence", "")).lower()
        if confidence in {"low", "review_required", "uncertain"}:
            review_required += 1
        if not signal.get("conversion_note"):
            review_required += 1
        stale_when = signal.get("stale_when")
        if isinstance(stale_when, list) and stale_when:
            stale_count += 1

    if review_required:
        findings.append(
            WorkflowFinding(
                "warning",
                "signal_mapping_review_required",
                "One or more signal mappings need review before model fault claims.",
                "signals",
                review_required,
            )
        )
    status = "partial" if missing or findings else "pass"
    return WorkflowReview(
        artifact_kind="external_model_intake",
        status=status,
        ok=not missing,
        findings=tuple(findings),
        missing_inputs=tuple(missing),
        next_actions=(
            ("review_signal_mappings_before_fault_claims",)
            if review_required
            else ("run_physicsguard_hierarchy_evaluate_with_observed_snapshot",)
        ),
        summary={
            "model_name": root.get("model_name"),
            "tool": root.get("tool"),
            "signal_count": len(signals),
            "review_required_count": review_required,
            "stale_trigger_count": stale_count,
            "semantics": "Intake records mapping evidence only; it does not convert observed values.",
        },
    )


def _invalid_yaml_review(kind: str) -> WorkflowReview:
    return WorkflowReview(
        artifact_kind=kind,
        status="fail",
        ok=False,
        findings=(WorkflowFinding("error", "invalid_yaml", "Workflow file must contain a YAML mapping."),),
        missing_inputs=("yaml_mapping",),
        next_actions=("provide_valid_yaml_mapping",),
    )


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _require_text(
    data: dict[str, Any],
    field_name: str,
    missing: list[str],
    prefix: str | None = None,
) -> None:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        missing.append(f"{prefix + '.' if prefix else ''}{field_name}")


def _require_list(
    data: dict[str, Any],
    field_name: str,
    missing: list[str],
    prefix: str | None = None,
    allow_empty: bool = False,
) -> None:
    value = data.get(field_name)
    if not isinstance(value, list) or (not allow_empty and not value):
        missing.append(f"{prefix + '.' if prefix else ''}{field_name}")


def _require_mapping_or_list(
    data: dict[str, Any],
    field_name: str,
    missing: list[str],
) -> None:
    value = data.get(field_name)
    if not isinstance(value, (dict, list)) or not value:
        missing.append(field_name)


def _preflight_next_actions(
    missing: list[str],
    findings: list[WorkflowFinding],
) -> list[str]:
    actions: list[str] = []
    if missing:
        actions.append("complete_model_understanding_preflight")
    if findings:
        actions.append("review_uncertain_mappings_before_fault_claims")
    if not actions:
        actions.append("create_or_select_level_0_physicsguard_audit")
    return actions


__all__ = [
    "DEFAULT_PROJECT_RECORD",
    "PHYSICSGUARD_REPOSITORY",
    "PHYSICSGUARD_WORKFLOW_SCHEMA_VERSION",
    "WorkflowFinding",
    "WorkflowReview",
    "adopt_project",
    "audit_project",
    "installed_physicsguard_version",
    "review_external_model_intake",
    "review_model_understanding_preflight",
]
