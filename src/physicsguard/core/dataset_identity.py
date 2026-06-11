"""Checks for logical dataset identity and symmetric relation indexes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from physicsguard.core.parameter_coverage import ContractFinding, ContractReview
from physicsguard.io.test_file_contract_loader import (
    load_data_file_manifest,
    load_logical_dataset_record,
    load_test_file_relation_index,
)


def check_logical_dataset_record(path: str | Path) -> ContractReview:
    record_path = Path(path)
    record = load_logical_dataset_record(record_path)
    findings: list[ContractFinding] = []
    for reference in record.representation_manifests:
        manifest_path = _resolve_path(record_path.parent, reference.manifest)
        try:
            manifest = load_data_file_manifest(manifest_path)
        except Exception as exc:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="logical_dataset_manifest_load_failed",
                    message=f"failed to load representation manifest: {exc}",
                    target=str(manifest_path),
                )
            )
            continue
        if reference.content_hash and manifest.source_file.content_hash != reference.content_hash:
            findings.append(
                ContractFinding(
                    severity="error",
                    type="logical_dataset_manifest_hash_mismatch",
                    message="manifest source content hash differs from logical dataset reference",
                    target=str(manifest_path),
                    details={
                        "declared": reference.content_hash,
                        "manifest": manifest.source_file.content_hash,
                    },
                )
            )
    status = _status(findings)
    return ContractReview(
        artifact_kind="logical_dataset_record",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "logical_dataset_id": record.logical_dataset_id,
            "representation_count": len(record.representation_manifests),
            "relation_group_count": len(record.relation_group_ids),
            "raw_data_policy": record.raw_data_policy.model_dump(mode="json"),
            "semantics": (
                "logical dataset records identify referenced data; they do not "
                "move raw data or prove physical model validity"
            ),
        },
        next_actions=_next_actions(findings),
    )


def check_test_file_relation_index(path: str | Path) -> ContractReview:
    index_path = Path(path)
    index = load_test_file_relation_index(index_path)
    findings: list[ContractFinding] = []
    known = set(index.logical_datasets)
    for dataset in index.logical_datasets:
        dataset_path = _resolve_path(index_path.parent, dataset)
        if not dataset_path.exists():
            findings.append(
                ContractFinding(
                    severity="error",
                    type="relation_index_dataset_missing",
                    message="referenced logical dataset file does not exist",
                    target=str(dataset_path),
                )
            )
    for relation in index.relations:
        unknown = sorted(member for member in relation.members if member not in known)
        if unknown and relation.relation_type in {
            "byte_identical",
            "canonical_equivalent",
            "same_test_run",
            "same_testbench",
            "overlapping_fields",
        }:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="relation_member_not_listed_as_dataset",
                    message="relation includes members not listed as logical dataset files",
                    target=relation.relation_id,
                    details={"members": unknown},
                )
            )
        if relation.relation_type in {"redundant_sensor", "fallback_sensor"} and not relation.target:
            findings.append(
                ContractFinding(
                    severity="warning",
                    type="sensor_relation_missing_target",
                    message="sensor relation should name the model or physical target it cross-checks",
                    target=relation.relation_id,
                )
            )
    status = _status(findings)
    return ContractReview(
        artifact_kind="test_file_relation_index",
        status=status,
        ok=status == "pass",
        findings=findings,
        summary={
            "project_id": index.project_id,
            "logical_dataset_count": len(index.logical_datasets),
            "relation_count": len(index.relations),
            "semantics": (
                "relation indexes describe symmetric relationships; they do not "
                "make one contract a parent of another"
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
        if finding.type == "logical_dataset_manifest_load_failed":
            actions.append("fix or regenerate the referenced representation manifest")
        elif finding.type == "logical_dataset_manifest_hash_mismatch":
            actions.append("refresh the logical dataset reference after confirming the file identity")
        elif finding.type == "relation_index_dataset_missing":
            actions.append("add the referenced logical dataset record or remove the stale relation")
        elif finding.type == "sensor_relation_missing_target":
            actions.append("name the model or physical target for the sensor cross-check relation")
    return sorted(set(actions))


__all__ = ["check_logical_dataset_record", "check_test_file_relation_index"]
