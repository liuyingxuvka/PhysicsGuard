"""Database-level catalog checks, maps, and safe query reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal, Optional
from uuid import uuid4

import yaml

from physicsguard import __version__
from physicsguard.core.parameter_coverage import ContractFinding, ContractReview
from physicsguard.core.project_evidence import (
    SCAN_EXCLUDED_DIRS,
    build_project_evidence_map,
    check_evidence_gaps,
)
from physicsguard.io.test_file_contract_loader import (
    load_database_catalog,
    load_database_model_template_index,
    load_database_policy,
    load_database_project_intake_plan,
    load_model_library_index,
    load_yaml_mapping,
)
from physicsguard.schema.database_catalog import (
    CandidateKind,
    CatalogProjectRecordSpec,
    DatabaseCatalogCandidateSpec,
    DatabaseCatalogGapSpec,
    DatabaseCatalogSpec,
    DatabaseHistoryEventSpec,
    DatabaseLifecycleArtifactsSpec,
    DatabaseMaintenanceReportSpec,
    DatabaseModelTemplateIndexSpec,
    DatabasePolicySpec,
    DatabaseProjectAdmissionSpec,
    DatabaseProjectIntakePlanSpec,
    DatabaseProjectLifecycleState,
)
from physicsguard.schema.project_evidence import GapSeverity
from physicsguard.schema.variable import ensure_non_empty


PHYSICSGUARD_REPOSITORY = "https://github.com/liuyingxuvka/PhysicsGuard"
DEFAULT_DATABASE_ARTIFACTS = DatabaseLifecycleArtifactsSpec()
ACTIVE_LIFECYCLE_STATES = {"active_registered", "active_validated", "active_reusable"}
INACTIVE_LIFECYCLE_STATES = {"archived", "deprecated", "superseded", "rejected"}
RAW_DATA_KEYS = {
    "raw_data",
    "raw_dataset",
    "raw_rows",
    "data_rows",
    "rows",
    "samples",
    "measurements",
    "time_series_values",
}
YAML_SUFFIXES = {".yaml", ".yml"}


@dataclass(frozen=True)
class DatabaseCatalogScanReport:
    artifact_kind: str
    status: str
    ok: bool
    candidates: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseCatalogGapReport:
    artifact_kind: str
    status: str
    ok: bool
    catalog_id: str
    blocking_gaps: list[dict[str, Any]] = field(default_factory=list)
    review_gaps: list[dict[str, Any]] = field(default_factory=list)
    optional_gaps: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseCatalogRefreshReport:
    artifact_kind: str
    status: str
    ok: bool
    catalog_id: str
    refreshed_projects: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseMapReport:
    artifact_kind: str
    status: str
    ok: bool
    catalog_id: str
    catalog_name: Optional[str]
    projects: list[dict[str, Any]]
    model_libraries: list[dict[str, Any]]
    indexes: dict[str, Any]
    gaps: dict[str, Any]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseQueryReport:
    artifact_kind: str
    status: str
    ok: bool
    catalog_id: str
    filters: dict[str, Any]
    matches: list[dict[str, Any]]
    gaps: dict[str, Any]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseLifecycleOperationReport:
    artifact_kind: str
    operation: str
    status: str
    ok: bool
    dry_run: bool = True
    applied: bool = False
    written_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    history_events: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseMaintenanceReport:
    artifact_kind: str
    status: str
    ok: bool
    database_root: str
    catalog_path: str
    policy_path: Optional[str] = None
    blocking_gaps: list[dict[str, Any]] = field(default_factory=list)
    review_gaps: list[dict[str, Any]] = field(default_factory=list)
    optional_gaps: list[dict[str, Any]] = field(default_factory=list)
    project_summaries: list[dict[str, Any]] = field(default_factory=list)
    lifecycle_artifacts: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_database_catalog(path: str | Path) -> ContractReview:
    catalog_path = Path(path)
    catalog = load_database_catalog(catalog_path)
    findings: list[ContractFinding] = []

    if catalog.policies.forbid_raw_data_payloads and _contains_raw_data_payload(catalog.metadata):
        findings.append(
            ContractFinding(
                severity="error",
                type="database_catalog_raw_data_payload",
                message="database catalog metadata must not embed raw test data payloads",
                target=catalog.catalog_id,
            )
        )

    for project in catalog.projects:
        findings.extend(_project_record_findings(catalog_path, project, catalog))
    for library in catalog.model_library_indexes:
        library_path = _resolve_path(catalog_path.parent, library.path)
        if not library_path.exists():
            findings.append(
                ContractFinding(
                    severity="error",
                    type="database_catalog_model_library_missing",
                    message="catalog model-library reference path is missing",
                    target=str(library_path),
                )
            )
            continue
        try:
            load_model_library_index(library_path)
        except Exception as exc:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="database_catalog_model_library_invalid",
                    message=f"catalog model-library reference is invalid: {exc}",
                    target=str(library_path),
                )
            )
    status = _status(findings)
    return ContractReview(
        artifact_kind="database_catalog",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "catalog_id": catalog.catalog_id,
            "catalog_name": catalog.catalog_name,
            "project_count": len(catalog.projects),
            "model_library_index_count": len(catalog.model_library_indexes),
            "semantics": (
                "database catalogs are cross-project navigation maps; they do not "
                "store raw datasets or prove project comparability"
            ),
        },
        next_actions=_next_actions(findings),
    )


def scan_database_catalog_candidates(
    root: str | Path,
    catalog_path: str | Path | None = None,
) -> DatabaseCatalogScanReport:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"scan root does not exist: {root_path}")
    catalog = load_database_catalog(catalog_path) if catalog_path else None
    catalog_base = Path(catalog_path).parent if catalog_path else root_path
    registered = _registered_catalog_paths(catalog, catalog_base) if catalog else {}
    candidates: list[DatabaseCatalogCandidateSpec] = []
    findings: list[ContractFinding] = []

    for path in sorted(item for item in root_path.rglob("*") if item.is_file()):
        if _is_excluded(path) or path.suffix.lower() not in YAML_SUFFIXES:
            continue
        kind, reason = _classify_catalog_candidate(path)
        if kind is None:
            continue
        normalized = _normalize_path(path)
        matched = registered.get(normalized)
        candidates.append(
            DatabaseCatalogCandidateSpec(
                path=str(path.relative_to(root_path) if path.is_relative_to(root_path) else path),
                candidate_kind=kind,
                reason=reason,
                registered=matched is not None,
                matched_id=matched,
            )
        )

    unregistered = [item for item in candidates if not item.registered]
    for item in unregistered:
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_catalog_candidate_unregistered",
                message="scanner found a candidate project or model-library artifact not registered in the database catalog",
                target=item.path,
                details={"candidate_kind": item.candidate_kind, "reason": item.reason},
            )
        )
    status = "partial" if unregistered else "pass"
    return DatabaseCatalogScanReport(
        artifact_kind="database_catalog_scan",
        status=status,
        ok=status == "pass",
        candidates=[item.model_dump(mode="json") for item in candidates],
        findings=[asdict(item) for item in findings],
        summary={
            "root": str(root_path),
            "catalog": str(catalog_path) if catalog_path else None,
            "candidate_count": len(candidates),
            "registered_candidate_count": len(candidates) - len(unregistered),
            "unregistered_candidate_count": len(unregistered),
            "semantics": "database catalog scan is read-only and does not mutate catalog files",
        },
    )


def refresh_database_catalog(path: str | Path) -> DatabaseCatalogRefreshReport:
    catalog_path = Path(path)
    catalog = load_database_catalog(catalog_path)
    refreshed: list[dict[str, Any]] = []
    findings: list[ContractFinding] = []
    for project in catalog.projects:
        summary, project_findings = _project_summary(catalog_path, project)
        refreshed.append(summary)
        findings.extend(project_findings)
    status = _status(findings)
    return DatabaseCatalogRefreshReport(
        artifact_kind="database_catalog_refresh",
        status=status,
        ok=status == "pass",
        catalog_id=catalog.catalog_id,
        refreshed_projects=refreshed,
        findings=[asdict(item) for item in findings],
        summary={
            "project_count": len(catalog.projects),
            "refreshed_project_count": len([item for item in refreshed if item.get("registry_loaded")]),
            "semantics": "refresh is read-only; write updated catalog summaries explicitly after review",
        },
    )


def check_database_catalog_gaps(path: str | Path) -> DatabaseCatalogGapReport:
    catalog_path = Path(path)
    catalog = load_database_catalog(catalog_path)
    gaps = _collect_catalog_gaps(catalog_path, catalog)
    blocking = [gap for gap in gaps if gap.severity == "blocking"]
    review = [gap for gap in gaps if gap.severity == "review"]
    optional = [gap for gap in gaps if gap.severity == "optional"]
    status = "fail" if blocking else "partial" if review else "pass"
    return DatabaseCatalogGapReport(
        artifact_kind="database_catalog_gap_report",
        status=status,
        ok=status == "pass",
        catalog_id=catalog.catalog_id,
        blocking_gaps=[gap.model_dump(mode="json") for gap in blocking],
        review_gaps=[gap.model_dump(mode="json") for gap in review],
        optional_gaps=[gap.model_dump(mode="json") for gap in optional],
        findings=[],
        summary={
            "blocking_gap_count": len(blocking),
            "review_gap_count": len(review),
            "optional_gap_count": len(optional),
            "semantics": (
                "blocking database gaps prevent broad database-level validation, reuse, "
                "or comparison claims; review gaps remain visible for scoped search"
            ),
        },
    )


def build_database_map(path: str | Path) -> DatabaseMapReport:
    catalog_path = Path(path)
    catalog = load_database_catalog(catalog_path)
    refresh = refresh_database_catalog(catalog_path)
    gap_report = check_database_catalog_gaps(catalog_path)
    projects = refresh.refreshed_projects
    indexes = _build_indexes(projects)
    model_libraries = _model_library_entries(catalog_path, catalog)
    status = "fail" if gap_report.blocking_gaps else "partial" if gap_report.review_gaps else "pass"
    return DatabaseMapReport(
        artifact_kind="database_catalog_map",
        status=status,
        ok=status == "pass",
        catalog_id=catalog.catalog_id,
        catalog_name=catalog.catalog_name,
        projects=projects,
        model_libraries=model_libraries,
        indexes=indexes,
        gaps={
            "blocking": gap_report.blocking_gaps,
            "review": gap_report.review_gaps,
            "optional": gap_report.optional_gaps,
        },
        summary={
            "project_count": len(projects),
            "project_with_registry_count": sum(1 for item in projects if item.get("registry_loaded")),
            "tag_count": len(indexes["tags"]),
            "quantity_count": len(indexes["quantities"]),
            "model_target_count": len(indexes["model_targets"]),
            "model_library_index_count": len(model_libraries),
            "semantics": (
                "database maps are search and onboarding summaries; they do not replace "
                "project evidence maps, validation reports, or comparison scope review"
            ),
        },
    )


def query_database_catalog(
    path: str | Path,
    *,
    tag: str | None = None,
    quantity: str | None = None,
    component: str | None = None,
    model_target: str | None = None,
    has_validation: bool | None = None,
    has_test_data: bool | None = None,
    project_status: str | None = None,
    include_inactive: bool = False,
) -> DatabaseQueryReport:
    database_map = build_database_map(path)
    filters = {
        "tag": tag,
        "quantity": quantity,
        "component": component,
        "model_target": model_target,
        "has_validation": has_validation,
        "has_test_data": has_test_data,
        "project_status": project_status,
        "include_inactive": include_inactive if include_inactive else None,
    }
    active_filters = {key: value for key, value in filters.items() if value is not None}
    matches = [
        project
        for project in database_map.projects
        if include_inactive
        or project_status is not None
        or project.get("lifecycle_state") not in {"archived", "deprecated", "superseded", "rejected"}
        if _project_matches(project, active_filters)
    ]
    return DatabaseQueryReport(
        artifact_kind="database_catalog_query",
        status=database_map.status,
        ok=database_map.ok,
        catalog_id=database_map.catalog_id,
        filters=active_filters,
        matches=matches,
        gaps=database_map.gaps,
        summary={
            "match_count": len(matches),
            "project_count": len(database_map.projects),
            "semantics": (
                "query matches are related candidates; inspect project registries, gap "
                "reports, and validation evidence before broad technical comparisons"
            ),
        },
    )


def initialize_database_root(
    root: str | Path,
    *,
    database_id: str = "local_physicsguard_database",
    database_name: str | None = None,
    apply: bool = False,
    overwrite: bool = False,
    actor: str = "PhysicsGuard AI",
) -> DatabaseLifecycleOperationReport:
    """Initialize an explicit local database root, dry-run by default."""

    root_path = Path(root)
    artifacts = DEFAULT_DATABASE_ARTIFACTS
    targets = _database_artifact_paths(root_path, artifacts)
    findings: list[ContractFinding] = []
    written: list[str] = []
    skipped: list[str] = []
    event = _history_event(
        "database_created",
        actor=actor,
        target_artifact=str(root_path),
        reason="initialize explicit PhysicsGuard database root",
        apply=apply,
        affected_paths=[str(path) for path in targets.values()],
    )

    payloads = {
        "database_policy": DatabasePolicySpec(
            database_id=database_id,
            database_name=database_name or database_id,
            physicsguard_version=__version__,
            scope_summary="Explicit local PhysicsGuard database. Update this scope before broad use.",
            maintainer=actor,
        ).model_dump(mode="json"),
        "database_catalog": DatabaseCatalogSpec(
            catalog_id=database_id,
            catalog_name=database_name or database_id,
            physicsguard_version=__version__,
            created_at=_now(),
            updated_at=_now(),
            description="Explicit local PhysicsGuard database catalog. It is a map, not a raw-data store.",
            catalog_roots=["."],
            database_policy=artifacts.database_policy,
            database_history=artifacts.database_history,
            database_maintenance_report=artifacts.database_maintenance_report,
            model_template_index=artifacts.model_template_index,
        ).model_dump(mode="json"),
        "database_maintenance_report": DatabaseMaintenanceReportSpec(
            artifact_kind="database_maintenance_report",
            status="partial",
            ok=False,
            database_root=str(root_path),
            catalog_path=artifacts.database_catalog,
            policy_path=artifacts.database_policy,
            summary={"semantics": "Initial placeholder; run database audit after adding projects."},
            next_actions=["Run database audit after project intake."],
        ).model_dump(mode="json"),
        "model_template_index": DatabaseModelTemplateIndexSpec(
            index_id=f"{database_id}_model_templates",
            database_id=database_id,
            physicsguard_version=__version__,
        ).model_dump(mode="json"),
    }
    markdown = _render_handoff_markdown(
        database_root=root_path,
        catalog=None,
        maintenance=None,
        policy=DatabasePolicySpec(
            database_id=database_id,
            database_name=database_name or database_id,
            physicsguard_version=__version__,
            scope_summary="Explicit local PhysicsGuard database. Update this scope before broad use.",
            maintainer=actor,
        ),
    )
    status_markdown = _render_status_markdown(database_id, [], [], "Initial database root; run audit after intake.")

    if not apply:
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_init",
            status="dry_run",
            ok=True,
            dry_run=True,
            applied=False,
            written_files=[],
            skipped_files=[str(path) for path in targets.values() if path.exists()],
            history_events=[event.model_dump(mode="json")],
            findings=[],
            summary={
                "database_root": str(root_path),
                "would_create": [str(path) for path in targets.values() if overwrite or not path.exists()],
                "semantics": "dry-run only; pass apply=True or CLI --apply to write database files",
            },
            next_actions=["Review the dry-run file list, then rerun with explicit apply intent if correct."],
        )

    root_path.mkdir(parents=True, exist_ok=True)
    for key, path in targets.items():
        if path.exists() and not overwrite:
            skipped.append(str(path))
            continue
        if key in payloads:
            _write_yaml(path, payloads[key])
        elif key == "database_readme":
            path.write_text(markdown, encoding="utf-8")
        elif key == "database_status":
            path.write_text(status_markdown, encoding="utf-8")
        elif key == "database_history":
            path.write_text("", encoding="utf-8")
        written.append(str(path))
    _append_history(targets["database_history"], event)
    written.append(str(targets["database_history"]))
    status = "pass" if not findings else _status(findings)
    return DatabaseLifecycleOperationReport(
        artifact_kind="database_lifecycle_operation",
        operation="database_init",
        status=status,
        ok=status == "pass",
        dry_run=False,
        applied=True,
        written_files=sorted(set(written)),
        skipped_files=skipped,
        history_events=[event.model_dump(mode="json")],
        findings=[asdict(item) for item in findings],
        summary={
            "database_root": str(root_path),
            "database_id": database_id,
            "semantics": "explicit local database root initialized; not a hidden global database",
        },
        next_actions=["Run database intake-plan for projects that should enter this database."],
    )


def check_database_policy(path: str | Path) -> ContractReview:
    policy_path = Path(path)
    policy = load_database_policy(policy_path)
    findings: list[ContractFinding] = []
    if policy.forbid_raw_data_payloads and _contains_raw_data_payload(policy.metadata):
        findings.append(
            ContractFinding(
                severity="error",
                type="database_policy_raw_data_payload",
                message="database policy metadata must not embed raw test data payloads",
                target=policy.database_id,
            )
        )
    if not policy.physicsguard_repository:
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_policy_repository_missing",
                message="database policy should reference the PhysicsGuard repository or record why it is unknown",
                target=policy.database_id,
            )
        )
    status = _status(findings)
    return ContractReview(
        artifact_kind="database_policy",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "database_id": policy.database_id,
            "database_name": policy.database_name,
            "physicsguard_repository": policy.physicsguard_repository,
            "semantics": "database policy governs explicit local database lifecycle; it is not validation proof",
        },
        next_actions=_next_actions(findings),
    )


def check_database_model_template_index(path: str | Path) -> ContractReview:
    index_path = Path(path)
    index = load_database_model_template_index(index_path)
    findings: list[ContractFinding] = []
    base_dir = index_path.parent
    for template in index.templates:
        if not template.template_path and not template.model_library_entry_id:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="database_model_template_source_missing",
                    message="model template should reference a template file or model-library entry",
                    target=template.template_id,
                )
            )
        if template.template_path and not _resolve_path(base_dir, template.template_path).exists():
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="database_model_template_path_missing",
                    message="model template path does not exist locally",
                    target=template.template_id,
                    details={"path": template.template_path},
                )
            )
        if not template.known_limits:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="database_model_template_limits_missing",
                    message="model template should record known limits before reuse guidance",
                    target=template.template_id,
                )
            )
        if not template.validation_reports and template.review_state not in {"review_required", "source_missing"}:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="database_model_template_validation_boundary_missing",
                    message="model template should reference validation reports or mark review/source-missing state",
                    target=template.template_id,
                )
            )
    for library in index.model_library_indexes:
        library_path = _resolve_path(base_dir, library.path)
        if not library_path.exists():
            findings.append(
                ContractFinding(
                    severity="error",
                    type="database_model_template_library_missing",
                    message="referenced model-library index does not exist",
                    target=str(library_path),
                )
            )
    status = _status(findings)
    return ContractReview(
        artifact_kind="database_model_template_index",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "index_id": index.index_id,
            "template_count": len(index.templates),
            "model_library_index_count": len(index.model_library_indexes),
            "semantics": "model templates are reuse starting points, not project-specific validation proof",
        },
        next_actions=_next_actions(findings),
    )


def plan_database_project_intake(
    database_root: str | Path,
    project_root: str | Path,
    *,
    catalog_path: str | Path | None = None,
    project_id: str | None = None,
    requested_state: DatabaseProjectLifecycleState = "candidate",
) -> DatabaseLifecycleOperationReport:
    root_path = Path(database_root)
    project_path = Path(project_root)
    catalog = Path(catalog_path) if catalog_path else root_path / DEFAULT_DATABASE_ARTIFACTS.database_catalog
    findings: list[ContractFinding] = []
    registry_path = _find_project_evidence_registry(project_path)
    adoption_path = project_path / ".physicsguard" / "project.yaml"
    inferred_project_id = project_id or project_path.name
    project_name: str | None = None
    gap_status = "unknown"
    if registry_path:
        try:
            registry_data = load_yaml_mapping(registry_path)
            inferred_project_id = project_id or str(registry_data.get("project_id") or inferred_project_id)
            profile = registry_data.get("project_profile") if isinstance(registry_data.get("project_profile"), dict) else {}
            project_name = profile.get("project_name") if isinstance(profile.get("project_name"), str) else None
            gap_report = check_evidence_gaps(registry_path)
            gap_status = gap_report.status
            if gap_report.blocking_gaps:
                findings.append(
                    ContractFinding(
                        severity="error" if requested_state in {"active_registered", "active_validated", "active_reusable"} else "warning",
                        type="database_intake_project_blocking_gaps",
                        message="project evidence registry has blocking gaps",
                        target=inferred_project_id,
                        details={"blocking_gap_count": len(gap_report.blocking_gaps)},
                    )
                )
        except Exception as exc:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="database_intake_registry_invalid",
                    message=f"project evidence registry could not be checked: {exc}",
                    target=str(registry_path),
                )
            )
    elif requested_state in {"active_registered", "active_validated", "active_reusable"}:
        findings.append(
            ContractFinding(
                severity="error",
                type="database_intake_registry_missing",
                message="active project intake requires a project evidence registry or explicit placeholder state",
                target=inferred_project_id,
            )
        )
    if not adoption_path.exists() and requested_state in {"active_registered", "active_validated", "active_reusable"}:
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_intake_project_adoption_missing",
                message="active database project should have a project-level PhysicsGuard adoption record or missing reason",
                target=inferred_project_id,
            )
        )
    plan = DatabaseProjectIntakePlanSpec(
        database_root=str(root_path),
        catalog_path=str(catalog),
        project_id=inferred_project_id,
        requested_state=requested_state,
        project_root=str(project_path),
        project_name=project_name,
        project_evidence_registry=str(_relative_or_absolute(registry_path, catalog.parent)) if registry_path else None,
        registry_missing_reason=None if registry_path else "project evidence registry not found during intake scan",
        project_adoption_record=str(_relative_or_absolute(adoption_path, catalog.parent)) if adoption_path.exists() else None,
        project_adoption_missing_reason=None if adoption_path.exists() else "project adoption record not found during intake scan",
        admission_reason="intake plan generated from explicit database project intake",
        metadata={"evidence_gap_status": gap_status},
    )
    status = _status(findings)
    return DatabaseLifecycleOperationReport(
        artifact_kind="database_lifecycle_operation",
        operation="database_intake_plan",
        status="dry_run" if status == "pass" else status,
        ok=status in {"pass", "partial"},
        dry_run=True,
        applied=False,
        written_files=[],
        findings=[asdict(item) for item in findings],
        summary={
            "intake_plan": plan.model_dump(mode="json"),
            "project_level_requirements_met": status == "pass",
            "semantics": "intake planning is read-only; use database admit with explicit apply to modify the catalog",
        },
        next_actions=[
            "Review the intake plan.",
            "Use placeholder/candidate state for incomplete projects or fix blocking gaps before active admission.",
        ],
    )


def admit_database_project(
    plan_path: str | Path,
    *,
    apply: bool = False,
    actor: str = "PhysicsGuard AI",
) -> DatabaseLifecycleOperationReport:
    plan = load_database_project_intake_plan(plan_path)
    catalog_path = Path(plan.catalog_path)
    catalog = load_database_catalog(catalog_path)
    findings: list[ContractFinding] = []
    active_states = {"active_registered", "active_validated", "active_reusable"}
    if plan.requested_state in active_states and not plan.project_evidence_registry:
        findings.append(
            ContractFinding(
                severity="error",
                type="database_admit_registry_missing",
                message="active project admission requires project_evidence_registry",
                target=plan.project_id,
            )
        )
    if plan.requested_state == "active_validated":
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_admit_validation_review_required",
                message="active_validated admission should be reviewed against validation reports",
                target=plan.project_id,
            )
        )
    status = _status(findings)
    if not apply:
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_admit_project",
            status="dry_run" if status == "pass" else status,
            ok=status != "fail",
            dry_run=True,
            applied=False,
            findings=[asdict(item) for item in findings],
            summary={
                "project_id": plan.project_id,
                "requested_state": plan.requested_state,
                "catalog_path": str(catalog_path),
                "semantics": "dry-run only; pass apply=True or CLI --apply to update the catalog and history",
            },
            next_actions=["Review findings, then rerun with explicit apply intent if admission is correct."],
        )
    if status == "fail":
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_admit_project",
            status="fail",
            ok=False,
            dry_run=False,
            applied=False,
            findings=[asdict(item) for item in findings],
            summary={"project_id": plan.project_id, "catalog_path": str(catalog_path)},
            next_actions=_next_actions(findings),
        )
    catalog_data = catalog.model_dump(mode="json")
    record = _project_record_from_intake_plan(plan, actor=actor)
    replaced = False
    for index, item in enumerate(catalog_data["projects"]):
        if item["project_id"] == plan.project_id:
            catalog_data["projects"][index] = record
            replaced = True
            break
    if not replaced:
        catalog_data["projects"].append(record)
    catalog_data["updated_at"] = _now()
    DatabaseCatalogSpec.model_validate(catalog_data)
    _write_yaml(catalog_path, catalog_data)
    history_path = _history_path_for_catalog(catalog_path, catalog)
    event = _history_event(
        "project_admitted",
        actor=actor,
        target_project_id=plan.project_id,
        reason=plan.admission_reason or "project admitted through database intake",
        apply=True,
        before_state=None if not replaced else "updated_existing_record",
        after_state=plan.requested_state,
        affected_paths=[str(catalog_path), str(history_path)],
    )
    _append_history(history_path, event)
    return DatabaseLifecycleOperationReport(
        artifact_kind="database_lifecycle_operation",
        operation="database_admit_project",
        status="pass",
        ok=True,
        dry_run=False,
        applied=True,
        written_files=[str(catalog_path), str(history_path)],
        history_events=[event.model_dump(mode="json")],
        findings=[asdict(item) for item in findings],
        summary={"project_id": plan.project_id, "catalog_path": str(catalog_path), "replaced": replaced},
        next_actions=["Run database audit and render handoff after admission."],
    )


def audit_database_maintenance(
    database_root: str | Path,
    *,
    catalog_path: str | Path | None = None,
    policy_path: str | Path | None = None,
) -> DatabaseMaintenanceReport:
    root_path = Path(database_root)
    catalog_file = Path(catalog_path) if catalog_path else root_path / DEFAULT_DATABASE_ARTIFACTS.database_catalog
    policy_file = Path(policy_path) if policy_path else root_path / DEFAULT_DATABASE_ARTIFACTS.database_policy
    gaps: list[DatabaseCatalogGapSpec] = []
    lifecycle = _lifecycle_artifact_status(root_path)
    for name, item in lifecycle.items():
        if not item["exists"]:
            severity: GapSeverity = "blocking" if name in {"database_policy", "database_catalog", "database_history"} else "review"
            gaps.append(
                _gap(
                    f"lifecycle_{name}_missing",
                    severity,
                    "lifecycle_artifact_missing",
                    item["path"],
                    f"database lifecycle artifact is missing: {name}",
                    None,
                    ["database_lifecycle_policy"],
                    [f"create {item['path']} or run database init"],
                )
            )
    project_summaries: list[dict[str, Any]] = []
    if catalog_file.exists():
        catalog = load_database_catalog(catalog_file)
        project_summaries = refresh_database_catalog(catalog_file).refreshed_projects
        gaps.extend(_collect_catalog_gaps(catalog_file, catalog))
        for project in catalog.projects:
            gaps.extend(_lifecycle_project_gaps(catalog_file, project))
    else:
        catalog = None
    if policy_file.exists():
        try:
            policy_review = check_database_policy(policy_file)
            for finding in policy_review.findings:
                severity: GapSeverity = "blocking" if finding.severity == "error" else "review"
                gaps.append(
                    _gap(
                        f"policy_{finding.type}",
                        severity,
                        finding.type,
                        finding.target or str(policy_file),
                        finding.message,
                        None,
                        ["database_lifecycle_policy"],
                        _next_actions([finding]),
                    )
                )
        except Exception as exc:
            gaps.append(
                _gap(
                    "policy_invalid",
                    "blocking",
                    "database_policy_invalid",
                    str(policy_file),
                    f"database policy cannot be loaded: {exc}",
                    None,
                    ["database_lifecycle_policy"],
                    ["repair database_policy.yaml"],
                )
            )
    gaps = _dedupe_gaps(gaps)
    blocking = [gap for gap in gaps if gap.severity == "blocking"]
    review = [gap for gap in gaps if gap.severity == "review"]
    optional = [gap for gap in gaps if gap.severity == "optional"]
    status = "fail" if blocking else "partial" if review else "pass"
    return DatabaseMaintenanceReport(
        artifact_kind="database_maintenance_report",
        status=status,
        ok=status == "pass",
        database_root=str(root_path),
        catalog_path=str(catalog_file),
        policy_path=str(policy_file) if policy_file.exists() else None,
        blocking_gaps=[gap.model_dump(mode="json") for gap in blocking],
        review_gaps=[gap.model_dump(mode="json") for gap in review],
        optional_gaps=[gap.model_dump(mode="json") for gap in optional],
        project_summaries=project_summaries,
        lifecycle_artifacts=lifecycle,
        summary={
            "project_count": len(project_summaries),
            "blocking_gap_count": len(blocking),
            "review_gap_count": len(review),
            "optional_gap_count": len(optional),
            "semantics": "maintenance audit is database lifecycle evidence; it does not prove physics validation",
        },
        next_actions=_gap_next_actions(gaps),
    )


def archive_database_project(
    catalog_path: str | Path,
    project_id: str,
    *,
    reason: str,
    archive_state: Literal["archived", "deprecated", "superseded", "rejected"] = "archived",
    superseded_by_project_id: str | None = None,
    apply: bool = False,
    actor: str = "PhysicsGuard AI",
) -> DatabaseLifecycleOperationReport:
    catalog_file = Path(catalog_path)
    catalog = load_database_catalog(catalog_file)
    ensure_non_empty(project_id, "project_id")
    ensure_non_empty(reason, "reason")
    catalog_data = catalog.model_dump(mode="json")
    target = None
    for item in catalog_data["projects"]:
        if item["project_id"] == project_id:
            target = item
            break
    if target is None:
        finding = ContractFinding(
            severity="error",
            type="database_archive_project_missing",
            message="project_id is not present in catalog",
            target=project_id,
        )
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_archive_project",
            status="fail",
            ok=False,
            findings=[asdict(finding)],
            summary={"project_id": project_id, "catalog_path": str(catalog_file)},
            next_actions=["Check the project_id or run database query/map before archive."],
        )
    if archive_state == "superseded" and not superseded_by_project_id:
        finding = ContractFinding(
            severity="error",
            type="database_archive_superseded_target_missing",
            message="superseded archive requires superseded_by_project_id",
            target=project_id,
        )
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_archive_project",
            status="fail",
            ok=False,
            findings=[asdict(finding)],
            summary={"project_id": project_id, "catalog_path": str(catalog_file)},
            next_actions=["Provide superseded_by_project_id or choose a different archive state."],
        )
    previous_state = target.get("lifecycle_state")
    if not apply:
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_archive_project",
            status="dry_run",
            ok=True,
            dry_run=True,
            applied=False,
            summary={
                "project_id": project_id,
                "previous_state": previous_state,
                "new_state": archive_state,
                "semantics": "dry-run only; pass apply=True or CLI --apply to update catalog and history",
            },
            next_actions=["Review archive reason and rerun with explicit apply intent if correct."],
        )
    new_lifecycle_state = archive_state
    target["lifecycle_state"] = new_lifecycle_state
    target["project_status"] = "archived" if archive_state in {"archived", "superseded"} else "deprecated"
    target["archive_record"] = {
        "archive_state": archive_state,
        "reason": reason,
        "recorded_at": _now(),
        "recorded_by": actor,
        "superseded_by_project_id": superseded_by_project_id,
        "previous_state": previous_state,
    }
    if archive_state == "superseded":
        target["superseded_by_project_id"] = superseded_by_project_id
    if archive_state == "rejected":
        target["rejected_reason"] = reason
    catalog_data["updated_at"] = _now()
    DatabaseCatalogSpec.model_validate(catalog_data)
    _write_yaml(catalog_file, catalog_data)
    history_path = _history_path_for_catalog(catalog_file, catalog)
    event_type = {
        "archived": "project_archived",
        "deprecated": "project_deprecated",
        "superseded": "project_superseded",
        "rejected": "project_rejected",
    }[archive_state]
    event = _history_event(
        event_type,
        actor=actor,
        target_project_id=project_id,
        reason=reason,
        apply=True,
        before_state=str(previous_state),
        after_state=new_lifecycle_state,
        affected_paths=[str(catalog_file), str(history_path)],
    )
    _append_history(history_path, event)
    return DatabaseLifecycleOperationReport(
        artifact_kind="database_lifecycle_operation",
        operation="database_archive_project",
        status="pass",
        ok=True,
        dry_run=False,
        applied=True,
        written_files=[str(catalog_file), str(history_path)],
        history_events=[event.model_dump(mode="json")],
        summary={"project_id": project_id, "previous_state": previous_state, "new_state": new_lifecycle_state},
        next_actions=["Run database audit and render handoff after archive/deprecation/supersession."],
    )


def render_database_handoff(
    database_root: str | Path,
    *,
    catalog_path: str | Path | None = None,
    policy_path: str | Path | None = None,
    apply: bool = False,
    actor: str = "PhysicsGuard AI",
) -> DatabaseLifecycleOperationReport:
    root_path = Path(database_root)
    catalog_file = Path(catalog_path) if catalog_path else root_path / DEFAULT_DATABASE_ARTIFACTS.database_catalog
    policy_file = Path(policy_path) if policy_path else root_path / DEFAULT_DATABASE_ARTIFACTS.database_policy
    catalog = load_database_catalog(catalog_file) if catalog_file.exists() else None
    policy = load_database_policy(policy_file) if policy_file.exists() else None
    maintenance = audit_database_maintenance(root_path, catalog_path=catalog_file, policy_path=policy_file)
    markdown = _render_handoff_markdown(root_path, catalog, maintenance, policy)
    status_markdown = _render_status_markdown(
        catalog.catalog_id if catalog else root_path.name,
        maintenance.blocking_gaps,
        maintenance.review_gaps,
        maintenance.status,
    )
    readme_path = root_path / DEFAULT_DATABASE_ARTIFACTS.database_readme
    status_path = root_path / DEFAULT_DATABASE_ARTIFACTS.database_status
    history_path = root_path / DEFAULT_DATABASE_ARTIFACTS.database_history
    event = _history_event(
        "handoff_rendered",
        actor=actor,
        target_artifact=str(readme_path),
        reason="render database AI handoff documents",
        apply=apply,
        affected_paths=[str(readme_path), str(status_path), str(history_path)],
    )
    if not apply:
        return DatabaseLifecycleOperationReport(
            artifact_kind="database_lifecycle_operation",
            operation="database_render_handoff",
            status="dry_run",
            ok=True,
            dry_run=True,
            applied=False,
            history_events=[event.model_dump(mode="json")],
            summary={
                "readme_path": str(readme_path),
                "status_path": str(status_path),
                "rendered_markdown": markdown,
                "semantics": "dry-run only; pass apply=True or CLI --apply to write handoff Markdown",
            },
            next_actions=["Review rendered Markdown, then rerun with explicit apply intent if correct."],
        )
    root_path.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(markdown, encoding="utf-8")
    status_path.write_text(status_markdown, encoding="utf-8")
    _append_history(history_path, event)
    return DatabaseLifecycleOperationReport(
        artifact_kind="database_lifecycle_operation",
        operation="database_render_handoff",
        status="pass",
        ok=True,
        dry_run=False,
        applied=True,
        written_files=[str(readme_path), str(status_path), str(history_path)],
        history_events=[event.model_dump(mode="json")],
        summary={"readme_path": str(readme_path), "status_path": str(status_path)},
        next_actions=["Share DATABASE_README.md and DATABASE_STATUS.md with AI agents entering the database."],
    )


def _database_artifact_paths(root: Path, artifacts: DatabaseLifecycleArtifactsSpec) -> dict[str, Path]:
    return {
        "database_readme": root / artifacts.database_readme,
        "database_status": root / artifacts.database_status,
        "database_policy": root / artifacts.database_policy,
        "database_catalog": root / artifacts.database_catalog,
        "database_history": root / artifacts.database_history,
        "database_maintenance_report": root / artifacts.database_maintenance_report,
        "model_template_index": root / artifacts.model_template_index,
    }


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _append_history(path: Path, event: DatabaseHistoryEventSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True))
        handle.write("\n")


def _history_event(
    event_type: str,
    *,
    actor: str,
    target_project_id: str | None = None,
    target_artifact: str | None = None,
    reason: str | None = None,
    apply: bool = False,
    before_state: str | None = None,
    after_state: str | None = None,
    affected_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DatabaseHistoryEventSpec:
    return DatabaseHistoryEventSpec(
        event_id=str(uuid4()),
        event_type=event_type,
        occurred_at=_now(),
        actor=actor,
        target_project_id=target_project_id,
        target_artifact=target_artifact,
        reason=reason,
        dry_run=not apply,
        apply=apply,
        before_state=before_state,
        after_state=after_state,
        affected_paths=affected_paths or [],
        metadata=metadata or {},
    )


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _find_project_evidence_registry(project_root: Path) -> Path | None:
    preferred = project_root / "evidence" / "project_evidence_registry.yaml"
    if preferred.exists():
        return preferred
    for name in ("project_evidence_registry.yaml", "project_evidence_registry.yml"):
        direct = project_root / name
        if direct.exists():
            return direct
    candidates = sorted(
        path
        for path in project_root.rglob("*")
        if path.is_file()
        and path.name in {"project_evidence_registry.yaml", "project_evidence_registry.yml"}
        and not _is_excluded(path)
    )
    return candidates[0] if candidates else None


def _relative_or_absolute(path: Path | None, base: Path) -> Path | str | None:
    if path is None:
        return None
    try:
        return path.resolve(strict=False).relative_to(base.resolve(strict=False))
    except ValueError:
        return path


def _project_record_from_intake_plan(plan: DatabaseProjectIntakePlanSpec, *, actor: str) -> dict[str, Any]:
    gap_status = str(plan.metadata.get("evidence_gap_status", "unknown"))
    if gap_status not in {"unknown", "pass", "partial", "fail"}:
        gap_status = "unknown"
    project_status = "draft"
    if plan.requested_state in ACTIVE_LIFECYCLE_STATES:
        project_status = "active"
    elif plan.requested_state in {"archived", "superseded"}:
        project_status = "archived"
    elif plan.requested_state in {"deprecated", "rejected"}:
        project_status = "deprecated"
    admission = DatabaseProjectAdmissionSpec(
        requested_state=plan.requested_state,
        project_root=plan.project_root,
        project_adoption_record=plan.project_adoption_record,
        project_adoption_missing_reason=plan.project_adoption_missing_reason,
        project_evidence_registry=plan.project_evidence_registry,
        project_evidence_missing_reason=plan.registry_missing_reason,
        evidence_gap_status=gap_status,  # type: ignore[arg-type]
        admitted_at=_now(),
        admitted_by=actor,
        admission_reason=plan.admission_reason,
        metadata=plan.metadata,
    )
    return CatalogProjectRecordSpec(
        project_id=plan.project_id,
        project_name=plan.project_name,
        project_name_unknown_reason=None if plan.project_name else "project name not found during intake scan",
        project_evidence_registry=plan.project_evidence_registry,
        registry_missing_reason=plan.registry_missing_reason,
        project_status=project_status,  # type: ignore[arg-type]
        lifecycle_state=plan.requested_state,
        admission=admission,
        domain_tags=plan.domain_tags,
        system_tags=plan.system_tags,
        component_tags=plan.component_tags,
        testbench_tags=plan.testbench_tags,
        measurement_tags=plan.measurement_tags,
        last_scanned_at=_now(),
        notes=["Created from database project intake plan."],
        metadata={"project_root": plan.project_root, **plan.metadata},
    ).model_dump(mode="json")


def _history_path_for_catalog(catalog_path: Path, catalog: DatabaseCatalogSpec) -> Path:
    history = catalog.database_history or catalog.lifecycle_artifacts.database_history
    return _resolve_path(catalog_path.parent, history)


def _lifecycle_artifact_status(root: Path) -> dict[str, dict[str, Any]]:
    artifacts = DEFAULT_DATABASE_ARTIFACTS
    result: dict[str, dict[str, Any]] = {}
    for key, path in _database_artifact_paths(root, artifacts).items():
        result[key] = {"path": str(path), "exists": path.exists()}
    return result


def _lifecycle_project_gaps(catalog_path: Path, project: CatalogProjectRecordSpec) -> list[DatabaseCatalogGapSpec]:
    gaps: list[DatabaseCatalogGapSpec] = []
    if project.lifecycle_state in ACTIVE_LIFECYCLE_STATES and not project.project_evidence_registry:
        gaps.append(
            _gap(
                f"{project.project_id}_active_registry_missing",
                "blocking",
                "active_project_registry_missing",
                project.project_id,
                "active database project requires a project evidence registry",
                project.project_id,
                ["database_project_intake", "project_evidence_registry"],
                ["add project_evidence_registry or move this project to placeholder/candidate state"],
            )
        )
    if project.lifecycle_state == "active_validated" and not project.has_validation:
        gaps.append(
            _gap(
                f"{project.project_id}_validated_state_without_validation",
                "review",
                "validated_state_without_validation",
                project.project_id,
                "project is marked active_validated but catalog validation evidence is absent or unknown",
                project.project_id,
                ["database_project_intake", "model_dataset_validation"],
                ["link validation evidence or downgrade lifecycle_state to active_registered"],
            )
        )
    if project.lifecycle_state == "active_reusable" and not project.has_model_library_entry:
        gaps.append(
            _gap(
                f"{project.project_id}_reusable_state_without_model_library",
                "review",
                "reusable_state_without_model_library",
                project.project_id,
                "project is marked active_reusable but no model-library entry is recorded",
                project.project_id,
                ["database_project_intake", "model_library"],
                ["link a model-library entry or downgrade lifecycle_state"],
            )
        )
    if project.lifecycle_state in INACTIVE_LIFECYCLE_STATES and project.archive_record is None:
        gaps.append(
            _gap(
                f"{project.project_id}_inactive_without_archive_record",
                "review",
                "inactive_project_archive_record_missing",
                project.project_id,
                "inactive project should keep an archive/deprecation/supersession record",
                project.project_id,
                ["database_history_and_archive"],
                ["add archive_record with reason and recorded_at"],
            )
        )
    if project.lifecycle_state == "superseded" and not project.superseded_by_project_id:
        gaps.append(
            _gap(
                f"{project.project_id}_superseded_target_missing",
                "blocking",
                "superseded_project_target_missing",
                project.project_id,
                "superseded project requires superseded_by_project_id",
                project.project_id,
                ["database_history_and_archive"],
                ["record superseded_by_project_id"],
            )
        )
    if project.lifecycle_state == "rejected" and not project.rejected_reason:
        gaps.append(
            _gap(
                f"{project.project_id}_rejected_reason_missing",
                "blocking",
                "rejected_project_reason_missing",
                project.project_id,
                "rejected project requires rejected_reason",
                project.project_id,
                ["database_history_and_archive"],
                ["record rejected_reason"],
            )
        )
    return gaps


def _gap_next_actions(gaps: list[DatabaseCatalogGapSpec]) -> list[str]:
    actions: list[str] = []
    for gap in gaps:
        actions.extend(gap.suggested_action)
    return sorted(set(actions))


def _render_handoff_markdown(
    database_root: Path,
    catalog: DatabaseCatalogSpec | None,
    maintenance: DatabaseMaintenanceReport | None,
    policy: DatabasePolicySpec | None,
) -> str:
    database_id = catalog.catalog_id if catalog else policy.database_id if policy else database_root.name
    database_name = catalog.catalog_name if catalog else policy.database_name if policy else None
    project_count = len(catalog.projects) if catalog else 0
    active_count = sum(1 for project in catalog.projects if project.lifecycle_state not in INACTIVE_LIFECYCLE_STATES) if catalog else 0
    lines = [
        "# PhysicsGuard Database Map",
        "",
        f"- Database id: `{database_id}`",
        f"- Database name: `{database_name or 'unknown'}`",
        f"- Database root: `{database_root}`",
        f"- PhysicsGuard repository: `{policy.physicsguard_repository if policy else PHYSICSGUARD_REPOSITORY}`",
        f"- Project count: `{project_count}`",
        f"- Active/searchable project count: `{active_count}`",
        "",
        "## Required first reads",
        "",
        "- `database_policy.yaml`: lifecycle rules and write policy.",
        "- `database_catalog.yaml`: project list, project evidence registries, model libraries, and lifecycle states.",
        "- `database_maintenance_report.yaml`: latest database gap scan.",
        "- `DATABASE_STATUS.md`: concise current blockers and review gaps.",
        "- `database_history.jsonl`: append-only lifecycle history.",
        "- `model_template_index.yaml`: reusable model templates and their limits.",
        "",
        "## Operating rules",
        "",
        "- This is an explicit local database root, not a hidden global database.",
        "- Do not store raw test datasets inside database artifacts; store paths, summaries, hashes, and evidence pointers.",
        "- Active projects should satisfy project-level PhysicsGuard requirements before broad database claims.",
        "- Archived, deprecated, superseded, and rejected projects remain visible for history but are excluded from default queries.",
        "- Model templates are reuse starting points; every target project still needs its own evidence and validation review.",
        "",
        "## Project overview",
        "",
    ]
    if catalog and catalog.projects:
        lines.append("| Project | Lifecycle | Registry | Validation | Notes |")
        lines.append("| --- | --- | --- | --- | --- |")
        for project in catalog.projects:
            notes = "; ".join(project.notes[:2]) if project.notes else ""
            lines.append(
                "| "
                f"{project.project_id} | {project.lifecycle_state} | "
                f"{project.project_evidence_registry or project.registry_missing_reason or 'missing'} | "
                f"{project.confidence_summary.validation_state} | {notes} |"
            )
    else:
        lines.append("No projects are registered yet.")
    lines.extend(["", "## Latest maintenance status", ""])
    if maintenance:
        lines.extend(
            [
                f"- Status: `{maintenance.status}`",
                f"- Blocking gaps: `{len(maintenance.blocking_gaps)}`",
                f"- Review gaps: `{len(maintenance.review_gaps)}`",
                f"- Optional gaps: `{len(maintenance.optional_gaps)}`",
            ]
        )
        if maintenance.next_actions:
            lines.append("")
            lines.append("## Next actions")
            lines.append("")
            for action in maintenance.next_actions[:12]:
                lines.append(f"- {action}")
    else:
        lines.append("Maintenance audit has not been run yet.")
    lines.append("")
    return "\n".join(lines)


def _render_status_markdown(
    database_id: str,
    blocking_gaps: list[dict[str, Any]],
    review_gaps: list[dict[str, Any]],
    status: str,
) -> str:
    lines = [
        "# PhysicsGuard Database Status",
        "",
        f"- Database id: `{database_id}`",
        f"- Status: `{status}`",
        f"- Blocking gaps: `{len(blocking_gaps)}`",
        f"- Review gaps: `{len(review_gaps)}`",
        "",
    ]
    if blocking_gaps:
        lines.append("## Blocking gaps")
        lines.append("")
        for gap in blocking_gaps[:20]:
            lines.append(f"- `{gap.get('gap_type')}` at `{gap.get('target')}`: {gap.get('reason')}")
        lines.append("")
    if review_gaps:
        lines.append("## Review gaps")
        lines.append("")
        for gap in review_gaps[:20]:
            lines.append(f"- `{gap.get('gap_type')}` at `{gap.get('target')}`: {gap.get('reason')}")
        lines.append("")
    if not blocking_gaps and not review_gaps:
        lines.append("No blocking or review gaps are currently reported.")
        lines.append("")
    return "\n".join(lines)


def _project_record_findings(
    catalog_path: Path,
    project: CatalogProjectRecordSpec,
    catalog: DatabaseCatalogSpec,
) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    if catalog.policies.forbid_raw_data_payloads and _contains_raw_data_payload(project.metadata):
        findings.append(
            ContractFinding(
                severity="error",
                type="database_catalog_project_raw_data_payload",
                message="catalog project metadata must not embed raw test data payloads",
                target=project.project_id,
            )
        )
    if project.lifecycle_state in INACTIVE_LIFECYCLE_STATES:
        return findings
    if not project.project_evidence_registry and not project.registry_missing_reason:
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_catalog_project_registry_unresolved",
                message="catalog project should reference a project evidence registry or explain why it is missing",
                target=project.project_id,
            )
        )
    if not project.project_name and not project.project_name_unknown_reason:
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_catalog_project_name_unresolved",
                message="catalog project should record a project name or explicit unknown reason",
                target=project.project_id,
            )
        )
    if project.project_evidence_registry:
        registry_path = _resolve_path(catalog_path.parent, project.project_evidence_registry)
        if not registry_path.exists():
            findings.append(
                ContractFinding(
                    severity="error",
                    type="database_catalog_project_registry_missing",
                    message="catalog project evidence registry path is missing",
                    target=project.project_id,
                    details={"path": str(registry_path)},
                )
            )
    if project.stale_reason:
        findings.append(
            ContractFinding(
                severity="warning",
                type="database_catalog_project_stale",
                message="catalog project record marks its summary as stale",
                target=project.project_id,
                details={"stale_reason": project.stale_reason},
            )
        )
    return findings


def _collect_catalog_gaps(catalog_path: Path, catalog: DatabaseCatalogSpec) -> list[DatabaseCatalogGapSpec]:
    gaps: list[DatabaseCatalogGapSpec] = []
    if catalog.policies.forbid_raw_data_payloads and _contains_raw_data_payload(catalog.metadata):
        gaps.append(
            _gap(
                "catalog_raw_data_payload",
                "blocking",
                "catalog_raw_data_payload",
                catalog.catalog_id,
                "database catalog metadata appears to embed raw test data",
                None,
                ["database_catalog"],
                ["move raw data to external files and keep only paths, hashes, and summaries"],
            )
        )
    for project in catalog.projects:
        if catalog.policies.forbid_raw_data_payloads and _contains_raw_data_payload(project.metadata):
            gaps.append(
                _gap(
                    f"{project.project_id}_raw_data_payload",
                    "blocking",
                    "project_raw_data_payload",
                    project.project_id,
                    "catalog project metadata appears to embed raw test data",
                    project.project_id,
                    ["database_catalog"],
                    ["remove raw rows from catalog metadata and register the source artifact by path"],
                )
            )
        gaps.extend(_lifecycle_project_gaps(catalog_path, project))
        if project.lifecycle_state in INACTIVE_LIFECYCLE_STATES:
            continue
        if not project.project_evidence_registry:
            severity: GapSeverity = "review" if project.registry_missing_reason else "blocking"
            gaps.append(
                _gap(
                    f"{project.project_id}_registry_missing",
                    severity,
                    "project_registry_missing",
                    project.project_id,
                    "project has no project evidence registry reference",
                    project.project_id,
                    ["database_catalog"],
                    ["create a project evidence registry or record a clear missing-registry reason"],
                )
            )
            continue
        registry_path = _resolve_path(catalog_path.parent, project.project_evidence_registry)
        if not registry_path.exists():
            gaps.append(
                _gap(
                    f"{project.project_id}_registry_path_missing",
                    "blocking",
                    "project_registry_path_missing",
                    str(registry_path),
                    "project evidence registry path does not exist",
                    project.project_id,
                    ["database_catalog"],
                    ["fix the registry path or mark the project registry as missing with a reason"],
                )
            )
            continue
        try:
            project_gaps = check_evidence_gaps(registry_path)
        except Exception as exc:
            gaps.append(
                _gap(
                    f"{project.project_id}_registry_invalid",
                    "blocking",
                    "project_registry_invalid",
                    str(registry_path),
                    f"project evidence registry cannot be checked: {exc}",
                    project.project_id,
                    ["project_evidence_registry"],
                    ["repair the project evidence registry before database-level claims"],
                )
            )
            continue
        for gap in project_gaps.blocking_gaps:
            gaps.append(_project_gap(project.project_id, "blocking", gap))
        for gap in project_gaps.review_gaps:
            gaps.append(_project_gap(project.project_id, "review", gap))
        if project.has_model and not project.has_validation:
            gaps.append(
                _gap(
                    f"{project.project_id}_model_without_validation",
                    "review",
                    "model_without_validation",
                    project.project_id,
                    "catalog project indicates a model exists but validation is not recorded",
                    project.project_id,
                    ["database_catalog"],
                    ["run model-dataset validation or record why validation is unavailable"],
                )
            )
        if project.stale_reason:
            gaps.append(
                _gap(
                    f"{project.project_id}_stale_summary",
                    "review",
                    "catalog_summary_stale",
                    project.project_id,
                    "catalog project summary is marked stale",
                    project.project_id,
                    ["database_catalog"],
                    ["refresh the catalog summary from the project evidence registry"],
                    {"stale_reason": project.stale_reason},
                )
            )
    for library in catalog.model_library_indexes:
        library_path = _resolve_path(catalog_path.parent, library.path)
        if not library_path.exists():
            gaps.append(
                _gap(
                    f"model_library_{library.path}_missing",
                    "blocking",
                    "model_library_missing",
                    str(library_path),
                    "database catalog model-library reference path does not exist",
                    None,
                    ["database_catalog"],
                    ["fix or remove the model-library reference"],
                )
            )
    return _dedupe_gaps(gaps)


def _project_summary(catalog_path: Path, project: CatalogProjectRecordSpec) -> tuple[dict[str, Any], list[ContractFinding]]:
    findings: list[ContractFinding] = []
    registry_loaded = False
    project_map: Any | None = None
    registry_path_value = project.project_evidence_registry
    if project.lifecycle_state in INACTIVE_LIFECYCLE_STATES:
        registry_loaded = False
    elif registry_path_value:
        registry_path = _resolve_path(catalog_path.parent, registry_path_value)
        if registry_path.exists():
            try:
                project_map = build_project_evidence_map(registry_path)
                registry_loaded = True
            except Exception as exc:
                findings.append(
                    ContractFinding(
                        severity="error",
                        type="database_catalog_project_map_failed",
                        message=f"project evidence map could not be built: {exc}",
                        target=project.project_id,
                    )
                )
        else:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="database_catalog_project_registry_missing",
                    message="catalog project evidence registry path is missing",
                    target=project.project_id,
                    details={"path": str(registry_path)},
                )
            )
    else:
        findings.append(
            ContractFinding(
                severity="warning" if project.registry_missing_reason else "error",
                type="database_catalog_project_registry_missing",
                message="catalog project has no project evidence registry reference",
                target=project.project_id,
            )
        )

    tags = _project_tags(project)
    measured_quantities: list[str] = []
    model_targets: list[str] = []
    fact_targets: list[str] = []
    gap_counts = dict(project.gap_counts)
    profile = {}
    tests: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    if project_map is not None:
        profile = project_map.project_profile
        tests = project_map.tests
        models = project_map.models
        facts = project_map.facts
        bindings = project_map.bindings
        coverage = project_map.coverage_summary
        measured_quantities = sorted(
            {
                quantity
                for test in tests
                for quantity in test.get("measured_quantities", [])
                if quantity
            }
        )
        model_targets = sorted(set(coverage.get("tested_model_targets", [])) | set(coverage.get("required_binding_targets", [])))
        fact_targets = sorted(coverage.get("fact_bound_model_targets", []))
        gap_counts = {
            "blocking": len(project_map.gaps.get("blocking", [])),
            "review": len(project_map.gaps.get("review", [])),
            "optional": len(project_map.gaps.get("optional", [])),
        }
    has_test_data = project.has_test_data if project.has_test_data is not None else bool(tests)
    has_model = project.has_model if project.has_model is not None else bool(models)
    has_validation = project.has_validation if project.has_validation is not None else _has_validation_artifact(project_map)
    return (
        {
            "project_id": project.project_id,
            "project_name": project.project_name or profile.get("project_name"),
            "project_name_unknown_reason": project.project_name_unknown_reason or profile.get("project_name_unknown_reason"),
            "project_status": project.project_status,
            "lifecycle_state": project.lifecycle_state,
            "admission": project.admission.model_dump(mode="json"),
            "archive_record": project.archive_record.model_dump(mode="json") if project.archive_record else None,
            "superseded_by_project_id": project.superseded_by_project_id,
            "rejected_reason": project.rejected_reason,
            "project_evidence_registry": project.project_evidence_registry,
            "registry_loaded": registry_loaded,
            "registry_missing_reason": project.registry_missing_reason,
            "registry_digest": project.registry_digest,
            "tags": tags,
            "domain_tags": project.domain_tags,
            "system_tags": project.system_tags,
            "subsystem_tags": project.subsystem_tags,
            "component_tags": project.component_tags,
            "test_object_tags": project.test_object_tags,
            "testbench_tags": project.testbench_tags,
            "measurement_tags": project.measurement_tags,
            "run_period_summary": project.run_period_summary or _run_period_summary(profile),
            "location_summary": project.location_summary or _location_summary(profile),
            "has_test_data": has_test_data,
            "has_model": has_model,
            "has_validation": has_validation,
            "has_model_library_entry": project.has_model_library_entry,
            "tested_quantities": measured_quantities,
            "model_targets": model_targets,
            "fact_bound_model_targets": fact_targets,
            "test_count": len(tests),
            "model_count": len(models),
            "fact_count": len(facts),
            "binding_count": len(bindings),
            "gap_counts": gap_counts,
            "confidence_summary": project.confidence_summary.model_dump(mode="json"),
            "last_scanned_at": project.last_scanned_at,
            "stale_reason": project.stale_reason,
            "notes": project.notes,
        },
        findings,
    )


def _model_library_entries(catalog_path: Path, catalog: DatabaseCatalogSpec) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for library in catalog.model_library_indexes:
        library_path = _resolve_path(catalog_path.parent, library.path)
        loaded_id = library.library_id
        entry_count = None
        if library_path.exists():
            try:
                index = load_model_library_index(library_path)
                loaded_id = loaded_id or index.library_id
                entry_count = len(index.entries)
            except Exception:
                entry_count = None
        entries.append(
            {
                "library_id": loaded_id,
                "path": library.path,
                "path_exists": library_path.exists(),
                "entry_count": entry_count,
                "status": library.status,
                "notes": library.notes,
            }
        )
    return entries


def _build_indexes(projects: list[dict[str, Any]]) -> dict[str, Any]:
    indexes: dict[str, dict[str, list[str]]] = {
        "tags": {},
        "quantities": {},
        "model_targets": {},
        "components": {},
        "validated_projects": {},
        "projects_with_test_data": {},
    }
    for project in projects:
        project_id = project["project_id"]
        for tag in project.get("tags", []):
            _append_index(indexes["tags"], tag, project_id)
        for quantity in project.get("tested_quantities", []):
            _append_index(indexes["quantities"], quantity, project_id)
        for target in project.get("model_targets", []) + project.get("fact_bound_model_targets", []):
            _append_index(indexes["model_targets"], target, project_id)
        for component in project.get("component_tags", []):
            _append_index(indexes["components"], component, project_id)
        if project.get("has_validation"):
            _append_index(indexes["validated_projects"], "true", project_id)
        if project.get("has_test_data"):
            _append_index(indexes["projects_with_test_data"], "true", project_id)
    return indexes


def _project_matches(project: dict[str, Any], filters: dict[str, Any]) -> bool:
    if "tag" in filters and not _contains_casefold(project.get("tags", []), filters["tag"]):
        return False
    if "quantity" in filters and not _contains_casefold(project.get("tested_quantities", []), filters["quantity"]):
        return False
    if "component" in filters and not _contains_casefold(project.get("component_tags", []), filters["component"]):
        return False
    if "model_target" in filters and not _contains_casefold(
        project.get("model_targets", []) + project.get("fact_bound_model_targets", []),
        filters["model_target"],
    ):
        return False
    if "has_validation" in filters and project.get("has_validation") is not filters["has_validation"]:
        return False
    if "has_test_data" in filters and project.get("has_test_data") is not filters["has_test_data"]:
        return False
    if "project_status" in filters and project.get("project_status") != filters["project_status"]:
        return False
    return True


def _registered_catalog_paths(catalog: DatabaseCatalogSpec | None, base_dir: Path) -> dict[Path, str]:
    paths: dict[Path, str] = {}
    if catalog is None:
        return paths
    for project in catalog.projects:
        if project.project_evidence_registry:
            paths[_normalize_path(_resolve_path(base_dir, project.project_evidence_registry))] = project.project_id
    for library in catalog.model_library_indexes:
        paths[_normalize_path(_resolve_path(base_dir, library.path))] = library.library_id or library.path
    return paths


def _classify_catalog_candidate(path: Path) -> tuple[CandidateKind | None, str]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return "other", "YAML file could not be classified but may be database evidence"
    if not isinstance(data, dict):
        return None, ""
    if "catalog_id" in data and "projects" in data:
        return "database_catalog", "database catalog YAML"
    if "registry_id" in data and "artifacts" in data:
        return "project_evidence_registry", "project evidence registry YAML"
    if "library_id" in data and "entries" in data:
        return "model_library", "model library YAML"
    return None, ""


def _contains_raw_data_payload(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in RAW_DATA_KEYS and isinstance(child, (list, dict)):
                return True
            if _contains_raw_data_payload(child):
                return True
    if isinstance(value, list):
        return any(_contains_raw_data_payload(item) for item in value)
    return False


def _project_gap(project_id: str, severity: GapSeverity, gap: dict[str, Any]) -> DatabaseCatalogGapSpec:
    return _gap(
        f"{project_id}_{gap.get('gap_id', gap.get('gap_type', 'project_gap'))}",
        severity,
        f"project_{gap.get('gap_type', 'evidence_gap')}",
        gap.get("target", project_id),
        gap.get("reason", "project evidence gap"),
        project_id,
        ["project_evidence_registry", *gap.get("required_by", [])],
        gap.get("suggested_search", []),
        {"project_gap": gap},
    )


def _gap(
    gap_id: str,
    severity: GapSeverity,
    gap_type: str,
    target: str,
    reason: str,
    project_id: str | None,
    required_by: list[str],
    suggested_action: list[str],
    metadata: dict[str, Any] | None = None,
) -> DatabaseCatalogGapSpec:
    return DatabaseCatalogGapSpec(
        gap_id=_safe_id(gap_id),
        severity=severity,
        gap_type=gap_type,
        target=target,
        reason=reason,
        project_id=project_id,
        required_by=required_by,
        suggested_action=suggested_action,
        metadata=metadata or {},
    )


def _project_tags(project: CatalogProjectRecordSpec) -> list[str]:
    values: list[str] = []
    for group in (
        project.domain_tags,
        project.system_tags,
        project.subsystem_tags,
        project.component_tags,
        project.test_object_tags,
        project.testbench_tags,
        project.measurement_tags,
    ):
        values.extend(group)
    return sorted(dict.fromkeys(values))


def _run_period_summary(profile: dict[str, Any]) -> Optional[str]:
    run_period = profile.get("run_period") or {}
    return run_period.get("coverage_period") or _join_known(
        [run_period.get("run_started_at"), run_period.get("run_ended_at")],
        " to ",
    )


def _location_summary(profile: dict[str, Any]) -> Optional[str]:
    locations = profile.get("locations") or []
    labels = [
        location.get("label")
        or location.get("facility")
        or location.get("city")
        or location.get("region")
        or location.get("country")
        for location in locations
    ]
    labels = [item for item in labels if item]
    return ", ".join(labels) if labels else profile.get("location_unknown_reason")


def _has_validation_artifact(project_map: Any | None) -> bool:
    if project_map is None:
        return False
    return any(
        artifact.get("artifact_kind") in {"validation_plan", "validation_report"}
        for artifact in project_map.artifacts
    )


def _append_index(index: dict[str, list[str]], key: str, project_id: str) -> None:
    values = index.setdefault(key, [])
    if project_id not in values:
        values.append(project_id)


def _contains_casefold(values: list[str], target: str) -> bool:
    target_folded = str(target).casefold()
    return any(str(value).casefold() == target_folded for value in values)


def _join_known(values: list[str | None], separator: str) -> Optional[str]:
    known = [value for value in values if value]
    return separator.join(known) if known else None


def _dedupe_gaps(gaps: list[DatabaseCatalogGapSpec]) -> list[DatabaseCatalogGapSpec]:
    seen: set[tuple[str, str, str, str | None]] = set()
    result: list[DatabaseCatalogGapSpec] = []
    for gap in gaps:
        key = (gap.gap_type, gap.target, gap.severity, gap.project_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(gap)
    return result


def _is_excluded(path: Path) -> bool:
    return any(part in SCAN_EXCLUDED_DIRS for part in path.parts)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _normalize_path(path: Path) -> Path:
    return path.resolve(strict=False)


def _safe_id(value: str) -> str:
    safe = []
    for char in value:
        safe.append(char if char.isalnum() or char in {"_", "-"} else "_")
    return "".join(safe)


def _status(findings: list[ContractFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "partial"
    return "pass"


def _next_actions(findings: list[ContractFinding]) -> list[str]:
    actions: list[str] = []
    for finding in findings:
        if finding.type.endswith("raw_data_payload"):
            actions.append("remove raw data from the catalog and keep only file references")
        elif "registry" in finding.type:
            actions.append("fix or create the referenced project evidence registry")
        elif "model_library" in finding.type:
            actions.append("fix or remove the model-library reference")
        elif finding.severity == "warning":
            actions.append(f"review {finding.type}")
        elif finding.severity == "error":
            actions.append(f"fix {finding.type}")
    return sorted(set(actions))


__all__ = [
    "DatabaseCatalogGapReport",
    "DatabaseCatalogRefreshReport",
    "DatabaseCatalogScanReport",
    "DatabaseLifecycleOperationReport",
    "DatabaseMaintenanceReport",
    "DatabaseMapReport",
    "DatabaseQueryReport",
    "admit_database_project",
    "archive_database_project",
    "audit_database_maintenance",
    "build_database_map",
    "check_database_catalog",
    "check_database_catalog_gaps",
    "check_database_model_template_index",
    "check_database_policy",
    "initialize_database_root",
    "plan_database_project_intake",
    "query_database_catalog",
    "refresh_database_catalog",
    "render_database_handoff",
    "scan_database_catalog_candidates",
]
