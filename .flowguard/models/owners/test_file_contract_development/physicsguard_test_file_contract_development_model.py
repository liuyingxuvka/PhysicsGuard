"""FlowGuard development-process model for the test-file contract upgrade."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class DevelopmentInput:
    case_id: str
    openspec_valid: bool
    flowguard_models_current: bool
    implementation_complete: bool
    docs_skills_examples_complete: bool
    tests_current: bool
    local_install_synced: bool
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class SpecReady:
    case_id: str
    flowguard_models_current: bool
    implementation_complete: bool
    docs_skills_examples_complete: bool
    tests_current: bool
    local_install_synced: bool
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class FlowGuardReady:
    case_id: str
    implementation_complete: bool
    docs_skills_examples_complete: bool
    tests_current: bool
    local_install_synced: bool
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class ImplementationReady:
    case_id: str
    docs_skills_examples_complete: bool
    tests_current: bool
    local_install_synced: bool
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class PackageReady:
    case_id: str
    tests_current: bool
    local_install_synced: bool
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class EvidenceReady:
    case_id: str
    local_install_synced: bool
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class InstallReady:
    case_id: str
    git_publish_ready: bool
    release_created: bool


@dataclass(frozen=True)
class GitReady:
    case_id: str
    release_created: bool


@dataclass(frozen=True)
class ReleaseDone:
    case_id: str


@dataclass(frozen=True)
class DevelopmentBlocked:
    case_id: str
    reason: str


@dataclass(frozen=True)
class State:
    openspec_validated: tuple[str, ...] = ()
    flowguard_checked: tuple[str, ...] = ()
    implementation_done: tuple[str, ...] = ()
    docs_skills_examples_done: tuple[str, ...] = ()
    tests_passed: tuple[str, ...] = ()
    local_install_synced: tuple[str, ...] = ()
    git_ready: tuple[str, ...] = ()
    releases_created: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()


class ValidateOpenSpec:
    name = "ValidateOpenSpec"
    reads = ()
    writes = ("openspec_validated", "blocked")
    accepted_input_type = DevelopmentInput
    input_description = "DevelopmentInput"
    output_description = "SpecReady or DevelopmentBlocked"
    idempotency = "OpenSpec validation is read-only."

    def apply(self, input_obj: DevelopmentInput, state: State) -> Iterable[FunctionResult]:
        if not input_obj.openspec_valid:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "openspec_not_valid"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="openspec_invalid",
            )
            return
        yield FunctionResult(
            output=SpecReady(
                input_obj.case_id,
                input_obj.flowguard_models_current,
                input_obj.implementation_complete,
                input_obj.docs_skills_examples_complete,
                input_obj.tests_current,
                input_obj.local_install_synced,
                input_obj.git_publish_ready,
                input_obj.release_created,
            ),
            new_state=replace(state, openspec_validated=state.openspec_validated + (input_obj.case_id,)),
            label="openspec_validated",
        )


class CheckFlowGuardModels:
    name = "CheckFlowGuardModels"
    reads = ("openspec_validated",)
    writes = ("flowguard_checked", "blocked")
    accepted_input_type = SpecReady
    input_description = "SpecReady"
    output_description = "FlowGuardReady or DevelopmentBlocked"
    idempotency = "FlowGuard route checks are executable and can be rerun."

    def apply(self, input_obj: SpecReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.flowguard_models_current:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "flowguard_models_or_checks_stale"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="flowguard_models_stale",
            )
            return
        yield FunctionResult(
            output=FlowGuardReady(
                input_obj.case_id,
                input_obj.implementation_complete,
                input_obj.docs_skills_examples_complete,
                input_obj.tests_current,
                input_obj.local_install_synced,
                input_obj.git_publish_ready,
                input_obj.release_created,
            ),
            new_state=replace(state, flowguard_checked=state.flowguard_checked + (input_obj.case_id,)),
            label="flowguard_models_current",
        )


class ImplementArtifacts:
    name = "ImplementArtifacts"
    reads = ("flowguard_checked",)
    writes = ("implementation_done", "docs_skills_examples_done", "blocked")
    accepted_input_type = FlowGuardReady
    input_description = "FlowGuardReady"
    output_description = "ImplementationReady or DevelopmentBlocked"
    idempotency = "Implementation writes are versioned in git and can stale later evidence."

    def apply(self, input_obj: FlowGuardReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.implementation_complete:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "code_artifacts_incomplete"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="implementation_incomplete",
            )
            return
        if not input_obj.docs_skills_examples_complete:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "docs_skills_examples_incomplete"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="docs_skills_examples_incomplete",
            )
            return
        yield FunctionResult(
            output=ImplementationReady(
                input_obj.case_id,
                input_obj.docs_skills_examples_complete,
                input_obj.tests_current,
                input_obj.local_install_synced,
                input_obj.git_publish_ready,
                input_obj.release_created,
            ),
            new_state=replace(
                state,
                implementation_done=state.implementation_done + (input_obj.case_id,),
                docs_skills_examples_done=state.docs_skills_examples_done + (input_obj.case_id,),
            ),
            label="implementation_and_artifacts_complete",
        )


class RunValidation:
    name = "RunValidation"
    reads = ("implementation_done", "docs_skills_examples_done")
    writes = ("tests_passed", "blocked")
    accepted_input_type = ImplementationReady
    input_description = "ImplementationReady"
    output_description = "EvidenceReady or DevelopmentBlocked"
    idempotency = "Validation evidence is current only until later writes affect covered artifacts."

    def apply(self, input_obj: ImplementationReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.tests_current:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "validation_not_current_or_failed"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="validation_failed_or_stale",
            )
            return
        yield FunctionResult(
            output=EvidenceReady(
                input_obj.case_id,
                input_obj.local_install_synced,
                input_obj.git_publish_ready,
                input_obj.release_created,
            ),
            new_state=replace(state, tests_passed=state.tests_passed + (input_obj.case_id,)),
            label="validation_current",
        )


class SyncLocalInstall:
    name = "SyncLocalInstall"
    reads = ("tests_passed",)
    writes = ("local_install_synced", "blocked")
    accepted_input_type = EvidenceReady
    input_description = "EvidenceReady"
    output_description = "InstallReady or DevelopmentBlocked"
    idempotency = "Editable install and skill sync can be rerun and checked by import path and content hashes."

    def apply(self, input_obj: EvidenceReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.local_install_synced:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "local_package_or_installed_skills_unsynced"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="local_install_unsynced",
            )
            return
        yield FunctionResult(
            output=InstallReady(input_obj.case_id, input_obj.git_publish_ready, input_obj.release_created),
            new_state=replace(state, local_install_synced=state.local_install_synced + (input_obj.case_id,)),
            label="local_install_synced",
        )


class PrepareGitPublish:
    name = "PrepareGitPublish"
    reads = ("local_install_synced",)
    writes = ("git_ready", "blocked")
    accepted_input_type = InstallReady
    input_description = "InstallReady"
    output_description = "GitReady or DevelopmentBlocked"
    idempotency = "Git readiness is checked against current worktree and remote state."

    def apply(self, input_obj: InstallReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.git_publish_ready:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "git_publish_not_ready"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="git_publish_not_ready",
            )
            return
        yield FunctionResult(
            output=GitReady(input_obj.case_id, input_obj.release_created),
            new_state=replace(state, git_ready=state.git_ready + (input_obj.case_id,)),
            label="git_publish_ready",
        )


class CreateRelease:
    name = "CreateRelease"
    reads = ("git_ready",)
    writes = ("releases_created", "blocked")
    accepted_input_type = GitReady
    input_description = "GitReady"
    output_description = "ReleaseDone or DevelopmentBlocked"
    idempotency = "Release creation is external and must not be claimed until confirmed."

    def apply(self, input_obj: GitReady, state: State) -> Iterable[FunctionResult]:
        if not input_obj.release_created:
            yield FunctionResult(
                output=DevelopmentBlocked(input_obj.case_id, "github_release_not_created"),
                new_state=replace(state, blocked=state.blocked + (input_obj.case_id,)),
                label="release_not_created",
            )
            return
        yield FunctionResult(
            output=ReleaseDone(input_obj.case_id),
            new_state=replace(state, releases_created=state.releases_created + (input_obj.case_id,)),
            label="release_created",
        )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del state, trace
    return isinstance(current_output, (ReleaseDone, DevelopmentBlocked))


def no_release_without_current_flowguard_and_tests(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.releases_created) - (set(state.flowguard_checked) & set(state.tests_passed))
    if missing:
        return InvariantResult.fail(f"release without FlowGuard/tests: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_release_without_local_sync(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.releases_created) - set(state.local_install_synced)
    if missing:
        return InvariantResult.fail(f"release without local install and skill sync: {sorted(missing)!r}")
    return InvariantResult.pass_()


def no_release_without_git_ready(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.releases_created) - set(state.git_ready)
    if missing:
        return InvariantResult.fail(f"release without git publish readiness: {sorted(missing)!r}")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="no_release_without_current_flowguard_and_tests",
        description="GitHub release needs current FlowGuard models and validation.",
        predicate=no_release_without_current_flowguard_and_tests,
    ),
    Invariant(
        name="no_release_without_local_sync",
        description="GitHub release needs local package and installed skill sync evidence.",
        predicate=no_release_without_local_sync,
    ),
    Invariant(
        name="no_release_without_git_ready",
        description="GitHub release needs current git publish readiness evidence.",
        predicate=no_release_without_git_ready,
    ),
)


EXTERNAL_INPUTS = (
    DevelopmentInput("clean_release", True, True, True, True, True, True, True, True),
    DevelopmentInput("openspec_gap", False, True, True, True, True, True, True, True),
    DevelopmentInput("flowguard_gap", True, False, True, True, True, True, True, True),
    DevelopmentInput("implementation_gap", True, True, False, True, True, True, True, True),
    DevelopmentInput("docs_skill_gap", True, True, True, False, True, True, True, True),
    DevelopmentInput("validation_gap", True, True, True, True, False, True, True, True),
    DevelopmentInput("sync_gap", True, True, True, True, True, False, True, True),
    DevelopmentInput("git_gap", True, True, True, True, True, True, False, True),
    DevelopmentInput("release_gap", True, True, True, True, True, True, True, False),
)

MAX_SEQUENCE_LENGTH = 1


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow(
        (
            ValidateOpenSpec(),
            CheckFlowGuardModels(),
            ImplementArtifacts(),
            RunValidation(),
            SyncLocalInstall(),
            PrepareGitPublish(),
            CreateRelease(),
        ),
        name="physicsguard_test_file_contract_development_process",
    )


__all__ = [
    "DevelopmentInput",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "build_workflow",
    "initial_state",
    "terminal_predicate",
]
