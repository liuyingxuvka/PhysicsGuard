"""Core execution primitives for PhysicsGuard."""

__all__ = [
    "BoundedSolver",
    "AuditEvaluator",
    "ComparisonResult",
    "ContractReview",
    "DiagnosticReporter",
    "ModuleRegistry",
    "ObservedEvaluationResult",
    "ResidualBuilder",
    "ResidualRecord",
    "SolverResult",
    "VariableRecord",
    "VariableDeviationDiagnostic",
    "VariableRegistry",
    "check_test_file_contract",
    "diff_test_file_contracts",
    "field_signature_hash",
    "generate_delimited_manifest",
    "inspect_test_file_contract",
    "sha256_file",
    "validate_model_dataset",
    "evaluate_hypothesis_observation",
    "freeze_hypothesis_plan",
    "rank_observation_candidates",
    "review_signal_mapping_ledger",
]


def __getattr__(name: str):
    if name == "DiagnosticReporter":
        from physicsguard.core.diagnostics import DiagnosticReporter

        return DiagnosticReporter
    if name in {"field_signature_hash", "generate_delimited_manifest", "sha256_file"}:
        from physicsguard.core.data_file_manifest import (
            field_signature_hash,
            generate_delimited_manifest,
            sha256_file,
        )

        return {
            "field_signature_hash": field_signature_hash,
            "generate_delimited_manifest": generate_delimited_manifest,
            "sha256_file": sha256_file,
        }[name]
    if name == "diff_test_file_contracts":
        from physicsguard.core.contract_diff import diff_test_file_contracts

        return diff_test_file_contracts
    if name == "ContractReview":
        from physicsguard.core.parameter_coverage import ContractReview
        return ContractReview
    if name in {
        "check_test_file_contract",
        "inspect_test_file_contract",
    }:
        from physicsguard.core.test_file_contract import (
            check_test_file_contract,
            inspect_test_file_contract,
        )

        return {
            "check_test_file_contract": check_test_file_contract,
            "inspect_test_file_contract": inspect_test_file_contract,
        }[name]
    if name == "review_signal_mapping_ledger":
        from physicsguard.core.signal_mapping import review_signal_mapping_ledger

        return review_signal_mapping_ledger
    if name == "validate_model_dataset":
        from physicsguard.core.model_dataset_validation import validate_model_dataset

        return validate_model_dataset
    if name in {
        "AuditEvaluator",
        "ComparisonResult",
        "ObservedEvaluationResult",
        "VariableDeviationDiagnostic",
    }:
        from physicsguard.core.evaluator import (
            AuditEvaluator,
            ComparisonResult,
            ObservedEvaluationResult,
            VariableDeviationDiagnostic,
        )

        return {
            "AuditEvaluator": AuditEvaluator,
            "ComparisonResult": ComparisonResult,
            "ObservedEvaluationResult": ObservedEvaluationResult,
            "VariableDeviationDiagnostic": VariableDeviationDiagnostic,
        }[name]
    if name in {"VariableRecord", "VariableRegistry"}:
        from physicsguard.core.registry import VariableRecord, VariableRegistry

        return {
            "VariableRecord": VariableRecord,
            "VariableRegistry": VariableRegistry,
        }[name]
    if name in {"ResidualBuilder", "ResidualRecord"}:
        from physicsguard.core.residual import ResidualBuilder, ResidualRecord

        return {
            "ResidualBuilder": ResidualBuilder,
            "ResidualRecord": ResidualRecord,
        }[name]
    if name in {"BoundedSolver", "SolverResult"}:
        from physicsguard.core.solver import BoundedSolver, SolverResult

        return {
            "BoundedSolver": BoundedSolver,
            "SolverResult": SolverResult,
        }[name]
    if name == "ModuleRegistry":
        from physicsguard.modules.registry import ModuleRegistry

        return ModuleRegistry
    if name in {
        "evaluate_hypothesis_observation",
        "freeze_hypothesis_plan",
        "rank_observation_candidates",
    }:
        from physicsguard.core.task_local_revision import (
            evaluate_hypothesis_observation,
            freeze_hypothesis_plan,
            rank_observation_candidates,
        )

        return {
            "evaluate_hypothesis_observation": evaluate_hypothesis_observation,
            "freeze_hypothesis_plan": freeze_hypothesis_plan,
            "rank_observation_candidates": rank_observation_candidates,
        }[name]
    raise AttributeError(name)
