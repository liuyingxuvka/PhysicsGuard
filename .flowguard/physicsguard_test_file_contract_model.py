"""FlowGuard model for the PhysicsGuard test-file contract route.

Risk intent:
- The route is optional for model-only PhysicsGuard work.
- When test data is in scope, no broad AI analysis claim is allowed until the
  concrete file has a generated manifest, a fresh extractor, a testbench
  profile, a model binding, a complete parameter catalog, a role matrix, mapping
  edges with evidence, known model targets, and a passing contract check.
- AI-suggested mappings without evidence must stay review_required or blocked;
  they must not silently become covered.
- If a test file exposes fields that the current model does not cover, the
  route must request model extension or human evidence instead of inventing a
  binding.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class ContractInput:
    case_id: str
    has_test_data: bool
    source_file_available: bool
    manifest_generated: bool
    manifest_fresh: bool
    extractor_identity_recorded: bool
    testbench_profile_available: bool
    model_binding_available: bool
    catalog_complete: bool
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class RouteSelected:
    case_id: str
    source_file_available: bool
    manifest_generated: bool
    manifest_fresh: bool
    extractor_identity_recorded: bool
    testbench_profile_available: bool
    model_binding_available: bool
    catalog_complete: bool
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class ManifestReady:
    case_id: str
    manifest_fresh: bool
    extractor_identity_recorded: bool
    testbench_profile_available: bool
    model_binding_available: bool
    catalog_complete: bool
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class FreshManifestReady:
    case_id: str
    testbench_profile_available: bool
    model_binding_available: bool
    catalog_complete: bool
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class ProfileReady:
    case_id: str
    model_binding_available: bool
    catalog_complete: bool
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class BindingReady:
    case_id: str
    catalog_complete: bool
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class CatalogReady:
    case_id: str
    roles_complete: bool
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class RoleMatrixReady:
    case_id: str
    mappings_complete: bool
    mapping_evidence_complete: bool
    all_model_targets_known: bool
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class MappingReady:
    case_id: str
    review_required: bool
    planned_model_gap: bool
    contract_check_passed: bool


@dataclass(frozen=True)
class CoverageReady:
    case_id: str
    broad_claim_allowed: bool


@dataclass(frozen=True)
class AnalysisClaimAllowed:
    case_id: str


@dataclass(frozen=True)
class ModelOnlyRoute:
    case_id: str


@dataclass(frozen=True)
class WorkflowBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    model_only_routes: tuple[str, ...] = ()
    testfile_routes: tuple[str, ...] = ()
    manifests_generated: tuple[str, ...] = ()
    manifests_fresh: tuple[str, ...] = ()
    profiles_resolved: tuple[str, ...] = ()
    model_bindings_resolved: tuple[str, ...] = ()
    catalogs_complete: tuple[str, ...] = ()
    role_matrices_complete: tuple[str, ...] = ()
    mapping_edges_resolved: tuple[str, ...] = ()
    mapping_evidence_recorded: tuple[str, ...] = ()
    model_targets_known: tuple[str, ...] = ()
    coverage_contracts_passed: tuple[str, ...] = ()
    broad_claims_allowed: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class SelectTestFileRoute:
    name = "SelectTestFileRoute"
    reads = ()
    writes = ("model_only_routes", "testfile_routes")
    accepted_input_type = ContractInput
    input_description = "PhysicsGuard user request"
    output_description = "RouteSelected or AnalysisClaimAllowed"
    idempotency = "Route selection is deterministic for a request scope."

    def apply(self, input_obj: ContractInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.has_test_data:
            yield FunctionResult(
                output=AnalysisClaimAllowed(input_obj.case_id),
                new_state=replace(
                    state,
                    model_only_routes=state.model_only_routes + (input_obj.case_id,),
                    broad_claims_allowed=state.broad_claims_allowed + (input_obj.case_id,),
                ),
                label="no_test_data_optional_route",
            )
            return
        yield FunctionResult(
            output=RouteSelected(
                input_obj.case_id,
                input_obj.source_file_available,
                input_obj.manifest_generated,
                input_obj.manifest_fresh,
                input_obj.extractor_identity_recorded,
                input_obj.testbench_profile_available,
                input_obj.model_binding_available,
                input_obj.catalog_complete,
                input_obj.roles_complete,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, testfile_routes=state.testfile_routes + (input_obj.case_id,)),
            label="test_data_route_selected",
        )


class GenerateDataFileManifest:
    name = "GenerateDataFileManifest"
    reads = ("testfile_routes",)
    writes = ("manifests_generated", "blocked")
    accepted_input_type = RouteSelected
    input_description = "RouteSelected"
    output_description = "ManifestReady or WorkflowBlocked"
    idempotency = "Manifest generation can be rerun from the same source file and extractor profile."

    def apply(self, input_obj: RouteSelected, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.testfile_routes:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "testfile_route_not_selected"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="manifest_missing_route",
            )
            return
        if not input_obj.source_file_available:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "source_file_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="source_file_missing",
            )
            return
        if not input_obj.manifest_generated:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "manifest_not_generated"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="manifest_not_generated",
            )
            return
        yield FunctionResult(
            output=ManifestReady(
                input_obj.case_id,
                input_obj.manifest_fresh,
                input_obj.extractor_identity_recorded,
                input_obj.testbench_profile_available,
                input_obj.model_binding_available,
                input_obj.catalog_complete,
                input_obj.roles_complete,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, manifests_generated=state.manifests_generated + (input_obj.case_id,)),
            label="manifest_generated",
        )


class VerifyManifestFreshness:
    name = "VerifyManifestFreshness"
    reads = ("manifests_generated",)
    writes = ("manifests_fresh", "blocked")
    accepted_input_type = ManifestReady
    input_description = "ManifestReady"
    output_description = "FreshManifestReady or WorkflowBlocked"
    idempotency = "Freshness verification compares file/script hashes without side effects."

    def apply(self, input_obj: ManifestReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.case_id not in state.manifests_generated:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "manifest_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="freshness_missing_manifest",
            )
            return
        if not input_obj.extractor_identity_recorded:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "manifest_missing_extractor_identity"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="manifest_missing_extractor",
            )
            return
        if not input_obj.manifest_fresh:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "manifest_or_extractor_stale"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="manifest_stale",
            )
            return
        yield FunctionResult(
            output=FreshManifestReady(
                input_obj.case_id,
                input_obj.testbench_profile_available,
                input_obj.model_binding_available,
                input_obj.catalog_complete,
                input_obj.roles_complete,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, manifests_fresh=state.manifests_fresh + (input_obj.case_id,)),
            label="manifest_fresh",
        )


class ResolveTestbenchProfile:
    name = "ResolveTestbenchProfile"
    reads = ("manifests_fresh",)
    writes = ("profiles_resolved", "blocked")
    accepted_input_type = FreshManifestReady
    input_description = "FreshManifestReady"
    output_description = "ProfileReady or WorkflowBlocked"
    idempotency = "Profile resolution reads declared profile artifacts only."

    def apply(self, input_obj: FreshManifestReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.testbench_profile_available:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "testbench_profile_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="testbench_profile_missing",
            )
            return
        yield FunctionResult(
            output=ProfileReady(
                input_obj.case_id,
                input_obj.model_binding_available,
                input_obj.catalog_complete,
                input_obj.roles_complete,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, profiles_resolved=state.profiles_resolved + (input_obj.case_id,)),
            label="testbench_profile_resolved",
        )


class ResolveModelBinding:
    name = "ResolveModelBinding"
    reads = ("profiles_resolved",)
    writes = ("model_bindings_resolved", "blocked")
    accepted_input_type = ProfileReady
    input_description = "ProfileReady"
    output_description = "BindingReady or WorkflowBlocked"
    idempotency = "Model binding resolution reads declared hierarchy/model artifacts only."

    def apply(self, input_obj: ProfileReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.model_binding_available:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "model_binding_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="model_binding_missing",
            )
            return
        yield FunctionResult(
            output=BindingReady(
                input_obj.case_id,
                input_obj.catalog_complete,
                input_obj.roles_complete,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, model_bindings_resolved=state.model_bindings_resolved + (input_obj.case_id,)),
            label="model_binding_resolved",
        )


class BuildParameterCatalog:
    name = "BuildParameterCatalog"
    reads = ("model_bindings_resolved",)
    writes = ("catalogs_complete", "blocked")
    accepted_input_type = BindingReady
    input_description = "BindingReady"
    output_description = "CatalogReady or WorkflowBlocked"
    idempotency = "Catalog check is deterministic against manifest fields."

    def apply(self, input_obj: BindingReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.catalog_complete:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "manifest_fields_missing_from_catalog"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="catalog_missing_fields",
            )
            return
        yield FunctionResult(
            output=CatalogReady(
                input_obj.case_id,
                input_obj.roles_complete,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, catalogs_complete=state.catalogs_complete + (input_obj.case_id,)),
            label="catalog_complete",
        )


class ApplyRoleMatrix:
    name = "ApplyRoleMatrix"
    reads = ("catalogs_complete",)
    writes = ("role_matrices_complete", "blocked")
    accepted_input_type = CatalogReady
    input_description = "CatalogReady"
    output_description = "RoleMatrixReady or WorkflowBlocked"
    idempotency = "Role matrix check does not mutate observed values."

    def apply(self, input_obj: CatalogReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.roles_complete:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "role_or_disposition_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="role_matrix_missing_roles",
            )
            return
        yield FunctionResult(
            output=RoleMatrixReady(
                input_obj.case_id,
                input_obj.mappings_complete,
                input_obj.mapping_evidence_complete,
                input_obj.all_model_targets_known,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(state, role_matrices_complete=state.role_matrices_complete + (input_obj.case_id,)),
            label="role_matrix_complete",
        )


class ResolveMappingEdges:
    name = "ResolveMappingEdges"
    reads = ("role_matrices_complete",)
    writes = ("mapping_edges_resolved", "mapping_evidence_recorded", "model_targets_known", "blocked")
    accepted_input_type = RoleMatrixReady
    input_description = "RoleMatrixReady"
    output_description = "MappingReady or WorkflowBlocked"
    idempotency = "Mapping review records evidence; it cannot invent target semantics."

    def apply(self, input_obj: RoleMatrixReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.mappings_complete:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "mapping_edges_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="mapping_edges_missing",
            )
            return
        if not input_obj.mapping_evidence_complete:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "mapping_evidence_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="mapping_missing_evidence",
            )
            return
        if not input_obj.all_model_targets_known:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "model_target_unknown_or_model_gap"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="mapping_unknown_targets_model_gap",
            )
            return
        yield FunctionResult(
            output=MappingReady(
                input_obj.case_id,
                input_obj.review_required,
                input_obj.planned_model_gap,
                input_obj.contract_check_passed,
            ),
            new_state=replace(
                state,
                mapping_edges_resolved=state.mapping_edges_resolved + (input_obj.case_id,),
                mapping_evidence_recorded=state.mapping_evidence_recorded + (input_obj.case_id,),
                model_targets_known=state.model_targets_known + (input_obj.case_id,),
            ),
            label="mapping_edges_evidenced",
        )


class EnforceCoverageContract:
    name = "EnforceCoverageContract"
    reads = ("mapping_edges_resolved", "mapping_evidence_recorded", "model_targets_known")
    writes = ("coverage_contracts_passed", "blocked")
    accepted_input_type = MappingReady
    input_description = "MappingReady"
    output_description = "CoverageReady or WorkflowBlocked"
    idempotency = "Coverage check is deterministic and fail-closed."

    def apply(self, input_obj: MappingReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.review_required:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "mapping_review_required"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="review_required_partial",
            )
            return
        if input_obj.planned_model_gap:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "planned_child_model_or_model_extension_required"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="planned_child_model_partial",
            )
            return
        if not input_obj.contract_check_passed:
            yield FunctionResult(
                output=WorkflowBlocked(input_obj.case_id, "contract_check_failed"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="contract_check_failed",
            )
            return
        yield FunctionResult(
            output=CoverageReady(input_obj.case_id, True),
            new_state=replace(state, coverage_contracts_passed=state.coverage_contracts_passed + (input_obj.case_id,)),
            label="coverage_contract_passed",
        )


class GateAnalysisClaim:
    name = "GateAnalysisClaim"
    reads = ("coverage_contracts_passed",)
    writes = ("broad_claims_allowed", "blocked")
    accepted_input_type = object
    input_description = "CoverageReady, ModelOnlyRoute, or WorkflowBlocked"
    output_description = "AnalysisClaimAllowed or WorkflowBlocked"
    idempotency = "Claim gate only projects current evidence into a safe claim boundary."

    def apply(self, input_obj, state: State) -> Iterable[FunctionResult]:
        if isinstance(input_obj, ModelOnlyRoute):
            yield FunctionResult(
                output=AnalysisClaimAllowed(input_obj.case_id),
                new_state=replace(state, broad_claims_allowed=state.broad_claims_allowed + (input_obj.case_id,)),
                label="model_only_claim_allowed",
            )
            return
        if isinstance(input_obj, WorkflowBlocked):
            yield FunctionResult(
                output=input_obj,
                new_state=state,
                label="broad_claim_blocked",
            )
            return
        if isinstance(input_obj, CoverageReady) and input_obj.broad_claim_allowed:
            yield FunctionResult(
                output=AnalysisClaimAllowed(input_obj.case_id),
                new_state=replace(state, broad_claims_allowed=state.broad_claims_allowed + (input_obj.case_id,)),
                label="broad_claim_allowed",
            )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (AnalysisClaimAllowed, WorkflowBlocked))


def no_testfile_claim_without_manifest(state: State, trace) -> InvariantResult:
    del trace
    testfile_claims = set(state.broad_claims_allowed) & set(state.testfile_routes)
    missing = tuple(sorted(testfile_claims - set(state.manifests_fresh)))
    if missing:
        return InvariantResult.fail(f"test-file claim without fresh manifest: {missing!r}")
    return InvariantResult.pass_()


def no_testfile_claim_without_catalog_roles_and_mappings(state: State, trace) -> InvariantResult:
    del trace
    testfile_claims = set(state.broad_claims_allowed) & set(state.testfile_routes)
    ready = set(state.catalogs_complete) & set(state.role_matrices_complete) & set(state.mapping_edges_resolved)
    missing = tuple(sorted(testfile_claims - ready))
    if missing:
        return InvariantResult.fail(f"test-file claim without catalog/role/mapping coverage: {missing!r}")
    return InvariantResult.pass_()


def no_testfile_claim_without_mapping_evidence_or_known_targets(state: State, trace) -> InvariantResult:
    del trace
    testfile_claims = set(state.broad_claims_allowed) & set(state.testfile_routes)
    ready = set(state.mapping_evidence_recorded) & set(state.model_targets_known)
    missing = tuple(sorted(testfile_claims - ready))
    if missing:
        return InvariantResult.fail(f"test-file claim without mapping evidence or known model targets: {missing!r}")
    return InvariantResult.pass_()


def no_testfile_claim_without_contract_pass(state: State, trace) -> InvariantResult:
    del trace
    testfile_claims = set(state.broad_claims_allowed) & set(state.testfile_routes)
    missing = tuple(sorted(testfile_claims - set(state.coverage_contracts_passed)))
    if missing:
        return InvariantResult.fail(f"test-file claim without passing coverage contract: {missing!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="no_testfile_claim_without_manifest",
        description="Test-data broad claims require a fresh generated manifest.",
        predicate=no_testfile_claim_without_manifest,
    ),
    Invariant(
        name="no_testfile_claim_without_catalog_roles_and_mappings",
        description="Every manifest field must be cataloged, classified, and mapped or explicitly disposed.",
        predicate=no_testfile_claim_without_catalog_roles_and_mappings,
    ),
    Invariant(
        name="no_testfile_claim_without_mapping_evidence_or_known_targets",
        description="AI mappings require evidence and known model targets; unknowns must not become covered.",
        predicate=no_testfile_claim_without_mapping_evidence_or_known_targets,
    ),
    Invariant(
        name="no_testfile_claim_without_contract_pass",
        description="Broad AI analysis claims require a passing contract check.",
        predicate=no_testfile_claim_without_contract_pass,
    ),
)


EXTERNAL_INPUTS = (
    ContractInput("model_only", False, False, False, False, False, False, False, False, False, False, False, False, False, False, False),
    ContractInput("clean_testfile", True, True, True, True, True, True, True, True, True, True, True, True, False, False, True),
    ContractInput("source_missing", True, False, True, True, True, True, True, True, True, True, True, True, False, False, True),
    ContractInput("manifest_missing", True, True, False, True, True, True, True, True, True, True, True, True, False, False, True),
    ContractInput("extractor_missing", True, True, True, True, False, True, True, True, True, True, True, True, False, False, True),
    ContractInput("manifest_stale", True, True, True, False, True, True, True, True, True, True, True, True, False, False, True),
    ContractInput("profile_missing", True, True, True, True, True, False, True, True, True, True, True, True, False, False, True),
    ContractInput("binding_missing", True, True, True, True, True, True, False, True, True, True, True, True, False, False, True),
    ContractInput("catalog_gap", True, True, True, True, True, True, True, False, True, True, True, True, False, False, True),
    ContractInput("role_gap", True, True, True, True, True, True, True, True, False, True, True, True, False, False, True),
    ContractInput("mapping_gap", True, True, True, True, True, True, True, True, True, False, True, True, False, False, True),
    ContractInput("mapping_no_evidence", True, True, True, True, True, True, True, True, True, True, False, True, False, False, True),
    ContractInput("unknown_model_target", True, True, True, True, True, True, True, True, True, True, True, False, False, False, True),
    ContractInput("review_required", True, True, True, True, True, True, True, True, True, True, True, True, True, False, False),
    ContractInput("planned_model_gap", True, True, True, True, True, True, True, True, True, True, True, True, False, True, False),
    ContractInput("contract_failed", True, True, True, True, True, True, True, True, True, True, True, True, False, False, False),
)

MAX_SEQUENCE_LENGTH = 1


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow(
        (
            SelectTestFileRoute(),
            GenerateDataFileManifest(),
            VerifyManifestFreshness(),
            ResolveTestbenchProfile(),
            ResolveModelBinding(),
            BuildParameterCatalog(),
            ApplyRoleMatrix(),
            ResolveMappingEdges(),
            EnforceCoverageContract(),
            GateAnalysisClaim(),
        ),
        name="physicsguard_test_file_contract_route",
    )


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "ContractInput",
    "State",
    "build_workflow",
    "initial_state",
    "terminal_predicate",
]
