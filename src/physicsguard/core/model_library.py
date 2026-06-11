"""Checks for PhysicsGuard reusable model library indexes."""

from __future__ import annotations

from pathlib import Path

from physicsguard.core.data_file_manifest import sha256_file
from physicsguard.core.parameter_coverage import ContractFinding, ContractReview
from physicsguard.core.project_evidence import check_evidence_gaps
from physicsguard.io.test_file_contract_loader import load_model_library_index, load_yaml_mapping


def check_model_library_index(path: str | Path) -> ContractReview:
    index_path = Path(path)
    index = load_model_library_index(index_path)
    findings: list[ContractFinding] = []
    for entry in index.entries:
        model_path = _resolve_path(index_path.parent, entry.model_file)
        if not model_path.exists():
            findings.append(
                ContractFinding(
                    severity="error",
                    type="model_library_model_file_missing",
                    message="model library entry references a missing model file",
                    target=str(model_path),
                )
            )
        elif entry.model_hash:
            actual = sha256_file(model_path)
            if actual != entry.model_hash:
                findings.append(
                    ContractFinding(
                        severity="error",
                        type="model_library_model_hash_mismatch",
                        message="model library entry model_hash does not match the current file",
                        target=str(model_path),
                        details={"declared": entry.model_hash, "actual": actual},
                    )
                )
        for report in entry.validation_reports:
            report_path = _resolve_path(index_path.parent, report)
            if not report_path.exists():
                findings.append(
                    ContractFinding(
                        severity="error",
                        type="model_library_validation_report_missing",
                        message="model library validation report reference is missing",
                        target=str(report_path),
                    )
                )
                continue
            try:
                load_yaml_mapping(report_path)
            except Exception as exc:
                findings.append(
                    ContractFinding(
                        severity="error",
                        type="model_library_validation_report_invalid",
                        message=f"validation report is not readable YAML: {exc}",
                        target=str(report_path),
                    )
                )
        if entry.reuse_status == "validated" and not entry.validation_reports:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="model_library_validated_without_report",
                    message="validated reuse status requires validation report evidence",
                    target=entry.model_id,
                )
            )
        if entry.evidence_registry and entry.evidence_bundle_id:
            gap_report = check_evidence_gaps(_resolve_path(index_path.parent, entry.evidence_registry), entry.evidence_bundle_id)
            for gap in gap_report.blocking_gaps:
                findings.append(
                    ContractFinding(
                        severity="error",
                        type="model_library_blocking_evidence_gap",
                        message="blocking evidence gap prevents validated model reuse",
                        target=entry.model_id,
                        details=gap,
                    )
                )
            for gap in gap_report.review_gaps:
                findings.append(
                    ContractFinding(
                        severity="warning",
                        type="model_library_review_evidence_gap",
                        message="review evidence gap remains visible for model reuse",
                        target=entry.model_id,
                        details=gap,
                    )
                )
        elif entry.reuse_status in {"validated", "partial"} and (entry.evidence_registry or entry.evidence_bundle_id):
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="model_library_evidence_bundle_incomplete",
                    message="model library evidence registry and evidence_bundle_id should be declared together",
                    target=entry.model_id,
                )
            )
        if entry.reuse_status == "validated" and not entry.evidence_bundle_id:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="model_library_validated_without_evidence_bundle",
                    message="validated reuse should reference a project evidence bundle",
                    target=entry.model_id,
                )
            )
    status = _status(findings)
    return ContractReview(
        artifact_kind="model_library_index",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "library_id": index.library_id,
            "entry_count": len(index.entries),
            "semantics": (
                "model library entries store reusable evidence references; they do "
                "not store raw data or prove validity outside recorded boundaries"
            ),
        },
        next_actions=_next_actions(findings),
    )


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _status(findings: list[ContractFinding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "partial"
    return "pass"


def _next_actions(findings: list[ContractFinding]) -> list[str]:
    actions: list[str] = []
    for finding in findings:
        if finding.type == "model_library_model_file_missing":
            actions.append("fix the model_file path or remove the stale model library entry")
        elif finding.type == "model_library_model_hash_mismatch":
            actions.append("refresh model_hash after reviewing model changes")
        elif finding.type.startswith("model_library_validation_report"):
            actions.append("provide current validation report evidence before reuse claims")
        elif finding.type.startswith("model_library_blocking_evidence_gap"):
            actions.append("resolve blocking project evidence gaps before validated reuse")
        elif finding.type == "model_library_validated_without_evidence_bundle":
            actions.append("add a project evidence bundle before broad reuse claims")
    return sorted(set(actions))


__all__ = ["check_model_library_index"]
