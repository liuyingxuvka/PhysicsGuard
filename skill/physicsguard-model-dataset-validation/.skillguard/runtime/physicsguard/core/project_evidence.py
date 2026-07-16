"""Project evidence registry checks, scanning, and gap reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

from physicsguard.core.parameter_coverage import ContractFinding, ContractReview
from physicsguard.io.test_file_contract_loader import load_project_evidence_registry, load_yaml_mapping
from physicsguard.schema.project_evidence import (
    ArtifactKind,
    BindingExpectationSpec,
    ContextCardSpec,
    EvidenceBundleSpec,
    EvidenceCandidateSpec,
    EvidenceGapSpec,
    GapSeverity,
    ProjectEvidenceRegistrySpec,
)


SCAN_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
}
SOURCE_DOCUMENT_SUFFIXES = {".ppt", ".pptx", ".pdf", ".doc", ".docx", ".xls", ".xlsx"}
TEST_DATA_SUFFIXES = {".csv", ".tsv", ".dat", ".mat", ".h5", ".hdf5", ".parquet"}
YAML_SUFFIXES = {".yaml", ".yml"}


@dataclass(frozen=True)
class ProjectEvidenceScanReport:
    artifact_kind: str
    status: str
    ok: bool
    candidates: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceGapReport:
    artifact_kind: str
    status: str
    ok: bool
    registry_id: str
    bundle_id: Optional[str] = None
    blocking_gaps: list[dict[str, Any]] = field(default_factory=list)
    review_gaps: list[dict[str, Any]] = field(default_factory=list)
    optional_gaps: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectEvidenceMapReport:
    artifact_kind: str
    status: str
    ok: bool
    registry_id: str
    project_id: Optional[str]
    project_scope: dict[str, Any]
    project_profile: dict[str, Any]
    artifacts: list[dict[str, Any]]
    tests: list[dict[str, Any]]
    models: list[dict[str, Any]]
    facts: list[dict[str, Any]]
    bindings: list[dict[str, Any]]
    binding_expectations: list[dict[str, Any]]
    coverage_summary: dict[str, Any]
    gaps: dict[str, Any]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_project_evidence_registry(path: str | Path) -> ContractReview:
    registry_path = Path(path)
    registry = load_project_evidence_registry(registry_path)
    base_dir = registry_path.parent
    findings: list[ContractFinding] = []
    artifact_ids = {item.artifact_id for item in registry.artifacts}
    fact_ids = {item.fact_id for item in registry.facts}
    binding_ids = {item.binding_id for item in registry.evidence_bindings}
    expectation_ids = {item.expectation_id for item in registry.binding_expectations}
    context_ids = {item.context_id for item in registry.context_cards}
    bundle_ids = {item.bundle_id for item in registry.evidence_bundles}
    missing_ids = {item.missing_id for item in registry.missing_evidence}

    _source_ref_findings(findings, registry.project_profile.source_refs, artifact_ids, "project_profile")
    _source_ref_findings(
        findings,
        registry.project_profile.run_period.source_refs,
        artifact_ids,
        "project_profile.run_period",
    )
    for location in registry.project_profile.locations:
        _source_ref_findings(findings, location.source_refs, artifact_ids, f"project_profile.locations.{location.location_id}")

    for artifact in registry.artifacts:
        if artifact.path:
            artifact_path = _resolve_path(base_dir, artifact.path)
            if not artifact_path.exists():
                findings.append(
                    ContractFinding(
                        severity="warning",
                        type="artifact_path_missing",
                        message="registered artifact path does not exist locally",
                        target=artifact.artifact_id,
                        details={"path": str(artifact_path)},
                    )
                )
        if artifact.local_copy_path:
            local_copy_path = _resolve_path(base_dir, artifact.local_copy_path)
            if not local_copy_path.exists():
                findings.append(
                    ContractFinding(
                        severity="warning",
                        type="artifact_local_copy_missing",
                        message="registered artifact local copy path does not exist locally",
                        target=artifact.artifact_id,
                        details={"local_copy_path": str(local_copy_path)},
                    )
                )
        if artifact.artifact_kind in {"cleaned_test_data", "derived_test_data"}:
            has_lineage = bool(
                artifact.lineage.derived_from
                or artifact.lineage.split_from
                or artifact.lineage.merged_from
                or artifact.lineage.original_source_missing_reason
            )
            if not has_lineage:
                findings.append(
                    ContractFinding(
                        severity="warning",
                        type="artifact_lineage_missing",
                        message="cleaned or derived test data should record lineage or a missing-source reason",
                        target=artifact.artifact_id,
                    )
                )
        _source_ref_findings(findings, artifact.source_refs, artifact_ids, artifact.artifact_id)
        _lineage_reference_findings(findings, artifact, artifact_ids)

    findings.extend(_lineage_cycle_findings(registry))

    for fact in registry.facts:
        if not fact.source_refs and not fact.value_missing_reason:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="fact_source_missing",
                    message="engineering fact has no source reference or missing-source explanation",
                    target=fact.fact_id,
                )
            )
        _source_ref_findings(findings, fact.source_refs, artifact_ids, fact.fact_id)
        if fact.behavior.kind == "time_series_reference" and fact.behavior.time_series_artifact not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="time_series_artifact_missing",
                    message="time-series fact references an unknown artifact",
                    target=fact.fact_id,
                    details={"artifact_id": fact.behavior.time_series_artifact},
                )
            )
        findings.extend(_piecewise_overlap_findings(fact.fact_id, fact.behavior.piecewise_segments))

    for binding in registry.evidence_bindings:
        if binding.source_artifact and binding.source_artifact not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="binding_source_artifact_missing",
                    message="binding references an unknown source artifact",
                    target=binding.binding_id,
                    details={"source_artifact": binding.source_artifact},
                )
            )
        if binding.source_contract and binding.source_contract not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="binding_source_contract_missing",
                    message="binding references an unknown source contract artifact",
                    target=binding.binding_id,
                    details={"source_contract": binding.source_contract},
                )
            )
        if binding.source_fact and binding.source_fact not in fact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="binding_source_fact_missing",
                    message="binding references an unknown source fact",
                    target=binding.binding_id,
                    details={"source_fact": binding.source_fact},
                )
            )

    for expectation in registry.binding_expectations:
        if expectation.source_artifact and expectation.source_artifact not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="binding_expectation_source_artifact_missing",
                    message="binding expectation references an unknown source artifact",
                    target=expectation.expectation_id,
                    details={"source_artifact": expectation.source_artifact},
                )
            )
        if expectation.source_contract and expectation.source_contract not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="binding_expectation_source_contract_missing",
                    message="binding expectation references an unknown source contract artifact",
                    target=expectation.expectation_id,
                    details={"source_contract": expectation.source_contract},
                )
            )
        if expectation.source_fact and expectation.source_fact not in fact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="binding_expectation_source_fact_missing",
                    message="binding expectation references an unknown source fact",
                    target=expectation.expectation_id,
                    details={"source_fact": expectation.source_fact},
                )
            )

    for context in registry.context_cards:
        if context.artifact_id and context.artifact_id not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="context_artifact_missing",
                    message="context card references an unknown artifact",
                    target=context.context_id,
                    details={"artifact_id": context.artifact_id},
                )
            )
        _source_ref_findings(findings, context.source_refs, artifact_ids, context.context_id)

    for bundle in registry.evidence_bundles:
        _bundle_reference_findings(findings, bundle, artifact_ids, fact_ids, binding_ids, context_ids, missing_ids)

    for conflict in registry.conflicts:
        if conflict.status == "unresolved":
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="evidence_conflict_unresolved",
                    message="evidence conflict remains unresolved",
                    target=conflict.conflict_id,
                    details={"severity": conflict.severity, "members": conflict.members},
                )
            )

    status = _status(findings)
    return ContractReview(
        artifact_kind="project_evidence_registry",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "registry_id": registry.registry_id,
            "project_name_known": bool(registry.project_profile.project_name),
            "project_location_count": len(registry.project_profile.locations),
            "artifact_count": len(registry.artifacts),
            "fact_count": len(registry.facts),
            "binding_count": len(registry.evidence_bindings),
            "binding_expectation_count": len(expectation_ids),
            "context_count": len(registry.context_cards),
            "bundle_count": len(registry.evidence_bundles),
            "conflict_count": len(registry.conflicts),
            "missing_evidence_count": len(registry.missing_evidence),
            "semantics": (
                "project evidence registries organize references, facts, contexts, gaps, "
                "and lifecycle evidence; they do not copy large raw data or confirm AI-extracted facts"
            ),
        },
        next_actions=_next_actions(findings),
    )


def scan_project_evidence_candidates(
    root: str | Path,
    registry_path: str | Path | None = None,
) -> ProjectEvidenceScanReport:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"scan root does not exist: {root_path}")
    registry = load_project_evidence_registry(registry_path) if registry_path else None
    registry_base = Path(registry_path).parent if registry_path else root_path
    registered_paths = _registered_paths(registry, registry_base) if registry else {}
    candidates: list[EvidenceCandidateSpec] = []
    findings: list[ContractFinding] = []

    for path in sorted(item for item in root_path.rglob("*") if item.is_file()):
        if _is_excluded(path):
            continue
        kind, reason = _classify_candidate(path)
        if kind is None:
            continue
        normalized = _normalize_path(path)
        matched = registered_paths.get(normalized)
        candidates.append(
            EvidenceCandidateSpec(
                path=str(path.relative_to(root_path) if path.is_relative_to(root_path) else path),
                artifact_kind=kind,
                reason=reason,
                registered=matched is not None,
                matched_artifact_id=matched,
            )
        )

    unregistered = [item for item in candidates if not item.registered]
    for item in unregistered:
        findings.append(
            ContractFinding(
                severity="warning",
                type="scan_candidate_unregistered",
                message="scanner found a candidate artifact not registered in project evidence",
                target=item.path,
                details={"artifact_kind": item.artifact_kind, "reason": item.reason},
            )
        )
    status = "partial" if unregistered else "pass"
    return ProjectEvidenceScanReport(
        artifact_kind="project_evidence_scan",
        status=status,
        ok=status == "pass",
        candidates=[item.model_dump(mode="json") for item in candidates],
        findings=[asdict(item) for item in findings],
        summary={
            "root": str(root_path),
            "registry": str(registry_path) if registry_path else None,
            "candidate_count": len(candidates),
            "registered_candidate_count": len(candidates) - len(unregistered),
            "unregistered_candidate_count": len(unregistered),
            "semantics": "scan is read-only and does not mutate registry files",
        },
    )


def check_evidence_gaps(path: str | Path, bundle_id: str | None = None) -> EvidenceGapReport:
    registry_path = Path(path)
    registry = load_project_evidence_registry(registry_path)
    gaps = _collect_gaps(registry, bundle_id=bundle_id, base_dir=registry_path.parent)
    blocking = [gap for gap in gaps if gap.severity == "blocking"]
    review = [gap for gap in gaps if gap.severity == "review"]
    optional = [gap for gap in gaps if gap.severity == "optional"]
    status = "fail" if blocking else "partial" if review else "pass"
    return EvidenceGapReport(
        artifact_kind="project_evidence_gap_report",
        status=status,
        ok=status == "pass",
        registry_id=registry.registry_id,
        bundle_id=bundle_id,
        blocking_gaps=[gap.model_dump(mode="json") for gap in blocking],
        review_gaps=[gap.model_dump(mode="json") for gap in review],
        optional_gaps=[gap.model_dump(mode="json") for gap in optional],
        findings=[],
        summary={
            "blocking_gap_count": len(blocking),
            "review_gap_count": len(review),
            "optional_gap_count": len(optional),
            "semantics": (
                "blocking gaps prevent validation pass or validated reuse; review and optional gaps "
                "must remain visible but may allow scoped progress"
            ),
        },
    )


def check_evidence_bundle(path: str | Path, bundle_id: str) -> EvidenceGapReport:
    return check_evidence_gaps(path, bundle_id=bundle_id)


def build_project_evidence_map(path: str | Path) -> ProjectEvidenceMapReport:
    registry = load_project_evidence_registry(path)
    gap_report = check_evidence_gaps(path)
    artifact_by_id = {item.artifact_id: item for item in registry.artifacts}
    tested_targets = sorted(
        {
            binding.model_target
            for binding in registry.evidence_bindings
            if binding.binding_kind == "source_field_to_model_target" and binding.model_target
        }
    )
    fact_targets = sorted(
        {
            binding.model_target
            for binding in registry.evidence_bindings
            if binding.binding_kind == "fact_to_model_parameter" and binding.model_target
        }
    )
    required_binding_targets = sorted(
        {
            requirement.target_id
            for context in registry.context_cards
            for requirement in context.required_evidence
            if requirement.kind == "binding"
        }
    )
    missing_required_targets = sorted(set(required_binding_targets) - set(tested_targets) - set(fact_targets))
    exempt_expectations = [item for item in registry.binding_expectations if item.policy == "exempt"]
    unknown_expectations = [item for item in registry.binding_expectations if item.policy == "unknown"]
    tests = [_test_map_entry(artifact, registry) for artifact in registry.artifacts if artifact.artifact_kind in {"raw_test_data", "cleaned_test_data", "derived_test_data"}]
    models = [_model_map_entry(context, registry) for context in registry.context_cards if context.context_kind == "model"]
    status = "fail" if gap_report.blocking_gaps else "partial" if gap_report.review_gaps else "pass"
    return ProjectEvidenceMapReport(
        artifact_kind="project_evidence_map",
        status=status,
        ok=status == "pass",
        registry_id=registry.registry_id,
        project_id=registry.project_id,
        project_scope=_project_scope(registry),
        project_profile=_project_profile_map(registry),
        artifacts=[
            {
                "artifact_id": artifact.artifact_id,
                "artifact_kind": artifact.artifact_kind,
                "path": artifact.path,
                "local_copy_path": artifact.local_copy_path,
                "external_reference": artifact.external_reference,
                "status": artifact.status,
            }
            for artifact in registry.artifacts
        ],
        tests=tests,
        models=models,
        facts=[
            {
                "fact_id": fact.fact_id,
                "fact_kind": fact.fact_kind,
                "unit": fact.unit,
                "behavior": fact.behavior.kind,
                "review_state": fact.review.state,
                "source_count": len(fact.source_refs),
            }
            for fact in registry.facts
        ],
        bindings=[
            {
                "binding_id": binding.binding_id,
                "binding_kind": binding.binding_kind,
                "authority": binding.authority,
                "source_artifact": binding.source_artifact,
                "source_contract": binding.source_contract,
                "source_field": binding.source_field,
                "source_fact": binding.source_fact,
                "canonical_quantity": binding.canonical_quantity,
                "unit": binding.unit,
                "model_target": binding.model_target,
                "model_part": binding.model_part,
                "validation_role": binding.validation_role,
                "status": binding.status,
            }
            for binding in registry.evidence_bindings
        ],
        binding_expectations=[
            {
                "expectation_id": expectation.expectation_id,
                "subject_kind": expectation.subject_kind,
                "subject_id": expectation.subject_id,
                "policy": expectation.policy,
                "source_artifact": expectation.source_artifact,
                "source_contract": expectation.source_contract,
                "source_field": expectation.source_field,
                "source_fact": expectation.source_fact,
                "model_target": expectation.model_target,
                "model_part": expectation.model_part,
                "required_for": expectation.required_for,
                "exemption_reason": expectation.exemption_reason,
            }
            for expectation in registry.binding_expectations
        ],
        coverage_summary={
            "tested_model_targets": tested_targets,
            "fact_bound_model_targets": fact_targets,
            "required_binding_targets": required_binding_targets,
            "missing_required_targets": missing_required_targets,
            "binding_expectation_count": len(registry.binding_expectations),
            "must_bind_expectation_count": sum(1 for item in registry.binding_expectations if item.policy == "must_bind"),
            "exempt_binding_expectation_count": len(exempt_expectations),
            "unknown_binding_expectation_count": len(unknown_expectations),
            "unresolved_binding_gap_count": sum(
                1
                for gap in [*gap_report.blocking_gaps, *gap_report.review_gaps, *gap_report.optional_gaps]
                if "binding" in gap.get("gap_type", "")
            ),
            "model_count": len(models),
            "test_artifact_count": len(tests),
            "source_document_count": sum(1 for item in registry.artifacts if item.artifact_kind == "source_document"),
        },
        gaps={
            "blocking": gap_report.blocking_gaps,
            "review": gap_report.review_gaps,
            "optional": gap_report.optional_gaps,
        },
        summary={
            "semantics": (
                "project evidence maps are navigation and onboarding summaries; "
                "they do not replace validation reports or prove physical correctness"
            ),
            "artifact_count": len(registry.artifacts),
            "fact_count": len(registry.facts),
            "binding_count": len(registry.evidence_bindings),
            "binding_expectation_count": len(registry.binding_expectations),
            "context_count": len(registry.context_cards),
            "bundle_count": len(registry.evidence_bundles),
        },
    )


def has_blocking_evidence_gaps(path: str | Path, bundle_id: str | None = None) -> bool:
    return bool(check_evidence_gaps(path, bundle_id=bundle_id).blocking_gaps)


def _collect_gaps(
    registry: ProjectEvidenceRegistrySpec,
    bundle_id: str | None = None,
    base_dir: Path | None = None,
) -> list[EvidenceGapSpec]:
    artifacts = {item.artifact_id: item for item in registry.artifacts}
    facts = {item.fact_id: item for item in registry.facts}
    bindings = {item.binding_id: item for item in registry.evidence_bindings}
    contexts = {item.context_id: item for item in registry.context_cards}
    bundles = {item.bundle_id: item for item in registry.evidence_bundles}
    missing = {item.missing_id: item for item in registry.missing_evidence}
    expectations = {item.expectation_id: item for item in registry.binding_expectations}
    gaps: list[EvidenceGapSpec] = []
    gaps.extend(_project_profile_gaps(registry))

    target_bundles: Iterable[EvidenceBundleSpec]
    if bundle_id:
        bundle = bundles.get(bundle_id)
        if bundle is None:
            return [
                _gap(
                    "bundle_missing",
                    "blocking",
                    "bundle_missing",
                    bundle_id,
                    "requested evidence bundle is not registered",
                    ["registry"],
                )
            ]
        target_bundles = [bundle]
    else:
        target_bundles = bundles.values()

    target_contexts: dict[str, ContextCardSpec] = {}
    if bundle_id:
        for bundle in target_bundles:
            if bundle.model_context and bundle.model_context in contexts:
                target_contexts[bundle.model_context] = contexts[bundle.model_context]
            for context_id in bundle.contexts:
                if context_id in contexts:
                    target_contexts[context_id] = contexts[context_id]
    else:
        target_contexts = contexts

    for context in target_contexts.values():
        for requirement in context.required_evidence:
            known = _requirement_exists(requirement.kind, requirement.target_id, artifacts, facts, bindings, contexts, bundles)
            if not known:
                gaps.append(
                    _gap(
                        requirement.requirement_id or f"missing_{requirement.kind}_{requirement.target_id}",
                        requirement.missing_severity,
                        f"missing_required_{requirement.kind}",
                        requirement.target_id,
                        requirement.reason or "required evidence is not registered",
                        [f"context:{context.context_id}"],
                        _suggested_search(requirement.kind),
                    )
                )

    target_expectations = _target_binding_expectations(
        expectations.values(),
        target_bundles,
        bundle_id=bundle_id,
        target_context_ids=set(target_contexts),
    )
    gaps.extend(_binding_expectation_gaps(target_expectations, facts, bindings))
    gaps.extend(_physical_parameter_binding_gaps(facts, bindings, target_expectations))
    if base_dir is not None:
        gaps.extend(_test_contract_binding_gaps(registry, base_dir, target_expectations))

    for bundle in target_bundles:
        for artifact_id in bundle.artifacts + bundle.contracts + bundle.validation_reports:
            if artifact_id not in artifacts:
                gaps.append(
                    _gap(
                        f"bundle_missing_artifact_{artifact_id}",
                        "blocking",
                        "bundle_artifact_missing",
                        artifact_id,
                        "evidence bundle references an unknown artifact",
                        [f"bundle:{bundle.bundle_id}"],
                    )
                )
        for fact_id in bundle.facts:
            if fact_id not in facts:
                gaps.append(
                    _gap(
                        f"bundle_missing_fact_{fact_id}",
                        "blocking",
                        "bundle_fact_missing",
                        fact_id,
                        "evidence bundle references an unknown fact",
                        [f"bundle:{bundle.bundle_id}"],
                        _suggested_search("fact"),
                    )
                )
        for binding_id in bundle.bindings:
            if binding_id not in bindings:
                gaps.append(
                    _gap(
                        f"bundle_missing_binding_{binding_id}",
                        "blocking",
                        "bundle_binding_missing",
                        binding_id,
                        "evidence bundle references an unknown binding",
                        [f"bundle:{bundle.bundle_id}"],
                    )
                )
        for context_id in ([bundle.model_context] if bundle.model_context else []) + bundle.contexts:
            if context_id not in contexts:
                gaps.append(
                    _gap(
                        f"bundle_missing_context_{context_id}",
                        "blocking",
                        "bundle_context_missing",
                        str(context_id),
                        "evidence bundle references an unknown context",
                        [f"bundle:{bundle.bundle_id}"],
                    )
                )
        for missing_id in bundle.missing_evidence + bundle.open_gaps:
            item = missing.get(missing_id)
            if item is not None and item.status == "unresolved":
                gaps.append(
                    _gap(
                        item.missing_id,
                        item.severity,
                        "missing_evidence_unresolved",
                        item.target,
                        item.source_missing_reason or "required evidence remains unresolved",
                        [f"bundle:{bundle.bundle_id}", *item.required_by],
                        item.search_attempts,
                    )
                )

    for conflict in registry.conflicts:
        if conflict.status == "unresolved":
            if not bundle_id or any(member in _bundle_member_ids(bundle) for bundle in target_bundles for member in conflict.members):
                gaps.append(
                    _gap(
                        conflict.conflict_id,
                        conflict.severity,
                        "evidence_conflict_unresolved",
                        ",".join(conflict.members),
                        conflict.reason,
                        ["conflict"],
                    )
                )

    if not bundle_id:
        for item in registry.missing_evidence:
            if item.status == "unresolved":
                gaps.append(
                    _gap(
                        item.missing_id,
                        item.severity,
                        "missing_evidence_unresolved",
                        item.target,
                        item.source_missing_reason or "required evidence remains unresolved",
                        item.required_by,
                        item.search_attempts,
                    )
                )
    return _dedupe_gaps(gaps)


def _requirement_exists(
    kind: str,
    target_id: str,
    artifacts: dict[str, Any],
    facts: dict[str, Any],
    bindings: dict[str, Any],
    contexts: dict[str, Any],
    bundles: dict[str, Any],
) -> bool:
    if kind == "fact":
        return target_id in facts
    if kind in {"artifact", "validation_report"}:
        return target_id in artifacts
    if kind == "context":
        return target_id in contexts
    if kind == "binding":
        return target_id in bindings or any(
            getattr(binding, "model_target", None) == target_id for binding in bindings.values()
        )
    if kind == "bundle":
        return target_id in bundles
    return False


def _project_profile_gaps(registry: ProjectEvidenceRegistrySpec) -> list[EvidenceGapSpec]:
    profile = registry.project_profile
    gaps: list[EvidenceGapSpec] = []
    if not profile.project_name:
        gaps.append(
            _gap(
                "project_profile_project_name_missing",
                "review",
                "project_profile_project_name_unknown" if profile.project_name_unknown_reason else "project_profile_project_name_missing",
                "project_name",
                profile.project_name_unknown_reason or "project name is not recorded",
                ["registry:project_profile"],
                ["search project reports, test plans, folder names, and human-provided project notes"],
            )
        )
    run_period = profile.run_period
    has_run_period = bool(run_period.run_started_at or run_period.run_ended_at or run_period.coverage_period)
    if not has_run_period:
        gaps.append(
            _gap(
                "project_profile_run_period_missing",
                "review",
                "project_profile_run_period_unknown" if run_period.unknown_reason else "project_profile_run_period_missing",
                "project_run_period",
                run_period.unknown_reason or "project run period is not recorded",
                ["registry:project_profile"],
                ["search test logs, report dates, validation plans, and data-file timestamps"],
            )
        )
    if not profile.locations:
        gaps.append(
            _gap(
                "project_profile_location_missing",
                "review",
                "project_profile_location_unknown" if profile.location_unknown_reason else "project_profile_location_missing",
                "project_locations",
                profile.location_unknown_reason or "project run location is not recorded",
                ["registry:project_profile"],
                ["search source reports, lab/testbench notes, and project handoff documents"],
            )
        )
    for location in profile.locations:
        if location.unknown_reason:
            gaps.append(
                _gap(
                    f"project_profile_location_unknown_{location.location_id}",
                    "review",
                    "project_profile_location_unknown",
                    location.location_id,
                    location.unknown_reason,
                    ["registry:project_profile"],
                    ["replace unknown location placeholder with sourced location evidence when available"],
                )
            )
    if _project_profile_has_known_values(profile) and not _project_profile_has_source_refs(profile):
        gaps.append(
            _gap(
                "project_profile_source_refs_missing",
                "review",
                "project_profile_source_refs_missing",
                "project_profile",
                "project profile has known basic information but no source reference",
                ["registry:project_profile"],
                ["add source_refs from reports, plans, contracts, or human-provided evidence notes"],
            )
        )
    return gaps


def _project_profile_has_known_values(profile: Any) -> bool:
    return bool(
        profile.project_name
        or profile.owner
        or profile.customer
        or profile.objective
        or profile.run_period.run_started_at
        or profile.run_period.run_ended_at
        or profile.run_period.coverage_period
        or profile.locations
    )


def _project_profile_has_source_refs(profile: Any) -> bool:
    return bool(
        profile.source_refs
        or profile.run_period.source_refs
        or any(location.source_refs for location in profile.locations)
    )


def _target_binding_expectations(
    expectations: Iterable[BindingExpectationSpec],
    target_bundles: Iterable[EvidenceBundleSpec],
    *,
    bundle_id: str | None,
    target_context_ids: set[str],
) -> list[BindingExpectationSpec]:
    if bundle_id is None:
        return list(expectations)
    bundle_list = list(target_bundles)
    bundle_member_ids = set().union(*(_bundle_member_ids(bundle) for bundle in bundle_list)) if bundle_list else set()
    bundle_refs = {bundle_id, f"bundle:{bundle_id}", *target_context_ids, *(f"context:{item}" for item in target_context_ids)}
    selected: list[BindingExpectationSpec] = []
    for expectation in expectations:
        if any(ref in bundle_refs for ref in expectation.required_for):
            selected.append(expectation)
            continue
        referenced_ids = {
            expectation.source_artifact,
            expectation.source_contract,
            expectation.source_fact,
            expectation.model_target,
            expectation.subject_id,
        }
        if any(ref in bundle_member_ids for ref in referenced_ids if ref):
            selected.append(expectation)
    return selected


def _binding_expectation_gaps(
    expectations: Iterable[BindingExpectationSpec],
    facts: dict[str, Any],
    bindings: dict[str, Any],
) -> list[EvidenceGapSpec]:
    gaps: list[EvidenceGapSpec] = []
    for expectation in expectations:
        if expectation.policy == "exempt":
            continue
        if expectation.policy == "unknown":
            gaps.append(
                _gap(
                    f"binding_expectation_unknown_{expectation.expectation_id}",
                    "review",
                    "binding_expectation_unknown",
                    expectation.subject_id,
                    "binding expectation is still unknown and needs AI review",
                    expectation.required_for,
                    ["review source files and decide must_bind or exempt with a reason"],
                    {"expectation_id": expectation.expectation_id},
                )
            )
            continue
        if not _expectation_has_binding(expectation, facts, bindings):
            gaps.append(
                _gap(
                    f"binding_expectation_unmet_{expectation.expectation_id}",
                    expectation.missing_severity,
                    "binding_expectation_unmet",
                    expectation.subject_id,
                    "expected model/test binding is missing from project evidence",
                    expectation.required_for,
                    ["add evidence_bindings entry or mark binding_expectation exempt with reason"],
                    {"expectation_id": expectation.expectation_id},
                )
            )
    return gaps


def _physical_parameter_binding_gaps(
    facts: dict[str, Any],
    bindings: dict[str, Any],
    expectations: Iterable[BindingExpectationSpec],
) -> list[EvidenceGapSpec]:
    expectation_by_fact = {
        expectation.source_fact or expectation.subject_id: expectation
        for expectation in expectations
        if expectation.subject_kind == "engineering_fact"
    }
    gaps: list[EvidenceGapSpec] = []
    for fact_id, fact in facts.items():
        if fact.fact_kind != "physical_parameter":
            continue
        expectation = expectation_by_fact.get(fact_id)
        if expectation is not None:
            continue
        if _fact_has_binding(fact_id, fact, bindings):
            continue
        gaps.append(
            _gap(
                f"physical_parameter_binding_unreviewed_{fact_id}",
                "review",
                "physical_parameter_binding_unreviewed",
                fact_id,
                "physical parameter has no model binding and no explicit exemption or binding expectation",
                ["registry:facts"],
                ["add fact-to-model binding, add binding expectation, or record exemption reason"],
            )
        )
    return gaps


def _test_contract_binding_gaps(
    registry: ProjectEvidenceRegistrySpec,
    base_dir: Path,
    expectations: Iterable[BindingExpectationSpec],
) -> list[EvidenceGapSpec]:
    expectations_list = list(expectations)
    gaps: list[EvidenceGapSpec] = []
    binding_records = registry.evidence_bindings
    for artifact in registry.artifacts:
        if artifact.artifact_kind != "test_file_contract" or not artifact.path:
            continue
        contract_path = _resolve_path(base_dir, artifact.path)
        if not contract_path.exists():
            continue
        try:
            from physicsguard.core.test_file_contract import resolve_test_file_contract

            resolved = resolve_test_file_contract(contract_path)
        except Exception as exc:
            gaps.append(
                _gap(
                    f"test_contract_binding_scan_failed_{artifact.artifact_id}",
                    "review",
                    "test_contract_binding_scan_failed",
                    artifact.artifact_id,
                    "registered test-file contract could not be inspected for binding completeness",
                    [f"artifact:{artifact.artifact_id}"],
                    ["run testfile contract-check and repair the contract before project evidence gap-check"],
                    {"error": str(exc)},
                )
            )
            continue
        if resolved.role_matrix is None:
            continue
        for role in resolved.role_matrix.value.roles:
            if role.coverage_status != "covered":
                continue
            source_id = role.source_id
            if _test_field_exempted(artifact.artifact_id, source_id, expectations_list):
                continue
            if _source_field_has_binding(artifact.artifact_id, source_id, binding_records):
                continue
            gaps.append(
                _gap(
                    f"test_field_project_binding_missing_{artifact.artifact_id}_{_gap_safe_id(source_id)}",
                    "review",
                    "test_field_project_binding_missing",
                    source_id,
                    "covered test field has no project-level binding summary or explicit exemption",
                    [f"artifact:{artifact.artifact_id}", f"contract:{resolved.contract.contract_id}"],
                    ["add evidence binding summary or add binding expectation exemption with reason"],
                    {
                        "artifact_id": artifact.artifact_id,
                        "contract_id": resolved.contract.contract_id,
                        "model_role": role.model_role,
                        "coverage_status": role.coverage_status,
                    },
                )
            )
    return gaps


def _expectation_has_binding(
    expectation: BindingExpectationSpec,
    facts: dict[str, Any],
    bindings: dict[str, Any],
) -> bool:
    if expectation.subject_kind == "engineering_fact":
        fact_id = expectation.source_fact or expectation.subject_id
        fact = facts.get(fact_id)
        return fact is not None and _fact_has_binding(
            fact_id,
            fact,
            bindings,
            model_target=expectation.model_target,
        )
    if expectation.subject_kind == "test_field":
        source_field = expectation.source_field or expectation.subject_id
        return any(
            binding.source_field == source_field
            and (expectation.source_contract is None or binding.source_contract == expectation.source_contract)
            and (expectation.model_target is None or binding.model_target == expectation.model_target)
            for binding in bindings.values()
        )
    if expectation.subject_kind == "model_target":
        model_target = expectation.model_target or expectation.subject_id
        return _model_target_has_binding(model_target, facts, bindings)
    if expectation.subject_kind == "artifact":
        return any(
            binding.source_artifact == expectation.subject_id
            or binding.source_contract == expectation.subject_id
            or binding.authority == expectation.subject_id
            for binding in bindings.values()
        )
    return any(
        expectation.subject_id
        in {
            binding.source_artifact,
            binding.source_contract,
            binding.source_field,
            binding.source_fact,
            binding.model_target,
        }
        for binding in bindings.values()
    )


def _fact_has_binding(
    fact_id: str,
    fact: Any,
    bindings: dict[str, Any],
    *,
    model_target: str | None = None,
) -> bool:
    fact_targets = set(getattr(fact.bindings, "model_targets", []))
    if model_target:
        if model_target in fact_targets:
            return True
    elif fact_targets:
        return True
    return any(
        binding.source_fact == fact_id and (model_target is None or binding.model_target == model_target)
        for binding in bindings.values()
    )


def _model_target_has_binding(model_target: str, facts: dict[str, Any], bindings: dict[str, Any]) -> bool:
    if any(binding.model_target == model_target for binding in bindings.values()):
        return True
    return any(model_target in getattr(fact.bindings, "model_targets", []) for fact in facts.values())


def _test_field_exempted(
    artifact_id: str,
    source_field: str,
    expectations: Iterable[BindingExpectationSpec],
) -> bool:
    return any(
        expectation.policy == "exempt"
        and expectation.subject_kind == "test_field"
        and (expectation.source_field or expectation.subject_id) == source_field
        and (expectation.source_contract is None or expectation.source_contract == artifact_id)
        for expectation in expectations
    )


def _source_field_has_binding(artifact_id: str, source_field: str, bindings: Iterable[Any]) -> bool:
    return any(
        binding.source_field == source_field
        and (binding.source_contract in {None, artifact_id} or binding.source_artifact == artifact_id)
        for binding in bindings
    )


def _source_ref_findings(
    findings: list[ContractFinding],
    source_refs,
    artifact_ids: set[str],
    target: str,
) -> None:
    for source in source_refs:
        if source.artifact_id and source.artifact_id not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="source_reference_artifact_missing",
                    message="source reference points to an unknown artifact",
                    target=target,
                    details={"artifact_id": source.artifact_id},
                )
            )


def _lineage_reference_findings(findings: list[ContractFinding], artifact, artifact_ids: set[str]) -> None:
    for field_name in ("derived_from", "split_from", "merged_from"):
        for reference in getattr(artifact.lineage, field_name):
            if reference not in artifact_ids:
                findings.append(
                    ContractFinding(
                        severity="warning",
                        type="artifact_lineage_reference_missing",
                        message="artifact lineage references an unknown artifact",
                        target=artifact.artifact_id,
                        details={"field": field_name, "artifact_id": reference},
                    )
                )


def _lineage_cycle_findings(registry: ProjectEvidenceRegistrySpec) -> list[ContractFinding]:
    edges = {
        item.artifact_id: set(item.lineage.derived_from + item.lineage.split_from + item.lineage.merged_from)
        for item in registry.artifacts
    }
    findings: list[ContractFinding] = []

    def visit(node: str, stack: list[str], seen: set[str]) -> None:
        if node in stack:
            cycle = stack[stack.index(node) :] + [node]
            findings.append(
                ContractFinding(
                    severity="error",
                    type="artifact_lineage_cycle",
                    message="artifact lineage contains a cycle",
                    target=node,
                    details={"cycle": cycle},
                )
            )
            return
        if node in seen:
            return
        seen.add(node)
        for parent in edges.get(node, set()):
            visit(parent, [*stack, node], seen)

    seen: set[str] = set()
    for artifact_id in edges:
        visit(artifact_id, [], seen)
    return findings


def _piecewise_overlap_findings(fact_id: str, segments) -> list[ContractFinding]:
    intervals: list[tuple[float, float, str]] = []
    for segment in segments:
        if segment.valid_from_test_time_s is None or segment.valid_until_test_time_s is None:
            continue
        intervals.append((segment.valid_from_test_time_s, segment.valid_until_test_time_s, segment.segment_id))
    intervals.sort()
    findings: list[ContractFinding] = []
    for left, right in zip(intervals, intervals[1:]):
        if left[1] > right[0]:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="piecewise_segment_overlap",
                    message="piecewise fact segments overlap in test time",
                    target=fact_id,
                    details={"left": left[2], "right": right[2]},
                )
            )
    return findings


def _bundle_reference_findings(
    findings: list[ContractFinding],
    bundle: EvidenceBundleSpec,
    artifact_ids: set[str],
    fact_ids: set[str],
    binding_ids: set[str],
    context_ids: set[str],
    missing_ids: set[str],
) -> None:
    for artifact_id in bundle.artifacts + bundle.contracts + bundle.validation_reports:
        if artifact_id not in artifact_ids:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="evidence_bundle_artifact_missing",
                    message="evidence bundle references an unknown artifact",
                    target=bundle.bundle_id,
                    details={"artifact_id": artifact_id},
                )
            )
    for fact_id in bundle.facts:
        if fact_id not in fact_ids:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="evidence_bundle_fact_missing",
                    message="evidence bundle references an unknown fact",
                    target=bundle.bundle_id,
                    details={"fact_id": fact_id},
                )
            )
    for binding_id in bundle.bindings:
        if binding_id not in binding_ids:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="evidence_bundle_binding_missing",
                    message="evidence bundle references an unknown binding",
                    target=bundle.bundle_id,
                    details={"binding_id": binding_id},
                )
            )
    for context_id in ([bundle.model_context] if bundle.model_context else []) + bundle.contexts:
        if context_id not in context_ids:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="evidence_bundle_context_missing",
                    message="evidence bundle references an unknown context",
                    target=bundle.bundle_id,
                    details={"context_id": context_id},
                )
            )
    for missing_id in bundle.open_gaps + bundle.missing_evidence:
        if missing_id not in missing_ids:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="evidence_bundle_gap_record_missing",
                    message="evidence bundle references an unknown missing evidence record",
                    target=bundle.bundle_id,
                    details={"missing_id": missing_id},
                )
            )


def _registered_paths(registry: ProjectEvidenceRegistrySpec | None, base_dir: Path) -> dict[Path, str]:
    paths: dict[Path, str] = {}
    if registry is None:
        return paths
    for artifact in registry.artifacts:
        if artifact.path:
            paths[_normalize_path(_resolve_path(base_dir, artifact.path))] = artifact.artifact_id
    return paths


def _classify_candidate(path: Path) -> tuple[ArtifactKind | None, str]:
    suffix = path.suffix.lower()
    if suffix in SOURCE_DOCUMENT_SUFFIXES:
        return "source_document", f"{suffix} source document may contain engineering facts"
    if suffix in TEST_DATA_SUFFIXES:
        return "raw_test_data", f"{suffix} file may be test data"
    if suffix not in YAML_SUFFIXES:
        return None, ""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return "other", "YAML file could not be classified but may be a project artifact"
    if not isinstance(data, dict):
        return None, ""
    if "registry_id" in data and "artifacts" in data:
        return "other", "project evidence registry"
    if "contract_id" in data:
        return "test_file_contract", "test-file contract YAML"
    if "logical_dataset_id" in data:
        return "logical_dataset", "logical dataset YAML"
    if "relations" in data and "project_id" in data:
        return "relation_index", "test-file relation index YAML"
    if "validation_id" in data and "audit_file" in data:
        return "validation_plan", "model-dataset validation plan YAML"
    if "artifact_kind" in data and data.get("artifact_kind") == "model_dataset_validation":
        return "validation_report", "model-dataset validation report YAML"
    if data.get("artifact_kind") == "physicsguard_validation_depth_receipt":
        return "validation_depth_receipt", "native PhysicsGuard validation-depth receipt YAML"
    if "series_id" in data and "points" in data:
        return "observed_series", "bounded observed series YAML"
    if data.get("artifact_kind") == "physicsguard_signal_mapping_review":
        return "signal_mapping_review", "PhysicsGuard signal-mapping review YAML"
    if "library_id" in data and "entries" in data:
        return "model_library", "model library YAML"
    if "audit_name" in data or "hierarchy" in data or "system" in data:
        return "model_file", "PhysicsGuard model or audit YAML"
    if "parameters" in data:
        return "parameter_catalog", "parameter catalog YAML"
    return None, ""


def _is_excluded(path: Path) -> bool:
    return any(part in SCAN_EXCLUDED_DIRS for part in path.parts)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _normalize_path(path: Path) -> Path:
    return path.resolve(strict=False)


def _bundle_member_ids(bundle: EvidenceBundleSpec) -> set[str]:
    return set(
        bundle.artifacts
        + bundle.facts
        + bundle.bindings
        + bundle.contexts
        + bundle.contracts
        + bundle.validation_reports
        + bundle.open_gaps
        + bundle.missing_evidence
        + ([bundle.model_context] if bundle.model_context else [])
    )


def _gap(
    gap_id: str,
    severity: GapSeverity,
    gap_type: str,
    target: str,
    reason: str,
    required_by: list[str],
    suggested_search: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> EvidenceGapSpec:
    return EvidenceGapSpec(
        gap_id=_gap_safe_id(gap_id),
        severity=severity,
        gap_type=gap_type,
        target=target,
        reason=reason,
        required_by=required_by,
        suggested_search=suggested_search or [],
        metadata=metadata or {},
    )


def _gap_safe_id(value: str) -> str:
    safe = []
    for char in value:
        safe.append(char if char.isalnum() or char in {"_", "-"} else "_")
    return "".join(safe)


def _suggested_search(kind: str) -> list[str]:
    if kind == "fact":
        return [
            "check registered engineering facts",
            "search registered source documents",
            "inspect model parameters",
            "inspect test contracts and manifests",
            "ask for human confirmation if no source is available",
        ]
    if kind == "artifact":
        return ["scan project files", "check external references", "ask for the missing file path"]
    if kind == "context":
        return ["create or update the relevant model/testbench/test-object context card"]
    if kind == "binding":
        return [
            "inspect test-file contracts",
            "inspect project evidence binding records",
            "inspect model context required targets",
            "create a binding record that cites its authority",
        ]
    return ["inspect project evidence registry"]


def _project_scope(registry: ProjectEvidenceRegistrySpec) -> dict[str, Any]:
    scopes = [context.intended_scope.model_dump(mode="json", exclude_none=True) for context in registry.context_cards]
    return {
        "project_id": registry.project_id,
        "project_name": registry.project_profile.project_name,
        "context_scopes": scopes,
    }


def _project_profile_map(registry: ProjectEvidenceRegistrySpec) -> dict[str, Any]:
    profile = registry.project_profile
    return {
        "project_name": profile.project_name,
        "project_name_unknown_reason": profile.project_name_unknown_reason,
        "owner": profile.owner,
        "customer": profile.customer,
        "objective": profile.objective,
        "run_period": profile.run_period.model_dump(mode="json", exclude_none=True),
        "locations": [location.model_dump(mode="json", exclude_none=True) for location in profile.locations],
        "location_unknown_reason": profile.location_unknown_reason,
        "source_count": (
            len(profile.source_refs)
            + len(profile.run_period.source_refs)
            + sum(len(location.source_refs) for location in profile.locations)
        ),
        "review_state": profile.review.state,
    }


def _test_map_entry(artifact, registry: ProjectEvidenceRegistrySpec) -> dict[str, Any]:
    bindings = [
        binding
        for binding in registry.evidence_bindings
        if binding.source_artifact == artifact.artifact_id or binding.source_contract == artifact.artifact_id
    ]
    expectations = [
        expectation
        for expectation in registry.binding_expectations
        if expectation.source_artifact == artifact.artifact_id or expectation.source_contract == artifact.artifact_id
    ]
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_kind": artifact.artifact_kind,
        "time_context": artifact.time_context.model_dump(mode="json", exclude_none=True),
        "applies_to": artifact.applies_to.model_dump(mode="json", exclude_none=True),
        "lineage": artifact.lineage.model_dump(mode="json", exclude_none=True),
        "measured_quantities": sorted({binding.canonical_quantity for binding in bindings if binding.canonical_quantity}),
        "model_targets": sorted({binding.model_target for binding in bindings if binding.model_target}),
        "binding_ids": [binding.binding_id for binding in bindings],
        "binding_expectations": [
            {
                "expectation_id": expectation.expectation_id,
                "subject_id": expectation.subject_id,
                "policy": expectation.policy,
                "model_target": expectation.model_target,
                "exemption_reason": expectation.exemption_reason,
            }
            for expectation in expectations
        ],
    }


def _model_map_entry(context: ContextCardSpec, registry: ProjectEvidenceRegistrySpec) -> dict[str, Any]:
    target_to_binding = {
        binding.model_target: binding.binding_id
        for binding in registry.evidence_bindings
        if binding.model_target
    }
    parts = []
    for part in context.model_parts:
        covered = sorted(target for target in part.model_targets if target in target_to_binding)
        uncovered = sorted(target for target in part.model_targets if target not in target_to_binding)
        parts.append(
            {
                "part_id": part.part_id,
                "name": part.name,
                "description": part.description,
                "model_targets": part.model_targets,
                "covered_targets": covered,
                "uncovered_targets": uncovered,
            }
        )
    required_bindings = [
        requirement.target_id for requirement in context.required_evidence if requirement.kind == "binding"
    ]
    return {
        "context_id": context.context_id,
        "artifact_id": context.artifact_id,
        "physicsguard_version": context.physicsguard_version,
        "intended_scope": context.intended_scope.model_dump(mode="json", exclude_none=True),
        "known_invalid_scope": context.known_invalid_scope,
        "model_parts": parts,
        "required_binding_targets": required_bindings,
        "covered_required_targets": sorted(target for target in required_bindings if target in target_to_binding),
        "uncovered_required_targets": sorted(target for target in required_bindings if target not in target_to_binding),
    }


def _dedupe_gaps(gaps: list[EvidenceGapSpec]) -> list[EvidenceGapSpec]:
    seen: set[tuple[str, str, str]] = set()
    result: list[EvidenceGapSpec] = []
    for gap in gaps:
        key = (gap.gap_type, gap.target, gap.severity)
        if key in seen:
            continue
        seen.add(key)
        result.append(gap)
    return result


def _status(findings: list[ContractFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "partial"
    return "pass"


def _next_actions(findings: list[ContractFinding]) -> list[str]:
    actions: list[str] = []
    for finding in findings:
        if finding.type == "artifact_path_missing":
            actions.append("fix the registered artifact path or use an external_reference")
        elif finding.type == "artifact_lineage_missing":
            actions.append("record artifact lineage or original_source_missing_reason")
        elif finding.type == "artifact_lineage_cycle":
            actions.append("break the artifact lineage cycle")
        elif finding.type.endswith("_missing"):
            actions.append("add the missing evidence record or update stale references")
        elif finding.type == "piecewise_segment_overlap":
            actions.append("repair overlapping piecewise fact segments")
        elif finding.type == "evidence_conflict_unresolved":
            actions.append("resolve the evidence conflict or keep it visible as a blocking/review gap")
    return sorted(set(actions))


__all__ = [
    "EvidenceGapReport",
    "ProjectEvidenceScanReport",
    "ProjectEvidenceMapReport",
    "build_project_evidence_map",
    "check_evidence_bundle",
    "check_evidence_gaps",
    "check_project_evidence_registry",
    "has_blocking_evidence_gaps",
    "scan_project_evidence_candidates",
]
