"""FlowGuard model for PhysicsGuard database catalog workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


DatabaseClaim = Literal["none", "query", "comparison", "reuse"]


@dataclass(frozen=True)
class DatabaseCatalogInput:
    case_id: str
    catalog_found: bool
    project_references_registered: bool
    raw_data_embedded: bool
    project_registries_loaded: bool
    cross_project_indexes_built: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    database_map_generated: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class CatalogFound:
    case_id: str
    project_references_registered: bool
    raw_data_embedded: bool
    project_registries_loaded: bool
    cross_project_indexes_built: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    database_map_generated: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class ProjectReferencesReady:
    case_id: str
    project_registries_loaded: bool
    cross_project_indexes_built: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    database_map_generated: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class ProjectRegistriesLoaded:
    case_id: str
    cross_project_indexes_built: bool
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    database_map_generated: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class CrossProjectIndexesReady:
    case_id: str
    gap_check_ran: bool
    blocking_gaps: bool
    review_gaps: bool
    database_map_generated: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class CatalogGapChecked:
    case_id: str
    review_gaps: bool
    database_map_generated: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class DatabaseMapReady:
    case_id: str
    review_gaps: bool
    comparison_scope_known: bool
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class DatabaseHandoffReady:
    case_id: str
    downstream_claim: DatabaseClaim


@dataclass(frozen=True)
class DatabaseCatalogPartial:
    case_id: str
    reason: str


@dataclass(frozen=True)
class DatabaseCatalogBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    catalog_found: tuple[str, ...] = ()
    project_references_registered: tuple[str, ...] = ()
    registries_loaded: tuple[str, ...] = ()
    indexes_built: tuple[str, ...] = ()
    gap_checked: tuple[str, ...] = ()
    map_generated: tuple[str, ...] = ()
    handoff_ready: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class FindCatalog:
    name = "FindCatalog"
    reads = ()
    writes = ("catalog_found", "blocked")
    accepted_input_type = DatabaseCatalogInput
    input_description = "database catalog maintenance request"
    output_description = "CatalogFound or DatabaseCatalogBlocked"
    idempotency = "Catalog discovery reads current database catalog files."

    def apply(self, input_obj: DatabaseCatalogInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.catalog_found:
            yield FunctionResult(
                output=DatabaseCatalogBlocked(input_obj.case_id, "catalog_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="catalog_missing_blocked",
            )
            return
        yield FunctionResult(
            output=CatalogFound(
                input_obj.case_id,
                input_obj.project_references_registered,
                input_obj.raw_data_embedded,
                input_obj.project_registries_loaded,
                input_obj.cross_project_indexes_built,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.database_map_generated,
                input_obj.comparison_scope_known,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, catalog_found=state.catalog_found + (input_obj.case_id,)),
            label="catalog_found",
        )


class RegisterProjectReferences:
    name = "RegisterProjectReferences"
    reads = ("catalog_found",)
    writes = ("project_references_registered", "partial", "blocked")
    accepted_input_type = CatalogFound
    input_description = "located database catalog"
    output_description = "ProjectReferencesReady or blocked/partial output"
    idempotency = "Project reference review checks catalog records only."

    def apply(self, input_obj: CatalogFound, state: State) -> Iterable[FunctionResult]:
        if input_obj.raw_data_embedded:
            yield FunctionResult(
                output=DatabaseCatalogBlocked(input_obj.case_id, "raw_data_embedded"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="raw_data_payload_blocked",
            )
            return
        if not input_obj.project_references_registered:
            yield FunctionResult(
                output=DatabaseCatalogPartial(input_obj.case_id, "project_references_missing"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="project_references_missing_partial",
            )
            return
        yield FunctionResult(
            output=ProjectReferencesReady(
                input_obj.case_id,
                input_obj.project_registries_loaded,
                input_obj.cross_project_indexes_built,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.database_map_generated,
                input_obj.comparison_scope_known,
                input_obj.downstream_claim,
            ),
            new_state=replace(
                state,
                project_references_registered=state.project_references_registered + (input_obj.case_id,),
            ),
            label="project_references_registered",
        )


class LoadProjectRegistries:
    name = "LoadProjectRegistries"
    reads = ("project_references_registered",)
    writes = ("registries_loaded", "partial")
    accepted_input_type = ProjectReferencesReady
    input_description = "project references registered in catalog"
    output_description = "ProjectRegistriesLoaded or DatabaseCatalogPartial"
    idempotency = "Registry loading reads project evidence registry paths."

    def apply(self, input_obj: ProjectReferencesReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.project_registries_loaded:
            yield FunctionResult(
                output=DatabaseCatalogPartial(input_obj.case_id, "project_registries_missing_or_unloaded"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="project_registries_unloaded_partial",
            )
            return
        yield FunctionResult(
            output=ProjectRegistriesLoaded(
                input_obj.case_id,
                input_obj.cross_project_indexes_built,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.database_map_generated,
                input_obj.comparison_scope_known,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, registries_loaded=state.registries_loaded + (input_obj.case_id,)),
            label="project_registries_loaded",
        )


class BuildCrossProjectIndexes:
    name = "BuildCrossProjectIndexes"
    reads = ("registries_loaded",)
    writes = ("indexes_built", "partial")
    accepted_input_type = ProjectRegistriesLoaded
    input_description = "loaded project evidence registries"
    output_description = "CrossProjectIndexesReady or DatabaseCatalogPartial"
    idempotency = "Index building is a deterministic projection of current project maps."

    def apply(self, input_obj: ProjectRegistriesLoaded, state: State) -> Iterable[FunctionResult]:
        if not input_obj.cross_project_indexes_built:
            yield FunctionResult(
                output=DatabaseCatalogPartial(input_obj.case_id, "cross_project_indexes_missing"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="indexes_missing_partial",
            )
            return
        yield FunctionResult(
            output=CrossProjectIndexesReady(
                input_obj.case_id,
                input_obj.gap_check_ran,
                input_obj.blocking_gaps,
                input_obj.review_gaps,
                input_obj.database_map_generated,
                input_obj.comparison_scope_known,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, indexes_built=state.indexes_built + (input_obj.case_id,)),
            label="cross_project_indexes_built",
        )


class RunCatalogGapCheck:
    name = "RunCatalogGapCheck"
    reads = ("indexes_built",)
    writes = ("gap_checked", "blocked")
    accepted_input_type = CrossProjectIndexesReady
    input_description = "database catalog with derived indexes"
    output_description = "CatalogGapChecked or DatabaseCatalogBlocked"
    idempotency = "Catalog gap check is deterministic for current catalog and project maps."

    def apply(self, input_obj: CrossProjectIndexesReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.gap_check_ran:
            yield FunctionResult(
                output=DatabaseCatalogBlocked(input_obj.case_id, "catalog_gap_check_missing"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="catalog_gap_check_missing_blocked",
            )
            return
        if input_obj.blocking_gaps:
            yield FunctionResult(
                output=DatabaseCatalogBlocked(input_obj.case_id, "catalog_blocking_gaps"),
                new_state=replace(
                    state,
                    gap_checked=state.gap_checked + (input_obj.case_id,),
                    blocked=state.blocked + (input_obj.case_id,),
                ),
                label="catalog_blocking_gaps",
            )
            return
        yield FunctionResult(
            output=CatalogGapChecked(
                input_obj.case_id,
                input_obj.review_gaps,
                input_obj.database_map_generated,
                input_obj.comparison_scope_known,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, gap_checked=state.gap_checked + (input_obj.case_id,)),
            label="catalog_gap_check_clean" if not input_obj.review_gaps else "catalog_review_gaps_visible",
        )


class BuildDatabaseMap:
    name = "BuildDatabaseMap"
    reads = ("gap_checked",)
    writes = ("map_generated", "partial")
    accepted_input_type = CatalogGapChecked
    input_description = "gap-checked catalog"
    output_description = "DatabaseMapReady or DatabaseCatalogPartial"
    idempotency = "Database map generation projects current catalog state."

    def apply(self, input_obj: CatalogGapChecked, state: State) -> Iterable[FunctionResult]:
        if not input_obj.database_map_generated:
            yield FunctionResult(
                output=DatabaseCatalogPartial(input_obj.case_id, "database_map_missing"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="database_map_missing_partial",
            )
            return
        yield FunctionResult(
            output=DatabaseMapReady(
                input_obj.case_id,
                input_obj.review_gaps,
                input_obj.comparison_scope_known,
                input_obj.downstream_claim,
            ),
            new_state=replace(state, map_generated=state.map_generated + (input_obj.case_id,)),
            label="database_map_ready" if not input_obj.review_gaps else "database_map_ready_with_review_gaps",
        )


class GateQueryOrComparison:
    name = "GateQueryOrComparison"
    reads = ("map_generated",)
    writes = ("handoff_ready", "partial", "blocked")
    accepted_input_type = DatabaseMapReady
    input_description = "database map ready"
    output_description = "DatabaseHandoffReady, partial, or blocked output"
    idempotency = "Query/comparison gate checks current map and claim scope."

    def apply(self, input_obj: DatabaseMapReady, state: State) -> Iterable[FunctionResult]:
        if input_obj.downstream_claim == "comparison" and not input_obj.comparison_scope_known:
            yield FunctionResult(
                output=DatabaseCatalogBlocked(input_obj.case_id, "comparison_scope_unknown"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="comparison_scope_unknown_blocked",
            )
            return
        if input_obj.review_gaps and input_obj.downstream_claim in {"query", "comparison", "reuse"}:
            yield FunctionResult(
                output=DatabaseCatalogPartial(input_obj.case_id, "handoff_with_review_gaps"),
                new_state=replace(state, partial=state.partial + (input_obj.case_id,)),
                label="handoff_review_gaps_partial",
            )
            return
        label = {
            "none": "database_map_navigation_ready",
            "query": "database_query_ready",
            "comparison": "database_comparison_ready",
            "reuse": "database_reuse_search_ready",
        }[input_obj.downstream_claim]
        yield FunctionResult(
            output=DatabaseHandoffReady(input_obj.case_id, input_obj.downstream_claim),
            new_state=replace(state, handoff_ready=state.handoff_ready + (input_obj.case_id,)),
            label=label,
        )


def no_handoff_without_catalog_and_projects(state: State, trace) -> InvariantResult:
    del trace
    ready = set(state.catalog_found) & set(state.project_references_registered)
    missing = set(state.handoff_ready) - ready
    if missing:
        return InvariantResult.fail(f"database handoff without catalog/projects: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_handoff_without_registry_index_gap_and_map(state: State, trace) -> InvariantResult:
    del trace
    ready = set(state.registries_loaded) & set(state.indexes_built) & set(state.gap_checked) & set(state.map_generated)
    missing = set(state.handoff_ready) - ready
    if missing:
        return InvariantResult.fail(f"database handoff without registry/index/gap/map: {sorted(missing)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("no_handoff_without_catalog_and_projects", "Database handoff requires catalog and project references.", no_handoff_without_catalog_and_projects),
    Invariant("no_handoff_without_registry_index_gap_and_map", "Database handoff requires registry loading, index building, gap-check, and map.", no_handoff_without_registry_index_gap_and_map),
)

MAX_SEQUENCE_LENGTH = 7


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (DatabaseHandoffReady, DatabaseCatalogPartial, DatabaseCatalogBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            FindCatalog(),
            RegisterProjectReferences(),
            LoadProjectRegistries(),
            BuildCrossProjectIndexes(),
            RunCatalogGapCheck(),
            BuildDatabaseMap(),
            GateQueryOrComparison(),
        ),
        name="physicsguard_database_catalog",
    )
