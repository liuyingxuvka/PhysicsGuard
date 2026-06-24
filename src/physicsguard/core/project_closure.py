"""Project-level closure aggregation for PhysicsGuard workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.evidence_mesh import check_evidence_mesh
from physicsguard.core.model_library import check_model_library_index
from physicsguard.core.project_evidence import (
    build_project_evidence_map,
    check_evidence_gaps,
    check_project_evidence_registry,
)
from physicsguard.core.test_file_contract import check_test_file_contract
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.io.test_file_contract_loader import load_project_closure_plan
from physicsguard.schema.project_closure import (
    ProjectClosureFindingSpec,
    ProjectClosurePlanSpec,
    ProjectClosureReportSpec,
    ProjectClosureSkippedCheckSpec,
)
from physicsguard.workflow import audit_project


@dataclass(frozen=True)
class ProjectClosureFinding:
    severity: str
    type: str
    message: str
    source: str
    target: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectClosureSkippedCheck:
    check: str
    reason: str
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectClosureReport:
    artifact_kind: str
    closure_id: str
    claim_scope: str
    closure_status: str
    ok: bool
    checked_inputs: list[dict[str, Any]]
    blocking_findings: list[dict[str, Any]]
    review_findings: list[dict[str, Any]]
    optional_findings: list[dict[str, Any]]
    skipped_checks: list[dict[str, Any]]
    safe_claim: str
    unsafe_claim_boundary: str
    next_actions: list[str]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_project_closure(path: str | Path) -> ProjectClosureReport:
    plan_path = Path(path)
    plan = load_project_closure_plan(plan_path)
    base_dir = plan_path.parent
    project_root = _resolve_path(base_dir, plan.project_root)
    checked_inputs: list[dict[str, Any]] = []
    findings: list[ProjectClosureFinding] = []
    skipped: list[ProjectClosureSkippedCheck] = []

    _run_project_audit(plan, project_root, checked_inputs, findings, skipped)
    _run_evidence_checks(plan, base_dir, checked_inputs, findings, skipped)
    _run_test_contract_checks(plan, base_dir, checked_inputs, findings, skipped)
    _run_validation_checks(plan, base_dir, checked_inputs, findings, skipped)
    _run_model_library_checks(plan, base_dir, checked_inputs, findings, skipped)
    _run_evidence_mesh_checks(plan, base_dir, checked_inputs, findings, skipped)
    _run_hierarchy_closure_checks(plan, base_dir, checked_inputs, findings, skipped)

    blocking = [finding for finding in findings if finding.severity == "error"]
    review = [finding for finding in findings if finding.severity == "warning"]
    optional = [finding for finding in findings if finding.severity == "info"]
    skipped_blockers = [
        item for item in skipped if item.required and not plan.allow_skipped_required_checks
    ]
    if skipped_blockers:
        blocking.extend(
            ProjectClosureFinding(
                severity="error",
                type="project_closure_required_check_skipped",
                message="required closure check was skipped",
                source="project_closure",
                target=item.check,
                details={"reason": item.reason},
            )
            for item in skipped_blockers
        )

    if blocking:
        status = "blocked"
    elif review and not plan.allow_review_gaps:
        status = "blocked"
    elif review:
        status = "partial"
    elif optional and not plan.allow_optional_gaps:
        status = "downgraded"
    else:
        status = "passed"

    report = ProjectClosureReport(
        artifact_kind="physicsguard_project_closure_report",
        closure_id=plan.closure_id,
        claim_scope=plan.claim_scope,
        closure_status=status,
        ok=status == "passed",
        checked_inputs=checked_inputs,
        blocking_findings=[item.to_dict() for item in blocking],
        review_findings=[item.to_dict() for item in review],
        optional_findings=[item.to_dict() for item in optional],
        skipped_checks=[item.to_dict() for item in skipped],
        safe_claim=_safe_claim(plan, status),
        unsafe_claim_boundary=_unsafe_claim_boundary(plan),
        next_actions=_next_actions(blocking, review, skipped),
        summary={
            "checked_input_count": len(checked_inputs),
            "blocking_finding_count": len(blocking),
            "review_finding_count": len(review),
            "optional_finding_count": len(optional),
            "skipped_check_count": len(skipped),
            "semantics": (
                "project closure is current-run claim readiness evidence; "
                "project evidence maps remain navigation, not validation proof"
            ),
        },
    )
    ProjectClosureReportSpec.model_validate(report.to_dict())
    return report


def _run_project_audit(
    plan: ProjectClosurePlanSpec,
    project_root: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    if not plan.required_checks.project_audit:
        return
    checked_inputs.append({"check": "project_audit", "path": str(project_root)})
    try:
        result = audit_project(project_root)
    except Exception as exc:
        findings.append(_finding("error", "project_audit_failed", "project audit failed", "project_audit", str(project_root), {"error": str(exc)}))
        return
    if not result.get("ok"):
        findings.append(_finding("error", "project_audit_not_ok", "project audit did not pass", "project_audit", str(project_root), result))
    for warning in result.get("warnings", []) if isinstance(result.get("warnings"), list) else []:
        findings.append(_finding("warning", "project_audit_warning", str(warning), "project_audit", str(project_root), result))


def _run_evidence_checks(
    plan: ProjectClosurePlanSpec,
    base_dir: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    registry = _optional_resolve(base_dir, plan.evidence_registry)
    if plan.required_checks.evidence_check:
        if registry is None:
            skipped.append(ProjectClosureSkippedCheck("evidence_check", "no evidence_registry declared"))
        else:
            checked_inputs.append({"check": "evidence_check", "path": str(registry)})
            try:
                review = check_project_evidence_registry(registry)
            except Exception as exc:
                findings.append(_finding("error", "evidence_check_failed", "project evidence registry check failed", "project_evidence", str(registry), {"error": str(exc)}))
            else:
                _review_findings(review.to_dict(), "project_evidence", findings)

    if plan.required_checks.evidence_gap_check:
        if registry is None:
            skipped.append(ProjectClosureSkippedCheck("evidence_gap_check", "no evidence_registry declared"))
        else:
            bundle_ids = plan.evidence_bundle_ids or [None]
            for bundle_id in bundle_ids:
                checked_inputs.append({"check": "evidence_gap_check", "path": str(registry), "bundle_id": bundle_id})
                try:
                    gap_report = check_evidence_gaps(registry, bundle_id)
                except Exception as exc:
                    findings.append(_finding("error", "evidence_gap_check_failed", "project evidence gap check failed", "project_evidence", str(registry), {"bundle_id": bundle_id, "error": str(exc)}))
                    continue
                for gap in gap_report.blocking_gaps:
                    findings.append(_gap_finding("error", gap, "project_evidence"))
                for gap in gap_report.review_gaps:
                    findings.append(_gap_finding("warning", gap, "project_evidence"))
                for gap in gap_report.optional_gaps:
                    findings.append(_gap_finding("info", gap, "project_evidence"))

    if plan.required_checks.evidence_map:
        if registry is None:
            skipped.append(ProjectClosureSkippedCheck("evidence_map", "no evidence_registry declared"))
        else:
            checked_inputs.append({"check": "evidence_map", "path": str(registry), "proof_boundary": "navigation_only"})
            try:
                project_map = build_project_evidence_map(registry)
            except Exception as exc:
                findings.append(_finding("error", "evidence_map_failed", "project evidence map generation failed", "project_evidence", str(registry), {"error": str(exc)}))
            else:
                if not project_map.ok:
                    findings.append(_finding("warning", "evidence_map_not_ok", "project evidence map is partial", "project_evidence", str(registry), project_map.to_dict()))


def _run_test_contract_checks(
    plan: ProjectClosurePlanSpec,
    base_dir: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    if not plan.required_checks.test_contracts and not plan.test_contracts:
        return
    if not plan.test_contracts:
        skipped.append(ProjectClosureSkippedCheck("test_contracts", "no test_contracts declared", plan.required_checks.test_contracts))
        return
    for value in plan.test_contracts:
        path = _resolve_path(base_dir, value)
        checked_inputs.append({"check": "test_file_contract", "path": str(path)})
        try:
            review = check_test_file_contract(path)
        except Exception as exc:
            findings.append(_finding("error", "test_contract_check_failed", "test-file contract check failed", "test_file_contract", str(path), {"error": str(exc)}))
            continue
        _review_findings(review.to_dict(), "test_file_contract", findings)


def _run_validation_checks(
    plan: ProjectClosurePlanSpec,
    base_dir: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    if not plan.required_checks.validation and not plan.validation_plans:
        return
    if not plan.validation_plans:
        skipped.append(ProjectClosureSkippedCheck("validation", "no validation_plans declared", plan.required_checks.validation))
        return
    for value in plan.validation_plans:
        path = _resolve_path(base_dir, value)
        checked_inputs.append({"check": "model_dataset_validation", "path": str(path)})
        try:
            report = validate_model_dataset(path)
        except Exception as exc:
            findings.append(_finding("error", "validation_check_failed", "model-dataset validation failed to run", "model_dataset_validation", str(path), {"error": str(exc)}))
            continue
        _report_status_findings(report.to_dict(), "model_dataset_validation", findings)


def _run_model_library_checks(
    plan: ProjectClosurePlanSpec,
    base_dir: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    if not plan.required_checks.model_library and not plan.model_library_indexes:
        return
    if not plan.model_library_indexes:
        skipped.append(ProjectClosureSkippedCheck("model_library", "no model_library_indexes declared", plan.required_checks.model_library))
        return
    for value in plan.model_library_indexes:
        path = _resolve_path(base_dir, value)
        checked_inputs.append({"check": "model_library", "path": str(path)})
        try:
            review = check_model_library_index(path)
        except Exception as exc:
            findings.append(_finding("error", "model_library_check_failed", "model-library check failed", "model_library", str(path), {"error": str(exc)}))
            continue
        _review_findings(review.to_dict(), "model_library", findings)


def _run_evidence_mesh_checks(
    plan: ProjectClosurePlanSpec,
    base_dir: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    if not plan.required_checks.evidence_mesh and not plan.evidence_meshes:
        return
    if not plan.evidence_meshes:
        skipped.append(ProjectClosureSkippedCheck("evidence_mesh", "no evidence_meshes declared", plan.required_checks.evidence_mesh))
        return
    for value in plan.evidence_meshes:
        path = _resolve_path(base_dir, value)
        checked_inputs.append({"check": "evidence_mesh", "path": str(path)})
        try:
            report = check_evidence_mesh(path)
        except Exception as exc:
            findings.append(_finding("error", "evidence_mesh_check_failed", "evidence mesh check failed", "evidence_mesh", str(path), {"error": str(exc)}))
            continue
        _report_status_findings(report.to_dict(), "evidence_mesh", findings)


def _run_hierarchy_closure_checks(
    plan: ProjectClosurePlanSpec,
    base_dir: Path,
    checked_inputs: list[dict[str, Any]],
    findings: list[ProjectClosureFinding],
    skipped: list[ProjectClosureSkippedCheck],
) -> None:
    if not plan.required_checks.hierarchy_closure and not plan.audit_pairs:
        return
    if not plan.audit_pairs:
        skipped.append(ProjectClosureSkippedCheck("hierarchy_closure", "no audit_pairs declared", plan.required_checks.hierarchy_closure))
        return
    for pair in plan.audit_pairs:
        audit_path = _resolve_path(base_dir, pair.audit_file)
        observed_path = _resolve_path(base_dir, pair.observed_file)
        checked_inputs.append({"check": "hierarchy_closure", "path": str(audit_path), "observed": str(observed_path)})
        try:
            spec = load_hierarchical_audit_spec(audit_path)
            observed = load_observed_values(observed_path)
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
        except Exception as exc:
            findings.append(_finding("error", "hierarchy_closure_failed", "hierarchy closure check failed", "hierarchy_closure", str(audit_path), {"error": str(exc)}))
            continue
        if not report.audit_pass:
            findings.append(
                _finding(
                    "error",
                    "hierarchy_audit_not_passed",
                    "hierarchy observed evaluation did not pass",
                    "hierarchy_closure",
                    str(audit_path),
                    {"label": pair.label, "max_abs_normalized_residual": report.max_abs_normalized_residual},
                )
            )
        if report.recommended_refinements:
            findings.append(
                _finding(
                    "warning",
                    "hierarchy_recommended_refinements_present",
                    "hierarchy report still recommends refinements",
                    "hierarchy_closure",
                    str(audit_path),
                    {"count": len(report.recommended_refinements)},
                )
            )


def _review_findings(report: dict[str, Any], source: str, findings: list[ProjectClosureFinding]) -> None:
    status = str(report.get("status", ""))
    if status == "fail":
        findings.append(_finding("error", f"{source}_status_fail", f"{source} status is fail", source, None, report))
    elif status in {"partial", "pass_with_gaps"}:
        findings.append(_finding("warning", f"{source}_status_partial", f"{source} status is partial", source, None, report))
    for item in report.get("findings", []) if isinstance(report.get("findings"), list) else []:
        severity = "error" if item.get("severity") == "error" else "warning" if item.get("severity") == "warning" else "info"
        findings.append(
            _finding(
                severity,
                str(item.get("type", f"{source}_finding")),
                str(item.get("message", "")),
                source,
                item.get("target") or item.get("field"),
                dict(item.get("details", {})) if isinstance(item.get("details"), dict) else item,
            )
        )


def _report_status_findings(report: dict[str, Any], source: str, findings: list[ProjectClosureFinding]) -> None:
    status = str(report.get("status", ""))
    if status == "fail":
        findings.append(_finding("error", f"{source}_status_fail", f"{source} status is fail", source, None, report))
    elif status == "partial":
        findings.append(_finding("warning", f"{source}_status_partial", f"{source} status is partial", source, None, report))
    for item in report.get("findings", []) if isinstance(report.get("findings"), list) else []:
        severity = "error" if item.get("severity") == "error" else "warning" if item.get("severity") == "warning" else "info"
        findings.append(
            _finding(
                severity,
                str(item.get("type", f"{source}_finding")),
                str(item.get("message", "")),
                source,
                item.get("target"),
                dict(item.get("details", {})) if isinstance(item.get("details"), dict) else item,
            )
        )
    for key, default_severity in (
        ("blocking_findings", "error"),
        ("review_findings", "warning"),
        ("optional_findings", "info"),
    ):
        items = report.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            details = dict(item.get("details", {})) if isinstance(item.get("details"), dict) else {}
            if item.get("source"):
                details["inner_source"] = item["source"]
            findings.append(
                _finding(
                    str(item.get("severity") or default_severity),
                    str(item.get("type", f"{source}_finding")),
                    str(item.get("message", "")),
                    source,
                    item.get("target"),
                    details,
                )
            )


def _gap_finding(severity: str, gap: dict[str, Any], source: str) -> ProjectClosureFinding:
    return _finding(
        severity,
        str(gap.get("gap_type", "project_evidence_gap")),
        str(gap.get("reason", "project evidence gap")),
        source,
        gap.get("target"),
        gap,
    )


def _finding(
    severity: str,
    kind: str,
    message: str,
    source: str,
    target: str | None = None,
    details: dict[str, Any] | None = None,
) -> ProjectClosureFinding:
    item = ProjectClosureFinding(
        severity=severity,
        type=kind,
        message=message,
        source=source,
        target=target,
        details=details or {},
    )
    ProjectClosureFindingSpec.model_validate(item.to_dict())
    return item


def _safe_claim(plan: ProjectClosurePlanSpec, status: str) -> str:
    if status == "passed":
        return f"{plan.claim_scope} closure passed inside the checked PhysicsGuard project boundary."
    if status == "partial":
        return f"{plan.claim_scope} evidence is partial; only scoped progress claims are supported."
    if status == "downgraded":
        return f"{plan.claim_scope} evidence is downgraded; optional gaps or limited scope must remain visible."
    return f"{plan.claim_scope} broad claims are blocked until closure findings are resolved."


def _unsafe_claim_boundary(plan: ProjectClosurePlanSpec) -> str:
    return (
        f"Do not claim {plan.claim_scope} beyond the checked project audit, evidence bundles, "
        "test contracts, validation reports, model-library records, evidence mesh reports, "
        "and hierarchy closure inputs. "
        "Evidence maps are navigation only and do not prove validation."
    )


def _next_actions(
    blocking: Iterable[ProjectClosureFinding],
    review: Iterable[ProjectClosureFinding],
    skipped: Iterable[ProjectClosureSkippedCheck],
) -> list[str]:
    actions: set[str] = set()
    for item in blocking:
        if "evidence" in item.source:
            actions.add("resolve blocking project evidence gaps before broad claims")
        elif item.source == "test_file_contract":
            actions.add("fix test-file contract errors before AI analysis readiness")
        elif item.source == "model_dataset_validation":
            actions.add("repair model-dataset validation before validation claims")
        elif item.source == "model_library":
            actions.add("repair model-library evidence before reuse claims")
        elif item.source == "evidence_mesh":
            actions.add("repair evidence mesh route receipts before broad closure claims")
        elif item.source == "hierarchy_closure":
            actions.add("rerun or refine hierarchy closure before localization claims")
        elif item.source == "project_audit":
            actions.add("repair PhysicsGuard project adoption before closure")
    for item in review:
        if "evidence" in item.source:
            actions.add("keep review project evidence gaps visible or resolve them")
    for item in skipped:
        if item.required:
            actions.add(f"provide required closure input for {item.check}")
    return sorted(actions)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def _optional_resolve(base: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    return _resolve_path(base, value)


__all__ = ["ProjectClosureReport", "run_project_closure"]
