"""Abstract lifecycle model for the isolated PhysicsGuard template-pack change.

This model proves process order and freshness rules only. Its abstract proof
artifacts never substitute for the real commands executed by this change.
"""

from __future__ import annotations

from flowguard import (
    PROCESS_ARTIFACT_CODE,
    PROCESS_ARTIFACT_MODEL,
    PROCESS_ARTIFACT_REQUIREMENT,
    PROCESS_ARTIFACT_TEST,
    PROCESS_EVIDENCE_PASSED,
    DevelopmentProcessPlan,
    FreshnessRule,
    ProofArtifactRef,
    ProcessAction,
    ProcessArtifact,
    ProcessEvidence,
    ValidationRequirement,
    review_development_process_flow,
)


PROVIDER_ID = "openspec"
WORK_PACKAGE_ID = "add-physicsguard-purpose-pack-builder"
TASK_IDS = ("task:2-models", "task:3-builder", "task:4-focused-tests")
OBLIGATION_IDS = (
    "obligation:deterministic-selection",
    "obligation:one-field-owner",
    "obligation:instance-fingerprint",
    "obligation:native-validation",
)
CHECK_IDS = (
    "check:existing-model-preflight",
    "check:risk-intent",
    "check:focused-pytest",
)


def proof_artifact(artifact_id: str, command: str, *covered: str) -> ProofArtifactRef:
    result_path = f"model-evidence/{artifact_id.replace(':', '_')}.json"
    return ProofArtifactRef(
        artifact_id,
        producer_route="development_process_flow",
        command=command,
        result_status=PROCESS_EVIDENCE_PASSED,
        exit_code=0,
        result_path=result_path,
        artifact_fingerprints={result_path: "sha256:abstract-model-proof"},
        covered_obligation_ids=covered,
        assertion_scope="abstract_process_model",
        metadata={
            "claim_boundary": "process-order simulation only; current commands and files remain separate evidence",
        },
    )


def artifacts(*, spec_version: str = "1", code_version: str = "1") -> tuple[ProcessArtifact, ...]:
    return (
        ProcessArtifact(
            "openspec.template-pack-change",
            PROCESS_ARTIFACT_REQUIREMENT,
            spec_version,
            path="openspec/changes/add-physicsguard-purpose-pack-builder",
            owner="openspec",
            description="Official provider-owned proposal/design/spec/tasks package; OpenSpec source is read-only.",
            spec_provider_id=PROVIDER_ID,
            work_package_id=WORK_PACKAGE_ID,
            spec_task_ids=TASK_IDS,
            spec_obligation_ids=OBLIGATION_IDS,
            spec_check_ids=CHECK_IDS,
        ),
        ProcessArtifact(
            "model.existing-owner-preflight",
            PROCESS_ARTIFACT_MODEL,
            "1",
            path="flowguard-model/.flowguard/existing_model_preflight",
            owner="existing_model_preflight",
            upstream_artifact_ids=("openspec.template-pack-change",),
        ),
        ProcessArtifact(
            "model.template-pack-selection",
            PROCESS_ARTIFACT_MODEL,
            "1",
            path="flowguard-model/.flowguard/risk_intent_check_plan",
            owner="model_first_function_flow",
            upstream_artifact_ids=(
                "openspec.template-pack-change",
                "model.existing-owner-preflight",
            ),
        ),
        ProcessArtifact(
            "manifest.physicsguard-purpose-packs",
            PROCESS_ARTIFACT_CODE,
            code_version,
            path="purpose_packs/physicsguard-purpose-packs.yaml",
            owner="physicsguard.template_packs",
            upstream_artifact_ids=(
                "openspec.template-pack-change",
                "model.template-pack-selection",
            ),
        ),
        ProcessArtifact(
            "code.physicsguard-template-pack-adapter",
            PROCESS_ARTIFACT_CODE,
            code_version,
            path="src/physicsguard/template_packs.py",
            owner="physicsguard.template_packs",
            upstream_artifact_ids=(
                "openspec.template-pack-change",
                "model.template-pack-selection",
                "manifest.physicsguard-purpose-packs",
            ),
        ),
        ProcessArtifact(
            "tests.physicsguard-template-packs",
            PROCESS_ARTIFACT_TEST,
            code_version,
            path="tests/test_template_packs.py",
            owner="pytest",
            upstream_artifact_ids=(
                "openspec.template-pack-change",
                "model.template-pack-selection",
                "manifest.physicsguard-purpose-packs",
                "code.physicsguard-template-pack-adapter",
            ),
        ),
    )


def correct_plan() -> DevelopmentProcessPlan:
    return DevelopmentProcessPlan(
        "physicsguard-template-pack-isolated-lifecycle",
        require_proof_artifacts=True,
        behavior_plane="development_process",
        require_behavior_plane_boundary=True,
        artifacts=artifacts(),
        actions=(
            ProcessAction(
                "freeze-openspec-package",
                reads_artifacts=("openspec.template-pack-change",),
                order_after=(),
                behavior_plane="development_process",
                spec_provider_id=PROVIDER_ID,
                spec_work_package_id=WORK_PACKAGE_ID,
                spec_task_ids=TASK_IDS,
                spec_obligation_ids=OBLIGATION_IDS,
                description="Read provider artifacts; do not modify OpenSpec source/install.",
            ),
            ProcessAction(
                "run-existing-owner-preflight",
                reads_artifacts=("openspec.template-pack-change", "model.existing-owner-preflight"),
                produced_evidence_ids=("evidence.existing-owner-preflight",),
                order_after=("freeze-openspec-package",),
                behavior_plane="development_process",
            ),
            ProcessAction(
                "run-selection-risk-model",
                reads_artifacts=("openspec.template-pack-change", "model.template-pack-selection"),
                required_evidence_ids=("evidence.existing-owner-preflight",),
                produced_evidence_ids=("evidence.selection-risk-model",),
                order_after=("run-existing-owner-preflight",),
                behavior_plane="development_process",
            ),
            ProcessAction(
                "add-isolated-manifest-and-adapter",
                reads_artifacts=(
                    "openspec.template-pack-change",
                    "model.template-pack-selection",
                ),
                writes_artifacts=(
                    "manifest.physicsguard-purpose-packs",
                    "code.physicsguard-template-pack-adapter",
                    "tests.physicsguard-template-packs",
                ),
                required_evidence_ids=("evidence.selection-risk-model",),
                order_after=("run-selection-risk-model",),
                behavior_plane="development_process",
            ),
            ProcessAction(
                "run-focused-template-pack-tests",
                reads_artifacts=(
                    "manifest.physicsguard-purpose-packs",
                    "code.physicsguard-template-pack-adapter",
                    "tests.physicsguard-template-packs",
                ),
                produced_evidence_ids=("evidence.focused-template-pack-tests",),
                order_after=("add-isolated-manifest-and-adapter",),
                behavior_plane="development_process",
            ),
            ProcessAction(
                "claim-isolated-handoff-ready",
                action_type="claim_done",
                required_validation_ids=(
                    "validation.existing-owner-preflight",
                    "validation.selection-risk-model",
                    "validation.focused-template-pack-tests",
                ),
                order_after=("run-focused-template-pack-tests",),
                behavior_plane="development_process",
                description=(
                    "Scoped handoff only; project adoption, skills, installation, Git, release, and physical validity remain unproven."
                ),
            ),
        ),
        evidence=(
            ProcessEvidence(
                "evidence.existing-owner-preflight",
                evidence_kind="model",
                producer_route="existing_model_preflight",
                status=PROCESS_EVIDENCE_PASSED,
                covers_artifacts=("openspec.template-pack-change", "model.existing-owner-preflight"),
                covered_versions={
                    "openspec.template-pack-change": "1",
                    "model.existing-owner-preflight": "1",
                },
                verifier_artifacts=("model.existing-owner-preflight",),
                validation_requirement_ids=("validation.existing-owner-preflight",),
                produced_by_action_id="run-existing-owner-preflight",
                command="python .flowguard/existing_model_preflight/run_checks.py",
                proof_artifact=proof_artifact(
                    "abstract:existing-owner-preflight",
                    "python .flowguard/existing_model_preflight/run_checks.py",
                    "validation.existing-owner-preflight",
                ),
            ),
            ProcessEvidence(
                "evidence.selection-risk-model",
                evidence_kind="model",
                producer_route="model_first_function_flow",
                status=PROCESS_EVIDENCE_PASSED,
                covers_artifacts=("openspec.template-pack-change", "model.template-pack-selection"),
                covered_versions={
                    "openspec.template-pack-change": "1",
                    "model.template-pack-selection": "1",
                },
                verifier_artifacts=("model.template-pack-selection",),
                validation_requirement_ids=("validation.selection-risk-model",),
                produced_by_action_id="run-selection-risk-model",
                command="python .flowguard/risk_intent_check_plan/run_checks.py",
                proof_artifact=proof_artifact(
                    "abstract:selection-risk-model",
                    "python .flowguard/risk_intent_check_plan/run_checks.py",
                    "validation.selection-risk-model",
                ),
            ),
            ProcessEvidence(
                "evidence.focused-template-pack-tests",
                evidence_kind="test",
                producer_route="test_mesh_maintenance",
                status=PROCESS_EVIDENCE_PASSED,
                covers_artifacts=(
                    "manifest.physicsguard-purpose-packs",
                    "code.physicsguard-template-pack-adapter",
                    "tests.physicsguard-template-packs",
                ),
                covered_versions={
                    "manifest.physicsguard-purpose-packs": "1",
                    "code.physicsguard-template-pack-adapter": "1",
                    "tests.physicsguard-template-packs": "1",
                },
                verifier_artifacts=("tests.physicsguard-template-packs",),
                validation_requirement_ids=("validation.focused-template-pack-tests",),
                produced_by_action_id="run-focused-template-pack-tests",
                command="pytest -q tests/test_template_packs.py",
                proof_artifact=proof_artifact(
                    "abstract:focused-template-pack-tests",
                    "pytest -q tests/test_template_packs.py",
                    "validation.focused-template-pack-tests",
                ),
            ),
        ),
        validation_requirements=(
            ValidationRequirement(
                "validation.existing-owner-preflight",
                required_artifact_ids=("openspec.template-pack-change", "model.existing-owner-preflight"),
                required_evidence_kinds=("model",),
                evidence_ids=("evidence.existing-owner-preflight",),
                command="python .flowguard/existing_model_preflight/run_checks.py",
                spec_provider_id=PROVIDER_ID,
                spec_work_package_id=WORK_PACKAGE_ID,
                spec_obligation_ids=("obligation:deterministic-selection",),
                spec_check_ids=("check:existing-model-preflight",),
            ),
            ValidationRequirement(
                "validation.selection-risk-model",
                required_artifact_ids=("openspec.template-pack-change", "model.template-pack-selection"),
                required_evidence_kinds=("model",),
                evidence_ids=("evidence.selection-risk-model",),
                command="python .flowguard/risk_intent_check_plan/run_checks.py",
                spec_provider_id=PROVIDER_ID,
                spec_work_package_id=WORK_PACKAGE_ID,
                spec_obligation_ids=(
                    "obligation:deterministic-selection",
                    "obligation:one-field-owner",
                ),
                spec_check_ids=("check:risk-intent",),
            ),
            ValidationRequirement(
                "validation.focused-template-pack-tests",
                required_artifact_ids=(
                    "manifest.physicsguard-purpose-packs",
                    "code.physicsguard-template-pack-adapter",
                    "tests.physicsguard-template-packs",
                ),
                required_evidence_kinds=("test",),
                evidence_ids=("evidence.focused-template-pack-tests",),
                v_model_pair=True,
                command="pytest -q tests/test_template_packs.py",
                spec_provider_id=PROVIDER_ID,
                spec_work_package_id=WORK_PACKAGE_ID,
                spec_obligation_ids=OBLIGATION_IDS,
                spec_check_ids=("check:focused-pytest",),
            ),
        ),
        freshness_rules=(
            FreshnessRule(
                "spec-change-invalidates-model-code-and-tests",
                upstream_artifact_id="openspec.template-pack-change",
                invalidates_artifact_ids=(
                    "model.existing-owner-preflight",
                    "model.template-pack-selection",
                    "manifest.physicsguard-purpose-packs",
                    "code.physicsguard-template-pack-adapter",
                    "tests.physicsguard-template-packs",
                ),
                invalidates_evidence_kinds=("model", "test"),
            ),
            FreshnessRule(
                "selection-model-change-invalidates-implementation",
                upstream_artifact_id="model.template-pack-selection",
                invalidates_artifact_ids=(
                    "manifest.physicsguard-purpose-packs",
                    "code.physicsguard-template-pack-adapter",
                    "tests.physicsguard-template-packs",
                ),
                invalidates_evidence_kinds=("test",),
            ),
            FreshnessRule(
                "manifest-change-invalidates-focused-tests",
                upstream_artifact_id="manifest.physicsguard-purpose-packs",
                invalidates_artifact_ids=("tests.physicsguard-template-packs",),
                invalidates_evidence_kinds=("test",),
            ),
            FreshnessRule(
                "adapter-change-invalidates-focused-tests",
                upstream_artifact_id="code.physicsguard-template-pack-adapter",
                invalidates_artifact_ids=("tests.physicsguard-template-packs",),
                invalidates_evidence_kinds=("test",),
            ),
        ),
    )


def broken_stale_plan() -> DevelopmentProcessPlan:
    plan = correct_plan()
    return DevelopmentProcessPlan(
        "physicsguard-template-pack-stale-lifecycle",
        require_proof_artifacts=False,
        behavior_plane="development_process",
        require_behavior_plane_boundary=True,
        artifacts=artifacts(spec_version="2", code_version="2"),
        actions=(
            ProcessAction(
                "run-old-focused-tests",
                produced_evidence_ids=("evidence.focused-template-pack-tests",),
                behavior_plane="development_process",
            ),
            ProcessAction(
                "change-spec-and-adapter-after-tests",
                writes_artifacts=(
                    "openspec.template-pack-change",
                    "code.physicsguard-template-pack-adapter",
                ),
                order_after=("run-old-focused-tests",),
                behavior_plane="development_process",
            ),
            ProcessAction(
                "claim-stale-handoff-ready",
                action_type="claim_done",
                required_validation_ids=("validation.focused-template-pack-tests",),
                order_after=("change-spec-and-adapter-after-tests",),
                behavior_plane="development_process",
            ),
        ),
        evidence=plan.evidence,
        validation_requirements=plan.validation_requirements,
        freshness_rules=plan.freshness_rules,
    )


def run_checks():
    return (
        review_development_process_flow(correct_plan()),
        review_development_process_flow(broken_stale_plan()),
    )
