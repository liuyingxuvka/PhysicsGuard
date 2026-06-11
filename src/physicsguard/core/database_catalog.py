"""Database-level catalog checks, maps, and safe query reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from physicsguard.core.parameter_coverage import ContractFinding, ContractReview
from physicsguard.core.project_evidence import (
    SCAN_EXCLUDED_DIRS,
    build_project_evidence_map,
    check_evidence_gaps,
)
from physicsguard.io.test_file_contract_loader import (
    load_database_catalog,
    load_model_library_index,
    load_yaml_mapping,
)
from physicsguard.schema.database_catalog import (
    CandidateKind,
    CatalogProjectRecordSpec,
    DatabaseCatalogCandidateSpec,
    DatabaseCatalogGapSpec,
    DatabaseCatalogSpec,
)
from physicsguard.schema.project_evidence import GapSeverity


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
    }
    active_filters = {key: value for key, value in filters.items() if value is not None}
    matches = [
        project
        for project in database_map.projects
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


def _project_record_findings(
    catalog_path: Path,
    project: CatalogProjectRecordSpec,
    catalog: DatabaseCatalogSpec,
) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
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
    if catalog.policies.forbid_raw_data_payloads and _contains_raw_data_payload(project.metadata):
        findings.append(
            ContractFinding(
                severity="error",
                type="database_catalog_project_raw_data_payload",
                message="catalog project metadata must not embed raw test data payloads",
                target=project.project_id,
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
    if registry_path_value:
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
    "DatabaseMapReport",
    "DatabaseQueryReport",
    "build_database_map",
    "check_database_catalog",
    "check_database_catalog_gaps",
    "query_database_catalog",
    "refresh_database_catalog",
    "scan_database_catalog_candidates",
]
