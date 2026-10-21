"""Workflow governance helpers for PhysicsGuard AI debugging."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml





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
    "WorkflowFinding",
    "WorkflowReview",
    "review_external_model_intake",
    "review_model_understanding_preflight",
]
