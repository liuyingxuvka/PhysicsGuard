"""FlowGuard model for PhysicsGuard model-dataset validation gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class ValidationInput:
    case_id: str
    contracts_passed: bool
    direct_validation_ran: bool
    calibration_enabled: bool
    calibration_parameters_bounded: bool
    observed_values_mutated: bool
    optimization_success: bool
    holdout_passed: bool
    confidence_feedback_recorded: bool
    dataset_identity_current: bool = True
    mapping_review_current: bool = True
    claim_scope_honest: bool = True
    split_disjoint: bool = True
    residual_series_evaluated: bool = True
    envelope_intervals_preserved: bool = True
    depth_receipt_emitted: bool = True
    coverage_universe_complete: bool = True
    temporal_adequacy_passed: bool = True
    critical_family_coverage_passed: bool = True
    parameter_temporal_adequacy_passed: bool = True
    parameter_universe_complete: bool = True
    per_parameter_denominator_current: bool = True
    manifest_point_denominator_reconciled: bool = True
    parameter_strata_adequate: bool = True
    dynamic_coverage_floor_passed: bool = True
    representative_parameter_evidence_passed: bool = True
    parameter_model_contribution_passed: bool = True
    parameter_contribution_mode: str = "sensitive"
    non_sensitive_disposition_bounded: bool = True
    static_parameter_binding_passed: bool = True
    prediction_requested: bool = False
    stateful_dynamic: bool = False
    predictive_rollout_passed: bool = False
    portable_native_runtime_bound: bool = True


@dataclass(frozen=True)
class ContractsReady:
    case_id: str
    direct_validation_ran: bool
    calibration_enabled: bool
    calibration_parameters_bounded: bool
    observed_values_mutated: bool
    optimization_success: bool
    holdout_passed: bool
    confidence_feedback_recorded: bool
    dataset_identity_current: bool
    mapping_review_current: bool
    claim_scope_honest: bool
    split_disjoint: bool
    residual_series_evaluated: bool
    envelope_intervals_preserved: bool
    depth_receipt_emitted: bool
    coverage_universe_complete: bool
    temporal_adequacy_passed: bool
    critical_family_coverage_passed: bool
    parameter_temporal_adequacy_passed: bool
    parameter_universe_complete: bool
    per_parameter_denominator_current: bool
    manifest_point_denominator_reconciled: bool
    parameter_strata_adequate: bool
    dynamic_coverage_floor_passed: bool
    representative_parameter_evidence_passed: bool
    parameter_model_contribution_passed: bool
    parameter_contribution_mode: str
    non_sensitive_disposition_bounded: bool
    static_parameter_binding_passed: bool
    prediction_requested: bool
    stateful_dynamic: bool
    predictive_rollout_passed: bool
    portable_native_runtime_bound: bool


@dataclass(frozen=True)
class DepthReady:
    case_id: str
    direct_validation_ran: bool
    calibration_enabled: bool
    calibration_parameters_bounded: bool
    observed_values_mutated: bool
    optimization_success: bool
    holdout_passed: bool
    confidence_feedback_recorded: bool
    depth_receipt_emitted: bool


@dataclass(frozen=True)
class DirectValidationReady:
    case_id: str
    calibration_enabled: bool
    calibration_parameters_bounded: bool
    observed_values_mutated: bool
    optimization_success: bool
    holdout_passed: bool
    confidence_feedback_recorded: bool
    depth_receipt_emitted: bool


@dataclass(frozen=True)
class CalibrationReady:
    case_id: str
    holdout_passed: bool
    confidence_feedback_recorded: bool
    depth_receipt_emitted: bool


@dataclass(frozen=True)
class ValidationPassed:
    case_id: str


@dataclass(frozen=True)
class ValidationPartial:
    case_id: str
    reason: str


@dataclass(frozen=True)
class ValidationBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    contracts_ready: tuple[str, ...] = ()
    depth_inputs_ready: tuple[str, ...] = ()
    direct_validation_ran: tuple[str, ...] = ()
    calibration_ran: tuple[str, ...] = ()
    holdout_passed: tuple[str, ...] = ()
    confidence_feedback_recorded: tuple[str, ...] = ()
    depth_receipt_emitted: tuple[str, ...] = ()
    portable_native_runtime_bound: tuple[str, ...] = ()
    validation_passed: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class CheckContracts:
    name = "CheckContracts"
    reads = ()
    writes = ("contracts_ready", "blocked")
    accepted_input_type = ValidationInput
    input_description = "model-dataset validation request"
    output_description = "ContractsReady or ValidationBlocked"
    idempotency = "Contract checks are deterministic for current files."

    def apply(self, input_obj: ValidationInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.contracts_passed:
            yield FunctionResult(
                output=ValidationBlocked(input_obj.case_id, "contracts_not_passed"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="contracts_block_validation",
            )
            return
        yield FunctionResult(
            output=ContractsReady(
                input_obj.case_id,
                input_obj.direct_validation_ran,
                input_obj.calibration_enabled,
                input_obj.calibration_parameters_bounded,
                input_obj.observed_values_mutated,
                input_obj.optimization_success,
                input_obj.holdout_passed,
                input_obj.confidence_feedback_recorded,
                input_obj.dataset_identity_current,
                input_obj.mapping_review_current,
                input_obj.claim_scope_honest,
                input_obj.split_disjoint,
                input_obj.residual_series_evaluated,
                input_obj.envelope_intervals_preserved,
                input_obj.depth_receipt_emitted,
                input_obj.coverage_universe_complete,
                input_obj.temporal_adequacy_passed,
                input_obj.critical_family_coverage_passed,
                input_obj.parameter_temporal_adequacy_passed,
                input_obj.parameter_universe_complete,
                input_obj.per_parameter_denominator_current,
                input_obj.manifest_point_denominator_reconciled,
                input_obj.parameter_strata_adequate,
                input_obj.dynamic_coverage_floor_passed,
                input_obj.representative_parameter_evidence_passed,
                input_obj.parameter_model_contribution_passed,
                input_obj.parameter_contribution_mode,
                input_obj.non_sensitive_disposition_bounded,
                input_obj.static_parameter_binding_passed,
                input_obj.prediction_requested,
                input_obj.stateful_dynamic,
                input_obj.predictive_rollout_passed,
                input_obj.portable_native_runtime_bound,
            ),
            new_state=replace(state, contracts_ready=state.contracts_ready + (input_obj.case_id,)),
            label="contracts_passed",
        )


class GateValidationDepth:
    name = "GateValidationDepth"
    reads = ("contracts_ready",)
    writes = ("depth_inputs_ready", "portable_native_runtime_bound", "blocked")
    accepted_input_type = ContractsReady
    input_description = "contract-reviewed validation-depth inputs"
    output_description = "DepthReady or ValidationBlocked"
    idempotency = "Depth gates compare current identities and declared scope without mutating evidence."

    def apply(self, input_obj: ContractsReady, state: State) -> Iterable[FunctionResult]:
        gates = (
            (input_obj.portable_native_runtime_bound, "portable_native_runtime_missing", "portable_native_runtime_missing_blocked"),
            (input_obj.dataset_identity_current, "dataset_identity_stale", "dataset_identity_stale_blocked"),
            (input_obj.mapping_review_current, "mapping_review_uncertain", "mapping_review_uncertain_blocked"),
            (input_obj.claim_scope_honest, "claim_scope_overreach", "claim_scope_overreach_blocked"),
            (input_obj.split_disjoint, "calibration_holdout_overlap", "split_overlap_blocked"),
            (input_obj.residual_series_evaluated, "residual_series_missing", "residual_series_missing_blocked"),
            (input_obj.envelope_intervals_preserved, "envelope_intervals_missing", "envelope_intervals_missing_blocked"),
            (input_obj.coverage_universe_complete, "coverage_universe_incomplete", "coverage_universe_incomplete_blocked"),
            (input_obj.temporal_adequacy_passed, "temporal_adequacy_failed", "temporal_adequacy_failed_blocked"),
            (input_obj.critical_family_coverage_passed, "critical_family_coverage_failed", "critical_family_coverage_failed_blocked"),
            (input_obj.parameter_temporal_adequacy_passed, "parameter_temporal_adequacy_failed", "parameter_temporal_adequacy_failed_blocked"),
            (input_obj.parameter_universe_complete, "parameter_universe_incomplete", "parameter_universe_incomplete_blocked"),
            (input_obj.per_parameter_denominator_current, "per_parameter_denominator_missing", "per_parameter_denominator_missing_blocked"),
            (input_obj.manifest_point_denominator_reconciled, "manifest_point_denominator_mismatch", "manifest_point_denominator_mismatch_blocked"),
            (input_obj.parameter_strata_adequate, "parameter_strata_incomplete", "parameter_strata_incomplete_blocked"),
            (input_obj.dynamic_coverage_floor_passed, "dynamic_coverage_floor_insufficient", "dynamic_coverage_floor_insufficient_blocked"),
            (input_obj.representative_parameter_evidence_passed, "representative_parameter_evidence_missing", "representative_parameter_evidence_missing_blocked"),
            (input_obj.parameter_contribution_mode in {"sensitive", "verified_non_sensitive"}, "parameter_contribution_expectation_invalid", "parameter_contribution_expectation_invalid_blocked"),
            (input_obj.parameter_contribution_mode != "verified_non_sensitive" or input_obj.non_sensitive_disposition_bounded, "non_sensitive_parameter_disposition_unbounded", "non_sensitive_parameter_disposition_unbounded_blocked"),
            (input_obj.parameter_model_contribution_passed, "parameter_model_contribution_missing", "parameter_model_contribution_missing_blocked"),
            (input_obj.static_parameter_binding_passed, "static_parameter_binding_missing", "static_parameter_binding_missing_blocked"),
        )
        for passed, reason, label in gates:
            if not passed:
                yield FunctionResult(
                    output=ValidationBlocked(input_obj.case_id, reason),
                    new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                    label=label,
                )
                return
        if input_obj.prediction_requested and not input_obj.stateful_dynamic:
            yield FunctionResult(
                output=ValidationBlocked(input_obj.case_id, "pointwise_prediction_forbidden"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="pointwise_prediction_forbidden_blocked",
            )
            return
        if input_obj.prediction_requested and not input_obj.predictive_rollout_passed:
            yield FunctionResult(
                output=ValidationBlocked(input_obj.case_id, "predictive_rollout_failed"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="predictive_rollout_failed_blocked",
            )
            return
        yield FunctionResult(
            output=DepthReady(
                input_obj.case_id,
                input_obj.direct_validation_ran,
                input_obj.calibration_enabled,
                input_obj.calibration_parameters_bounded,
                input_obj.observed_values_mutated,
                input_obj.optimization_success,
                input_obj.holdout_passed,
                input_obj.confidence_feedback_recorded,
                input_obj.depth_receipt_emitted,
            ),
            new_state=replace(
                state,
                depth_inputs_ready=state.depth_inputs_ready + (input_obj.case_id,),
                portable_native_runtime_bound=state.portable_native_runtime_bound
                + (input_obj.case_id,),
            ),
            label="validation_depth_inputs_ready",
        )


class RunDirectValidation:
    name = "RunDirectValidation"
    reads = ("depth_inputs_ready",)
    writes = ("direct_validation_ran", "blocked")
    accepted_input_type = DepthReady
    input_description = "DepthReady"
    output_description = "DirectValidationReady or ValidationBlocked"
    idempotency = "Direct validation reads model and observed values only."

    def apply(self, input_obj: DepthReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.direct_validation_ran:
            yield FunctionResult(
                output=ValidationBlocked(input_obj.case_id, "direct_validation_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="direct_validation_missing",
            )
            return
        yield FunctionResult(
            output=DirectValidationReady(
                input_obj.case_id,
                input_obj.calibration_enabled,
                input_obj.calibration_parameters_bounded,
                input_obj.observed_values_mutated,
                input_obj.optimization_success,
                input_obj.holdout_passed,
                input_obj.confidence_feedback_recorded,
                input_obj.depth_receipt_emitted,
            ),
            new_state=replace(state, direct_validation_ran=state.direct_validation_ran + (input_obj.case_id,)),
            label="direct_validation_ran",
        )


class OptionalCalibration:
    name = "OptionalCalibration"
    reads = ("direct_validation_ran",)
    writes = ("calibration_ran", "partial", "blocked")
    accepted_input_type = DirectValidationReady
    input_description = "DirectValidationReady"
    output_description = "CalibrationReady, ValidationPartial, or ValidationBlocked"
    idempotency = "Calibration is deterministic for a fixed optimizer configuration."

    def apply(self, input_obj: DirectValidationReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.observed_values_mutated:
            yield FunctionResult(
                output=ValidationBlocked(input_obj.case_id, "observed_values_mutated"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="observed_mutation_blocked",
            )
            return
        if not input_obj.calibration_enabled:
            yield FunctionResult(
                output=CalibrationReady(
                    input_obj.case_id,
                    True,
                    input_obj.confidence_feedback_recorded,
                    input_obj.depth_receipt_emitted,
                ),
                new_state=state,
                label="calibration_not_enabled",
            )
            return
        if not input_obj.calibration_parameters_bounded:
            yield FunctionResult(
                output=ValidationBlocked(input_obj.case_id, "calibration_parameters_unbounded"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="calibration_unbounded_blocked",
            )
            return
        yield FunctionResult(
            output=CalibrationReady(
                input_obj.case_id,
                input_obj.holdout_passed,
                input_obj.confidence_feedback_recorded,
                input_obj.depth_receipt_emitted,
            ),
            new_state=replace(state, calibration_ran=state.calibration_ran + (input_obj.case_id,)),
            label="calibration_bounded",
        )


class GateValidationClaim:
    name = "GateValidationClaim"
    reads = ("direct_validation_ran",)
    writes = (
        "holdout_passed",
        "confidence_feedback_recorded",
        "depth_receipt_emitted",
        "validation_passed",
        "partial",
        "blocked",
    )
    accepted_input_type = object
    input_description = "CalibrationReady, ValidationPartial, or ValidationBlocked"
    output_description = "ValidationPassed, ValidationPartial, or ValidationBlocked"
    idempotency = "Claim gate projects current evidence into status."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, ValidationBlocked):
            yield FunctionResult(output=input_obj, new_state=state, label="validation_blocked")
            return
        if isinstance(input_obj, CalibrationReady):
            if not input_obj.depth_receipt_emitted:
                yield FunctionResult(
                    output=ValidationBlocked(input_obj.case_id, "depth_receipt_missing"),
                    new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                    label="depth_receipt_missing_blocked",
                )
                return
            if not input_obj.holdout_passed:
                yield FunctionResult(
                    output=ValidationPartial(input_obj.case_id, "holdout_not_passed"),
                    new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                    label="holdout_partial",
                )
                return
            if not input_obj.confidence_feedback_recorded:
                yield FunctionResult(
                    output=ValidationPartial(input_obj.case_id, "confidence_feedback_missing"),
                    new_state=replace(state, holdout_passed=state.holdout_passed + (input_obj.case_id,), partial=state.partial + (input_obj.case_id,)),
                    label="confidence_feedback_partial",
                )
                return
            yield FunctionResult(
                output=ValidationPassed(input_obj.case_id),
                new_state=replace(
                    state,
                    holdout_passed=state.holdout_passed + (input_obj.case_id,),
                    confidence_feedback_recorded=state.confidence_feedback_recorded + (input_obj.case_id,),
                    depth_receipt_emitted=state.depth_receipt_emitted + (input_obj.case_id,),
                    validation_passed=state.validation_passed + (input_obj.case_id,),
                ),
                label="validation_passed",
            )


def no_pass_without_contracts(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.validation_passed) - set(state.contracts_ready)
    if missing:
        return InvariantResult.fail(f"validation pass without contracts: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_direct_validation(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.validation_passed) - set(state.direct_validation_ran)
    if missing:
        return InvariantResult.fail(f"validation pass without direct validation: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_depth_inputs_and_receipt(state: State, trace) -> InvariantResult:
    del trace
    ready = (
        set(state.depth_inputs_ready)
        & set(state.depth_receipt_emitted)
        & set(state.portable_native_runtime_bound)
    )
    missing = set(state.validation_passed) - ready
    if missing:
        return InvariantResult.fail(f"validation pass without depth inputs/receipt: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_holdout_and_feedback(state: State, trace) -> InvariantResult:
    del trace
    ready = set(state.holdout_passed) & set(state.confidence_feedback_recorded)
    missing = set(state.validation_passed) - ready
    if missing:
        return InvariantResult.fail(f"validation pass without holdout/feedback: {sorted(missing)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("no_pass_without_contracts", "Validation pass requires passing contracts.", no_pass_without_contracts),
    Invariant("no_pass_without_direct_validation", "Validation pass requires direct validation.", no_pass_without_direct_validation),
    Invariant("no_pass_without_depth_inputs_and_receipt", "Validation pass requires current depth inputs and a native receipt.", no_pass_without_depth_inputs_and_receipt),
    Invariant("no_pass_without_holdout_and_feedback", "Validation pass requires holdout and confidence feedback.", no_pass_without_holdout_and_feedback),
)

EXTERNAL_INPUTS = (
    ValidationInput("clean_no_calibration", True, True, False, True, False, False, True, True),
    ValidationInput("calibrated_pass", True, True, True, True, False, True, True, True),
    ValidationInput("optimizer_only", True, True, True, True, False, True, False, True),
    ValidationInput("missing_contract", False, True, False, True, False, False, True, True),
    ValidationInput("mutates_observed", True, True, True, True, True, True, True, True),
    ValidationInput("unbounded_calibration", True, True, True, False, False, True, True, True),
)
DEPTH_EXTERNAL_INPUTS = (
    ValidationInput("portable_runtime_missing", True, True, False, True, False, False, True, True, portable_native_runtime_bound=False),
    ValidationInput("stale_dataset", True, True, False, True, False, False, True, True, dataset_identity_current=False),
    ValidationInput("uncertain_mapping", True, True, False, True, False, False, True, True, mapping_review_current=False),
    ValidationInput("snapshot_overclaim", True, True, False, True, False, False, True, True, claim_scope_honest=False),
    ValidationInput("split_overlap", True, True, True, True, False, True, True, True, split_disjoint=False),
    ValidationInput("series_missing", True, True, False, True, False, False, True, True, residual_series_evaluated=False),
    ValidationInput("envelope_intervals_missing", True, True, False, True, False, False, True, True, envelope_intervals_preserved=False),
    ValidationInput("depth_receipt_missing", True, True, False, True, False, False, True, True, depth_receipt_emitted=False),
    ValidationInput("shallow_point_universe", True, True, False, True, False, False, True, True, coverage_universe_complete=False),
    ValidationInput("endpoint_or_duplicate_time", True, True, False, True, False, False, True, True, temporal_adequacy_passed=False),
    ValidationInput("shallow_signal_family", True, True, False, True, False, False, True, True, critical_family_coverage_passed=False),
    ValidationInput("one_point_time_varying_parameter", True, True, False, True, False, False, True, True, parameter_temporal_adequacy_passed=False),
    ValidationInput("ten_thousand_parameters_two_bound", True, True, False, True, False, False, True, True, parameter_universe_complete=False),
    ValidationInput("parameter_denominator_missing", True, True, False, True, False, False, True, True, per_parameter_denominator_current=False),
    ValidationInput("manifest_point_count_mismatch", True, True, False, True, False, False, True, True, manifest_point_denominator_reconciled=False),
    ValidationInput("parameter_endpoints_or_same_stage", True, True, False, True, False, False, True, True, parameter_strata_adequate=False),
    ValidationInput("three_of_thousand", True, True, False, True, False, False, True, True, dynamic_coverage_floor_passed=False),
    ValidationInput("one_shallow_parameter_among_deep", True, True, False, True, False, False, True, True, parameter_temporal_adequacy_passed=False),
    ValidationInput("representative_parameter_without_direction_envelope", True, True, False, True, False, False, True, True, representative_parameter_evidence_passed=False),
    ValidationInput("disconnected_time_varying_parameter", True, True, False, True, False, False, True, True, parameter_model_contribution_passed=False),
    ValidationInput("effectless_sensitive_parameter", True, True, False, True, False, False, True, True, parameter_model_contribution_passed=False),
    ValidationInput("unbounded_non_sensitive_disposition", True, True, False, True, False, False, True, True, parameter_contribution_mode="verified_non_sensitive", non_sensitive_disposition_bounded=False),
    ValidationInput("verified_non_sensitive_parameter", True, True, False, True, False, False, True, True, parameter_contribution_mode="verified_non_sensitive", non_sensitive_disposition_bounded=True),
    ValidationInput("static_parameter_without_binding", True, True, False, True, False, False, True, True, static_parameter_binding_passed=False),
    ValidationInput("representative_32_of_1000", True, True, False, True, False, False, True, True),
    ValidationInput("pointwise_prediction", True, True, False, True, False, False, True, True, prediction_requested=True),
    ValidationInput("stateful_rollout_failed", True, True, False, True, False, False, True, True, prediction_requested=True, stateful_dynamic=True, predictive_rollout_passed=False),
    ValidationInput("stateful_rollout_pass", True, True, False, True, False, False, True, True, prediction_requested=True, stateful_dynamic=True, predictive_rollout_passed=True),
)
MAX_SEQUENCE_LENGTH = 5


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (ValidationPassed, ValidationPartial, ValidationBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            CheckContracts(),
            GateValidationDepth(),
            RunDirectValidation(),
            OptionalCalibration(),
            GateValidationClaim(),
        ),
        name="physicsguard_model_dataset_validation",
    )
