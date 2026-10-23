"""Fail-closed parameter coverage checks for test-file contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional

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


CONFIDENCE = {"high": .9, "medium": .6, "low": .3}


def confidence_value(value):
    if isinstance(value, str):
        return CONFIDENCE.get(value.lower(), -1.)
    return float(value) if isinstance(value, (float, int)) and not isinstance(value, bool) and 0 <= value <= 1 else -1.


def field_targets(field):
    return {"row": field.target} if field.target else field.targets


def check_field_mappings(contract, manifest, target_units):
    """Check the single field declaration against current headers and registry units."""
    from physicsguard.core.units import unit_conversion
    findings = []
    def add(code, name, message, target=None, severity="error"):
        findings.append(ContractFinding(severity, code, message, source_id=f"field:{name}", field_name=name, target=target))
    present = {f.name for f in manifest.fields}
    for name in sorted(present - set(contract.fields) - {contract.time_column}):
        add("field_unclassified", name, "data field has no declared role")
    for name in sorted(set(contract.fields) - present):
        add("contract_field_missing", name, "declared field is absent from this file")
    mapped = {}
    for name, field in contract.fields.items():
        if field.role == "ignored":
            if not field.reason or not field.reason.strip():
                add("ignored_without_reason", name, "ignored field requires a reason")
            continue
        if field.role not in {"measured", "command"}:
            add("field_unclassified", name, "field needs role measured, command or ignored")
            continue
        if field.planned_child_model:
            if not field.planned_child_model.get("reason"):
                add("planned_child_model_without_reason", name, "planned model gap requires a reason")
            else:
                add("planned_child_model", name, field.planned_child_model['reason'], severity="warning")
            continue
        if field.review_required:
            add("mapping_review_required", name, "mapping awaits review", severity="warning")
        if not field.evidence or not field.evidence.strip():
            add("mapping_missing_evidence", name, "mapping requires explicit evidence")
        if confidence_value(field.confidence) < contract.coverage.min_confidence:
            add("mapping_confidence_below_minimum", name, "mapping confidence is below the contract minimum")
        targets = field_targets(field)
        if not targets:
            add("mapping_missing_target", name, "measured/command field requires a target")
        for target in targets.values():
            if target in mapped:
                add("duplicate_active_mapping", name, f"target also mapped by {mapped[target]}", target)
            mapped[target] = name
            if target not in target_units:
                add("mapping_unknown_target", name, "target is not in the current model registry", target)
                continue
            if not field.unit:
                add("mapping_missing_unit", name, "mapped field requires a unit", target)
                continue
            try:
                unit_conversion(field.unit, target_units[target], field.conversion)
            except ValueError as exc:
                add(str(exc), name, f"cannot convert {field.unit} to {target_units[target]}", target)
    return findings


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



def _metadata_is_stale(metadata: Mapping[str, Any]) -> bool:
    status = str(metadata.get("status", "")).lower()
    return bool(metadata.get("stale") is True or metadata.get("is_stale") is True or status == "stale")
