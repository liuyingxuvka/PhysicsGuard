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


# Contract: what this model is about in the real code, its known-bad variants, and the replay on that code.

from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402

import yaml  # noqa: E402
from flowguard.explorer import Explorer  # noqa: E402

MODEL_ID = "test_file_contract"
PARENT = "system"
ROOT = Path(__file__).resolve().parents[2]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
IMPLEMENTED_BY = {
    "VerifyManifestFreshness": "src/physicsguard/core/test_file_contract.py:_manifest_findings",
    "ResolveTestbenchProfile": "src/physicsguard/core/test_file_contract.py:_testbench_profile_findings",
    "ResolveModelBinding": "src/physicsguard/core/test_file_contract.py:_model_binding_targets",
    "EnforceCoverageContract": "src/physicsguard/core/parameter_coverage.py:check_parameter_coverage",
    "GateAnalysisClaim": "src/physicsguard/core/test_file_contract.py:check_test_file_contract",
}
TESTED_BY = {
    "no_testfile_claim_without_catalog_roles_and_mappings": [
        "tests/test_test_file_contract_core.py:test_added_manifest_field_blocks_contract",
    ],
    "no_testfile_claim_without_mapping_evidence_or_known_targets": [
        "tests/test_test_file_contract_core.py:test_mapping_without_evidence_does_not_count_as_covered",
    ],
    "no_testfile_claim_without_contract_pass": [
        "tests/test_test_file_contract_core.py:test_clean_contract_passes_with_evidence_backed_mappings",
        "tests/test_test_file_contract_core.py:test_review_required_contract_is_partial_and_not_ok",
    ],
}
REQUIRED_LABELS = (
    "no_test_data_optional_route",
    "test_data_route_selected",
    "manifest_generated",
    "manifest_fresh",
    "testbench_profile_resolved",
    "model_binding_resolved",
    "catalog_complete",
    "role_matrix_complete",
    "mapping_edges_evidenced",
    "coverage_contract_passed",
    "broad_claim_allowed",
    "source_file_missing",
    "manifest_not_generated",
    "manifest_missing_extractor",
    "manifest_stale",
    "testbench_profile_missing",
    "model_binding_missing",
    "catalog_missing_fields",
    "role_matrix_missing_roles",
    "mapping_edges_missing",
    "mapping_missing_evidence",
    "mapping_unknown_targets_model_gap",
    "review_required_partial",
    "planned_child_model_partial",
    "contract_check_failed",
)


def _explorer(workflow: Workflow) -> Explorer:
    return Explorer(
        workflow=workflow,
        initial_states=(initial_state(),),
        external_inputs=EXTERNAL_INPUTS,
        invariants=INVARIANTS,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        terminal_predicate=terminal_predicate,
        required_labels=REQUIRED_LABELS,
    )


def build_explorer() -> Explorer:
    return _explorer(build_workflow())


def _gate_ignored(block_class, **passing):
    """Known bad: the gate's block is ignored; the case continues without the gate's record."""

    class GateIgnored(block_class):
        def apply(self, input_obj, state):
            for result in super().apply(input_obj, state):
                if isinstance(result.output, WorkflowBlocked):
                    forced = next(iter(super().apply(replace(input_obj, **passing), state)))
                    result = replace(result, output=forced.output, new_state=state, label=f"{result.label}_ignored")
                yield result

    return GateIgnored()


def broken_variants() -> dict[str, Explorer]:
    """Known-bad variants; each must violate an invariant of the design."""

    variants = {
        "freshness_gate_ignored": _gate_ignored(
            VerifyManifestFreshness, extractor_identity_recorded=True, manifest_fresh=True
        ),
        "mapping_gate_ignored": _gate_ignored(
            ResolveMappingEdges,
            mappings_complete=True,
            mapping_evidence_complete=True,
            all_model_targets_known=True,
        ),
        "coverage_gate_ignored": _gate_ignored(
            EnforceCoverageContract,
            review_required=False,
            planned_model_gap=False,
            contract_check_passed=True,
        ),
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


def _edit(relative: str, change):
    def apply(pump: Path) -> str:
        path = pump / relative
        data = _load(path)
        change(data)
        _write(path, data)
        return "contracts/clean_contract.yaml"

    return apply


def _append_row(pump: Path) -> str:
    data_file = pump / "data" / "clean.csv"
    data_file.write_text(data_file.read_text(encoding="utf-8") + "0.3,11.5,23.0,true\n", encoding="utf-8")
    return "contracts/clean_contract.yaml"


def _delete_source(pump: Path) -> str:
    (pump / "data" / "clean.csv").unlink()
    return "contracts/clean_contract.yaml"


def _edges(change):
    return _edit("coverage/pump_loop_mapping_edges.yaml", change)


def _drop_flow_edge(data: dict) -> None:
    data["edges"] = [item for item in data["edges"] if item["source_id"] != "field:flow_readback_kg_s"]


def _strip_evidence(data: dict) -> None:
    for edge in data["edges"]:
        edge["evidence"] = []


def _unknown_target(data: dict) -> None:
    next(item for item in data["edges"] if item["target"] == "pump_signal_map.y")["target"] = "pump_signal_map.missing"


def _review_required(data: dict) -> None:
    data["roles"][1]["coverage_status"] = "review_required"
    data["roles"][1]["reason"] = "AI inferred mapping from field name but human review is still needed."


REAL_CASES = {
    "clean_testfile": lambda pump: "contracts/clean_contract.yaml",
    "source_missing": _delete_source,
    "manifest_stale": _append_row,
    "extractor_missing": _edit("data/clean_manifest.yaml", lambda data: data.pop("extractor")),
    "profile_missing": _edit("contracts/clean_contract.yaml", lambda data: data.pop("testbench_profile")),
    "binding_missing": _edit("contracts/clean_contract.yaml", lambda data: data.pop("model_binding")),
    "catalog_gap": lambda pump: "contracts/added_field_contract.yaml",
    "role_gap": lambda pump: "contracts/unclassified_contract.yaml",
    "mapping_gap": _edges(_drop_flow_edge),
    "mapping_no_evidence": _edges(_strip_evidence),
    "unknown_model_target": _edges(_unknown_target),
    "review_required": _edit("coverage/pump_loop_role_matrix.yaml", _review_required),
    "contract_failed": lambda pump: "contracts/stale_model_contract.yaml",
}


def _model_statuses(case: ContractInput) -> set[str]:
    """Real contract statuses that agree with the model's terminal for this case."""

    run = build_workflow().execute(initial_state(), case, terminal_predicate=terminal_predicate)
    path = run.completed_paths[0]
    if isinstance(path.current_input, AnalysisClaimAllowed):
        return {"pass"}
    if path.trace.steps[-1].label.endswith("_partial"):
        return {"partial"}
    return {"partial", "fail"}


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
    """Run each mapped model case through check_test_file_contract and compare the status."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from physicsguard.core.test_file_contract import check_test_file_contract

    inputs = {item.case_id: item for item in EXTERNAL_INPUTS}
    mismatches = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (case_id, prepare) in enumerate(REAL_CASES.items()):
            pump = Path(tmp) / f"case_{index}" / "pump_loop"
            shutil.copytree(PUMP, pump)
            contract = pump / prepare(pump)
            try:
                real_status = check_test_file_contract(contract).status
            except (ValueError, FileNotFoundError):
                real_status = "fail"
            expected = _model_statuses(inputs[case_id])
            if real_status not in expected:
                mismatches.append(f"{case_id}: real status {real_status!r}, model expects {sorted(expected)}")
    return ReplayReport(len(REAL_CASES), mismatches)


if __name__ == "__main__":
    print(build_explorer().explore().format_text())
    for name, variant in broken_variants().items():
        print(f"known-bad {name}: {'caught' if not variant.explore().ok else 'MISSED'}")
    print(conformance().format_text())
