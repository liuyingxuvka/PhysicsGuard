"""Fail-closed parameter coverage checks for test-file contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional

from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.parameter_coverage import (
    CoveragePolicySpec,
    MappingEdgeSpec,
    ParameterCatalogSpec,
    ParameterMappingEdgesSpec,
    ParameterRoleMatrixSpec,
    RoleAssignmentSpec,
)


@dataclass(frozen=True)
class ContractFinding:
    severity: str
    type: str
    message: str
    source_id: Optional[str] = None
    field_name: Optional[str] = None
    target: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContractReview:
    artifact_kind: str
    status: str
    ok: bool
    findings: list[ContractFinding]
    summary: dict[str, Any]
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_parameter_coverage(
    *,
    manifest: DataFileManifestSpec,
    catalog: ParameterCatalogSpec | None,
    role_matrix: ParameterRoleMatrixSpec | None,
    mapping_edges: ParameterMappingEdgesSpec | None,
    policy: CoveragePolicySpec | None = None,
    valid_targets: Mapping[str, set[str]] | None = None,
) -> ContractReview:
    """Check that every manifest field has an explicit role and disposition."""

    resolved_policy = policy or CoveragePolicySpec()
    findings: list[ContractFinding] = []
    edges = mapping_edges or ParameterMappingEdgesSpec()
    if catalog is None:
        findings.append(
            ContractFinding(
                severity="error",
                type="missing_parameter_catalog",
                message="test-file contract must provide a parameter catalog",
            )
        )
        catalog = ParameterCatalogSpec(parameters=[])
    if role_matrix is None:
        findings.append(
            ContractFinding(
                severity="error",
                type="missing_role_matrix",
                message="test-file contract must provide a parameter role matrix",
            )
        )
        role_matrix = ParameterRoleMatrixSpec(roles=[])

    manifest_fields = {field.name for field in manifest.fields}
    catalog_by_source = {item.source_id: item for item in catalog.parameters}
    catalog_by_field = {item.field_name: item for item in catalog.parameters}
    roles_by_source = {item.source_id: item for item in role_matrix.roles}
    edges_by_source: dict[str, list[MappingEdgeSpec]] = {}
    for edge in edges.edges:
        edges_by_source.setdefault(edge.source_id, []).append(edge)

    if resolved_policy.require_all_manifest_fields:
        missing_fields = sorted(manifest_fields - set(catalog_by_field))
        for field_name in missing_fields:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="manifest_field_missing_from_catalog",
                    message="manifest field is not present in parameter catalog",
                    field_name=field_name,
                )
            )

    extra_catalog_fields = sorted(set(catalog_by_field) - manifest_fields)
    for field_name in extra_catalog_fields:
        entry = catalog_by_field[field_name]
        findings.append(
            ContractFinding(
                severity="warning",
                type="catalog_field_not_in_manifest",
                message="catalog entry does not match a field in this manifest",
                source_id=entry.source_id,
                field_name=field_name,
            )
        )

    for entry in catalog.parameters:
        role = roles_by_source.get(entry.source_id)
        if role is None:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="catalog_entry_missing_role",
                    message="catalog entry has no role/disposition row",
                    source_id=entry.source_id,
                    field_name=entry.field_name,
                )
            )
            continue
        findings.extend(_role_findings(entry.field_name, role, edges_by_source, resolved_policy))

    findings.extend(_mapping_edge_findings(edges, catalog_by_source, valid_targets, resolved_policy))

    status = _status(findings)
    return ContractReview(
        artifact_kind="parameter_coverage",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "manifest_field_count": len(manifest.fields),
            "catalog_entry_count": len(catalog.parameters),
            "role_count": len(role_matrix.roles),
            "mapping_edge_count": len(edges.edges),
            "error_count": sum(1 for finding in findings if finding.severity == "error"),
            "warning_count": sum(1 for finding in findings if finding.severity == "warning"),
            "semantics": (
                "coverage pass means file fields have explicit classification, disposition, "
                "and reviewable mappings; it does not prove physical correctness and does "
                "not mutate observed values"
            ),
        },
        next_actions=_next_actions(findings),
    )


def _role_findings(
    field_name: str,
    role: RoleAssignmentSpec,
    edges_by_source: Mapping[str, list[MappingEdgeSpec]],
    policy: CoveragePolicySpec,
) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    if role.coverage_status in {"missing", "unmapped"}:
        findings.append(
            ContractFinding(
                severity="error",
                type="uncovered_role_disposition",
                message="role matrix marks this source field as missing or unmapped",
                source_id=role.source_id,
                field_name=field_name,
            )
        )
    if role.coverage_status == "review_required" and not policy.allow_review_required:
        findings.append(
            ContractFinding(
                severity="warning",
                type="role_review_required",
                message="role row requires human review before broad AI analysis claims",
                source_id=role.source_id,
                field_name=field_name,
            )
        )
    if role.coverage_status == "planned_child_model" and not policy.allow_unmapped_planned:
        findings.append(
            ContractFinding(
                severity="error",
                type="planned_child_model_not_allowed",
                message="coverage policy does not allow planned child model as disposition",
                source_id=role.source_id,
                field_name=field_name,
            )
        )
    if role.coverage_status == "planned_child_model" and policy.allow_unmapped_planned:
        findings.append(
            ContractFinding(
                severity="warning",
                type="planned_child_model_limited_claim",
                message="field is covered by a planned child model; broad claims must stay limited",
                source_id=role.source_id,
                field_name=field_name,
            )
        )
    if role.coverage_status == "excluded" and not role.reason:
        findings.append(
            ContractFinding(
                severity="error",
                type="excluded_without_reason",
                message="excluded fields require an explicit reason",
                source_id=role.source_id,
                field_name=field_name,
            )
        )
    if (
        role.coverage_status == "covered"
        and policy.require_mapping_for_covered_roles
        and not edges_by_source.get(role.source_id)
    ):
        findings.append(
            ContractFinding(
                severity="error",
                type="covered_role_missing_mapping_edge",
                message="covered fields must have at least one mapping edge",
                source_id=role.source_id,
                field_name=field_name,
            )
        )
    return findings


def _mapping_edge_findings(
    mapping_edges: ParameterMappingEdgesSpec,
    catalog_by_source: Mapping[str, Any],
    valid_targets: Mapping[str, set[str]] | None,
    policy: CoveragePolicySpec,
) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    active_keys: set[tuple[str, str, str, str]] = set()
    for edge in mapping_edges.edges:
        if edge.source_id not in catalog_by_source:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="mapping_edge_unknown_source",
                    message="mapping edge source_id is not present in parameter catalog",
                    source_id=edge.source_id,
                    target=edge.target,
                )
            )
        if edge.review_required and not policy.allow_review_required:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="mapping_edge_review_required",
                    message="mapping edge requires review before broad AI analysis claims",
                    source_id=edge.source_id,
                    target=edge.target,
                )
            )
        if policy.require_mapping_evidence and not edge.evidence:
            findings.append(
                ContractFinding(
                    severity="error" if not edge.review_required else "warning",
                    type="mapping_edge_missing_evidence",
                    message=(
                        "mapping edge must record evidence; uncertain mappings must remain "
                        "review_required instead of being treated as fully covered"
                    ),
                    source_id=edge.source_id,
                    target=edge.target,
                    details={"target_type": edge.target_type, "relation": edge.relation},
                )
            )
        if (
            policy.minimum_mapping_confidence is not None
            and edge.confidence is not None
            and edge.confidence < policy.minimum_mapping_confidence
        ):
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="mapping_edge_low_confidence",
                    message="mapping edge confidence is below coverage policy minimum",
                    source_id=edge.source_id,
                    target=edge.target,
                    details={
                        "confidence": edge.confidence,
                        "minimum": policy.minimum_mapping_confidence,
                    },
                )
            )
        if policy.fail_on_stale and _metadata_is_stale(edge.metadata):
            findings.append(
                ContractFinding(
                    severity="error",
                    type="stale_mapping_edge",
                    message="mapping edge metadata marks this mapping as stale",
                    source_id=edge.source_id,
                    target=edge.target,
                )
            )
        normalized_type = _normalize_target_type(edge.target_type)
        if valid_targets is not None and normalized_type in valid_targets:
            if edge.target not in valid_targets[normalized_type]:
                findings.append(
                    ContractFinding(
                        severity="error",
                        type="mapping_edge_unknown_target",
                        message="mapping edge target is not present in the bound PhysicsGuard model",
                        source_id=edge.source_id,
                        target=edge.target,
                        details={"target_type": edge.target_type},
                    )
                )
        key = (edge.source_id, edge.relation, normalized_type, edge.target)
        if policy.fail_on_duplicate_active_mappings and key in active_keys:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="duplicate_active_mapping_edge",
                    message="duplicate active mapping edge found",
                    source_id=edge.source_id,
                    target=edge.target,
                    details={"relation": edge.relation, "target_type": edge.target_type},
                )
            )
        active_keys.add(key)
    return findings


def _metadata_is_stale(metadata: Mapping[str, Any]) -> bool:
    status = str(metadata.get("status", "")).lower()
    return bool(metadata.get("stale") is True or metadata.get("is_stale") is True or status == "stale")


def _normalize_target_type(target_type: str) -> str:
    if target_type in {"physics_variable", "model_variable", "variable"}:
        return "variable"
    if target_type in {"model_parameter", "parameter"}:
        return "parameter"
    if target_type in {"hierarchy_block", "block"}:
        return "block"
    if target_type in {"residual", "post_check"}:
        return "residual"
    return target_type


def _status(findings: list[ContractFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "partial"
    return "pass"


def _next_actions(findings: list[ContractFinding]) -> list[str]:
    actions: list[str] = []
    for finding in findings:
        if finding.severity == "error":
            actions.append(f"fix {finding.type}")
        elif finding.severity == "warning":
            actions.append(f"review {finding.type}")
    result: list[str] = []
    for action in actions:
        if action not in result:
            result.append(action)
    return result


__all__ = [
    "ContractFinding",
    "ContractReview",
    "check_parameter_coverage",
]
