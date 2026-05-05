"""Hierarchical and progressive PhysicsGuard audit support."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from typing import Any, Iterable, Optional

import numpy as np

from physicsguard.core.assumptions import AssumptionSummary
from physicsguard.core.diagnostics import DiagnosticReporter, ResidualDiagnostic
from physicsguard.core.evaluator import VariableDeviationDiagnostic
from physicsguard.core.registry import VariableRegistry
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.core.solver import BoundedSolver
from physicsguard.schema.hierarchy_spec import (
    AuditBlockSpec,
    BlockScoringSpec,
    ConfidenceScoringSpec,
    HierarchicalAuditSpec,
    HierarchySpec,
    RefinementRuleSpec,
)
from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.system_spec import SystemSpec


@dataclass(frozen=True)
class ResidualBlockAssignment:
    residual_name: str
    diagnostic_key: Optional[str]
    residual_role: str
    residual_source: str
    block_id: Optional[str]
    reason: Optional[str] = None


@dataclass(frozen=True)
class RecommendedRefinement:
    rule_id: str
    block_id: str
    next_template_ids: list[str]
    next_required_variables: list[str]
    next_required_parameters: list[str]
    rationale: Optional[str]
    priority: int
    trigger_score: float
    trigger_diagnostic_keys: list[str]


@dataclass(frozen=True)
class BlockDiagnostic:
    block_id: str
    name: Optional[str]
    level: int
    parent_id: Optional[str]
    tags: list[str]
    score: float
    confidence: float
    audit_pass: bool
    max_abs_normalized_residual: float
    residual_norm: float
    top_residuals: list[ResidualDiagnostic]
    post_check_residuals: list[ResidualDiagnostic]
    missing_required_variables: list[str]
    missing_required_parameters: list[str]
    unassigned_residual_count: int = 0
    recommended_refinements: list[RecommendedRefinement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HierarchicalAuditReport:
    audit_name: str
    system_name: str
    optimization_success: bool
    audit_pass: bool
    residual_norm: float
    max_abs_normalized_residual: float
    top_residuals: list[ResidualDiagnostic]
    top_blocks: list[BlockDiagnostic]
    block_assignments: list[ResidualBlockAssignment]
    unassigned_residuals: list[ResidualDiagnostic]
    missing_required_variables: list[str]
    missing_required_parameters: list[str]
    recommended_refinements: list[RecommendedRefinement]
    assumptions: AssumptionSummary
    warnings: list[str]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class HierarchicalComparisonReport:
    audit_name: str
    system_name: str
    observation_name: Optional[str]
    reference_optimization_success: bool
    reference_audit_pass: bool
    observed_audit_pass: bool
    reference_residual_norm: float
    observed_residual_norm: float
    reference_variables: dict[str, float]
    observed_variables: dict[str, float]
    top_variable_deviations: list[VariableDeviationDiagnostic]
    observed_hierarchy: HierarchicalAuditReport
    warnings: list[str]
    metadata: dict[str, Any]


class BlockIndex:
    """Index logical audit blocks and map residuals to blocks."""

    def __init__(self, hierarchy: HierarchySpec, system: SystemSpec) -> None:
        self.hierarchy = hierarchy
        self.system = system
        self._blocks = {block.id: block for block in hierarchy.blocks}
        self._children: dict[str, list[AuditBlockSpec]] = {block.id: [] for block in hierarchy.blocks}
        self._component_to_block: dict[str, str] = {}
        self._system_components = {component.id for component in system.components}
        self._interblock_id = "interblock" if "interblock" in self._blocks else None
        self._validate_components()
        for block in hierarchy.blocks:
            if block.parent_id is not None:
                self._children[block.parent_id].append(block)
            for component_id in block.components:
                self._component_to_block[component_id] = block.id

    def block_ids(self) -> list[str]:
        return list(self._blocks)

    def root_blocks(self) -> list[AuditBlockSpec]:
        return [block for block in self.hierarchy.blocks if block.parent_id is None]

    def children(self, block_id: str) -> list[AuditBlockSpec]:
        self._require_block(block_id)
        return list(self._children[block_id])

    def parent(self, block_id: str) -> AuditBlockSpec | None:
        block = self._require_block(block_id)
        return self._blocks.get(block.parent_id) if block.parent_id else None

    def ancestors(self, block_id: str) -> list[AuditBlockSpec]:
        block = self._require_block(block_id)
        result: list[AuditBlockSpec] = []
        while block.parent_id is not None:
            block = self._blocks[block.parent_id]
            result.append(block)
        return result

    def descendants(self, block_id: str) -> list[AuditBlockSpec]:
        self._require_block(block_id)
        result: list[AuditBlockSpec] = []
        stack = list(self._children[block_id])
        while stack:
            child = stack.pop(0)
            result.append(child)
            stack.extend(self._children[child.id])
        return result

    def component_block(self, component_id: str) -> str | None:
        return self._component_to_block.get(component_id)

    def unassigned_components(self) -> list[str]:
        assigned = set(self._component_to_block)
        return sorted(self._system_components - assigned)

    def block_for_variable(self, variable_name: str) -> str | None:
        if "." not in variable_name:
            return None
        component_id = variable_name.split(".", 1)[0]
        return self.component_block(component_id)

    def block_for_residual(self, residual: ResidualRecord) -> str | None:
        if residual.source in self._component_to_block:
            return self._component_to_block[residual.source]
        if residual.source == "connection":
            endpoints = _parse_connection_residual_name(residual.name)
            if endpoints is not None:
                return self._block_for_connection(endpoints[0], endpoints[1])
        if residual.source == "boundary":
            variable = _parse_boundary_residual_name(residual.name)
            if variable is not None:
                return self.block_for_variable(variable)
        for variable in _qualified_variable_candidates(residual.name, residual.source):
            block_id = self.block_for_variable(variable)
            if block_id is not None:
                return block_id
        return None

    def assignment_for_residual(self, residual: ResidualRecord) -> ResidualBlockAssignment:
        block_id = self.block_for_residual(residual)
        reason = "assigned" if block_id is not None else "unassigned"
        if residual.source == "connection" and block_id == self._interblock_id:
            reason = "interblock"
        return ResidualBlockAssignment(
            residual_name=residual.name,
            diagnostic_key=residual.diagnostic_key,
            residual_role=residual.role,
            residual_source=residual.source,
            block_id=block_id,
            reason=reason,
        )

    def _block_for_connection(self, from_variable: str, to_variable: str) -> str | None:
        from_block = self.block_for_variable(from_variable)
        to_block = self.block_for_variable(to_variable)
        if from_block is None or to_block is None:
            return self._interblock_id
        if from_block == to_block:
            return from_block
        common = self._nearest_common_ancestor(from_block, to_block)
        if common is not None:
            return common
        return self._interblock_id

    def _nearest_common_ancestor(self, left_id: str, right_id: str) -> str | None:
        left_path = [self._blocks[left_id], *self.ancestors(left_id)]
        right_path = [self._blocks[right_id], *self.ancestors(right_id)]
        right_by_id = {block.id: block for block in right_path}
        common = [block for block in left_path if block.id in right_by_id]
        if not common:
            return None
        return max(common, key=lambda block: block.level).id

    def _validate_components(self) -> None:
        missing: list[str] = []
        for block in self.hierarchy.blocks:
            for component_id in block.components:
                if component_id not in self._system_components:
                    missing.append(component_id)
        if missing:
            raise ValueError(f"hierarchy references unknown component ids: {', '.join(sorted(set(missing)))}")

    def _require_block(self, block_id: str) -> AuditBlockSpec:
        try:
            return self._blocks[block_id]
        except KeyError as exc:
            raise KeyError(f"unknown block id: {block_id}") from exc


class BlockScorer:
    """Compute block suspicion scores from residual diagnostics."""

    def score_block(
        self,
        block: AuditBlockSpec,
        residuals: list[ResidualDiagnostic],
        scoring_spec: BlockScoringSpec,
    ) -> float:
        del block
        values = self._weighted_abs_values(residuals, scoring_spec)
        if not values:
            return 0.0
        if scoring_spec.method == "max":
            return float(max(values))
        if scoring_spec.method == "rms":
            return float(math.sqrt(sum(value * value for value in values) / len(values)))
        if scoring_spec.method == "top_k_mean":
            top = sorted(values, reverse=True)[: scoring_spec.top_k]
            return float(sum(top) / len(top))
        if scoring_spec.method == "weighted_sum":
            return float(sum(values))
        raise ValueError(f"unsupported scoring method: {scoring_spec.method}")

    def residual_norm(self, residuals: list[ResidualDiagnostic]) -> float:
        return float(math.sqrt(sum(item.normalized_value**2 for item in residuals)))

    def max_abs_normalized_residual(self, residuals: list[ResidualDiagnostic]) -> float:
        return float(max((item.abs_normalized_value for item in residuals), default=0.0))

    def select_top_residuals(
        self,
        residuals: list[ResidualDiagnostic],
        top_n: int,
    ) -> list[ResidualDiagnostic]:
        return sorted(residuals, key=lambda item: item.abs_normalized_value, reverse=True)[:top_n]

    def filter_scored(
        self,
        residuals: list[ResidualDiagnostic],
        scoring_spec: BlockScoringSpec,
    ) -> list[ResidualDiagnostic]:
        include = set(scoring_spec.include_roles)
        exclude = set(scoring_spec.exclude_roles)
        return [item for item in residuals if item.role in include and item.role not in exclude]

    def _weighted_abs_values(
        self,
        residuals: list[ResidualDiagnostic],
        scoring_spec: BlockScoringSpec,
    ) -> list[float]:
        values: list[float] = []
        for item in self.filter_scored(residuals, scoring_spec):
            weight = scoring_spec.diagnostic_key_weights.get(item.diagnostic_key or "", 1.0)
            values.append(float(weight * item.abs_normalized_value))
        return values


class ConfidenceScorer:
    """Compute heuristic confidence for a block diagnostic."""

    def score(
        self,
        block: AuditBlockSpec,
        missing_required_variables: list[str],
        missing_required_parameters: list[str],
        residuals: list[ResidualDiagnostic],
        confidence_spec: ConfidenceScoringSpec,
    ) -> float:
        confidence = confidence_spec.base_confidence
        confidence -= len(missing_required_variables) * confidence_spec.missing_required_variable_penalty
        confidence -= len(missing_required_parameters) * confidence_spec.missing_required_parameter_penalty
        if not residuals:
            confidence -= confidence_spec.unassigned_residual_penalty
        confidence -= max(block.level, 0) * confidence_spec.coarse_level_penalty_per_level_above_zero
        return float(min(max(confidence, confidence_spec.min_confidence), confidence_spec.max_confidence))


class RefinementPlanner:
    """Apply refinement rules to suspicious block diagnostics."""

    def recommended_refinements(
        self,
        block_diagnostic: BlockDiagnostic,
        hierarchy_spec: HierarchySpec,
    ) -> list[RecommendedRefinement]:
        matches: list[RecommendedRefinement] = []
        for rule in hierarchy_spec.refinement_rules:
            if not self._rule_applies(rule, block_diagnostic):
                continue
            matches.append(
                RecommendedRefinement(
                    rule_id=rule.id,
                    block_id=block_diagnostic.block_id,
                    next_template_ids=list(rule.next_template_ids),
                    next_required_variables=list(rule.next_required_variables),
                    next_required_parameters=list(rule.next_required_parameters),
                    rationale=rule.rationale,
                    priority=rule.priority,
                    trigger_score=block_diagnostic.score,
                    trigger_diagnostic_keys=_trigger_keys(rule, block_diagnostic),
                )
            )
        return sorted(matches, key=lambda item: (-item.priority, -item.trigger_score, item.rule_id))

    def overall_plan(self, top_blocks: list[BlockDiagnostic]) -> list[RecommendedRefinement]:
        recommendations = [
            recommendation
            for block in top_blocks
            for recommendation in block.recommended_refinements
        ]
        return sorted(recommendations, key=lambda item: (-item.priority, -item.trigger_score, item.rule_id))

    def _rule_applies(self, rule: RefinementRuleSpec, block: BlockDiagnostic) -> bool:
        if rule.block_id is not None and rule.block_id != block.block_id:
            return False
        if block.score < rule.score_threshold:
            return False
        if rule.confidence_min is not None and block.confidence < rule.confidence_min:
            return False
        residuals = [*block.top_residuals, *block.post_check_residuals]
        if rule.trigger_diagnostic_keys:
            keys = {item.diagnostic_key for item in residuals}
            if not any(key in keys for key in rule.trigger_diagnostic_keys):
                return False
        if rule.trigger_roles:
            roles = {item.role for item in residuals}
            if not any(role in roles for role in rule.trigger_roles):
                return False
        return True


def _trigger_keys(rule: RefinementRuleSpec, block: BlockDiagnostic) -> list[str]:
    residuals = [*block.top_residuals, *block.post_check_residuals]
    keys = [item.diagnostic_key for item in residuals if item.diagnostic_key is not None]
    if rule.trigger_diagnostic_keys:
        allowed = set(rule.trigger_diagnostic_keys)
        keys = [key for key in keys if key in allowed]
    unique: list[str] = []
    for key in keys:
        if key not in unique:
            unique.append(key)
    return unique


class HierarchicalAuditRunner:
    """Run hierarchical audit diagnostics on solved or observed audit values."""

    def __init__(self, spec: HierarchicalAuditSpec) -> None:
        self.spec = spec

    def run(self, top_n_residuals: int = 20, top_n_blocks: int = 10) -> HierarchicalAuditReport:
        builder = ResidualBuilder(self.spec.system)
        solver_result = BoundedSolver(builder, self.spec.system.solver).solve()
        ordinary_report = DiagnosticReporter().generate(
            self.spec.system,
            builder,
            solver_result,
            top_n=top_n_residuals,
        )
        all_records = sorted(
            builder.diagnostic_residual_records(solver_result.x),
            key=lambda record: record.abs_normalized_value,
            reverse=True,
        )
        return self._build_report(
            builder=builder,
            all_records=all_records,
            optimization_success=ordinary_report.optimization_success,
            audit_pass=ordinary_report.audit_pass,
            residual_norm=ordinary_report.residual_norm,
            max_abs_normalized_residual=ordinary_report.max_abs_normalized_residual,
            top_residuals=ordinary_report.top_residuals,
            assumptions=ordinary_report.assumptions,
            warnings=list(ordinary_report.warnings),
            metadata={
                **ordinary_report.metadata,
                "mode": "hierarchy_solve",
                "solver_attempted": True,
                "assumption_confidence_integration": "report_level_only",
                "future_work": [
                    "time-series hierarchical evaluation",
                    "automatic refinement execution",
                ],
            },
            top_n_residuals=top_n_residuals,
            top_n_blocks=top_n_blocks,
        )

    def evaluate_observed(
        self,
        observed: ObservedValuesSpec,
        top_n_residuals: int = 20,
        top_n_blocks: int = 10,
    ) -> HierarchicalAuditReport:
        """Evaluate external observed values directly and roll residuals up by block.

        No reference solve is attempted. The observed values are substituted exactly
        as supplied, so this path is suitable for AI-guided debugging of external
        simulations where PhysicsGuard should identify suspicious blocks without
        fitting the values away.
        """

        builder = ResidualBuilder(self.spec.system)
        registry = builder.build_registry()
        values, missing, unknown = _observed_values_for_registry(observed, registry)
        if missing:
            raise ValueError(
                "observed values missing required registered variables: "
                + ", ".join(missing)
            )
        x = registry.dict_to_vector(values)
        diagnostic_records = sorted(
            builder.diagnostic_residual_records(x),
            key=lambda record: record.abs_normalized_value,
            reverse=True,
        )
        solver_records = builder.solver_residual_records(x)
        residual_norm, max_abs = _active_residual_metrics(solver_records)
        audit_pass = max_abs <= self.spec.system.solver.audit_threshold
        unit_warnings = _unit_warnings(observed, registry)
        warnings: list[str] = []
        if unknown:
            warnings.append("unknown observed variables ignored: " + ", ".join(unknown))
        warnings.extend(unit_warnings)
        if not audit_pass:
            warnings.append("observed audit did not pass")
        if max_abs > self.spec.system.solver.audit_threshold:
            warnings.append("max observed normalized residual exceeds audit threshold")
        if max_abs > 10:
            warnings.append("max observed normalized residual exceeds 10")
        assumption_summary = builder.assumption_summary()
        warnings.extend(assumption_summary.warnings)
        return self._build_report(
            builder=builder,
            all_records=diagnostic_records,
            optimization_success=True,
            audit_pass=audit_pass,
            residual_norm=residual_norm,
            max_abs_normalized_residual=max_abs,
            top_residuals=[_diagnostic_from_record(record) for record in diagnostic_records[:top_n_residuals]],
            assumptions=assumption_summary,
            warnings=_dedupe(warnings),
            metadata={
                "mode": "hierarchy_evaluate",
                "solver_attempted": False,
                "optimization_success_semantics": "not_applicable_no_solver",
                "audit_threshold": self.spec.system.solver.audit_threshold,
                "observation_name": observed.observation_name,
                "observation_metadata": observed.metadata,
                "observed_variable_count": len(observed.variables),
                "unknown_observed_variables": unknown,
                "unit_warnings": unit_warnings,
                "active_residual_count": len(solver_records),
                "diagnostic_residual_count": len(diagnostic_records),
                "assumption_confidence_integration": "report_level_only",
            },
            top_n_residuals=top_n_residuals,
            top_n_blocks=top_n_blocks,
        )

    def compare_observed(
        self,
        observed: ObservedValuesSpec,
        top_n_residuals: int = 20,
        top_n_blocks: int = 10,
    ) -> HierarchicalComparisonReport:
        """Solve a reference audit and compare external observed values by hierarchy."""

        builder = ResidualBuilder(self.spec.system)
        solver_result = BoundedSolver(builder, self.spec.system.solver).solve()
        observed_report = self.evaluate_observed(
            observed,
            top_n_residuals=top_n_residuals,
            top_n_blocks=top_n_blocks,
        )
        registry = builder.build_registry()
        observed_values, missing, _unknown = _observed_values_for_registry(observed, registry)
        if missing:
            raise ValueError(
                "observed values missing required registered variables: "
                + ", ".join(missing)
            )
        deviations = _variable_deviations(
            registry,
            solver_result.variables,
            observed_values,
            top_n_residuals,
        )
        warnings = list(observed_report.warnings)
        if not solver_result.optimization_success:
            warnings.append("reference optimizer did not converge")
        if not solver_result.audit_pass:
            warnings.append("reference audit did not pass")
        return HierarchicalComparisonReport(
            audit_name=self.spec.audit_name,
            system_name=self.spec.system.system_name,
            observation_name=observed.observation_name,
            reference_optimization_success=solver_result.optimization_success,
            reference_audit_pass=solver_result.audit_pass,
            observed_audit_pass=observed_report.audit_pass,
            reference_residual_norm=float(solver_result.residual_norm),
            observed_residual_norm=float(observed_report.residual_norm),
            reference_variables={key: float(value) for key, value in solver_result.variables.items()},
            observed_variables={key: float(value) for key, value in observed_values.items()},
            top_variable_deviations=deviations,
            observed_hierarchy=observed_report,
            warnings=_dedupe(warnings),
            metadata={
                "mode": "hierarchy_compare",
                "solver_attempted": True,
                "observation_metadata": observed.metadata,
                "reference_solver": {
                    "status": solver_result.status,
                    "message": solver_result.message,
                    "nfev": solver_result.nfev,
                    "max_nfev": solver_result.max_nfev,
                    "cost": solver_result.cost,
                    "optimality": solver_result.optimality,
                },
            },
        )

    def _build_report(
        self,
        *,
        builder: ResidualBuilder,
        all_records: list[ResidualRecord],
        optimization_success: bool,
        audit_pass: bool,
        residual_norm: float,
        max_abs_normalized_residual: float,
        top_residuals: list[ResidualDiagnostic],
        assumptions: AssumptionSummary,
        warnings: list[str],
        metadata: dict[str, Any],
        top_n_residuals: int,
        top_n_blocks: int,
    ) -> HierarchicalAuditReport:
        all_diagnostics = [_diagnostic_from_record(record) for record in all_records]
        block_index = BlockIndex(self.spec.hierarchy, builder.system)
        assignments = [block_index.assignment_for_residual(record) for record in all_records]
        diagnostics_by_name = {diagnostic.name: diagnostic for diagnostic in all_diagnostics}
        residuals_by_block: dict[str, list[ResidualDiagnostic]] = {block.id: [] for block in self.spec.hierarchy.blocks}
        unassigned: list[ResidualDiagnostic] = []
        for assignment in assignments:
            diagnostic = diagnostics_by_name[assignment.residual_name]
            if assignment.block_id is None:
                unassigned.append(diagnostic)
            else:
                residuals_by_block.setdefault(assignment.block_id, []).append(diagnostic)

        scorer = BlockScorer()
        confidence_scorer = ConfidenceScorer()
        planner = RefinementPlanner()
        block_diagnostics: list[BlockDiagnostic] = []
        registry = builder.build_registry()
        component_parameters = {component.id: component.parameters for component in builder.system.components}
        for block in self.spec.hierarchy.blocks:
            block_residuals = residuals_by_block.get(block.id, [])
            scored_residuals = scorer.filter_scored(block_residuals, self.spec.hierarchy.scoring)
            missing_variables = _missing_variables(block.required_variables, registry.names())
            missing_parameters = _missing_parameters(block, component_parameters)
            score = scorer.score_block(block, block_residuals, self.spec.hierarchy.scoring)
            confidence = confidence_scorer.score(
                block,
                missing_variables,
                missing_parameters,
                block_residuals,
                self.spec.hierarchy.confidence,
            )
            diagnostic = BlockDiagnostic(
                block_id=block.id,
                name=block.name,
                level=block.level,
                parent_id=block.parent_id,
                tags=list(block.tags),
                score=score,
                confidence=confidence,
                audit_pass=score <= self.spec.system.solver.audit_threshold,
                max_abs_normalized_residual=scorer.max_abs_normalized_residual(scored_residuals),
                residual_norm=scorer.residual_norm(scored_residuals),
                top_residuals=scorer.select_top_residuals(scored_residuals, top_n_residuals),
                post_check_residuals=scorer.select_top_residuals(
                    [item for item in block_residuals if item.role == "post_check"],
                    top_n_residuals,
                ),
                missing_required_variables=missing_variables,
                missing_required_parameters=missing_parameters,
                unassigned_residual_count=0,
                metadata=dict(block.metadata),
            )
            recommendations = planner.recommended_refinements(diagnostic, self.spec.hierarchy)
            block_diagnostics.append(
                BlockDiagnostic(
                    **{
                        **asdict(diagnostic),
                        "top_residuals": diagnostic.top_residuals,
                        "post_check_residuals": diagnostic.post_check_residuals,
                        "recommended_refinements": recommendations,
                    }
                )
            )

        top_blocks = sorted(block_diagnostics, key=lambda item: (-item.score, item.level, item.block_id))[:top_n_blocks]
        recommendations = planner.overall_plan(top_blocks)
        missing_required_variables = sorted({item for block in block_diagnostics for item in block.missing_required_variables})
        missing_required_parameters = sorted({item for block in block_diagnostics for item in block.missing_required_parameters})
        report_warnings = list(warnings)
        if unassigned:
            report_warnings.append(f"{len(unassigned)} residuals were not assigned to hierarchy blocks")
        unassigned_components = block_index.unassigned_components()
        if unassigned_components:
            report_warnings.append(f"unassigned components: {', '.join(unassigned_components)}")
        if missing_required_variables:
            report_warnings.append("hierarchy missing required variables")
        if missing_required_parameters:
            report_warnings.append("hierarchy missing required parameters")
        return HierarchicalAuditReport(
            audit_name=self.spec.audit_name,
            system_name=builder.system.system_name,
            optimization_success=optimization_success,
            audit_pass=audit_pass,
            residual_norm=float(residual_norm),
            max_abs_normalized_residual=float(max_abs_normalized_residual),
            top_residuals=top_residuals,
            top_blocks=top_blocks,
            block_assignments=assignments,
            unassigned_residuals=unassigned,
            missing_required_variables=missing_required_variables,
            missing_required_parameters=missing_required_parameters,
            recommended_refinements=recommendations,
            assumptions=assumptions,
            warnings=_dedupe(report_warnings),
            metadata={
                **metadata,
                "hierarchy": inspect_hierarchy(self.spec),
            },
        )

    def to_dict(self, report: Any) -> dict[str, Any]:
        return asdict(report)

    def to_json(self, report: HierarchicalAuditReport, pretty: bool = False) -> str:
        return json.dumps(self.to_dict(report), indent=2 if pretty else None, sort_keys=True)


def inspect_hierarchy(spec: HierarchicalAuditSpec) -> dict[str, Any]:
    index = BlockIndex(spec.hierarchy, spec.system)
    children = {block.id: [child.id for child in index.children(block.id)] for block in spec.hierarchy.blocks}
    return {
        "audit_name": spec.audit_name,
        "system_name": spec.system.system_name,
        "blocks": [
            {
                "id": block.id,
                "name": block.name,
                "level": block.level,
                "parent_id": block.parent_id,
                "children": children[block.id],
                "components": list(block.components),
                "tags": list(block.tags),
                "required_variables": list(block.required_variables),
                "optional_variables": list(block.optional_variables),
                "required_parameters": list(block.required_parameters),
                "optional_parameters": list(block.optional_parameters),
                "refinement_template_ids": list(block.refinement_template_ids),
            }
            for block in spec.hierarchy.blocks
        ],
        "root_blocks": [block.id for block in index.root_blocks()],
        "refinement_rules": [rule.model_dump() for rule in spec.hierarchy.refinement_rules],
        "referenced_components": sorted(index._component_to_block),
        "missing_components": index.unassigned_components(),
        "unassigned_components": index.unassigned_components(),
        "scoring": spec.hierarchy.scoring.model_dump(),
        "confidence": spec.hierarchy.confidence.model_dump(),
    }


def plan_from_report(report: HierarchicalAuditReport) -> dict[str, Any]:
    return {
        "top_blocks": [asdict(block) for block in report.top_blocks],
        "recommended_refinements": [asdict(item) for item in report.recommended_refinements],
        "missing_required_variables": report.missing_required_variables,
        "missing_required_parameters": report.missing_required_parameters,
        "warnings": report.warnings,
    }


def _diagnostic_from_record(record: ResidualRecord) -> ResidualDiagnostic:
    return ResidualDiagnostic(
        name=record.name,
        source=record.source,
        role=record.role,
        raw_value=float(record.value),
        scale=float(record.scale),
        normalized_value=float(record.normalized_value),
        abs_normalized_value=float(record.abs_normalized_value),
        diagnostic_key=record.diagnostic_key,
        description=record.description,
    )


def _parse_connection_residual_name(name: str) -> tuple[str, str] | None:
    if not name.startswith("connection:") or "=" not in name:
        return None
    left, right = name[len("connection:") :].split("=", 1)
    return left, right


def _parse_boundary_residual_name(name: str) -> str | None:
    if not name.startswith("boundary:"):
        return None
    return name[len("boundary:") :]


def _qualified_variable_candidates(*texts: str) -> Iterable[str]:
    for text in texts:
        for token in text.replace("=", " ").replace(":", " ").replace(",", " ").split():
            if "." in token:
                yield token.strip()


def _missing_variables(required: list[str], registry_names: list[str]) -> list[str]:
    registry = set(registry_names)
    return [name for name in required if "." in name and name not in registry]


def _missing_parameters(block: AuditBlockSpec, component_parameters: dict[str, dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for parameter in block.required_parameters:
        if "." in parameter:
            component_id, parameter_name = parameter.split(".", 1)
            if parameter_name not in component_parameters.get(component_id, {}):
                missing.append(parameter)
        elif not any(parameter in component_parameters.get(component_id, {}) for component_id in block.components):
            missing.append(parameter)
    return missing


def _observed_values_for_registry(
    observed: ObservedValuesSpec,
    registry: VariableRegistry,
) -> tuple[dict[str, float], list[str], list[str]]:
    registered = set(registry.names())
    observed_names = set(observed.variables)
    missing = sorted(registered - observed_names)
    unknown = sorted(observed_names - registered)
    values = {
        name: float(observed.variables[name].value)
        for name in registry.names()
        if name in observed.variables
    }
    return values, missing, unknown


def _unit_warnings(observed: ObservedValuesSpec, registry: VariableRegistry) -> list[str]:
    warnings: list[str] = []
    for name in registry.names():
        if name not in observed.variables:
            continue
        expected_unit = registry.get_record(name).unit
        observed_unit = observed.variables[name].unit
        if expected_unit and observed_unit and expected_unit != observed_unit:
            warnings.append(
                f"{name}: observed unit '{observed_unit}' differs from registry unit "
                f"'{expected_unit}'; numeric value was used as SI"
            )
    return warnings


def _active_residual_metrics(records: list[ResidualRecord]) -> tuple[float, float]:
    normalized = np.array([record.normalized_value for record in records], dtype=float)
    if normalized.ndim != 1 or not np.all(np.isfinite(normalized)):
        raise ValueError("observed residual vector contains NaN or inf")
    residual_norm = float(np.linalg.norm(normalized))
    max_abs = float(np.max(np.abs(normalized))) if normalized.size else 0.0
    return residual_norm, max_abs


def _variable_deviations(
    registry: VariableRegistry,
    reference_variables: dict[str, float],
    observed_variables: dict[str, float],
    top_n: int,
) -> list[VariableDeviationDiagnostic]:
    deviations: list[VariableDeviationDiagnostic] = []
    for name in registry.names():
        record = registry.get_record(name)
        reference_value = float(reference_variables[name])
        observed_value = float(observed_variables[name])
        raw_delta = observed_value - reference_value
        normalized_delta = raw_delta / record.scale
        deviations.append(
            VariableDeviationDiagnostic(
                variable=name,
                reference_value=reference_value,
                observed_value=observed_value,
                raw_delta=float(raw_delta),
                scale=float(record.scale),
                normalized_delta=float(normalized_delta),
                abs_normalized_delta=float(abs(normalized_delta)),
                unit=record.unit,
            )
        )
    return sorted(
        deviations,
        key=lambda deviation: deviation.abs_normalized_delta,
        reverse=True,
    )[:top_n]


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


__all__ = [
    "BlockDiagnostic",
    "BlockIndex",
    "BlockScorer",
    "ConfidenceScorer",
    "HierarchicalComparisonReport",
    "HierarchicalAuditReport",
    "HierarchicalAuditRunner",
    "RecommendedRefinement",
    "RefinementPlanner",
    "ResidualBlockAssignment",
    "inspect_hierarchy",
    "plan_from_report",
]
