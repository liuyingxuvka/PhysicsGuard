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
    "check_parameter_coverage",
    "build_project_evidence_map",
    "check_logical_dataset_record",
    "check_model_library_index",
    "check_evidence_bundle",
    "check_evidence_gaps",
    "check_evidence_mesh",
    "check_project_evidence_registry",
    "check_test_file_contract",
    "check_test_file_parameter_coverage",
    "check_test_file_project_index",
    "diff_test_file_contracts",
    "field_signature_hash",
    "load_fmi_observation_request",
    "observe_fmi_observation_request",
    "review_fmi_observation_request",
    "generate_delimited_manifest",
    "inspect_test_file_contract",
    "affected_physical_blueprint_projection",
    "compile_physical_blueprint_graph",
    "full_physical_blueprint_projection",
    "physical_model_blueprint_review_to_dict",
    "reverse_trace_physical_blueprint_projection",
    "review_physical_model_blueprint",
    "run_project_closure",
    "scan_project_evidence_candidates",
    "sha256_file",
    "summary_physical_blueprint_projection",
    "build_module_behavior_contract_index",
    "build_physical_blueprint_export_bundle",
    "load_physical_blueprint_export_bundle",
    "materialize_physical_blueprint_export_bundle",
    "query_physical_blueprint_export_bundle",
    "validate_model_dataset",
    "evaluate_candidate_model_revision",
    "evaluate_hypothesis_observation",
    "freeze_hypothesis_plan",
    "rank_observation_candidates",
    "review_project_profile_authority",
    "review_signal_mapping_ledger",
]


def __getattr__(name: str):
    if name in {
        "load_fmi_observation_request",
        "observe_fmi_observation_request",
        "review_fmi_observation_request",
    }:
        from physicsguard.core.fmi_observation import (
            load_fmi_observation_request,
            observe_fmi_observation_request,
            review_fmi_observation_request,
        )

        return {
            "load_fmi_observation_request": load_fmi_observation_request,
            "observe_fmi_observation_request": observe_fmi_observation_request,
            "review_fmi_observation_request": review_fmi_observation_request,
        }[name]
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
    if name in {"ContractReview", "check_parameter_coverage"}:
        from physicsguard.core.parameter_coverage import ContractReview, check_parameter_coverage

        return {
            "ContractReview": ContractReview,
            "check_parameter_coverage": check_parameter_coverage,
        }[name]
    if name in {
        "check_test_file_contract",
        "check_test_file_parameter_coverage",
        "check_test_file_project_index",
        "inspect_test_file_contract",
    }:
        from physicsguard.core.test_file_contract import (
            check_test_file_contract,
            check_test_file_parameter_coverage,
            check_test_file_project_index,
            inspect_test_file_contract,
        )

        return {
            "check_test_file_contract": check_test_file_contract,
            "check_test_file_parameter_coverage": check_test_file_parameter_coverage,
            "check_test_file_project_index": check_test_file_project_index,
            "inspect_test_file_contract": inspect_test_file_contract,
        }[name]
    if name == "review_project_profile_authority":
        from physicsguard.core.project_evidence import review_project_profile_authority

        return review_project_profile_authority
    if name == "review_signal_mapping_ledger":
        from physicsguard.core.signal_mapping import review_signal_mapping_ledger

        return review_signal_mapping_ledger
    if name in {"check_logical_dataset_record", "check_test_file_relation_index"}:
        from physicsguard.core.dataset_identity import (
            check_logical_dataset_record,
            check_test_file_relation_index,
        )

        return {
            "check_logical_dataset_record": check_logical_dataset_record,
            "check_test_file_relation_index": check_test_file_relation_index,
        }[name]
    if name == "validate_model_dataset":
        from physicsguard.core.model_dataset_validation import validate_model_dataset

        return validate_model_dataset
    if name == "check_model_library_index":
        from physicsguard.core.model_library import check_model_library_index

        return check_model_library_index
    if name == "run_project_closure":
        from physicsguard.core.project_closure import run_project_closure

        return run_project_closure
    if name in {
        "check_evidence_mesh",
    }:
        from physicsguard.core.evidence_mesh import check_evidence_mesh

        return check_evidence_mesh
    if name in {
        "check_evidence_bundle",
        "check_evidence_gaps",
        "check_project_evidence_registry",
        "build_project_evidence_map",
        "scan_project_evidence_candidates",
    }:
        from physicsguard.core.project_evidence import (
            build_project_evidence_map,
            check_evidence_bundle,
            check_evidence_gaps,
            check_project_evidence_registry,
            scan_project_evidence_candidates,
        )

        return {
            "check_evidence_bundle": check_evidence_bundle,
            "check_evidence_gaps": check_evidence_gaps,
            "check_project_evidence_registry": check_project_evidence_registry,
            "build_project_evidence_map": build_project_evidence_map,
            "scan_project_evidence_candidates": scan_project_evidence_candidates,
        }[name]
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
        "affected_physical_blueprint_projection",
        "compile_physical_blueprint_graph",
        "full_physical_blueprint_projection",
        "reverse_trace_physical_blueprint_projection",
        "summary_physical_blueprint_projection",
    }:
        from physicsguard.core.physical_blueprint_trace import (
            affected_physical_blueprint_projection,
            compile_physical_blueprint_graph,
            full_physical_blueprint_projection,
            reverse_trace_physical_blueprint_projection,
            summary_physical_blueprint_projection,
        )

        return {
            "affected_physical_blueprint_projection": affected_physical_blueprint_projection,
            "compile_physical_blueprint_graph": compile_physical_blueprint_graph,
            "full_physical_blueprint_projection": full_physical_blueprint_projection,
            "reverse_trace_physical_blueprint_projection": reverse_trace_physical_blueprint_projection,
            "summary_physical_blueprint_projection": summary_physical_blueprint_projection,
        }[name]
    if name in {
        "physical_model_blueprint_review_to_dict",
        "review_physical_model_blueprint",
    }:
        from physicsguard.core.physical_model_blueprint import (
            physical_model_blueprint_review_to_dict,
            review_physical_model_blueprint,
        )

        return {
            "physical_model_blueprint_review_to_dict": physical_model_blueprint_review_to_dict,
            "review_physical_model_blueprint": review_physical_model_blueprint,
        }[name]
    if name in {
        "build_module_behavior_contract_index",
        "build_physical_blueprint_export_bundle",
        "load_physical_blueprint_export_bundle",
        "materialize_physical_blueprint_export_bundle",
        "query_physical_blueprint_export_bundle",
    }:
        from physicsguard.core.physical_blueprint_bundle import (
            build_module_behavior_contract_index,
            build_physical_blueprint_export_bundle,
            load_physical_blueprint_export_bundle,
            materialize_physical_blueprint_export_bundle,
            query_physical_blueprint_export_bundle,
        )

        return {
            "build_module_behavior_contract_index": build_module_behavior_contract_index,
            "build_physical_blueprint_export_bundle": build_physical_blueprint_export_bundle,
            "load_physical_blueprint_export_bundle": load_physical_blueprint_export_bundle,
            "materialize_physical_blueprint_export_bundle": materialize_physical_blueprint_export_bundle,
            "query_physical_blueprint_export_bundle": query_physical_blueprint_export_bundle,
        }[name]
    if name in {
        "evaluate_candidate_model_revision",
        "evaluate_hypothesis_observation",
        "freeze_hypothesis_plan",
        "rank_observation_candidates",
    }:
        from physicsguard.core.task_local_revision import (
            evaluate_candidate_model_revision,
            evaluate_hypothesis_observation,
            freeze_hypothesis_plan,
            rank_observation_candidates,
        )

        return {
            "evaluate_candidate_model_revision": evaluate_candidate_model_revision,
            "evaluate_hypothesis_observation": evaluate_hypothesis_observation,
            "freeze_hypothesis_plan": freeze_hypothesis_plan,
            "rank_observation_candidates": rank_observation_candidates,
        }[name]
    raise AttributeError(name)
