"""Explicit assumption handling for PhysicsGuard audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any, TYPE_CHECKING

import numpy as np

from physicsguard.core.registry import VariableRegistry
from physicsguard.schema.assumption_spec import AssumptionSpec
from physicsguard.schema.system_spec import BoundarySpec, SystemSpec

if TYPE_CHECKING:
    from physicsguard.core.residual import ResidualRecord


@dataclass(frozen=True)
class AssumptionCard:
    id: str
    target_type: str
    target: str
    value: float | int | str | bool
    unit: str | None
    reason: str
    source: str
    impact: str
    confidence_penalty: float
    review_required: bool
    status: str
    applied: bool
    application: str | None
    warnings: list[str] = field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssumptionSummary:
    active_count: int
    rejected_count: int
    proposed_count: int
    applied_count: int
    high_impact_count: int
    medium_impact_count: int
    low_impact_count: int
    total_confidence_penalty: float
    confidence_factor: float
    cards: list[AssumptionCard]
    warnings: list[str]


@dataclass(frozen=True)
class AssumptionBoundarySpec:
    assumption_id: str
    variable: str
    value: float
    unit: str | None
    reason: str


class AssumptionManager:
    """Apply and report explicit assumptions for a SystemSpec."""

    def __init__(self, system: SystemSpec) -> None:
        self.original_system = system
        self.assumptions = list(system.assumptions)
        self._cards: dict[str, AssumptionCard] = {
            assumption.id: self._initial_card(assumption)
            for assumption in self.assumptions
        }

    def active_assumptions(self) -> list[AssumptionSpec]:
        return [assumption for assumption in self.assumptions if assumption.status == "active"]

    def rejected_assumptions(self) -> list[AssumptionSpec]:
        return [assumption for assumption in self.assumptions if assumption.status == "rejected"]

    def proposed_assumptions(self) -> list[AssumptionSpec]:
        return [assumption for assumption in self.assumptions if assumption.status == "proposed"]

    def apply_parameter_assumptions(self, system: SystemSpec) -> SystemSpec:
        components_by_id = {component.id: component for component in system.components}
        updated_components = list(system.components)

        for assumption in self.assumptions:
            if assumption.target_type != "parameter":
                continue
            if assumption.status != "active":
                self._mark_inactive(assumption)
                continue
            component_id, parameter_name = assumption.target.split(".", 1)
            if component_id not in components_by_id:
                raise ValueError(
                    f"{assumption.id}: parameter assumption references unknown component '{component_id}'"
                )
            index = next(
                i for i, component in enumerate(updated_components) if component.id == component_id
            )
            component = updated_components[index]
            parameters = dict(component.parameters)
            warnings: list[str] = []
            if parameter_name in parameters:
                if not assumption.allow_override:
                    warnings.append(
                        f"{assumption.id}: explicit parameter '{assumption.target}' was not overridden"
                    )
                    self._set_card(
                        assumption,
                        applied=False,
                        application="not_applied_existing_parameter",
                        warnings=warnings,
                    )
                    continue
                warnings.append(
                    f"{assumption.id}: explicit parameter '{assumption.target}' was overridden by assumption"
                )
                parameters[parameter_name] = assumption.value
                self._set_card(
                    assumption,
                    applied=True,
                    application="parameter_override",
                    warnings=warnings,
                )
            else:
                parameters[parameter_name] = assumption.value
                self._set_card(assumption, applied=True, application="parameter_fill")
            updated_components[index] = component.model_copy(update={"parameters": parameters})

        self._mark_non_parameter_cards(system)
        return system.model_copy(update={"components": updated_components})

    def assumption_boundary_specs(self, system: SystemSpec | None = None) -> list[AssumptionBoundarySpec]:
        active_system = system or self.original_system
        boundaries = {boundary.variable: boundary for boundary in active_system.boundaries}
        specs: list[AssumptionBoundarySpec] = []
        for assumption in self.assumptions:
            if assumption.target_type != "variable":
                continue
            if assumption.status != "active":
                self._mark_inactive(assumption)
                continue
            warnings: list[str] = []
            if assumption.target in boundaries and not assumption.allow_override:
                warnings.append(
                    f"{assumption.id}: explicit boundary for '{assumption.target}' was preferred over assumption"
                )
                self._set_card(
                    assumption,
                    applied=False,
                    application="not_applied_existing_boundary",
                    warnings=warnings,
                )
                continue
            if assumption.target in boundaries and assumption.allow_override:
                warnings.append(
                    f"{assumption.id}: explicit boundary for '{assumption.target}' was overridden by assumption"
                )
            value = _numeric_assumption_value(assumption)
            specs.append(
                AssumptionBoundarySpec(
                    assumption_id=assumption.id,
                    variable=assumption.target,
                    value=value,
                    unit=assumption.unit,
                    reason=assumption.reason,
                )
            )
            self._set_card(
                assumption,
                applied=True,
                application="boundary_residual",
                warnings=warnings,
            )
        return specs

    def assumption_residual_records(
        self,
        x: np.ndarray,
        registry: VariableRegistry,
        system: SystemSpec,
    ) -> list["ResidualRecord"]:
        from physicsguard.core.residual import ResidualRecord

        records: list[ResidualRecord] = []
        for spec in self.assumption_boundary_specs(system):
            try:
                index = registry.get_index(spec.variable)
                variable = registry.get_record(spec.variable)
            except KeyError as exc:
                raise KeyError(
                    f"{spec.assumption_id}: variable assumption references unknown variable: {exc}"
                ) from exc
            records.append(
                ResidualRecord(
                    name=f"assumption:{spec.variable}",
                    value=float(x[index] - spec.value),
                    scale=variable.scale,
                    source="assumption",
                    role="assumption",
                    diagnostic_key="assumed_variable_value",
                    description=f"Assumption {spec.assumption_id}: {spec.reason}",
                )
            )
        return records

    def should_skip_explicit_boundary(self, variable: str, system: SystemSpec) -> bool:
        del system
        for assumption in self.assumptions:
            if (
                assumption.target_type == "variable"
                and assumption.status == "active"
                and assumption.allow_override
                and assumption.target == variable
            ):
                return True
        return False

    def assumption_cards(self) -> list[AssumptionCard]:
        return list(self._cards.values())

    def build_summary(self, applied_cards: list[AssumptionCard] | None = None) -> AssumptionSummary:
        cards = applied_cards if applied_cards is not None else self.assumption_cards()
        active = [card for card in cards if card.status == "active"]
        rejected = [card for card in cards if card.status == "rejected"]
        proposed = [card for card in cards if card.status == "proposed"]
        active_applied = [card for card in active if card.applied]
        total_penalty = sum(card.confidence_penalty for card in active_applied)
        warnings: list[str] = []
        for card in cards:
            warnings.extend(card.warnings)
        if active:
            warnings.append("assumptions were used")
        if any(card.impact == "high" for card in active):
            warnings.append("high-impact assumptions were used")
        if proposed:
            warnings.append("proposed assumptions were not applied")
        if any(card.application == "parameter_override" for card in cards):
            warnings.append("one or more explicit parameters were overridden by assumptions")
        confidence_factor = max(0.0, 1.0 - total_penalty)
        if confidence_factor < 0.7:
            warnings.append("diagnostic confidence reduced by assumptions")
        return AssumptionSummary(
            active_count=len(active),
            rejected_count=len(rejected),
            proposed_count=len(proposed),
            applied_count=len(active_applied),
            high_impact_count=sum(1 for card in active if card.impact == "high"),
            medium_impact_count=sum(1 for card in active if card.impact == "medium"),
            low_impact_count=sum(1 for card in active if card.impact == "low"),
            total_confidence_penalty=float(total_penalty),
            confidence_factor=float(confidence_factor),
            cards=cards,
            warnings=_dedupe(warnings),
        )

    def summary_dict(self) -> dict[str, Any]:
        return asdict(self.build_summary())

    def _mark_non_parameter_cards(self, system: SystemSpec) -> None:
        boundaries = {boundary.variable for boundary in system.boundaries}
        for assumption in self.assumptions:
            if assumption.target_type == "parameter":
                continue
            if assumption.status != "active":
                self._mark_inactive(assumption)
                continue
            if assumption.target_type == "context":
                self._set_card(assumption, applied=True, application="context_only")
                continue
            if assumption.target_type == "variable":
                if assumption.target in boundaries and not assumption.allow_override:
                    self._set_card(
                        assumption,
                        applied=False,
                        application="not_applied_existing_boundary",
                        warnings=[
                            f"{assumption.id}: explicit boundary for '{assumption.target}' was preferred over assumption"
                        ],
                    )
                elif assumption.target in boundaries and assumption.allow_override:
                    self._set_card(
                        assumption,
                        applied=True,
                        application="boundary_residual",
                        warnings=[
                            f"{assumption.id}: explicit boundary for '{assumption.target}' was overridden by assumption"
                        ],
                    )
                else:
                    self._set_card(assumption, applied=True, application="boundary_residual")

    def _mark_inactive(self, assumption: AssumptionSpec) -> None:
        if assumption.status == "rejected":
            self._set_card(assumption, applied=False, application="not_applied_rejected")
        elif assumption.status == "proposed":
            self._set_card(
                assumption,
                applied=False,
                application="not_applied_proposed",
                warnings=[f"{assumption.id}: proposed assumption was not applied"],
            )

    def _initial_card(self, assumption: AssumptionSpec) -> AssumptionCard:
        application: str | None = None
        warnings: list[str] = []
        if assumption.status == "rejected":
            application = "not_applied_rejected"
        elif assumption.status == "proposed":
            application = "not_applied_proposed"
            warnings.append(f"{assumption.id}: proposed assumption was not applied")
        return AssumptionCard(
            id=assumption.id,
            target_type=assumption.target_type,
            target=assumption.target,
            value=assumption.value,
            unit=assumption.unit,
            reason=assumption.reason,
            source=assumption.source,
            impact=assumption.impact,
            confidence_penalty=assumption.effective_confidence_penalty,
            review_required=assumption.review_required,
            status=assumption.status,
            applied=False,
            application=application,
            warnings=warnings,
            notes=assumption.notes,
            metadata=dict(assumption.metadata),
        )

    def _set_card(
        self,
        assumption: AssumptionSpec,
        *,
        applied: bool,
        application: str | None,
        warnings: list[str] | None = None,
    ) -> None:
        existing = self._cards[assumption.id]
        self._cards[assumption.id] = replace(
            existing,
            applied=applied,
            application=application,
            warnings=_dedupe(warnings or []),
        )


def _numeric_assumption_value(assumption: AssumptionSpec) -> float:
    if isinstance(assumption.value, bool):
        raise ValueError(f"{assumption.id}: variable assumption value must be numeric")
    try:
        value = float(assumption.value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{assumption.id}: variable assumption value must be numeric") from exc
    if not np.isfinite(value):
        raise ValueError(f"{assumption.id}: variable assumption value must be finite")
    return value


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


__all__ = [
    "AssumptionBoundarySpec",
    "AssumptionCard",
    "AssumptionManager",
    "AssumptionSummary",
]
