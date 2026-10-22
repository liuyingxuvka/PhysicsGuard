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


@dataclass(frozen=True)
class DirectValidationReady:
    case_id: str
    calibration_enabled: bool
    calibration_parameters_bounded: bool
    observed_values_mutated: bool
    optimization_success: bool
    holdout_passed: bool
    confidence_feedback_recorded: bool


@dataclass(frozen=True)
class CalibrationReady:
    case_id: str
    holdout_passed: bool
    confidence_feedback_recorded: bool


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
            ),
            new_state=replace(state, contracts_ready=state.contracts_ready + (input_obj.case_id,)),
            label="contracts_passed",
        )


class GateValidationDepth:
    name = "GateValidationDepth"
    reads = ("contracts_ready",)
    writes = ("depth_inputs_ready", "partial", "blocked")
    accepted_input_type = ContractsReady
    input_description = "contract-reviewed validation-depth inputs"
    output_description = "DepthReady or ValidationBlocked"
    idempotency = "Depth gates compare current identities and declared scope without mutating evidence."

    def apply(self, input_obj: ContractsReady, state: State) -> Iterable[FunctionResult]:
        hard_gates = (
            (input_obj.dataset_identity_current, "dataset_files_missing", "dataset_files_missing_blocked"),
            (input_obj.mapping_review_current, "mapping_review_uncertain", "mapping_review_uncertain_blocked"),
            (input_obj.claim_scope_honest, "claim_scope_overreach", "claim_scope_overreach_blocked"),
            (input_obj.split_disjoint, "calibration_holdout_overlap", "split_overlap_blocked"),
            (input_obj.residual_series_evaluated, "residual_series_missing", "residual_series_missing_blocked"),
            (input_obj.envelope_intervals_preserved, "envelope_intervals_missing", "envelope_intervals_missing_blocked"),
            (input_obj.parameter_contribution_mode in {"sensitive", "verified_non_sensitive"}, "parameter_contribution_expectation_invalid", "parameter_contribution_expectation_invalid_blocked"),
            (input_obj.parameter_contribution_mode != "verified_non_sensitive" or input_obj.non_sensitive_disposition_bounded, "non_sensitive_parameter_disposition_unbounded", "non_sensitive_parameter_disposition_unbounded_blocked"),
        )
        for passed, reason, label in hard_gates:
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
        # Adequacy floors are advisory: a shortfall makes the validation partial, never a pass.
        adequacy_gates = (
            (input_obj.coverage_universe_complete, "coverage_universe_incomplete"),
            (input_obj.temporal_adequacy_passed, "temporal_adequacy_failed"),
            (input_obj.critical_family_coverage_passed, "critical_family_coverage_failed"),
            (input_obj.parameter_temporal_adequacy_passed, "parameter_temporal_adequacy_failed"),
            (input_obj.parameter_universe_complete, "parameter_universe_incomplete"),
            (input_obj.per_parameter_denominator_current, "per_parameter_denominator_missing"),
            (input_obj.manifest_point_denominator_reconciled, "manifest_point_denominator_mismatch"),
            (input_obj.parameter_strata_adequate, "parameter_strata_incomplete"),
            (input_obj.dynamic_coverage_floor_passed, "dynamic_coverage_floor_insufficient"),
            (input_obj.representative_parameter_evidence_passed, "representative_parameter_evidence_missing"),
            (input_obj.parameter_model_contribution_passed, "parameter_model_contribution_missing"),
            (input_obj.static_parameter_binding_passed, "static_parameter_binding_missing"),
        )
        for passed, reason in adequacy_gates:
            if not passed:
                yield FunctionResult(
                    output=ValidationPartial(input_obj.case_id, reason),
                    new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                    label=f"{reason}_warning",
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
            ),
            new_state=replace(
                state,
                depth_inputs_ready=state.depth_inputs_ready + (input_obj.case_id,),
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


def no_pass_without_depth_inputs(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.validation_passed) - set(state.depth_inputs_ready)
    if missing:
        return InvariantResult.fail(f"validation pass without depth inputs: {sorted(missing)!r}")
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
    Invariant("no_pass_without_depth_inputs", "Validation pass requires checked depth inputs.", no_pass_without_depth_inputs),
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
    ValidationInput("missing_dataset_file", True, True, False, True, False, False, True, True, dataset_identity_current=False),
    ValidationInput("uncertain_mapping", True, True, False, True, False, False, True, True, mapping_review_current=False),
    ValidationInput("snapshot_overclaim", True, True, False, True, False, False, True, True, claim_scope_honest=False),
    ValidationInput("split_overlap", True, True, True, True, False, True, True, True, split_disjoint=False),
    ValidationInput("series_missing", True, True, False, True, False, False, True, True, residual_series_evaluated=False),
    ValidationInput("envelope_intervals_missing", True, True, False, True, False, False, True, True, envelope_intervals_preserved=False),
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
MAX_SEQUENCE_LENGTH = 2  # every ordered pair of the plain and the depth inputs


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


# Contract: what this model is about in the real code, its known-bad variants, and the replay on that code.

from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402

import yaml  # noqa: E402
from flowguard.explorer import Explorer  # noqa: E402

MODEL_ID = "model_dataset_validation"
PARENT = "validation"
ROOT = Path(__file__).resolve().parents[2]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
IMPLEMENTED_BY = {
    "CheckContracts": "src/physicsguard/core/model_dataset_validation.py:_contract_findings",
    "GateValidationDepth": "src/physicsguard/core/validation_depth.py:evaluate_validation_depth",
    "GateValidationDepth.adequacy": "src/physicsguard/core/validation_adequacy.py:evaluate_validation_adequacy_artifacts",
    "RunDirectValidation": "src/physicsguard/core/model_dataset_validation.py:_evaluate",
    "OptionalCalibration": "src/physicsguard/core/model_dataset_validation.py:_calibration_summary",
    "GateValidationClaim": "src/physicsguard/core/model_dataset_validation.py:_status",
}
TESTED_BY = {
    "no_pass_without_contracts": [
        "tests/test_model_dataset_validation.py:test_nonpassing_required_contract_blocks_validation",
    ],
    "no_pass_without_depth_inputs": [
        "tests/test_validation_depth_receipts.py:test_uncertain_required_mapping_blocks_broad_validation",
        "tests/test_validation_depth_receipts.py:test_adequacy_floors_are_warnings_not_failures",
    ],
    "no_pass_without_holdout_and_feedback": [
        "tests/test_validation_depth_receipts.py:test_identical_content_under_different_holdout_label_is_overlap",
    ],
}
EXPECTED_STATUS = {"ValidationPassed": "pass", "ValidationPartial": "partial", "ValidationBlocked": "fail"}
REQUIRED_LABELS = (
    "contracts_passed",
    "direct_validation_ran",
    "calibration_not_enabled",
    "calibration_bounded",
    "validation_passed",
    "holdout_partial",
    "contracts_block_validation",
    "observed_mutation_blocked",
    "calibration_unbounded_blocked",
    "dataset_files_missing_blocked",
    "mapping_review_uncertain_blocked",
    "split_overlap_blocked",
    "parameter_temporal_adequacy_failed_warning",
    "static_parameter_binding_missing_warning",
    "pointwise_prediction_forbidden_blocked",
)


def _explorer(workflow: Workflow) -> Explorer:
    """Every ordered pair of the plain and the depth inputs (1,056 sequences, well under a second)."""
    return Explorer(
        workflow=workflow,
        initial_states=(initial_state(),),
        external_inputs=(*EXTERNAL_INPUTS, *DEPTH_EXTERNAL_INPUTS),
        invariants=INVARIANTS,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        terminal_predicate=terminal_predicate,
        required_labels=REQUIRED_LABELS,
    )


def build_explorer() -> Explorer:
    return _explorer(build_workflow())


class _HardDepthGateIgnored(GateValidationDepth):
    """Known bad: a failed hard depth gate lets the case continue."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if isinstance(result.output, ValidationBlocked):
                ready = DepthReady(
                    input_obj.case_id,
                    input_obj.direct_validation_ran,
                    input_obj.calibration_enabled,
                    input_obj.calibration_parameters_bounded,
                    input_obj.observed_values_mutated,
                    input_obj.optimization_success,
                    input_obj.holdout_passed,
                    input_obj.confidence_feedback_recorded,
                )
                result = replace(result, output=ready, new_state=state, label="hard_depth_gate_ignored")
            yield result


class _FailedHoldoutPasses(GateValidationClaim):
    """Known bad: a failed holdout still yields a validation pass."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if result.label == "holdout_partial":
                result = replace(
                    result,
                    output=ValidationPassed(input_obj.case_id),
                    new_state=replace(state, validation_passed=state.validation_passed + (input_obj.case_id,)),
                    label="validation_passed",
                )
            yield result


class _FailedContractsContinue(CheckContracts):
    """Known bad: failed contracts are ignored while all later gates still run."""

    def apply(self, input_obj, state):
        if not input_obj.contracts_passed:
            for result in super().apply(replace(input_obj, contracts_passed=True), state):
                yield replace(result, new_state=replace(result.new_state, contracts_ready=state.contracts_ready))
            return
        yield from super().apply(input_obj, state)


class _DirectValidationSkipped(RunDirectValidation):
    """Known bad: skip direct validation but allow calibration and the claim gate."""

    def apply(self, input_obj, state):
        for result in super().apply(input_obj, state):
            if isinstance(result.output, DirectValidationReady):
                result = replace(result, new_state=replace(result.new_state, direct_validation_ran=state.direct_validation_ran))
            yield result


def broken_variants() -> dict[str, Explorer]:
    """Known-bad variants; each must violate an invariant of the design."""

    variants = {
        "hard_depth_gate_ignored": _HardDepthGateIgnored(),
        "failed_holdout_passes": _FailedHoldoutPasses(),
        "failed_contracts_continue": _FailedContractsContinue(),
        "direct_validation_skipped": _DirectValidationSkipped(),
    }
    return {
        name: _explorer(Workflow(
            tuple(broken if isinstance(broken, type(block)) else block for block in build_workflow().blocks),
            name=name,
        ))
        for name, broken in variants.items()
    }


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _edit_plan(pump: Path, name: str, change) -> Path:
    path = pump / "validation" / name
    data = _load(path)
    change(pump, data)
    _write(path, data)
    return path


def _rollout(semantics: str):
    def change(pump: Path, plan: dict) -> None:
        def ref(identity_id: str, relative: str, cases=()):
            return {"identity_id": identity_id, "path": f"../{relative}", "case_ids": list(cases)}

        plan["depth"]["model_semantics"] = semantics
        plan["depth"]["predictive_rollout"] = {
            "rollout_id": "conformance_rollout",
            "producer_receipt_id": "conformance-producer",
            "model_identity": ref("pump_model", "model/pump_loop_hierarchy.yaml"),
            "training": [ref("training_series", "observed/clean_observed_series.yaml", ["baseline_case", "speed_ramp_case_01", "speed_ramp_case_02"])],
            "prediction_series": ref("prediction", "observed/predicted_future_series.yaml"),
            "future_holdout_series": ref("future_holdout", "observed/future_holdout_series.yaml", ["future_case_1", "future_case_2", "future_case_3"]),
            "training_end_time": 0.2,
            "initial_state": {"pump_signal_map.x": 11.0, "pump_signal_map.y": 22.0},
            "step_size": 1.0,
            "step_unit": "s",
            "horizon_steps": 3,
            "target_signals": ["pump_signal_map.x", "pump_signal_map.y"],
            "signal_scales": {"pump_signal_map.x": 1.0, "pump_signal_map.y": 2.0},
            "threshold_source": "conformance thresholds",
            "thresholds": {
                "maximum_worst_step_normalized_error": 0.0,
                "maximum_accumulated_normalized_error": 0.0,
                "maximum_absolute_lag_steps": 0,
                "maximum_phase_error": 0.0,
                "maximum_drift": 0.0,
                "maximum_error_growth": 0.0,
            },
        }

    return change


def _uncertain_mapping(pump: Path, plan: dict) -> None:
    edges_path = pump / "coverage" / "pump_loop_mapping_edges.yaml"
    edges = _load(edges_path)
    edge = next(item for item in edges["edges"] if item["target"] == "pump_signal_map.y")
    edge["confidence"] = 0.4
    _write(edges_path, edges)


def _snapshot_overclaim(pump: Path, plan: dict) -> None:
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"] = series["points"][:1]
    _write(series_path, series)
    plan["depth"]["time_scope"] = {"claim_scope": "time_window", "start_time": 0.0, "end_time": 0.0, "time_unit": "s", "expected_point_count": 1}
    plan["depth"]["scenarios"] = plan["depth"]["scenarios"][:1]


def _split_overlap(pump: Path, plan: dict) -> None:
    shutil.copyfile(pump / "observed" / "calibration_train.yaml", pump / "observed" / "renamed_holdout.yaml")
    plan["calibration"]["holdout_observed"] = "../observed/renamed_holdout.yaml"
    plan["depth"] = _load(pump / "validation" / "clean_validation_plan.yaml")["depth"]
    plan["depth"]["split"] = {
        "training": [{"identity_id": "train", "path": "../observed/calibration_train.yaml", "case_ids": ["training_case"]}],
        "holdout": [{"identity_id": "holdout", "path": "../observed/renamed_holdout.yaml", "case_ids": ["holdout_case"]}],
    }


def _invalid_series_point(pump: Path, plan: dict) -> None:
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"][1].update({"valid": False, "invalid_reason": "sensor export gap", "variables": {}})
    _write(series_path, series)


def _failing_holdout(pump: Path, plan: dict) -> None:
    holdout_path = pump / "observed" / "calibration_holdout.yaml"
    holdout = _load(holdout_path)
    for name, item in holdout["variables"].items():
        if name.endswith(".y"):
            item["value"] = float(item["value"]) * 3.0
    _write(holdout_path, holdout)
    plan["observed_file"] = "../observed/clean_observed.yaml"


REAL_CASES = {
    "clean_no_calibration": ("clean_validation_plan.yaml", lambda pump, plan: None),
    "missing_contract": ("clean_validation_plan.yaml", lambda pump, plan: plan["contracts"][0].update(contract="../contracts/unclassified_contract.yaml")),
    "calibrated_pass": ("calibration_validation_plan.yaml", lambda pump, plan: plan.update(observed_file="../observed/clean_observed.yaml")),
    "optimizer_only": ("calibration_validation_plan.yaml", _failing_holdout),
    "unbounded_calibration": ("calibration_validation_plan.yaml", lambda pump, plan: plan["calibration"]["parameters"][0].pop("upper")),
    "missing_dataset_file": ("clean_validation_plan.yaml", lambda pump, plan: plan["depth"]["dataset"]["files"][0].update(path="../data/missing.csv")),
    "uncertain_mapping": ("clean_validation_plan.yaml", _uncertain_mapping),
    "snapshot_overclaim": ("clean_validation_plan.yaml", _snapshot_overclaim),
    "split_overlap": ("calibration_validation_plan.yaml", _split_overlap),
    "series_missing": ("clean_validation_plan.yaml", _invalid_series_point),
    "one_point_time_varying_parameter": ("shallow_time_varying_validation_plan.yaml", lambda pump, plan: None),
    "pointwise_prediction": ("clean_validation_plan.yaml", _rollout("pointwise")),
    "stateful_rollout_pass": ("clean_validation_plan.yaml", _rollout("stateful_dynamic")),
}


class ReplayReport:
    """Conformance result: how many model cases were replayed on the real code, and the mismatches."""

    def __init__(self, checked: int, mismatches: list[str]) -> None:
        self.checked = checked
        self.mismatches = tuple(mismatches)
        self.ok = not self.mismatches

    def format_text(self, max_examples: int | None = None) -> str:
        lines = [f"conformance: {self.checked - len(self.mismatches)}/{self.checked} model cases match the real code"]
        return "\n".join(lines + [f"  mismatch: {line}" for line in self.mismatches[:max_examples]])


def conformance() -> ReplayReport:
    """Run each mapped model case through validate_model_dataset and compare the status."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from physicsguard.core.model_dataset_validation import validate_model_dataset

    workflow = build_workflow()
    inputs = {item.case_id: item for item in (*EXTERNAL_INPUTS, *DEPTH_EXTERNAL_INPUTS)}
    mismatches = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (case_id, (plan_name, change)) in enumerate(REAL_CASES.items()):
            pump = Path(tmp) / f"case_{index}" / "pump_loop"
            shutil.copytree(PUMP, pump)
            plan = _edit_plan(pump, plan_name, change)
            try:
                real_status = validate_model_dataset(plan).status
            except ValueError:
                real_status = "fail"
            run = workflow.execute(initial_state(), inputs[case_id], terminal_predicate=terminal_predicate)
            expected = EXPECTED_STATUS[type(run.completed_paths[0].current_input).__name__]
            if real_status != expected:
                mismatches.append(f"{case_id}: real status {real_status!r}, model expects {expected!r}")
    return ReplayReport(len(REAL_CASES), mismatches)


if __name__ == "__main__":
    print(build_explorer().explore().format_text())
    for name, variant in broken_variants().items():
        print(f"known-bad {name}: {'caught' if not variant.explore().ok else 'MISSED'}")
    print(conformance().format_text())
