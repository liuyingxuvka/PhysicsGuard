"""Signal mapping ledger and bug-family follow-up helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from physicsguard.core.diagnostics import ResidualDiagnostic
from physicsguard.core.registry import VariableRegistry
from physicsguard.schema.observation_spec import ObservedValueSpec, ObservedValuesSpec
from physicsguard.schema.system_spec import SystemSpec


LOW_CONFIDENCE_LABELS = {"low", "template", "unknown", "unreviewed", "review_required", "needs_review"}
REVIEW_STATUS_LABELS = {"review_required", "needs_review", "unreviewed", "template"}


@dataclass(frozen=True)
class SignalMappingRecord:
    physics_variable: str
    expected_unit: str = ""
    observed_unit: str = ""
    external_signal: str = ""
    source: str = ""
    mapping_confidence: str = ""
    mapping_status: str = ""
    review_required: bool = False
    conversion_factor: float | None = None
    conversion_offset: float | None = None
    conversion_note: str = ""
    mapped_at: str = ""
    stale_when: tuple[str, ...] = ()
    block_id: str = ""
    issue_codes: tuple[str, ...] = ()
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "physics_variable": self.physics_variable,
            "expected_unit": self.expected_unit,
            "observed_unit": self.observed_unit,
            "external_signal": self.external_signal,
            "source": self.source,
            "mapping_confidence": self.mapping_confidence,
            "mapping_status": self.mapping_status,
            "review_required": self.review_required,
            "conversion_factor": self.conversion_factor,
            "conversion_offset": self.conversion_offset,
            "conversion_note": self.conversion_note,
            "mapped_at": self.mapped_at,
            "stale_when": list(self.stale_when),
            "block_id": self.block_id,
            "issue_codes": list(self.issue_codes),
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True)
class BugFamilyFollowUp:
    followup_id: str
    family: str
    severity: str
    trigger: str
    affected_blocks: tuple[str, ...] = ()
    affected_variables: tuple[str, ...] = ()
    evidence_residuals: tuple[str, ...] = ()
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "followup_id": self.followup_id,
            "family": self.family,
            "severity": self.severity,
            "trigger": self.trigger,
            "affected_blocks": list(self.affected_blocks),
            "affected_variables": list(self.affected_variables),
            "evidence_residuals": list(self.evidence_residuals),
            "recommended_action": self.recommended_action,
        }


def build_signal_mapping_ledger(
    system: SystemSpec,
    observed: ObservedValuesSpec,
    registry: VariableRegistry,
    *,
    block_lookup: Any | None = None,
) -> tuple[SignalMappingRecord, ...]:
    """Create a reviewable map from PhysicsGuard variables to external signals.

    The ledger records mapping confidence and conversion evidence, but it does
    not transform observed values. Numeric observed values remain exactly what
    the evaluator received.
    """

    del system
    rows: list[SignalMappingRecord] = []
    for variable in registry.names():
        if variable not in observed.variables:
            continue
        expected_unit = str(registry.get_record(variable).unit or "")
        observed_value = observed.variables[variable]
        observed_unit = str(observed_value.unit or "")
        block_id = ""
        if block_lookup is not None:
            block = block_lookup.block_for_variable(variable)
            block_id = block or ""
        issue_codes = _mapping_issue_codes(expected_unit, observed_unit, observed_value)
        rows.append(
            SignalMappingRecord(
                physics_variable=variable,
                expected_unit=expected_unit,
                observed_unit=observed_unit,
                external_signal=observed_value.external_signal or observed_value.source or "",
                source=observed_value.source or "",
                mapping_confidence=_confidence_text(observed_value.mapping_confidence),
                mapping_status=observed_value.mapping_status or "",
                review_required=observed_value.review_required,
                conversion_factor=observed_value.conversion_factor,
                conversion_offset=observed_value.conversion_offset,
                conversion_note=observed_value.conversion_note or "",
                mapped_at=observed_value.mapped_at or "",
                stale_when=tuple(observed_value.stale_when),
                block_id=block_id,
                issue_codes=issue_codes,
                recommended_action=_mapping_recommendation(issue_codes, variable),
            )
        )
    return tuple(rows)


def mapping_warnings(records: Iterable[SignalMappingRecord]) -> tuple[str, ...]:
    warnings: list[str] = []
    for record in records:
        if record.issue_codes:
            warnings.append(
                f"{record.physics_variable}: signal mapping needs review ({', '.join(record.issue_codes)})"
            )
    return _dedupe(warnings)


def derive_bug_family_followups(
    *,
    top_blocks: Iterable[Any],
    top_residuals: Iterable[ResidualDiagnostic],
    mapping_records: Iterable[SignalMappingRecord],
) -> tuple[BugFamilyFollowUp, ...]:
    records = tuple(mapping_records)
    residuals = tuple(top_residuals)
    blocks = tuple(top_blocks)
    followups: list[BugFamilyFollowUp] = []
    mapping_issue_records = [record for record in records if record.issue_codes]
    if mapping_issue_records:
        followups.append(
            BugFamilyFollowUp(
                followup_id="signal_mapping_review",
                family="signal_mapping",
                severity="warning",
                trigger="one or more observed variables have low-confidence, stale, review-required, or unit-mismatch mapping evidence",
                affected_blocks=tuple(_dedupe(record.block_id for record in mapping_issue_records if record.block_id)),
                affected_variables=tuple(record.physics_variable for record in mapping_issue_records),
                evidence_residuals=tuple(residual.name for residual in residuals[:5]),
                recommended_action="Review the same signal family for sign convention, unit conversion, source variable selection, and stale mapping notes before refining physics.",
            )
        )
    if any(_mentions(residual, ("linear", "gain", "sign", "feedback")) for residual in residuals):
        followups.append(
            BugFamilyFollowUp(
                followup_id="linear_gain_sign_family",
                family="gain_sign_or_direction",
                severity="warning",
                trigger="top residuals suggest a linear relation, feedback, gain, or sign mismatch",
                affected_blocks=tuple(_dedupe(block.block_id for block in blocks[:3])),
                affected_variables=tuple(_variables_from_residuals(residuals)),
                evidence_residuals=tuple(residual.name for residual in residuals[:5]),
                recommended_action="Check peer gain/sign/direction mappings in the same controller or signal chain instead of stopping at the first failed residual.",
            )
        )
    if any("missing_conversion" in record.issue_codes for record in records):
        followups.append(
            BugFamilyFollowUp(
                followup_id="unit_conversion_family",
                family="unit_conversion",
                severity="warning",
                trigger="observed unit differs from the PhysicsGuard SI-unit expectation without an explicit conversion record",
                affected_blocks=tuple(_dedupe(record.block_id for record in records if "missing_conversion" in record.issue_codes and record.block_id)),
                affected_variables=tuple(record.physics_variable for record in records if "missing_conversion" in record.issue_codes),
                evidence_residuals=tuple(residual.name for residual in residuals[:5]),
                recommended_action="Review related variables that share the same physical dimension before trusting the residual localization.",
            )
        )
    if any(_mentions(residual, ("balance", "mass", "energy", "power", "heat", "flow")) for residual in residuals):
        followups.append(
            BugFamilyFollowUp(
                followup_id="conservation_balance_family",
                family="conservation_balance",
                severity="info",
                trigger="top residuals touch a balance-like physical relation",
                affected_blocks=tuple(_dedupe(block.block_id for block in blocks[:3])),
                affected_variables=tuple(_variables_from_residuals(residuals)),
                evidence_residuals=tuple(residual.name for residual in residuals[:5]),
                recommended_action="Inspect sibling inflow/outflow, loss, storage, and boundary-condition variables before adding deeper component physics.",
            )
        )
    return _dedupe_followups(followups)


def _mapping_issue_codes(expected_unit: str, observed_unit: str, observed_value: ObservedValueSpec) -> tuple[str, ...]:
    issues: list[str] = []
    if not observed_value.external_signal and not observed_value.source:
        issues.append("missing_external_signal")
    if _is_low_confidence(observed_value.mapping_confidence):
        issues.append("low_confidence")
    if observed_value.review_required or _label(observed_value.mapping_status) in REVIEW_STATUS_LABELS:
        issues.append("review_required")
    if expected_unit and observed_unit and expected_unit != observed_unit and observed_value.conversion_factor is None:
        issues.append("missing_conversion")
    if observed_value.stale_when:
        issues.append("stale_mapping")
    return _dedupe(issues)


def _mapping_recommendation(issue_codes: tuple[str, ...], variable: str) -> str:
    if not issue_codes:
        return "Mapping evidence is present; still verify it if this variable drives a top residual."
    if "missing_conversion" in issue_codes:
        return f"Add an explicit conversion record or remap {variable} to an SI-valued signal."
    if "review_required" in issue_codes or "low_confidence" in issue_codes:
        return f"Confirm {variable}'s source signal, sign convention, and unit before treating the block score as localized."
    if "stale_mapping" in issue_codes:
        return f"Refresh {variable}'s mapping evidence before using this audit as current."
    return f"Complete the mapping evidence for {variable}."


def _is_low_confidence(value: float | str | None) -> bool:
    if value is None:
        return False
    if isinstance(value, (float, int)):
        return float(value) < 0.75
    return _label(str(value)) in LOW_CONFIDENCE_LABELS


def _confidence_text(value: float | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, (float, int)):
        return f"{float(value):.3g}"
    return str(value)


def _label(value: str | None) -> str:
    return "_".join((value or "").strip().lower().replace("-", " ").split())


def _mentions(residual: ResidualDiagnostic, tokens: tuple[str, ...]) -> bool:
    haystack = " ".join(
        str(part or "").lower()
        for part in (residual.name, residual.source, residual.role, residual.diagnostic_key, residual.description)
    )
    return any(token in haystack for token in tokens)


def _variables_from_residuals(residuals: Iterable[ResidualDiagnostic]) -> list[str]:
    variables: list[str] = []
    for residual in residuals:
        for token in str(residual.name).replace("=", " ").replace(":", " ").replace(",", " ").split():
            token = token.strip()
            if "." in token and token not in variables:
                variables.append(token)
    return variables


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return tuple(unique)


def _dedupe_followups(values: Iterable[BugFamilyFollowUp]) -> tuple[BugFamilyFollowUp, ...]:
    seen: set[str] = set()
    unique: list[BugFamilyFollowUp] = []
    for value in values:
        if value.followup_id in seen:
            continue
        seen.add(value.followup_id)
        unique.append(value)
    return tuple(unique)


__all__ = [
    "BugFamilyFollowUp",
    "SignalMappingRecord",
    "build_signal_mapping_ledger",
    "derive_bug_family_followups",
    "mapping_warnings",
]
