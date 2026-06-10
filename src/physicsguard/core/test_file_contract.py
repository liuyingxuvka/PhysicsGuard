"""Resolved test-file contract checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar

import physicsguard
from physicsguard.core.data_file_manifest import field_signature_hash, sha256_file, stable_json_hash
from physicsguard.core.parameter_coverage import (
    ContractFinding,
    ContractReview,
    check_parameter_coverage,
)
from physicsguard.core.residual import ResidualBuilder
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.test_file_contract_loader import (
    load_coverage_policy,
    load_data_file_manifest,
    load_extractor_profile,
    load_model_binding,
    load_parameter_catalog,
    load_parameter_mapping_edges,
    load_parameter_role_matrix,
    load_test_file_contract,
    load_test_file_project_index,
    load_testbench_profile,
)
from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.parameter_coverage import (
    CoveragePolicySpec,
    ParameterCatalogSpec,
    ParameterMappingEdgesSpec,
    ParameterRoleMatrixSpec,
)
from physicsguard.schema.test_file_contract import (
    ExtractorProfileSpec,
    ModelBindingSpec,
    TestBenchProfileSpec,
    TestFileContractSpec,
)


SpecT = TypeVar("SpecT")


@dataclass(frozen=True)
class ResolvedArtifact(Generic[SpecT]):
    value: SpecT
    path: Optional[Path] = None


@dataclass(frozen=True)
class ResolvedTestFileContract:
    contract: TestFileContractSpec
    contract_path: Path
    manifest: ResolvedArtifact[DataFileManifestSpec]
    testbench_profile: Optional[ResolvedArtifact[TestBenchProfileSpec]]
    extractor_profile: Optional[ResolvedArtifact[ExtractorProfileSpec]]
    model_binding: Optional[ResolvedArtifact[ModelBindingSpec]]
    parameter_catalog: Optional[ResolvedArtifact[ParameterCatalogSpec]]
    role_matrix: Optional[ResolvedArtifact[ParameterRoleMatrixSpec]]
    mapping_edges: Optional[ResolvedArtifact[ParameterMappingEdgesSpec]]
    coverage_policy: ResolvedArtifact[CoveragePolicySpec]


def resolve_test_file_contract(path: str | Path) -> ResolvedTestFileContract:
    contract_path = Path(path)
    contract = load_test_file_contract(contract_path)
    base_dir = contract_path.parent
    return ResolvedTestFileContract(
        contract=contract,
        contract_path=contract_path,
        manifest=_resolve_required(
            contract.manifest,
            base_dir,
            DataFileManifestSpec,
            load_data_file_manifest,
            "manifest",
        ),
        testbench_profile=_resolve_optional(
            contract.testbench_profile,
            base_dir,
            TestBenchProfileSpec,
            load_testbench_profile,
        ),
        extractor_profile=_resolve_optional(
            contract.extractor_profile,
            base_dir,
            ExtractorProfileSpec,
            load_extractor_profile,
        ),
        model_binding=_resolve_optional(
            contract.model_binding,
            base_dir,
            ModelBindingSpec,
            load_model_binding,
        ),
        parameter_catalog=_resolve_optional(
            contract.parameter_catalog,
            base_dir,
            ParameterCatalogSpec,
            load_parameter_catalog,
        ),
        role_matrix=_resolve_optional(
            contract.role_matrix,
            base_dir,
            ParameterRoleMatrixSpec,
            load_parameter_role_matrix,
        ),
        mapping_edges=_resolve_optional(
            contract.mapping_edges,
            base_dir,
            ParameterMappingEdgesSpec,
            load_parameter_mapping_edges,
        ),
        coverage_policy=_resolve_optional(
            contract.coverage_policy,
            base_dir,
            CoveragePolicySpec,
            load_coverage_policy,
        )
        or ResolvedArtifact(CoveragePolicySpec()),
    )


def inspect_test_file_contract(path: str | Path) -> dict[str, Any]:
    resolved = resolve_test_file_contract(path)
    profile_id = (
        resolved.testbench_profile.value.profile_id
        if resolved.testbench_profile is not None
        else None
    )
    binding_id = (
        resolved.model_binding.value.binding_id
        if resolved.model_binding is not None
        else None
    )
    return {
        "artifact_kind": "test_file_contract_inspection",
        "contract_id": resolved.contract.contract_id,
        "file_id": resolved.contract.file_id,
        "contract_path": str(resolved.contract_path),
        "manifest_path": str(resolved.manifest.path) if resolved.manifest.path else None,
        "source_file": resolved.manifest.value.source_file.model_dump(mode="json"),
        "field_count": len(resolved.manifest.value.fields),
        "row_count": resolved.manifest.value.shape.row_count,
        "time": resolved.manifest.value.time.model_dump(mode="json", exclude_none=True),
        "testbench_profile_id": profile_id,
        "model_binding_id": binding_id,
        "catalog_entry_count": (
            len(resolved.parameter_catalog.value.parameters)
            if resolved.parameter_catalog is not None
            else 0
        ),
        "role_count": len(resolved.role_matrix.value.roles) if resolved.role_matrix is not None else 0,
        "mapping_edge_count": (
            len(resolved.mapping_edges.value.edges) if resolved.mapping_edges is not None else 0
        ),
        "known_defect_count": len(resolved.contract.known_defects),
        "semantics": (
            "inspection reports file-contract evidence only; run contract-check "
            "before using the file for broad AI analysis claims"
        ),
    }


def check_test_file_contract(path: str | Path) -> ContractReview:
    resolved = resolve_test_file_contract(path)
    findings: list[ContractFinding] = []
    findings.extend(_manifest_findings(resolved))
    findings.extend(_testbench_profile_findings(resolved))
    valid_targets, binding_findings = _model_binding_targets(resolved)
    findings.extend(binding_findings)
    coverage = check_parameter_coverage(
        manifest=resolved.manifest.value,
        catalog=resolved.parameter_catalog.value if resolved.parameter_catalog is not None else None,
        role_matrix=resolved.role_matrix.value if resolved.role_matrix is not None else None,
        mapping_edges=resolved.mapping_edges.value if resolved.mapping_edges is not None else None,
        policy=resolved.coverage_policy.value,
        valid_targets=valid_targets,
    )
    findings.extend(coverage.findings)
    findings.extend(_expected_model_target_findings(resolved, valid_targets))
    findings.extend(_known_defect_findings(resolved))
    status = _status(findings)
    return ContractReview(
        artifact_kind="test_file_contract",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "contract_id": resolved.contract.contract_id,
            "file_id": resolved.contract.file_id,
            "manifest_field_count": len(resolved.manifest.value.fields),
            "row_count": resolved.manifest.value.shape.row_count,
            "catalog_entry_count": (
                len(resolved.parameter_catalog.value.parameters)
                if resolved.parameter_catalog is not None
                else 0
            ),
            "role_count": len(resolved.role_matrix.value.roles) if resolved.role_matrix else 0,
            "mapping_edge_count": (
                len(resolved.mapping_edges.value.edges) if resolved.mapping_edges else 0
            ),
            "error_count": sum(1 for finding in findings if finding.severity == "error"),
            "warning_count": sum(1 for finding in findings if finding.severity == "warning"),
            "analysis_claim_gate": _analysis_claim_gate(status),
            "coverage_status": coverage.status,
            "semantics": (
                "contract pass means the test file is identified, classified, bound, "
                "and mapped enough for scoped AI analysis; it does not prove physical "
                "correctness and does not mutate observed values"
            ),
        },
        next_actions=_next_actions(findings),
    )


def check_test_file_parameter_coverage(path: str | Path) -> ContractReview:
    resolved = resolve_test_file_contract(path)
    valid_targets, target_findings = _model_binding_targets(resolved)
    coverage = check_parameter_coverage(
        manifest=resolved.manifest.value,
        catalog=resolved.parameter_catalog.value if resolved.parameter_catalog is not None else None,
        role_matrix=resolved.role_matrix.value if resolved.role_matrix is not None else None,
        mapping_edges=resolved.mapping_edges.value if resolved.mapping_edges is not None else None,
        policy=resolved.coverage_policy.value,
        valid_targets=valid_targets,
    )
    findings = [*target_findings, *coverage.findings]
    status = _status(findings)
    return ContractReview(
        artifact_kind="parameter_coverage_contract",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            **coverage.summary,
            "contract_id": resolved.contract.contract_id,
            "file_id": resolved.contract.file_id,
            "analysis_claim_gate": _analysis_claim_gate(status),
        },
        next_actions=_next_actions(findings),
    )


def check_test_file_project_index(path: str | Path) -> ContractReview:
    index_path = Path(path)
    index = load_test_file_project_index(index_path)
    findings: list[ContractFinding] = []
    contract_summaries: list[dict[str, Any]] = []
    for reference in index.test_files:
        contract_path = _resolve_path(index_path.parent, reference.contract)
        try:
            review = check_test_file_contract(contract_path)
        except Exception as exc:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="project_contract_check_failed",
                    message=f"failed to check referenced contract: {exc}",
                    target=str(contract_path),
                )
            )
            continue
        contract_summaries.append(
            {
                "contract": str(contract_path),
                "file_id": review.summary.get("file_id"),
                "status": review.status,
                "error_count": review.summary.get("error_count"),
                "warning_count": review.summary.get("warning_count"),
            }
        )
        for finding in review.findings:
            if finding.severity == "error":
                findings.append(
                    ContractFinding(
                        severity="error",
                        type=f"contract:{finding.type}",
                        message=f"{contract_path}: {finding.message}",
                        source_id=finding.source_id,
                        field_name=finding.field_name,
                        target=finding.target,
                        details=finding.details,
                    )
                )
            elif finding.severity == "warning":
                findings.append(
                    ContractFinding(
                        severity="warning",
                        type=f"contract:{finding.type}",
                        message=f"{contract_path}: {finding.message}",
                        source_id=finding.source_id,
                        field_name=finding.field_name,
                        target=finding.target,
                        details=finding.details,
                    )
                )
    status = _status(findings)
    return ContractReview(
        artifact_kind="test_file_project_index",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "project_id": index.project_id,
            "contract_count": len(index.test_files),
            "checked_contracts": contract_summaries,
            "error_count": sum(1 for finding in findings if finding.severity == "error"),
            "warning_count": sum(1 for finding in findings if finding.severity == "warning"),
        },
        next_actions=_next_actions(findings),
    )


def _manifest_findings(resolved: ResolvedTestFileContract) -> list[ContractFinding]:
    manifest = resolved.manifest.value
    findings: list[ContractFinding] = []
    expected_signature = field_signature_hash(manifest)
    if manifest.field_signature_hash != expected_signature:
        findings.append(
            ContractFinding(
                severity="error" if manifest.field_signature_hash else "warning",
                type="manifest_field_signature_mismatch",
                message="manifest field signature hash is missing or does not match fields",
                details={
                    "declared": manifest.field_signature_hash,
                    "expected": expected_signature,
                },
            )
        )
    if resolved.contract.manifest_hash:
        actual = _artifact_hash(resolved.manifest)
        if actual != resolved.contract.manifest_hash:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="manifest_hash_mismatch",
                    message="contract manifest_hash does not match resolved manifest artifact",
                    details={"declared": resolved.contract.manifest_hash, "actual": actual},
                )
            )
    source_path = _resolve_source_path(resolved)
    if source_path.exists():
        actual = sha256_file(source_path)
        if manifest.source_file.content_hash and actual != manifest.source_file.content_hash:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="source_file_hash_mismatch",
                    message="manifest source_file.content_hash does not match current source file",
                    target=str(source_path),
                    details={"declared": manifest.source_file.content_hash, "actual": actual},
                )
            )
    else:
        findings.append(
            ContractFinding(
                severity="warning",
                type="source_file_unavailable_for_freshness_check",
                message="source data file is not available, so content hash freshness cannot be rechecked",
                target=str(source_path),
            )
        )
    extractor = manifest.extractor
    if not extractor.script:
        findings.append(
            ContractFinding(
                severity="error",
                type="manifest_missing_extractor_identity",
                message="manifest must record extractor script identity",
            )
        )
    profile = resolved.extractor_profile.value if resolved.extractor_profile is not None else None
    if profile is not None:
        if profile.script_hash and extractor.script_hash and profile.script_hash != extractor.script_hash:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="extractor_script_hash_mismatch",
                    message="extractor profile hash differs from manifest extractor hash",
                    details={"profile": profile.script_hash, "manifest": extractor.script_hash},
                )
            )
        if profile.config_hash and extractor.config_hash and profile.config_hash != extractor.config_hash:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="extractor_config_hash_mismatch",
                    message="extractor profile config hash differs from manifest extractor config hash",
                )
            )
        if _metadata_is_stale(profile.metadata):
            findings.append(
                ContractFinding(
                    severity="error",
                    type="stale_extractor_profile",
                    message="extractor profile metadata marks this extractor as stale",
                )
            )
    return findings


def _testbench_profile_findings(resolved: ResolvedTestFileContract) -> list[ContractFinding]:
    if resolved.testbench_profile is None:
        return [
            ContractFinding(
                severity="warning",
                type="missing_testbench_profile",
                message="contract has no testbench profile; file can be checked but bench/version context is weaker",
            )
        ]
    profile = resolved.testbench_profile.value
    fields = {field.name for field in resolved.manifest.value.fields}
    findings: list[ContractFinding] = []
    for expected in sorted(set(profile.expected_fields) - fields):
        findings.append(
            ContractFinding(
                severity="error",
                type="testbench_expected_field_missing",
                message="testbench profile expected field is missing from manifest",
                field_name=expected,
            )
        )
    if _metadata_is_stale(profile.metadata):
        findings.append(
            ContractFinding(
                severity="error",
                type="stale_testbench_profile",
                message="testbench profile metadata marks this profile as stale",
            )
        )
    return findings


def _model_binding_targets(
    resolved: ResolvedTestFileContract,
) -> tuple[dict[str, set[str]] | None, list[ContractFinding]]:
    if resolved.model_binding is None:
        return None, [
            ContractFinding(
                severity="error",
                type="missing_model_binding",
                message="test-file contract must bind to a PhysicsGuard model/hierarchy artifact",
            )
        ]
    binding = resolved.model_binding.value
    findings: list[ContractFinding] = []
    if _metadata_is_stale(binding.metadata):
        findings.append(
            ContractFinding(
                severity="error",
                type="stale_model_binding",
                message="model binding metadata marks this binding as stale",
            )
        )
    if binding.physicsguard_version and binding.physicsguard_version != physicsguard.__version__:
        findings.append(
            ContractFinding(
                severity="warning",
                type="physicsguard_version_mismatch",
                message="model binding was recorded against a different PhysicsGuard version",
                details={
                    "binding_version": binding.physicsguard_version,
                    "runtime_version": physicsguard.__version__,
                },
            )
        )
    if binding.compatible_testbench_profiles and resolved.testbench_profile is not None:
        profile_id = resolved.testbench_profile.value.profile_id
        if profile_id not in binding.compatible_testbench_profiles:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="incompatible_testbench_profile",
                    message="model binding does not list this testbench profile as compatible",
                    details={"profile_id": profile_id},
                )
            )
    signature = field_signature_hash(resolved.manifest.value)
    if binding.compatible_manifest_signatures and signature not in binding.compatible_manifest_signatures:
        findings.append(
            ContractFinding(
                severity="error",
                type="incompatible_manifest_signature",
                message="model binding does not list this manifest field signature as compatible",
                details={"field_signature_hash": signature},
            )
        )

    targets = {
        "variable": set(binding.expected_variables),
        "parameter": set(binding.expected_parameters),
        "block": set(),
        "residual": set(),
    }
    if binding.hierarchy_file is None:
        return targets, findings
    hierarchy_path = _resolve_binding_path(resolved, binding.hierarchy_file)
    if not hierarchy_path.exists():
        findings.append(
            ContractFinding(
                severity="error",
                type="model_binding_hierarchy_file_missing",
                message="model binding hierarchy_file does not exist",
                target=str(hierarchy_path),
            )
        )
        return targets, findings
    if binding.hierarchy_hash:
        actual = sha256_file(hierarchy_path)
        if actual != binding.hierarchy_hash:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="model_binding_hierarchy_hash_mismatch",
                    message="model binding hierarchy_hash does not match current hierarchy file",
                    target=str(hierarchy_path),
                    details={"declared": binding.hierarchy_hash, "actual": actual},
                )
            )
    try:
        spec = load_hierarchical_audit_spec(hierarchy_path)
        builder = ResidualBuilder(spec.system)
        registry = builder.build_registry()
        targets["variable"].update(registry.names())
        targets["parameter"].update(
            f"{component.id}.{parameter}"
            for component in spec.system.components
            for parameter in component.parameters
        )
        targets["block"].update(block.id for block in spec.hierarchy.blocks)
        try:
            targets["residual"].update(
                record.name for record in builder.diagnostic_residual_records(registry.initial_vector())
            )
        except Exception as exc:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="model_binding_residual_target_probe_failed",
                    message=f"could not evaluate residual names from hierarchy initial vector: {exc}",
                    target=str(hierarchy_path),
                )
            )
    except Exception as exc:
        findings.append(
            ContractFinding(
                severity="error",
                type="model_binding_hierarchy_load_failed",
                message=f"could not load bound hierarchy model: {exc}",
                target=str(hierarchy_path),
            )
        )
    return targets, findings


def _expected_model_target_findings(
    resolved: ResolvedTestFileContract,
    valid_targets: dict[str, set[str]] | None,
) -> list[ContractFinding]:
    if resolved.model_binding is None:
        return []
    binding = resolved.model_binding.value
    edges = resolved.mapping_edges.value.edges if resolved.mapping_edges is not None else []
    mapped_variables = {edge.target for edge in edges if edge.target_type in {"physics_variable", "model_variable", "variable"}}
    mapped_parameters = {edge.target for edge in edges if edge.target_type in {"model_parameter", "parameter"}}
    findings: list[ContractFinding] = []
    for variable in sorted(set(binding.expected_variables) - mapped_variables):
        findings.append(
            ContractFinding(
                severity="error",
                type="expected_model_variable_unmapped",
                message="model binding expected variable has no mapping edge",
                target=variable,
            )
        )
    for parameter in sorted(set(binding.expected_parameters) - mapped_parameters):
        findings.append(
            ContractFinding(
                severity="warning",
                type="expected_model_parameter_unmapped",
                message="model binding expected parameter has no mapping edge",
                target=parameter,
            )
        )
    if valid_targets is None:
        return findings
    for variable in binding.expected_variables:
        if variable not in valid_targets.get("variable", set()):
            findings.append(
                ContractFinding(
                    severity="error",
                    type="expected_model_variable_unknown",
                    message="model binding expected variable is not in bound hierarchy model",
                    target=variable,
                )
            )
    for parameter in binding.expected_parameters:
        if parameter not in valid_targets.get("parameter", set()):
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="expected_model_parameter_unknown",
                    message="model binding expected parameter is not in bound hierarchy model",
                    target=parameter,
                )
            )
    return findings


def _known_defect_findings(resolved: ResolvedTestFileContract) -> list[ContractFinding]:
    return [
        ContractFinding(
            severity="warning",
            type="known_file_defect_limits_claim",
            message=defect.safe_claim or defect.description,
            target=defect.id,
            details={"impact": defect.impact},
        )
        for defect in resolved.contract.known_defects
    ]


def _resolve_required(
    value: Any,
    base_dir: Path,
    expected_type: type[SpecT],
    loader: Callable[[Path], SpecT],
    field_name: str,
) -> ResolvedArtifact[SpecT]:
    resolved = _resolve_optional(value, base_dir, expected_type, loader)
    if resolved is None:
        raise ValueError(f"test-file contract is missing required {field_name}")
    return resolved


def _resolve_optional(
    value: Any,
    base_dir: Path,
    expected_type: type[SpecT],
    loader: Callable[[Path], SpecT],
) -> Optional[ResolvedArtifact[SpecT]]:
    if value is None:
        return None
    if isinstance(value, expected_type):
        return ResolvedArtifact(value=value)
    if isinstance(value, str):
        path = _resolve_path(base_dir, value)
        return ResolvedArtifact(value=loader(path), path=path)
    raise TypeError(f"expected {expected_type.__name__} or path string, got {type(value).__name__}")


def _resolve_path(base_dir: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (base_dir / candidate)


def _resolve_binding_path(resolved: ResolvedTestFileContract, path: str) -> Path:
    base_dir = resolved.model_binding.path.parent if resolved.model_binding and resolved.model_binding.path else resolved.contract_path.parent
    return _resolve_path(base_dir, path)


def _resolve_source_path(resolved: ResolvedTestFileContract) -> Path:
    base_dir = resolved.manifest.path.parent if resolved.manifest.path else resolved.contract_path.parent
    return _resolve_path(base_dir, resolved.manifest.value.source_file.path)


def _artifact_hash(artifact: ResolvedArtifact[Any]) -> str:
    if artifact.path is not None:
        return sha256_file(artifact.path)
    if hasattr(artifact.value, "model_dump"):
        return stable_json_hash(artifact.value.model_dump(mode="json", exclude_none=True))
    return stable_json_hash(asdict(artifact.value))


def _metadata_is_stale(metadata: dict[str, Any]) -> bool:
    status = str(metadata.get("status", "")).lower()
    return bool(metadata.get("stale") is True or metadata.get("is_stale") is True or status == "stale")


def _status(findings: list[ContractFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "partial"
    return "pass"


def _analysis_claim_gate(status: str) -> str:
    if status == "pass":
        return "open_for_scoped_analysis"
    if status == "partial":
        return "limited_claims_only"
    return "blocked_until_contract_errors_are_fixed"


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
    "ResolvedArtifact",
    "ResolvedTestFileContract",
    "check_test_file_contract",
    "check_test_file_parameter_coverage",
    "check_test_file_project_index",
    "inspect_test_file_contract",
    "resolve_test_file_contract",
]
