"""FlowGuard model for PhysicsGuard evidence mesh claim gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class EvidenceMeshInput:
    case_id: str
    parent_current: bool
    child_current: bool
    child_consumed_by_parent: bool
    obligations_have_contracts: bool
    tests_current_and_bound: bool
    contract_cases_generated: bool
    contract_cases_have_oracles: bool
    contract_cases_consumed_downstream: bool
    parent_suite_current: bool
    child_suites_current: bool
    parent_consumes_child_suites: bool
    fields_projected: bool
    old_fields_closed: bool
    risk_ledger_current: bool
    risk_consumes_all_routes: bool


@dataclass(frozen=True)
class ModelMeshReady:
    source: EvidenceMeshInput


@dataclass(frozen=True)
class AlignmentReady:
    source: EvidenceMeshInput


@dataclass(frozen=True)
class ContractExhaustionReady:
    source: EvidenceMeshInput


@dataclass(frozen=True)
class TestMeshReady:
    source: EvidenceMeshInput


@dataclass(frozen=True)
class FieldLifecycleReady:
    source: EvidenceMeshInput


@dataclass(frozen=True)
class EvidenceMeshPassed:
    case_id: str


@dataclass(frozen=True)
class EvidenceMeshBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    model_mesh_checked: tuple[str, ...] = ()
    alignment_checked: tuple[str, ...] = ()
    contract_exhaustion_checked: tuple[str, ...] = ()
    test_mesh_checked: tuple[str, ...] = ()
    field_lifecycle_checked: tuple[str, ...] = ()
    risk_ledger_checked: tuple[str, ...] = ()
    mesh_passed: tuple[str, ...] = ()
    mesh_blocked: tuple[str, ...] = ()


class ReviewModelMesh:
    name = "ReviewModelMesh"
    reads = ()
    writes = ("model_mesh_checked", "mesh_blocked")
    accepted_input_type = EvidenceMeshInput
    input_description = "evidence mesh artifact"
    output_description = "ModelMeshReady or EvidenceMeshBlocked"
    idempotency = "Model mesh review reads current parent and child receipts."

    def apply(self, input_obj: EvidenceMeshInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.parent_current:
            yield FunctionResult(
                output=EvidenceMeshBlocked(input_obj.case_id, "parent_model_mesh_not_current"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (input_obj.case_id,)),
                label="parent_mesh_blocks",
            )
            return
        if not input_obj.child_current:
            yield FunctionResult(
                output=EvidenceMeshBlocked(input_obj.case_id, "child_evidence_not_current"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (input_obj.case_id,)),
                label="stale_child_blocks",
            )
            return
        if not input_obj.child_consumed_by_parent:
            yield FunctionResult(
                output=EvidenceMeshBlocked(input_obj.case_id, "child_evidence_not_consumed_by_parent"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (input_obj.case_id,)),
                label="child_local_only_blocks",
            )
            return
        yield FunctionResult(
            output=ModelMeshReady(input_obj),
            new_state=replace(state, model_mesh_checked=state.model_mesh_checked + (input_obj.case_id,)),
            label="model_mesh_ready",
        )


class ReviewModelTestAlignment:
    name = "ReviewModelTestAlignment"
    reads = ("model_mesh_checked",)
    writes = ("alignment_checked", "mesh_blocked")
    accepted_input_type = ModelMeshReady
    input_description = "model-mesh-ready evidence"
    output_description = "AlignmentReady or EvidenceMeshBlocked"
    idempotency = "Alignment review reads obligation, code-contract, and test receipts."

    def apply(self, input_obj: ModelMeshReady, state: State) -> Iterable[FunctionResult]:
        source = input_obj.source
        if not source.obligations_have_contracts:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "required_obligation_missing_code_contract"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="mta_missing_contract_blocks",
            )
            return
        if not source.tests_current_and_bound:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "required_obligation_missing_external_test"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="mta_missing_test_blocks",
            )
            return
        yield FunctionResult(
            output=AlignmentReady(source),
            new_state=replace(state, alignment_checked=state.alignment_checked + (source.case_id,)),
            label="model_test_alignment_ready",
        )


class ReviewContractExhaustion:
    name = "ReviewContractExhaustion"
    reads = ("alignment_checked",)
    writes = ("contract_exhaustion_checked", "mesh_blocked")
    accepted_input_type = AlignmentReady
    input_description = "alignment-ready evidence"
    output_description = "ContractExhaustionReady or EvidenceMeshBlocked"
    idempotency = "Contract exhaustion review reads generated case, oracle, and downstream receipts."

    def apply(self, input_obj: AlignmentReady, state: State) -> Iterable[FunctionResult]:
        source = input_obj.source
        if not source.contract_cases_generated:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "contract_case_not_generated"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="handwritten_case_blocks",
            )
            return
        if not source.contract_cases_have_oracles:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "contract_case_missing_oracle"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="missing_oracle_blocks",
            )
            return
        if not source.contract_cases_consumed_downstream:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "contract_case_not_consumed_downstream"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="case_not_consumed_blocks",
            )
            return
        yield FunctionResult(
            output=ContractExhaustionReady(source),
            new_state=replace(state, contract_exhaustion_checked=state.contract_exhaustion_checked + (source.case_id,)),
            label="contract_exhaustion_ready",
        )


class ReviewTestMesh:
    name = "ReviewTestMesh"
    reads = ("contract_exhaustion_checked",)
    writes = ("test_mesh_checked", "mesh_blocked")
    accepted_input_type = ContractExhaustionReady
    input_description = "contract-exhaustion-ready evidence"
    output_description = "TestMeshReady or EvidenceMeshBlocked"
    idempotency = "Test mesh review reads parent and child suite evidence."

    def apply(self, input_obj: ContractExhaustionReady, state: State) -> Iterable[FunctionResult]:
        source = input_obj.source
        if not source.parent_suite_current:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "parent_test_suite_not_current"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="parent_suite_blocks",
            )
            return
        if not source.child_suites_current:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "child_test_suite_not_current"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="progress_only_child_suite_blocks",
            )
            return
        if not source.parent_consumes_child_suites:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "child_test_suite_not_consumed"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="child_suite_local_only_blocks",
            )
            return
        yield FunctionResult(
            output=TestMeshReady(source),
            new_state=replace(state, test_mesh_checked=state.test_mesh_checked + (source.case_id,)),
            label="test_mesh_ready",
        )


class ReviewFieldLifecycle:
    name = "ReviewFieldLifecycle"
    reads = ("test_mesh_checked",)
    writes = ("field_lifecycle_checked", "mesh_blocked")
    accepted_input_type = TestMeshReady
    input_description = "test-mesh-ready evidence"
    output_description = "FieldLifecycleReady or EvidenceMeshBlocked"
    idempotency = "Field lifecycle review reads behavior-bearing projections and old-field dispositions."

    def apply(self, input_obj: TestMeshReady, state: State) -> Iterable[FunctionResult]:
        source = input_obj.source
        if not source.fields_projected:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "behavior_field_missing_projection"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="field_projection_blocks",
            )
            return
        if not source.old_fields_closed:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "old_field_missing_disposition"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="old_field_disposition_blocks",
            )
            return
        yield FunctionResult(
            output=FieldLifecycleReady(source),
            new_state=replace(state, field_lifecycle_checked=state.field_lifecycle_checked + (source.case_id,)),
            label="field_lifecycle_ready",
        )


class GateRiskLedger:
    name = "GateRiskLedger"
    reads = ("field_lifecycle_checked",)
    writes = ("risk_ledger_checked", "mesh_passed", "mesh_blocked")
    accepted_input_type = FieldLifecycleReady
    input_description = "field-lifecycle-ready evidence"
    output_description = "EvidenceMeshPassed or EvidenceMeshBlocked"
    idempotency = "Risk ledger review reads final claim row and consumed route receipts."

    def apply(self, input_obj: FieldLifecycleReady, state: State) -> Iterable[FunctionResult]:
        source = input_obj.source
        if not source.risk_ledger_current:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "risk_ledger_not_pass"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="risk_ledger_status_blocks",
            )
            return
        if not source.risk_consumes_all_routes:
            yield FunctionResult(
                output=EvidenceMeshBlocked(source.case_id, "risk_ledger_missing_required_routes"),
                new_state=replace(state, mesh_blocked=state.mesh_blocked + (source.case_id,)),
                label="risk_ledger_missing_route_blocks",
            )
            return
        yield FunctionResult(
            output=EvidenceMeshPassed(source.case_id),
            new_state=replace(
                state,
                risk_ledger_checked=state.risk_ledger_checked + (source.case_id,),
                mesh_passed=state.mesh_passed + (source.case_id,),
            ),
            label="evidence_mesh_passed",
        )


def no_pass_without_model_mesh(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.mesh_passed) - set(state.model_mesh_checked)
    if missing:
        return InvariantResult.fail(f"evidence mesh passed without model mesh: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_alignment(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.mesh_passed) - set(state.alignment_checked)
    if missing:
        return InvariantResult.fail(f"evidence mesh passed without alignment: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_contract_exhaustion(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.mesh_passed) - set(state.contract_exhaustion_checked)
    if missing:
        return InvariantResult.fail(f"evidence mesh passed without contract exhaustion: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_test_mesh(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.mesh_passed) - set(state.test_mesh_checked)
    if missing:
        return InvariantResult.fail(f"evidence mesh passed without test mesh: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_field_lifecycle(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.mesh_passed) - set(state.field_lifecycle_checked)
    if missing:
        return InvariantResult.fail(f"evidence mesh passed without field lifecycle: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_pass_without_risk_ledger(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.mesh_passed) - set(state.risk_ledger_checked)
    if missing:
        return InvariantResult.fail(f"evidence mesh passed without risk ledger: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_case_both_passed_and_blocked(state: State, trace) -> InvariantResult:
    del trace
    overlap = set(state.mesh_passed) & set(state.mesh_blocked)
    if overlap:
        return InvariantResult.fail(f"evidence mesh both passed and blocked: {sorted(overlap)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("no_pass_without_model_mesh", "Evidence mesh pass requires parent/child model mesh.", no_pass_without_model_mesh),
    Invariant("no_pass_without_alignment", "Evidence mesh pass requires model-code-test alignment.", no_pass_without_alignment),
    Invariant("no_pass_without_contract_exhaustion", "Evidence mesh pass requires generated case coverage.", no_pass_without_contract_exhaustion),
    Invariant("no_pass_without_test_mesh", "Evidence mesh pass requires fresh parent/child test mesh.", no_pass_without_test_mesh),
    Invariant("no_pass_without_field_lifecycle", "Evidence mesh pass requires field lifecycle closure.", no_pass_without_field_lifecycle),
    Invariant("no_pass_without_risk_ledger", "Evidence mesh pass requires final risk ledger consumption.", no_pass_without_risk_ledger),
    Invariant("no_case_both_passed_and_blocked", "Evidence mesh cannot both pass and block.", no_case_both_passed_and_blocked),
)

MAX_SEQUENCE_LENGTH = 6


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (EvidenceMeshPassed, EvidenceMeshBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            ReviewModelMesh(),
            ReviewModelTestAlignment(),
            ReviewContractExhaustion(),
            ReviewTestMesh(),
            ReviewFieldLifecycle(),
            GateRiskLedger(),
        ),
        name="physicsguard_evidence_mesh",
    )
