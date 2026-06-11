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
            ),
            new_state=replace(state, contracts_ready=state.contracts_ready + (input_obj.case_id,)),
            label="contracts_passed",
        )


class RunDirectValidation:
    name = "RunDirectValidation"
    reads = ("contracts_ready",)
    writes = ("direct_validation_ran", "blocked")
    accepted_input_type = ContractsReady
    input_description = "ContractsReady"
    output_description = "DirectValidationReady or ValidationBlocked"
    idempotency = "Direct validation reads model and observed values only."

    def apply(self, input_obj: ContractsReady, state: State) -> Iterable[FunctionResult]:
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
                output=CalibrationReady(input_obj.case_id, True, input_obj.confidence_feedback_recorded),
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
    writes = ("holdout_passed", "confidence_feedback_recorded", "validation_passed", "partial")
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
MAX_SEQUENCE_LENGTH = 4


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (ValidationPassed, ValidationPartial, ValidationBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            CheckContracts(),
            RunDirectValidation(),
            OptionalCalibration(),
            GateValidationClaim(),
        ),
        name="physicsguard_model_dataset_validation",
    )
